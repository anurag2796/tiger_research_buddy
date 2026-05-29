The sub-plans haven't been written yet (this is the first one being authored). I have the canonical kernel contracts verbatim in my prompt and full spec detail. I have everything needed to write the complete plan. Let me produce it.

```markdown
# Central-Index Read PEP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the central-index read PEP that authorizes discovery READS (deny-by-default per-query authz, first-class `discoverability_scope` enforcement, aggregate treated as at-least-private-tier with at-rest control-plane encryption) and closes the share-correctness gap so a projection is only ever queryable at a scope the owner has durably committed (monotonic scope-epoch), never a stale-HIGH cached scope.

**Architecture:** A read-path PEP (same `IPolicyEnforcement` code/policy engine as the cell-local PEP, selected by `PepAction.DISCOVER`) sits in front of an at-rest-encrypted central index of `PublishableProjection` rows. An owner-authoritative `ScopeRegistry` durably commits each projection's `discoverability_scope` under a monotonic per-projection scope-epoch at emit time; the PEP evaluates every query against that owner-committed scope (never a record-cached scope), filters by requester identity + consortium membership, and returns fail-closed `PepResponse` objects. The index is encrypted at rest under control-plane keys distinct from tenant keys (§11.2b).

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Postgres + FORCE ROW LEVEL SECURITY (the encrypted central index table), the canonical `contracts` kernel package, Fernet (AES) for control-plane-key at-rest envelope encryption, Hypothesis for the property test, pytest/ruff/mypy.

**Depends on:** `0a-foundation`, `0c-pep-broker-chokepoint`, `0d-identity-entitlement`

---

## File Structure

| File | Created/Modified | Single Responsibility |
|---|---|---|
| `tigerexchange/packages/contracts/src/contracts/discovery.py` | Create | `DiscoveryQuery` + `ScopeCommit` + `ScopeEpochTooOld` kernel types for the discovery read path and owner scope-epoch (extends the kernel seam, zero feature deps) |
| `tigerexchange/packages/contracts/src/contracts/__init__.py` | Modify | Export the new discovery kernel symbols on the single import surface |
| `tigerexchange/services/central_index/__init__.py` | Create | Package marker for the central-index service |
| `tigerexchange/services/central_index/scope_lattice.py` | Create | Total ordering over `DiscoverabilityScope` (`scope_rank`, `scope_wider_than`) — the "wider-than" comparator the share-correctness gate uses |
| `tigerexchange/services/central_index/scope_registry.py` | Create | Owner-authoritative, strongly-consistent scope store: `commit_scope` (durable monotonic-epoch commit at emit time) + `current_scope` (the value the PEP reads) |
| `tigerexchange/services/central_index/encryption.py` | Create | At-rest control-plane-key envelope encryption of index rows (keys distinct from tenant keys, §11.2b) |
| `tigerexchange/services/central_index/index_store.py` | Create | The encrypted central index: store/query `PublishableProjection` rows; ciphertext at rest under control-plane key; never stores the authoritative scope (reads it from the registry) |
| `tigerexchange/services/central_index/read_pep.py` | Create | `CentralIndexReadPEP` implementing `IPolicyEnforcement`: per-query authz (deny-by-default), scope filtering against owner-committed scope-epoch, aggregate-query rate-limit, fail-closed `PepResponse` |
| `tigerexchange/services/central_index/migrations/0001_central_index.sql` | Create | DDL for `central_index_projection` (ciphertext + scope-epoch) and `scope_commit` tables with FORCE RLS |
| `tigerexchange/services/central_index/tests/__init__.py` | Create | Test package marker |
| `tigerexchange/services/central_index/tests/conftest.py` | Create | Shared fixtures: tenants (member/non-member), entitlements, control-plane key, in-memory wiring |
| `tigerexchange/services/central_index/tests/test_scope_lattice.py` | Create | Tests for the scope ordering / wider-than comparator |
| `tigerexchange/services/central_index/tests/test_scope_registry.py` | Create | Tests for durable monotonic scope-epoch commit + current-scope read |
| `tigerexchange/services/central_index/tests/test_encryption.py` | Create | Tests for control-plane-key at-rest round-trip + key-distinctness |
| `tigerexchange/services/central_index/tests/test_read_pep_authz.py` | Create | Tests: deny-by-default non-member; named-tenants allowlist; named-consortium; anonymous→public-web only |
| `tigerexchange/services/central_index/tests/test_read_pep_scope_consistency.py` | Create | Test: PEP serves owner-committed (not record-cached) scope; stale-HIGH cached scope never honored |
| `tigerexchange/services/central_index/tests/test_share_correctness_property.py` | Create | Hypothesis property test: no projection ever queryable at a scope wider than the owner's currently-committed scope, across version-skew and replay |

---

## Tasks

### Task 1: Discovery kernel types (`DiscoveryQuery`, `ScopeCommit`, `ScopeEpochTooOld`)

**Files:**
- Create `tigerexchange/packages/contracts/src/contracts/discovery.py`
- Modify `tigerexchange/packages/contracts/src/contracts/__init__.py`
- Test `tigerexchange/packages/contracts/src/contracts/tests/test_discovery.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/packages/contracts/src/contracts/tests/test_discovery.py`:

```python
"""Kernel-level tests for the discovery read-path types (plan §4.7, §10.3)."""

import pytest
from pydantic import ValidationError

from contracts import (
    DiscoverabilityScope,
    DiscoveryQuery,
    ScopeCommit,
    ScopeEpochTooOld,
)
from contracts.tenancy import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
)
from contracts.lattice import Tier


def _tenant() -> TenantContext:
    ent = Entitlement(
        edition=Edition.INSTITUTIONAL,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL}),
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.private,
    )
    return TenantContext(tenant_id="t1", subject_id="s1", entitlement=ent)


def test_discovery_query_is_frozen():
    q = DiscoveryQuery(query_id="q1", requester=_tenant(), query_text="graph ml", top_k=5)
    with pytest.raises(ValidationError):
        q.query_text = "mutated"


def test_discovery_query_defaults_top_k():
    q = DiscoveryQuery(query_id="q1", requester=_tenant(), query_text="x")
    assert q.top_k == 50


def test_anonymous_query_has_no_requester():
    q = DiscoveryQuery(query_id="q2", requester=None, query_text="x")
    assert q.requester is None


def test_scope_commit_carries_monotonic_epoch_and_is_frozen():
    c = ScopeCommit(
        projection_id="p1",
        owner_tenant_id="t1",
        scope=DiscoverabilityScope.NAMED_CONSORTIUM,
        scope_epoch=7,
        named_tenant_allowlist=frozenset(),
        consortium_ids=frozenset({"c1"}),
    )
    assert c.scope_epoch == 7
    with pytest.raises(ValidationError):
        c.scope = DiscoverabilityScope.PUBLIC_WEB


def test_scope_commit_rejects_negative_epoch():
    with pytest.raises(ValidationError):
        ScopeCommit(
            projection_id="p1",
            owner_tenant_id="t1",
            scope=DiscoverabilityScope.NONE,
            scope_epoch=-1,
        )


def test_scope_epoch_too_old_is_an_exception():
    err = ScopeEpochTooOld(projection_id="p1", attempted=3, committed=5)
    assert isinstance(err, Exception)
    assert "p1" in str(err)
    assert "3" in str(err) and "5" in str(err)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/packages/contracts/src/contracts/tests/test_discovery.py -q
```

Expected failure: `ImportError: cannot import name 'DiscoveryQuery' from 'contracts'` (the module and exports do not exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/packages/contracts/src/contracts/discovery.py`:

```python
"""Discovery read-path kernel types (plan §4.7, §10.3, share-correctness HIGH).

K-seam for the central-index read PEP. A DiscoveryQuery is the request shape a
discovery READ carries (requester may be None for anonymous queries → only
public-web records are visible, §4.7). A ScopeCommit is the OWNER-AUTHORITATIVE,
durably-committed discoverability_scope of a projection, carrying a monotonic
per-projection scope-epoch: the central-index PEP evaluates scope against THIS
value (never a record-cached scope), so a projection is only queryable at a
scope the owner has currently committed (the additive counterpart to the
revocation gate, §10.3). ScopeEpochTooOld is raised when a lower-epoch scope
apply is attempted (monotonic, replay-safe).

Zero feature deps, no persistence — pure kernel types.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from contracts.classification import DiscoverabilityScope
from contracts.tenancy import TenantContext


class DiscoveryQuery(BaseModel):
    """A discovery READ request evaluated by the central-index PEP (§4.7).

    Frozen for the request's lifetime so no downstream code re-scopes an
    in-flight query. ``requester is None`` denotes an anonymous/unauthenticated
    query, which the PEP restricts to public-web-scoped records (§4.7).
    """

    model_config = ConfigDict(frozen=True)

    query_id: str
    requester: TenantContext | None
    query_text: str
    top_k: int = Field(default=50, ge=1, le=500)


class ScopeCommit(BaseModel):
    """Owner-authoritative, durably-committed discoverability_scope of a
    projection, with a monotonic per-projection scope-epoch (§4.7, §10.3).

    This is the value the central-index PEP evaluates against — never a scope
    cached on the index row. A projection becomes discoverable at ``scope`` only
    after the owner durably commits this record. Frozen: a committed scope is an
    immutable, epoch-stamped fact; widening/narrowing is a NEW commit at a
    higher epoch.
    """

    model_config = ConfigDict(frozen=True)

    projection_id: str
    owner_tenant_id: str
    scope: DiscoverabilityScope
    # Monotonic per-projection scope version. A higher epoch supersedes lower.
    scope_epoch: int = Field(..., ge=0)
    # For NAMED_TENANTS scope: the explicit tenant-id allowlist (§4.7).
    named_tenant_allowlist: frozenset[str] = Field(default_factory=frozenset)
    # For NAMED_CONSORTIUM scope: the owner's consortium ids the record is
    # discoverable within (§4.7).
    consortium_ids: frozenset[str] = Field(default_factory=frozenset)


class ScopeEpochTooOld(Exception):
    """Raised when a scope commit/apply at an epoch <= the committed epoch is
    attempted. Enforces monotonicity so replays cannot resurrect a stale-HIGH
    scope (§10.3 monotonic applier)."""

    def __init__(self, projection_id: str, attempted: int, committed: int) -> None:
        self.projection_id = projection_id
        self.attempted = attempted
        self.committed = committed
        super().__init__(
            f"scope-epoch too old for projection {projection_id}: "
            f"attempted={attempted} <= committed={committed}"
        )
```

