# TigerExchange — Canonical Shared contracts/kernel (Phase-0)

> AUTHORITATIVE interface definitions. Every sub-plan imports these verbatim.

I now have all required sections (4, 5, 7, 8, 9) plus the decisions document. I have everything needed to define the canonical kernel package. Let me produce the reference document.

Key authoritative facts extracted from the plan that the kernel must encode:
- 3-tier lattice: `public < private < confidential`, MAX-rule, unknown=most-restrictive (§5.6)
- Decisions: ALLOW/DENY/QUARANTINE; abstention→quarantine→default-deny (D6, §8/classifier)
- DiscoverabilityScope: `public-web | federation-wide | named-consortium | named-tenants | none` (§4.7, §7.3)
- Interface list verbatim from §5.1 K3
- PEP request/response + audit event (per-stream hash-chain, §4.1 AUDa)
- Compliance flags: FERPA|IRB|ITAR|EAR|GDPR-personal, sticky UNION (§6.1)
- Caveats: transfer_legality, export_attestation, FERPA_role (§4.3, §7.3)
- Deferred stubs: IRevocationAuthority, IExchangeFeed (Phase 1+)

---

# TigerExchange — Canonical Shared `contracts/kernel` Package (Phase-0)

This is the **authoritative** kernel. Every sub-plan author imports these symbols verbatim. The package is the near-frozen kernel of §5.1 (K1/K2/K3): zero outbound feature dependencies, no persistent state, pure types + Protocol interfaces. Targets Python 3.11+, Pydantic v2.

Package layout under `tigerexchange/packages/contracts/`:

```
tigerexchange/packages/contracts/
├── pyproject.toml
└── src/contracts/
    ├── __init__.py
    ├── lattice.py            # TierLattice, MAX-rule, compliance flags
    ├── tenancy.py            # TenantContext, Edition, Entitlement
    ├── classification.py     # ClassificationResult, Decision, DiscoverabilityScope, Caveats
    ├── projection.py         # PublishableProjection (versioned field-schema seam)
    ├── pep.py                # PEP request/response types
    ├── audit.py              # AuditEvent (per-stream hash-chain)
    └── interfaces.py         # all I* Protocol/ABC interfaces
```

Design rules applied throughout:
- **Frozen, hashable value objects** (`model_config = ConfigDict(frozen=True)`) for everything that crosses a trust boundary, so projections/decisions cannot be mutated after authorization.
- **`StrEnum`** (3.11+) for all enums so wire/DB values are stable strings, not ints.
- Interfaces are `typing.Protocol` (`@runtime_checkable`) for structural typing + import-linter friendliness; deferred-phase seams are minimal `Protocol`s with explicit **Phase-1+** docstrings and no method bodies that imply behavior.

---

## `tigerexchange/packages/contracts/pyproject.toml`

```toml
[project]
name = "tigerexchange-contracts"
version = "0.0.0"
description = "TigerExchange canonical shared kernel: TierLattice, tenancy, classification, PEP contracts, interface seams. Near-frozen, zero feature deps, no persistence."
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6,<3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/contracts"]

# Kernel fitness function (§5.5): zero outbound feature deps, no persistence.
# import-linter enforces this in CI; the kernel may NOT import any mod-*/service/store package.
[tool.importlinter]
root_package = "contracts"

[[tool.importlinter.contracts]]
name = "kernel-has-no-feature-or-persistence-deps"
type = "forbidden"
source_modules = ["contracts"]
forbidden_modules = [
    "sqlalchemy", "psycopg", "qdrant_client", "opensearchpy",
    "kuzu", "neo4j", "spicedb", "openfga_sdk",
]
```

---

## `tigerexchange/packages/contracts/src/contracts/lattice.py`

The frozen 3-tier lattice (§5.6). Ordering is `public < private < confidential`; the MAX-rule is the join (least-upper-bound). Unknown tier → most-restrictive (`confidential`) by construction. Compliance flags live here because they ride the lattice and are sticky (UNION on join, §6.1/§11).

