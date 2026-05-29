I have everything I need. Writing the complete plan now.

# Foundation: Monorepo, Contracts/Kernel, FORCE-RLS Tenant Isolation, FastAPI Skeleton, CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Stand up the walking skeleton every later TigerExchange plan extends — a Python 3.12 monorepo with the importable, versioned `contracts` kernel package, Postgres FORCE-RLS tenant isolation driven by `SET LOCAL` TenantContext, a runnable FastAPI service with a health endpoint, CI (pytest/ruff/mypy + import-linter + kernel fitness check) — plus the Week-1 GTM/cost validation gates as committed non-code deliverables.

**Architecture:** A `uv`/PEP-621 monorepo with one near-frozen `packages/contracts` kernel (zero feature deps, no persistence, versioned per the §5.6/§5.6b discipline extended to interfaces) and one `services/api` FastAPI app. The app derives a `TenantContext` per request and pins it to a transaction-scoped Postgres connection via `SET LOCAL app.tenant_id`; every tenant-scoped table carries `FORCE ROW LEVEL SECURITY` with `RESTRICTIVE` + `WITH CHECK` policies and a `tenant_id`-leading index. CI enforces the kernel fitness function (import-linter forbidden-import contracts + a fan-in/size check) and a kernel-interface backward+forward compatibility check analogous to the projection/event schema-registry discipline.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async, asyncpg), Postgres 16, pytest + testcontainers, ruff, mypy, import-linter, griffe (kernel API-diff compat check), uv (workspace).

**Depends on:** none

---

## File Structure

| File | Responsibility |
|---|---|
| `tigerexchange/pyproject.toml` | Root uv workspace + dev tool config (ruff, mypy, pytest markers). |
| `tigerexchange/.python-version` | Pins Python 3.12. |
| `tigerexchange/README.md` | One-paragraph repo map + boot/test commands. |
| `tigerexchange/packages/contracts/pyproject.toml` | Kernel package metadata + import-linter forbidden-import fitness contract. |
| `tigerexchange/packages/contracts/src/contracts/__init__.py` | Single import surface + `KERNEL_API_VERSION`. |
| `tigerexchange/packages/contracts/src/contracts/lattice.py` | `Tier`, MAX-rule join, `ComplianceFlag`, `LATTICE_VERSION` (K1). |
| `tigerexchange/packages/contracts/src/contracts/tenancy.py` | `TenantContext`, `Edition`, `Entitlement`, `Capability`, `IsolationPosture`. |
| `tigerexchange/packages/contracts/src/contracts/classification.py` | `Decision`, `DiscoverabilityScope`, `ClassificationResult`, `Caveats`. |
| `tigerexchange/packages/contracts/src/contracts/projection.py` | `PublishableProjection`, `PROJECTION_SCHEMA_VERSION` (K2). |
| `tigerexchange/packages/contracts/src/contracts/pep.py` | `PepAction`, `PepRequest`, `PepResponse`. |
| `tigerexchange/packages/contracts/src/contracts/audit.py` | `AuditEvent`, `AuditEventType`. |
| `tigerexchange/packages/contracts/src/contracts/interfaces.py` | All K3 interface Protocols + `INTERFACE_LOCUS` intra-cell/cross-node table. |
| `tigerexchange/packages/contracts/tests/test_lattice.py` | Lattice ordering / MAX-rule / fail-closed-parse tests. |
| `tigerexchange/packages/contracts/tests/test_classification.py` | Quarantine fail-closed + `is_retrievable` tests. |
| `tigerexchange/packages/contracts/tests/test_projection.py` | D6 confidential-rejection + version-stamp tests. |
| `tigerexchange/packages/contracts/tests/test_pep.py` | Fail-closed `PepResponse` payload invariant test. |
| `tigerexchange/packages/contracts/tests/test_kernel_fitness.py` | Kernel zero-persistence-dep + fan-in/size fitness check. |
| `tigerexchange/packages/contracts/api/contracts_api.txt` | Frozen kernel public-API surface for the CI compat check (the baseline). |
| `tigerexchange/packages/contracts/tests/test_kernel_compat.py` | Kernel-interface backward+forward compat check (griffe API-diff vs baseline). |
| `tigerexchange/services/api/pyproject.toml` | API service metadata; depends on `contracts` + SQLAlchemy/FastAPI. |
| `tigerexchange/services/api/src/api/config.py` | `Settings` (Pydantic-settings): DB DSN, env. |
| `tigerexchange/services/api/src/api/db.py` | Async engine + transaction-scoped `tenant_session` that issues `SET LOCAL`. |
| `tigerexchange/services/api/src/api/tenant_context.py` | Request->TenantContext derivation (header/JWT-stub) for Phase-0. |
| `tigerexchange/services/api/src/api/app.py` | FastAPI app factory, `/health`, tenant-context dependency, demo own-materials route. |
| `tigerexchange/services/api/src/api/dependencies.py` | **0a-OWNED** DI factory module: every `get_*` factory the feature modules (0i/0k/etc.) import from `api.dependencies` (get_pep, get_model_router, get_lit_retrieval, get_draft_store, get_discovery, get_funding, get_audit_sink, get_classifier, ...). Phase-0 ships fail-closed not-wired stubs; feature plans override via FastAPI `dependency_overrides`. |
| `tigerexchange/services/api/tests/test_dependencies.py` | Asserts every required `get_*` DI factory exists + is importable from `api.dependencies`. |
| `tigerexchange/services/api/migrations/001_tenant_rls.sql` | `own_materials` table + FORCE RLS + RESTRICTIVE/WITH CHECK policies + tenant_id-leading index. |
| `tigerexchange/services/api/migrations/002_forbidden_bypass_check.sql` | (test fixture) SECURITY DEFINER / matview the lint must flag. |
| `tigerexchange/services/api/tests/test_health.py` | App boots + `/health` returns 200. |
| `tigerexchange/services/api/tests/test_rls_isolation.py` | Cross-tenant-read-denied (BOLA) test on a live Postgres container. |
| `tigerexchange/services/api/tests/test_rls_lint.py` | Lint that flags SECURITY DEFINER / matview over tenant-scoped tables. |
| `tigerexchange/services/api/scripts/check_rls_bypass.py` | The CI lint script scanning migrations for forbidden bypasses. |
| `tigerexchange/.github/workflows/ci.yml` | CI: ruff, mypy, import-linter, pytest, kernel fitness, kernel compat, RLS lint. |
| `tigerexchange/docs/gates/week1-validation.md` | Gate A/B/Q17 sign-off doc + line-(a) ACV/burn stress test + PLG-positioning resolution. |

---

## Tasks

### Task 1: Monorepo scaffold + Python 3.12 + dev tooling

**Files:** Create `tigerexchange/pyproject.toml`, `tigerexchange/.python-version`, `tigerexchange/README.md`, `tigerexchange/packages/contracts/src/contracts/__init__.py` (empty stub for now), `tigerexchange/tests/test_repo_layout.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/test_repo_layout.py
"""Guards the monorepo skeleton: workspace members exist and Python is pinned to 3.12."""
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_python_is_312() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_workspace_declares_members() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    members = data["tool"]["uv"]["workspace"]["members"]
    assert "packages/contracts" in members
    assert "services/api" in members


def test_python_version_pinned() -> None:
    assert (ROOT / ".python-version").read_text().strip() == "3.12"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest tests/test_repo_layout.py -q
```
Expected: `FileNotFoundError` / collection error — `tigerexchange/pyproject.toml` and `.python-version` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/.python-version`:
```
3.12
```

`tigerexchange/pyproject.toml`:
```toml
[project]
name = "tigerexchange"
version = "0.0.0"
description = "TigerExchange monorepo root (workspace aggregator)."
requires-python = ">=3.12,<3.13"

[tool.uv.workspace]
members = ["packages/contracts", "services/api"]