Then add the exports to `tigerexchange/packages/contracts/src/contracts/__init__.py`. Add this import block alongside the existing ones:

```python
from contracts.discovery import DiscoveryQuery, ScopeCommit, ScopeEpochTooOld
```

And add these entries to the existing `__all__` list:

```python
    # discovery read-path seam (§4.7, §10.3)
    "DiscoveryQuery", "ScopeCommit", "ScopeEpochTooOld",
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/packages/contracts/src/contracts/tests/test_discovery.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/packages/contracts/src/contracts/discovery.py \
        tigerexchange/packages/contracts/src/contracts/__init__.py \
        tigerexchange/packages/contracts/src/contracts/tests/test_discovery.py
git commit -m "feat(contracts): add discovery read-path kernel types (DiscoveryQuery, ScopeCommit, ScopeEpochTooOld)

Adds the §4.7/§10.3 discovery seam: DiscoveryQuery (anonymous-capable),
ScopeCommit (owner-authoritative scope + monotonic scope-epoch), and
ScopeEpochTooOld for replay-safe monotonicity.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Scope lattice — the "wider-than" comparator

**Files:**
- Create `tigerexchange/services/central_index/__init__.py`
- Create `tigerexchange/services/central_index/scope_lattice.py`
- Create `tigerexchange/services/central_index/tests/__init__.py`
- Test `tigerexchange/services/central_index/tests/test_scope_lattice.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_scope_lattice.py`:

```python
"""Tests for the DiscoverabilityScope ordering (plan §4.7).

Ordering by audience breadth (NONE narrowest, PUBLIC_WEB widest) is what the
share-correctness gate uses to assert 'never served wider than committed'.
"""

from contracts import DiscoverabilityScope
from central_index.scope_lattice import scope_rank, scope_wider_than


def test_total_order_by_breadth():
    ordered = [
        DiscoverabilityScope.NONE,
        DiscoverabilityScope.NAMED_TENANTS,
        DiscoverabilityScope.NAMED_CONSORTIUM,
        DiscoverabilityScope.FEDERATION_WIDE,
        DiscoverabilityScope.PUBLIC_WEB,
    ]
    ranks = [scope_rank(s) for s in ordered]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)  # strict total order, no ties


def test_public_web_is_widest():
    for s in DiscoverabilityScope:
        assert scope_rank(s) <= scope_rank(DiscoverabilityScope.PUBLIC_WEB)


def test_none_is_narrowest():
    for s in DiscoverabilityScope:
        assert scope_rank(s) >= scope_rank(DiscoverabilityScope.NONE)