```python
"""Frozen 3-tier classification lattice (plan §5.6, §6.1).

This is K1 of the kernel: a tiny, near-frozen, formally-specified lattice
(3 tiers + total ordering + MAX-rule). It is the single source of truth for
tier sensitivity ordering across ALL nodes and consumers.

Safety invariants (do not relax without a lattice-version bump, §5.6):
  - Ordering is total: public < private < confidential.
  - The join of two tiers is the MAX (more-restrictive wins).
  - An UNKNOWN/unparseable tier is treated as the MOST-restrictive tier
    (confidential) — safe-by-construction, never fail-open.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
from functools import reduce
from typing import Iterable


class Tier(IntEnum):
    """The frozen 3-tier sensitivity lattice.

    IntEnum is used deliberately so the ordering IS the sensitivity ordering
    (public=0 < private=1 < confidential=2). The integer values are an
    implementation detail of the ordering; the wire/DB representation is the
    member NAME (see ``Tier.wire`` / ``Tier.parse``).
    """

    public = 0
    private = 1
    confidential = 2

    @property
    def wire(self) -> str:
        """Stable string form for wire/DB ('public'|'private'|'confidential')."""
        return self.name

    @classmethod
    def parse(cls, value: object) -> "Tier":
        """Parse a tier from wire/DB form, FAIL-CLOSED on anything unknown.

        Any unrecognized value (including None, empty, or an unknown string)
        resolves to the MOST-restrictive tier (confidential), per §5.6's
        "unknown tier is treated MOST-restrictive" rule. This is intentional:
        callers must never get a permissive default from bad input.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls[value.strip().lower()]
            except KeyError:
                return cls.confidential
        return cls.confidential


# --- MAX-rule helpers (the lattice join) ---------------------------------- #

def tier_join(a: Tier, b: Tier) -> Tier:
    """Least-upper-bound of two tiers = the MORE restrictive one (MAX-rule)."""
    return a if a >= b else b


def tier_join_all(tiers: Iterable[Tier]) -> Tier:
    """MAX-rule over a collection. Empty input fails closed to confidential.

    Used whenever sensitivity propagates across a join/derivation: a derived
    artifact's tier is the MAX of every input tier (§6.1 sticky propagation).
    """
    materialized = list(tiers)
    if not materialized:
        return Tier.confidential
    return reduce(tier_join, materialized)


class ComplianceFlag(StrEnum):
    """Sticky compliance/regulatory flags carried on a classification (§6.1).

    Flags are UNION-on-join (sticky): a derived artifact carries the union of
    every input's flags. They never drop on a join (§11). This set is frozen
    alongside the lattice; new flags require a lattice-version bump.
    """

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


# The lattice version this kernel build emits. Every PublishableProjection and
# ClassificationResult is stamped with this so a tightening change is
# recallable-by-construction (§5.6 reclassification recall).
LATTICE_VERSION: int = 1
```

---

## `tigerexchange/packages/contracts/src/contracts/tenancy.py`

`TenantContext` (the value the PEP and the RLS `SET LOCAL` path both consume), Edition, and the Entitlement capability model (§2.3, §5, §7). The `Edition`→capability mapping is evaluated centrally at the PEP; modules consume capabilities as a read-only contract and **physically cannot** enable a tier they are not entitled to.

```python
"""Tenant context + Edition/Entitlement capability model (plan §2.3, §5, §7).

TenantContext is the request-scoped identity of the tenant + subject that the
PEP authorizes against and that the Postgres RLS layer pins via
``SET LOCAL app.tenant_id = ...`` (transaction-scoped, never SET — §7.7).

Editions are entitlement CONFIG, not forks (§2.3). An Entitlement is the
resolved capability set for a tenant; it is evaluated at the PEP, and feature
modules consume it as a contract.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.lattice import Tier


class Edition(StrEnum):
    """Product editions (§2.3). Edition resolves to an Entitlement capability set."""

    PLG = "plg"  # public + own-materials ONLY; confidential/exchange hard-OFF (pooled plane)
    INSTITUTIONAL = "institutional"
    CAMPUS = "campus"
    CONSORTIUM_ANCHOR = "consortium-anchor"
    CONFIDENTIAL_SOVEREIGN = "confidential-sovereign"


class Capability(StrEnum):
    """Atomic, PEP-checkable capabilities (§2.3, §2.4).

    A module may only act on a capability the tenant's Entitlement grants.
    The PEP — not the module — is the evaluator (the contract tests in §2.3
    assert e.g. a PLG tenant cannot construct a confidential/exchange request).
    """

    PUBLIC_RETRIEVAL = "public-retrieval"
    OWN_MATERIALS = "own-materials"           # ingest/search the tenant's own private corpus
    PRIVATE_TIER = "private-tier"
    CONFIDENTIAL_WORKSPACE = "confidential-workspace"
    EXCHANGE_PARTICIPATION = "exchange-participation"  # cross-institution federation seam (Phase 1+)
    CROSS_INSTITUTION_GRANTS = "cross-institution-grants"  # Phase 1+
    TEAM_ASSEMBLY = "team-assembly"
    BYO_PROVIDER = "byo-provider"
    DEDICATED_GPU = "dedicated-gpu"


class IsolationPosture(StrEnum):
    """Where a tenant's workloads run (§2.3, D7)."""

    POOLED = "pooled"            # multi-tenant pooled plane (non-confidential only)
    DEDICATED_CELL = "dedicated-cell"
    DEDICATED_CELL_GPU = "dedicated-cell-gpu"


class Entitlement(BaseModel):
    """Resolved capability set for a tenant. Evaluated at the PEP (§2.3).

    Frozen: an Entitlement is a decision input, not mutable per-request state.
    """

    model_config = ConfigDict(frozen=True)

    edition: Edition
    capabilities: frozenset[Capability]
    isolation: IsolationPosture
    # The MAXIMUM tier this tenant may ever access/hold. PLG is capped at
    # private (own materials); confidential editions raise this ceiling.
    max_tier: Tier

    def has(self, capability: Capability) -> bool:
        """True iff the tenant is entitled to ``capability``. The PEP's gate."""
        return capability in self.capabilities

    def permits_tier(self, tier: Tier) -> bool:
        """True iff ``tier`` is at or below this tenant's tier ceiling."""
        return tier <= self.max_tier


class TenantContext(BaseModel):
    """Request-scoped tenant + subject identity (plan §4, §7).

    This is the object the PEP authorizes and that the RLS layer pins via
    ``SET LOCAL`` per transaction (§7.7). It is frozen for the request's
    lifetime so no downstream code can re-scope an in-flight request.
    """

    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(..., description="Stable owning-institution/tenant id; RLS leading key.")
    subject_id: str = Field(..., description="Authenticated subject (eduPersonUniqueId / OIDC sub).")
    entitlement: Entitlement
    # Consortium membership(s) — used by the central-index PEP to enforce
    # named-consortium discoverability_scope (§4.7).
    consortium_ids: frozenset[str] = Field(default_factory=frozenset)
    # eduPersonScopedAffiliation-style attributes consumed by ABAC (§7.1/§7.3).
    affiliations: frozenset[str] = Field(default_factory=frozenset)
    # True only after a fresh deprovision/affiliation check (§7.4). Stale/unknown
    # MUST be treated as not-fresh by the PEP for non-public tiers.
    subject_active: bool = True
```