[tool.uv.sources]
tigerexchange-contracts = { workspace = true }

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "testcontainers[postgres]>=4.8",
    "ruff>=0.6",
    "mypy>=1.11",
    "import-linter>=2.1",
    "griffe>=1.3",
]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["packages/contracts/src", "services/api/src"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = ["packages/contracts/src", "services/api/src"]
explicit_package_bases = true

[tool.pytest.ini_options]
markers = [
    "unit: pure in-process tests, no external services",
    "integration: requires a Postgres container",
]
asyncio_mode = "auto"
testpaths = ["tests", "packages/contracts/tests", "services/api/tests"]
```

`tigerexchange/README.md`:
```markdown
# TigerExchange (Phase-0 walking skeleton)

uv workspace monorepo.

- `packages/contracts` — near-frozen kernel: TierLattice, TenantContext, PublishableProjection, PEP/audit types, ~15 interface Protocols. Zero feature deps, no persistence.
- `services/api` — FastAPI service; boots, exposes `/health`, pins per-request TenantContext via `SET LOCAL` on a transaction-scoped Postgres connection, FORCE-RLS tenant isolation.

## Boot & test
    uv sync
    uv run pytest -m unit          # fast, no Postgres
    uv run pytest -m integration   # needs Docker (testcontainers Postgres)
    uv run ruff check . && uv run mypy . && uv run lint-imports
```

`tigerexchange/packages/contracts/src/contracts/__init__.py`:
```python
"""TigerExchange canonical kernel (placeholder; populated in Tasks 2-9)."""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest tests/test_repo_layout.py -q
```
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/ && git commit -m "chore(tigerexchange): scaffold uv monorepo pinned to py3.12

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Kernel K1 — TierLattice (`lattice.py`)

**Files:** Create `tigerexchange/packages/contracts/pyproject.toml`, `tigerexchange/packages/contracts/src/contracts/lattice.py`, `tigerexchange/packages/contracts/tests/test_lattice.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/contracts/tests/test_lattice.py
"""TierLattice (plan §5.6): total order, MAX-rule join, fail-closed parse, sticky flags."""
import pytest

from contracts.lattice import (
    LATTICE_VERSION,
    ComplianceFlag,
    Tier,
    compliance_union,
    tier_join,
    tier_join_all,
)


def test_total_ordering() -> None:
    assert Tier.public < Tier.private < Tier.confidential


def test_join_is_max() -> None:
    assert tier_join(Tier.public, Tier.confidential) is Tier.confidential
    assert tier_join(Tier.private, Tier.public) is Tier.private


def test_join_all_empty_fails_closed() -> None:
    assert tier_join_all([]) is Tier.confidential


def test_join_all_takes_max() -> None:
    assert tier_join_all([Tier.public, Tier.private, Tier.public]) is Tier.private


@pytest.mark.parametrize("bad", [None, "", "PUBLICish", 42, object()])
def test_parse_unknown_is_most_restrictive(bad: object) -> None:
    assert Tier.parse(bad) is Tier.confidential


def test_parse_known_wire_form() -> None:
    assert Tier.parse("private") is Tier.private
    assert Tier.private.wire == "private"


def test_compliance_union_is_sticky() -> None:
    a = frozenset({ComplianceFlag.FERPA})
    b = frozenset({ComplianceFlag.ITAR, ComplianceFlag.FERPA})
    assert compliance_union(a, b) == frozenset({ComplianceFlag.FERPA, ComplianceFlag.ITAR})


def test_lattice_version_present() -> None:
    assert LATTICE_VERSION == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_lattice.py -q
```
Expected: `ModuleNotFoundError: No module named 'contracts.lattice'` (and `contracts` not yet installed as a package).

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/contracts/pyproject.toml`:
```toml
[project]
name = "tigerexchange-contracts"
version = "0.0.0"
description = "TigerExchange canonical shared kernel: TierLattice, tenancy, classification, PEP contracts, interface seams. Near-frozen, zero feature deps, no persistence."
requires-python = ">=3.12,<3.13"
dependencies = ["pydantic>=2.6,<3"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/contracts"]

# Kernel fitness function (§5.5): zero outbound feature/persistence deps.
# import-linter enforces this in CI; the kernel may NOT import any
# service/store/feature package.
[tool.importlinter]
root_package = "contracts"

[[tool.importlinter.contracts]]
name = "kernel-has-no-feature-or-persistence-deps"
type = "forbidden"
source_modules = ["contracts"]
forbidden_modules = [
    "sqlalchemy", "psycopg", "asyncpg", "qdrant_client", "opensearchpy",
    "kuzu", "neo4j", "spicedb", "openfga_sdk", "fastapi", "api",
]
```

`tigerexchange/packages/contracts/src/contracts/lattice.py` — use the canonical kernel `lattice.py` verbatim from the CANONICAL KERNEL CONTRACTS section (the `from __future__ import annotations` module defining `Tier(IntEnum)` with `wire`/`parse`, `tier_join`, `tier_join_all`, `ComplianceFlag(StrEnum)`, `compliance_union`, and `LATTICE_VERSION = 1`). Reproduced here in full:

```python
"""Frozen 3-tier classification lattice (plan §5.6, §6.1)."""
from __future__ import annotations

from enum import IntEnum, StrEnum
from functools import reduce
from typing import Iterable


class Tier(IntEnum):
    """The frozen 3-tier sensitivity lattice (public < private < confidential)."""

    public = 0
    private = 1
    confidential = 2

    @property
    def wire(self) -> str:
        return self.name

    @classmethod
    def parse(cls, value: object) -> "Tier":
        """Parse from wire/DB form, FAIL-CLOSED on anything unknown (§5.6)."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls[value.strip().lower()]
            except KeyError:
                return cls.confidential
        return cls.confidential


def tier_join(a: Tier, b: Tier) -> Tier:
    """Least-upper-bound = the MORE restrictive tier (MAX-rule)."""
    return a if a >= b else b


def tier_join_all(tiers: Iterable[Tier]) -> Tier:
    """MAX-rule over a collection. Empty input fails closed to confidential."""
    materialized = list(tiers)
    if not materialized:
        return Tier.confidential
    return reduce(tier_join, materialized)


class ComplianceFlag(StrEnum):
    """Sticky compliance flags; UNION-on-join (§6.1)."""

    FERPA = "FERPA"
    IRB = "IRB"
    ITAR = "ITAR"
    EAR = "EAR"
    GDPR_PERSONAL = "GDPR-personal"


def compliance_union(*flag_sets: frozenset[ComplianceFlag]) -> frozenset[ComplianceFlag]:
    """UNION of compliance-flag sets (sticky-flag propagation, §6.1)."""
    out: set[ComplianceFlag] = set()
    for fs in flag_sets:
        out.update(fs)
    return frozenset(out)


LATTICE_VERSION: int = 1
```

Install the package editable so `contracts` is importable: `cd tigerexchange && uv sync` (or `python -m pip install -e packages/contracts`).

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_lattice.py -q
```
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): add K1 TierLattice (MAX-rule, fail-closed parse, sticky flags)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Kernel — tenancy (`tenancy.py`)

**Files:** Create `tigerexchange/packages/contracts/src/contracts/tenancy.py`, `tigerexchange/packages/contracts/tests/test_tenancy.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/contracts/tests/test_tenancy.py
"""Tenancy contract (§2.3, §7): Entitlement capability gating + PLG tier ceiling, frozen ctx."""
import pytest
from pydantic import ValidationError

from contracts.lattice import Tier
from contracts.tenancy import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
)


def _plg_entitlement() -> Entitlement:
    return Entitlement(
        edition=Edition.PLG,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL, Capability.OWN_MATERIALS}),
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.private,
    )


def test_plg_cannot_reach_confidential_tier() -> None:
    ent = _plg_entitlement()
    assert ent.permits_tier(Tier.private) is True
    assert ent.permits_tier(Tier.confidential) is False


def test_plg_lacks_confidential_capability() -> None:
    ent = _plg_entitlement()
    assert ent.has(Capability.OWN_MATERIALS) is True
    assert ent.has(Capability.CONFIDENTIAL_WORKSPACE) is False
    assert ent.has(Capability.EXCHANGE_PARTICIPATION) is False


def test_tenant_context_is_frozen() -> None:
    ctx = TenantContext(
        tenant_id="tenant-A", subject_id="sub-1", entitlement=_plg_entitlement()
    )
    with pytest.raises(ValidationError):
        ctx.tenant_id = "tenant-B"  # type: ignore[misc]


def test_tenant_context_defaults() -> None:
    ctx = TenantContext(
        tenant_id="tenant-A", subject_id="sub-1", entitlement=_plg_entitlement()
    )
    assert ctx.consortium_ids == frozenset()
    assert ctx.subject_active is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_tenancy.py -q
```
Expected: `ModuleNotFoundError: No module named 'contracts.tenancy'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/packages/contracts/src/contracts/tenancy.py` using the canonical `tenancy.py` verbatim (the module defining `Edition`, `Capability`, `IsolationPosture`, `Entitlement` with `has`/`permits_tier`, and frozen `TenantContext`). Reproduced in full:

```python
"""Tenant context + Edition/Entitlement capability model (plan §2.3, §5, §7)."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.lattice import Tier


class Edition(StrEnum):
    PLG = "plg"
    INSTITUTIONAL = "institutional"
    CAMPUS = "campus"
    CONSORTIUM_ANCHOR = "consortium-anchor"
    CONFIDENTIAL_SOVEREIGN = "confidential-sovereign"


class Capability(StrEnum):
    PUBLIC_RETRIEVAL = "public-retrieval"
    OWN_MATERIALS = "own-materials"
    PRIVATE_TIER = "private-tier"
    CONFIDENTIAL_WORKSPACE = "confidential-workspace"
    EXCHANGE_PARTICIPATION = "exchange-participation"
    CROSS_INSTITUTION_GRANTS = "cross-institution-grants"
    TEAM_ASSEMBLY = "team-assembly"
    BYO_PROVIDER = "byo-provider"
    DEDICATED_GPU = "dedicated-gpu"


class IsolationPosture(StrEnum):
    POOLED = "pooled"
    DEDICATED_CELL = "dedicated-cell"
    DEDICATED_CELL_GPU = "dedicated-cell-gpu"


class Entitlement(BaseModel):
    """Resolved capability set for a tenant. Evaluated at the PEP (§2.3)."""

    model_config = ConfigDict(frozen=True)

    edition: Edition
    capabilities: frozenset[Capability]
    isolation: IsolationPosture
    max_tier: Tier

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def permits_tier(self, tier: Tier) -> bool:
        return tier <= self.max_tier


class TenantContext(BaseModel):
    """Request-scoped tenant + subject identity (§4, §7); pinned via SET LOCAL (§7.7)."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(..., description="Stable owning-institution/tenant id; RLS leading key.")
    subject_id: str = Field(..., description="Authenticated subject (eduPersonUniqueId / OIDC sub).")
    entitlement: Entitlement
    consortium_ids: frozenset[str] = Field(default_factory=frozenset)
    affiliations: frozenset[str] = Field(default_factory=frozenset)
    subject_active: bool = True
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_tenancy.py -q
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): add tenancy (TenantContext, Edition/Entitlement, PLG tier ceiling)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Kernel — classification (`classification.py`)

**Files:** Create `tigerexchange/packages/contracts/src/contracts/classification.py`, `tigerexchange/packages/contracts/tests/test_classification.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/contracts/tests/test_classification.py
"""Classification fail-closed semantics (D6, §8): quarantine == confidential + non-retrievable."""
from contracts.classification import (
    Caveats,
    ClassificationResult,
    Decision,
    DiscoverabilityScope,
)
from contracts.lattice import Tier


def test_quarantine_is_confidential_and_not_retrievable() -> None:
    r = ClassificationResult.quarantine(reason="abstain: low confidence")
    assert r.tier is Tier.confidential
    assert r.decision is Decision.QUARANTINE
    assert r.is_retrievable is False
    assert r.confidence == 0.0


def test_allow_is_retrievable() -> None:
    r = ClassificationResult(tier=Tier.public, decision=Decision.ALLOW, confidence=0.95)
    assert r.is_retrievable is True


def test_deny_is_not_retrievable() -> None:
    r = ClassificationResult(tier=Tier.private, decision=Decision.DENY, confidence=0.8)
    assert r.is_retrievable is False


def test_discoverability_scope_values() -> None:
    assert {s.value for s in DiscoverabilityScope} == {
        "public-web", "federation-wide", "named-consortium", "named-tenants", "none",
    }


def test_caveats_optional_fields() -> None:
    c = Caveats(transfer_legality=True, export_attestation="att-123", ferpa_role="instructor")
    assert c.transfer_legality is True
    assert Caveats().ferpa_role is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_classification.py -q
```
Expected: `ModuleNotFoundError: No module named 'contracts.classification'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/packages/contracts/src/contracts/classification.py` using the canonical `classification.py` verbatim (`Decision`, `DiscoverabilityScope`, `ClassificationResult` with `quarantine()` classmethod + `is_retrievable` property + `lattice_version` stamp, and `Caveats`). Reproduced in full:

```python
"""Classification result + Decision/DiscoverabilityScope enums (plan §4.7, §8, D6)."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.lattice import LATTICE_VERSION, ComplianceFlag, Tier


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"


class DiscoverabilityScope(StrEnum):
    PUBLIC_WEB = "public-web"
    FEDERATION_WIDE = "federation-wide"
    NAMED_CONSORTIUM = "named-consortium"
    NAMED_TENANTS = "named-tenants"
    NONE = "none"


class ClassificationResult(BaseModel):
    """Output of the single fail-closed classifier (§8, D6)."""

    model_config = ConfigDict(frozen=True)

    tier: Tier
    decision: Decision
    compliance_flags: frozenset[ComplianceFlag] = Field(default_factory=frozenset)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = ""
    lattice_version: int = LATTICE_VERSION

    @classmethod
    def quarantine(cls, reason: str, confidence: float = 0.0) -> "ClassificationResult":
        return cls(
            tier=Tier.confidential,
            decision=Decision.QUARANTINE,
            confidence=confidence,
            reason=reason,
        )

    @property
    def is_retrievable(self) -> bool:
        return self.decision is Decision.ALLOW


class Caveats(BaseModel):
    """Sticky, re-evaluated-at-access caveats on a sharing grant (§4.3, §7.3)."""

    model_config = ConfigDict(frozen=True)

    transfer_legality: bool | None = None
    export_attestation: str | None = None
    ferpa_role: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_classification.py -q
```
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): add classification (Decision/QUARANTINE fail-closed, DiscoverabilityScope, Caveats)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Kernel K2 — PublishableProjection (`projection.py`)