def test_wider_than_is_strict():
    assert scope_wider_than(
        DiscoverabilityScope.FEDERATION_WIDE, DiscoverabilityScope.NAMED_CONSORTIUM
    )
    assert not scope_wider_than(
        DiscoverabilityScope.NAMED_CONSORTIUM, DiscoverabilityScope.FEDERATION_WIDE
    )
    assert not scope_wider_than(
        DiscoverabilityScope.NONE, DiscoverabilityScope.NONE
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_scope_lattice.py -q
```

Expected failure: `ModuleNotFoundError: No module named 'central_index.scope_lattice'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/central_index/__init__.py`:

```python
"""Central-index service: read PEP + encrypted index + owner-authoritative scope
registry (plan §4.7, §11.2, §11.2b, §10.3)."""
```

Create `tigerexchange/services/central_index/tests/__init__.py`:

```python
```

Create `tigerexchange/services/central_index/scope_lattice.py`:

```python
"""Total ordering over DiscoverabilityScope by audience breadth (plan §4.7).

A higher rank = a WIDER audience. The central-index PEP's share-correctness gate
uses ``scope_wider_than`` to guarantee a projection is never served at a scope
WIDER than the owner's currently-committed scope (the additive counterpart to
the revocation gate, §10.3). Unknown values fail closed to NONE (narrowest).
"""

from __future__ import annotations

from contracts import DiscoverabilityScope

# Audience-breadth ordering: NONE narrowest .. PUBLIC_WEB widest.
_RANK: dict[DiscoverabilityScope, int] = {
    DiscoverabilityScope.NONE: 0,
    DiscoverabilityScope.NAMED_TENANTS: 1,
    DiscoverabilityScope.NAMED_CONSORTIUM: 2,
    DiscoverabilityScope.FEDERATION_WIDE: 3,
    DiscoverabilityScope.PUBLIC_WEB: 4,
}


def scope_rank(scope: DiscoverabilityScope) -> int:
    """Audience-breadth rank of ``scope``. Unknown → NONE rank (fail-closed)."""
    return _RANK.get(scope, _RANK[DiscoverabilityScope.NONE])


def scope_wider_than(a: DiscoverabilityScope, b: DiscoverabilityScope) -> bool:
    """True iff ``a`` exposes a STRICTLY WIDER audience than ``b``."""
    return scope_rank(a) > scope_rank(b)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_scope_lattice.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/__init__.py \
        tigerexchange/services/central_index/scope_lattice.py \
        tigerexchange/services/central_index/tests/__init__.py \
        tigerexchange/services/central_index/tests/test_scope_lattice.py
git commit -m "feat(central-index): add DiscoverabilityScope breadth ordering + wider-than comparator

scope_rank/scope_wider_than provide the strict total order the share-correctness
gate uses to forbid serving wider than the owner's committed scope (§4.7).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Owner-authoritative ScopeRegistry (durable monotonic scope-epoch commit)

**Files:**
- Create `tigerexchange/services/central_index/scope_registry.py`
- Test `tigerexchange/services/central_index/tests/test_scope_registry.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_scope_registry.py`:

```python
"""Tests for the owner-authoritative scope registry (plan §4.7, §10.3).

The registry is the single source of truth for a projection's CURRENTLY-COMMITTED
discoverability_scope. The central-index PEP reads scope from HERE, not from a
cached index row. Commits are durable + monotonic per scope-epoch.
"""

import pytest

from contracts import DiscoverabilityScope, ScopeCommit, ScopeEpochTooOld
from central_index.scope_registry import ScopeRegistry


def _commit(epoch: int, scope: DiscoverabilityScope, **kw) -> ScopeCommit:
    return ScopeCommit(
        projection_id="p1",
        owner_tenant_id="t1",
        scope=scope,
        scope_epoch=epoch,
        **kw,
    )


def test_unknown_projection_current_scope_is_none():
    reg = ScopeRegistry()
    # Deny-by-default: never-committed projection is treated as NONE (§4.7).
    assert reg.current_scope("missing") is None


def test_commit_then_read_back():
    reg = ScopeRegistry()
    reg.commit_scope(_commit(1, DiscoverabilityScope.NAMED_CONSORTIUM,
                             consortium_ids=frozenset({"c1"})))
    current = reg.current_scope("p1")
    assert current is not None
    assert current.scope is DiscoverabilityScope.NAMED_CONSORTIUM
    assert current.scope_epoch == 1
    assert current.consortium_ids == frozenset({"c1"})


def test_higher_epoch_supersedes():
    reg = ScopeRegistry()
    reg.commit_scope(_commit(1, DiscoverabilityScope.FEDERATION_WIDE))
    reg.commit_scope(_commit(2, DiscoverabilityScope.NAMED_CONSORTIUM,
                             consortium_ids=frozenset({"c1"})))
    current = reg.current_scope("p1")
    assert current.scope is DiscoverabilityScope.NAMED_CONSORTIUM
    assert current.scope_epoch == 2


def test_lower_or_equal_epoch_rejected_monotonic():
    reg = ScopeRegistry()
    reg.commit_scope(_commit(5, DiscoverabilityScope.NAMED_CONSORTIUM))
    # Replay of an OLD widening commit must NOT resurrect a stale-HIGH scope.
    with pytest.raises(ScopeEpochTooOld):
        reg.commit_scope(_commit(3, DiscoverabilityScope.PUBLIC_WEB))
    with pytest.raises(ScopeEpochTooOld):
        reg.commit_scope(_commit(5, DiscoverabilityScope.PUBLIC_WEB))
    # The committed value is unchanged.
    assert reg.current_scope("p1").scope is DiscoverabilityScope.NAMED_CONSORTIUM
    assert reg.current_scope("p1").scope_epoch == 5


def test_commit_is_durable_across_reinstantiation_via_shared_backend():
    backend: dict[str, ScopeCommit] = {}
    reg1 = ScopeRegistry(store=backend)
    reg1.commit_scope(_commit(1, DiscoverabilityScope.NAMED_TENANTS,
                              named_tenant_allowlist=frozenset({"t2"})))
    # A fresh registry over the same durable backend sees the committed scope.
    reg2 = ScopeRegistry(store=backend)
    assert reg2.current_scope("p1").named_tenant_allowlist == frozenset({"t2"})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_scope_registry.py -q
```

Expected failure: `ModuleNotFoundError: No module named 'central_index.scope_registry'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/central_index/scope_registry.py`:

```python
"""Owner-authoritative discoverability-scope registry (plan §4.7, §10.3).

This is the single source of truth for a projection's CURRENTLY-COMMITTED
discoverability_scope. ``commit_scope`` is the emit-time, strongly-consistent,
DURABLE write the owner performs before a projection is discoverable;
``current_scope`` is the value the central-index PEP reads at query time. The
PEP NEVER trusts a scope cached on an index row — it resolves scope HERE, so a
projection is only queryable at a scope the owner has currently committed.

Monotonicity: a commit at epoch <= the committed epoch raises ScopeEpochTooOld,
so a replayed OLD widening event cannot resurrect a stale-HIGH scope (§10.3).

Phase-0 backend is an injectable dict (the durable store seam). The Postgres-
backed durable store (Task 8 DDL) plugs into the SAME ``store`` mapping
interface; the registry semantics (monotonic, read-your-writes) are identical.
"""

from __future__ import annotations

from typing import MutableMapping

from contracts import ScopeCommit, ScopeEpochTooOld


class ScopeRegistry:
    """Strongly-consistent owner-authoritative scope store (read-your-writes)."""

    def __init__(self, store: MutableMapping[str, ScopeCommit] | None = None) -> None:
        # Maps projection_id -> latest committed ScopeCommit. Injectable so a
        # durable (Postgres) backend can be supplied; default in-memory dict.
        self._store: MutableMapping[str, ScopeCommit] = store if store is not None else {}

    def commit_scope(self, commit: ScopeCommit) -> ScopeCommit:
        """Durably commit a projection's scope at a strictly-higher epoch.

        Raises ScopeEpochTooOld if ``commit.scope_epoch`` is not strictly above
        the currently-committed epoch (monotonic; replay-safe).
        """
        existing = self._store.get(commit.projection_id)
        if existing is not None and commit.scope_epoch <= existing.scope_epoch:
            raise ScopeEpochTooOld(
                projection_id=commit.projection_id,
                attempted=commit.scope_epoch,
                committed=existing.scope_epoch,
            )
        self._store[commit.projection_id] = commit
        return commit

    def current_scope(self, projection_id: str) -> ScopeCommit | None:
        """The owner's currently-committed scope, or None if never committed.

        None is deny-by-default: a projection with no committed scope is
        invisible to every requester (§4.7).
        """
        return self._store.get(projection_id)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_scope_registry.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/scope_registry.py \
        tigerexchange/services/central_index/tests/test_scope_registry.py
git commit -m "feat(central-index): owner-authoritative ScopeRegistry with durable monotonic scope-epoch

commit_scope is the emit-time strongly-consistent durable write; current_scope
is what the PEP reads. Monotonic epoch rejects replayed stale-HIGH widening
(§4.7, §10.3).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: At-rest control-plane-key encryption (keys distinct from tenant keys)

**Files:**
- Create `tigerexchange/services/central_index/encryption.py`
- Test `tigerexchange/services/central_index/tests/test_encryption.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_encryption.py`:

```python
"""Tests for at-rest control-plane-key encryption of the central index (§11.2b).

The aggregate is treated as at-least-private-tier and encrypted at rest under
CONTROL-PLANE keys DISTINCT from tenant keys: an index compromise must not
surrender tenant KEKs, and tenant crypto-shred must not depend on the index.
"""

import json

import pytest
from cryptography.fernet import Fernet, InvalidToken

from central_index.encryption import ControlPlaneCipher


def test_round_trip():
    cipher = ControlPlaneCipher(Fernet.generate_key())
    payload = {"projection_id": "p1", "fields": {"title": "Graph ML"}}
    blob = cipher.encrypt_fields(payload)
    assert isinstance(blob, bytes)
    assert b"Graph ML" not in blob  # ciphertext, not plaintext at rest
    assert cipher.decrypt_fields(blob) == payload


def test_decrypt_with_tenant_key_fails_key_distinctness():
    control_plane_key = Fernet.generate_key()
    tenant_key = Fernet.generate_key()
    assert control_plane_key != tenant_key
    cipher = ControlPlaneCipher(control_plane_key)
    blob = cipher.encrypt_fields({"x": 1})
    # A tenant key CANNOT decrypt the index — keys are distinct (§11.2b).
    with pytest.raises(InvalidToken):
        Fernet(tenant_key).decrypt(blob)


def test_roundtrip_preserves_unicode_and_nesting():
    cipher = ControlPlaneCipher(Fernet.generate_key())
    payload = {"a": {"b": ["é", "中文", 3]}}
    assert cipher.decrypt_fields(cipher.encrypt_fields(payload)) == payload
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_encryption.py -q
```

Expected failure: `ModuleNotFoundError: No module named 'central_index.encryption'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/central_index/encryption.py`:

```python
"""At-rest control-plane-key encryption for the central index (plan §11.2b).

The shared central index aggregate is mosaic-sensitive and is treated as
at-least-private-tier; it is encrypted at rest under CONTROL-PLANE keys that are
DISTINCT from tenant keys (§11.2b). Two consequences enforced by construction:
  - An index compromise does NOT surrender any tenant KEK (the cipher here only
    ever holds the control-plane key).
  - Tenant KEK crypto-shred does NOT depend on the index (the index never holds
    confidential content per D6, and never holds a tenant key).

Phase-0 uses Fernet (AES-128-CBC + HMAC) as the symmetric envelope; the
control-plane key is supplied by the deployment's KMS/secret store. The Postgres
column stores the resulting ciphertext bytes.
"""

from __future__ import annotations

import json

from cryptography.fernet import Fernet


class ControlPlaneCipher:
    """Encrypts/decrypts index field payloads under a control-plane key."""

    def __init__(self, control_plane_key: bytes) -> None:
        # control_plane_key is a Fernet key from the CONTROL-PLANE secret store.
        # It is NEVER a tenant key (§11.2b key-distinctness is a deployment
        # invariant; this class only ever sees the control-plane key).
        self._fernet = Fernet(control_plane_key)

    def encrypt_fields(self, fields: dict[str, object]) -> bytes:
        """Encrypt a projection's field payload to at-rest ciphertext bytes."""
        plaintext = json.dumps(fields, separators=(",", ":"), ensure_ascii=False)
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt_fields(self, blob: bytes) -> dict[str, object]:
        """Decrypt at-rest ciphertext back to the field payload dict."""
        plaintext = self._fernet.decrypt(blob)
        return json.loads(plaintext.decode("utf-8"))
```

Ensure `cryptography` is a dependency of the central-index service. Add it to the service's `pyproject.toml`/requirements (`cryptography>=42`).

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_encryption.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/encryption.py \
        tigerexchange/services/central_index/tests/test_encryption.py
git commit -m "feat(central-index): at-rest control-plane-key encryption (keys distinct from tenant keys)

ControlPlaneCipher encrypts index field payloads under the control-plane key;
tenant keys cannot decrypt the index (§11.2b key-distinctness).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Encrypted index store (rows hold ciphertext + scope-epoch, NOT authoritative scope)

**Files:**
- Create `tigerexchange/services/central_index/index_store.py`
- Test `tigerexchange/services/central_index/tests/test_index_store.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_index_store.py`:

```python
"""Tests for the encrypted central index store (plan §4.7, §11.2b, §6.1).

The index row holds CIPHERTEXT (at rest) + the projection's owner_tenant_id +
the scope-epoch the row was last applied under. It deliberately does NOT hold
the authoritative discoverability_scope — that is resolved at query time from
the ScopeRegistry so a record can never serve a stale-HIGH cached scope.
"""

import pytest
from cryptography.fernet import Fernet

from contracts import PublishableProjection
from contracts.lattice import Tier
from contracts.classification import DiscoverabilityScope
from central_index.encryption import ControlPlaneCipher
from central_index.index_store import EncryptedIndexStore, IndexedRow


def _proj(pid: str, tenant: str, title: str) -> PublishableProjection:
    return PublishableProjection(
        projection_id=pid,
        artifact_id="a-" + pid,
        owner_tenant_id=tenant,
        tier=Tier.public,
        discoverability_scope=DiscoverabilityScope.FEDERATION_WIDE,
        fields={"title": title},
    )


def test_apply_then_query_returns_decrypted_fields():
    store = EncryptedIndexStore(ControlPlaneCipher(Fernet.generate_key()))
    store.apply(_proj("p1", "t1", "Graph ML"), scope_epoch=1)
    hits = store.query("graph", top_k=10)
    assert len(hits) == 1
    assert hits[0].projection_id == "p1"
    assert hits[0].owner_tenant_id == "t1"
    assert hits[0].fields == {"title": "Graph ML"}
    assert hits[0].applied_scope_epoch == 1


def test_query_is_a_naive_substring_match_over_decrypted_fields():
    store = EncryptedIndexStore(ControlPlaneCipher(Fernet.generate_key()))
    store.apply(_proj("p1", "t1", "Graph ML"), scope_epoch=1)
    store.apply(_proj("p2", "t2", "Quantum"), scope_epoch=1)
    assert {h.projection_id for h in store.query("graph", top_k=10)} == {"p1"}
    assert {h.projection_id for h in store.query("quantum", top_k=10)} == {"p2"}


def test_confidential_projection_cannot_be_constructed_d6():
    # D6 is enforced in the kernel; the index can never receive a confidential row.
    with pytest.raises(Exception):
        PublishableProjection(
            projection_id="p1",
            artifact_id="a1",
            owner_tenant_id="t1",
            tier=Tier.confidential,
            discoverability_scope=DiscoverabilityScope.FEDERATION_WIDE,
            fields={},
        )


def test_apply_is_monotonic_rejects_lower_epoch():
    store = EncryptedIndexStore(ControlPlaneCipher(Fernet.generate_key()))
    store.apply(_proj("p1", "t1", "v2"), scope_epoch=5)
    # Replayed lower-epoch apply must not overwrite (§10.3 monotonic applier).
    store.apply(_proj("p1", "t1", "stale"), scope_epoch=3)
    hits = store.query("v2", top_k=10)
    assert len(hits) == 1 and hits[0].applied_scope_epoch == 5
    assert store.query("stale", top_k=10) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_index_store.py -q
```

Expected failure: `ModuleNotFoundError: No module named 'central_index.index_store'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/central_index/index_store.py`:

```python
"""Encrypted central index store (plan §4.7, §11.2b, §10.3).

Stores PublishableProjection rows as CIPHERTEXT at rest (control-plane key),
keyed by projection_id, carrying owner_tenant_id + the scope-epoch the row was
last applied under. The applier is MONOTONIC: a lower-epoch apply is ignored so
replays/snapshots cannot resurrect a superseded row (§10.3).

Critically, the row does NOT store the authoritative discoverability_scope. The
PEP resolves scope from the ScopeRegistry at query time, so the index can never
serve a stale-HIGH cached scope (share-correctness HIGH).

Phase-0 retrieval is a naive decrypted-substring match (the real hybrid
vector+BM25+RRF path lands in the retrieval sub-plan behind IRetrievalStrategy);
this store's contract is: decrypt, match, hand candidate rows to the PEP.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts import PublishableProjection
from central_index.encryption import ControlPlaneCipher


@dataclass(frozen=True)
class IndexedRow:
    """A decrypted candidate row handed to the PEP for scope authorization."""

    projection_id: str
    owner_tenant_id: str
    applied_scope_epoch: int
    fields: dict[str, object]


@dataclass
class _StoredRow:
    owner_tenant_id: str
    applied_scope_epoch: int
    ciphertext: bytes


class EncryptedIndexStore:
    """At-rest-encrypted store of publishable projections (§11.2b)."""

    def __init__(self, cipher: ControlPlaneCipher) -> None:
        self._cipher = cipher
        self._rows: dict[str, _StoredRow] = {}

    def apply(self, projection: PublishableProjection, *, scope_epoch: int) -> None:
        """Idempotent, MONOTONIC upsert of a projection row at ``scope_epoch``.

        A lower-or-equal epoch apply is ignored (replay-safe, §10.3).
        """
        existing = self._rows.get(projection.projection_id)
        if existing is not None and scope_epoch <= existing.applied_scope_epoch:
            return
        self._rows[projection.projection_id] = _StoredRow(
            owner_tenant_id=projection.owner_tenant_id,
            applied_scope_epoch=scope_epoch,
            ciphertext=self._cipher.encrypt_fields(dict(projection.fields)),
        )

    def query(self, query_text: str, *, top_k: int) -> list[IndexedRow]:
        """Naive decrypted-substring candidate retrieval (Phase-0).

        Returns up to ``top_k`` matching rows as decrypted IndexedRow candidates
        for the PEP to scope-authorize. NOT yet scope-filtered.
        """
        needle = query_text.lower()
        out: list[IndexedRow] = []
        for pid, row in self._rows.items():
            fields = self._cipher.decrypt_fields(row.ciphertext)
            haystack = " ".join(str(v) for v in fields.values()).lower()
            if needle in haystack:
                out.append(
                    IndexedRow(
                        projection_id=pid,
                        owner_tenant_id=row.owner_tenant_id,
                        applied_scope_epoch=row.applied_scope_epoch,
                        fields=fields,
                    )
                )
            if len(out) >= top_k:
                break
        return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_index_store.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/index_store.py \
        tigerexchange/services/central_index/tests/test_index_store.py
git commit -m "feat(central-index): encrypted monotonic index store (ciphertext rows, no cached authoritative scope)

EncryptedIndexStore stores at-rest ciphertext + scope-epoch, applies monotonically,
and deliberately omits the authoritative scope so the PEP can never serve a
stale-HIGH cached scope (§4.7, §11.2b, §10.3).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Central-index read PEP — per-query authz + scope filtering (deny-by-default)

**Files:**
- Create `tigerexchange/services/central_index/read_pep.py`
- Create `tigerexchange/services/central_index/tests/conftest.py`
- Test `tigerexchange/services/central_index/tests/test_read_pep_authz.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/conftest.py`:

```python
"""Shared fixtures for central-index read PEP tests (plan §4.7)."""

import pytest
from cryptography.fernet import Fernet

from contracts import (
    DiscoverabilityScope,
    PublishableProjection,
    ScopeCommit,
)
from contracts.lattice import Tier
from contracts.tenancy import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
)
from central_index.encryption import ControlPlaneCipher
from central_index.index_store import EncryptedIndexStore
from central_index.read_pep import CentralIndexReadPEP
from central_index.scope_registry import ScopeRegistry


def make_tenant(tenant_id: str, *, consortia=frozenset(), active=True) -> TenantContext:
    ent = Entitlement(
        edition=Edition.INSTITUTIONAL,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL}),
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.private,
    )
    return TenantContext(
        tenant_id=tenant_id,
        subject_id="subj-" + tenant_id,
        entitlement=ent,
        consortium_ids=frozenset(consortia),
        subject_active=active,
    )


@pytest.fixture
def cipher() -> ControlPlaneCipher:
    return ControlPlaneCipher(Fernet.generate_key())


@pytest.fixture
def registry() -> ScopeRegistry:
    return ScopeRegistry()


@pytest.fixture
def store(cipher) -> EncryptedIndexStore:
    return EncryptedIndexStore(cipher)


@pytest.fixture
def pep(store, registry) -> CentralIndexReadPEP:
    return CentralIndexReadPEP(store=store, scope_registry=registry)


def publish(
    store: EncryptedIndexStore,
    registry: ScopeRegistry,
    *,
    projection_id: str,
    owner: str,
    title: str,
    scope: DiscoverabilityScope,
    epoch: int = 1,
    allowlist=frozenset(),
    consortia=frozenset(),
):
    """Emit-time: owner durably commits scope BEFORE the row is queryable (§4.7)."""
    registry.commit_scope(
        ScopeCommit(
            projection_id=projection_id,
            owner_tenant_id=owner,
            scope=scope,
            scope_epoch=epoch,
            named_tenant_allowlist=frozenset(allowlist),
            consortium_ids=frozenset(consortia),
        )
    )
    proj = PublishableProjection(
        projection_id=projection_id,
        artifact_id="a-" + projection_id,
        owner_tenant_id=owner,
        tier=Tier.public,
        discoverability_scope=scope,
        fields={"title": title},
    )
    store.apply(proj, scope_epoch=epoch)
```

Create `tigerexchange/services/central_index/tests/test_read_pep_authz.py`:

```python
"""Per-query authz + discoverability_scope enforcement at the read PEP (§4.7).

Covers the §15.2 security contract tests: discoverability-scope denied to a
non-member; named-tenants allowlist enforcement; named-consortium; deny-by-
default for unauthenticated; deprovisioned subject denied.
"""

from contracts import Decision, DiscoverabilityScope, DiscoveryQuery, PepAction
from .conftest import make_tenant, publish


def _query(requester, text="graph", top_k=10) -> DiscoveryQuery:
    return DiscoveryQuery(query_id="q", requester=requester, query_text=text, top_k=top_k)


def test_public_web_visible_to_anyone_including_anonymous(pep, store, registry):
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    resp = pep.authorize_query(_query(None))
    assert resp.decision is Decision.ALLOW
    assert resp.action is PepAction.DISCOVER
    assert {r["projection_id"] for r in resp.payload} == {"p1"}
    assert resp.discoverability_scope is DiscoverabilityScope.PUBLIC_WEB


def test_anonymous_sees_only_public_web(pep, store, registry):
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    publish(store, registry, projection_id="p2", owner="owner",
            title="graph fed", scope=DiscoverabilityScope.FEDERATION_WIDE)
    resp = pep.authorize_query(_query(None))
    assert {r["projection_id"] for r in resp.payload} == {"p1"}


def test_federation_wide_visible_to_authenticated_member(pep, store, registry):
    publish(store, registry, projection_id="p2", owner="owner",
            title="graph fed", scope=DiscoverabilityScope.FEDERATION_WIDE)
    resp = pep.authorize_query(_query(make_tenant("member")))
    assert {r["projection_id"] for r in resp.payload} == {"p2"}


def test_named_consortium_denied_to_non_member(pep, store, registry):
    publish(store, registry, projection_id="p3", owner="owner",
            title="graph consortium", scope=DiscoverabilityScope.NAMED_CONSORTIUM,
            consortia={"c1"})
    # Requester is authenticated but NOT in consortium c1 → no result (deny-by-default).
    resp = pep.authorize_query(_query(make_tenant("outsider", consortia={"c2"})))
    assert resp.payload == []
    # And a c1 member sees it.
    resp2 = pep.authorize_query(_query(make_tenant("insider", consortia={"c1"})))
    assert {r["projection_id"] for r in resp2.payload} == {"p3"}


def test_named_tenants_allowlist_enforced(pep, store, registry):
    publish(store, registry, projection_id="p4", owner="owner",
            title="graph allowlisted", scope=DiscoverabilityScope.NAMED_TENANTS,
            allowlist={"t-allowed"})
    assert pep.authorize_query(_query(make_tenant("t-denied"))).payload == []
    allowed = pep.authorize_query(_query(make_tenant("t-allowed")))
    assert {r["projection_id"] for r in allowed.payload} == {"p4"}


def test_scope_none_never_in_index_results(pep, store, registry):
    publish(store, registry, projection_id="p5", owner="owner",
            title="graph optout", scope=DiscoverabilityScope.NONE)
    # Even the owner-brokered-only tenant's own member cannot read it via the index.
    assert pep.authorize_query(_query(make_tenant("anyone"))).payload == []


def test_owner_always_sees_own_projection(pep, store, registry):
    publish(store, registry, projection_id="p6", owner="owner",
            title="graph mine", scope=DiscoverabilityScope.NAMED_CONSORTIUM,
            consortia={"cX"})
    resp = pep.authorize_query(_query(make_tenant("owner")))
    assert {r["projection_id"] for r in resp.payload} == {"p6"}


def test_deprovisioned_subject_denied_all(pep, store, registry):
    publish(store, registry, projection_id="p7", owner="owner",
            title="graph fed", scope=DiscoverabilityScope.FEDERATION_WIDE)
    stale = make_tenant("member", active=False)
    assert pep.authorize_query(_query(stale)).payload == []


def test_no_match_is_allow_with_empty_payload(pep, store, registry):
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    resp = pep.authorize_query(_query(make_tenant("m"), text="nonexistent"))
    assert resp.decision is Decision.ALLOW
    assert resp.payload == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_read_pep_authz.py -q
```

Expected failure: `ModuleNotFoundError: No module named 'central_index.read_pep'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/central_index/read_pep.py`:

```python
"""Central-index read PEP (plan §4.7, §11.2b, §10.3).

The SAME PEP code/policy engine as the cell-local PEP (one IPolicyEnforcement
contract, D4), deployed at the central-index location and selected by
PepAction.DISCOVER. It authorizes discovery READS:

  1. Per-query authorization, DENY-BY-DEFAULT: no membership relation -> no
     result. Anonymous/unauthenticated queries see only public-web records.
     A deprovisioned subject (subject_active=False) sees nothing.

  2. First-class discoverability_scope enforced AT QUERY TIME against the
     requester's identity + consortium membership. CRITICALLY, the scope is
     resolved from the owner-authoritative ScopeRegistry (the currently-
     committed scope-epoch), NEVER from a scope cached on the index row — so a
     projection is only ever queryable at the owner's currently-committed scope
     (the share-correctness gate; additive counterpart to revocation, §10.3).

  3. The aggregate is treated as AT-LEAST-PRIVATE-TIER: a per-requester bulk
     rate limit guards against broad capability-mapping recon (§4.7/§11.2b).
     (DP/k-anon inference defenses are §11.2 and ship separately.)

Returns a fail-closed PepResponse: payload present only on ALLOW; non-matching
or fully-filtered queries return ALLOW with an empty payload (the query was
authorized; nothing the requester may see matched). Authz failures that should
deny the whole query (e.g. rate-limit trip) return DENY with no payload.
"""

from __future__ import annotations

from contracts import (
    Decision,
    DiscoverabilityScope,
    DiscoveryQuery,
    PepAction,
    PepResponse,
)
from contracts.lattice import Tier
from central_index.index_store import EncryptedIndexStore, IndexedRow
from central_index.scope_registry import ScopeRegistry


class CentralIndexReadPEP:
    """Read PEP enforcing per-query authz + discoverability_scope (§4.7)."""

    def __init__(
        self,
        *,
        store: EncryptedIndexStore,
        scope_registry: ScopeRegistry,
        max_results_per_query: int = 200,
    ) -> None:
        self._store = store
        self._registry = scope_registry
        self._max_results_per_query = max_results_per_query

    def authorize_query(self, query: DiscoveryQuery) -> PepResponse:
        """Authorize a discovery read and return scope-filtered hits.

        Deny-by-default at every step; the aggregate is at-least-private-tier.
        """
        requester = query.requester

        # Deprovisioned/inactive subjects are denied at every non-public path.
        # (For anonymous requesters there is no subject to check.)
        if requester is not None and not requester.subject_active:
            return PepResponse(
                request_id=query.query_id,
                decision=Decision.DENY,
                effective_tier=Tier.private,
                reason="requester subject is not active (deprovisioned/stale)",
            )

        candidates = self._store.query(query.query_text, top_k=self._max_results_per_query)

        allowed: list[dict[str, object]] = []
        for row in candidates:
            if self._is_visible(row, requester):
                allowed.append(
                    {
                        "projection_id": row.projection_id,
                        "owner_tenant_id": row.owner_tenant_id,
                        "fields": row.fields,
                    }
                )
            if len(allowed) >= query.top_k:
                break

        return PepResponse(
            request_id=query.query_id,
            decision=Decision.ALLOW,
            effective_tier=Tier.private,  # aggregate treated at-least-private (§4.7)
            payload=allowed,
            # Report the scope class the result set was authorized under (the
            # broadest the requester is entitled to see); informational.
            discoverability_scope=self._result_scope(requester),
            reason="discovery read authorized",
            # NOTE: action is carried via attributes for the discover locus;
            # see PepResponse below. (PepResponse has no action field; the
            # caller knows this is a DISCOVER response.)
        )

    # --- scope authorization (the heart of §4.7 + share-correctness) -------- #

    def _is_visible(self, row: IndexedRow, requester) -> bool:
        """True iff ``requester`` may read ``row`` under the OWNER-COMMITTED scope.

        Scope is resolved from the ScopeRegistry (owner-authoritative,
        currently-committed scope-epoch), NEVER from a scope cached on the row.
        Deny-by-default: an uncommitted projection or any unhandled scope -> False.
        """
        committed = self._registry.current_scope(row.projection_id)
        if committed is None:
            return False  # never committed -> not discoverable (§4.7)

        scope = committed.scope

        # The owner can always read its own projection regardless of scope.
        if requester is not None and requester.tenant_id == row.owner_tenant_id:
            return True

        if scope is DiscoverabilityScope.NONE:
            return False  # owner-brokered drill-down only; never in index reads
        if scope is DiscoverabilityScope.PUBLIC_WEB:
            return True  # anyone, including anonymous
        # Everything below requires an authenticated requester.
        if requester is None:
            return False
        if scope is DiscoverabilityScope.FEDERATION_WIDE:
            return True  # any authenticated federation member
        if scope is DiscoverabilityScope.NAMED_CONSORTIUM:
            return bool(requester.consortium_ids & committed.consortium_ids)
        if scope is DiscoverabilityScope.NAMED_TENANTS:
            return requester.tenant_id in committed.named_tenant_allowlist
        return False  # unknown scope -> fail closed

    def _result_scope(self, requester) -> DiscoverabilityScope:
        return (
            DiscoverabilityScope.PUBLIC_WEB
            if requester is None
            else DiscoverabilityScope.FEDERATION_WIDE
        )
```

Note on the inline comment about `action`: `PepResponse` in the canonical kernel has no `action` field, but the authz test asserts `resp.action is PepAction.DISCOVER`. Resolve this by NOT asserting `action` on the response. Update the failing test from Step 1: remove the line `assert resp.action is PepAction.DISCOVER` in `test_public_web_visible_to_anyone_including_anonymous` and remove the unused `PepAction` import. The `PepAction.DISCOVER` locus selection lives on the *request* path (the FastAPI wiring builds a `DiscoveryQuery`, and a `PepRequest` with `action=PepAction.DISCOVER` is the equivalent broker-path framing); the response is identified as a discovery response by the caller. Apply this test edit before running Step 4.

Concretely, the corrected test top section is:

```python
from contracts import Decision, DiscoverabilityScope, DiscoveryQuery
from .conftest import make_tenant, publish
```

and the corrected first test body drops the action assertion:

```python
def test_public_web_visible_to_anyone_including_anonymous(pep, store, registry):
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    resp = pep.authorize_query(_query(None))
    assert resp.decision is Decision.ALLOW
    assert {r["projection_id"] for r in resp.payload} == {"p1"}
    assert resp.discoverability_scope is DiscoverabilityScope.PUBLIC_WEB
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_read_pep_authz.py -q
```

Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/read_pep.py \
        tigerexchange/services/central_index/tests/conftest.py \
        tigerexchange/services/central_index/tests/test_read_pep_authz.py
git commit -m "feat(central-index): read PEP with per-query authz + discoverability_scope (deny-by-default)

CentralIndexReadPEP resolves scope from the owner-authoritative ScopeRegistry
(never a cached row scope), enforces public-web/federation-wide/named-consortium/
named-tenants/none at query time, denies non-members and deprovisioned subjects,
and treats the aggregate as at-least-private (§4.7, §11.2b).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Aggregate rate-limit (mosaic / at-least-private-tier bulk control)

**Files:**
- Modify `tigerexchange/services/central_index/read_pep.py`
- Test `tigerexchange/services/central_index/tests/test_read_pep_ratelimit.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_read_pep_ratelimit.py`:

```python
"""Aggregate/bulk query rate-limit at the read PEP (plan §4.7 mosaic control).

The index aggregate is access-controlled as at-least-private-tier: broad
capability-mapping recon is rate-limited per requester. Over-limit -> DENY with
no payload (fail-closed)."""

from contracts import Decision, DiscoverabilityScope, DiscoveryQuery
from central_index.read_pep import CentralIndexReadPEP
from .conftest import make_tenant, publish


def _q(requester, text="graph") -> DiscoveryQuery:
    return DiscoveryQuery(query_id="q", requester=requester, query_text=text, top_k=10)


def test_over_limit_query_is_denied(store, registry):
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    pep = CentralIndexReadPEP(
        store=store, scope_registry=registry, queries_per_window=2
    )
    member = make_tenant("m1")
    assert pep.authorize_query(_q(member)).decision is Decision.ALLOW
    assert pep.authorize_query(_q(member)).decision is Decision.ALLOW
    # Third query in the window trips the bulk control.
    denied = pep.authorize_query(_q(member))
    assert denied.decision is Decision.DENY
    assert denied.payload is None
    assert "rate" in denied.reason.lower()


def test_limit_is_per_requester(store, registry):
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    pep = CentralIndexReadPEP(
        store=store, scope_registry=registry, queries_per_window=1
    )
    a, b = make_tenant("a"), make_tenant("b")
    assert pep.authorize_query(_q(a)).decision is Decision.ALLOW
    assert pep.authorize_query(_q(a)).decision is Decision.DENY
    # Different requester has its own budget.
    assert pep.authorize_query(_q(b)).decision is Decision.ALLOW


def test_anonymous_requesters_share_one_bucket(store, registry):
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    pep = CentralIndexReadPEP(
        store=store, scope_registry=registry, queries_per_window=1
    )
    assert pep.authorize_query(_q(None)).decision is Decision.ALLOW
    assert pep.authorize_query(_q(None)).decision is Decision.DENY
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_read_pep_ratelimit.py -q
```

Expected failure: `TypeError: CentralIndexReadPEP.__init__() got an unexpected keyword argument 'queries_per_window'`.

- [ ] **Step 3: Write minimal implementation**

Edit `CentralIndexReadPEP.__init__` in `tigerexchange/services/central_index/read_pep.py` to add the counter and parameter:

```python
    def __init__(
        self,
        *,
        store: EncryptedIndexStore,
        scope_registry: ScopeRegistry,
        max_results_per_query: int = 200,
        queries_per_window: int = 1000,
    ) -> None:
        self._store = store
        self._registry = scope_registry
        self._max_results_per_query = max_results_per_query
        self._queries_per_window = queries_per_window
        # Per-requester query counter for the current window (anonymous share
        # one bucket keyed "__anon__"). A fixed-window limiter is sufficient for
        # the at-least-private bulk control; sliding-window/Redis is deferred.
        self._window_counts: dict[str, int] = {}
```

Then add the rate-limit check at the very top of `authorize_query`, before the subject-active check:

```python
    def authorize_query(self, query: DiscoveryQuery) -> PepResponse:
        """Authorize a discovery read and return scope-filtered hits.

        Deny-by-default at every step; the aggregate is at-least-private-tier.
        """
        requester = query.requester

        # Bulk/aggregate control: the index aggregate is at-least-private-tier,
        # so broad capability-mapping recon is rate-limited per requester (§4.7).
        bucket = "__anon__" if requester is None else requester.tenant_id
        count = self._window_counts.get(bucket, 0) + 1
        self._window_counts[bucket] = count
        if count > self._queries_per_window:
            return PepResponse(
                request_id=query.query_id,
                decision=Decision.DENY,
                effective_tier=Tier.private,
                reason="aggregate query rate limit exceeded (mosaic control, §4.7)",
            )

        # Deprovisioned/inactive subjects are denied at every non-public path.
        if requester is not None and not requester.subject_active:
            return PepResponse(
                request_id=query.query_id,
                decision=Decision.DENY,
                effective_tier=Tier.private,
                reason="requester subject is not active (deprovisioned/stale)",
            )
```

(Remove the now-duplicated `requester = query.requester` and subject-active block lower in the method — they move to the top as shown.)

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_read_pep_ratelimit.py \
                 tigerexchange/services/central_index/tests/test_read_pep_authz.py -q
```

Expected: `12 passed` (3 new + 9 regression).

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/read_pep.py \
        tigerexchange/services/central_index/tests/test_read_pep_ratelimit.py
git commit -m "feat(central-index): per-requester aggregate rate-limit (mosaic / at-least-private control)

Adds a fixed-window per-requester bulk-query limiter; over-limit -> DENY with no
payload, treating the aggregate as at-least-private-tier (§4.7).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Share-correctness — PEP serves owner-committed scope, never stale-HIGH cached scope

**Files:**
- Test `tigerexchange/services/central_index/tests/test_read_pep_scope_consistency.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_read_pep_scope_consistency.py`:

```python
"""Emit-time strong-consistency of discoverability_scope at the PEP (HIGH item).

The PEP MUST evaluate scope against the owner's CURRENTLY-COMMITTED scope (the
monotonic scope-epoch in the ScopeRegistry), never a scope cached on the index
row. This proves the over-share mirror of the revocation gate (§4.7, §10.3):
  - A row applied while its row-cached scope is FEDERATION_WIDE must NOT be
    served federation-wide if the owner has since committed NAMED_CONSORTIUM.
  - A projection whose scope-commit has NOT happened is invisible (deny-by-default).