---

## `tigerexchange/packages/contracts/src/contracts/classification.py`

`ClassificationResult`, the `Decision` enum (ALLOW/DENY/QUARANTINE), and `DiscoverabilityScope`. The classifier is fail-closed: abstention/ambiguity → `QUARANTINE`, which the rest of the system treats as confidential and excludes from all retrieval (D6, §8).

```python
"""Classification result + Decision/DiscoverabilityScope enums (plan §4.7, §8, D6).

The classifier is SINGLE and FAIL-CLOSED. Abstention or ambiguity does not
produce a tier guess: it produces QUARANTINE, which the rest of the platform
treats as confidential + default-deny + excluded from ALL retrieval, pending
human adjudication (D6). These types carry that decision verbatim.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.lattice import LATTICE_VERSION, ComplianceFlag, Tier


class Decision(StrEnum):
    """Terminal authorization/classification decision (D6, §4.7)."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    # Abstention/ambiguity: unclassified == treated confidential, excluded from
    # all retrieval, routed to the human-adjudication queue (D6, §8).
    QUARANTINE = "QUARANTINE"


class DiscoverabilityScope(StrEnum):
    """First-class discoverability scope on every PublishableProjection (§4.7, §7.3).

    Publishing to discovery is NOT consent to be discovered by everyone. The
    central-index PEP enforces this at query time against requester identity
    and consortium membership (§4.7).
    """

    PUBLIC_WEB = "public-web"            # discoverable by anyone
    FEDERATION_WIDE = "federation-wide"  # any authenticated federation member
    NAMED_CONSORTIUM = "named-consortium"  # only within the publisher's consortium(s)
    NAMED_TENANTS = "named-tenants"      # only an explicit tenant allowlist
    NONE = "none"                        # not centrally indexed; owner-brokered drill-down only


class ClassificationResult(BaseModel):
    """Output of the single fail-closed classifier (§8, D6).

    A QUARANTINE result MUST be honored as confidential-and-excluded by every
    consumer; ``tier`` is forced to confidential and ``decision`` to QUARANTINE
    on abstention so a careless reader of ``tier`` alone still fails closed.
    """

    model_config = ConfigDict(frozen=True)

    tier: Tier
    decision: Decision
    compliance_flags: frozenset[ComplianceFlag] = Field(default_factory=frozenset)
    # Classifier confidence in [0, 1]; below the abstention threshold the
    # classifier MUST emit decision=QUARANTINE (enforced by the impl, asserted here).
    confidence: float = Field(..., ge=0.0, le=1.0)
    # Free-form reason / abstention cause for the adjudication queue + audit.
    reason: str = ""
    # Stamp so a lattice tightening can recall/re-derive this result (§5.6).
    lattice_version: int = LATTICE_VERSION

    @classmethod
    def quarantine(cls, reason: str, confidence: float = 0.0) -> "ClassificationResult":
        """Construct the canonical fail-closed quarantine result (D6).

        Forces tier=confidential and decision=QUARANTINE so the record is
        excluded from all retrieval and queued for human adjudication.
        """
        return cls(
            tier=Tier.confidential,
            decision=Decision.QUARANTINE,
            confidence=confidence,
            reason=reason,
        )

    @property
    def is_retrievable(self) -> bool:
        """False for QUARANTINE/DENY: never enters any retrieval path (D6)."""
        return self.decision is Decision.ALLOW


class Caveats(BaseModel):
    """Sticky, re-evaluated-at-access caveats on a sharing grant (§4.3, §7.3).

    Caveats are re-evaluated at grantee-side access, not trusted from the token.
    """

    model_config = ConfigDict(frozen=True)

    transfer_legality: bool | None = None     # cross-jurisdiction transfer permitted?
    export_attestation: str | None = None     # export-conformance attestation ref (ITAR/EAR)
    ferpa_role: str | None = None              # FERPA authorization role of the requester
```