**Files:** Create `tigerexchange/packages/contracts/src/contracts/projection.py`, `tigerexchange/packages/contracts/tests/test_projection.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/contracts/tests/test_projection.py
"""PublishableProjection (K2, §4.7/§5.6b/D6): confidential rejected, dual version stamps."""
import pytest
from pydantic import ValidationError

from contracts.classification import DiscoverabilityScope
from contracts.projection import PROJECTION_SCHEMA_VERSION, PublishableProjection
from contracts.lattice import LATTICE_VERSION, Tier


def _public_projection(tier: Tier) -> PublishableProjection:
    return PublishableProjection(
        projection_id="proj-1",
        artifact_id="art-1",
        owner_tenant_id="tenant-A",
        tier=tier,
        discoverability_scope=DiscoverabilityScope.FEDERATION_WIDE,
        fields={"title": "Hybrid retrieval over scholarly corpora"},
    )


def test_public_projection_carries_both_versions() -> None:
    p = _public_projection(Tier.public)
    assert p.lattice_version == LATTICE_VERSION
    assert p.projection_schema_version == PROJECTION_SCHEMA_VERSION


def test_private_projection_allowed() -> None:
    assert _public_projection(Tier.private).tier is Tier.private


def test_confidential_projection_rejected_d6() -> None:
    with pytest.raises(ValidationError):
        _public_projection(Tier.confidential)


def test_projection_is_frozen() -> None:
    p = _public_projection(Tier.public)
    with pytest.raises(ValidationError):
        p.tier = Tier.private  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_projection.py -q
```
Expected: `ModuleNotFoundError: No module named 'contracts.projection'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/packages/contracts/src/contracts/projection.py` using the canonical `projection.py` verbatim (frozen `PublishableProjection` with `_no_confidential_in_index` field-validator, `PROJECTION_SCHEMA_VERSION = 1`, dual version stamps). Reproduced in full:

```python
"""PublishableProjection — the federation-seam contract (plan §4.7, §5.6b, §6.1)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from contracts.classification import DiscoverabilityScope
from contracts.lattice import LATTICE_VERSION, Tier

PROJECTION_SCHEMA_VERSION: int = 1


class PublishableProjection(BaseModel):
    """Public/shared-tier projection of an artifact for the central index (§4.7, D6)."""

    model_config = ConfigDict(frozen=True)

    projection_id: str
    artifact_id: str = Field(..., description="Source artifact this projects (owner-local).")
    owner_tenant_id: str

    tier: Tier
    discoverability_scope: DiscoverabilityScope

    fields: dict[str, object] = Field(default_factory=dict)

    lattice_version: int = LATTICE_VERSION
    projection_schema_version: int = PROJECTION_SCHEMA_VERSION

    @field_validator("tier")
    @classmethod
    def _no_confidential_in_index(cls, v: Tier) -> Tier:
        if v is Tier.confidential:
            raise ValueError(
                "PublishableProjection cannot carry confidential tier (D6): "
                "confidential content never enters the shared central index."
            )
        return v
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_projection.py -q
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): add K2 PublishableProjection (D6 confidential-reject, dual version stamps)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Kernel — PEP request/response (`pep.py`)

**Files:** Create `tigerexchange/packages/contracts/src/contracts/pep.py`, `tigerexchange/packages/contracts/tests/test_pep.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/contracts/tests/test_pep.py
"""PEP contracts (§4.2/§4.7, D4): one request/response shape; fail-closed payload invariant."""
import pytest
from pydantic import ValidationError

from contracts.classification import Decision
from contracts.lattice import Tier
from contracts.pep import PepAction, PepRequest, PepResponse
from contracts.tenancy import Capability, Edition, Entitlement, IsolationPosture, TenantContext


def _ctx() -> TenantContext:
    return TenantContext(
        tenant_id="tenant-A",
        subject_id="sub-1",
        entitlement=Entitlement(
            edition=Edition.INSTITUTIONAL,
            capabilities=frozenset({Capability.PRIVATE_TIER}),
            isolation=IsolationPosture.DEDICATED_CELL,
            max_tier=Tier.confidential,
        ),
    )


def test_request_carries_action_and_capability() -> None:
    req = PepRequest(
        request_id="r-1",
        tenant=_ctx(),
        action=PepAction.RETRIEVE,
        required_capability=Capability.PRIVATE_TIER,
        resource_id="art-9",
    )
    assert req.action is PepAction.RETRIEVE


def test_allow_response_may_carry_payload() -> None:
    resp = PepResponse(
        request_id="r-1",
        decision=Decision.ALLOW,
        effective_tier=Tier.private,
        payload=[{"title": "x"}],
    )
    assert resp.payload == [{"title": "x"}]


def test_deny_response_with_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PepResponse(
            request_id="r-1",
            decision=Decision.DENY,
            effective_tier=Tier.private,
            payload=[{"leak": "should-not-happen"}],
        )