"""

from contracts import (
    Decision,
    DiscoverabilityScope,
    DiscoveryQuery,
    PublishableProjection,
    ScopeCommit,
)
from contracts.lattice import Tier
from .conftest import make_tenant


def _q(requester) -> DiscoveryQuery:
    return DiscoveryQuery(query_id="q", requester=requester, query_text="graph", top_k=10)


def _row(store, pid, owner, row_scope, epoch):
    """Insert an index row whose CACHED scope is row_scope (possibly stale-HIGH)."""
    store.apply(
        PublishableProjection(
            projection_id=pid,
            artifact_id="a-" + pid,
            owner_tenant_id=owner,
            tier=Tier.public,
            discoverability_scope=row_scope,  # the cached value the PEP must IGNORE
            fields={"title": "graph " + pid},
        ),
        scope_epoch=epoch,
    )


def test_row_cached_scope_is_ignored_owner_committed_wins(pep, store, registry):
    # Index row was applied with a stale-HIGH cached scope of FEDERATION_WIDE.
    _row(store, "p1", "owner", DiscoverabilityScope.FEDERATION_WIDE, epoch=1)
    # But the owner's CURRENTLY-COMMITTED scope is the narrower NAMED_CONSORTIUM.
    registry.commit_scope(ScopeCommit(
        projection_id="p1", owner_tenant_id="owner",
        scope=DiscoverabilityScope.NAMED_CONSORTIUM, scope_epoch=1,
        consortium_ids=frozenset({"c1"}),
    ))
    # A federation member NOT in c1 must NOT see it (cached HIGH scope ignored).
    outsider = pep.authorize_query(_q(make_tenant("outsider", consortia={"c2"})))
    assert outsider.payload == []
    # A c1 member sees it (the committed scope is honored).
    insider = pep.authorize_query(_q(make_tenant("insider", consortia={"c1"})))
    assert {r["projection_id"] for r in insider.payload} == {"p1"}


def test_uncommitted_projection_is_invisible(pep, store, registry):
    # Row present in index, but the owner has NOT committed any scope.
    _row(store, "p2", "owner", DiscoverabilityScope.PUBLIC_WEB, epoch=1)
    resp = pep.authorize_query(_q(make_tenant("anyone")))
    assert resp.decision is Decision.ALLOW
    assert resp.payload == []  # deny-by-default: no committed scope -> invisible


def test_narrowing_commit_takes_effect_immediately(pep, store, registry):
    _row(store, "p3", "owner", DiscoverabilityScope.PUBLIC_WEB, epoch=1)
    registry.commit_scope(ScopeCommit(
        projection_id="p3", owner_tenant_id="owner",
        scope=DiscoverabilityScope.PUBLIC_WEB, scope_epoch=1,
    ))
    assert pep.authorize_query(_q(None)).payload  # anon sees public-web
    # Owner narrows to NONE at a higher epoch (emit-time strong consistency).
    registry.commit_scope(ScopeCommit(
        projection_id="p3", owner_tenant_id="owner",
        scope=DiscoverabilityScope.NONE, scope_epoch=2,
    ))
    # Now invisible to everyone via the index, even though the row is unchanged.
    assert pep.authorize_query(_q(None)).payload == []
    assert pep.authorize_query(_q(make_tenant("m"))).payload == []
```

- [ ] **Step 2: Run test to verify it fails or passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_read_pep_scope_consistency.py -q
```

These tests assert the behavior already built in Task 6 (`_is_visible` resolves scope from the registry, ignoring the row's cached scope). They should PASS immediately — this task is a *characterization gate* proving the share-correctness property holds at the unit level before the property test. If any test fails, the PEP is reading a cached scope somewhere; fix `_is_visible` to resolve exclusively via `self._registry.current_scope(...)` until green. Expected: `3 passed`.

- [ ] **Step 3: (No new implementation if green.)** If green, no code change. If red, the only permitted fix is to ensure `_is_visible` ignores `row` scope and reads `self._registry.current_scope(row.projection_id)`. (The Task 6 implementation already does this; this step exists to enforce it.)

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/ -q
```

Expected: all central-index tests pass.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/tests/test_read_pep_scope_consistency.py
git commit -m "test(central-index): characterize share-correctness — PEP honors owner-committed scope, ignores cached row scope

Proves the over-share mirror of the revocation gate at the unit level: a
stale-HIGH cached row scope is never honored; uncommitted projections are
invisible; narrowing commits take effect immediately (§4.7, §10.3).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Property test — no projection ever queryable wider than committed scope (version-skew + replay)

**Files:**
- Test `tigerexchange/services/central_index/tests/test_share_correctness_property.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_share_correctness_property.py`:

```python
"""Property test: no projection is EVER queryable at a discoverability_scope
WIDER than the owner's currently-committed scope, across version-skew and replay
(plan §10.3, share-correctness HIGH; additive counterpart to the revocation gate).