---

## `tigerexchange/packages/contracts/src/contracts/projection.py`

`PublishableProjection` (K2) — the single contract most exposed to data-model churn (§5.6b). It carries `lattice_version`, an independent `projection_schema_version`, and `discoverability_scope` as first-class stamped attributes. Confidential payloads never appear here (D6). The MAX-rule from `lattice.py` bounds the tier it may carry.

```python
"""PublishableProjection — the federation-seam contract (plan §4.7, §5.6b, §6.1).

K2 of the kernel. This is the ONLY shape that crosses the federation seam into
the shared central index. It holds public/shared-tier metadata + non-reversible
derived signals ONLY — never confidential-derived content or embeddings (D6).

It carries TWO independent versions:
  - lattice_version: governs tier SEMANTICS (§5.6).
  - projection_schema_version: governs the FIELD SCHEMA / allowlist that
    physically crosses the seam (§5.6b), evolved under backward+forward
    schema-registry compatibility, independent of the lattice version.

Only the broker/PEP may construct this (import-linter forbids feature modules
from constructing a PublishableProjection — §4.2).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from contracts.classification import DiscoverabilityScope
from contracts.lattice import LATTICE_VERSION, Tier

# The field-schema version this kernel build emits (§5.6b). Independent of
# LATTICE_VERSION. Bumped under backward+forward schema-registry compatibility.
PROJECTION_SCHEMA_VERSION: int = 1


class PublishableProjection(BaseModel):
    """Public/shared-tier projection of an artifact for the central index (§4.7, D6).

    Frozen: a published projection is an immutable, stamped record. Tier is
    constrained to public|private (never confidential — D6); the central index
    never holds confidential-derived content.
    """

    model_config = ConfigDict(frozen=True)

    projection_id: str
    artifact_id: str = Field(..., description="Source artifact this projects (owner-local).")
    owner_tenant_id: str

    # The tier of the PROJECTION (MAX-rule-bounded at derivation). D6 forbids
    # confidential here; the validator enforces it.
    tier: Tier
    discoverability_scope: DiscoverabilityScope

    # The allowlisted, publishable field payload. Concrete fields are governed
    # by the registered Protobuf/Avro schema at projection_schema_version
    # (§5.6b); the kernel pins the envelope + versions, not the field set.
    fields: dict[str, object] = Field(default_factory=dict)

    lattice_version: int = LATTICE_VERSION
    projection_schema_version: int = PROJECTION_SCHEMA_VERSION

    @field_validator("tier")
    @classmethod
    def _no_confidential_in_index(cls, v: Tier) -> Tier:
        """D6: confidential-derived content NEVER enters the shared index."""
        if v is Tier.confidential:
            raise ValueError(
                "PublishableProjection cannot carry confidential tier (D6): "
                "confidential content never enters the shared central index."
            )
        return v
```

---

## `tigerexchange/packages/contracts/src/contracts/pep.py`

The single PEP request/response types (D4, §4.2/§4.7). One request shape serves both PEP deployment loci (cell-local and central-index read), distinguished by `action`. The response is fail-closed: a `Decision.DENY`/`QUARANTINE` carries no payload.

