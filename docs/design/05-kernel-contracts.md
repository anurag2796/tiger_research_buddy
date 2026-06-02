# 05 — Kernel Contracts: the frozen `contracts` package (verbatim types + Protocols)

> **What this document is.** The `tigerexchange/packages/contracts` package is the *near-frozen shared kernel* that every other package imports and that itself imports nothing feature-side. This file gives you the **actual, copy-pasteable Python** for that kernel: the tier lattice, the value objects (Pydantic v2 frozen models), the enums, the request/response types for the Policy Enforcement Point (PEP), and **all `I*` Protocol interfaces** with full method signatures.
>
> **Who reads this.** The builder. You are expected to type these definitions into the kernel package essentially verbatim, then implement everything else *against* these Protocols. When this document and a feature LLD disagree about a kernel type signature, **this document wins** (it is the kernel; the kernel is upstream of every feature).
>
> **Authority chain.** `_design-brief.json` (locked) → `CONVENTIONS-single-box.md` (this-file-wins pins) → this document for kernel shapes. Decisions referenced here are **D3, D4, D6, D7, D10** (plus D2 for the deferred federation stubs). Decision IDs are **D1..D14 only** — there are no other labels.
>
> **Cross-references.** Security semantics that *consume* these contracts: see `06-security-spine-lld.md`. The PEP decision order is specified there and summarized here. Concrete DDL for the storage rows behind these value objects: `13-data-model-and-schemas.md`. The data-plane Protocol implementations (`IVectorStore`/`ILexicalIndex`/`IGraph`): `07-data-layer-and-retrieval-lld.md`. The AI-plane Protocol implementations (`IModelRouter`/`IModelProvider`): `08-ai-plane-and-model-router-lld.md`. Key custody (`IKms`): `06-security-spine-lld.md`. The deferred federation stubs (`IExchangeFeed`/`IRevocationAuthority`): `15-future-federation-interfaces.md`.

---

## 0. Table of contents