Model:
  - The owner commits a SEQUENCE of scope updates (monotonic epochs) — the
    authoritative timeline. We also REPLAY old commits out of order and apply
    index rows with arbitrary (possibly stale-HIGH) cached scopes + out-of-order
    epochs (version-skew). After the storm, for EVERY requester profile, every
    hit the PEP returns must be authorized by the FINAL owner-committed scope,
    and must NOT be visible at any scope strictly WIDER than that committed scope.
"""

from hypothesis import given, settings, strategies as st

from contracts import (
    DiscoverabilityScope,
    DiscoveryQuery,
    PublishableProjection,
    ScopeCommit,
    ScopeEpochTooOld,
)
from contracts.lattice import Tier
from central_index.encryption import ControlPlaneCipher
from central_index.index_store import EncryptedIndexStore
from central_index.read_pep import CentralIndexReadPEP
from central_index.scope_lattice import scope_wider_than
from central_index.scope_registry import ScopeRegistry
from cryptography.fernet import Fernet

from .conftest import make_tenant

_SCOPES = list(DiscoverabilityScope)


def _visible_under(scope: ScopeCommit, requester) -> bool:
    """Reference oracle: is a row with committed ``scope`` visible to requester?"""
    s = scope.scope
    if requester is not None and requester.tenant_id == scope.owner_tenant_id:
        return True
    if s is DiscoverabilityScope.NONE:
        return False
    if s is DiscoverabilityScope.PUBLIC_WEB:
        return True
    if requester is None:
        return False
    if s is DiscoverabilityScope.FEDERATION_WIDE:
        return True
    if s is DiscoverabilityScope.NAMED_CONSORTIUM:
        return bool(requester.consortium_ids & scope.consortium_ids)
    if s is DiscoverabilityScope.NAMED_TENANTS:
        return requester.tenant_id in scope.named_tenant_allowlist
    return False


_scope_strat = st.sampled_from(_SCOPES)
# (epoch, scope) commit events; epochs may collide/regress to exercise monotonicity.
_commit_event = st.tuples(st.integers(min_value=0, max_value=20), _scope_strat)
_commit_seq = st.lists(_commit_event, min_size=1, max_size=12)
# Index row applies: (epoch, cached_scope) — cached scope is arbitrary (skew).
_row_apply = st.tuples(st.integers(min_value=0, max_value=20), _scope_strat)
_row_seq = st.lists(_row_apply, min_size=1, max_size=12)


@settings(max_examples=300, deadline=None)
@given(commits=_commit_seq, rows=_row_seq, shuffle_seed=st.integers(0, 10_000))
def test_never_queryable_wider_than_committed(commits, rows, shuffle_seed):
    owner = "owner"
    consortia = frozenset({"c1"})
    allowlist = frozenset({"t-allowed"})
    pid = "p1"

    registry = ScopeRegistry()
    store = EncryptedIndexStore(ControlPlaneCipher(Fernet.generate_key()))
    pep = CentralIndexReadPEP(
        store=store, scope_registry=registry, queries_per_window=10_000
    )

    # Apply scope commits (owner timeline) — monotonic; out-of-order/replay raises.
    for epoch, scope in commits:
        c = ScopeCommit(
            projection_id=pid, owner_tenant_id=owner, scope=scope,
            scope_epoch=epoch, consortium_ids=consortia,
            named_tenant_allowlist=allowlist,
        )
        try:
            registry.commit_scope(c)
        except ScopeEpochTooOld:
            pass  # replayed/regressed commit correctly rejected

    # Apply index rows with arbitrary cached scope + out-of-order epochs (skew),
    # including replays of the same epoch.
    ordered_rows = rows + rows[:: -1]  # replay the sequence reversed
    for epoch, cached_scope in ordered_rows:
        store.apply(
            PublishableProjection(
                projection_id=pid, artifact_id="a", owner_tenant_id=owner,
                tier=Tier.public, discoverability_scope=cached_scope,
                fields={"title": "graph p1"},
            ),
            scope_epoch=epoch,
        )

    committed = registry.current_scope(pid)

    requesters = [
        None,                                              # anonymous
        make_tenant("outsider", consortia={"c9"}),         # member, wrong consortium
        make_tenant("insider", consortia={"c1"}),          # member of c1
        make_tenant("t-allowed"),                          # on the named allowlist
        make_tenant("t-denied"),                           # not allowlisted
        make_tenant(owner),                                # the owner itself
    ]

    for r in requesters:
        resp = pep.authorize_query(
            DiscoveryQuery(query_id="q", requester=r, query_text="graph", top_k=10)
        )
        served = {h["projection_id"] for h in (resp.payload or [])}

        if committed is None:
            # No committed scope -> never queryable by anyone.
            assert served == set(), "uncommitted projection was served"
            continue

        # 1) If served, the FINAL committed scope must authorize this requester.
        if pid in served:
            assert _visible_under(committed, r), (
                f"served at a scope wider than committed: committed={committed.scope}, "
                f"requester consortia/tenant={getattr(r, 'tenant_id', None)}"
            )

        # 2) It must NOT be visible at any scope strictly WIDER than committed.
        for wider in _SCOPES:
            if scope_wider_than(wider, committed.scope):
                wider_commit = committed.model_copy(update={"scope": wider})
                if _visible_under(wider_commit, r) and not _visible_under(committed, r):
                    assert pid not in served, (
                        f"projection visible at WIDER scope {wider} than "
                        f"committed {committed.scope}"
                    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_share_correctness_property.py -q
```

If the PEP is correct (Task 6), this should PASS. To verify the property test genuinely has teeth (TDD discipline), temporarily break `_is_visible` to read the row's cached scope instead of the registry (e.g. by inserting a buggy branch that returns `True` for `FEDERATION_WIDE` cached rows), re-run, and confirm Hypothesis reports a falsifying example. Then revert the deliberate break. Document the observed falsifying counterexample in the commit body.

- [ ] **Step 3: Write minimal implementation**

No production code change — the property holds against the Task 6 PEP. Ensure `hypothesis` is a dev dependency of the central-index service (add `hypothesis>=6` to dev requirements). This step's "implementation" is confirming the dependency is declared and the revert from Step 2 is clean.

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_share_correctness_property.py -q
```

Expected: `1 passed` (300 Hypothesis examples, no falsifying case).

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/tests/test_share_correctness_property.py
git commit -m "test(central-index): property test — no projection queryable wider than owner-committed scope

Hypothesis test over random commit sequences + version-skew + replay: every served
hit is authorized by the FINAL owner-committed scope and never visible at a wider
scope. Additive counterpart to the revocation gate (§10.3, §15.2). Confirmed teeth:
a row-cached-scope bug yields a falsifying example.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Durable Postgres backing for the central index + scope registry (FORCE RLS, control-plane-key ciphertext at rest)

**Files:**
- Create `tigerexchange/services/central_index/migrations/0001_central_index.sql`
- Test `tigerexchange/services/central_index/tests/test_migration_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_migration_schema.py`:

```python
"""DDL invariants for the central-index durable backing (plan §4.7, §7.7, §11.2b).

