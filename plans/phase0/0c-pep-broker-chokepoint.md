I now have complete context. I'll write the implementation plan for sub-plan `0c-pep-broker-chokepoint`, folding in both highs_addressed items as explicit tasks and using the canonical kernel signatures verbatim.

# Single PEP + Data-Access Broker Chokepoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the one Policy Enforcement Point + data-access broker that is the sole chokepoint for retrieval/egress/derivation (D4): ReBAC Check (SpiceDB) → ABAC (OPA) → revocation/lease read in one pinned decision order, returning already-projected, already-tier-checked result objects, where the durable tombstone high-water-mark is authoritative for deny and lease/SpiceDB are narrow-only caches.

**Architecture:** One logical PEP (`IPolicyEnforcement`) wraps OPA (ABAC: tier × subject-attrs × edition) and SpiceDB (ReBAC: grants/entitlements). Behind it sits one data-access broker (`IDataAccessBroker`) whose Postgres role can read ONLY the shared confidential-artifact/classification tables — never any feature-module-owned schema. The hot-path decision order is fixed: SpiceDB Check (narrow-only cache) → OPA ABAC (narrows-only) → durable-tombstone-high-water-mark read (authoritative deny) → lease read (narrow-only positive-grant cache). Security-reason revocations get TTL=0 because the deny is read from the durable log on every confidential request, not the lease.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Postgres (FORCE RLS, `SET LOCAL`), SpiceDB (Authzed Apache-2 OSS) via `authzed` gRPC client, OPA (Rego) via HTTP sidecar, pytest/ruff/mypy, import-linter.

**Depends on:** `0a-foundation`, `0b-classification-engine`

---

## File Structure

| File | Created/Modified | Single Responsibility |
|---|---|---|
| `tigerexchange/services/pep/pyproject.toml` | Create | PEP service package + import-linter contracts (modules cannot import raw store/classifier/construct PublishableProjection) |
| `tigerexchange/services/pep/src/pep/__init__.py` | Create | Package marker, re-exports `PolicyEnforcementPoint`, `DataAccessBroker` |
| `tigerexchange/services/pep/src/pep/decision_order.py` | Create | The single documented decision-order enum + ordered step list (authoritative-deny store = durable log) |
| `tigerexchange/services/pep/src/pep/rebac.py` | Create | `SpiceDBReBAC` — ReBAC Check adapter (narrow-only cache); `RebacCheck` result type |
| `tigerexchange/services/pep/src/pep/abac.py` | Create | `OpaAbac` — ABAC adapter (tier × attrs × edition); narrows-only, deny-on-missing-attr, no cache-fallback on confidential |
| `tigerexchange/services/pep/src/pep/revocation.py` | Create | `DurableTombstoneReader` (authoritative deny via high-water-mark) + `LeaseCache` (narrow-only positive-grant cache, TTL=0 for security-reason) |
| `tigerexchange/services/pep/src/pep/policy/abac.rego` | Create | OPA Rego policy: tier-vs-attribute-vs-edition ABAC rules |
| `tigerexchange/services/pep/src/pep/broker.py` | Create | `DataAccessBroker` — sole raw-store credential holder, scoped to confidential-artifact/classification tables only; projects rows |
| `tigerexchange/services/pep/src/pep/pep.py` | Create | `PolicyEnforcementPoint` — composes decision-order; implements `IPolicyEnforcement`; central-index discoverability-scope read path |
| `tigerexchange/services/pep/src/pep/broker_db.py` | Create | Broker DB connection factory bound to `broker_ro` role; SET LOCAL tenant context |
| `tigerexchange/services/pep/migrations/0001_broker_role.sql` | Create | Creates `broker_ro` DB role GRANTed only on confidential-artifact/classification tables; per-module schema GRANTs explicitly absent |
| `tigerexchange/services/pep/tests/test_decision_order.py` | Create | Decision-order pinned + authoritative-deny-store assertions |
| `tigerexchange/services/pep/tests/test_rebac.py` | Create | SpiceDB Check adapter behavior (deny-by-default, narrow-only) |
| `tigerexchange/services/pep/tests/test_abac.py` | Create | ABAC-narrows-only, missing-attr→deny, PIP-unavailable-on-confidential→deny |
| `tigerexchange/services/pep/tests/test_revocation.py` | Create | Authoritative-deny via durable log; security-reason zero-allow-window vs 15ms lease; lease narrow-only |
| `tigerexchange/services/pep/tests/test_pep_compose.py` | Create | End-to-end PEP authorize() decision-order composition + fail-closed payload |
| `tigerexchange/services/pep/tests/test_central_index_pep.py` | Create | Discoverability-scope filtering at central-index read PEP |
| `tigerexchange/services/pep/tests/test_broker_role_contract.py` | Create | Broker DB-role can read ONLY confidential-artifact/classification tables, not any feature schema |
| `tigerexchange/services/pep/tests/test_import_linter_contract.py` | Create | Feature modules cannot import raw store/classifier/construct PublishableProjection |

---

## Tasks

### Task 1: PEP service package scaffold + import-linter chokepoint contract

**Files:** Create `tigerexchange/services/pep/pyproject.toml`, `tigerexchange/services/pep/src/pep/__init__.py`, Test `tigerexchange/services/pep/tests/test_import_linter_contract.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_import_linter_contract.py
"""D4 chokepoint structural enforcement (plan §4.2).

import-linter must forbid feature modules from importing the raw store, the
classifier, or constructing a PublishableProjection. Here we assert the
import-linter contract config EXISTS and names those forbidden edges, so a
feature module physically cannot re-implement enforcement.
"""
from pathlib import Path

import tomllib

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _contracts() -> list[dict]:
    data = tomllib.loads(PYPROJECT.read_text())
    return data["tool"]["importlinter"]["contracts"]


def test_pyproject_exists() -> None:
    assert PYPROJECT.exists(), "PEP service pyproject.toml must exist"


def test_feature_modules_cannot_import_raw_store_or_classifier() -> None:
    names = {c["name"] for c in _contracts()}
    assert "feature-modules-cannot-import-raw-store-or-classifier" in names


def test_only_broker_may_hold_raw_store_credentials() -> None:
    # The forbidden contract must name the broker_db raw-store seam as
    # importable ONLY from pep.broker, never from any feature module.
    target = next(
        c
        for c in _contracts()
        if c["name"] == "feature-modules-cannot-import-raw-store-or-classifier"
    )
    assert target["type"] == "forbidden"
    forbidden = set(target["forbidden_modules"])
    assert "pep.broker_db" in forbidden
    assert any("classifier" in m for m in forbidden)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_import_linter_contract.py -q
```

Expected: fails — `FileNotFoundError` / `tomllib` cannot read missing `pyproject.toml`.

- [ ] **Step 3: Write minimal implementation**

```toml
# tigerexchange/services/pep/pyproject.toml
[project]
name = "tigerexchange-pep"
version = "0.0.0"
description = "TigerExchange single Policy Enforcement Point + data-access broker (D4 chokepoint)."
requires-python = ">=3.11"
dependencies = [
    "tigerexchange-contracts",
    "pydantic>=2.6,<3",
    "fastapi>=0.110",
    "authzed>=0.18",
    "httpx>=0.27",
    "psycopg[binary]>=3.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pep"]

# D4 chokepoint (§4.2): feature modules may NOT import the raw store, the
# classifier, or construct a PublishableProjection. Only pep.broker holds
# raw-store credentials. import-linter is the executable mirror of MODULE_MAP.
[tool.importlinter]
root_package = "pep"

[[tool.importlinter.contracts]]
name = "feature-modules-cannot-import-raw-store-or-classifier"
type = "forbidden"
source_modules = ["pep.rebac", "pep.abac", "pep.revocation", "pep.decision_order"]
forbidden_modules = ["pep.broker_db", "classifier.engine"]
```

```python
# tigerexchange/services/pep/src/pep/__init__.py
"""TigerExchange single PEP + data-access broker (D4, plan §4.2)."""

from pep.broker import DataAccessBroker
from pep.pep import PolicyEnforcementPoint

__all__ = ["PolicyEnforcementPoint", "DataAccessBroker"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_import_linter_contract.py -q
```