def test_quarantine_response_with_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PepResponse(
            request_id="r-1",
            decision=Decision.QUARANTINE,
            effective_tier=Tier.confidential,
            payload=[{"leak": "x"}],
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_pep.py -q
```
Expected: `ModuleNotFoundError: No module named 'contracts.pep'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/packages/contracts/src/contracts/pep.py` using the canonical `pep.py` verbatim (`PepAction`, frozen `PepRequest`, frozen `PepResponse` with the `model_post_init` fail-closed payload guard). Reproduced in full:

```python
"""Policy Enforcement Point request/response contracts (plan §4.2, §4.7, D4)."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.classification import Caveats, Decision, DiscoverabilityScope
from contracts.lattice import Tier
from contracts.tenancy import Capability, TenantContext


class PepAction(StrEnum):
    RETRIEVE = "retrieve"
    EGRESS = "egress"
    DERIVE = "derive"
    DISCOVER = "discover"
    BROKERED_DRILLDOWN = "brokered-drilldown"


class PepRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    tenant: TenantContext
    action: PepAction
    required_capability: Capability
    resource_id: str | None = None
    grant_id: str | None = None
    deadline_ms: int | None = None
    attributes: dict[str, object] = Field(default_factory=dict)


class PepResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    decision: Decision
    effective_tier: Tier
    payload: list[dict[str, object]] | None = None
    discoverability_scope: DiscoverabilityScope | None = None
    caveats: Caveats | None = None
    reason: str = ""

    def model_post_init(self, _ctx: object) -> None:
        if self.decision is not Decision.ALLOW and self.payload is not None:
            raise ValueError(
                "PepResponse: non-ALLOW decision must carry no payload (fail-closed)."
            )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_pep.py -q
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): add PEP request/response (single shape, fail-closed payload invariant)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Kernel — audit event (`audit.py`)

**Files:** Create `tigerexchange/packages/contracts/src/contracts/audit.py`, `tigerexchange/packages/contracts/tests/test_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/contracts/tests/test_audit.py
"""AuditEvent (§4.1): per-stream hash-chain shape; genesis prev_hash None; frozen."""
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from contracts.audit import AuditEvent, AuditEventType
from contracts.classification import Decision


def _event(seq: int, prev: str | None) -> AuditEvent:
    return AuditEvent(
        event_id=f"e-{seq}",
        stream_id="cell-A",
        sequence=seq,
        event_type=AuditEventType.PEP_DECISION,
        occurred_at=datetime.now(UTC),
        tenant_id="tenant-A",
        decision=Decision.ALLOW,
        prev_hash=prev,
        entry_hash=f"h-{seq}",
    )


def test_genesis_has_no_prev_hash() -> None:
    g = _event(0, None)
    assert g.prev_hash is None
    assert g.sequence == 0


def test_chain_links_prev_to_entry() -> None:
    g = _event(0, None)
    nxt = _event(1, g.entry_hash)
    assert nxt.prev_hash == g.entry_hash


def test_negative_sequence_rejected() -> None:
    with pytest.raises(ValidationError):
        _event(-1, None)


def test_event_is_frozen() -> None:
    g = _event(0, None)
    with pytest.raises(ValidationError):
        g.entry_hash = "tampered"  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_audit.py -q
```
Expected: `ModuleNotFoundError: No module named 'contracts.audit'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/packages/contracts/src/contracts/audit.py` using the canonical `audit.py` verbatim (`AuditEventType`, frozen `AuditEvent` with `stream_id`/`sequence`/`prev_hash`/`entry_hash`). Reproduced in full:

```python
"""Per-stream hash-chained audit event (plan §4.1, §4.4a)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.classification import Decision


class AuditEventType(StrEnum):
    PEP_DECISION = "pep-decision"
    CLASSIFICATION = "classification"
    REVOCATION = "revocation"
    EGRESS = "egress"
    GRANT_ISSUED = "grant-issued"
    BROKERED_ACCESS = "brokered-access"


class AuditEvent(BaseModel):
    """A single, frozen, hash-chained audit record (§4.1)."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    stream_id: str = Field(..., description="Per-stream hash-chain partition key.")
    sequence: int = Field(..., ge=0, description="Monotonic per-stream sequence number.")

    event_type: AuditEventType
    occurred_at: datetime

    tenant_id: str
    subject_id: str | None = None
    resource_id: str | None = None

    decision: Decision | None = None
    reason: str = ""

    prev_hash: str | None = None
    entry_hash: str = Field(..., description="H(prev_hash || canonical(this event payload)).")

    detail: dict[str, object] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_audit.py -q
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): add per-stream hash-chain AuditEvent

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Kernel K3 — interfaces + intra-cell/cross-node locus table (`interfaces.py`)

**Files:** Create `tigerexchange/packages/contracts/src/contracts/interfaces.py`, `tigerexchange/packages/contracts/tests/test_interfaces.py`

This task lands the ~15 K3 Protocols AND the **kernel-interface versioning/evolution** structure: the canonical `InterfaceLocus` `StrEnum` plus the static `INTERFACE_LOCUS` table declaring each interface as `intra_cell` (single-deploy, evolves with the cell) or `cross_node` (needs negotiated min-common-version evolution). These are **canonical kernel symbols** (defined in `00-kernel-contracts.md` under the R8 kernel-interface-versioning amendment); 0a builds them verbatim and re-exports them in Task 9 — they are NOT non-canonical additions. The locus table is what the compat check in Task 9 keys off.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/contracts/tests/test_interfaces.py
"""K3 interfaces (§5.1) + intra_cell/cross_node evolution-locus declaration (R8)."""
import pytest

from contracts import interfaces as ifc
from contracts.interfaces import (
    INTERFACE_LOCUS,
    InterfaceLocus,
    IPolicyEnforcement,
    IExchangeFeed,
)


EXPECTED_INTERFACES = {
    "IClassifier", "IPolicyEnforcement", "IDataAccessBroker", "IModelProvider",
    "IModelRouter", "IRetrievalStrategy", "IReranker", "IExpertiseFingerprint",
    "ICollaborationGraph", "IAuditSink", "IGrantStore", "IExchangeFeed",
    "IRevocationAuthority",
}


def test_all_interfaces_present() -> None:
    for name in EXPECTED_INTERFACES:
        assert hasattr(ifc, name), f"missing kernel interface {name}"


def test_every_interface_has_a_declared_locus() -> None:
    # Every named interface MUST declare an evolution locus (intra-cell vs cross-node)
    # so the CI compat check (Task 9) knows whether a breaking change is gateable.
    missing = EXPECTED_INTERFACES - set(INTERFACE_LOCUS)
    assert missing == set(), f"interfaces without declared locus: {missing}"


def test_locus_values_are_valid() -> None:
    valid = {m.value for m in InterfaceLocus}
    assert valid == {"intra_cell", "cross_node"}
    assert all(v in InterfaceLocus for v in INTERFACE_LOCUS.values())


def test_federation_seam_interfaces_are_cross_node() -> None:
    # The deferred federation seams (exchange-feed, revocation authority) cross node
    # boundaries and need negotiated evolution.
    assert INTERFACE_LOCUS["IExchangeFeed"] is InterfaceLocus.cross_node
    assert INTERFACE_LOCUS["IRevocationAuthority"] is InterfaceLocus.cross_node


def test_cell_local_pep_is_intra_cell() -> None:
    assert INTERFACE_LOCUS["IPolicyEnforcement"] is InterfaceLocus.intra_cell


def test_protocols_are_runtime_checkable() -> None:
    class _Stub:
        def authorize(self, request: object) -> object:  # noqa: ANN401
            return request

    # runtime_checkable Protocol => isinstance structural check works
    assert isinstance(_Stub(), IPolicyEnforcement)


def test_deferred_seam_documented_phase1() -> None:
    assert "Phase-1+" in (IExchangeFeed.__doc__ or "")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_interfaces.py -q
```
Expected: `ModuleNotFoundError: No module named 'contracts.interfaces'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/packages/contracts/src/contracts/interfaces.py` using the canonical `interfaces.py` verbatim (all `@runtime_checkable Protocol`s: `IClassifier, IPolicyEnforcement, IDataAccessBroker, IModelProvider, IModelRouter, IRetrievalStrategy, IReranker, IExpertiseFingerprint, ICollaborationGraph, IAuditSink, IGrantStore, Grant`, plus the Phase-1+ deferred stubs `IExchangeFeed, IRevocationAuthority`), then **append** the canonical kernel-interface-versioning block below verbatim from `00-kernel-contracts.md` (R8). These are **canonical kernel symbols**, not a 0a-local addition; `StrEnum` is already imported at the top of `interfaces.py` via `from enum import StrEnum`:

```python
# --------------------------------------------------------------------------- #
# Kernel-interface versioning / evolution contract (R8, §5.1/§5.8).
# These pin the kernel API surface itself: a single integer API version, the
# locus each interface is deployed at (intra_cell vs cross_node), and a frozen
# name->locus mapping. They are part of the canonical kernel; 0a re-exports them
# in Task 9 (they are NOT non-canonical symbols).
#
# intra_cell : single-deploy interface; evolves WITH the cell, no cross-node
#              negotiation needed (the impl and all callers ship together).
# cross_node : crosses the federation seam between nodes (the deferred Phase-1+
#              seams), so a breaking change needs additive-by-default + a
#              negotiated min-common-version, exactly like PublishableProjection
#              (§5.6b).
#
# The Task-9 CI compat check keys off this table: a removed/renamed symbol or a
# changed signature on a `cross_node` interface is a HARD CI failure (must be
# additive + version-negotiated); the same change on an `intra_cell` interface
# is a soft warning (cell ships atomically).
# --------------------------------------------------------------------------- #

# Monotonic version of the kernel interface surface (K3). Bumped on any breaking
# change to an interface signature; lets 0a assert compatibility.
KERNEL_API_VERSION: int = 1


class InterfaceLocus(StrEnum):
    """Deployment locus of a kernel interface (§4.2, §5.8).

    intra_cell: invoked inside a single tenant cell / owner-local trust boundary.
    cross_node: invoked across the federation seam between nodes (Phase-1+ for
    the deferred seams, but the locus is fixed now so it cannot drift).
    """

    intra_cell = "intra_cell"
    cross_node = "cross_node"


# Frozen mapping of every kernel interface NAME to its locus. The deferred
# federation seams (IExchangeFeed, IRevocationAuthority) are cross_node; all
# Phase-0-active interfaces are intra_cell. The central-index read PEP runs the
# SAME IPolicyEnforcement code at the seam, but the interface itself is pinned
# intra_cell here because Phase-0 exercises only the owner-local locus.
INTERFACE_LOCUS: dict[str, InterfaceLocus] = {
    "IClassifier": InterfaceLocus.intra_cell,
    "IPolicyEnforcement": InterfaceLocus.intra_cell,
    "IDataAccessBroker": InterfaceLocus.intra_cell,
    "IModelProvider": InterfaceLocus.intra_cell,
    "IModelRouter": InterfaceLocus.intra_cell,
    "IRetrievalStrategy": InterfaceLocus.intra_cell,
    "IReranker": InterfaceLocus.intra_cell,
    "IExpertiseFingerprint": InterfaceLocus.intra_cell,
    "ICollaborationGraph": InterfaceLocus.intra_cell,
    "IAuditSink": InterfaceLocus.intra_cell,
    "IGrantStore": InterfaceLocus.intra_cell,
    "IExchangeFeed": InterfaceLocus.cross_node,        # Phase-1+ seam
    "IRevocationAuthority": InterfaceLocus.cross_node,  # Phase-1+ seam
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_interfaces.py -q
```
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): add K3 interface Protocols + intra-cell/cross-node evolution-locus table

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Kernel public API surface, fitness check, and kernel-interface compat check

**Files:** Create `tigerexchange/packages/contracts/src/contracts/__init__.py` (replace stub), `tigerexchange/packages/contracts/api/contracts_api.txt`, `tigerexchange/packages/contracts/tests/test_kernel_fitness.py`, `tigerexchange/packages/contracts/tests/test_kernel_compat.py`

This task closes the deliverable's "versioned (per-interface or whole-package backward+forward compat rule), import-linter + kernel fan-in/size fitness check run green in CI" requirement and the kernel-interface-versioning HIGH. The compat check uses `griffe` to diff the live kernel public API against a committed baseline; removals/renames fail (forward+backward break), additions pass (additive), and `cross-node` interfaces get the strict treatment.

- [ ] **Step 1: Write the failing tests**

```python
# tigerexchange/packages/contracts/tests/test_kernel_fitness.py
"""Kernel fitness function (§5.5): zero persistence/feature deps; bounded fan-in/size."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "contracts"

FORBIDDEN_TOP_LEVEL = {
    "sqlalchemy", "psycopg", "asyncpg", "qdrant_client", "opensearchpy",
    "kuzu", "neo4j", "spicedb", "openfga_sdk", "fastapi", "api", "dagster",
}


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    return mods


def test_kernel_imports_no_persistence_or_feature_packages() -> None:
    for py in SRC.rglob("*.py"):
        offenders = _imported_top_level_modules(py) & FORBIDDEN_TOP_LEVEL
        assert offenders == set(), f"{py.name} imports forbidden kernel deps: {offenders}"


def test_kernel_has_no_persistence_state() -> None:
    # No module-level mutable connection/engine/session globals in the kernel.
    banned_substrings = ("create_engine", "sessionmaker", "connect(")
    for py in SRC.rglob("*.py"):
        text = py.read_text()
        for banned in banned_substrings:
            assert banned not in text, f"{py.name} appears to hold persistent state: {banned}"


def test_kernel_size_bounded() -> None:
    # Fan-in/size fitness: the near-frozen kernel stays small. Ceiling guards drift.
    py_files = list(SRC.rglob("*.py"))
    total_lines = sum(len(p.read_text().splitlines()) for p in py_files)
    assert len(py_files) <= 10, f"kernel module count drifted: {len(py_files)}"
    assert total_lines <= 900, f"kernel grew beyond fitness ceiling: {total_lines} lines"
```

```python
# tigerexchange/packages/contracts/tests/test_kernel_compat.py
"""Kernel-interface backward+forward compat check (convergence HIGH).

Diffs the live kernel public API against the committed baseline in
api/contracts_api.txt. A REMOVED or RENAMED public symbol breaks both backward
and forward compat -> HARD FAIL (must be additive + version-negotiated, §5.6b).
An ADDED public symbol is additive -> pass, but the baseline must be refreshed
in the same commit (so reviewers see the surface grow deliberately).
"""
from pathlib import Path

import contracts

BASELINE = Path(__file__).resolve().parent.parent / "api" / "contracts_api.txt"


def _live_surface() -> set[str]:
    return set(contracts.__all__)


def _baseline_surface() -> set[str]:
    return {
        line.strip()
        for line in BASELINE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_no_public_symbol_removed_or_renamed() -> None:
    removed = _baseline_surface() - _live_surface()
    assert removed == set(), (
        f"kernel public API removed/renamed (breaks backward+forward compat): {removed}. "
        "Removals must follow the §5.6b deprecation procedure, not silent deletion."
    )


def test_added_symbols_are_recorded_in_baseline() -> None:
    added = _live_surface() - _baseline_surface()
    assert added == set(), (
        f"kernel public API grew without updating api/contracts_api.txt: {added}. "
        "Additive change is allowed but the baseline must be refreshed in the same commit."
    )


def test_kernel_api_version_present() -> None:
    assert isinstance(contracts.KERNEL_API_VERSION, int)
    assert contracts.KERNEL_API_VERSION >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/test_kernel_fitness.py packages/contracts/tests/test_kernel_compat.py -q
```
Expected: `test_kernel_compat` errors (`AttributeError: module 'contracts' has no attribute '__all__'` / missing `KERNEL_API_VERSION`, and `api/contracts_api.txt` not found). `test_kernel_fitness` may pass already; that is fine — the compat tests are the gate to make green.

- [ ] **Step 3: Write minimal implementation**

Replace `tigerexchange/packages/contracts/src/contracts/__init__.py` with the canonical single-import-surface block (the CORRECTED version — do **not** include the `IRerankerLike :=` walrus artifact), and add `KERNEL_API_VERSION`:

```python
"""TigerExchange canonical kernel — single import surface (plan §5.1).

These signatures are AUTHORITATIVE. Every sub-plan imports from `contracts`
verbatim. The kernel is near-frozen, has zero feature-module deps, and holds no
persistent state (§5.5 fitness function). The public surface is versioned and
guarded by a backward+forward compat check (api/contracts_api.txt).
"""
from contracts.audit import AuditEvent, AuditEventType
from contracts.classification import (
    Caveats,
    ClassificationResult,
    Decision,
    DiscoverabilityScope,
)
from contracts.interfaces import (
    INTERFACE_LOCUS,
    KERNEL_API_VERSION,
    Grant,
    IAuditSink,
    IClassifier,
    ICollaborationGraph,
    IDataAccessBroker,
    IExchangeFeed,
    IExpertiseFingerprint,
    IGrantStore,
    IModelProvider,
    IModelRouter,
    InterfaceLocus,
    IPolicyEnforcement,
    IReranker,
    IRetrievalStrategy,
    IRevocationAuthority,
)
from contracts.lattice import (
    LATTICE_VERSION,
    ComplianceFlag,
    Tier,
    compliance_union,
    tier_join,
    tier_join_all,
)
from contracts.pep import PepAction, PepRequest, PepResponse
from contracts.projection import PROJECTION_SCHEMA_VERSION, PublishableProjection
from contracts.tenancy import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
)

# KERNEL_API_VERSION, InterfaceLocus, and INTERFACE_LOCUS are CANONICAL kernel
# symbols defined in contracts.interfaces (R8 kernel-interface-versioning
# amendment); the kernel re-exports them here. A breaking change to a
# `cross_node` interface (INTERFACE_LOCUS) requires a negotiated
# min-common-version per §5.6b, never a silent removal.

__all__ = [
    "KERNEL_API_VERSION",
    # lattice (K1)
    "Tier", "tier_join", "tier_join_all", "ComplianceFlag", "compliance_union",
    "LATTICE_VERSION",
    # tenancy
    "TenantContext", "Edition", "Entitlement", "Capability", "IsolationPosture",
    # classification
    "Decision", "DiscoverabilityScope", "ClassificationResult", "Caveats",
    # projection (K2)
    "PublishableProjection", "PROJECTION_SCHEMA_VERSION",
    # pep
    "PepRequest", "PepResponse", "PepAction",
    # audit
    "AuditEvent", "AuditEventType",
    # interfaces (K3) + evolution-locus
    "IClassifier", "IPolicyEnforcement", "IDataAccessBroker", "IModelRouter",
    "IModelProvider", "IRetrievalStrategy", "IReranker", "IExpertiseFingerprint",
    "ICollaborationGraph", "IExchangeFeed", "IGrantStore", "Grant", "IAuditSink",
    "IRevocationAuthority", "INTERFACE_LOCUS", "InterfaceLocus",
]
```

Generate the baseline so it exactly matches `__all__` (one symbol per line):

```bash
cd tigerexchange && python -c "import contracts, pathlib; pathlib.Path('packages/contracts/api').mkdir(parents=True, exist_ok=True); pathlib.Path('packages/contracts/api/contracts_api.txt').write_text('# Kernel public API baseline (compat check). Refresh deliberately on additive change.\n' + '\n'.join(sorted(contracts.__all__)) + '\n')"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tigerexchange && python -m pytest packages/contracts/tests/ -q && python -m lint_imports --config packages/contracts/pyproject.toml
```
Expected: all contracts tests pass (kernel fitness + compat green); `lint-imports` reports the `kernel-has-no-feature-or-persistence-deps` contract KEPT.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/packages/contracts && git commit -m "feat(contracts): freeze kernel public API surface + fitness + backward/forward compat check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: API service config + async DB engine with transaction-scoped TenantContext (`SET LOCAL`)

**Files:** Create `tigerexchange/services/api/pyproject.toml`, `tigerexchange/services/api/src/api/config.py`, `tigerexchange/services/api/src/api/db.py`, `tigerexchange/services/api/tests/test_db_set_local.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/api/tests/test_db_set_local.py
"""tenant_session pins TenantContext via SET LOCAL on a transaction-scoped connection (§7.7)."""
import pytest
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from api.db import Database

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_dsn():
    with PostgresContainer("postgres:16-alpine") as pg:
        # asyncpg DSN form
        yield pg.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")


async def test_set_local_sets_tenant_for_this_txn_only(pg_dsn: str) -> None:
    db = Database(pg_dsn)
    async with db.tenant_session("tenant-A") as session:
        row = await session.execute(text("SELECT current_setting('app.tenant_id', true)"))
        assert row.scalar_one() == "tenant-A"
    # New transaction without a tenant: SET LOCAL did NOT leak (would be NULL/empty).
    async with db.engine.connect() as conn:
        row = await conn.execute(text("SELECT current_setting('app.tenant_id', true)"))
        leaked = row.scalar_one()
        assert leaked in (None, ""), f"tenant context leaked across connections: {leaked!r}"
    await db.dispose()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_db_set_local.py -q
```
Expected: `ModuleNotFoundError: No module named 'api.db'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/services/api/pyproject.toml`:
```toml
[project]
name = "tigerexchange-api"
version = "0.0.0"
description = "TigerExchange FastAPI service: health, per-request TenantContext via SET LOCAL, FORCE-RLS tenant isolation."
requires-python = ">=3.12,<3.13"
dependencies = [
    "tigerexchange-contracts",
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "pydantic-settings>=2.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/api"]
```

`tigerexchange/services/api/src/api/config.py`:
```python
"""Service configuration (Pydantic-settings)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TIGEREXCHANGE_", env_file=".env")

    database_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    env: str = "dev"
```

`tigerexchange/services/api/src/api/db.py`:
```python
"""Async engine + transaction-scoped tenant session (§7.7).

The tenant context is pinned with SET LOCAL (transaction-scoped), NEVER SET, so a
PgBouncer transaction-mode connection cannot leak tenant context to the next
borrower. SET LOCAL must run inside an explicit transaction; tenant_session opens
one and binds the tenant before yielding the session.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Database:
    def __init__(self, dsn: str) -> None:
        self.engine = create_async_engine(dsn, pool_pre_ping=True)
        self._sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def tenant_session(self, tenant_id: str) -> AsyncIterator[AsyncSession]:
        """Open a transaction and pin app.tenant_id via SET LOCAL for its lifetime."""
        async with self._sessionmaker() as session:
            async with session.begin():
                # set_config(key, value, is_local=true) == SET LOCAL; parameterized to
                # avoid injection. Scoped to THIS transaction only.
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": tenant_id},
                )
                yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_db_set_local.py -q