The migration must: (a) store projection FIELDS as ciphertext (a BYTEA column),
never plaintext; (b) carry owner_tenant_id + applied_scope_epoch on the index
row; (c) keep the authoritative scope in a SEPARATE scope_commit table keyed by
projection_id with a monotonic scope_epoch; (d) enable FORCE ROW LEVEL SECURITY
with a RESTRICTIVE tenant policy and tenant_id-leading index (§7.7 defense-in-depth).
This test asserts the SQL text contains those structural guarantees (no live DB
needed in unit CI; an integration harness exercises the live DB separately).
"""

from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "0001_central_index.sql"
)


def _sql() -> str:
    return MIGRATION.read_text().lower()


def test_migration_file_exists():
    assert MIGRATION.exists()


def test_fields_stored_as_bytea_ciphertext():
    sql = _sql()
    assert "fields_ciphertext bytea not null" in sql
    # No plaintext jsonb/text column for fields.
    assert "fields jsonb" not in sql
    assert "fields text" not in sql


def test_index_row_carries_owner_and_scope_epoch():
    sql = _sql()
    assert "owner_tenant_id" in sql
    assert "applied_scope_epoch bigint not null" in sql


def test_scope_commit_table_is_separate_and_monotonic():
    sql = _sql()
    assert "create table central_index_projection" in sql
    assert "create table scope_commit" in sql
    # scope_commit keyed by projection_id, carries scope + monotonic epoch.
    assert "scope_epoch bigint not null" in sql
    assert "scope text not null" in sql


def test_force_rls_restrictive_tenant_policy_and_leading_index():
    sql = _sql()
    assert "force row level security" in sql
    assert "as restrictive" in sql
    assert "current_setting('app.tenant_id'" in sql
    # tenant_id-leading index for the RLS path (§7.7).
    assert "(owner_tenant_id," in sql or "(owner_tenant_id)" in sql
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_migration_schema.py -q
```

Expected failure: `assert MIGRATION.exists()` fails (file not created yet).

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/central_index/migrations/0001_central_index.sql`:

```sql
-- Central-index durable backing (plan §4.7, §7.7, §11.2b).
--
-- Two tables:
--   central_index_projection : the encrypted index rows. fields_ciphertext is
--     the at-rest control-plane-key ciphertext (§11.2b) — NEVER plaintext.
--     Carries owner_tenant_id + the scope-epoch the row was last applied under
--     (monotonic applier, §10.3). Does NOT store the authoritative scope.
--   scope_commit : the owner-authoritative discoverability_scope, keyed by
--     projection_id, with a monotonic scope_epoch. The PEP reads scope HERE so
--     a row can never serve a stale-HIGH cached scope (share-correctness HIGH).
--
-- FORCE ROW LEVEL SECURITY + RESTRICTIVE tenant policy + tenant_id-leading index
-- are the §7.7 defense-in-depth boundary; SET LOCAL app.tenant_id pins the tenant
-- per transaction. The control-plane operator role is the index reader/writer;
-- tenants never query the aggregate directly (the PEP is the only reader).

CREATE TABLE central_index_projection (
    projection_id         TEXT   PRIMARY KEY,
    owner_tenant_id       TEXT   NOT NULL,
    applied_scope_epoch   BIGINT NOT NULL,
    projection_schema_version INT NOT NULL,
    lattice_version       INT    NOT NULL,
    fields_ciphertext     BYTEA  NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- tenant_id-leading index for the RLS-scoped path (§7.7).
CREATE INDEX idx_cip_owner_tenant ON central_index_projection (owner_tenant_id, projection_id);

ALTER TABLE central_index_projection ENABLE ROW LEVEL SECURITY;
ALTER TABLE central_index_projection FORCE ROW LEVEL SECURITY;

CREATE POLICY cip_tenant_isolation ON central_index_projection
    AS RESTRICTIVE
    USING (owner_tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (owner_tenant_id = current_setting('app.tenant_id', true));

CREATE TABLE scope_commit (
    projection_id          TEXT   PRIMARY KEY,
    owner_tenant_id        TEXT   NOT NULL,
    scope                  TEXT   NOT NULL,
    scope_epoch            BIGINT NOT NULL,
    named_tenant_allowlist TEXT[] NOT NULL DEFAULT '{}',
    consortium_ids         TEXT[] NOT NULL DEFAULT '{}',
    committed_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scope_commit_owner ON scope_commit (owner_tenant_id, projection_id);

ALTER TABLE scope_commit ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_commit FORCE ROW LEVEL SECURITY;

CREATE POLICY scope_commit_tenant_isolation ON scope_commit
    AS RESTRICTIVE
    USING (owner_tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (owner_tenant_id = current_setting('app.tenant_id', true));
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_migration_schema.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/migrations/0001_central_index.sql \
        tigerexchange/services/central_index/tests/test_migration_schema.py
git commit -m "feat(central-index): durable Postgres DDL — ciphertext rows + separate monotonic scope_commit + FORCE RLS

central_index_projection stores at-rest control-plane-key ciphertext + applied
scope-epoch; scope_commit holds the owner-authoritative scope separately
(monotonic epoch). Both tables FORCE RLS + RESTRICTIVE tenant policy +
tenant_id-leading index (§4.7, §7.7, §11.2b).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: FastAPI discovery read endpoint wired to the PEP

**Files:**
- Create `tigerexchange/services/central_index/api.py`
- Test `tigerexchange/services/central_index/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/central_index/tests/test_api.py`:

```python
"""FastAPI discovery read endpoint over the central-index PEP (plan §4.7).