1. [Why a frozen kernel exists, and the kernel fitness function](#1-why-a-frozen-kernel-exists-and-the-kernel-fitness-function)
2. [Package layout, imports, and pinned versions](#2-package-layout-imports-and-pinned-versions)
3. [The Tier lattice and the MAX-rule join](#3-the-tier-lattice-and-the-max-rule-join)
4. [Capability + Entitlement (`permits_tier`)](#4-capability--entitlement-permits_tier)
5. [TenantContext (frozen, request-scoped)](#5-tenantcontext-frozen-request-scoped)
6. [Classification: ClassificationResult + Decision + `is_retrievable`](#6-classification-classificationresult--decision--is_retrievable)
7. [PublishableProjection (the only shape that crosses into the shared index)](#7-publishableprojection-the-only-shape-that-crosses-into-the-shared-index)
8. [PEP request/response types (PepRequest / PepResponse)](#8-pep-requestresponse-types-peprequest--pepresponse)
9. [Supporting value objects (AuditEvent, RelationTuple, RetrievedItem, GenerationRequest)](#9-supporting-value-objects)
10. [All `I*` Protocols — full method signatures](#10-all-i-protocols--full-method-signatures)
11. [The complete `contracts` package as files](#11-the-complete-contracts-package-as-files)
12. [Acceptance tests this document must satisfy (P0.0)](#12-acceptance-tests-this-document-must-satisfy-p00)
13. [What is deliberately NOT in the kernel](#13-what-is-deliberately-not-in-the-kernel)

---

## 1. Why a frozen kernel exists, and the kernel fitness function

The whole system is a **modular monolith** (D2): one FastAPI process, one Postgres, a small fixed set of model-serving processes. Feature modules (`mod-discovery`, `mod-lit-intelligence`, `mod-funding`, `mod-workspace`) are *dumb plug-ins behind the PEP* (D3). For that to be true, there must be exactly one shared vocabulary of types and interfaces that everyone agrees on and nobody can fork. That is the kernel.

**The kernel fitness function — three invariants, all CI-enforced.** A symbol belongs in `contracts` if and only if it satisfies *all three*:

| # | Invariant | Why | How enforced |
|---|-----------|-----|--------------|
| 1 | **Zero feature dependencies.** The kernel imports only the standard library + `pydantic` + `typing`. It imports nothing from `mod-*`, nothing from the data plane, nothing from the AI plane, nothing from the security implementation. | If the kernel imported a feature, the feature could not import the kernel without a cycle, and the "everyone shares one vocabulary" property collapses. | `import-linter` contract `kernel-no-feature-deps`: `contracts` is forbidden to import any package except stdlib/pydantic. Fails CI on violation. |
| 2 | **No persistent state, no I/O.** Kernel modules define types, enums, pure functions, and Protocols. They open no sockets, touch no files, hold no module-level mutable singletons, run no DB queries. | A type that does I/O is not a contract; it is an implementation, and implementations belong behind a Protocol where they can be swapped (e.g. Postgres → future Qdrant) without editing the kernel. | AST test `test_kernel_is_pure`: scans `contracts/**.py` and asserts no `import sqlalchemy/asyncpg/httpx/socket/open(...)`, no module-level non-constant assignments. |
| 3 | **Referenced by ≥ 2 packages.** Every public kernel symbol is imported by at least two distinct downstream packages (or is a Protocol intended to be implemented by one package and called by ≥ 1 other). | A symbol used by only one package is that package's private detail, not shared vocabulary; putting it in the kernel inflates the frozen surface a 30B builder must keep stable. | Review-time rule + an AST audit `test_kernel_symbols_have_two_consumers` that greps the workspace for importers; a symbol with < 2 importers is flagged (warning at P0, hard gate from P0.8). |

> **Rationale (chosen over alternatives).** We chose a *single frozen kernel package* over (a) duplicating types per module (a 30B builder will drift two copies of `Tier` and create a silent confidentiality hole) and (b) a "shared utils" grab-bag with no fitness rule (becomes a god-module that every change touches, defeating the modular-monolith boundary). The fitness function is the objective test that keeps the kernel small and stable.

**"Near-frozen", not "frozen forever".** Adding a *new* Protocol or a *new* enum member is allowed when a phase needs it (e.g. a P1 capability). **Changing the meaning or signature of an existing kernel symbol is a breaking change** and requires updating every consumer in the same commit. Treat the kernel like a wire protocol.

---

## 2. Package layout, imports, and pinned versions

```
tigerexchange/
  packages/
    contracts/
      __init__.py            # re-exports the public surface
      tiers.py               # Tier, tier_join, tier_join_all
      capabilities.py        # Capability, Entitlement
      tenant.py              # TenantContext
      classification.py      # Decision, ClassificationResult
      projection.py          # DiscoverabilityScope, PublishableProjection
      pep.py                 # PepAction, PepRequest, PepResponse, PepDecision
      audit.py               # AuditEvent
      values.py              # RelationTuple, RetrievedItem, GenerationRequest/Result, KeyRef
      protocols.py           # ALL I* Protocols
```

**Hard environment pins (do not deviate).**

* Python **3.11+ (NOT 3.12)** — the Jetson JetPack 6.2 wheel set is built against 3.11; 3.12 breaks the pinned CUDA wheels. Use `from __future__ import annotations` in every module so all annotations are strings (cheap, forward-ref safe).
* `pydantic >= 2.7, < 3` — Pydantic **v2** only. All value objects use `model_config = ConfigDict(frozen=True)` for immutability and `@field_validator` / `@model_validator` (v2 API). Do **not** use v1 `class Config:` or `@validator`.
* No third-party imports in the kernel beyond `pydantic`. `typing.Protocol`, `enum`, `dataclasses` (we use Pydantic, not dataclasses, for value objects), `datetime`, `uuid` are stdlib and allowed.

> **Why `StrEnum` for capabilities/tiers and not bare `str`?** `StrEnum` (stdlib since 3.11) gives you a closed set of string-valued members: JSON-serializable, comparable to plain strings, but the type checker (`mypy`) flags a typo like `Capability.PUBLIC_RETREIVAL`. A 30B builder mistyping a capability string is exactly the failure we are designing out. We chose `StrEnum` over `IntEnum` because these values are persisted/logged and a human reading an audit row wants `"confidential_retrieval"`, not `3`.

---

## 3. The Tier lattice and the MAX-rule join

The confidentiality tier is the spine of the whole security model. There are **exactly three tiers**, totally ordered by restrictiveness:

```
public  <  private  <  confidential
(least restrictive)        (most restrictive)
```

* **public** — may enter the SHARED cross-tenant index (D6); may be sent to a cloud model (D-not-applicable: see `08`); discoverable across tenants.
* **private** — tenant-internal, not cross-tenant-shared by default; local-only inference.
* **confidential** — the highest tier. Confidential content (drafts, prior winning proposals) **never** enters the shared cross-tenant index (D6), is **local-only inference always** (D10), and is the target of crypto-shred (D7). The *unknown / abstained* classification collapses to **confidential** (fail-closed).

### 3.1 The MAX-rule (`tier_join` / `tier_join_all`)

When a derived artifact is produced from multiple inputs (e.g. a generated draft grounded on a public paper *and* a confidential prior proposal), its tier is the **maximum (most restrictive)** of all input tiers. This is the **MAX-rule** and it is non-negotiable: it is the mathematical reason a confidential input can never be laundered down to public through a derivation.

```python
tier_join(public, confidential) == confidential
tier_join(private, public)      == private
tier_join_all([public, public]) == public
tier_join_all([])               == confidential   # <-- unknown -> MOST restrictive
```

> **The empty-list rule is load-bearing and is an acceptance test (P0.0).** `tier_join_all([]) == confidential`. An empty input set means *we do not know what went into this*, and "unknown → most restrictive" is the fail-closed default. A 30B builder's natural instinct is to return the *least* restrictive identity element (`public`) for an empty join, which would be a fail-OPEN bug. We pin the opposite explicitly and test it. Chosen over returning `public` (fail-open) and over raising on empty (forces every caller to special-case empty derivations, inviting an unchecked path that defaults to public).

### 3.2 `tiers.py` (verbatim)

```python
from __future__ import annotations

from enum import IntEnum
from typing import Iterable


class Tier(IntEnum):
    """Confidentiality lattice. ORDER MATTERS: higher int == more restrictive.

    We use IntEnum (not StrEnum) for Tier specifically because the MAX-rule is a
    numeric max() over a total order, and IntEnum makes max()/comparison correct
    and obvious. The persisted/serialized form is the .name (a string) via
    .to_label()/from_label below, so audit rows still read "confidential".
    """

    PUBLIC = 0
    PRIVATE = 1
    CONFIDENTIAL = 2

    def to_label(self) -> str:
        return self.name.lower()

    @classmethod
    def from_label(cls, label: str) -> "Tier":
        try:
            return cls[label.strip().upper()]
        except KeyError as exc:  # unknown label -> fail closed
            raise ValueError(f"unknown tier label: {label!r}") from exc


# The most-restrictive tier, used as the fail-closed default everywhere.
MOST_RESTRICTIVE_TIER: Tier = Tier.CONFIDENTIAL


def tier_join(a: Tier, b: Tier) -> Tier:
    """Pairwise MAX-rule join: the more restrictive of the two tiers."""
    return a if a >= b else b


def tier_join_all(tiers: Iterable[Tier]) -> Tier:
    """MAX-rule over an arbitrary set of tiers.

    CRITICAL fail-closed contract: an EMPTY input returns CONFIDENTIAL
    (unknown provenance -> most restrictive). Do NOT change this to PUBLIC.
    """
    result = Tier.PUBLIC
    seen = False
    for t in tiers:
        seen = True
        result = tier_join(result, t)
    if not seen:
        return MOST_RESTRICTIVE_TIER  # tier_join_all([]) == CONFIDENTIAL
    return result
```

> **Implementation note.** We intentionally do **not** write `tier_join_all` as `max(tiers, default=Tier.CONFIDENTIAL)`. `max(..., default=...)` returns the default *only* for an empty iterable, which is what we want — but the explicit loop above is included verbatim so the builder sees the empty-set semantics spelled out and cannot accidentally write `max(tiers, default=Tier.PUBLIC)`. If you prefer the one-liner, it must be `max(tiers, default=MOST_RESTRICTIVE_TIER)` and the acceptance test still applies.

---

## 4. Capability + Entitlement (`permits_tier`)

`Capability` is the closed set of things a tenant's resolved entitlement may permit a request to do. `Entitlement` is the *resolved, per-tenant, per-edition* capability set evaluated **at the PEP** (D4 step 1–2). Modules **read** an entitlement; they never **decide** one (security-spine control "Entitlement-at-PEP capability gating").

### 4.1 The capability set (required members, verbatim names)

These five members are **required by name** (the brief enumerates them); add others only when a phase needs them.

| Capability | Meaning | Gated where |
|------------|---------|-------------|
| `OWN_MATERIALS` | Read/write the tenant's own (non-confidential) materials. | baseline read/write |
| `PUBLIC_RETRIEVAL` | Query the SHARED cross-tenant public index. | `mod-discovery`, public path of `mod-lit-intelligence` |
| `CONFIDENTIAL_RETRIEVAL` | Query the **per-tenant confidential retrieval surface** (own-tenant only, D6). | confidential grounding path of `mod-lit-intelligence` |
| `CROSS_GROUP_SHARE` | Issue/accept a cross-tenant `SharingGrant` (lights up cross-group workspace membership). | `mod-workspace` invite flow |
| `CONFIDENTIAL_DRAFTING` | Run generation on the shared 30B generator with the **confidential** locality + KV-isolation path (D10). | `mod-workspace` / confidential `mod-lit-intelligence` |

### 4.2 `permits_tier` — the entitlement → tier gate

`Entitlement.permits_tier(tier)` answers: *given this resolved entitlement, is the holder permitted to operate at this confidentiality tier at all?* This is **necessary but not sufficient** for an ALLOW — it is one of the six fixed PEP steps (D4); ABAC tier, ReBAC, tombstone, and lease must also pass. The rule:

* `public` tier requires `PUBLIC_RETRIEVAL` **or** `OWN_MATERIALS` (anyone who can read anything can touch public).
* `private` tier requires `OWN_MATERIALS`.
* `confidential` tier requires **`CONFIDENTIAL_RETRIEVAL` or `CONFIDENTIAL_DRAFTING`** (you must be entitled to *either* read the confidential surface or draft confidentially to touch the confidential tier at all).

This directly powers the contract test **"a lower tier cannot construct a confidential/cross-group request"** (security spine): an entitlement lacking both confidential capabilities returns `permits_tier(Tier.CONFIDENTIAL) == False`, and the PEP DENIES.

### 4.3 `capabilities.py` (verbatim)

```python
from __future__ import annotations

from enum import StrEnum
from typing import FrozenSet

from pydantic import BaseModel, ConfigDict, Field

from .tiers import Tier


class Capability(StrEnum):
    """Closed set of permittable capabilities. Add members only when a phase needs one.
    The five below are REQUIRED by name."""

    OWN_MATERIALS = "own_materials"
    PUBLIC_RETRIEVAL = "public_retrieval"
    CONFIDENTIAL_RETRIEVAL = "confidential_retrieval"
    CROSS_GROUP_SHARE = "cross_group_share"
    CONFIDENTIAL_DRAFTING = "confidential_drafting"


class Edition(StrEnum):
    """Per-tenant edition/plan. P0 ships exactly two; the business/pricing model is
    DROPPED (see brief) -- edition here is purely a capability bundle, not a price tier."""

    DISCOVERY_ONLY = "discovery_only"   # public discovery; no confidential surface, no cross-group share
    COLLABORATION = "collaboration"     # full loop: confidential retrieval + drafting + cross-group share


class Entitlement(BaseModel):
    """Resolved, per-tenant capability set. EVALUATED AT THE PEP. Modules read; never decide.
    Frozen value object."""

    model_config = ConfigDict(frozen=True)

    edition: Edition
    capabilities: FrozenSet[Capability] = Field(default_factory=frozenset)

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def permits_tier(self, tier: Tier) -> bool:
        """Entitlement gate on confidentiality tier. Necessary, NOT sufficient for ALLOW.

        public        -> PUBLIC_RETRIEVAL or OWN_MATERIALS
        private       -> OWN_MATERIALS
        confidential  -> CONFIDENTIAL_RETRIEVAL or CONFIDENTIAL_DRAFTING
        """
        if tier == Tier.PUBLIC:
            return self.has(Capability.PUBLIC_RETRIEVAL) or self.has(Capability.OWN_MATERIALS)
        if tier == Tier.PRIVATE:
            return self.has(Capability.OWN_MATERIALS)
        if tier == Tier.CONFIDENTIAL:
            return self.has(Capability.CONFIDENTIAL_RETRIEVAL) or self.has(
                Capability.CONFIDENTIAL_DRAFTING
            )
        return False  # unknown tier -> fail closed
```

> **Why `FrozenSet` for capabilities?** The entitlement is a value object pinned to a request; making the capability collection immutable means no module can mutate it mid-request to grant itself a capability. Pydantic v2 coerces a `set`/`list` literal into a `frozenset` here at construction. Chosen over a `list` (mutable, order-dependent, allows accidental in-place `.append`).

---

## 5. TenantContext (frozen, request-scoped)

`TenantContext` is the immutable identity of a single request, derived from the OIDC token at the FastAPI boundary and pinned to the Postgres transaction via `SET LOCAL` (D5). It is the carrier that the PEP reads to know *who is asking* and *under what entitlement*. It is **frozen** — once constructed for a request it cannot be mutated, so no module can escalate the request's tenant or capabilities partway through.

> **`tenant_id` is `str` and is the leading column of every RLS predicate (D5).** It is set on the connection via `set_config('app.tenant_id', <bound param>, true)` (transaction-scoped, leak-proof under PgBouncer transaction pooling — see `06-security-spine-lld.md`). The kernel does not perform the `SET LOCAL` (that is I/O — forbidden in the kernel by fitness invariant #2); the kernel only defines the immutable carrier. The DB-binding code lives in the app/PEP layer.

### 5.1 `tenant.py` (verbatim)

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .capabilities import Entitlement


class TenantContext(BaseModel):
    """Request-scoped, immutable identity. Built from the OIDC token at the FastAPI
    boundary; tenant_id is pinned to the transaction via SET LOCAL (D5). Frozen."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(min_length=1)        # leading index col on every RLS-scoped table
    subject_id: str = Field(min_length=1)       # the requesting Researcher (canonical subject id)
    entitlement: Entitlement
    orcid_id: str | None = None                 # canonical researcher id when present
    request_id: str | None = None               # correlation id for audit; not security-bearing

    def permits_tier(self, tier) -> bool:
        """Convenience pass-through to the resolved entitlement."""
        return self.entitlement.permits_tier(tier)

    def has(self, capability) -> bool:
        return self.entitlement.has(capability)
```

> **Why no `tenant_id` validation against a registry here?** The kernel cannot query the DB (fitness invariant #2). Whether `tenant_id` exists and is active is checked at the PEP/broker against Postgres. The kernel only guarantees the *shape* (non-empty string) and *immutability*.

---

## 6. Classification: ClassificationResult + Decision + `is_retrievable`

A record is classified **before** it can be embedded/indexed/graphed (D6, "classify-gates-index hard edge"). The classifier is fail-closed: **abstention/ambiguity → QUARANTINE → human adjudication queue**, and unclassified is treated as confidential. Walking-skeleton P0 is **binary allow/quarantine** (the `DENY` member exists for the full model and for explicit policy denials, but P0 only emits `ALLOW`/`QUARANTINE`).

### 6.1 `Decision` and `is_retrievable`

```
ALLOW       -> the record passed classification at its claimed tier
QUARANTINE  -> abstain/ambiguous/low-confidence -> treated CONFIDENTIAL, sent to adjudication, NEVER indexed to the shared sink
DENY        -> hard policy denial (e.g. license-prohibited, compliance flag) -> never indexed
```

`is_retrievable` is the single predicate the SHARED-index ingestion edge consults. **Only `is_retrievable == True` records reach the shared cross-tenant sink (vector/BM25/graph/outbox).** The rule:

```
is_retrievable == (decision == ALLOW) AND (tier == PUBLIC)
```

That is: a record is eligible for the SHARED index iff it was explicitly allowed **and** is public-tier. A `private` or `confidential` record is *never* retrievable on the shared surface even if `ALLOW`. (Confidential own-tenant content reaches the *per-tenant confidential surface* by a separate path — see D6 and `07` — not via `is_retrievable`.)

### 6.2 `classification.py` (verbatim)

```python
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .tiers import Tier


class Decision(StrEnum):
    ALLOW = "allow"
    QUARANTINE = "quarantine"   # abstain/ambiguous -> treated CONFIDENTIAL, adjudication queue
    DENY = "deny"               # hard policy denial


class ClassificationResult(BaseModel):
    """Fail-closed classifier output gating SHARED-index ingestion (D6).
    P0 walking-skeleton emits ALLOW/QUARANTINE only. Frozen value object."""

    model_config = ConfigDict(frozen=True)

    tier: Tier
    decision: Decision
    class_codes: tuple[str, ...] = Field(default_factory=tuple)  # persisted as TEXT[] in DDL
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    compliance_flags: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def is_retrievable(self) -> bool:
        """ONLY ALLOW + PUBLIC reaches the SHARED cross-tenant index. Everything else is gated out."""
        return self.decision == Decision.ALLOW and self.tier == Tier.PUBLIC

    @classmethod
    def quarantined(cls, reason_code: str, confidence: float = 0.0) -> "ClassificationResult":
        """Fail-closed factory: abstain/ambiguous -> CONFIDENTIAL tier, QUARANTINE decision."""
        return cls(
            tier=Tier.CONFIDENTIAL,
            decision=Decision.QUARANTINE,
            class_codes=(reason_code,),
            confidence=confidence,
        )
```

> **Why `tuple[str, ...]` for `class_codes`/`compliance_flags` and not `list`?** Frozen value objects must contain only immutable fields, otherwise the "frozen" guarantee is hollow (you could mutate the list inside a frozen model). Pydantic v2 will coerce an incoming `list` to a `tuple` here. The DDL stores these as `TEXT[]` (see `13-data-model-and-schemas.md`); the boundary code converts tuple ↔ array.

---

## 7. PublishableProjection (the only shape that crosses into the shared index)

`PublishableProjection` is the **single shape allowed to cross into the SHARED / cross-tenant retrieval surface** (D3, D6). It is an *allowlist projection*: an explicit, named subset of public/private fields of some entity. The validator **rejects `confidential` tier** so confidential content can never even be *constructed* into a shape destined for the shared index. **Only the broker constructs it** — an `import-linter` + AST test forbids any `mod-*` module from importing or instantiating `PublishableProjection` directly (D3 consequence; see `06` for the lint).

### 7.1 The hard rules baked into the validator

1. **`tier` must be `public` or `private` — `confidential` raises.** (The core fail-closed invariant; acceptance test P0.0 `PublishableProjection(tier=confidential) raises`.)
2. **`fields` is an allowlist** — a mapping of explicitly-projected field names → values. There is no "include everything" mode.
3. **`discoverability_scope`** carries the *future-federation* seam (D2). It is **carry-forward-clean** — i.e. it survives unchanged into the eventual cross-box layer (unlike crypto-shred and CTE-ReBAC, which are known rewrites). It includes a `NONE` member meaning "not discoverable anywhere" (a projection that exists for local use but is not advertised).
4. **`projection_version`** is a monotonic integer used by the *monotonic applier* (D12) to guarantee a re-ingest cannot resurrect a revoked/down-classified record (a stale, lower-version projection is rejected against the live `revocation_epoch`). It is required, must be ≥ 1.

### 7.2 `DiscoverabilityScope` (with `NONE`)

```
NONE          -> not discoverable anywhere (local-only existence; the safe default)
TENANT_LOCAL  -> discoverable within the owning tenant only
SHARED_BOX    -> discoverable across tenants on THIS box (the P0 cross-tenant public surface)
FEDERATED     -> discoverable across boxes (DEFERRED -- federation seam, not built in P0)
```

> **Why `NONE` is the default and is explicit.** A projection with no stated scope must default to *not discoverable* (fail-closed), never to "shared". A 30B builder omitting `discoverability_scope` should get the safe value, so the field defaults to `NONE`. The `FEDERATED` member exists now so the type is stable across the federation boundary (D2) but is **never emitted in P0**.

### 7.3 `projection.py` (verbatim)

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .tiers import Tier


class DiscoverabilityScope(StrEnum):
    NONE = "none"               # default, fail-closed: not discoverable anywhere
    TENANT_LOCAL = "tenant_local"
    SHARED_BOX = "shared_box"   # the P0 cross-tenant public surface
    FEDERATED = "federated"     # DEFERRED (D2) -- never emitted in P0


class PublishableProjection(BaseModel):
    """The ONLY shape that may cross into the SHARED / cross-tenant retrieval surface (D3/D6).
    Validator REJECTS confidential tier. Only the broker constructs this (enforced by lint).
    Frozen value object."""

    model_config = ConfigDict(frozen=True)

    entity_ref: str = Field(min_length=1)                 # opaque ref to the source entity
    tier: Tier                                            # MUST be public or private
    fields: Mapping[str, Any]                             # ALLOWLISTED projected fields only
    discoverability_scope: DiscoverabilityScope = DiscoverabilityScope.NONE
    projection_version: int = Field(ge=1)                 # monotonic; used by the monotonic applier (D12)

    @field_validator("tier")
    @classmethod
    def _reject_confidential(cls, v: Tier) -> Tier:
        if v == Tier.CONFIDENTIAL:
            raise ValueError(
                "PublishableProjection cannot carry confidential tier: confidential content "
                "must never be constructed for the SHARED index (D6)."
            )
        return v
```

> **Why a `field_validator` and not a `model_validator`?** The rejection rule depends only on the single `tier` field, so a field-level validator is the tightest, clearest expression and runs even when other fields are absent/invalid. The error message names D6 so a builder reading the traceback understands *why* it failed.
>
> **Why `Mapping[str, Any]` for `fields` and not a concrete model per entity?** The shared index carries projections of heterogeneous entities (Work, Award, Opportunity, enriched fingerprints). A per-entity model would bloat the frozen kernel with feature shapes (violating fitness invariant #1). The *allowlist enforcement* (which field names are permitted for which entity) lives in the broker, which is the only constructor; the kernel guarantees only that no confidential projection can exist.

---

## 8. PEP request/response types (PepRequest / PepResponse)

Every retrieve/egress/derive call goes through **one in-process PEP** (`IPolicyEnforcement.authorize`, D3/D4). The kernel defines the request and response shapes; the *decision order* is implemented in `mod-pep` and specified in `06-security-spine-lld.md`. The fixed order (D4), summarized so a builder reading the kernel understands what these types feed:

```
authorize(request) runs, cheap-first, fail-closed (any error/abstain -> DENY):
  1. entitlement / edition gate        (Entitlement on request.context)
  2. capability gate                   (request.required_capability in entitlement)
  3. ABAC tier check                   (in-Python lattice: entitlement.permits_tier + MAX-rule)
  4. ReBAC relation Check              (Postgres recursive CTE -- via IPolicyEnforcement.check)
  5. owner-local durable tombstone read (AUTHORITATIVE deny)
  6. short-TTL lease                   (narrow-only positive cache)
```

### 8.1 The action verbs and the request shape

`PepAction` is the closed set of mediated operations. `PepRequest` carries everything the six steps need; it is frozen so a module cannot mutate the request after the PEP reads it.

```
PepAction:
  RETRIEVE_PUBLIC        -> query the SHARED public index
  RETRIEVE_CONFIDENTIAL  -> query the OWN-TENANT confidential surface (D6)
  DERIVE                 -> produce a derived artifact (MAX-rule applies to inputs)
  EGRESS                 -> send content outward (e.g. to a model provider; locality-checked)
  SHARE                  -> issue/accept a cross-tenant SharingGrant
  READ_OBJECT            -> read a specific object by ref (BOLA-checked)
  WRITE_OBJECT           -> write/update a specific object by ref
```

### 8.2 The response shape

`PepResponse` returns an `effect` (ALLOW/DENY — note: the *classifier* uses QUARANTINE, the *PEP* returns ALLOW/DENY only, a deliberate separation), the `reason_code` (for audit + debugging), and, on ALLOW, an optional narrow positive `lease_ttl_seconds` and the resolved `tier`. **On any uncertainty the PEP returns DENY** — there is no "maybe".

### 8.3 `pep.py` (verbatim)

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .capabilities import Capability
from .tenant import TenantContext
from .tiers import Tier


class PepAction(StrEnum):
    RETRIEVE_PUBLIC = "retrieve_public"
    RETRIEVE_CONFIDENTIAL = "retrieve_confidential"
    DERIVE = "derive"
    EGRESS = "egress"
    SHARE = "share"
    READ_OBJECT = "read_object"
    WRITE_OBJECT = "write_object"


class PepEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"   # the PEP NEVER returns QUARANTINE -- that is the classifier's verb (D6)


class PepRequest(BaseModel):
    """Everything the fixed 6-step decision order (D4) needs. Frozen."""

    model_config = ConfigDict(frozen=True)

    context: TenantContext
    action: PepAction
    # The capability this action requires (step 2). e.g. RETRIEVE_CONFIDENTIAL -> CONFIDENTIAL_RETRIEVAL.
    required_capability: Capability
    # The confidentiality tier of the resource/operation (step 3 ABAC). For DERIVE this is the
    # MAX-rule join of input tiers; the caller computes it via tier_join_all and passes it.
    resource_tier: Tier
    # ReBAC tuple coordinates (step 4) when the action is object/relationship scoped.
    relation: str | None = None          # e.g. "editor", "viewer", "co_pi"
    object_ref: str | None = None        # the object the relation targets
    # Optional structured attributes for audit / future ABAC extension. Not security-bearing by itself.
    attributes: Mapping[str, Any] = Field(default_factory=dict)


class PepResponse(BaseModel):
    """The authorize() verdict. ALLOW or DENY only; fail-closed. Frozen."""

    model_config = ConfigDict(frozen=True)

    effect: PepEffect
    reason_code: str                     # e.g. "ok", "tier_denied", "rebac_denied", "tombstoned",
                                         #      "pip_unavailable", "entitlement_denied"
    resolved_tier: Tier | None = None    # set on ALLOW
    lease_ttl_seconds: int | None = None # narrow-only positive cache window on ALLOW

    @property
    def allowed(self) -> bool:
        return self.effect == PepEffect.ALLOW

    @classmethod
    def deny(cls, reason_code: str) -> "PepResponse":
        return cls(effect=PepEffect.DENY, reason_code=reason_code)

    @classmethod
    def allow(cls, tier: Tier, reason_code: str = "ok", lease_ttl_seconds: int | None = None) -> "PepResponse":
        return cls(
            effect=PepEffect.ALLOW,
            reason_code=reason_code,
            resolved_tier=tier,
            lease_ttl_seconds=lease_ttl_seconds,
        )
```

> **Why does `PepResponse` never carry QUARANTINE?** The classifier and the PEP are different controls. The classifier decides whether *content* may enter an index (ALLOW/QUARANTINE/DENY). The PEP decides whether a *request* may proceed (ALLOW/DENY). Conflating them would let a 30B builder route a "quarantine" through the authorize path and treat it as a soft state — there is no soft state in authorization; it is binary and fail-closed. This separation is the security spine "fixed fail-closed decision order" control.

---

## 9. Supporting value objects

These are the remaining frozen value objects the Protocols traffic in. They satisfy fitness invariant #3 (each is referenced by ≥ 2 packages).

### 9.1 `RelationTuple` — the Zanzibar-style ReBAC row

Evaluated by the recursive-CTE `Check()` (D4 step 4). **Local-only resolution** — a known federation-boundary rewrite (D2); the kernel type is stable but the resolver is not federation-portable.

### 9.2 `RetrievedItem` — what `IRetrievalStrategy`/`IVectorStore`/`ILexicalIndex` return

A single retrieved chunk with its fused score. Carries its `tier` so the broker can re-assert the MAX-rule on derivation.

### 9.3 `GenerationRequest` / `GenerationResult` — what `IModelRouter`/`IModelProvider` traffic in

Carries the `tier` and a `confidential` flag so the router can enforce locality (D10) and the provider can set `enable_prefix_caching=False` on the confidential path.

### 9.4 `KeyRef` — opaque key handle for `IKms`

The kernel never holds key material; it holds an opaque reference. Actual KEK/DEK bytes live only inside the `LocalKms` implementation (`06`).

### 9.5 `values.py` (verbatim)

```python
from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .tiers import Tier


class RelationTuple(BaseModel):
    """Zanzibar-style ReBAC storage row. Resolved by a recursive-CTE Check() (D4 step 4),
    LOCAL-only (a known federation-boundary rewrite, D2). Inherits tenant RLS. Frozen."""

    model_config = ConfigDict(frozen=True)

    subject: str        # e.g. "user:alice" or "team:42#member"
    relation: str       # e.g. "editor", "viewer", "co_pi", "member"
    object: str         # e.g. "proposal:99"
    tenant_id: str = Field(min_length=1)   # leading index col; RLS-scoped


class RetrievedItem(BaseModel):
    """One retrieved chunk + fused score. Carries tier so the broker re-asserts MAX-rule. Frozen."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    parent_id: str | None = None     # hierarchical parent (return 512-1024 tok parent; embed child)
    text: str
    tier: Tier
    score: float                     # fused RRF score (stage 1) or rerank score (stage 2)
    source_ref: str                  # entity ref the chunk derives from
    metadata: Mapping[str, Any] = Field(default_factory=dict)


class GenerationRequest(BaseModel):
    """A generation call routed by IModelRouter to an IModelProvider. Frozen.
    `confidential=True` forces local-only inference + prefix-caching-OFF on the shared 30B (D10)."""

    model_config = ConfigDict(frozen=True)

    prompt: str
    tier: Tier
    confidential: bool = False
    max_tokens: int = Field(gt=0, default=1024)
    temperature: float = Field(ge=0.0, le=2.0, default=0.2)
    # Opaque per-request routing hints; not security-bearing on their own.
    routing_hints: Mapping[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    model_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    served_locally: bool = True   # MUST be True for confidential/private (egress guard, D10)


class KeyRef(BaseModel):
    """Opaque handle to key material held INSIDE LocalKms. The kernel never holds bytes. Frozen."""

    model_config = ConfigDict(frozen=True)

    kek_id: str
    tenant_id: str = Field(min_length=1)
```

---

## 10. All `I*` Protocols — full method signatures

These are `typing.Protocol` interfaces (structural typing): an implementation satisfies a Protocol by having the right methods, no explicit subclassing required. Decorate each with `@runtime_checkable` so the DI factory can `isinstance`-check a provided implementation at wiring time (a cheap fail-fast guard). All methods that touch I/O are `async` (the app is FastAPI + asyncpg). Pure/sync helpers stay sync.

> **Why Protocols over abstract base classes (ABCs)?** Protocols give us structural typing with zero import coupling — the data-plane package does not need to import the kernel ABC and subclass it; it just needs to *match the shape*. This keeps the dependency arrows pointing one way (everyone → kernel) and lets a future implementation (e.g. a Qdrant `IVectorStore`) be swapped without touching the kernel. Chosen over ABCs (force `class PgVectorStore(IVectorStore)` inheritance, a tighter coupling) and over bare duck typing (no `mypy` checking, no `@runtime_checkable` guard).

### 10.1 Catalogue

| Protocol | Implemented by (P0) | Called by | Decision |
|----------|---------------------|-----------|----------|
| `IPolicyEnforcement` | `mod-pep` | every feature module (indirectly via broker) | D3, D4 |
| `IClassifier` | `mod-ingestion` classification service | ingestion DAG, write-back applier | D6 |
| `IEntitlementEvaluator` | `mod-pep` | `IPolicyEnforcement.authorize` step 1–2 | D4 |
| `IRetrievalStrategy` | `retrieval` (HybridRetriever) | broker, `mod-lit-intelligence`, `mod-discovery` | D8 |
| `IVectorStore` | `retrieval` (pgvector HNSW) | `IRetrievalStrategy` | D8 |
| `ILexicalIndex` | `retrieval` (native BM25) | `IRetrievalStrategy` | D8 |
| `IGraph` | `retrieval` (edge table + recursive CTE) | `mod-discovery`, write-back | D8 |
| `IModelRouter` | `mod_ai` | broker, `mod-lit-intelligence`, `mod-workspace` | D9, D10 |
| `IModelProvider` | `mod_ai` provider registry | `IModelRouter` | D9, D10 |
| `IKms` | `confidential_crypto` (LocalKms) | broker, `mod-workspace`, crypto-shred | D7 |
| `IGrantStore` | `mod-pep` / `mod-workspace` | `mod-workspace` invite/revoke | D11 |
| `IRevocationAuthority` | **DEFERRED stub** | future federation | D2 |
| `IExchangeFeed` | **DEFERRED stub** | future federation | D2 |
| `IAuditSink` | `mod-audit` | PEP, classifier, broker, revocation | audit spine |

### 10.2 `protocols.py` (verbatim)

```python
from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from .audit import AuditEvent
from .capabilities import Entitlement
from .classification import ClassificationResult
from .pep import PepRequest, PepResponse
from .projection import PublishableProjection
from .tenant import TenantContext
from .tiers import Tier
from .values import (
    GenerationRequest,
    GenerationResult,
    KeyRef,
    RelationTuple,
    RetrievedItem,
)


# --------------------------------------------------------------------------- #
# Authorization (D3, D4)                                                       #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IPolicyEnforcement(Protocol):
    """The single in-process PEP. authorize() runs the fixed 6-step fail-closed order (D4).
    check() resolves a single ReBAC relation via the recursive-CTE (D4 step 4, LOCAL-only)."""

    async def authorize(self, request: PepRequest) -> PepResponse:
        """Run the fixed decision order; return ALLOW/DENY. Any error/abstain -> DENY."""
        ...

    async def check(
        self, *, subject: str, relation: str, object: str, tenant_id: str
    ) -> bool:
        """Zanzibar-style relation Check via Postgres recursive CTE. LOCAL-only (D2)."""
        ...


@runtime_checkable
class IEntitlementEvaluator(Protocol):
    """Resolves the per-tenant Entitlement consulted by authorize() steps 1-2 (D4)."""

    async def resolve(self, *, tenant_id: str, subject_id: str) -> Entitlement:
        ...


# --------------------------------------------------------------------------- #
# Classification (D6)                                                          #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IClassifier(Protocol):
    """Fail-closed classifier gating SHARED-index ingestion. Abstain -> QUARANTINE (D6).
    P0 walking-skeleton is BINARY allow/quarantine."""

    async def classify(
        self, *, content: str, declared_tier: Tier | None, tenant_id: str
    ) -> ClassificationResult:
        ...


# --------------------------------------------------------------------------- #
# Retrieval (D8) -- all three stores backed by the SINGLE Postgres in P0       #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IRetrievalStrategy(Protocol):
    """Two-stage hybrid (pgvector + BM25 + RRF) -> cross-encoder rerank (D8).
    `confidential_surface` selects the per-tenant own-confidential index (D6) vs the shared public index."""

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int = 8,
        confidential_surface: bool = False,
    ) -> Sequence[RetrievedItem]:
        ...


@runtime_checkable
class IVectorStore(Protocol):
    """Dense ANN (pgvector HNSW, RAM-resident/NVMe). create_collection is CREATE-IF-ABSENT.
    NEVER drop-on-create / recreate_collection."""

    async def collection_exists(self, *, name: str, tenant_id: str) -> bool:
        ...

    async def create_collection_if_absent(
        self, *, name: str, dim: int, tenant_id: str
    ) -> None:
        """Idempotent. MUST be a no-op if the collection already exists. NEVER drops."""
        ...

    async def upsert(
        self,
        *,
        collection: str,
        tenant_id: str,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[dict[str, Any]],
    ) -> None:
        ...

    async def search(
        self,
        *,
        collection: str,
        tenant_id: str,
        vector: Sequence[float],
        top_k: int,
    ) -> Sequence[RetrievedItem]:
        ...


@runtime_checkable
class ILexicalIndex(Protocol):
    """Native BM25 (VectorChord-BM25 or ParadeDB pg_search, whichever benchmarks on aarch64, D8)."""

    async def index(
        self,
        *,
        collection: str,
        tenant_id: str,
        ids: Sequence[str],
        texts: Sequence[str],
        payloads: Sequence[dict[str, Any]],
    ) -> None:
        ...

    async def search(
        self,
        *,
        collection: str,
        tenant_id: str,
        query: str,
        top_k: int,
    ) -> Sequence[RetrievedItem]:
        ...


@runtime_checkable
class IGraph(Protocol):
    """Metadata-backbone edge table traversed by bounded-hop recursive CTEs (D8). No Apache AGE."""

    async def add_edge(
        self,
        *,
        tenant_id: str,
        src: str,
        dst: str,
        edge_type: str,
        weight: float = 1.0,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        ...

    async def ego_net(
        self, *, tenant_id: str, node: str, max_hops: int = 2
    ) -> Sequence[dict[str, Any]]:
        """Bounded-hop neighborhood via recursive CTE. max_hops is REQUIRED bounded (no unbounded walks)."""
        ...


# --------------------------------------------------------------------------- #
# AI plane (D9, D10)                                                           #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IModelRouter(Protocol):
    """Classification-routed inference. Confidential/private -> in-boundary ONLY (D10).
    Router + transport read the SAME tier->locality policy table; disagreement HARD-FAILS."""

    async def generate(
        self, *, request: GenerationRequest, context: TenantContext
    ) -> GenerationResult:
        ...

    async def embed(
        self, *, texts: Sequence[str], tenant_id: str
    ) -> Sequence[Sequence[float]]:
        ...

    async def rerank(
        self, *, query: str, candidates: Sequence[str], tenant_id: str
    ) -> Sequence[float]:
        ...


@runtime_checkable
class IModelProvider(Protocol):
    """A single backing model process (vLLM generator / embedder / reranker, or ST in-process).
    `is_local` MUST be True for any provider eligible to serve confidential/private (D10)."""

    @property
    def model_id(self) -> str: ...

    @property
    def is_local(self) -> bool: ...

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Confidential requests MUST be served with prefix caching DISABLED + serialized (D10)."""
        ...


# --------------------------------------------------------------------------- #
# Key management / crypto-shred (D7)                                           #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IKms(Protocol):
    """In-process LocalKms behind this Protocol. Per-tenant KEK wraps a per-tenant DEK.
    Box-master anchored by fTPM/passphrase (P0 default). destroy_kek() == crypto-shred (O(1))."""

    async def create_kek(self, *, tenant_id: str) -> KeyRef:
        ...

    async def get_dek(self, *, key_ref: KeyRef) -> bytes:
        """Unwrap and return the per-tenant DEK (for AES-GCM blob crypto + tablespace unlock)."""
        ...

    async def encrypt_blob(self, *, key_ref: KeyRef, plaintext: bytes, aad: bytes | None = None) -> bytes:
        """AES-256-GCM on a NON-searchable blob (D7). Never used on searchable vectors/BM25."""
        ...

    async def decrypt_blob(self, *, key_ref: KeyRef, ciphertext: bytes, aad: bytes | None = None) -> bytes:
        ...

    async def destroy_kek(self, *, key_ref: KeyRef) -> None:
        """CRYPTO-SHRED. O(1). After this, BOTH the AES-GCM blobs AND the encrypted-tablespace
        searchable indexes for this tenant become permanently undecryptable (D7)."""
        ...


# --------------------------------------------------------------------------- #
# ReBAC grants (D11)                                                           #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IGrantStore(Protocol):
    """Owner-authoritative, revocable cross-group SharingGrants (ReBAC tuples). Lights up
    cross-tenant workspace membership (D11). Revocation is fail-closed + durable (see 06)."""

    async def grant(
        self, *, tuple: RelationTuple, granted_by: str, scope: str, reason: str | None = None
    ) -> None:
        ...

    async def revoke(
        self, *, tuple: RelationTuple, reason: str
    ) -> None:
        """Commits (fsync) to the durable revocation log BEFORE any allow/deny observes it (06)."""
        ...

    async def list_grants(
        self, *, tenant_id: str, object: str | None = None
    ) -> Sequence[RelationTuple]:
        ...


# --------------------------------------------------------------------------- #
# Audit spine                                                                  #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IAuditSink(Protocol):
    """Per-stream hash-chained, tamper-evident security audit (prev_hash -> entry_hash).
    SEPARATE from the non-security loop-event stream."""

    async def append(self, *, event: AuditEvent) -> None:
        ...

    async def verify_chain(self, *, stream_id: str) -> bool:
        """Re-walk the hash chain; return False if any link is broken (tamper-evident)."""
        ...


# --------------------------------------------------------------------------- #
# DEFERRED federation stubs (D2) -- DESIGNED, NOT BUILT in P0                  #
# --------------------------------------------------------------------------- #
@runtime_checkable
class IRevocationAuthority(Protocol):
    """DEFERRED (D2). Cross-BOX revocation authority. In P0 this is a STUB with no impl.

    HONEST federation note: single-box crypto-shred is ENCRYPTED-TABLESPACE DEK-DESTRUCTION,
    which is NODE-LOCAL -- a future IRevocationAuthority CANNOT crypto-shred ANOTHER node's
    tablespace. This is a KNOWN federation-boundary REWRITE, NOT a clean transport swap (D2).
    See 15-future-federation-interfaces.md.
    """

    async def assert_revoked(self, *, object_ref: str, revocation_epoch: int) -> None:
        ...

    async def current_epoch(self, *, object_ref: str) -> int:
        ...


@runtime_checkable
class IExchangeFeed(Protocol):
    """DEFERRED (D2). Cross-BOX discovery exchange of PublishableProjection records. STUB in P0.

    Carries forward CLEANLY: it traffics only in PublishableProjection (confidential-rejecting)
    with discoverability_scope == FEDERATED. The projection shape is federation-portable; the
    TRANSPORT is what gets added later. See 15-future-federation-interfaces.md.
    """

    async def publish(self, *, projection: PublishableProjection) -> None:
        ...

    async def pull(self, *, since_version: int) -> Sequence[PublishableProjection]:
        ...
```

> **Deferred-stub discipline.** `IRevocationAuthority` and `IExchangeFeed` are **defined now** (so the federation seam is stable, D2) but have **no P0 implementation**. The DI factory must **not** wire a real provider for them in P0; any attempt to call them should raise `NotImplementedError` from a placeholder, never silently no-op (a silent no-op on revocation would be a confidentiality hole). Their docstrings state, honestly, that crypto-shred and CTE-ReBAC are *node-local rewrites*, not transport swaps — do not let a future builder believe federation is "just plumbing".

---

## 11. The complete `contracts` package as files

Below is the `__init__.py` re-export surface. Keep it explicit (no `import *`) so the public kernel surface is auditable and `mypy`-checkable.

### 11.1 `contracts/__init__.py` (verbatim)

```python
from __future__ import annotations

# Tiers + MAX-rule
from .tiers import Tier, tier_join, tier_join_all, MOST_RESTRICTIVE_TIER

# Capabilities + entitlement
from .capabilities import Capability, Edition, Entitlement

# Request-scoped identity
from .tenant import TenantContext

# Classification
from .classification import Decision, ClassificationResult

# Shared-index projection
from .projection import DiscoverabilityScope, PublishableProjection

# PEP types
from .pep import PepAction, PepEffect, PepRequest, PepResponse

# Audit
from .audit import AuditEvent

# Value objects
from .values import (
    RelationTuple,
    RetrievedItem,
    GenerationRequest,
    GenerationResult,
    KeyRef,
)

# Protocols
from .protocols import (
    IPolicyEnforcement,
    IEntitlementEvaluator,
    IClassifier,
    IRetrievalStrategy,
    IVectorStore,
    ILexicalIndex,
    IGraph,
    IModelRouter,
    IModelProvider,
    IKms,
    IGrantStore,
    IAuditSink,
    IRevocationAuthority,   # DEFERRED stub (D2)
    IExchangeFeed,          # DEFERRED stub (D2)
)

__all__ = [
    "Tier", "tier_join", "tier_join_all", "MOST_RESTRICTIVE_TIER",
    "Capability", "Edition", "Entitlement",
    "TenantContext",
    "Decision", "ClassificationResult",
    "DiscoverabilityScope", "PublishableProjection",
    "PepAction", "PepEffect", "PepRequest", "PepResponse",
    "AuditEvent",
    "RelationTuple", "RetrievedItem", "GenerationRequest", "GenerationResult", "KeyRef",
    "IPolicyEnforcement", "IEntitlementEvaluator", "IClassifier",
    "IRetrievalStrategy", "IVectorStore", "ILexicalIndex", "IGraph",
    "IModelRouter", "IModelProvider", "IKms", "IGrantStore", "IAuditSink",
    "IRevocationAuthority", "IExchangeFeed",
]
```

### 11.2 `contracts/audit.py` (verbatim)

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEvent(BaseModel):
    """Per-stream hash-chained, tamper-evident SECURITY record (prev_hash -> entry_hash).
    SEPARATE from the non-security LoopEvent stream. Frozen value object.

    The hash linkage (prev_hash/entry_hash) is computed by the IAuditSink implementation
    (mod-audit); the kernel only defines the carrier shape. See 06-security-spine-lld.md."""

    model_config = ConfigDict(frozen=True)

    stream_id: str = Field(min_length=1)
    seq: int = Field(ge=0)
    event_type: str = Field(min_length=1)   # e.g. "pep_decision", "classification", "revocation", "egress"
    payload: Mapping[str, Any] = Field(default_factory=dict)
    prev_hash: str | None = None            # None for the genesis entry of a stream
    entry_hash: str | None = None           # filled by the sink on append
    ts: datetime = Field(default_factory=_utcnow)
```

> **Why the kernel defines `AuditEvent` but not the hashing.** The *shape* of an audit row is shared vocabulary (the PEP, classifier, broker, and revocation all emit it → fitness invariant #3). The *hash chaining* is I/O-adjacent stateful logic that belongs in `mod-audit` behind `IAuditSink` (fitness invariant #2 forbids it in the kernel). The kernel carries `prev_hash`/`entry_hash` fields so the sink can populate them, but the kernel never computes them.

---

## 12. Acceptance tests this document must satisfy (P0.0)

These are the P0.0 acceptance gates from the build phases. **The security-bearing ones are HUMAN-authored** (the brief: the 30B builder must not author its own safety net). The builder implements the kernel; a human writes (or has already written) the tripwires below. The builder's job is to make them green.

```python
# test_tier_lattice.py
def test_empty_join_is_confidential():
    from contracts import tier_join_all, Tier
    assert tier_join_all([]) == Tier.CONFIDENTIAL          # unknown -> most restrictive

def test_max_rule():
    from contracts import tier_join_all, Tier
    assert tier_join_all([Tier.PUBLIC, Tier.CONFIDENTIAL]) == Tier.CONFIDENTIAL
    assert tier_join_all([Tier.PUBLIC, Tier.PRIVATE]) == Tier.PRIVATE
    assert tier_join_all([Tier.PUBLIC, Tier.PUBLIC]) == Tier.PUBLIC

# test_projection_rejects_confidential.py   [HUMAN-authored]
def test_publishable_projection_rejects_confidential():
    import pytest
    from pydantic import ValidationError
    from contracts import PublishableProjection, Tier, DiscoverabilityScope
    with pytest.raises(ValidationError):
        PublishableProjection(
            entity_ref="work:1", tier=Tier.CONFIDENTIAL, fields={"title": "x"},
            discoverability_scope=DiscoverabilityScope.SHARED_BOX, projection_version=1,
        )

# test_permits_tier.py   [HUMAN-authored]
def test_lower_tier_cannot_touch_confidential():
    from contracts import Entitlement, Edition, Capability, Tier
    ent = Entitlement(edition=Edition.DISCOVERY_ONLY, capabilities=frozenset({Capability.PUBLIC_RETRIEVAL}))
    assert ent.permits_tier(Tier.PUBLIC) is True
    assert ent.permits_tier(Tier.CONFIDENTIAL) is False    # no confidential capability -> denied

def test_is_retrievable_only_allow_public():
    from contracts import ClassificationResult, Decision, Tier
    assert ClassificationResult(tier=Tier.PUBLIC, decision=Decision.ALLOW).is_retrievable is True
    assert ClassificationResult(tier=Tier.CONFIDENTIAL, decision=Decision.ALLOW).is_retrievable is False
    assert ClassificationResult(tier=Tier.PUBLIC, decision=Decision.QUARANTINE).is_retrievable is False

# test_kernel_fitness.py
def test_kernel_imports_no_features():
    # import-linter contract "kernel-no-feature-deps" is the real gate; this is a smoke check.
    import contracts  # must import with only stdlib + pydantic available
```

Additional P0.0 gates from the brief: `import-linter` green (kernel imports nothing feature-side); `pytest + ruff + mypy` clean; one of the three vLLM processes loads a tiny model from the SM 8.7 wheel (a smoke test that lives in `04-tech-stack-and-arm64-runbook.md`, not the kernel).

> **Frozen-model immutability is also testable.** Constructing any value object and attempting attribute assignment must raise `pydantic.ValidationError` (Pydantic v2 raises on assignment to a frozen model). Add a property-style test asserting `frozen=True` holds for `TenantContext`, `Entitlement`, `ClassificationResult`, `PublishableProjection`, `PepRequest`, `PepResponse`, `RelationTuple`, `RetrievedItem`, `KeyRef`, `AuditEvent`.

---

## 13. What is deliberately NOT in the kernel

The kernel is small on purpose. The following are explicitly **out** (each would violate a fitness invariant or reintroduce forbidden tech):

| Not in kernel | Why | Where it lives |
|---------------|-----|----------------|
| The PEP decision-order *implementation* | I/O (Postgres CTE, tombstone read) → fitness #2 | `mod-pep` (`06`) |
| The recursive-CTE `Check()` SQL | I/O → fitness #2; also LOCAL-only, a federation rewrite (D2) | `mod-pep` (`06`) |
| `LocalKms` (actual KEK/DEK bytes, fTPM seal) | Holds secret state → fitness #2 | `confidential_crypto` (`06`) |
| Concrete pgvector / BM25 / graph SQL | I/O → fitness #2; swappable behind Protocols | `retrieval` (`07`) |
| vLLM process management, prefix-caching flags | I/O + process state; D10 mechanics | `mod_ai` (`08`) |
| Per-entity Pydantic models (Work, Pursuit, Proposal, …) | Feature shapes → fitness #1 (would couple kernel to features) | `13-data-model-and-schemas.md` |
| RLS migrations, `SET LOCAL` binding | I/O → fitness #2 | `06`, `13` |
| **OPA / Rego, SpiceDB, Cedar, OPA Go daemon** | FORBIDDEN single-box revisions (D4): ABAC is in-Python, ReBAC is Postgres-CTE | n/a — not built |
| **A second resident 30B model copy; MIG** | FORBIDDEN (D10): exceeds 64GB; Orin Ampere has no MIG | n/a — not built |
| **Application-layer AES-GCM on vectors/BM25** | FORBIDDEN (D7): mathematically unsearchable; use encrypted-tablespace + DEK-destroy | n/a — `IKms.encrypt_blob` is for NON-searchable blobs only |
| **OP-TEE/EKB as a build deliverable; CloudHSM/cloud-KMS** | FORBIDDEN (D7): firmware-C wall / no-cloud box; fTPM/passphrase is the P0 default | optional human hardening (`06`, `15`) |
| Real `IExchangeFeed` / `IRevocationAuthority` transport | DEFERRED (D2): designed, not built; node-local mechanisms are known rewrites | `15-future-federation-interfaces.md` |

> **The one rule to remember.** If a symbol does I/O, holds state, or names a feature, it does **not** belong in the kernel — it belongs behind one of the `I*` Protocols above. The kernel is types, enums, pure functions, and interfaces. Nothing else.