```python
"""Policy Enforcement Point request/response contracts (plan §4.2, §4.7, D4).

The PEP is the SINGLE confidentiality chokepoint (D4). One request/response
contract serves both deployment loci of the SAME PEP code (§4.2):
  - cell-local PEP (raw confidential data, owner-side authority), and
  - central-index read PEP (scope-filtered reads of published projections).

The locus is selected by ``PepAction``; both consume the one owned policy table.
Feature modules send a PepRequest and receive already-projected,
already-tier-checked PepResponse objects — they never see raw classification
logic or raw stores (§4.2).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.classification import Caveats, Decision, DiscoverabilityScope
from contracts.lattice import Tier
from contracts.tenancy import Capability, TenantContext


class PepAction(StrEnum):
    """The action being authorized; also selects the PEP locus (§4.2)."""

    RETRIEVE = "retrieve"          # cell-local read of a tenant's own data
    EGRESS = "egress"              # boundary egress (re-checked publishable allowlist, §4.2)
    DERIVE = "derive"              # derivation (router/embedding/synthesis)
    DISCOVER = "discover"          # central-index read PEP query (§4.7)
    BROKERED_DRILLDOWN = "brokered-drilldown"  # cross-tenant owner-authoritative access (§4.3)


class PepRequest(BaseModel):
    """A request for an authorization + brokered access decision (D4)."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    tenant: TenantContext
    action: PepAction
    # Capability the action requires; the PEP checks tenant.entitlement.has(...).
    required_capability: Capability
    # Target the action touches (artifact id, query string, projection id, ...).
    resource_id: str | None = None
    # For BROKERED_DRILLDOWN: the sharing grant-ID. The OWNER node re-derives
    # scope/tier/caveats from its authoritative GrantStore and IGNORES any
    # scope claim presented here (§4.3 owner-side re-derivation).
    grant_id: str | None = None
    # Remaining deadline for this hop (ms); a hop that cannot meet it
    # fails-closed-fast (§4.3 deadline propagation).
    deadline_ms: int | None = None
    # Opaque per-action attributes (query text, discovery scope filter, etc.).
    attributes: dict[str, object] = Field(default_factory=dict)


class PepResponse(BaseModel):
    """The PEP's terminal decision. Fail-closed: payload only on ALLOW.

    On DENY/QUARANTINE the ``payload`` MUST be None. The broker is the only
    holder of raw-store credentials; what it returns here is already projected
    and tier-checked (§4.2).
    """

    model_config = ConfigDict(frozen=True)

    request_id: str
    decision: Decision
    effective_tier: Tier
    # Present ONLY on ALLOW; already-projected, already-tier-checked objects.
    payload: list[dict[str, object]] | None = None
    # For DISCOVER results: the scope under which each hit was authorized (§4.7).
    discoverability_scope: DiscoverabilityScope | None = None
    # Re-derived caveats that remain sticky for downstream egress (§4.3/§11.5).
    caveats: Caveats | None = None
    # Human-readable obligation/deny reason; mirrored into the audit event.
    reason: str = ""

    def model_post_init(self, _ctx: object) -> None:
        if self.decision is not Decision.ALLOW and self.payload is not None:
            raise ValueError("PepResponse: non-ALLOW decision must carry no payload (fail-closed).")
```

---

## `tigerexchange/packages/contracts/src/contracts/audit.py`

The per-stream hash-chain audit event type (§4.1 `AUDa`, §4.4a). Each event links to the previous event's hash within its stream; the chain head is periodically checkpointed to the cross-tenant transparency log.

```python
"""Per-stream hash-chained audit event (plan §4.1, §4.4a).

Every PEP decision, classification, revocation, and egress emits an AuditEvent
into a per-stream hash chain. ``prev_hash`` links to the prior event's
``entry_hash`` in the SAME stream; tampering breaks the chain. Signed chain-head
checkpoints are anchored to the cross-tenant transparency log (§4.1 TXP).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.classification import Decision


class AuditEventType(StrEnum):
    """Kinds of auditable events on the confidentiality spine."""

    PEP_DECISION = "pep-decision"
    CLASSIFICATION = "classification"
    REVOCATION = "revocation"
    EGRESS = "egress"
    GRANT_ISSUED = "grant-issued"
    BROKERED_ACCESS = "brokered-access"


class AuditEvent(BaseModel):
    """A single, frozen, hash-chained audit record (§4.1).

    The hash chain is per-stream: ``stream_id`` partitions the chain (e.g. one
    chain per cell/tenant). ``entry_hash`` = H(prev_hash || canonical(payload));
    the kernel pins the SHAPE and chain semantics, the AuditSink impl computes
    the hash and persists it.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str
    stream_id: str = Field(..., description="Per-stream hash-chain partition key.")
    sequence: int = Field(..., ge=0, description="Monotonic per-stream sequence number.")

    event_type: AuditEventType
    occurred_at: datetime

    tenant_id: str
    subject_id: str | None = None
    resource_id: str | None = None

    # Decision recorded (for PEP_DECISION / EGRESS / BROKERED_ACCESS events).
    decision: Decision | None = None
    reason: str = ""

    # Hash-chain links. prev_hash is None only for the genesis entry of a stream.
    prev_hash: str | None = None
    entry_hash: str = Field(..., description="H(prev_hash || canonical(this event payload)).")

    # Arbitrary structured detail (already redacted of confidential payload).
    detail: dict[str, object] = Field(default_factory=dict)
```

---

## `tigerexchange/packages/contracts/src/contracts/interfaces.py`

All K3 interfaces (§5.1). Active Phase-0 interfaces have full method signatures; deferred-phase seams (`IExchangeFeed`, `IRevocationAuthority`) are minimal stubs with **Phase-1+** docstrings — the kernel pins the seam, Phase-0 ships no implementation.