The HTTP layer constructs a DiscoveryQuery from the authenticated requester and
delegates ALL authorization to the PEP. A DENY (e.g. rate-limit) -> HTTP 403; an
ALLOW with filtered results -> 200 with only the scope-authorized hits.
"""

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from contracts import DiscoverabilityScope
from central_index.api import build_app
from central_index.encryption import ControlPlaneCipher
from central_index.index_store import EncryptedIndexStore
from central_index.read_pep import CentralIndexReadPEP
from central_index.scope_registry import ScopeRegistry
from .conftest import make_tenant, publish


def _client(pep, requester):
    app = build_app(pep, requester_provider=lambda: requester)
    return TestClient(app)


def _wire():
    store = EncryptedIndexStore(ControlPlaneCipher(Fernet.generate_key()))
    registry = ScopeRegistry()
    pep = CentralIndexReadPEP(store=store, scope_registry=registry, queries_per_window=2)
    return store, registry, pep


def test_member_gets_authorized_hits():
    store, registry, pep = _wire()
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    client = _client(pep, make_tenant("m1"))
    resp = client.post("/discovery/query", json={"query_text": "graph", "top_k": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert {h["projection_id"] for h in body["results"]} == {"p1"}


def test_non_member_named_consortium_gets_empty():
    store, registry, pep = _wire()
    publish(store, registry, projection_id="p3", owner="owner",
            title="graph consortium", scope=DiscoverabilityScope.NAMED_CONSORTIUM,
            consortia={"c1"})
    client = _client(pep, make_tenant("outsider", consortia={"c2"}))
    resp = client.post("/discovery/query", json={"query_text": "graph", "top_k": 10})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_rate_limit_returns_403():
    store, registry, pep = _wire()
    publish(store, registry, projection_id="p1", owner="owner",
            title="graph public", scope=DiscoverabilityScope.PUBLIC_WEB)
    client = _client(pep, make_tenant("m1"))
    assert client.post("/discovery/query", json={"query_text": "graph"}).status_code == 200
    assert client.post("/discovery/query", json={"query_text": "graph"}).status_code == 200
    assert client.post("/discovery/query", json={"query_text": "graph"}).status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_api.py -q
```

Expected failure: `ModuleNotFoundError: No module named 'central_index.api'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/central_index/api.py`:

```python
"""FastAPI discovery read endpoint over the central-index PEP (plan §4.7).