```
Expected: `1 passed` (requires Docker for testcontainers).

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/services/api && git commit -m "feat(api): async DB engine with transaction-scoped SET LOCAL tenant context

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: FORCE-RLS migration (RESTRICTIVE + WITH CHECK + tenant_id-leading index)

**Files:** Create `tigerexchange/services/api/migrations/001_tenant_rls.sql`, `tigerexchange/services/api/tests/test_rls_isolation.py`

This is the deliverable's core security demonstration: the **cross-tenant-read-denied (BOLA)** test of §7.7.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/api/tests/test_rls_isolation.py
"""FORCE-RLS cross-tenant isolation (§7.7): BOLA denied via direct read + borrowed connection."""
from pathlib import Path

import pytest
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from api.db import Database

pytestmark = pytest.mark.integration

MIGRATION = Path(__file__).resolve().parent.parent / "migrations" / "001_tenant_rls.sql"


@pytest.fixture(scope="module")
def pg_dsn():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")


async def _apply_migration_and_seed(db: Database) -> None:
    # DDL as superuser (engine connection); FORCE RLS still applies to a non-owner app role.
    async with db.engine.begin() as conn:
        for stmt in MIGRATION.read_text().split(";"):
            if stmt.strip():
                await conn.execute(text(stmt))
    # Seed one row per tenant THROUGH the tenant_session so WITH CHECK is satisfied.
    async with db.tenant_session("tenant-A") as s:
        await s.execute(
            text("INSERT INTO own_materials (id, tenant_id, title) VALUES (1, 'tenant-A', 'A-secret')")
        )
    async with db.tenant_session("tenant-B") as s:
        await s.execute(
            text("INSERT INTO own_materials (id, tenant_id, title) VALUES (2, 'tenant-B', 'B-secret')")
        )


async def test_tenant_a_sees_only_own_rows(pg_dsn: str) -> None:
    db = Database(pg_dsn)
    await _apply_migration_and_seed(db)
    async with db.tenant_session("tenant-A") as s:
        rows = (await s.execute(text("SELECT title FROM own_materials"))).scalars().all()
    assert rows == ["A-secret"]
    await db.dispose()


async def test_bola_read_of_other_tenant_row_by_id_denied(pg_dsn: str) -> None:
    db = Database(pg_dsn)
    await _apply_migration_and_seed(db)
    # tenant-A explicitly targets tenant-B's row id=2 (classic BOLA/IDOR).
    async with db.tenant_session("tenant-A") as s:
        rows = (await s.execute(text("SELECT title FROM own_materials WHERE id = 2"))).scalars().all()
    assert rows == [], "RLS failed: tenant-A read tenant-B's row by id (BOLA)"
    await db.dispose()


async def test_cross_tenant_insert_blocked_by_with_check(pg_dsn: str) -> None:
    db = Database(pg_dsn)
    await _apply_migration_and_seed(db)
    # tenant-A tries to write a row stamped tenant-B -> WITH CHECK must reject.
    with pytest.raises(Exception):
        async with db.tenant_session("tenant-A") as s:
            await s.execute(
                text("INSERT INTO own_materials (id, tenant_id, title) VALUES (99, 'tenant-B', 'forged')")
            )
    await db.dispose()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_rls_isolation.py -q
```
Expected: collection passes but tests error — `migrations/001_tenant_rls.sql` does not exist (`FileNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/services/api/migrations/001_tenant_rls.sql`:
```sql
-- Pooled-plane per-tenant isolation: FORCE RLS defense-in-depth (§7.7).
-- Footguns explicitly closed: FORCE RLS (owner/superuser cannot bypass),
-- RESTRICTIVE (AND-combined; adding a policy can only narrow), WITH CHECK
-- (blocks cross-tenant INSERT/UPDATE), tenant_id leading index (index-driven
-- predicate, no full-scan side channel). SET LOCAL drives current_setting.

CREATE TABLE own_materials (
    id        BIGINT PRIMARY KEY,
    tenant_id TEXT   NOT NULL,
    title     TEXT   NOT NULL
);

-- tenant_id as the LEADING index column (§7.7).
CREATE INDEX own_materials_tenant_id_idx ON own_materials (tenant_id, id);

ALTER TABLE own_materials ENABLE ROW LEVEL SECURITY;
-- FORCE so the table OWNER does not bypass RLS (§7.7).
ALTER TABLE own_materials FORCE ROW LEVEL SECURITY;

-- RESTRICTIVE (AND-combined), not PERMISSIVE; reads filtered AND writes WITH CHECK'd.
CREATE POLICY own_materials_tenant_isolation ON own_materials
    AS RESTRICTIVE
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
```

Note: the test seeds through `tenant_session` so reads/writes run under the bound tenant and FORCE RLS applies. Because RESTRICTIVE policies are AND-combined with no PERMISSIVE base policy, an explicit base PERMISSIVE policy is not added — the single RESTRICTIVE policy is the boundary, which the BOLA test verifies returns zero foreign rows. (If a future migration adds a PERMISSIVE policy, the RESTRICTIVE one still narrows it.)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_rls_isolation.py -q
```
Expected: `3 passed` — cross-tenant read denied, BOLA-by-id denied, cross-tenant insert blocked by WITH CHECK.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/services/api && git commit -m "feat(api): FORCE-RLS tenant isolation migration + cross-tenant-read-denied test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Forbidden-bypass lint (no SECURITY DEFINER / matview over tenant-scoped tables)

**Files:** Create `tigerexchange/services/api/scripts/check_rls_bypass.py`, `tigerexchange/services/api/migrations/002_forbidden_bypass_check.sql` (a fixture the lint must catch, kept under a `tests/fixtures` path so it is never applied), `tigerexchange/services/api/tests/test_rls_lint.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/api/tests/test_rls_lint.py
"""RLS-bypass lint (§7.7): flag SECURITY DEFINER / materialized views over tenant tables."""
from pathlib import Path

from api_scripts.check_rls_bypass import find_rls_bypasses

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GOOD_MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


def test_clean_migration_has_no_bypasses() -> None:
    assert find_rls_bypasses(GOOD_MIGRATIONS) == []


def test_security_definer_function_is_flagged() -> None:
    findings = find_rls_bypasses(FIXTURES)
    joined = " ".join(findings).lower()
    assert "security definer" in joined


def test_materialized_view_is_flagged() -> None:
    findings = find_rls_bypasses(FIXTURES)
    joined = " ".join(findings).lower()
    assert "materialized view" in joined
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_rls_lint.py -q
```
Expected: `ModuleNotFoundError: No module named 'api_scripts.check_rls_bypass'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/services/api/scripts/__init__.py` — make scripts importable as `api_scripts`:
```python
"""CLI/lint scripts for the API service."""
```
(Configure the package name by adding to `services/api/pyproject.toml` `[tool.hatch.build.targets.wheel] packages = ["src/api", "scripts"]` and a `[tool.hatch.build.targets.wheel.force-include] "scripts" = "api_scripts"`. Simpler for Phase-0: place the module at `services/api/src/api_scripts/check_rls_bypass.py` and reference it as `api_scripts.check_rls_bypass`. Use the src layout.)

Create `tigerexchange/services/api/src/api_scripts/__init__.py`:
```python
"""CLI/lint scripts for the API service."""
```

Create `tigerexchange/services/api/src/api_scripts/check_rls_bypass.py`:
```python
"""Lint: forbid SECURITY DEFINER functions and materialized views in migrations (§7.7).

These constructs can bypass the tenant predicate. Phase-0 forbids them outright in
applied migrations; if ever required, they must explicitly re-apply the tenant filter
(reviewed exception, out of scope for Phase-0).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SECURITY_DEFINER = re.compile(r"security\s+definer", re.IGNORECASE)
_MATERIALIZED_VIEW = re.compile(r"create\s+materialized\s+view", re.IGNORECASE)


def find_rls_bypasses(migrations_dir: Path) -> list[str]:
    findings: list[str] = []
    for sql in sorted(migrations_dir.glob("*.sql")):
        text = sql.read_text()
        if _SECURITY_DEFINER.search(text):
            findings.append(f"{sql.name}: SECURITY DEFINER (RLS-bypass risk)")
        if _MATERIALIZED_VIEW.search(text):
            findings.append(f"{sql.name}: MATERIALIZED VIEW (RLS-bypass risk)")
    return findings


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("services/api/migrations")
    findings = find_rls_bypasses(target)
    for f in findings:
        print(f"FORBIDDEN RLS BYPASS: {f}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create the fixture `tigerexchange/services/api/tests/fixtures/bad_migration.sql` (a deliberately-bad file the lint must catch — under `tests/fixtures`, NEVER applied):
```sql
-- FIXTURE ONLY: intentionally violates §7.7. Used by test_rls_lint; never applied.
CREATE MATERIALIZED VIEW own_materials_all AS SELECT * FROM own_materials;

CREATE FUNCTION read_any(_id bigint) RETURNS text
  LANGUAGE sql SECURITY DEFINER AS $$ SELECT title FROM own_materials WHERE id = _id $$;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_rls_lint.py -q && python -m api_scripts.check_rls_bypass services/api/migrations
```
Expected: `3 passed`; the CLI run against the real migrations dir prints nothing and exits 0.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/services/api && git commit -m "feat(api): lint forbidding SECURITY DEFINER / matview RLS bypass over tenant tables

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: FastAPI app — `/health` + tenant-context dependency + demo own-materials route

**Files:** Create `tigerexchange/services/api/src/api/tenant_context.py`, `tigerexchange/services/api/src/api/app.py`, `tigerexchange/services/api/tests/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/api/tests/test_health.py
"""App boots and /health returns 200; tenant-context dependency derives a frozen TenantContext."""
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.tenant_context import tenant_context_from_headers

pytestmark = pytest.mark.unit


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_tenant_context_derived_from_header() -> None:
    ctx = tenant_context_from_headers(x_tenant_id="tenant-A", x_subject_id="sub-1")
    assert ctx.tenant_id == "tenant-A"
    assert ctx.subject_id == "sub-1"
    # PLG-default edition: own-materials only, capped at private (no confidential).
    assert ctx.entitlement.permits_tier_confidential_is_false()


def test_missing_tenant_header_rejected() -> None:
    client = TestClient(create_app())
    resp = client.get("/own-materials")  # no X-Tenant-Id
    assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_health.py -q
```
Expected: `ModuleNotFoundError: No module named 'api.app'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/services/api/src/api/tenant_context.py`:
```python
"""Phase-0 request -> TenantContext derivation.

Phase-0 ships Direct OIDC only (§7.1); here we accept signed headers as the
identity stub. The derived TenantContext defaults to the PLG edition (public +
own-materials, capped at private; confidential/exchange hard-OFF) per §2.3/§7.7.
Real OIDC/CILogon brokering is a later sub-plan; the SHAPE is fixed now.
"""
from __future__ import annotations

from contracts.lattice import Tier
from contracts.tenancy import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
)


def _plg_entitlement() -> Entitlement:
    return Entitlement(
        edition=Edition.PLG,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL, Capability.OWN_MATERIALS}),
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.private,
    )


def tenant_context_from_headers(x_tenant_id: str, x_subject_id: str) -> TenantContext:
    return TenantContext(
        tenant_id=x_tenant_id,
        subject_id=x_subject_id,
        entitlement=_plg_entitlement(),
    )
```

The `test_tenant_context_derived_from_header` test calls `permits_tier_confidential_is_false()`, which is not on the canonical `Entitlement`. To keep the kernel frozen, change that test line before running Step 4 to use the canonical API:
```python
    assert ctx.entitlement.permits_tier(Tier.confidential) is False
```
(and add `from contracts.lattice import Tier` to the test imports). This keeps the assertion identical in intent while using only canonical kernel signatures.

`tigerexchange/services/api/src/api/app.py`:
```python
"""FastAPI app factory: /health + tenant-context dependency + demo own-materials route."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException

from api.config import Settings
from api.db import Database
from api.tenant_context import tenant_context_from_headers
from contracts.tenancy import TenantContext


def _require_tenant(
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_subject_id: Annotated[str | None, Header()] = None,
) -> TenantContext:
    if not x_tenant_id or not x_subject_id:
        raise HTTPException(status_code=401, detail="X-Tenant-Id and X-Subject-Id required")
    return tenant_context_from_headers(x_tenant_id=x_tenant_id, x_subject_id=x_subject_id)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="TigerExchange API", version="0.0.0")
    app.state.settings = settings
    app.state.db = None  # lazily created; /health must not require a DB.

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/own-materials")
    async def own_materials(
        tenant: Annotated[TenantContext, Depends(_require_tenant)],
    ) -> dict[str, object]:
        # Phase-0 walking skeleton: demonstrates the per-request tenant binding path.
        # The DB read runs under tenant_session(SET LOCAL) so RLS scopes it (§7.7).
        if app.state.db is None:
            app.state.db = Database(settings.database_dsn)
        from sqlalchemy import text

        async with app.state.db.tenant_session(tenant.tenant_id) as session:
            rows = (await session.execute(text("SELECT title FROM own_materials"))).scalars().all()
        return {"tenant_id": tenant.tenant_id, "titles": list(rows)}

    return app
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_health.py -q
```
Expected: `3 passed` (the `/own-materials` 401 path needs no DB; the 200 path is covered by the integration RLS test).

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/services/api && git commit -m "feat(api): FastAPI app with /health, tenant-context dependency, tenant-scoped demo route

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13b: DI factory module (`api.dependencies`) — every `get_*` factory the feature modules import

**Files:** Create `tigerexchange/services/api/src/api/dependencies.py`, `tigerexchange/services/api/tests/test_dependencies.py`

This module is **OWNED by 0a** (R6). The later feature sub-plans (0i retrieval, 0k feature modules, etc.) import their wiring from `api.dependencies` — so 0a must define every `get_*` DI factory they reference: `get_pep`, `get_model_router`, `get_lit_retrieval`, `get_draft_store`, `get_discovery`, `get_funding`, `get_audit_sink`, `get_classifier`. In Phase-0 these return **fail-closed not-wired stubs** (a feature module that has not yet provided a concrete impl gets a clear `NotWiredError`, never a silent `None`); each feature plan supplies its real implementation by overriding the factory via FastAPI `app.dependency_overrides[...]`. The factory signatures + names are the frozen seam; the bodies are Phase-0 stubs.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/api/tests/test_dependencies.py
"""api.dependencies (R6): 0a owns every get_* DI factory the feature modules import."""
import pytest

from api import dependencies as deps

pytestmark = pytest.mark.unit

REQUIRED_FACTORIES = [
    "get_pep",
    "get_model_router",
    "get_lit_retrieval",
    "get_draft_store",
    "get_discovery",
    "get_funding",
    "get_audit_sink",
    "get_classifier",
]


def test_every_required_factory_is_defined() -> None:
    for name in REQUIRED_FACTORIES:
        assert hasattr(deps, name), f"api.dependencies missing DI factory {name}"
        assert callable(getattr(deps, name))


def test_unwired_factory_fails_closed_not_none() -> None:
    # Phase-0: a not-yet-wired feature dependency must FAIL CLOSED, never return None.
    with pytest.raises(deps.NotWiredError):
        deps.get_pep()
    with pytest.raises(deps.NotWiredError):
        deps.get_classifier()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_dependencies.py -q
```
Expected: `ModuleNotFoundError: No module named 'api.dependencies'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/services/api/src/api/dependencies.py`:
```python
"""DI factory seam for the API service (R6 — OWNED by 0a).

Feature sub-plans (0i retrieval, 0k feature modules, ...) import their wiring
from `api.dependencies`. 0a defines every get_* factory NAME + signature here so
those imports resolve from day one. Phase-0 bodies are FAIL-CLOSED stubs: an
un-overridden factory raises NotWiredError (never returns None). A feature plan
supplies its concrete impl by setting `app.dependency_overrides[get_x] = ...`
(or by re-binding the factory) when it lands — the kernel Protocols
(IPolicyEnforcement, IModelRouter, IRetrievalStrategy, IAuditSink, IClassifier)
are the typed contract each factory returns.
"""
from __future__ import annotations

from contracts.interfaces import (
    IAuditSink,
    IClassifier,
    IModelRouter,
    IPolicyEnforcement,
    IRetrievalStrategy,
)


class NotWiredError(RuntimeError):
    """Raised when a feature dependency is requested before its plan wired it.

    Fail-closed: Phase-0 ships the seam, not the implementation. A feature plan
    overrides the factory (FastAPI dependency_overrides) when it lands.
    """


def _not_wired(factory: str, owning_plan: str) -> NotWiredError:
    return NotWiredError(
        f"{factory}() is not wired in Phase-0; {owning_plan} provides the concrete "
        f"implementation via app.dependency_overrides[{factory}]."
    )


def get_pep() -> IPolicyEnforcement:
    """PolicyEnforcementPoint (0c owns the concrete impl)."""
    raise _not_wired("get_pep", "0c")


def get_model_router() -> IModelRouter:
    """Classification-routed model router (0f owns the concrete impl)."""
    raise _not_wired("get_model_router", "0f")


def get_lit_retrieval() -> IRetrievalStrategy:
    """Hybrid literature retrieval strategy (0i owns the concrete impl)."""
    raise _not_wired("get_lit_retrieval", "0i")


def get_draft_store() -> object:
    """Confidential draft persistence (0k, single-tenant own-data; depends on 0g)."""
    raise _not_wired("get_draft_store", "0k")


def get_discovery() -> object:
    """Discovery / expertise-fingerprint service (0i/0j own the concrete impl)."""
    raise _not_wired("get_discovery", "0i")


def get_funding() -> object:
    """Funding-lite feature service (0k owns the concrete impl)."""
    raise _not_wired("get_funding", "0k")


def get_audit_sink() -> IAuditSink:
    """Per-stream hash-chained audit sink (0e owns the concrete impl)."""
    raise _not_wired("get_audit_sink", "0e")


def get_classifier() -> IClassifier:
    """Single fail-closed classifier — classification.classifier (0b owns it)."""
    raise _not_wired("get_classifier", "0b")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest services/api/tests/test_dependencies.py -q
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/services/api && git commit -m "feat(api): add 0a-owned api.dependencies DI factory seam (fail-closed get_* stubs)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: CI pipeline (ruff, mypy, import-linter, pytest, kernel fitness/compat, RLS lint)

**Files:** Create `tigerexchange/.github/workflows/ci.yml`, `tigerexchange/tests/test_ci_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/test_ci_config.py
"""CI must run every Phase-0 gate: ruff, mypy, import-linter, pytest, kernel checks, RLS lint."""
from pathlib import Path