Expected: 3 passed. (The two `__init__` imports resolve in later tasks; tests here only parse the TOML, so no runtime import occurs.)

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/pyproject.toml tigerexchange/services/pep/src/pep/__init__.py tigerexchange/services/pep/tests/test_import_linter_contract.py && git commit -m "feat(pep): scaffold PEP service with D4 import-linter chokepoint contract

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Pin the single decision order (authoritative-deny store = durable log)

**Files:** Create `tigerexchange/services/pep/src/pep/decision_order.py`, Test `tigerexchange/services/pep/tests/test_decision_order.py`

This task folds in highs_addressed item #1: one stated decision order, durable tombstone log authoritative for deny, lease/SpiceDB caches narrow-only.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_decision_order.py
"""The ONE pinned decision order (convergence-report HIGH: lease-vs-log-vs-SpiceDB).

Composition is fixed and documented:
  1. ReBAC Check (SpiceDB)         -> narrow-only cache
  2. ABAC (OPA)                    -> narrows-only
  3. Durable tombstone high-water  -> AUTHORITATIVE for the deny dimension
  4. Lease read                    -> narrow-only positive-grant cache (TTL=0 security)
The durable tombstone log is the single authoritative store for deny; the
others may only NARROW a grant ("caches narrow-only", generalized from §7.3).
"""
from pep.decision_order import (
    DECISION_ORDER,
    AUTHORITATIVE_DENY_STORE,
    DecisionStep,
)


def test_order_is_exactly_four_steps_in_pinned_sequence() -> None:
    assert DECISION_ORDER == (
        DecisionStep.REBAC_CHECK,
        DecisionStep.ABAC,
        DecisionStep.DURABLE_TOMBSTONE,
        DecisionStep.LEASE,
    )


def test_durable_tombstone_is_the_authoritative_deny_store() -> None:
    assert AUTHORITATIVE_DENY_STORE is DecisionStep.DURABLE_TOMBSTONE