The HTTP layer is a thin shell: it constructs a DiscoveryQuery from the
authenticated requester (supplied by ``requester_provider`` — the
Keycloak/CILogon-resolved TenantContext from 0d-identity-entitlement, or None
for anonymous) and delegates ALL authorization to the PEP. It NEVER filters,
scopes, or reads the index itself. DENY -> 403; ALLOW -> 200 with the
scope-authorized payload only.
"""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from contracts import Decision, DiscoveryQuery
from contracts.tenancy import TenantContext
from central_index.read_pep import CentralIndexReadPEP


class DiscoveryRequestBody(BaseModel):
    query_text: str
    top_k: int = Field(default=50, ge=1, le=500)


def build_app(
    pep: CentralIndexReadPEP,
    *,
    requester_provider: Callable[[], TenantContext | None],
) -> FastAPI:
    """Build the discovery API. ``requester_provider`` resolves the authenticated
    requester (or None for anonymous) — wired to identity in production."""

    app = FastAPI(title="TigerExchange Central-Index Discovery")

    @app.post("/discovery/query")
    def discovery_query(body: DiscoveryRequestBody) -> dict[str, object]:
        requester = requester_provider()
        query = DiscoveryQuery(
            query_id=str(uuid.uuid4()),
            requester=requester,
            query_text=body.query_text,
            top_k=body.top_k,
        )
        resp = pep.authorize_query(query)
        if resp.decision is not Decision.ALLOW:
            raise HTTPException(status_code=403, detail=resp.reason)
        return {
            "results": resp.payload or [],
            "discoverability_scope": (
                resp.discoverability_scope.value if resp.discoverability_scope else None
            ),
        }

    return app
```

Ensure `fastapi` and `httpx` (for `TestClient`) are dependencies/dev-dependencies of the central-index service.

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tigerexchange/services/central_index/tests/test_api.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add tigerexchange/services/central_index/api.py \
        tigerexchange/services/central_index/tests/test_api.py
git commit -m "feat(central-index): FastAPI discovery read endpoint delegating all authz to the PEP

POST /discovery/query builds a DiscoveryQuery from the authenticated requester
and delegates to CentralIndexReadPEP; DENY -> 403, ALLOW -> 200 with only
scope-authorized hits (§4.7).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Full suite + lint/type gate green

**Files:** (no new files; verification + any fixups)

- [ ] **Step 1: Write/confirm the gate command** Run the full central-index suite plus the contracts discovery test together:

```bash
python -m pytest tigerexchange/services/central_index/tests/ \
                 tigerexchange/packages/contracts/src/contracts/tests/test_discovery.py -q
```

- [ ] **Step 2: Run to verify current state** Expected: all tests pass (Tasks 1-11). If any fail, fix the offending module only (no scope creep).

- [ ] **Step 3: Run lint + type check**

```bash
ruff check tigerexchange/services/central_index tigerexchange/packages/contracts/src/contracts/discovery.py
mypy tigerexchange/services/central_index tigerexchange/packages/contracts/src/contracts/discovery.py
```

Fix any `ruff`/`mypy` findings (unused imports, missing annotations) with minimal edits. Expected after fixes: `ruff` clean, `mypy` clean.

- [ ] **Step 4: Re-run the full suite to confirm green after fixups**

```bash
python -m pytest tigerexchange/services/central_index/tests/ \
                 tigerexchange/packages/contracts/src/contracts/tests/test_discovery.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A tigerexchange/services/central_index tigerexchange/packages/contracts
git commit -m "chore(central-index): lint/type clean + full read-PEP suite green

ruff + mypy clean across the central-index read PEP, scope registry, encrypted
index store, and discovery kernel types; full suite green (§4.7, §10.3, §11.2b,
§15.2).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Deliverable checklist (maps to sub-plan spec)

- **Read PEP in front of the central index, same PEP code/contract (`IPolicyEnforcement` / `PepResponse`), `PepAction.DISCOVER` locus** — Task 6 (`CentralIndexReadPEP`), Task 11 (HTTP).
- **Per-query authz, deny-by-default (no membership → no result)** — Task 6 (`_is_visible`, anonymous→public-web only, deprovisioned denied), tested in `test_read_pep_authz.py`.
- **First-class `discoverability_scope` enforced at query time (public-web | federation-wide | named-consortium | named-tenants | none)** — kernel `DiscoverabilityScope` + Task 2 ordering + Task 6 enforcement.
- **Named-tenants allowlist + named-consortium membership enforcement** — Task 6 tests `test_named_tenants_allowlist_enforced`, `test_named_consortium_denied_to_non_member`.
- **Discoverability-scope denied to a non-member** (§15.2 security contract test) — Task 6.
- **Aggregate at-least-private-tier + at-rest control-plane-key encryption distinct from tenant keys** — Task 4 (`ControlPlaneCipher`), Task 5 (ciphertext rows), Task 7 (bulk rate-limit), Task 10 (BYTEA-at-rest DDL).
- **Confidential payloads structurally absent (D6)** — kernel `PublishableProjection` validator rejects confidential tier (Task 5 `test_confidential_projection_cannot_be_constructed_d6`).
- **HIGH — emit-time strong consistency / monotonic scope-epoch / never stale-HIGH** — Task 3 (`ScopeRegistry` durable monotonic commit), Task 6 (PEP reads owner-committed scope, ignores cached row scope), Task 8 (characterization), Task 10 (separate `scope_commit` table).
- **HIGH property test — no projection queryable wider than committed scope across version-skew + replay** — Task 9.
- **Clean seams for the deferred exchange-federation extension** — the PEP/`ScopeRegistry`/`EncryptedIndexStore` consume only kernel types and `IPolicyEnforcement`; the `IExchangeFeed` Phase-1+ stub remains untouched and unimplemented.
```

I have written the complete implementation plan for sub-plan `0j-central-index-read-pep`. Key facts for the caller:

- The plan is grounded in the actual spec sections read from `/home/anurag/codebase/tiger_research_buddy/plans/final-plan-v2.md` (§4.7 three mechanisms, §11.2/§11.2b two distinct protections, §10.3 consistency contract + the share-correctness gap, §15.2 testing strategy) and the convergence-report HIGH item (`/home/anurag/codebase/tiger_research_buddy/plans/convergence-report.md` lines 28-30).
- 12 TDD tasks, every code step complete (no placeholders), all under `tigerexchange/services/central_index/` and `tigerexchange/packages/contracts/`.
- Uses canonical kernel signatures verbatim (`IPolicyEnforcement`, `PepResponse`, `PepAction.DISCOVER`, `DiscoverabilityScope`, `PublishableProjection`, `TenantContext`, `Decision`, `Tier`) and adds three new kernel types on the discovery seam (`DiscoveryQuery`, `ScopeCommit`, `ScopeEpochTooOld`).
- The two `highs_addressed` items are explicit tasks: emit-time strong-consistency via the owner-authoritative monotonic-scope-epoch `ScopeRegistry` (Tasks 3, 6, 8, 10) and the Hypothesis property test "no projection ever queryable wider than the owner's committed scope across version-skew and replay" (Task 9).
- Phase-0 scope respected: confidential payloads structurally absent (D6, kernel validator), exchange-federation seam left unimplemented (`IExchangeFeed` stub untouched), Postgres FORCE RLS + RESTRICTIVE + tenant_id-leading index for the index tables.

One deviation flagged in the plan itself: the canonical `PepResponse` has no `action` field, so the plan corrects one authz test (Task 6, Step 3) to drop an `assert resp.action is PepAction.DISCOVER` assertion rather than invent a non-canonical field — the `DISCOVER` locus lives on the request path.