import yaml

CI = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def _all_run_steps() -> str:
    doc = yaml.safe_load(CI.read_text())
    steps = []
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if "run" in step:
                steps.append(step["run"])
    return "\n".join(steps)


def test_ci_runs_required_gates() -> None:
    runs = _all_run_steps().lower()
    for gate in [
        "ruff check",
        "mypy",
        "lint-imports",
        "pytest",
        "check_rls_bypass",
    ]:
        assert gate in runs, f"CI missing required gate: {gate}"


def test_ci_has_postgres_service_for_integration() -> None:
    runs = _all_run_steps().lower()
    # integration RLS tests need Docker/testcontainers available on the runner.
    assert "-m integration" in runs or "pytest" in runs
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest tests/test_ci_config.py -q
```
Expected: `FileNotFoundError` — `.github/workflows/ci.yml` does not exist.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/.github/workflows/ci.yml`:
```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - name: Set up Python 3.12
        run: uv python install 3.12
      - name: Sync
        run: uv sync --all-extras
      - name: Lint
        run: uv run ruff check .
      - name: Format check
        run: uv run ruff format --check .
      - name: Type-check
        run: uv run mypy .
      - name: Import-linter (kernel fitness contracts)
        run: uv run lint-imports --config packages/contracts/pyproject.toml
      - name: RLS-bypass lint
        run: uv run python -m api_scripts.check_rls_bypass services/api/migrations
      - name: Unit tests + kernel fitness + kernel compat
        run: uv run pytest -m unit -q
      - name: Kernel contracts suite (fitness + backward/forward compat)
        run: uv run pytest packages/contracts/tests -q

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - name: Set up Python 3.12
        run: uv python install 3.12
      - name: Sync
        run: uv sync --all-extras
      - name: Integration tests (Postgres FORCE-RLS cross-tenant-read-denied)
        run: uv run pytest -m integration -q
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest tests/test_ci_config.py -q
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/.github && git commit -m "ci: add ruff/mypy/import-linter/pytest + kernel fitness/compat + RLS-bypass gates

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: Full local green run (all gates) before the non-code deliverables

**Files:** none (verification task)

- [ ] **Step 1: Write the failing test** — n/a; this task runs the complete suite as the consolidated gate. Treat any red as the "failing test."

- [ ] **Step 2: Run the full local CI sequence**

```bash
cd tigerexchange && uv sync --all-extras
cd tigerexchange && uv run ruff check . && uv run ruff format --check .
cd tigerexchange && uv run mypy .
cd tigerexchange && uv run lint-imports --config packages/contracts/pyproject.toml
cd tigerexchange && uv run python -m api_scripts.check_rls_bypass services/api/migrations
cd tigerexchange && uv run pytest -q
```
Expected: ruff clean, mypy `Success: no issues`, import-linter `Contracts: 1 kept, 0 broken`, RLS lint exit 0, full pytest green (unit + integration if Docker present).

- [ ] **Step 3: Fix any failures** — if ruff/mypy flag issues, address them minimally in the offending file (no behavior change). Re-run the specific failing command until green. (Use superpowers:systematic-debugging if a failure is non-obvious.)

- [ ] **Step 4: Confirm green** — all six commands above pass. This is the deliverable's "boots, health endpoint, SET LOCAL TenantContext, FORCE-RLS cross-tenant-read-denied test passing, contracts importable + versioned, import-linter + fitness check green in CI" acceptance.

- [ ] **Step 5: Commit** (only if Step 3 made changes)

```bash
cd tigerexchange && git add -A && git commit -m "chore: green the full local CI gate sequence

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: Week-1 validation gates sign-off doc (Gate A / Gate B / Q17)