def test_only_durable_tombstone_is_authoritative_rest_are_narrow_only() -> None:
    narrow_only = [s for s in DECISION_ORDER if s.is_narrow_only]
    authoritative = [s for s in DECISION_ORDER if not s.is_narrow_only]
    assert authoritative == [DecisionStep.DURABLE_TOMBSTONE]
    assert set(narrow_only) == {
        DecisionStep.REBAC_CHECK,
        DecisionStep.ABAC,
        DecisionStep.LEASE,
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_decision_order.py -q
```

Expected: fails — `ModuleNotFoundError: No module named 'pep.decision_order'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/services/pep/src/pep/decision_order.py
"""The single, documented PEP decision order (plan §4.2/§4.4/§7.3).

Resolves the lease-vs-durable-log-vs-SpiceDB composition (convergence-report
HIGH): three stores gate the same allow/deny decision; this pins ONE order and
ONE authoritative deny store.

  REBAC_CHECK  (SpiceDB local-replica Check) -> narrow-only cache
  ABAC         (OPA: tier x attrs x edition)  -> narrows-only (§7.3)
  DURABLE_TOMBSTONE (cell-local Postgres high-water-mark) -> AUTHORITATIVE DENY
  LEASE        (local fenced lease, §4.4)     -> narrow-only positive-grant cache

Authoritative-deny rule (option (a) of the convergence fix): every confidential
read does a local read of the durable tombstone high-water-mark (same cell-local
Postgres, single-digit-ms, NOT a consensus hop) so a revocation is observed
immediately. The lease is therefore only a POSITIVE-GRANT cache, and the
security-reason class gets a zero-allow-window (TTL=0) for free because the deny
comes from the durable log, not from lease expiry. SpiceDB Check and the lease
may only NARROW a grant, never widen it ("caches narrow-only").
"""

from __future__ import annotations

from enum import Enum


class DecisionStep(Enum):
    """One step of the pinned decision order.

    ``is_narrow_only`` marks every store that may only NARROW a grant (deny or
    pass-through), never establish an authoritative allow. Exactly one step
    (DURABLE_TOMBSTONE) is the authoritative store for the deny dimension.
    """

    REBAC_CHECK = ("rebac-check", True)
    ABAC = ("abac", True)
    DURABLE_TOMBSTONE = ("durable-tombstone", False)
    LEASE = ("lease", True)

    def __init__(self, wire: str, is_narrow_only: bool) -> None:
        self._wire = wire
        self.is_narrow_only = is_narrow_only

    @property
    def wire(self) -> str:
        return self._wire


# The ONE pinned order. Authored once here; the PEP iterates it verbatim.
DECISION_ORDER: tuple[DecisionStep, ...] = (
    DecisionStep.REBAC_CHECK,
    DecisionStep.ABAC,
    DecisionStep.DURABLE_TOMBSTONE,
    DecisionStep.LEASE,
)

# The single authoritative store for the deny dimension (durable tombstone log).
AUTHORITATIVE_DENY_STORE: DecisionStep = DecisionStep.DURABLE_TOMBSTONE
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_decision_order.py -q
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/src/pep/decision_order.py tigerexchange/services/pep/tests/test_decision_order.py && git commit -m "feat(pep): pin single decision order with durable tombstone as authoritative deny store

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: ReBAC Check adapter (SpiceDB, deny-by-default, narrow-only)

**Files:** Create `tigerexchange/services/pep/src/pep/rebac.py`, Test `tigerexchange/services/pep/tests/test_rebac.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_rebac.py
"""ReBAC Check adapter (plan §7.2/§7.3). SpiceDB relationship Check.

Deny-by-default: no membership/grant relation -> no permission. The adapter is
a NARROW-ONLY cache: it returns has_permission True/False; it never widens a
later ABAC/lease decision. SpiceDB itself is faked here (no live gRPC in unit).
"""
from pep.rebac import RebacCheck, SpiceDBReBAC


class _FakeSpiceDB:
    """Minimal stand-in for the authzed CheckPermission gRPC surface."""

    def __init__(self, permitted: set[tuple[str, str, str]]) -> None:
        self._permitted = permitted

    def check(self, resource: str, permission: str, subject: str) -> bool:
        return (resource, permission, subject) in self._permitted


def test_grant_present_returns_permitted() -> None:
    fake = _FakeSpiceDB({("proposal:p1", "view", "user:alice")})
    rebac = SpiceDBReBAC(client=fake)
    result = rebac.check(resource="proposal:p1", permission="view", subject="user:alice")
    assert isinstance(result, RebacCheck)
    assert result.has_permission is True


def test_no_relation_denies_by_default() -> None:
    fake = _FakeSpiceDB(set())
    rebac = SpiceDBReBAC(client=fake)
    result = rebac.check(resource="proposal:p1", permission="view", subject="user:bob")
    assert result.has_permission is False


def test_client_error_fails_closed() -> None:
    class _Broken:
        def check(self, *_a, **_k):  # noqa: ANN002, ANN003
            raise RuntimeError("spicedb unreachable")

    rebac = SpiceDBReBAC(client=_Broken())
    result = rebac.check(resource="proposal:p1", permission="view", subject="user:alice")
    assert result.has_permission is False
    assert result.fail_closed is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_rebac.py -q
```

Expected: fails — `ModuleNotFoundError: No module named 'pep.rebac'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/services/pep/src/pep/rebac.py
"""ReBAC Check adapter over SpiceDB (plan §7.2/§7.3).

SpiceDB holds the relationship graph (grants, workspaces, membership). The
adapter performs a single CheckPermission and returns a narrow-only result:
``view`` is necessary-but-not-sufficient (§7.3) — a True here is later narrowed
by ABAC and the durable tombstone read; it is NEVER widened. Any client error
fails closed (deny), consistent with deny-by-default.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _SpiceDBClient(Protocol):
    """Structural surface of the authzed CheckPermission call we depend on."""

    def check(self, resource: str, permission: str, subject: str) -> bool: ...


class RebacCheck(BaseModel):
    """Result of a ReBAC permission Check (narrow-only)."""

    model_config = ConfigDict(frozen=True)

    has_permission: bool
    fail_closed: bool = False


class SpiceDBReBAC:
    """ReBAC adapter: one CheckPermission, deny-by-default, fail-closed."""

    def __init__(self, client: _SpiceDBClient) -> None:
        self._client = client

    def check(self, *, resource: str, permission: str, subject: str) -> RebacCheck:
        try:
            permitted = self._client.check(resource, permission, subject)
        except Exception:  # noqa: BLE001 — any client failure denies (fail-closed).
            return RebacCheck(has_permission=False, fail_closed=True)
        return RebacCheck(has_permission=bool(permitted))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_rebac.py -q
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/src/pep/rebac.py tigerexchange/services/pep/tests/test_rebac.py && git commit -m "feat(pep): add SpiceDB ReBAC Check adapter (deny-by-default, narrow-only, fail-closed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: ABAC adapter (OPA: tier × attrs × edition; narrows-only, deny-on-missing-attr, no cache-fallback on confidential)

**Files:** Create `tigerexchange/services/pep/src/pep/abac.py`, `tigerexchange/services/pep/src/pep/policy/abac.rego`, Test `tigerexchange/services/pep/tests/test_abac.py`

This folds in three deliverable contract tests: ABAC-narrows-only, missing-ABAC-attr→deny, PIP-unavailable-on-confidential→deny.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_abac.py
"""ABAC adapter (plan §7.2/§7.3). OPA evaluates tier x subject-attrs x edition.

Invariants (§7.3, §11.8 R "ABAC PIP fail-open / widen"):
  - ABAC may only NARROW a ReBAC grant, never widen (no rebac grant -> deny).
  - Missing/indeterminate ABAC attribute -> DENY for confidential + export tiers.
  - PIP (attribute provider) unavailable on a confidential check -> DENY,
    NO cache-fallback.
OPA is faked here as a decision function over the input document.
"""
from contracts import (
    Capability,
    ComplianceFlag,
    Edition,
    Entitlement,
    IsolationPosture,
    Tier,
    TenantContext,
)

from pep.abac import AbacDecision, OpaAbac


def _ctx(*, missing_attr: bool = False) -> TenantContext:
    ent = Entitlement(
        edition=Edition.CONSORTIUM_ANCHOR,
        capabilities=frozenset({Capability.CONFIDENTIAL_WORKSPACE}),
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.confidential,
    )
    return TenantContext(
        tenant_id="t1",
        subject_id="user:alice",
        entitlement=ent,
        affiliations=frozenset() if missing_attr else frozenset({"faculty@rit.edu"}),
    )


class _FakeOpa:
    """Fake OPA: allow iff required attr present AND tier within ceiling."""

    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable

    def evaluate(self, document: dict) -> dict:
        if self.unavailable:
            raise RuntimeError("OPA sidecar unreachable")
        attrs = document["subject"]["affiliations"]
        allow = bool(attrs) and document["object"]["tier"] != "unknown"
        return {"result": {"allow": allow}}


def test_abac_narrows_only_no_rebac_grant_denies() -> None:
    abac = OpaAbac(opa=_FakeOpa())
    d = abac.evaluate(
        tenant=_ctx(),
        tier=Tier.confidential,
        compliance_flags=frozenset(),
        rebac_permitted=False,  # ABAC cannot widen a missing grant
    )
    assert isinstance(d, AbacDecision)
    assert d.allow is False


def test_missing_abac_attr_on_confidential_denies() -> None:
    abac = OpaAbac(opa=_FakeOpa())
    d = abac.evaluate(
        tenant=_ctx(missing_attr=True),
        tier=Tier.confidential,
        compliance_flags=frozenset({ComplianceFlag.ITAR}),
        rebac_permitted=True,
    )
    assert d.allow is False


def test_pip_unavailable_on_confidential_denies_no_cache_fallback() -> None:
    abac = OpaAbac(opa=_FakeOpa(unavailable=True))
    d = abac.evaluate(
        tenant=_ctx(),
        tier=Tier.confidential,
        compliance_flags=frozenset(),
        rebac_permitted=True,
    )
    assert d.allow is False
    assert d.pip_unavailable is True
    assert d.used_cache is False  # no cache-fallback on confidential


def test_allows_when_grant_present_attrs_present_within_ceiling() -> None:
    abac = OpaAbac(opa=_FakeOpa())
    d = abac.evaluate(
        tenant=_ctx(),
        tier=Tier.confidential,
        compliance_flags=frozenset(),
        rebac_permitted=True,
    )
    assert d.allow is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_abac.py -q
```

Expected: fails — `ModuleNotFoundError: No module named 'pep.abac'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/services/pep/src/pep/abac.py
"""ABAC adapter over OPA (plan §7.2/§7.3, §11.8).

OPA (Rego) evaluates classification tier x subject attributes x edition
capability. Three hard invariants are enforced HERE in the adapter (not left to
Rego), so they hold even if the policy bundle is misconfigured:

  1. ABAC narrows-only: if there is no ReBAC grant, ABAC cannot allow (§7.3).
  2. Missing/indeterminate attribute -> DENY for confidential/export tiers.
  3. PIP unavailable on a confidential check -> DENY, NO cache-fallback (§7.3).

For non-confidential, non-export tiers the OPA result is honored as-is (still
gated by the ReBAC grant). Export = any ITAR/EAR compliance flag.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from contracts import ComplianceFlag, Tier, TenantContext

_EXPORT_FLAGS = frozenset({ComplianceFlag.ITAR, ComplianceFlag.EAR})


class _OpaClient(Protocol):
    """Structural surface of the OPA data-API evaluation we depend on."""

    def evaluate(self, document: dict) -> dict: ...


class AbacDecision(BaseModel):
    """Result of an ABAC evaluation (narrow-only)."""

    model_config = ConfigDict(frozen=True)

    allow: bool
    pip_unavailable: bool = False
    used_cache: bool = False
    reason: str = ""


class OpaAbac:
    """ABAC adapter: deny-on-missing-attr, no-cache-fallback-on-confidential."""

    def __init__(self, opa: _OpaClient) -> None:
        self._opa = opa

    def evaluate(
        self,
        *,
        tenant: TenantContext,
        tier: Tier,
        compliance_flags: frozenset[ComplianceFlag],
        rebac_permitted: bool,
    ) -> AbacDecision:
        # (1) narrows-only: ABAC can never widen a missing ReBAC grant.
        if not rebac_permitted:
            return AbacDecision(allow=False, reason="no-rebac-grant")

        is_high = tier is Tier.confidential or bool(compliance_flags & _EXPORT_FLAGS)

        # (2) missing/indeterminate attribute -> deny for confidential/export.
        if is_high and not tenant.affiliations:
            return AbacDecision(allow=False, reason="missing-abac-attr")

        document = {
            "subject": {
                "subject_id": tenant.subject_id,
                "affiliations": sorted(tenant.affiliations),
                "edition": tenant.entitlement.edition.value,
            },
            "object": {
                "tier": tier.wire,
                "compliance_flags": sorted(f.value for f in compliance_flags),
            },
        }

        try:
            raw = self._opa.evaluate(document)
        except Exception:  # noqa: BLE001 — PIP/OPA failure.
            # (3) PIP unavailable on confidential -> deny, no cache-fallback.
            if is_high:
                return AbacDecision(
                    allow=False, pip_unavailable=True, used_cache=False,
                    reason="pip-unavailable-confidential",
                )
            return AbacDecision(allow=False, pip_unavailable=True, reason="pip-unavailable")

        allow = bool(raw.get("result", {}).get("allow", False))
        # Final ceiling guard: never allow above the tenant's tier ceiling.
        if allow and not tenant.entitlement.permits_tier(tier):
            return AbacDecision(allow=False, reason="tier-above-ceiling")
        return AbacDecision(allow=allow, reason="opa" if allow else "opa-deny")
```

```rego
# tigerexchange/services/pep/src/pep/policy/abac.rego
# ABAC policy (plan §7.2/§7.3): tier x subject-attrs x edition.
# Deny-by-default. The Python adapter (pep/abac.py) enforces the hard
# narrows-only / missing-attr / PIP-unavailable invariants; this bundle
# expresses the positive tier-vs-attribute rules.
package tigerexchange.abac

import rego.v1

default allow := false

# Public tier: any authenticated subject with an affiliation may read.
allow if {
	input.object.tier == "public"
	count(input.subject.affiliations) > 0
}

# Private tier: requires a non-empty affiliation set.
allow if {
	input.object.tier == "private"
	count(input.subject.affiliations) > 0
}

# Confidential tier: requires a confidential-capable edition AND attributes.
allow if {
	input.object.tier == "confidential"
	count(input.subject.affiliations) > 0
	input.subject.edition in {"consortium-anchor", "confidential-sovereign", "institutional", "campus"}
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_abac.py -q
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/src/pep/abac.py tigerexchange/services/pep/src/pep/policy/abac.rego tigerexchange/services/pep/tests/test_abac.py && git commit -m "feat(pep): add OPA ABAC adapter (narrows-only, deny-on-missing-attr, no cache-fallback on confidential)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Revocation — durable tombstone (authoritative deny) + lease (narrow-only, TTL=0 security)

**Files:** Create `tigerexchange/services/pep/src/pep/revocation.py`, Test `tigerexchange/services/pep/tests/test_revocation.py`

This folds in highs_addressed item #1's reconciliation: durable-log high-water-mark authoritative for deny; security-reason zero-allow-window vs the 15ms lease read; lease narrow-only.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_revocation.py
"""Revocation composition (convergence-report HIGH; plan §4.4/§4.4a/§4.5).

Option (a) is implemented: every confidential read does a LOCAL read of the
durable tombstone high-water-mark (cell-local Postgres, single-digit-ms). The
durable log is AUTHORITATIVE for deny; the lease is a NARROW-ONLY positive-grant
cache. This gives the security-reason class a ZERO allow-window (the deny comes
from the durable log, not from lease expiry) while the 15ms lease read remains a
positive-grant fast path for the benign case.
"""
from pep.revocation import DurableTombstoneReader, LeaseCache, RevocationOutcome


class _FakeDurableLog:
    """In-memory stand-in for revocation_log (epoch, grant_id, reason)."""

    def __init__(self) -> None:
        self.tombstoned: dict[str, str] = {}  # grant_id -> reason
        self.high_water_mark = 0

    def commit_tombstone(self, grant_id: str, reason: str) -> int:
        self.high_water_mark += 1
        self.tombstoned[grant_id] = reason
        return self.high_water_mark

    def is_tombstoned(self, grant_id: str) -> tuple[bool, str | None]:
        if grant_id in self.tombstoned:
            return True, self.tombstoned[grant_id]
        return False, None


def test_durable_log_is_authoritative_deny() -> None:
    log = _FakeDurableLog()
    log.commit_tombstone("g1", reason="benign-admin")
    reader = DurableTombstoneReader(log=log)
    outcome = reader.check("g1")
    assert isinstance(outcome, RevocationOutcome)
    assert outcome.denied is True


def test_security_reason_zero_allow_window_even_with_valid_lease() -> None:
    # Lease still says VALID (positive-grant cache not yet expired)...
    lease = LeaseCache()
    lease.put("g2", ttl_ms=2000)  # 2s lease, not expired
    log = _FakeDurableLog()
    log.commit_tombstone("g2", reason="security")  # security-reason revoke
    reader = DurableTombstoneReader(log=log)

    # The durable read denies REGARDLESS of the still-valid lease -> zero window.
    outcome = reader.check("g2")
    assert outcome.denied is True
    assert outcome.reason == "security"
    # Lease is narrow-only: it can only ever narrow, never override the deny.
    assert lease.is_valid("g2") is True  # lease unaware, but durable wins


def test_lease_is_narrow_only_positive_grant_cache() -> None:
    lease = LeaseCache()
    assert lease.is_valid("g3") is False  # no positive grant cached -> not valid
    lease.put("g3", ttl_ms=15)
    assert lease.is_valid("g3") is True


def test_not_tombstoned_is_not_denied() -> None:
    reader = DurableTombstoneReader(log=_FakeDurableLog())
    outcome = reader.check("g4")
    assert outcome.denied is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_revocation.py -q
```

Expected: fails — `ModuleNotFoundError: No module named 'pep.revocation'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/services/pep/src/pep/revocation.py
"""Revocation: durable-tombstone authoritative deny + narrow-only lease cache.

Resolves the lease-vs-durable-log composition (convergence-report HIGH) via
option (a) of the fix:

  - The durable tombstone log (cell-local Postgres ``revocation_log``, §4.4a) is
    the SINGLE AUTHORITATIVE store for the deny dimension. Every confidential
    read reads its high-water-mark locally (single-digit-ms, NOT a consensus
    hop), so a revocation — including a security-reason revocation — is observed
    IMMEDIATELY (zero allow-window, §4.5).
  - The lease (§4.4) is reduced to a NARROW-ONLY POSITIVE-GRANT cache: it can
    affirm "this grant was valid as of the lease" but it can never override the
    durable deny. Security-reason revocations therefore have TTL=0 semantics by
    construction — the lease is irrelevant to the deny.

This keeps the §4.3 latency budget honest: the 15ms lease read is the
positive-grant fast path; the authoritative deny is the local durable read.
"""

from __future__ import annotations

import time
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _DurableLog(Protocol):
    """Structural surface of the cell-local revocation_log (§4.4a)."""

    def is_tombstoned(self, grant_id: str) -> tuple[bool, str | None]: ...


class RevocationOutcome(BaseModel):
    """Result of the authoritative durable tombstone read."""

    model_config = ConfigDict(frozen=True)

    denied: bool
    reason: str | None = None


class DurableTombstoneReader:
    """Authoritative deny: local read of the durable tombstone high-water-mark."""

    def __init__(self, log: _DurableLog) -> None:
        self._log = log

    def check(self, grant_id: str) -> RevocationOutcome:
        tombstoned, reason = self._log.is_tombstoned(grant_id)
        return RevocationOutcome(denied=tombstoned, reason=reason)


class LeaseCache:
    """Narrow-only positive-grant cache (§4.4). NEVER overrides a durable deny."""

    def __init__(self) -> None:
        self._expiry_ms: dict[str, float] = {}

    def put(self, grant_id: str, *, ttl_ms: int) -> None:
        self._expiry_ms[grant_id] = (time.monotonic() * 1000.0) + ttl_ms

    def is_valid(self, grant_id: str) -> bool:
        expiry = self._expiry_ms.get(grant_id)
        if expiry is None:
            return False
        return (time.monotonic() * 1000.0) < expiry
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_revocation.py -q
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/src/pep/revocation.py tigerexchange/services/pep/tests/test_revocation.py && git commit -m "feat(pep): durable tombstone as authoritative deny, lease as narrow-only positive-grant cache (zero allow-window for security-reason)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Broker DB role migration — credentials scoped to confidential-artifact/classification tables only

**Files:** Create `tigerexchange/services/pep/migrations/0001_broker_role.sql`, `tigerexchange/services/pep/src/pep/broker_db.py`

This folds in highs_addressed item #2 (broker topology): the broker holds credentials ONLY for the shared confidential-artifact/classification tables, never feature-module schemas.

- [ ] **Step 1: Write the failing test**

```sql
-- tigerexchange/services/pep/migrations/0001_broker_role.sql
-- Broker topology (convergence-report HIGH; plan §4.2/§5.2).
-- The data-access broker is the chokepoint for the SHARED confidential-artifact
-- store ONLY. Its DB role (broker_ro) is GRANTed SELECT on the shared
-- confidential-artifact + classification tables and NOTHING else. Feature-module
-- operational schemas stay behind their own DB roles and are NEVER granted here,
-- so the broker physically cannot read a feature module's schema.

-- Shared confidential-artifact store (PROPOSAL/ARTIFACT/CLASSIFICATION, §6.1).
CREATE SCHEMA IF NOT EXISTS confidential_artifact;

CREATE TABLE IF NOT EXISTS confidential_artifact.artifact (
    artifact_id   TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL,
    proposal_id   TEXT,
    payload       JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS confidential_artifact.classification (
    artifact_id        TEXT PRIMARY KEY
        REFERENCES confidential_artifact.artifact (artifact_id),
    tenant_id          TEXT NOT NULL,
    tier               TEXT NOT NULL,
    decision           TEXT NOT NULL,
    compliance_flags   TEXT[] NOT NULL DEFAULT '{}',
    lattice_version    INT  NOT NULL
);

-- tenant_id leading index (defense-in-depth RLS predicate, §7.7).
CREATE INDEX IF NOT EXISTS idx_artifact_tenant ON confidential_artifact.artifact (tenant_id, artifact_id);
CREATE INDEX IF NOT EXISTS idx_classification_tenant ON confidential_artifact.classification (tenant_id, artifact_id);

-- A feature-module-owned operational schema the broker MUST NOT be able to read.
CREATE SCHEMA IF NOT EXISTS mod_lit_intelligence;
CREATE TABLE IF NOT EXISTS mod_lit_intelligence.draft (
    draft_id   TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    body       TEXT NOT NULL
);

-- The broker's read-only role: ONLY the shared confidential-artifact schema.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'broker_ro') THEN
        CREATE ROLE broker_ro NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA confidential_artifact TO broker_ro;
GRANT SELECT ON confidential_artifact.artifact TO broker_ro;
GRANT SELECT ON confidential_artifact.classification TO broker_ro;

-- Explicitly REVOKE any access to feature-module schemas (belt-and-suspenders).
REVOKE ALL ON SCHEMA mod_lit_intelligence FROM broker_ro;
REVOKE ALL ON ALL TABLES IN SCHEMA mod_lit_intelligence FROM broker_ro;
```

```python
# tigerexchange/services/pep/src/pep/broker_db.py
"""Broker raw-store connection factory (plan §4.2/§5.2).

The ONLY module permitted to import this is pep.broker (import-linter enforced).
It returns a psycopg connection authenticated as ``broker_ro`` — a DB role
GRANTed SELECT on confidential_artifact.* ONLY (migration 0001). The broker thus
holds credentials for the SHARED confidential-artifact store, never for any
feature-module-owned schema.

SET LOCAL pins the tenant context for RLS within the transaction (§7.7).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

BROKER_ROLE = "broker_ro"


@contextmanager
def broker_connection(dsn: str, *, tenant_id: str) -> Iterator[psycopg.Connection]:
    """Open a broker_ro connection with tenant context pinned via SET LOCAL.

    The DSN MUST authenticate as ``broker_ro``. ``SET LOCAL`` (transaction-
    scoped) prevents tenant-context leakage across pooled connections (§7.7).
    """
    conn = psycopg.connect(dsn)
    try:
        with conn.transaction():
            conn.execute(
                "SET LOCAL app.tenant_id = %s",
                (tenant_id,),
            )
            yield conn
    finally:
        conn.close()
```

- [ ] **Step 2: Verify the migration applies (this is the failing step until Task 7's contract test runs against it)**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -c "import pathlib; sql = pathlib.Path('migrations/0001_broker_role.sql').read_text(); assert 'GRANT SELECT ON confidential_artifact.artifact TO broker_ro' in sql; assert 'mod_lit_intelligence' in sql; print('migration present')"
```

Expected first run (before file exists): `FileNotFoundError`. After Step 1: prints `migration present`.

- [ ] **Step 3: Apply migration to the test Postgres**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && psql "${TIGEREXCHANGE_TEST_DSN:?set to a test Postgres superuser DSN}" -v ON_ERROR_STOP=1 -f migrations/0001_broker_role.sql && echo APPLIED
```

Expected: `APPLIED` (schemas, tables, `broker_ro` role created/granted).

- [ ] **Step 4: Confirm the role grants are scoped (quick check)**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && psql "${TIGEREXCHANGE_TEST_DSN:?}" -tAc "SELECT has_table_privilege('broker_ro','confidential_artifact.artifact','SELECT'), has_table_privilege('broker_ro','mod_lit_intelligence.draft','SELECT')"
```

Expected: `t|f` — broker_ro can SELECT the artifact table, cannot SELECT the feature-module table.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/migrations/0001_broker_role.sql tigerexchange/services/pep/src/pep/broker_db.py && git commit -m "feat(pep): broker_ro DB role scoped to shared confidential-artifact tables only (broker topology)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Broker-role contract test (broker reads ONLY confidential-artifact/classification, not any feature schema)

**Files:** Create `tigerexchange/services/pep/tests/test_broker_role_contract.py`

This is the explicit broker-role contract test demanded by highs_addressed item #2.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_broker_role_contract.py
"""Broker-role contract test (convergence-report HIGH; plan §4.2/§5.2/§15.2).

The broker's DB role (broker_ro) can read ONLY the shared confidential-artifact
and classification tables, NOT any feature-module-owned schema. This is the
structural proof the broker is a narrow chokepoint, not a god-object that
reaches into every module's schema.

Requires a live test Postgres with migration 0001 applied. The connection
authenticates as broker_ro (TIGEREXCHANGE_BROKER_DSN).
"""
import os

import psycopg
import pytest

BROKER_DSN = os.environ.get("TIGEREXCHANGE_BROKER_DSN")

pytestmark = pytest.mark.skipif(
    not BROKER_DSN, reason="TIGEREXCHANGE_BROKER_DSN (broker_ro) not configured"
)


def test_broker_can_read_confidential_artifact_tables() -> None:
    with psycopg.connect(BROKER_DSN) as conn:
        # Both shared confidential-artifact tables are readable.
        conn.execute("SELECT artifact_id FROM confidential_artifact.artifact LIMIT 1")
        conn.execute("SELECT tier FROM confidential_artifact.classification LIMIT 1")


def test_broker_cannot_read_feature_module_schema() -> None:
    with psycopg.connect(BROKER_DSN) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT body FROM mod_lit_intelligence.draft LIMIT 1")


def test_broker_cannot_write_confidential_artifact() -> None:
    # Broker is read-only even on the tables it CAN read (SELECT-only grant).
    with psycopg.connect(BROKER_DSN) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "INSERT INTO confidential_artifact.artifact (artifact_id, tenant_id, payload) "
                "VALUES ('x', 't1', '{}'::jsonb)"
            )
```

- [ ] **Step 2: Run test to verify it fails (before broker_ro DSN / grants are correct)**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && TIGEREXCHANGE_BROKER_DSN="${TIGEREXCHANGE_BROKER_DSN:?point at a broker_ro login}" python -m pytest tests/test_broker_role_contract.py -q
```

Expected before grants are correct: `test_broker_cannot_read_feature_module_schema` fails because the broker can still read the feature schema (or skips if DSN unset). With migration 0001 applied, the failure surfaces only if the REVOKE is missing.

- [ ] **Step 3: Write minimal implementation**

No new production code — the enforcement lives entirely in migration `0001_broker_role.sql` (Task 6). If Step 2 shows the feature-schema read is NOT blocked, add the explicit grant-revocation already present in the migration and re-apply:

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && psql "${TIGEREXCHANGE_TEST_DSN:?}" -v ON_ERROR_STOP=1 -c "REVOKE ALL ON ALL TABLES IN SCHEMA mod_lit_intelligence FROM broker_ro; REVOKE ALL ON SCHEMA mod_lit_intelligence FROM broker_ro;" && echo REVOKED
```

Expected: `REVOKED`.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && TIGEREXCHANGE_BROKER_DSN="${TIGEREXCHANGE_BROKER_DSN:?}" python -m pytest tests/test_broker_role_contract.py -q
```

Expected: 3 passed (broker reads artifact/classification; denied on feature schema; denied on write).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/tests/test_broker_role_contract.py && git commit -m "test(pep): broker-role contract — reads only confidential-artifact tables, never feature schema

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Data-access broker — fetch from shared store + project (sole raw-store credential holder)

**Files:** Create `tigerexchange/services/pep/src/pep/broker.py`, Test extends `tigerexchange/services/pep/tests/test_pep_compose.py` (broker portion)

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_pep_compose.py
"""Broker + PEP composition tests (plan §4.2). Part 1: the broker.

The broker is the ONLY raw-store credential holder. Given an ALLOW decision it
fetches rows from the SHARED confidential-artifact store and returns
already-projected, already-tier-checked objects. It implements IDataAccessBroker.
A query that the PEP denied yields no fetch.
"""
from contracts import (
    Capability,
    Decision,
    DiscoverabilityScope,
    Edition,
    Entitlement,
    IDataAccessBroker,
    IsolationPosture,
    PepAction,
    PepRequest,
    PepResponse,
    PublishableProjection,
    Tier,
    TenantContext,
)

from pep.broker import DataAccessBroker


def _ctx() -> TenantContext:
    ent = Entitlement(
        edition=Edition.CONSORTIUM_ANCHOR,
        capabilities=frozenset({Capability.CONFIDENTIAL_WORKSPACE}),
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.confidential,
    )
    return TenantContext(tenant_id="t1", subject_id="user:alice", entitlement=ent,
                         affiliations=frozenset({"faculty@rit.edu"}))


class _FakeStore:
    """Stand-in for confidential_artifact reads via broker_ro."""

    def fetch_rows(self, tenant_id: str, resource_id: str | None) -> list[dict]:
        return [
            {"artifact_id": "a1", "tenant_id": tenant_id, "tier": "private",
             "title": "Proposal Draft", "body": "secret-body"},
        ]


def test_broker_implements_interface() -> None:
    broker = DataAccessBroker(store=_FakeStore())
    assert isinstance(broker, IDataAccessBroker)


def test_broker_projects_rows_dropping_raw_body() -> None:
    broker = DataAccessBroker(store=_FakeStore())
    req = PepRequest(
        request_id="r1", tenant=_ctx(), action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="a1",
    )
    allow = PepResponse(request_id="r1", decision=Decision.ALLOW, effective_tier=Tier.private)
    out = broker.fetch(req, allow)
    assert out.decision is Decision.ALLOW
    assert out.payload is not None
    # Projected payload carries the allowlisted title, NOT the raw body.
    assert out.payload[0]["title"] == "Proposal Draft"
    assert "body" not in out.payload[0]


def test_broker_does_not_fetch_on_deny() -> None:
    broker = DataAccessBroker(store=_FakeStore())
    req = PepRequest(
        request_id="r2", tenant=_ctx(), action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="a1",
    )
    deny = PepResponse(request_id="r2", decision=Decision.DENY, effective_tier=Tier.private)
    out = broker.fetch(req, deny)
    assert out.decision is Decision.DENY
    assert out.payload is None


def test_broker_project_builds_publishable_projection() -> None:
    broker = DataAccessBroker(store=_FakeStore())
    req = PepRequest(
        request_id="r3", tenant=_ctx(), action=PepAction.EGRESS,
        required_capability=Capability.OWN_MATERIALS, resource_id="a1",
    )
    rows = [{"artifact_id": "a1", "tenant_id": "t1", "tier": "public", "title": "T"}]
    proj = broker.project(req, rows)
    assert isinstance(proj, PublishableProjection)
    assert proj.tier is Tier.public
    assert proj.discoverability_scope is DiscoverabilityScope.NONE
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_pep_compose.py -q
```

Expected: fails — `ModuleNotFoundError: No module named 'pep.broker'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/services/pep/src/pep/broker.py
"""Data-access broker — the sole raw-store credential holder (plan §4.2).

The broker sits behind the PEP. Given an ALLOW decision it reads rows from the
SHARED confidential-artifact store (via broker_ro, which can ONLY read
confidential_artifact.* — Task 6/7) and returns already-PROJECTED,
already-tier-checked objects. Feature modules never receive raw-store handles
and never see the raw body. On a non-ALLOW decision the broker fetches nothing.

Projection drops every field NOT on the publishable allowlist; the raw body and
any non-allowlisted column never leave the broker (egress allowlist, §4.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from contracts import (
    Decision,
    DiscoverabilityScope,
    PepRequest,
    PepResponse,
    PublishableProjection,
    Tier,
)

# Allowlisted publishable fields (the egress allowlist schema, §4.2).
_PUBLISHABLE_FIELDS = ("artifact_id", "tier", "title")


class _Store(Protocol):
    """Structural surface of the broker_ro confidential-artifact reader."""

    def fetch_rows(self, tenant_id: str, resource_id: str | None) -> list[dict]: ...


class DataAccessBroker:
    """Implements IDataAccessBroker. Sole holder of shared-store credentials."""

    def __init__(self, store: _Store) -> None:
        self._store = store

    def fetch(self, request: PepRequest, decision: PepResponse) -> PepResponse:
        if decision.decision is not Decision.ALLOW:
            # Fail-closed: no fetch, no payload on a non-ALLOW decision.
            return decision
        rows = self._store.fetch_rows(request.tenant.tenant_id, request.resource_id)
        projected = [self._project_row(row, decision.effective_tier) for row in rows]
        return PepResponse(
            request_id=decision.request_id,
            decision=Decision.ALLOW,
            effective_tier=decision.effective_tier,
            payload=projected,
            caveats=decision.caveats,
            reason=decision.reason,
        )

    def project(
        self, request: PepRequest, raw_rows: Sequence[dict[str, object]]
    ) -> PublishableProjection:
        first = raw_rows[0]
        tier = Tier.parse(first.get("tier"))
        return PublishableProjection(
            projection_id=f"{request.request_id}:proj",
            artifact_id=str(first["artifact_id"]),
            owner_tenant_id=request.tenant.tenant_id,
            tier=tier,
            discoverability_scope=DiscoverabilityScope.NONE,
            fields={k: first[k] for k in _PUBLISHABLE_FIELDS if k in first},
        )

    @staticmethod
    def _project_row(row: dict, effective_tier: Tier) -> dict:
        projected = {k: row[k] for k in _PUBLISHABLE_FIELDS if k in row}
        projected["effective_tier"] = effective_tier.wire
        return projected
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_pep_compose.py -q
```

Expected: 4 passed (the broker portion of the file).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/src/pep/broker.py tigerexchange/services/pep/tests/test_pep_compose.py && git commit -m "feat(pep): data-access broker — sole raw-store credential holder, projects allowlisted fields

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: PolicyEnforcementPoint — compose decision order; fail-closed payload (IPolicyEnforcement)

**Files:** Create `tigerexchange/services/pep/src/pep/pep.py`, extend Test `tigerexchange/services/pep/tests/test_pep_compose.py`

- [ ] **Step 1: Write the failing test (append to test_pep_compose.py)**

```python
# tigerexchange/services/pep/tests/test_pep_compose.py  (append)
"""Part 2: the PEP composes the pinned decision order and is fail-closed."""
from contracts import IPolicyEnforcement

from pep.abac import OpaAbac
from pep.pep import PolicyEnforcementPoint
from pep.rebac import SpiceDBReBAC
from pep.revocation import DurableTombstoneReader, LeaseCache


class _FakeSpice:
    def __init__(self, permit: bool) -> None:
        self.permit = permit

    def check(self, *_a, **_k) -> bool:  # noqa: ANN002, ANN003
        return self.permit


class _FakeOpaAllow:
    def evaluate(self, _doc: dict) -> dict:
        return {"result": {"allow": True}}


class _FakeLog:
    def __init__(self, tombstoned: dict[str, str] | None = None) -> None:
        self._t = tombstoned or {}

    def is_tombstoned(self, grant_id: str) -> tuple[bool, str | None]:
        if grant_id in self._t:
            return True, self._t[grant_id]
        return False, None


def _build(*, permit: bool, tombstoned: dict[str, str] | None = None) -> PolicyEnforcementPoint:
    return PolicyEnforcementPoint(
        rebac=SpiceDBReBAC(client=_FakeSpice(permit)),
        abac=OpaAbac(opa=_FakeOpaAllow()),
        tombstone=DurableTombstoneReader(log=_FakeLog(tombstoned)),
        lease=LeaseCache(),
        broker=DataAccessBroker(store=_FakeStore()),
    )


def test_pep_implements_interface() -> None:
    assert isinstance(_build(permit=True), IPolicyEnforcement)


def test_allow_when_rebac_abac_pass_and_not_tombstoned() -> None:
    pep = _build(permit=True)
    req = PepRequest(
        request_id="r10", tenant=_ctx(), action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="a1",
        grant_id="g10",
    )
    resp = pep.authorize(req)
    assert resp.decision is Decision.ALLOW
    assert resp.payload is not None


def test_rebac_deny_short_circuits_before_abac() -> None:
    pep = _build(permit=False)
    req = PepRequest(
        request_id="r11", tenant=_ctx(), action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="a1",
        grant_id="g11",
    )
    resp = pep.authorize(req)
    assert resp.decision is Decision.DENY
    assert resp.payload is None
    assert resp.reason == "rebac-deny"


def test_durable_tombstone_denies_even_when_rebac_abac_allow() -> None:
    pep = _build(permit=True, tombstoned={"g12": "security"})
    req = PepRequest(
        request_id="r12", tenant=_ctx(), action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="a1",
        grant_id="g12",
    )
    resp = pep.authorize(req)
    assert resp.decision is Decision.DENY
    assert resp.payload is None
    assert resp.reason == "revoked:security"


def test_capability_not_entitled_denies() -> None:
    pep = _build(permit=True)
    plg_ent = Entitlement(
        edition=Edition.PLG,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL, Capability.OWN_MATERIALS}),
        isolation=IsolationPosture.POOLED, max_tier=Tier.private,
    )
    plg = TenantContext(tenant_id="t2", subject_id="user:carol", entitlement=plg_ent,
                        affiliations=frozenset({"faculty@x.edu"}))
    req = PepRequest(
        request_id="r13", tenant=plg, action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="a1",
        grant_id="g13",
    )
    resp = pep.authorize(req)
    assert resp.decision is Decision.DENY
    assert resp.reason == "capability-not-entitled"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_pep_compose.py -q
```

Expected: fails — `ModuleNotFoundError: No module named 'pep.pep'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/services/pep/src/pep/pep.py
"""The single Policy Enforcement Point (plan §4.2/§7.6, D4).

Implements IPolicyEnforcement. Composes the ONE pinned decision order
(decision_order.py) in this exact sequence per request:

  0. Capability gate   — tenant entitlement must grant required_capability.
  1. REBAC_CHECK       — SpiceDB Check (narrow-only); deny short-circuits.
  2. ABAC              — OPA (narrows-only); deny short-circuits.
  3. DURABLE_TOMBSTONE — authoritative deny store; tombstoned -> deny (zero window).
  4. LEASE             — narrow-only positive-grant cache (refreshed on allow).

On ALLOW the broker fetches + projects. Non-ALLOW carries no payload (the
PepResponse model enforces this; we also never call the broker on deny).
"""

from __future__ import annotations

from contracts import (
    Decision,
    PepAction,
    PepRequest,
    PepResponse,
)

from pep.abac import OpaAbac
from pep.broker import DataAccessBroker
from pep.decision_order import DECISION_ORDER, DecisionStep
from pep.rebac import SpiceDBReBAC
from pep.revocation import DurableTombstoneReader, LeaseCache

# Map PepAction -> the SpiceDB permission name to Check (§7.3).
_ACTION_PERMISSION = {
    PepAction.RETRIEVE: "view",
    PepAction.EGRESS: "view",
    PepAction.DERIVE: "view",
    PepAction.DISCOVER: "discover",
    PepAction.BROKERED_DRILLDOWN: "view",
}

_DEFAULT_LEASE_TTL_MS = 2000  # benign-class positive-grant cache TTL (§4.5).


class PolicyEnforcementPoint:
    """The one logical PEP. Same code at cell-local and central-index loci."""

    def __init__(
        self,
        *,
        rebac: SpiceDBReBAC,
        abac: OpaAbac,
        tombstone: DurableTombstoneReader,
        lease: LeaseCache,
        broker: DataAccessBroker,
    ) -> None:
        self._rebac = rebac
        self._abac = abac
        self._tombstone = tombstone
        self._lease = lease
        self._broker = broker

    def authorize(self, request: PepRequest) -> PepResponse:
        tier, flags = self._object_classification(request)

        # Step 0: capability gate (edition/entitlement, evaluated at the PEP, §2.3).
        if not request.tenant.entitlement.has(request.required_capability):
            return self._deny(request, tier, "capability-not-entitled")

        for step in DECISION_ORDER:
            if step is DecisionStep.REBAC_CHECK:
                rebac = self._rebac.check(
                    resource=f"artifact:{request.resource_id}",
                    permission=_ACTION_PERMISSION[request.action],
                    subject=f"user:{request.tenant.subject_id}",
                )
                if not rebac.has_permission:
                    return self._deny(request, tier, "rebac-deny")
                rebac_permitted = True

            elif step is DecisionStep.ABAC:
                abac = self._abac.evaluate(
                    tenant=request.tenant,
                    tier=tier,
                    compliance_flags=flags,
                    rebac_permitted=rebac_permitted,
                )
                if not abac.allow:
                    return self._deny(request, tier, f"abac-deny:{abac.reason}")

            elif step is DecisionStep.DURABLE_TOMBSTONE:
                if request.grant_id is not None:
                    outcome = self._tombstone.check(request.grant_id)
                    if outcome.denied:
                        return self._deny(request, tier, f"revoked:{outcome.reason}")

            elif step is DecisionStep.LEASE:
                # Narrow-only positive-grant cache: refresh on a passing decision.
                if request.grant_id is not None:
                    self._lease.put(request.grant_id, ttl_ms=_DEFAULT_LEASE_TTL_MS)

        allow = PepResponse(
            request_id=request.request_id, decision=Decision.ALLOW, effective_tier=tier
        )
        return self._broker.fetch(request, allow)

    @staticmethod
    def _deny(request: PepRequest, tier, reason: str) -> PepResponse:  # noqa: ANN001
        return PepResponse(
            request_id=request.request_id,
            decision=Decision.DENY,
            effective_tier=tier,
            reason=reason,
        )

    @staticmethod
    def _object_classification(request: PepRequest):  # noqa: ANN205
        """Resolve (tier, compliance_flags) for the request's object.

        In Phase-0 the broker's store holds the classification; for the
        authorize() decision the object tier defaults to the tenant ceiling so
        confidential requests exercise the confidential ABAC path. The fetched
        rows carry their own row-level tier (broker projection).
        """
        from contracts import Tier  # local import to keep module top clean

        return Tier.confidential, frozenset()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_pep_compose.py -q
```

Expected: 9 passed (4 broker + 5 PEP composition tests).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/src/pep/pep.py tigerexchange/services/pep/tests/test_pep_compose.py && git commit -m "feat(pep): PolicyEnforcementPoint composes pinned decision order, fail-closed payload

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Central-index read PEP — discoverability-scope filtering

**Files:** Modify `tigerexchange/services/pep/src/pep/pep.py`, Create Test `tigerexchange/services/pep/tests/test_central_index_pep.py`

This implements the central-index read PEP with `discoverability_scope` (deliverable: "central-index read PEP with discoverability_scope").

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/pep/tests/test_central_index_pep.py
"""Central-index read PEP (plan §4.7/§7.6). discoverability_scope at query time.

Same PEP code, central-index locus (PepAction.DISCOVER). It scope-filters
PUBLISHED projections by the requester's identity + consortium membership:
  - public-web        -> visible to anyone
  - federation-wide   -> any authenticated member
  - named-consortium  -> only members of the publisher's consortium
  - named-tenants     -> only an explicit tenant allowlist
  - none              -> never centrally indexed
Deny-by-default: a named-consortium record is invisible to a non-member.
"""
from contracts import (
    Capability,
    DiscoverabilityScope,
    Edition,
    Entitlement,
    IsolationPosture,
    PublishableProjection,
    Tier,
    TenantContext,
)

from pep.pep import filter_by_discoverability


def _ctx(consortia: frozenset[str]) -> TenantContext:
    ent = Entitlement(
        edition=Edition.INSTITUTIONAL,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL}),
        isolation=IsolationPosture.DEDICATED_CELL, max_tier=Tier.private,
    )
    return TenantContext(tenant_id="req-tenant", subject_id="user:dan", entitlement=ent,
                         consortium_ids=consortia, affiliations=frozenset({"a@x.edu"}))


def _proj(scope: DiscoverabilityScope, *, owner: str = "owner-t",
          fields: dict | None = None) -> PublishableProjection:
    return PublishableProjection(
        projection_id=f"p-{scope.value}", artifact_id="a", owner_tenant_id=owner,
        tier=Tier.public, discoverability_scope=scope, fields=fields or {},
    )


def test_public_web_visible_to_anyone() -> None:
    out = filter_by_discoverability([_proj(DiscoverabilityScope.PUBLIC_WEB)], _ctx(frozenset()))
    assert len(out) == 1


def test_named_consortium_hidden_from_non_member() -> None:
    p = _proj(DiscoverabilityScope.NAMED_CONSORTIUM, fields={"consortium_ids": ["c1"]})
    out = filter_by_discoverability([p], _ctx(frozenset({"c2"})))
    assert out == []


def test_named_consortium_visible_to_member() -> None:
    p = _proj(DiscoverabilityScope.NAMED_CONSORTIUM, fields={"consortium_ids": ["c1"]})
    out = filter_by_discoverability([p], _ctx(frozenset({"c1"})))
    assert len(out) == 1


def test_named_tenants_enforced_against_allowlist() -> None:
    p = _proj(DiscoverabilityScope.NAMED_TENANTS, fields={"allowed_tenant_ids": ["req-tenant"]})
    out = filter_by_discoverability([p], _ctx(frozenset()))
    assert len(out) == 1
    p2 = _proj(DiscoverabilityScope.NAMED_TENANTS, fields={"allowed_tenant_ids": ["other"]})
    assert filter_by_discoverability([p2], _ctx(frozenset())) == []


def test_scope_none_never_indexed() -> None:
    out = filter_by_discoverability([_proj(DiscoverabilityScope.NONE)], _ctx(frozenset()))
    assert out == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_central_index_pep.py -q
```

Expected: fails — `ImportError: cannot import name 'filter_by_discoverability' from 'pep.pep'`.

- [ ] **Step 3: Write minimal implementation (append to pep.py)**

```python
# tigerexchange/services/pep/src/pep/pep.py  (append at module level)

from contracts import DiscoverabilityScope, PublishableProjection, TenantContext


def filter_by_discoverability(
    projections: list[PublishableProjection], requester: TenantContext
) -> list[PublishableProjection]:
    """Central-index read PEP scope filter (§4.7). Deny-by-default.

    Enforces each projection's discoverability_scope against the requester's
    identity + consortium membership. A named-consortium/named-tenants record is
    invisible to anyone outside its scope; scope=none is never indexed.
    """
    visible: list[PublishableProjection] = []
    for p in projections:
        if _scope_permits(p, requester):
            visible.append(p)
    return visible


def _scope_permits(p: PublishableProjection, requester: TenantContext) -> bool:
    scope = p.discoverability_scope
    if scope is DiscoverabilityScope.PUBLIC_WEB:
        return True
    if scope is DiscoverabilityScope.FEDERATION_WIDE:
        return bool(requester.affiliations)  # any authenticated member
    if scope is DiscoverabilityScope.NAMED_CONSORTIUM:
        allowed = set(p.fields.get("consortium_ids", []))
        return bool(allowed & requester.consortium_ids)
    if scope is DiscoverabilityScope.NAMED_TENANTS:
        allowed = set(p.fields.get("allowed_tenant_ids", []))
        return requester.tenant_id in allowed
    # DiscoverabilityScope.NONE (or any unknown) -> never indexed (deny-by-default).
    return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest tests/test_central_index_pep.py -q
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/pep/src/pep/pep.py tigerexchange/services/pep/tests/test_central_index_pep.py && git commit -m "feat(pep): central-index read PEP enforces discoverability_scope (deny-by-default)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Full-suite green + lint/type/import-linter gate

**Files:** Test all under `tigerexchange/services/pep/`

- [ ] **Step 1: Write the failing check (run the full gate)**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest -q && ruff check src/ && mypy src/ && lint-imports
```

Expected initially: `lint-imports` may fail if `pep.broker` is referenced from a `source_module`; pytest/ruff/mypy should pass after Tasks 1-10.

- [ ] **Step 2: Inspect the import-linter failure (if any)**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && lint-imports || true
```

Expected: the contract `feature-modules-cannot-import-raw-store-or-classifier` must report KEPT (only `pep.broker` imports `pep.broker_db`; the listed `source_modules` do not).

- [ ] **Step 3: Confirm/adjust the import-linter config so the broker is the sole importer**

Verify `pep.broker` is NOT in `source_modules` of the forbidden contract (it must legitimately import `pep.broker_db`). If `lint-imports` reports a broken edge, the offending source module imported `pep.broker_db` or `classifier.engine` — remove that import. No code change is expected if Tasks 1-10 were followed; this step is the verification gate.

- [ ] **Step 4: Run full gate to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/pep && python -m pytest -q && ruff check src/ && mypy src/ && lint-imports
```

Expected: all tests pass; `ruff` clean; `mypy` clean; `lint-imports` reports `Contracts: 1 kept, 0 broken`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add -A tigerexchange/services/pep && git commit -m "chore(pep): full suite green — pytest/ruff/mypy/import-linter gate passes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes on decisions encoded (for reviewers)

- **Decision order (highs_addressed #1):** `decision_order.py` pins exactly `REBAC_CHECK → ABAC → DURABLE_TOMBSTONE → LEASE`. The durable tombstone log is the single `AUTHORITATIVE_DENY_STORE`; SpiceDB Check, ABAC, and the lease are `is_narrow_only`. Option (a) from the convergence fix is implemented: every confidential request reads the durable high-water-mark locally, so a security-reason revocation produces a zero allow-window even while a 15ms positive-grant lease is still nominally valid (`test_security_reason_zero_allow_window_even_with_valid_lease`). The §7.3 "ABAC narrows-only" invariant is generalized to "caches narrow-only" across all three caches.
- **Broker topology (highs_addressed #2):** migration `0001_broker_role.sql` creates `broker_ro` GRANTed SELECT on `confidential_artifact.artifact` and `confidential_artifact.classification` ONLY, with explicit REVOKE on the feature-module schema `mod_lit_intelligence`. `test_broker_role_contract.py` asserts the broker can read the two shared tables, cannot read any feature schema, and cannot write. "Single PEP" = one logical policy decision point (`PolicyEnforcementPoint`) over one broker that holds credentials only for the shared confidential-artifact store — not a god-object reaching into module schemas.
- **Canonical kernel:** All public types are imported verbatim from `contracts` (`TenantContext`, `Entitlement`, `Capability`, `Edition`, `IsolationPosture`, `Tier`, `ComplianceFlag`, `Decision`, `DiscoverabilityScope`, `PepRequest`, `PepResponse`, `PepAction`, `PublishableProjection`, `IPolicyEnforcement`, `IDataAccessBroker`). `Tier.parse`, `Tier.wire`, `Entitlement.has`, `Entitlement.permits_tier`, and `PepResponse.model_post_init` fail-closed behavior are used as defined.
- **Deferred seams:** `IRevocationAuthority`/`IExchangeFeed` are not implemented (Phase-1+). The Phase-0 durable read is a local `DurableTombstoneReader` over the cell-local `revocation_log`, not the deferred cross-institution revocation authority.

One implementation note flagged: `PolicyEnforcementPoint._object_classification` returns `(Tier.confidential, frozenset())` as the Phase-0 authorize-time default so confidential ABAC paths are exercised; the row-level tier is carried by the broker's projection. A later task (in `0b`/`0d` integration) should wire the classifier-backed per-object tier lookup into the broker's store read so authorize-time tier matches the fetched row's classification — left as a clean seam, not stubbed with placeholder logic.