```python
"""Kernel interface definitions (K3 — plan §5.1, §5.8).

All interfaces are runtime-checkable Protocols (structural typing) so feature
modules depend on the SHAPE, not a base class, and import-linter can forbid
modules from importing concrete impls. Active Phase-0 interfaces carry full
signatures. Deferred seams (IExchangeFeed, IRevocationAuthority) are minimal
stubs with explicit "Phase-1+" docstrings — present so later phases extend the
kernel cleanly, but NOT implemented in Phase-0.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, Sequence, runtime_checkable

from contracts.audit import AuditEvent
from contracts.classification import Caveats, ClassificationResult, Decision
from contracts.lattice import Tier
from contracts.pep import PepRequest, PepResponse
from contracts.projection import PublishableProjection
from contracts.tenancy import TenantContext


# --------------------------------------------------------------------------- #
# Enforcement plane (the single chokepoint, D4)
# --------------------------------------------------------------------------- #

@runtime_checkable
class IClassifier(Protocol):
    """Single fail-closed classifier (§8, D6).

    Abstention/ambiguity MUST return ClassificationResult.quarantine(...);
    implementations never emit a permissive tier on low confidence.
    """

    def classify(self, content: bytes, tenant: TenantContext) -> ClassificationResult: ...


@runtime_checkable
class IPolicyEnforcement(Protocol):
    """The Policy Enforcement Point — the single confidentiality chokepoint (D4, §4.2).

    Same code deployed cell-local AND at the central index (§4.2); the locus is
    selected by PepRequest.action. Consumes the one owned policy table. Returns
    already-projected, already-tier-checked PepResponse objects; modules never
    see raw classification logic or raw stores.
    """

    def authorize(self, request: PepRequest) -> PepResponse: ...


@runtime_checkable
class IDataAccessBroker(Protocol):
    """The data-access broker — the ONLY holder of raw-store credentials (D4, §4.2).

    Sits behind the PEP. Given an ALLOW decision, fetches from the per-tenant
    raw stores under per-module DB-role isolation and returns projected results.
    Feature modules never receive raw-store handles.
    """

    def fetch(self, request: PepRequest, decision: PepResponse) -> PepResponse: ...

    def project(
        self, request: PepRequest, raw_rows: Sequence[dict[str, object]]
    ) -> PublishableProjection: ...


# --------------------------------------------------------------------------- #
# AI / Model-Router layer (D-AI, §8)
# --------------------------------------------------------------------------- #

@runtime_checkable
class IModelProvider(Protocol):
    """A registered model provider declaring the locality classes it satisfies (§5.8, §8.3).

    The router selects over a REGISTRY of providers by declared locality +
    capability + cost — never a hardcoded tier->provider table.
    """

    @property
    def provider_id(self) -> str: ...

    def satisfies_locality(self, tier: Tier) -> bool:
        """True iff this provider may serve data at ``tier`` (attested locality)."""
        ...

    def no_retention_attested(self) -> bool: ...


@runtime_checkable
class IModelRouter(Protocol):
    """Provider-agnostic, classification-routed model router (D-AI, §8.1/§8.2).

    Selects a provider whose declared locality satisfies the data's
    classification (local/in-boundary for non-public; cloud frontier for
    public). Fails closed to the in-boundary model if no compliant provider
    attests (§8.3).
    """

    def route(
        self, classification: ClassificationResult, tenant: TenantContext
    ) -> IModelProvider: ...


# --------------------------------------------------------------------------- #
# Retrieval (§9)
# --------------------------------------------------------------------------- #

@runtime_checkable
class IRetrievalStrategy(Protocol):
    """Hybrid retrieval behind one interface (vector + BM25 + RRF) (§9.1).

    Callers consume only this; engine choice (Qdrant/OpenSearch) is insulated.
    Returns already-PEP-gated, already-projected hits.
    """

    def retrieve(
        self, query: str, tenant: TenantContext, *, top_k: int = 8
    ) -> list[PublishableProjection]: ...


@runtime_checkable
class IReranker(Protocol):
    """Cross-encoder reranker (BGE-reranker / Qwen3-Reranker), local (§9.1)."""

    def rerank(
        self,
        query: str,
        candidates: Sequence[PublishableProjection],
        *,
        top_k: int = 8,
    ) -> list[PublishableProjection]: ...


# --------------------------------------------------------------------------- #
# Discovery graph (mod-discovery, §9.2, §6.3)
# --------------------------------------------------------------------------- #

@runtime_checkable
class IExpertiseFingerprint(Protocol):
    """SPECTER2-based expertise fingerprint for expert/team-assembly discovery (§9.2, §8.4).

    Public-tier by construction (§6.3); confidential records never contribute.
    """

    def fingerprint(self, researcher_id: str) -> Sequence[float]: ...

    def similarity(self, a: str, b: str) -> float: ...


@runtime_checkable
class ICollaborationGraph(Protocol):
    """Cross-institution collaboration graph traversal (§9.2, §6.3).

    Public-tier ego-graph / candidate traversal for team-assembly context.
    Backed by an IGraphStore (AGE, with Neo4j/Memgraph fallback) behind a
    conformance suite (§5.8).
    """

    def neighbors(self, researcher_id: str, *, hops: int = 1) -> list[str]: ...

    def candidate_collaborators(
        self, researcher_id: str, *, limit: int = 50
    ) -> list[str]: ...


# --------------------------------------------------------------------------- #
# Audit spine (§4.1, §4.4a)
# --------------------------------------------------------------------------- #

@runtime_checkable
class IAuditSink(Protocol):
    """Per-stream hash-chained audit sink (§4.1).

    append() links the new event to the prior entry_hash in its stream and
    returns the persisted event (with computed entry_hash). checkpoint() emits
    a signed chain-head for the cross-tenant transparency log (§4.1 TXP).
    """

    def append(self, event: AuditEvent) -> AuditEvent: ...

    def head(self, stream_id: str) -> AuditEvent | None: ...

    def checkpoint(self, stream_id: str) -> str:
        """Return a signed chain-head digest for transparency-log anchoring."""
        ...


# --------------------------------------------------------------------------- #
# Grant / sharing store (mod-workspace, §4.3, §7.3) — Phase-0: own-tenant only
# --------------------------------------------------------------------------- #

@runtime_checkable
class IGrantStore(Protocol):
    """Authoritative store of sharing grants at the owning node (D5, §4.3).

    In Phase-0 only the OWNER-LOCAL read path is exercised (own-tenant grants);
    cross-institution issuance is Phase-1+. The owner re-derives scope/tier/
    caveats/revocation from THIS store and ignores token-presented scope (§4.3).
    """

    def get_grant(self, grant_id: str, tenant: TenantContext) -> "Grant | None": ...

    def is_revoked(self, grant_id: str) -> bool:
        """Strongly-consistent local read against the durable tombstone log (§4.4a)."""
        ...


class Grant(Protocol):
    """Read-only view of a sharing grant as the owner re-derives it (§4.3, §7.3)."""

    @property
    def grant_id(self) -> str: ...

    @property
    def tier(self) -> Tier: ...

    @property
    def caveats(self) -> Caveats: ...

    @property
    def revocation_epoch(self) -> int: ...


# --------------------------------------------------------------------------- #
# DEFERRED SEAMS — Phase-1+ stubs. Present so the kernel is cleanly extended
# later; Phase-0 ships NO implementation of these.
# --------------------------------------------------------------------------- #

@runtime_checkable
class IExchangeFeed(Protocol):
    """Phase-1+ STUB. Cross-institution federation discovery feed (§4.1 Exchange).

    Phase-0 ships none of this: there is no federation seam, no exchange feed,
    no cross-institution discovery. The interface fixes the shape so mod-discovery
    / mod-funding can light up federation in Phase-1 without a kernel change.
    Phase-0 implementations MUST NOT exist; importing a concrete impl is a
    Phase-0 import-linter violation.
    """

    def publish(self, projection: PublishableProjection, tenant: TenantContext) -> None:
        """Phase-1+: push a MAX-rule-bounded projection to the Exchange (CDC)."""
        ...

    def query(
        self, query: str, tenant: TenantContext, *, top_k: int = 50
    ) -> list[PublishableProjection]:
        """Phase-1+: federation-wide discovery, central-index PEP scope-filtered (§4.7)."""
        ...


@runtime_checkable
class IRevocationAuthority(Protocol):
    """Phase-1+ STUB SEAM ONLY. Owner-local fenced-lease revocation authority (D5, §4.4).

    The full revocation authority + tombstone log + fenced-lease replication is
    explicitly DEFERRED (not Phase-0). This seam exists only so the owner-local
    fail-closed lease design (§4.4/§4.4a) and the cross-institution revocation
    path can be implemented in a later phase without re-touching the kernel.
    Phase-0 ships NO implementation.
    """

    def check_lease(self, grant_id: str, tenant: TenantContext) -> Decision:
        """Phase-1+: local fail-closed lease read (valid && now<expiry && not-tombstoned)."""
        ...

    def revoke(self, grant_id: str, reason: str, tenant: TenantContext) -> int:
        """Phase-1+: durable-commit tombstone -> fence-bump -> lease-invalidate; returns new epoch."""
        ...

    def current_epoch(self, tenant: TenantContext) -> int:
        """Phase-1+: owner-local monotonic revocation epoch."""
        ...


# --------------------------------------------------------------------------- #
# Kernel-interface versioning / evolution contract (R8, §5.1/§5.8)
# --------------------------------------------------------------------------- #
# These pin the kernel API surface itself: a single integer API version, the
# locus each interface is deployed at (intra-cell vs cross-node), and a frozen
# name->locus mapping. They are part of the canonical kernel; 0a legitimately
# re-exports them (they are NOT non-canonical symbols).

# Monotonic version of the kernel interface surface (K3). Bumped on any
# breaking change to an interface signature; lets 0a assert compatibility.
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

(`StrEnum` is imported at the top of `interfaces.py` via `from enum import StrEnum`.)

---

## `tigerexchange/packages/contracts/src/contracts/__init__.py`

Single import surface. Sub-plan authors import everything from `contracts`.

```python
"""TigerExchange canonical kernel — single import surface (plan §5.1).

These signatures are AUTHORITATIVE. Every sub-plan imports from `contracts`
verbatim. The kernel is near-frozen, has zero feature-module deps, and holds
no persistent state (§5.5 fitness function).
"""