**Files:** Create `tigerexchange/docs/gates/week1-validation.md`, `tigerexchange/tests/test_gate_doc_present.py`

This is a **non-code deliverable** carried by this sub-plan so the build is not committed against unvalidated revenue (§3.3 Gate A/B, Q17). The test enforces the doc exists and contains the required, fillable decision fields; the human GTM founder fills the verdicts.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/test_gate_doc_present.py
"""Week-1 GTM/cost validation gates must exist as a committed, structured sign-off doc."""
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "gates" / "week1-validation.md"


def test_gate_doc_exists() -> None:
    assert DOC.exists(), "Week-1 validation sign-off doc is a required Phase-0 deliverable"


def test_gate_doc_covers_all_required_gates() -> None:
    text = DOC.read_text()
    for required in [
        "Gate A",            # anchor price indication >= $120k vs external comparable
        "Gate B",            # D3 three conditions
        "Q17",               # paid sandbox signs without full review/BAA
        "Line-(a)",          # public-assistant ACV/win-rate + runway stress test
        "PLG-positioning",   # PLG funnel reconciliation
        "VERDICT:",          # each gate carries an explicit verdict field
    ]:
        assert required in text, f"gate doc missing section: {required}"


def test_gate_a_external_comparable_not_cogs() -> None:
    text = DOC.read_text()
    assert "external comparable" in text
    assert "NOT against COGS" in text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest tests/test_gate_doc_present.py -q
```
Expected: `test_gate_doc_exists` fails — doc absent.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/docs/gates/week1-validation.md`:
```markdown
# TigerExchange Phase-0 Week-1 Validation Gates — Sign-off

> These gates run BEFORE engineering commits against revenue (§3.3). All five are
> filled in Week 1 by the GTM founder + counsel. Each carries an explicit VERDICT.
> A failed hard gate triggers the stated pivot, not a silent continuation.

## Gate A — anchor-grant-wedge demand (HARD; §3.3, §16.2, Q1)
Requirement: the anchor center's RD office gives a **written price indication
>= the $120k/yr minimum-viable ACV** against a **named grant-program budget line**,
validated against an **external comparable** (a Cayuse/Kuali research-admin module
ACV or an NIH-center software line item) — **NOT against COGS** — and funds a paid
sandbox pilot.
- Named anchor center / RD office: ____________________
- Named budget line: ____________________
- External comparable cited: ____________________
- Written price indication ($/yr): ____________________
- VERDICT: [ ] PASS  [ ] FAIL  → on FAIL: pivot the wedge before engineering.

## Gate B — federation / cold-start basis (HARD; §3.3, §3.4, D3)
Requirement (D3 three conditions, confirmed in writing):
- (i) existing confidential cross-institution sharing relationship + its legal vehicle (DUA) in force: [ ]
- (ii) N>=2 sites already collaborating: [ ]
- (iii) recurring funded grant need: [ ]
- (iv) named RD/center-admin budget owner: ____________________
- VERDICT: [ ] PASS  [ ] FAIL  → on FAIL: Phase 1 is an independent kill-gate, not an automatic continuation.

## Q17 — CISO sandbox-without-review (HARD Week-1 sub-condition; §19 Q17, R33)
Requirement: named anchor CISO / contracts officer confirms **in writing** that a
paid sandbox pilot can sign **without full vendor security review / BAA**.
- Named CISO / contracts officer: ____________________
- Written confirmation reference: ____________________
- VERDICT: [ ] PASS  [ ] FAIL  → on FAIL: re-baseline runway against full-review cycle.

## Line-(a) ACV / win-rate quantification + runway stress test  (see week1-validation appendix below)
See Section "Line-(a) stress test" in this document (Task 17).

## PLG-positioning resolution  (see resolution below)
See Section "PLG-positioning" in this document (Task 18).
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest tests/test_gate_doc_present.py::test_gate_doc_exists tests/test_gate_doc_present.py::test_gate_a_external_comparable_not_cogs -q
```
Expected: 2 passed (the `test_gate_doc_covers_all_required_gates` will go green once Tasks 17 and 18 append their sections).

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/docs/gates tigerexchange/tests/test_gate_doc_present.py && git commit -m "docs(gates): add Week-1 Gate A/B/Q17 sign-off scaffold + presence test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: Line-(a) ACV / win-rate quantification + 32-month runway stress test (HIGH)

**Files:** Modify `tigerexchange/docs/gates/week1-validation.md`, create `tigerexchange/docs/gates/line_a_runway_stress.py`, `tigerexchange/tests/test_line_a_runway.py`

This folds in the convergence-report HIGH: line-(a) ACV must be quantified at a realistic **$20–60k** (not implicitly $120k) and the 32-month runway stress-tested. We make the stress test an executable model with an asserted invariant so the number cannot silently regress.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/test_line_a_runway.py
"""Line-(a) public-assistant ACV stress test (convergence HIGH): runway modeled at $20-60k, NOT $120k."""
from docs.gates.line_a_runway_stress import (
    LINE_A_ACV_RANGE,
    logos_needed_to_cover_burn,
    runway_months_with_line_a,
)

MONTHLY_BURN = 94_000  # $94k/mo loaded burn (§16.3)
SEED = 3_000_000       # $3.0M seed (§16.3)


def test_line_a_acv_modeled_below_confidential_floor() -> None:
    lo, hi = LINE_A_ACV_RANGE
    assert (lo, hi) == (20_000, 60_000), "line (a) must be stress-tested at $20-60k, not $120k"


def test_logos_needed_at_low_acv_is_quantified() -> None:
    # At $20k ACV, covering $94k/mo = $1.128M/yr needs ~57 logos -> implausible in anchor network.
    assert logos_needed_to_cover_burn(acv=20_000, monthly_burn=MONTHLY_BURN) >= 56
    # At $60k ACV, ~19 logos -> still well above the Phase-0 "2-4 paid sandbox logos" target.
    assert logos_needed_to_cover_burn(acv=60_000, monthly_burn=MONTHLY_BURN) >= 19


def test_phase0_target_logos_do_not_cover_burn_alone() -> None:
    # Phase-0 target is 2-4 line-(a) logos. Stress test: they must NOT be assumed to cover burn;
    # the runway must survive on seed until line (b) lands at month 12-18.
    annual_line_a_revenue = 4 * 60_000  # most optimistic: 4 logos at the TOP of the range
    months = runway_months_with_line_a(
        seed=SEED, monthly_burn=MONTHLY_BURN, annual_line_a_revenue=annual_line_a_revenue
    )
    # Must still exceed the month-18 line-(b) landing milestone with margin.
    assert months >= 18, f"runway under realistic line-(a) does not reach line-(b) at mo 18: {months}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest tests/test_line_a_runway.py -q
```
Expected: `ModuleNotFoundError: No module named 'docs.gates.line_a_runway_stress'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/docs/__init__.py` and `tigerexchange/docs/gates/__init__.py` (empty) so the model is importable, then `tigerexchange/docs/gates/line_a_runway_stress.py`:
```python
"""Line-(a) public-assistant ACV / win-rate + runway stress test (convergence HIGH).

Line (a) = the FAST, undifferentiated public grant-assistant surface (competes vs
Atom $179/mo, Pivot-RP, Instrumentl, free VIVO federation). The plan's runway-survival
claim previously assumed line-(a) logos clear at/near the $120k CONFIDENTIAL floor.
That is competitively implausible. This model stress-tests at a realistic $20-60k ACV
and asserts the runway survives on SEED (not line-(a) revenue) until line (b) lands at
month 12-18.
"""
from __future__ import annotations

import math

# Realistic public-assistant ACV band (NOT the $120k confidential floor).
LINE_A_ACV_RANGE: tuple[int, int] = (20_000, 60_000)


def logos_needed_to_cover_burn(acv: int, monthly_burn: int) -> int:
    """How many line-(a) logos at `acv` are required to cover annualized burn."""
    annual_burn = monthly_burn * 12
    return math.ceil(annual_burn / acv)


def runway_months_with_line_a(
    seed: int, monthly_burn: int, annual_line_a_revenue: int
) -> int:
    """Months of runway: seed drawn down at (burn - line-(a) monthly revenue)."""
    monthly_line_a = annual_line_a_revenue / 12
    net_monthly_burn = monthly_burn - monthly_line_a
    if net_monthly_burn <= 0:
        return 9999  # line-(a) already covers burn (not expected in the realistic band)
    return math.floor(seed / net_monthly_burn)
```

Append the resolution to `tigerexchange/docs/gates/week1-validation.md` (replace the placeholder "Line-(a)" pointer with the full section):

```markdown
## Line-(a) stress test — public-assistant ACV / win-rate (resolves convergence HIGH)

**Decision.** Line (a) (fast undifferentiated public grant-assistant) is modeled at a
realistic **$20-60k ACV**, NOT the $120k confidential floor. At $94k/mo burn ($1.128M/yr):
- $20k ACV -> ~57 logos to cover burn; $60k ACV -> ~19 logos.
- Phase-0 target is **2-4 paid sandbox->production line-(a) logos** -> at most $240k/yr
  (4 x $60k) -> **does NOT cover burn**.

**Consequence (committed).** The runway-survival claim is re-cut: it rests on **seed**
($3.0M), not on line-(a) covering burn. Even at the optimistic 4 x $60k line-(a) revenue,
modeled runway (`runway_months_with_line_a`) **>= 18 months**, clearing the month-12-18
line-(b) confidential-federation close. Line (a) extends runway; it is not the survival
mechanism. If the anchor's known network cannot yield the modeled line-(a) logos, the
runway is re-cut against line (b)'s month-12-18 timeline + a larger seed or a faster
confidential close (§16.3).
- Win-rate assumption to validate in Gate A interviews: ____________________
- Reachable line-(a) logos in anchor network within runway: ____________________
- VERDICT: [ ] runway survives on seed to line-(b) landing  [ ] re-cut required
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest tests/test_line_a_runway.py -q
```
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/docs tigerexchange/tests/test_line_a_runway.py && git commit -m "docs(gates): quantify line-(a) ACV (\$20-60k) and stress-test 32-month runway

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 18: PLG champion-funnel sequencing reconciliation (HIGH) + final gate-doc green

**Files:** Modify `tigerexchange/docs/gates/week1-validation.md`, create `tigerexchange/tests/test_plg_positioning.py`

This folds in the convergence-report HIGH: PLG ships Phase 3 (§18), after the anchor/expansion deals it was framed to feed — so it CANNOT be the Phase-0/1/2 funnel. We commit option (a) from the report: PLG is explicitly NOT the funnel for anchor/Phase-2 deals (those are founder-led direct BD per §16.4); PLG is repositioned as a Phase-3 broad-acquisition/brand surface.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/test_plg_positioning.py
"""PLG-positioning reconciliation (convergence HIGH): PLG is NOT the Phase-0/1/2 funnel."""
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "gates" / "week1-validation.md"


def test_plg_positioning_section_present() -> None:
    text = DOC.read_text()
    assert "PLG-positioning" in text


def test_plg_not_funnel_for_anchor_phase0_1_2() -> None:
    text = DOC.read_text().lower()
    assert "founder-led direct bd" in text
    assert "not a funnel" in text or "not the funnel" in text
    # anchor/expansion deals are founder-led, NOT PLG-seeded.
    assert "phase 3" in text


def test_full_gate_doc_now_complete() -> None:
    # The gate-doc coverage test from Task 16 must be fully green once this section lands.
    text = Path(DOC).read_text()
    for required in ["Gate A", "Gate B", "Q17", "Line-(a)", "PLG-positioning", "VERDICT:"]:
        assert required in text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest tests/test_plg_positioning.py -q
```
Expected: `test_plg_not_funnel_for_anchor_phase0_1_2` fails — the reconciliation text is not yet in the doc.

- [ ] **Step 3: Write minimal implementation**

Append to `tigerexchange/docs/gates/week1-validation.md`:
```markdown
## PLG-positioning — champion-funnel sequencing reconciliation (resolves convergence HIGH)

**Inconsistency.** PLG ($179/mo) was framed as a "champion-seeding top-of-funnel" that
"seeds champions inside target consortia," but PLG ships in **Phase 3** (§18) — AFTER the
anchor land (Phase 0-1) and the first cross-buyer expansion (Phase 2). It therefore cannot
have seeded any champion during the window the anchor/expansion deals must close.

**Resolution (committed — option (a)).** PLG is **NOT a funnel** for the anchor or Phase-2
expansion deals. Those are **founder-led direct BD** (§16.4): two Week-1 kill-gates +
founder-led 6-9-month first close + consortium-director/CTSA/Big-Ten + Cayuse/Kuali
integration partnerships (§1). The "seeds champions inside target consortia" claim is
withdrawn for Phases 0-2. PLG is repositioned as a **Phase-3 broad-acquisition / brand
surface only** (D7: explicit loss-leader top-of-funnel for the LATER broad motion), running
on the §7.7-isolated pooled plane (public + own-materials, confidential/exchange hard-OFF).
- Stakeholder sign-off that PLG is loss-leader / Phase-3-only, not Phase-0-2 funnel: ______
- VERDICT: [ ] reconciled (PLG = Phase-3 brand surface, founder-led BD owns anchor/expansion)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest tests/test_plg_positioning.py tests/test_gate_doc_present.py -q
```
Expected: all gate-doc tests green, including `test_gate_doc_covers_all_required_gates` from Task 16.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add tigerexchange/docs tigerexchange/tests/test_plg_positioning.py && git commit -m "docs(gates): reconcile PLG as Phase-3 brand surface (NOT Phase-0/1/2 champion funnel)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 19: Final acceptance sweep — deliverable checklist green

**Files:** none (verification task; use superpowers:verification-before-completion)

- [ ] **Step 1: Run the entire suite and every CI gate locally**

```bash
cd tigerexchange && uv run ruff check . && uv run ruff format --check . && uv run mypy . \
  && uv run lint-imports --config packages/contracts/pyproject.toml \
  && uv run python -m api_scripts.check_rls_bypass services/api/migrations \
  && uv run pytest -q
```

- [ ] **Step 2: Verify each deliverable line item against output**
  - [ ] FastAPI service boots + `/health` 200 (`test_health.py`).
  - [ ] Per-request TenantContext via `SET LOCAL` on a transaction-scoped connection (`test_db_set_local.py`).
  - [ ] FORCE-RLS cross-tenant-read-denied: RESTRICTIVE + WITH CHECK + tenant_id-leading index, BOLA-by-id denied, no SECURITY DEFINER/matview bypass (`test_rls_isolation.py`, `test_rls_lint.py`).
  - [ ] `contracts` importable + versioned (`KERNEL_API_VERSION`), per-interface intra-cell/cross-node locus declared, backward+forward compat check green (`test_kernel_compat.py`, `test_interfaces.py`).
  - [ ] import-linter + kernel fan-in/size fitness green (`lint-imports`, `test_kernel_fitness.py`).
  - [ ] 0a-owned `api.dependencies` DI seam defines every `get_*` factory the feature modules import, fail-closed when un-wired (`test_dependencies.py`).
  - [ ] Gate A/B/Q17 sign-off doc + line-(a) ACV/burn stress test + PLG positioning committed (`test_gate_doc_present.py`, `test_line_a_runway.py`, `test_plg_positioning.py`).

- [ ] **Step 3: Fix any gap** — if any checklist item is not backed by green output, return to the owning task and resolve before claiming completion. Do not assert completion without the command output as evidence.

- [ ] **Step 4: Confirm the walking skeleton is the clean seam for later plans** — kernel deferred stubs (`IExchangeFeed`, `IRevocationAuthority`) are present and Phase-1+ documented; no Phase-0 implementation of confidential sharing/revocation/federation exists (DEFER scope honored).

- [ ] **Step 5: Final commit (if Step 3 changed anything)**

```bash
cd tigerexchange && git add -A && git commit -m "chore: Phase-0 foundation acceptance sweep green

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```