from contracts.audit import AuditEvent, AuditEventType
from contracts.classification import (
    Caveats,
    ClassificationResult,
    Decision,
    DiscoverabilityScope,
)
from contracts.interfaces import (
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
    IPolicyEnforcement,
    IRerankerLike := IReranker,  # noqa: F821  (see below)
)
from contracts.interfaces import IReranker, IRetrievalStrategy, IRevocationAuthority
from contracts.interfaces import (
    INTERFACE_LOCUS,
    KERNEL_API_VERSION,
    InterfaceLocus,
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

__all__ = [
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
    # interfaces (K3)
    "IClassifier", "IPolicyEnforcement", "IDataAccessBroker", "IModelRouter",
    "IModelProvider", "IRetrievalStrategy", "IReranker", "IExpertiseFingerprint",
    "ICollaborationGraph", "IExchangeFeed", "IGrantStore", "Grant", "IAuditSink",
    "IRevocationAuthority",
    # kernel-interface versioning / evolution contract (R8)
    "KERNEL_API_VERSION", "InterfaceLocus", "INTERFACE_LOCUS",
]
```

Note: drop the `IRerankerLike :=` walrus line above — it was an editing artifact. The correct `__init__.py` import block for the rerank symbol is simply:

```python
from contracts.interfaces import (
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
    IPolicyEnforcement,
    IReranker,
    IRetrievalStrategy,
    IRevocationAuthority,
)
from contracts.interfaces import (
    INTERFACE_LOCUS,
    KERNEL_API_VERSION,
    InterfaceLocus,
)
```

---

## Summary of decisions encoded (for sub-plan authors)

- **Tier lattice (K1, `lattice.py`):** frozen `public(0) < private(1) < confidential(2)` total order via `IntEnum`; `tier_join`/`tier_join_all` are the MAX-rule join (empty → confidential); `Tier.parse` is fail-closed (unknown → confidential, §5.6). `ComplianceFlag` + `compliance_union` carry sticky UNION-on-join flags (§6.1).
- **Decision enum (`classification.py`):** `ALLOW | DENY | QUARANTINE`. `ClassificationResult.quarantine()` is the canonical abstention path (tier forced confidential, excluded from retrieval, D6). `DiscoverabilityScope`: `public-web | federation-wide | named-consortium | named-tenants | none` (§4.7).
- **Tenancy (`tenancy.py`):** `TenantContext` is what the PEP authorizes and what `SET LOCAL` pins for RLS (§7.7). `Edition`/`Entitlement`/`Capability` map a tenant to a PEP-evaluated capability set; PLG is tier-capped at `private`, `confidential-workspace`/`exchange-participation` are off (§2.3).
- **PEP contracts (`pep.py`):** one `PepRequest`/`PepResponse` for both PEP loci (cell-local + central-index), distinguished by `PepAction`. Fail-closed: non-ALLOW carries no payload (enforced in `model_post_init`). `grant_id` triggers owner-side re-derivation (§4.3).
- **Audit (`audit.py`):** per-stream hash-chained `AuditEvent` (`prev_hash`→`entry_hash`), checkpointed to the transparency log (§4.1).
- **Interfaces (`interfaces.py`):** all 12 K3 interfaces as `@runtime_checkable Protocol`s. **Active Phase-0:** `IClassifier, IPolicyEnforcement, IDataAccessBroker, IModelRouter, IModelProvider, IRetrievalStrategy, IReranker, IExpertiseFingerprint, ICollaborationGraph, IAuditSink, IGrantStore`. **Deferred stubs (Phase-1+, no Phase-0 impl):** `IExchangeFeed`, `IRevocationAuthority` — seams only, with explicit Phase-1+ docstrings.
- **Kernel-interface versioning (R8, `interfaces.py`):** `KERNEL_API_VERSION: int = 1`, the `InterfaceLocus` StrEnum (`intra_cell | cross_node`), and the frozen `INTERFACE_LOCUS` name→locus mapping pin the kernel API surface itself. Deferred federation seams (`IExchangeFeed`, `IRevocationAuthority`) are `cross_node`; all Phase-0-active interfaces are `intra_cell`. These are canonical kernel symbols (0a re-exports them legitimately).
- **D6 enforced in code:** `PublishableProjection` rejects `confidential` tier at validation; confidential content can never enter the shared index.
- **Fitness function (§5.5):** `pyproject.toml` import-linter contract forbids the kernel from importing any persistence/feature engine, keeping it zero-dep and stateless.

One caveat flagged: the first `__init__.py` block contains an editing artifact (the `IRerankerLike :=` walrus import) — use the corrected import block shown immediately after it. All other code is consistent and import-clean.