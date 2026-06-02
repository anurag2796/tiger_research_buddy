# 02 — Glossary & Domain Primer

> **What this document is.** A single, flat, alphabetically-grouped dictionary of *every*
> domain term and technical term used across the TigerExchange (single-Orin edition) corpus.
> Each entry is self-contained: definition, why it exists, and — for non-obvious choices — the
> rejected alternative and the reason. If you are a builder and you hit a word you do not know in
> any other doc, look it up **here first**, then follow the cross-reference to the doc that owns
> the detail.
>
> **Who reads this.** A local ~30B model that will build the application. The entries are
> deliberately verbose and concrete. Nothing here is novel: every name, type, and pin is taken
> from the four ground-truth documents and reproduced consistently. This doc **defines** terms;
> it does **not** redefine types or DDL.
>
> **Authority chain (which doc wins on conflict).**
> 1. `_design-brief.json` — locked intent (the `decisions[]` D1..D14, entities, security spine).
> 2. `CONVENTIONS-single-box.md` — the "this file wins" pins (names, paths, versions, forbidden list).
> 3. `05-kernel-contracts.md` — the frozen kernel types + Protocols (exact signatures).
> 4. `13-data-model-and-schemas.md` — the physical DDL + Pydantic row models (exact table/column names).
>
> This glossary is **below** all four. If a definition here ever drifts from those, those win;
> flag the drift so a human can fix this file.
>
> **Decision IDs are `D1`..`D14` only.** There is no `D-AI`, no `D9`-meaning-something-else, no `D15`.
> When an entry cites a decision, it is one of the fourteen in `_design-brief.json → decisions[]`.

---

## 0. Table of contents

1. [How to read an entry](#1-how-to-read-an-entry)
2. [The 30-second mental model](#2-the-30-second-mental-model)
3. [Organizational & tenancy terms](#3-organizational--tenancy-terms)
4. [The security spine terms](#4-the-security-spine-terms)
5. [Cryptography & crypto-shred terms](#5-cryptography--crypto-shred-terms)
6. [Retrieval & AI-plane terms](#6-retrieval--ai-plane-terms)
7. [The collaboration loop terms](#7-the-collaboration-loop-terms)
8. [Identity & external data-source terms](#8-identity--external-data-source-terms)
9. [Storage, memory, and build-process terms](#9-storage-memory-and-build-process-terms)
10. [Quick-reference tables](#10-quick-reference-tables)

---

## 1. How to read an entry

Each entry has up to four parts:

- **Term** — the canonical name. Code-spelled names (`like_this`) are the exact identifier the
  builder must type. Prose names (Like This) are concept labels.
- **Definition** — what it *is*, in concrete terms.
- **Why / chosen over** — the rationale, and the rejected alternative with the reason ("we chose
  X over Y because Z"), wherever the choice is non-obvious.
- **See** — the sibling doc + decision ID that owns the full detail.

Cross-references use the filename (e.g. `06-security-spine-lld.md`) and decision IDs (e.g. `D7`).

---

## 2. The 30-second mental model

Read this once; the rest of the glossary fills in the words.

TigerExchange is **one application on one Jetson AGX Orin 64GB**. It serves multiple **research
groups** (each one a **Tenant**) and runs a **closed collaboration loop**: a funding **Opportunity**
match starts a **Pursuit**; the platform assembles a cross-group **Team** from a living
**expertise graph**; the team **co-authors** a confidential **Proposal** inside an encrypted live
buffer; the funding **outcome** is recorded; and on a **win** the team + award + artifacts are
**written back** into the public graph so the next match is better. More collaboration → richer
graph → better matches → more funding.

Every data access — every retrieve, every egress to a model, every derivation — passes through
**one** in-process gate called the **PEP** (Policy Enforcement Point). Confidential content
(drafts, prior winning proposals) is physically isolated by row-level security, an encrypted
storage volume per tenant, and a single shared model that never leaks one tenant's request into
another's. The whole thing is sequenced as a **walking skeleton**: prove the loop end-to-end on
the simplest substrate first, then add breadth.

---

## 3. Organizational & tenancy terms

### Tenant (a.k.a. Group, Research Group)

**Definition.** A research group or institution living on the one box. The **Tenant is the unit of
isolation**: RLS scoping, KEK custody, per-tenant encrypted-tablespace crypto-shred, and the
per-tenant confidential retrieval surface are all keyed by `tenant_id`. In prose the words
"tenant", "group", and "research group" are interchangeable. `tenant_id` is a `uuid`, is the
**leading column** of every tenant-scoped index, and is pinned per request via `SET LOCAL` (see
[SET LOCAL](#set-local), [RLS](#rls-row-level-security)).

**Why / chosen over.** We model groups as tenants on **one** Postgres rather than
schema-per-tenant or database-per-tenant because a 64GB box cannot afford the migration sprawl and
resource duplication of many schemas/DBs (D5 rejected alternative). Isolation is enforced by
FORCE-RLS + a per-tenant encrypted volume instead — far cheaper per group.

**Federation note.** In the future cross-box layer (designed, **not built** — D2) a Tenant maps to
a *node*. That mapping is honest about what does **not** carry forward: the encrypted-tablespace
crypto-shred and the recursive-CTE ReBAC are node-local and would be rewrites, not transport swaps.

**See** `13-data-model-and-schemas.md §1` (the `tex.tenant` DDL), `D2`, `D5`, `D6`, `D7`.

### Tenant pair

**Definition.** The walking-skeleton test fixture: exactly **two** tenants (A and B) used to prove
cross-group collaboration and cross-tenant isolation end-to-end (e.g. "tenant A grounds on A's prior
proposal; tenant B physically cannot retrieve it"). P0 proves the loop on a tenant pair before any
breadth is added.

**See** `_design-brief.json → product_summary` (walking-skeleton), `D6` (P0.9 test).

### TenantContext

**Definition.** A **frozen** (immutable) request-scoped value object — the identity of a single
request: `tenant_id`, `subject_id`, the resolved `Entitlement`, optional `orcid_id` and
`request_id`. Built once from the OIDC token at the FastAPI boundary, then pinned to the Postgres
transaction via `SET LOCAL`. Because it is frozen, no module can escalate the request's tenant or
capabilities partway through.

**Why frozen.** Immutability is the guarantee that a feature module cannot mutate "who is asking"
mid-request to grant itself access. There is **no `tenant_context` table** — it is a transient
kernel object, not persisted.

**See** `05-kernel-contracts.md §5` (verbatim Pydantic), `13-data-model-and-schemas.md §3`, `D5`.

### Entitlement / Edition

**Definition.** **Entitlement** is the resolved, per-tenant, per-edition **capability set**
evaluated *at the PEP* (D4 steps 1–2). **Edition** is a capability *bundle* (P0 ships exactly two:
`discovery_only` and `collaboration`). Modules **read** an entitlement; they **never decide** one.
The edition→capability mapping is a **Python constant** in `mod-pep`, not a DB table.

**Why a code constant over a table.** The set is tiny and fixed; a table invites drift and a sync
bug a 30B builder would get wrong (D4 rationale). **Edition is purely a capability bundle, not a
price tier** — the business/pricing model is dropped entirely (D1).

**See** `05-kernel-contracts.md §4`, `13-data-model-and-schemas.md §4`, `D1`, `D4`.

### Capability

**Definition.** A `StrEnum` member naming one thing a request may be permitted to do. The five
**required** members (by name):

| `Capability` | Permits |
|---|---|
| `OWN_MATERIALS` | read/write the tenant's own (non-confidential) materials |
| `PUBLIC_RETRIEVAL` | query the SHARED cross-tenant public index |
| `CONFIDENTIAL_RETRIEVAL` | query the **per-tenant confidential retrieval surface** (own-tenant only) |
| `CROSS_GROUP_SHARE` | issue/accept a cross-tenant `SharingGrant` |
| `CONFIDENTIAL_DRAFTING` | run generation on the confidential locality + KV-isolation path |

**Why a closed `StrEnum`.** A closed set means `mypy` flags a typo like `PUBLIC_RETREIVAL`; the
persisted/logged form is the human-readable string (`"confidential_retrieval"`), not an int.
Chosen over bare `str` (no typo protection) and `IntEnum` (unreadable in audit rows).

**See** `05-kernel-contracts.md §4`, `D4`.

### Researcher / User

**Definition.** A person, anchored to a canonical **ORCID iD**. The **node identity in the
expertise graph**. A researcher holds memberships in one or more tenants and is the subject of
`subject_id`. The relational account row is `tex.app_user` (tenant-scoped, RLS); the *public graph*
references the researcher by `orcid_id`/`subject_id`, not by reading the RLS row.

**See** `13-data-model-and-schemas.md §2`, [ORCID](#orcid).

---

## 4. The security spine terms

### PEP (Policy Enforcement Point)

**Definition.** The **single in-process** authorization gate. `PolicyEnforcementPoint.authorize()`
is the sole chokepoint that every retrieve / egress / derive flows through. It returns **ALLOW or
DENY only** — it is binary and fail-closed; there is no "maybe". The PEP is built **first** (P0.2),
before any data plane, because everything downstream inherits its enforcement for free.

The PEP runs a **fixed, cheap-first, fail-closed decision order** (D4). Any step that errors or
abstains **DENIES**:

```
authorize(request) — fixed order, any error/abstain -> DENY:
  1. entitlement / edition gate        (Entitlement on request.context)
  2. capability gate                   (request.required_capability in entitlement)
  3. ABAC tier check                   (in-Python lattice: permits_tier + MAX-rule)
  4. ReBAC relation Check              (Postgres recursive CTE — LOCAL-only)
  5. owner-local durable tombstone read (AUTHORITATIVE deny)
  6. short-TTL lease                   (narrow-only positive cache)
```

**Why one fixed order.** The convergence finding was that several stores gating one decision with
*undefined composition* is a **fail-OPEN** risk. One stated order + durable-log-authoritative-deny
+ narrow-only caches removes the ambiguity a 30B builder would otherwise resolve unsafely. On one
box where every group shares the same process and disk, a single chokepoint is *more* important,
not less.

**Note on it returning ALLOW/DENY only.** The PEP never returns `QUARANTINE` — that is the
*classifier's* verb (see [Classify-gates-index](#classify-gates-index)). The classifier decides
whether *content* may enter an index; the PEP decides whether a *request* may proceed. Conflating
them would let a builder treat "quarantine" as a soft authorization state; there is no soft state in
authorization.

**See** `05-kernel-contracts.md §8` (`PepRequest`/`PepResponse`), `06-security-spine-lld.md`,
`D3`, `D4`.

### Broker (data-access broker)

**Definition.** The component **inside `mod-pep`** that actually fetches data after the PEP says
ALLOW. Feature modules receive **already-projected, already-tier-checked** objects from the broker;
they never open a DB connection, never import the raw store, never construct a
[`PublishableProjection`](#publishableprojection). The broker is the **only** code that constructs
a `PublishableProjection` and the **only** gate to the per-tenant confidential retrieval surface.

**The exact scope of the broker's credentials (load-bearing wording).** The broker holds raw-store
credentials **ONLY** for (a) the shared confidential-artifact / classification tables and (b)
per-tenant confidential-index access — **NOT** every module's schema.

**Why this precise scope.** This resolves the old "broker-as-god-object vs module-owns-its-data"
contradiction (D3). If the broker held creds to *every* schema it would re-centralize all coupling
(god object); if modules opened their own connections they could bypass RLS and the PEP order
(leak vector). Scoping the broker to shared+confidential tables only is the middle path. **Never**
describe the broker as "the only holder of raw-store credentials" — that wording is the banned god-
object framing.

**See** `06-security-spine-lld.md`, `_design-brief.json → security_spine` (chokepoint control), `D3`.

### Fail-closed

**Definition.** The system-wide default: **when in doubt, DENY / treat as most restrictive**.
Concretely:

- Any PEP decision step that errors or abstains → DENY.
- Unknown / abstained classification → `QUARANTINE` → treated **confidential**, never indexed to a
  shared sink.
- An empty tier join → `confidential` (the most restrictive tier).
- A transaction with no `SET LOCAL app.tenant_id` → returns **zero rows** (not an error, not all
  rows).
- A missing ABAC attribute or unavailable policy-information-point → DENY.
- A `PublishableProjection` with no stated discoverability scope → `NONE` (not discoverable).

**Why.** A 30B builder's natural instinct on an unknown case is often the *open* default (return
`public`, return all rows, allow). Every such default is pinned to the *closed* side and tested.
Fail-closed is the correctness backbone; the security CI gates exist to prove it holds.

**See** `05-kernel-contracts.md §3, §6`, `06-security-spine-lld.md`, all of `D4`/`D6`/`D7`.

### Tier (the confidentiality lattice)

**Definition.** Exactly **three** confidentiality tiers, totally ordered by restrictiveness:

```
public  <  private  <  confidential
(least restrictive)        (most restrictive)
```

- **public** — may enter the SHARED cross-tenant index; discoverable across tenants.
- **private** — tenant-internal, not cross-tenant-shared by default; local-only inference.
- **confidential** — highest tier. Confidential content (drafts, prior winning proposals) **never**
  enters the shared cross-tenant index, is **local-only inference always**, and is the target of
  crypto-shred. Unknown/abstained classification collapses to confidential.

`Tier` is an `IntEnum` in the kernel (`PUBLIC=0`, `PRIVATE=1`, `CONFIDENTIAL=2`) so the MAX-rule is
a literal numeric `max()`; it is persisted as the lowercase label (`"confidential"`), stored in
Postgres as the native `tex.tier` enum.

**Why three, not more.** A fixed tiny lattice is a few lines of fail-closed Python (in-process
ABAC), which beats standing up a policy engine (D4). The lattice is the *spine* of the whole
security model — every other control keys off it.

**See** `05-kernel-contracts.md §3`, `13-data-model-and-schemas.md §0.8`, `D4`, `D6`.

### MAX-rule (tier join)

**Definition.** When a derived artifact is produced from multiple inputs, its tier is the
**maximum (most restrictive)** of all input tiers. This is the **MAX-rule**, implemented as
`tier_join` (pairwise) and `tier_join_all` (over a set):

```python
tier_join(public, confidential)      == confidential
tier_join_all([public, private])     == private
tier_join_all([public, public])      == public
tier_join_all([])                    == confidential   # EMPTY -> MOST restrictive (load-bearing)
```

**Why MAX, and why empty → confidential.** MAX is the mathematical reason a confidential input can
**never** be laundered down to public through a derivation (e.g. a draft grounded on a public paper
*and* a confidential prior proposal is confidential). The **empty-list rule is the trap**: a 30B
builder's instinct is to return the *least* restrictive identity element (`public`) for an empty
join, which is a fail-OPEN bug. An empty input means "we do not know what went into this", so
unknown → most restrictive. This is a P0.0 acceptance test: `tier_join_all([]) == confidential`.
Chosen over returning `public` (fail-open) and over raising on empty (forces every caller to
special-case empty, inviting an unchecked path that defaults to public).

**See** `05-kernel-contracts.md §3.1`, `D4`, `D6`.

### ABAC (Attribute-Based Access Control)

**Definition.** The tier/classification check — PEP step 3. It is **in-process Python** using the
kernel lattice (`tier_join_all` MAX-rule, `Entitlement.permits_tier`, caveats re-evaluated at
access). **ABAC narrows, never widens** — it can only make access more restrictive (property-tested).

**Why in-Python, chosen over OPA / Cedar.** The ABAC ruleset is a tiny fixed 3-tier lattice + a
capability gate — a few lines of fail-closed Python beat standing up a policy engine: nothing to
sync, nothing to operate, and a module physically cannot bypass it because it lives inside the PEP.
We **rejected OPA** (a Go daemon + Rego + data-sync to operate, and a module could still call the
store around it) and we **rejected Cedar** (the old plan even listed Cedar as primary — a
contradiction the conventions outlawed). The single-box answer is **neither**: ABAC is in-Python.

**See** `CONVENTIONS-single-box.md §5` (ABAC row), `06-security-spine-lld.md`, `D4`. OPA/Cedar are
on the **FORBIDDEN** list.

### ReBAC (Relationship-Based Access Control)

**Definition.** The relation/membership check — PEP step 4. It is a **Postgres-native relation-tuple
table** `(subject, relation, object, tenant_id)` evaluated by a **recursive-CTE `Check()`** in the
same Postgres, behind the kernel `IPolicyEnforcement.check` Protocol. This is the Zanzibar tuple
model mapped onto one indexed table; recursive CTEs evaluate nested relations (e.g. group
memberships) fast.

**Why Postgres-CTE, chosen over SpiceDB.** The tuple model maps cleanly to one indexed Postgres
table, tuples inherit tenant RLS isolation, and it adds zero new infrastructure — pure SQL. We
**rejected SpiceDB / OpenFGA-as-a-service** (a separate datastore + operator + Go, high single-node
complexity).

**HONEST federation caveat.** The recursive-CTE `Check` resolves **LOCAL tables only**. Cross-box
federation needs *distributed* tuple resolution this cannot do — a **KNOWN federation-boundary
REWRITE**, not a transport swap. Do not claim otherwise.

**See** `CONVENTIONS-single-box.md §5` (ReBAC row) + `§12`, `06-security-spine-lld.md`,
`13-data-model-and-schemas.md §13` (`RelationTuple` DDL), `D4`, `D2`. SpiceDB is **FORBIDDEN** as a
P0 build.

### RLS (Row-Level Security)

**Definition.** The Postgres mechanism that makes a tenant invisible to other tenants. Every
tenant-scoped table carries **exactly** this policy shape (D5):

```sql
ALTER TABLE tex.<name> ENABLE ROW LEVEL SECURITY;
ALTER TABLE tex.<name> FORCE  ROW LEVEL SECURITY;   -- applies even to the table owner
CREATE POLICY tenant_isolation ON tex.<name>
    AS RESTRICTIVE                                   -- AND-combined; a later policy cannot WIDEN
    FOR ALL
    TO tigerexchange_app
    USING      (tenant_id = current_setting('app.tenant_id', true)::uuid)   -- read filter
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);  -- write filter
```

The app connects as `tigerexchange_app`, a **NOSUPERUSER / NOBYPASSRLS / NOINHERIT** non-owner
role. `tenant_id` is the **leading** index column.

**Why each clause.** `FORCE` closes owner-bypass; `AS RESTRICTIVE` stops a future migration from
OR-widening access (PERMISSIVE policies OR-combine); `WITH CHECK` blocks cross-tenant writes/
poisoning; `current_setting(..., true)` returns NULL when unset so `NULL = uuid` → not-true →
**zero rows** (the fail-closed property). Chosen over schema/database-per-tenant (sprawl,
resource-prohibitive on 64GB) and over PERMISSIVE policies / session-level `SET` (leak vectors).

**The four RLS-bypass lint vectors** (`check_rls_bypass.py`, P0.1) forbid: `SECURITY DEFINER`
functions; `MATERIALIZED VIEW` over a tenant table; a plain `VIEW` without
`WITH (security_invoker = true)` (the 3rd vector the old lint missed); and any `PERMISSIVE` policy
on a tenant table.

**See** `13-data-model-and-schemas.md §0.3–0.4`, `06-security-spine-lld.md`, `D5`.

### SET LOCAL

**Definition.** The mandatory way to pin the tenant for a request:
`SELECT set_config('app.tenant_id', $1, true)`. The third argument `true` makes it
**transaction-scoped** (= `SET LOCAL`). The value is passed as a **bound parameter** `$1`, never
string-interpolated.

**Why `SET LOCAL`, not `SET SESSION`.** Under PgBouncer **transaction mode**, connections are reused
across requests. `SET SESSION` would leak the previous tenant's context onto the next request on a
reused connection — a cross-tenant breach. `SET LOCAL` is scoped to the transaction and is
leak-proof under pooling. The bound parameter avoids `tenant_id` SQL injection.

**See** `13-data-model-and-schemas.md §0.1, §3`, `06-security-spine-lld.md`, `D5`.

### PublishableProjection

**Definition.** The **single shape allowed to cross into the SHARED / cross-tenant retrieval
surface**. It is an *allowlist projection*: an explicit, named subset of public/private fields of
some entity. Its validator **rejects `confidential` tier** so confidential content can never even
be *constructed* into a shape destined for the shared index. **Only the broker constructs it** (an
import-linter + AST test forbids any feature module from importing or instantiating it).

Fields: `entity_ref`, `tier` (public|private only), `fields` (the allowlisted mapping),
`discoverability_scope` (a `DiscoverabilityScope` enum, default `NONE`), `projection_version`
(monotonic, ≥ 1).

**Why an allowlist projection that rejects confidential.** It is the *structural* guarantee that
confidential-tier content cannot be shaped for the shared index — if any module could build one,
that guarantee evaporates (D3/D6). There is no "include everything" mode. We **rejected query-time
post-filtering of one shared index** because that leaves confidential vectors/postings physically
present in a cross-tenant index = a standing breach.

**`discoverability_scope`** is a future-federation seam that is **carry-forward-clean** (it survives
unchanged into the eventual cross-box layer, unlike crypto-shred and CTE-ReBAC). Members: `NONE`
(default, not discoverable anywhere — fail-closed), `TENANT_LOCAL`, `SHARED_BOX` (the P0 cross-tenant
public surface), `FEDERATED` (deferred — never emitted in P0).

**`projection_version`** feeds the [monotonic applier](#monotonic-applier) so a stale, lower-version
re-ingest cannot resurrect a revoked/down-classified record.

**See** `05-kernel-contracts.md §7` (verbatim validator), `13-data-model-and-schemas.md`, `D3`,
`D6`, `D2`, `D12`.

### Classify-gates-index

**Definition.** The hard fail-closed ingestion edge: **a record is classified BEFORE it can be
embedded / indexed / graphed.** Only `ClassificationResult.is_retrievable` records (i.e.
`Decision.ALLOW` **and** `tier == public`) reach the **SHARED cross-tenant** sink (vector / BM25 /
graph / outbox). Classifier abstention or ambiguity → **QUARANTINE** (treated confidential) → a
**human adjudication queue**, never indexed. The walking-skeleton P0 classifier is **binary
allow/quarantine** (the `DENY` member exists in the model for hard policy/license denials but P0
emits only ALLOW/QUARANTINE).

`Decision` is a `StrEnum`: `ALLOW`, `QUARANTINE`, `DENY`. `is_retrievable` is the single predicate
the shared-index edge consults: `is_retrievable == (decision == ALLOW) AND (tier == PUBLIC)`.

**Why classify *before* index, fail-closed.** If a record could be embedded/indexed before
classification, a quarantined or confidential record could leak into the shared cross-tenant index =
a standing breach. Structural fail-closed enforcement at the edge is the only safe order. We
**rejected classifier fail-open on low confidence** (violates fail-closed) and **rejected making
confidential content wholly unindexable** (that would kill own-tenant grounding — the moat; instead
see the per-tenant confidential surface below).

**See** `05-kernel-contracts.md §6` (verbatim), `09-ingestion-and-identity-resolution-lld.md`,
`D6`.

### Per-tenant confidential retrieval surface

**Definition.** A **tenant-scoped, RLS-isolated** vector + BM25 retrieval index that holds **only
that tenant's own** confidential drafts and prior winning proposals, living on the tenant's
**encrypted tablespace** (so its DEK destruction = crypto-shred). It is queryable **only** by that
tenant's confidential drafting path (PEP-enforced, requires `CONFIDENTIAL_RETRIEVAL`). Backed by the
table `tex.confidential_index_entry` and the `ConfidentialIndexEntry` row model. It uses the **same
two-stage hybrid+rerank pipeline** as the shared public surface, just on its own encrypted
tablespace.

**Why a separate surface exists at all (the key clarification).** "Confidential content never enters
any **shared** index" means the **cross-tenant public** index — it does **NOT** mean confidential
content is unindexable for its **owning tenant**. If it were unindexable, the centerpiece moat
(grounding drafts in the tenant's own prior winning proposals) would be non-functional. So:
- Tenant A grounds its draft on A's prior proposals.
- Tenant B physically cannot retrieve A's confidential entries (proven by the HUMAN-authored P0.9
  test `confidential-surface-cross-tenant-denied`).

We **rejected query-time post-filtering of one shared index** (leaves confidential content
cross-tenant-visible) and **rejected making confidential content wholly unindexable** (kills the
moat).

**See** `13-data-model-and-schemas.md §10` (`tex.confidential_index_entry`),
`07-data-layer-and-retrieval-lld.md`, `_design-brief.json → retrieval_design`, `D6`, `D7`, `D8`.

### Revocation / Tombstone

**Definition.** **Owner-authoritative, fail-closed** access removal. Revocation **commits (fsync) to
a durable `revocation_log` BEFORE any allow/deny observes it**. The durable log is **authoritative
for DENY** (PEP step 5). Crash-recovery rebuilds authorization strictly from the durable log and
**refuses confidential reads until recovery completes** (anti-resurrection). Revocation-by-reason:
`security`/`consent` reasons give a **zero allow-window** (immediate). The owner re-derives effective
scope; a caller's claimed scope is an **untrusted hint**. `revocation_epoch` is a monotonic counter
feeding the [monotonic applier](#monotonic-applier).

**Why durable-before-observe.** On one box there is no global consensus to worry about, so what
matters is **durability + crash recovery**. Committing the revocation durably before any decision can
observe it is what guarantees a crash mid-revocation leaves the object **denied**, not resurrected —
proven every CI by an injected-clock `crash-mid-revocation stays-denied` test.

**See** `06-security-spine-lld.md`, `_design-brief.json → security_spine` (revocation control),
`13-data-model-and-schemas.md` (`revocation_log`), `D2` (owner-authoritative is carry-forward-clean).

### Audit spine / `AuditEvent`

**Definition.** A **per-stream hash-chained, tamper-evident** security record:
`prev_hash -> entry_hash` with periodic locally-signed chain-head checkpoints, stored in Postgres.
Records PEP decisions, classification, revocation, egress, grant-issued. The kernel defines the
carrier shape (`AuditEvent`); the **hash chaining is computed by the `IAuditSink` implementation**
in `mod-audit`, never in the kernel.

**Two streams, never mixed.** The security `AuditEvent` stream (hash-chained) is **separate** from
the non-security [`LoopEvent`](#loopevent--loop-event-stream) product-analytics stream. A loop event
**must not** write to the security stream (P0.3 acceptance).

**Why local hash-chaining only.** A tamper-evident record of who accessed which group's confidential
artifact under which grant is a right-sized multi-group moat and lets you prove a revoked grant
stopped serving. External RFC-3161 / transparency-log anchoring is **dropped** — it is a
federation/compelled-operator concern, not relevant to a self-hosted box.

**See** `05-kernel-contracts.md §11.2, §10.2` (`IAuditSink`), `06-security-spine-lld.md`,
`_design-brief.json → security_spine` (audit control).

### Security-contract CI gates (HUMAN-authored)

**Definition.** The adversarial test suite that encodes the security spine as executable invariants
(zero-leak classifier, broker-over-assert-denied, BOLA cross-tenant-read-denied,
confidential-surface-cross-tenant-denied, post-crypto-shred zero-decryptable-hits across **both**
paths, lower-tier-cannot-construct-confidential-request, crash-mid-revocation-stays-denied,
MAX-rule + ABAC-narrows-only, etc.). These live in `tests/security/`.

**Hard rule: these are authored by a HUMAN, not by the 30B builder.** The builder writes the
*implementation* until the human-authored gates go green; the builder MUST NOT add, weaken, skip, or
`xfail` anything in `tests/security/`. The builder MAY write non-security unit/integration tests in
`tests/unit/` and `tests/integration/`.

**Why.** A mid-size local model cannot be trusted to author the tripwires that prove it did not
introduce a leak — if the same model writes both the code and the tests, a subtle fail-open path can
pass its own weak test.

**See** `CONVENTIONS-single-box.md §10`, `_design-brief.json → security_spine` (last control).

---

## 5. Cryptography & crypto-shred terms

### KEK (Key-Encryption-Key)

**Definition.** A **per-tenant** key that wraps (encrypts) that tenant's DEK. KEKs are held by the
in-process `LocalKms`, themselves **encrypted under ONE box-master key**. The kernel never holds key
bytes — it holds an opaque `KeyRef` (`kek_id`, `tenant_id`).

**See** `05-kernel-contracts.md §9.4` (`KeyRef`), `06-security-spine-lld.md`, `D7`.

### DEK (Data-Encryption-Key)

**Definition.** A **per-tenant** key that does the actual encryption work. The same DEK does **two**
jobs (this is the crucial split): (1) **AES-256-GCM** on **non-searchable blobs**, and (2)
**unlocking the per-tenant encrypted tablespace** that holds the **searchable** confidential indexes.
The DEK is wrapped by the tenant's KEK.

**See** `05-kernel-contracts.md §9–10` (`IKms`), `D7`.

### LocalKms / `IKms`

**Definition.** The dependency-free, **in-process** key-management service behind the kernel `IKms`
Protocol. It creates per-tenant KEKs, unwraps DEKs, does AES-GCM on blobs, and exposes
`destroy_kek()` (crypto-shred). The **box-master key** that wraps the KEKs is anchored, at P0 by
default, by **either**:
- **fTPM via userspace `tpm2-tools` / `tpm2-pytss`** — seal the master key to a TPM PCR (no custom
  Trusted Application), **or**
- a **passphrase-derived** master key (NIST SP 800-108 KDF), entered at boot, **never written to
  disk**.

**Why LocalKms + fTPM/passphrase, chosen over CloudHSM and over OP-TEE/EKB.** We **rejected
CloudHSM / cloud-KMS** because it contradicts the no-cloud single box. We **demoted OP-TEE/EKB**
(the secure-world hardware anchor) out of the P0 build because it requires irreversible OEM
fuse-burning + Secure Boot provisioning + a custom OP-TEE Trusted Application **in C**, with
documented unresolved NVIDIA-forum failures — a hard build wall for a Python-writing 30B builder.
OP-TEE/EKB stays as **optional human-operator hardening** behind the same `IKms`. We also **rejected
a raw key file** (master key plaintext on the slow HDD — unacceptable).

**See** `05-kernel-contracts.md §10.2` (`IKms`), `06-security-spine-lld.md`,
`CONVENTIONS-single-box.md §5` (KMS row), `D7`. OP-TEE/EKB-as-build-deliverable and CloudHSM are
**FORBIDDEN**.

### Crypto-shred

**Definition.** Erasing data **by destroying the key**, in O(1), instead of physically deleting
every record across every engine. `destroy_kek()` is the primitive. After it runs, **both** of the
following become permanently undecryptable for that tenant: the AES-GCM blobs AND the
encrypted-tablespace searchable indexes. A post-shred **zero-decryptable-hits** CI gate proves
erasure across both paths.

**Why crypto-shred, chosen over per-record physical deletion.** Per-record deletion across vector +
BM25 + graph + blob stores is **unprovable** and **races** (a partially-deleted state is a leak).
Destroying the single key is O(1) and provable.

**The crypto-shred SPLIT (the single most important crypto detail — do not invert it).** Crypto-shred
is split **by searchability**:

| What | Mechanism | Why |
|---|---|---|
| **SEARCHABLE** confidential derivatives (per-tenant vector / BM25 / graph indexes) | **Encrypted-tablespace + DEK-destroy** (see below) — **PRIMARY**, not a fallback | AES-GCM on vectors/BM25 is mathematically unsearchable |
| **NON-searchable** confidential blobs (CRDT snapshots, autosave, version history, eval traces, cache values) | **AES-256-GCM application-layer encryption** (see below) | ALE is correct exactly where data is never searched |

**See** `06-security-spine-lld.md`, `CONVENTIONS-single-box.md §5–6`, `D7`. This split is a named
**open_risk** (builder might invert it) — the build deliberately builds the blob path (P0.4a) before
the searchable path (P0.4b, after the data plane P0.5 exists).

### Encrypted tablespace (a.k.a. LUKS / dm-crypt volume) — for SEARCHABLE derivatives

**Definition.** A per-tenant **encrypted block device** (LUKS / dm-crypt volume, surfaced to
Postgres as a per-tenant tablespace) that holds the tenant's confidential **searchable** indexes
(vector + BM25 + graph). The index data is **plaintext-AT-REST *inside* the encrypted volume** — so
it is fully searchable while the volume is **mounted** (HNSW needs real distances) — and is
crypto-shredded by **destroying the per-tenant DEK** that unlocks the volume, then drop-and-rebuild.

**Why this is the PRIMARY mechanism for searchable indexes (and why NOT AES-GCM them).**
Application-layer **AES-GCM on vectors/BM25 postings is mathematically impossible to search**: AES
ciphertext destroys the distance metric pgvector/HNSW need, and encrypted postings cannot be
tokenized/scored. So volume-level encryption is the **only workable** crypto-shred for searchable
derivatives. The prior design had this **inverted** (it labeled "ALE on vectors before insert" as
primary) — that would produce a broken or insecure system. A HUMAN-authored test asserts the
confidential vector surface remains **SEARCHABLE while mounted** (proving we did not AES-GCM the
vectors) AND yields **zero decryptable hits after DEK destruction**.

**Federation note.** This mechanism is **node-local** — a future `IRevocationAuthority` cannot
crypto-shred another node's tablespace. It is a **KNOWN federation-boundary REWRITE**, not a
transport swap.

**See** `13-data-model-and-schemas.md §10, §0.6` (placement + partition-per-tenant detail),
`06-security-spine-lld.md`, `CONVENTIONS-single-box.md §5`, `D7`, `D2`.

### AES-GCM blob (application-layer encryption, ALE) — for NON-searchable blobs ONLY

**Definition.** **AES-256-GCM** via the `cryptography` library, under the per-tenant DEK, applied
**only** to **non-searchable at-rest blobs**: CRDT draft snapshots, autosave, version history,
eval traces, and cache **values**. The kernel exposes `IKms.encrypt_blob` / `decrypt_blob` for this.
`destroy_kek()` reaches these blobs too.

**Why ALE here and ONLY here.** ALE is the right mechanism **exactly** where data is never searched
(opaque blobs) and the **wrong** mechanism for indexes. Scoping ALE to blobs makes crypto-shred
reach drafts/history/eval while leaving searchable indexes to the encrypted-tablespace mechanism.
We **rejected homomorphic / searchable / distance-preserving encryption** (research-grade, x86-tuned,
beyond the builder). **AES-GCM on vectors / BM25 postings / graph edges is FORBIDDEN.**

**See** `05-kernel-contracts.md §10.2` (`encrypt_blob`), `CONVENTIONS-single-box.md §5–6`, `D7`.

---

## 6. Retrieval & AI-plane terms

### Two-stage retrieval / `IRetrievalStrategy`

**Definition.** P0 retrieval is a **two-stage pipeline behind ONE `IRetrievalStrategy`**, with all
three sub-stores (`IVectorStore`, `ILexicalIndex`, `IGraph`) backed by a **single Postgres 16**:
- **Stage 1 (hybrid):** dense vector search (pgvector HNSW) + native BM25, fused with **RRF k=60 in
  SQL**.
- **Stage 2 (rerank):** a local cross-encoder reranks top-50 → top-8.

The same pipeline serves **two surfaces**: the SHARED public index and each tenant's per-tenant
confidential surface (selected by the `confidential_surface` flag).

**Why single-Postgres, chosen over Qdrant+OpenSearch.** A memory-shared 64GB Orin with a slow HDD
cannot afford four always-on services (Qdrant + OpenSearch + SpiceDB + Apache-AGE) competing for the
RAM the models need. One transactional store also makes per-tenant RLS and tablespace crypto-shred
dramatically simpler. We **rejected Qdrant/OpenSearch as P0 stores** (demoted to documented future
scale-out adapters) and **rejected Apache AGE** (the graph is fine as an edge table).

**See** `05-kernel-contracts.md §10.2` (Protocols), `07-data-layer-and-retrieval-lld.md`,
`_design-brief.json → retrieval_design`, `D8`. Qdrant/OpenSearch/Apache-AGE are **FORBIDDEN** at P0.

### RRF (Reciprocal Rank Fusion)

**Definition.** The parameter-free fusion that combines the dense and BM25 result lists into one
ranked list, **in SQL**, with `k=60`. Each item's fused score is the sum over lists of
`1 / (k + rank_in_that_list)`.

**Why RRF, chosen over learned/convex fusion.** RRF is **parameter-free**, **score-scale-immune**,
and needs **ZERO labeled data** — exactly right for a fresh deployment. We **rejected
learned/convex fusion** because it needs per-tenant labels you will not have at launch (deferred
until labels exist).

**See** `07-data-layer-and-retrieval-lld.md`, `D8`.

### BM25 / lexical index / `ILexicalIndex`

**Definition.** Exact-keyword (lexical) search over text, scored by the BM25 ranking function.
Implemented as a **native Postgres BM25 index** — **VectorChord-BM25** (`vchord_bm25`) by default,
with **ParadeDB `pg_search`** as a co-equal verified alternate (use whichever **builds and
benchmarks** on the real aarch64 box; P0.5 includes an **on-box BM25 benchmark** test).

**Why BM25 is non-optional.** Scholarly + grant queries are **entity-heavy** — author/lab names,
grant/solicitation numbers, gene/method acronyms — which dense vectors miss. **No inherited x86
"3x-vs-Elasticsearch" number is relied upon**; the only rationale that matters here is one-engine
consolidation, and the only number that counts is the one benchmarked on the actual box.

**See** `07-data-layer-and-retrieval-lld.md`, `13-data-model-and-schemas.md §5b`,
`_design-brief.json → retrieval_design`, `D8`. ParadeDB is the fallback if VectorChord's Rust
extension will not build (a named open_risk).

### Dense vector search / pgvector HNSW / `IVectorStore`

**Definition.** Approximate nearest-neighbor search over dense embeddings, using **pgvector with an
HNSW index**, kept **RAM-resident / on NVMe**. This is the **verified P0 default**. The
`IVectorStore` Protocol exposes `create_collection_if_absent` (**create-if-absent, never
recreate**), `upsert`, and `search`.

**Why HNSW RAM-resident, and why RaBitQ is P1-only.** HNSW is **pure random I/O** and **catastrophic
off the HDD** (10s+ queries), so the live index MUST stay RAM-resident / on NVMe regardless. The
disk-friendly **VectorChord IVF+RaBitQ / DiskANN-style** ">RAM index" is a **P1 verify-then-adopt**
task, **NOT a P0 dependency** — its arm64 status is needs-verification and it does not gate P0.

**See** `05-kernel-contracts.md §10.2` (`IVectorStore`), `13-data-model-and-schemas.md §5b`,
`CONVENTIONS-single-box.md §9` (create-if-absent), `D8`. `recreate_collection` is **FORBIDDEN**.

### Rerank / cross-encoder

**Definition.** Stage 2 of retrieval: a **local cross-encoder** scores each (query, candidate) pair
and reorders the top-50 → top-8. Model: **bge-reranker-v2-m3 (568M)** or **Qwen3-Reranker-0.6B**,
served via a dedicated vLLM score-endpoint process **or** a sentence-transformers `CrossEncoder`
in-process (the memory saver — avoids a third CUDA context). Exposed by `IModelRouter.rerank`.

**Why rerank.** It adds **+5–15 nDCG@10 for <200ms** and is the cheapest large quality win (two-stage
beats single-stage: Recall@5 0.816 vs 0.695). We **rejected Ollama** for this (it has **no
`/api/rerank`** endpoint as of 2026) and **rejected large rerankers** (won't fit hot beside the 30B).

**See** `08-ai-plane-and-model-router-lld.md`, `07-data-layer-and-retrieval-lld.md`,
`_design-brief.json → retrieval_design`, `D8`, `D9`.

### HippoRAG2

**Definition.** A graph-augmented retrieval technique (Personalized-PageRank over the metadata
graph, ~1k tokens/query) that boosts retrieval using graph structure. It is a **P1 SQL/Python add**,
**NOT a P0 deliverable**. The P0 graph is a deterministic metadata edge table traversed by
bounded-hop recursive CTEs; HippoRAG2 layers PPR on top later.

**Why P1, and what was rejected.** P0 is single-shot hybrid+rerank only. We **rejected Microsoft
GraphRAG global summarization** (~331k tokens/query) as infeasible on an edge box, and **rejected
Apache AGE** (another engine to operate; the edge table + recursive CTE is enough).

**See** `07-data-layer-and-retrieval-lld.md`, `_design-brief.json → retrieval_design`, `D8`.

### `IGraph` / metadata-backbone edge table

**Definition.** The expertise/collaboration graph, stored as a **deterministic edge table**
(authors / papers / citations / affiliations / venues / grants / topics) and traversed by
**bounded-hop recursive CTEs** (e.g. `ego_net(node, max_hops)` — `max_hops` is **required bounded**;
no unbounded walks). It is built from corpus metadata with **no recurring LLM entity-extraction
tax**. This same graph **IS** the collaborator-discovery product surface.

**See** `05-kernel-contracts.md §10.2` (`IGraph`), `07-data-layer-and-retrieval-lld.md`, `D8`.

### Embedder (serve-time) — bge-m3

**Definition.** The **single serve-time retriever embedder**: **bge-m3** (dense+sparse+ColBERT, 8192
ctx, 568M) or **Qwen3-Embedding-0.6B**. It produces the 1024-dim dense vectors stored in the HNSW
column. Exposed by `IModelRouter.embed`.

**Why small, chosen over Qwen3-Embedding-8B.** It must coexist with the 30B generator in 64GB. We
**rejected Qwen3-Embedding-8B** (MTEB #1 but an 8B resident model is not worth it on a shared box).

**See** `08-ai-plane-and-model-router-lld.md`, `13-data-model-and-schemas.md §5b` (`vector(1024)`),
`D8`.

### SPECTER2 (INGEST-ONLY, then unloaded)

**Definition.** A **citation-aware** embedding model (SPECTER2 base + PROXIMITY adapter via the
`adapters` library) that produces the paper-similarity / ExpertiseFingerprint vectors. It is a
**SECOND embedding space** and is **INGEST-ONLY**: run as a **batch job at ingest to precompute**
the vectors, then **UNLOADED**. It is **NEVER serve-resident** and **NEVER served by vLLM pooling**.

**Why ingest-only, chosen over keeping it resident.** SPECTER2 beats general models on
citation-proximity (which powers collaborator discovery), but it is an adapter on SciBERT — not a
drop-in sentence-transformers model — and a second resident embedding space at serve-time wastes
RAM. Precomputing at ingest then unloading means it costs **~0GB at serve** and appears **only in the
INGEST-WINDOW budget**. Fallback: if the `adapters` library is troublesome on aarch64, use bge-m3 for
the connectivity/similarity axis at reduced citation-precision and make SPECTER2 a P1 enhancement.

**See** `04-tech-stack-and-arm64-runbook.md`, `09-ingestion-and-identity-resolution-lld.md`,
`CONVENTIONS-single-box.md §5` (SPECTER2 row), `D8`. A second resident SPECTER2 at serve is
**FORBIDDEN**.

### `IModelRouter` / `IModelProvider` / the tier→locality guard

**Definition.** `IModelRouter` is the classification-routed inference façade (`generate`, `embed`,
`rerank`). `IModelProvider` is a single backing model process. Both the router and the egress
transport read **ONE owned `tier→locality` policy table**; **disagreement between them HARD-FAILS**.
**Confidential / private → in-boundary (local) inference ONLY**; public may use cloud.
`GenerationResult.served_locally` MUST be True for confidential/private.

**Why two enforcement points, one table.** It stops router/transport **drift** — if the router and
the transport could disagree about whether a request is allowed to egress, a confidential draft could
leak. Forcing both to read the same table and hard-failing on disagreement closes that gap.

**See** `05-kernel-contracts.md §10.2`, `08-ai-plane-and-model-router-lld.md`, `D9`, `D10`.

### Generator (the shared 30B) / Qwen3-30B-A3B

**Definition.** **ONE shared vLLM process** serving **Qwen3-30B-A3B** (MoE, 30.5B total / 3.3B
active per token) at **W4A16 AWQ or GPTQ-Int4**, ~17GB resident. The **same one process** serves all
tenants, including confidential drafting. Plan SLOs against ~30–45 tok/s decode and ~2000 tok/s
prefill.

**Why MoE 30B in ONE process, chosen over a dense 32B and over a second copy.** MoE activation
sparsity keeps **decode bandwidth-bound at ~3B speed at near-32B quality** (a dense Qwen2.5-32B is
~19GB AND slower to decode). Critically, there is **only ONE resident copy** — a second resident 30B
(~17GB weights + 4–8GB context) would push the total to ~70GB > 64GB, so the centerpiece path could
not run. **A second resident 30B copy is FORBIDDEN.** Fallback: Qwen3-14B dense (~9GB INT4), used if
the MoE quant misbehaves, or by an *optional* dedicated confidential process **with the 30B evicted
first** — never two 30B copies resident.

**See** `08-ai-plane-and-model-router-lld.md`, `CONVENTIONS-single-box.md §5`, `D9`, `D10`.

### Confidential KV isolation (one shared generator, prefix-caching off + serialized)

**Definition.** How one shared generator safely serves confidential requests **without a second
model copy**: (a) **disable prefix caching** for confidential requests
(`--enable-prefix-caching=False` on that path) so no prefix/KV is shared across requests, and (b)
**strictly serialize** confidential vs non-confidential requests with a KV-cache boundary. **No
per-confidential-tenant model duplication. No GPU MIG.**

**Why this is safe and fits, chosen over a dedicated process and over MIG.** vLLM does **not** leak
KV across separate requests by default; the real cross-request leak vector is **shared-prefix
caching**, which we disable for confidential requests. A **dedicated vLLM process per confidential
tenant** would require a second full resident 30B (the fatal ~70GB arithmetic above) — **rejected**.
**GPU MIG is physically unavailable on the Orin Ampere GPU** — **rejected**, deferred to a future
Thor/Blackwell. A startup/route assertion enforces prefix-caching-off; a HUMAN-authored test verifies
a confidential request does not reuse a cached prefix.

**See** `08-ai-plane-and-model-router-lld.md`, `_design-brief.json → security_spine`
(confidential-isolation control), `D10`. Second 30B copy and MIG are both **FORBIDDEN**.

### RAGAS / in-boundary judge

**Definition.** The retrieval/generation evaluation: RAGAS faithfulness + context precision/recall +
nDCG@k / Recall@k on a small per-tenant gold set, wired into CI as a regression gate. The judge LLM
is the **in-boundary local 30B** — **mandatory**, because confidential drafts forbid a cloud judge.
Eval artifacts are **confidential-tier** (AES-GCM blob, crypto-shred-reachable).

**See** `07-data-layer-and-retrieval-lld.md`, `_design-brief.json → retrieval_design`, `D8`.

### Partial-failure policy

**Definition.** The two retrieval surfaces fail differently: **public/shared discovery** returns
**partial-results-with-an-honest-completeness-indicator** (never whole-query-fail); the
**confidential path** is **whole-query-fail-closed**. A 30B builder must not "degrade" the
confidential path the way it degrades public discovery.

**See** `07-data-layer-and-retrieval-lld.md`, `_design-brief.json → retrieval_design`.

---

## 7. The collaboration loop terms

### The collaboration loop (the centerpiece)

**Definition.** The closed, compounding five-stage cycle that is the product's reason to exist
(D1): (1) **discover/trigger** a funding match → (2) **assemble** a cross-group team → (3)
**confidentially co-author** a proposal → (4) record the **outcome** → (5) on a **win**, **write
back** team + award + artifacts into the public graph. More collaboration → richer graph → better
matches → more funding.

```mermaid
flowchart LR
    O[1. Opportunity match\n(mod-funding)] --> P[Pursuit created]
    P --> T[2. Team assembled\n(mod-discovery: coverage + connectivity)]
    T --> C[3. Confidential co-author\n(mod-workspace CRDT + dual-source grounding)]
    C --> R[4. Outcome recorded\nproposal.outcome_recorded]
    R -->|WIN| W[5. Write-back edge\n(loop-engine: CO_PI_WITH + outcome signal + WORK nodes)]
    W -. richer graph -> better next match .-> T
```

**Why a closed loop is the moat (D1).** Incumbents are structurally split across this loop (RIM
tools stop at discovery; grant-writers never ground in a shared corpus; intro tools hand off to
humans). TigerExchange owns the **seams** they lack and is the only design that **learns from
outcomes**. We deliberately do **NOT** compete on funder-database breadth (unwinnable on one
HDD-bound box); the moat is depth-within-tenant + per-tenant confidentiality + the outcome-learning
loop.

**See** `01-product-and-loop-overview.md`, `12-collaboration-loop-and-writeback-lld.md`, `D1`, `D12`.

### Pursuit

**Definition.** **THE loop-threading object.** A single durable domain object that binds a matched
**Opportunity → draft Proposal → candidate Team + ongoing match alerts**, threading all five loop
stages. It is the "single sticky home" that creates data gravity (an Instrumentl-style project +
tracker analog). Tenant-scoped (RLS). Its `lifecycle_state` is a state machine
(`draft → matched → team_forming → drafting → submitted → won/lost/abandoned`); the terminal `won`
state fires `proposal.outcome_recorded`, which triggers the write-back edge.

**Why a first-class object, chosen over not modeling it.** The v2 plan had all the pieces but never
**wired the loop**; a single durable Pursuit object is what makes the loop first-class and testable.

**See** `13-data-model-and-schemas.md §8` (`tex.pursuit`),
`12-collaboration-loop-and-writeback-lld.md`, `D1`, `D12`.

### Proposal

**Definition.** The **confidential co-authored grant proposal**. **MAX-rule confidential tier**
(DB-pinned: `CHECK (tier = 'confidential')`). Its *content* lives as (a) a live **CRDT** buffer,
snapshotted as an **AES-GCM non-searchable blob** into the KEK-bound draft store, and (b) indexed
into the **owning tenant's confidential retrieval surface** for own-tenant grounding. The `proposal`
row is the relational anchor; it **never** enters the shared cross-tenant index.

**See** `13-data-model-and-schemas.md §9` (`tex.proposal`),
`11-mod-workspace-confidential-coauthoring-lld.md`, `D6`, `D7`, `D11`.

### Dual-source grounding

**Definition.** `mod-lit-intelligence` grounds a draft on **TWO** retrieval surfaces for the owning
tenant: (A) the **SHARED PUBLIC** corpus index (cross-tenant, public-tier only) **AND** (B) the
**per-tenant CONFIDENTIAL retrieval surface** (the tenant's own prior winning proposals + drafts).
This is the explicit resolution of the "Stage-3 grounding vs public-only" contradiction.

**Why both, not public-only.** Grounding a draft in the tenant's **own prior winning proposals** is
the centerpiece moat; grounding only on the public corpus throws that away. Isolation guarantees
tenant A grounds on A's proposals and tenant B cannot retrieve them.

**See** `10-feature-modules-lld.md`, `07-data-layer-and-retrieval-lld.md`, `D6`.

### Team / TeamMember (`TEAM_ROLE`)

**Definition.** The assembled cross-group team and each member's scoped, revocable workspace role —
Notion-style: **PI = owner, co-PI = edit, reviewer = comment, viewer = view**, with a permission
cascade and **highest-permission-wins**. Members may span tenants (`member_tenant_id` may differ from
the team's owning `tenant_id` — that cross-group act is what the activation north-star measures).

**RLS subtlety.** The `team_member` row is owned by the *workspace-owner* tenant; a member from a
*different* tenant gets access via a `SharingGrant` / `relation_tuple` resolved by the ReBAC Check —
**not** by reading `team_member` directly. `revoked_at` is a soft UI signal; the **authoritative**
deny is the durable revocation log.

**See** `13-data-model-and-schemas.md §11` (`tex.team_member`),
`11-mod-workspace-confidential-coauthoring-lld.md`, `D11`.

### SharingGrant

**Definition.** A **revocable, scope-bounded cross-group access grant** that lights up cross-tenant
workspace membership. **Owner-authoritative** (the owner tenant re-derives effective scope; a
caller's claimed scope is an untrusted hint). It is materialized as a `RelationTuple` (for the ReBAC
Check) plus human-facing metadata (scope, expiry, reason) in `tex.sharing_grant`.

**See** `13-data-model-and-schemas.md §12`, `06-security-spine-lld.md`, `D2` (owner-authoritative
is carry-forward-clean), `D11`.

### CRDT / real-time mode

**Definition.** **CRDT** = Conflict-free Replicated Data Type — a data structure whose concurrent
edits **merge in any order** without a central coordinator. TigerExchange uses **Yjs/y-crdt via
`pycrdt`** (aarch64 wheels), served by a self-hosted **pycrdt-websocket** server on the box. The
CRDT doc is the **live edit buffer**, periodically snapshotted (AES-GCM blob) into the KEK-bound
draft store.

**Real-time mode** = the walking-skeleton P0 editorial mode: **REAL-TIME concurrent edit only**.
Suggesting / tracked-changes (PI accept/reject) and anchored comments + resolve are **P1**, not P0.

**Why CRDT, chosen over OT and last-write-wins.** CRDT merges in any order, survives server restart,
and supports offline edit + autosave recovery — fully self-hostable on one box. We **rejected
Operational Transformation** (requires a central server, worse offline/recovery) and **rejected
last-write-wins** (silently loses concurrent edits).

**Why real-time-only at P0, chosen over shipping all editorial modes.** Shipping all three editorial
modes + scoped roles + cascade in P0 is too large a surface for a 30B builder to get the
confidentiality right; **real-time edit alone proves the cross-group aha-moment** (the activation
north-star) and the confidential-snapshot + revocation security path.

**See** `11-mod-workspace-confidential-coauthoring-lld.md`, `CONVENTIONS-single-box.md §5` (CRDT
row), `D11`.

### Outcome / `proposal.outcome_recorded`

**Definition.** Loop Stage 4. `mod-funding` records the funding result — `submitted` / `won` /
`lost` — emitting the event `proposal.outcome_recorded`. A **won** outcome is the trigger for the
write-back edge (Stage 5).

**See** `12-collaboration-loop-and-writeback-lld.md`, `D12`.

### Write-back edge (the compounding edge)

**Definition.** Loop Stage 5 — **the centerpiece data flow the v2 plan never wired.** On
`proposal.outcome_recorded` (won), a **Dagster outbox sensor** fires a **semaphore-gated async**
enrichment job (the WRITEBACK-WINDOW) that, off the interactive hot path: (i) materializes in-platform
**`CO_PI_WITH`** edges between actual team members (tagged with the proposal/award); (ii) attaches a
**transparent outcome-weighted expertise signal** per member for the RFP concepts — **ONE signal
among similarity + connectivity**, to dodge the incumbency-bias trap; (iii) ingests produced
artifacts as new public **WORK** nodes through the **same classify-gates-index monotonic applier**.

A contract test asserts a **won outcome demonstrably changes a subsequent match ranking** (the
compounding contract test).

**Why async + semaphore-gated, chosen over synchronous and over uncapped async.** Synchronous
write-back would put slow HDD graph writes on the interactive editing path; **rejected**. Uncapped
async DuckDB during interactive use causes RAM contention; **rejected**. The semaphore yields to
interactive generation and the DuckDB memory is capped (`memory_limit='4GB'`), so write-back does not
contend uncontrolled with serving. **Why outcome weight is one transparent signal:** opaque
outcome-weighting as the sole ranker entrenches established investigators (the **incumbency-bias
trap**); keeping it transparent and one-of-three avoids it.

**See** `12-collaboration-loop-and-writeback-lld.md`, `loop-engine` package, `D12`. The async-DuckDB
contention is a named open_risk.

### Monotonic applier

**Definition.** The idempotent ingest/write-back mechanism that compares a record's
`projection_version` against the live `revocation_epoch` and **rejects a stale, lower-version
projection**. It guarantees a re-ingest (including the write-back edge) **cannot resurrect a
revoked or down-classified record**.

**See** `09-ingestion-and-identity-resolution-lld.md`,
`12-collaboration-loop-and-writeback-lld.md`, `05-kernel-contracts.md §7` (`projection_version`),
`D12`.

### ExpertiseFingerprint

**Definition.** A researcher's **time-evolving expertise vector**: the SPECTER2-space centroid
(precomputed at ingest) + topic/concept weights + the **outcome-weighted signal** the write-back
edge mutates. It is the **living graph signal** that the loop updates on every win. Key fields:
`subject_id`, `concept_weights[]`, `specter2_centroid`, `outcome_weight_by_concept`,
`last_enriched_at`.

**See** `13-data-model-and-schemas.md`, `_design-brief.json → domain_entities`, `D12`,
[SPECTER2](#specter2-ingest-only-then-unloaded).

### CollaborationEdge (`CO_PI_WITH` / `CO_AUTHORED`)

**Definition.** A **weighted, time-decayed** collaboration edge built from co-authorship **AND**
co-funding, plus **in-platform won-proposal `CO_PI_WITH`** edges added by the write-back. It powers
the **connectivity axis** of team assembly. Key fields: `src_subject`, `dst_subject`, `edge_type`,
`weight`, `time_decay`, `source_proposal_id` (if in-platform), `award_number` (if funded).

**See** `13-data-model-and-schemas.md`, `_design-brief.json → domain_entities`, `D12`.

### Two-axis team ranking (coverage + connectivity)

**Definition.** `mod-discovery` ranks candidate team members on **two axes** over the **public-tier**
expertise graph: (1) **expertise COVERAGE** of the RFP's required concept areas (complementary /
gap-filling, shown as a **coverage matrix with gaps**), and (2) graph **CONNECTIVITY** / prior
co-authorship + co-funding distance — with the outcome-weighted overlay and a per-candidate "why".
**The PI always curates** (the algorithm alone produces worse teams). `mod-discovery` touches **no**
confidential data.

**See** `10-feature-modules-lld.md`, `_design-brief.json → collaboration_loop_design` (Stage 2),
`D1`.

### `LoopEvent` / loop-event stream

**Definition.** A **NON-security** product-analytics event on a **dedicated stream**, kept
**separate** from the hash-chained security audit. Event types include `pursuit_created`,
`opportunity_matched`, `team_shortlisted`, `invite_sent`, `collaborator_joined` (cross-tenant),
`first_co_edit`, `suggestion_resolved`, `proposal_submitted`, `outcome_recorded`, `graph_enriched`.

**Activation north-star** = `collaborator_joined` where `joining_tenant != workspace_owner_tenant`
(a cross-GROUP collaborative act). **Loop health** = the funnel `match → team → edit → submit → win`
+ time-to-team + cross-group edit ratio.

**Why a separate stream.** Mixing product analytics into the hash-chained security audit would
pollute the tamper-evident chain. A loop event must **not** write to the security stream (P0.3
acceptance).

**See** `12-collaboration-loop-and-writeback-lld.md`, `mod-audit` package,
`_design-brief.json → collaboration_loop_design`, `D12`.

---

## 8. Identity & external data-source terms

> All external sources are integrated as **periodic enrichment imports** (snapshot / file readers),
> **never** as metered live APIs on the hot path (D14). Every ingested record carries a
> `source` enum value and a provenance + license tag. The funding-opportunity source value is the
> exact string **`grants_gov`** (snake_case) — not `grants.gov`, not `GrantsGov`.

### ORCID

**Definition.** Open Researcher and Contributor ID — the **canonical researcher identifier** a
`Researcher` is anchored to (a `0000-0000-0000-0000`-form iD). It is the node identity in the
expertise graph and aligns the platform to mandatory federal rails. Source enum: `orcid` (ingested
**anchors-only** from the large summaries file).

**See** `09-ingestion-and-identity-resolution-lld.md`, `13-data-model-and-schemas.md §2`, `D14`.

### SciENcv

**Definition.** The NIH/NSF **Common Forms** biosketch interchange. A researcher row carries an
opaque `sciencv_profile_ref` so assembled teams are **submission-ready** (SciENcv Common Forms are
NIH-required from May 2026). It is a federal-rails alignment, not a data source to crawl.

**See** `13-data-model-and-schemas.md §2`, `_design-brief.json → product_summary`, `D14`.

### ROR

**Definition.** Research Organization Registry — the canonical **institution identifier**. Used to
**scope public ingestion** ("ingest the works/awards for this chosen ROR institution set") so the
corpus is **depth-within-tenant**, not a full-world ingest. Source enum: `ror` (ingested in full —
it is small).

**Why ROR-scoped ingest, chosen over full-world.** A single HDD-bound box cannot mirror
cloud-scale corpora; scoping by ROR (and/or topic) via DuckDB keeps the working set feasible and the
moat focused on depth.

**See** `09-ingestion-and-identity-resolution-lld.md`, `CONVENTIONS-single-box.md §8.5`, `D14`.

### OpenAlex

**Definition.** The free scholarly metadata corpus (works/authors/venues/topics). The largest cold
source (~330GB gz, **scoped down** by ROR/topic via DuckDB). Source enum: `openalex`.

**Cadence + delta (load-bearing, D14).** The **free** public snapshot is **QUARTERLY** (monthly
snapshots + daily changefiles require a **paid** plan). Ingestion is **DELTA, partitioned by
`updated_date`** — download only new `updated_date` partitions, **never** a full re-ingest. The
delta-by-`updated_date` instruction holds **regardless** of cadence, so switching cadence is a
schedule change, not a code change.

> **Verification flag (a human should confirm before launch):** sources disagree on the current
> *free* cadence; this corpus **follows the brief (quarterly free)**. Build delta-by-`updated_date`
> either way; if monthly freshness is required, budget the paid tier explicitly.

**See** `09-ingestion-and-identity-resolution-lld.md`, `CONVENTIONS-single-box.md §8.3`, `D14`.

### Crossref

**Definition.** A scholarly metadata source (DOIs, bibliographic records), ~200GB via Academic
Torrents. Source enum: `crossref`. Public-tier, classify-gated like all corpus sources.

**See** `09-ingestion-and-identity-resolution-lld.md`, `D14`.

### Grants.gov (`grants_gov`)

**Definition.** The source of **Grant Opportunities** — open funding calls (a daily XML extract).
This is the **top-of-loop trigger** (loop Stage 1). Source enum value is the exact string
**`grants_gov`** (D14). Public-tier.

**Why opportunities are the trigger, chosen over discovery-first.** A concrete funding need beats
aimless expert browsing and avoids the discovery-first cold-start problem.

**See** `13-data-model-and-schemas.md §6` (`tex.opportunity`), `CONVENTIONS-single-box.md §8.1`,
`D1`, `D14`.

### RePORTER (NIH RePORTER) & NSF Awards

**Definition.** Sources of **Grant Awards** — historical funded projects that feed PI track-record
and **co-funding collaboration edges**. Source enums: `nih_reporter`, `nsf_awards`. Public-tier.

**Why opportunities and awards are modeled distinctly (D14).** They have different loop semantics:
**Opportunities drive the win-loop** (Stage 1 trigger); **Awards feed expertise + co-funding edges**
(the connectivity axis). Do not collapse them into one table.

**See** `13-data-model-and-schemas.md §7` (`tex.award`), `D14`.

### Provenance / license gate

**Definition.** Every ingested record carries a **provenance + license** tag. The commercial-use
gate is **fail-closed**: ingest only the PMC **"Commercial Use Allowed"** subset; store the ODC-BY
attribution string with derived data. Classification + RLS + the separate confidential surface keep
confidential drafts physically separate from the public CC0 corpus.

**See** `09-ingestion-and-identity-resolution-lld.md`, `CONVENTIONS-single-box.md §8.4`, `D14`.

---

## 9. Storage, memory, and build-process terms

### The three memory regimes (SERVE / INGEST-WINDOW / WRITEBACK-WINDOW)

**Definition.** The box runs in **exactly ONE** of three **mutually-exclusive** memory regimes at a
time (the 64GB LPDDR5 is **unified** — CPU and GPU share one pool, the hard ceiling for **all**
processes combined):

| Regime | When | Approx total | Notes |
|---|---|---|---|
| **SERVE** | interactive steady state | **~49GB** (saver ~46GB) | 7 OS + 25 generator + 2.5 embedder + 2.5 reranker + 0 SPECTER2 + 7 Postgres buffers + 5 backends. Confidential drafting adds **NO** resident model copy. |
| **INGEST-WINDOW** | bulk DuckDB load, **serving PAUSED** | **~25GB** (generator evicted) / ~42GB (idle-resident) | DuckDB `memory_limit='8GB'` + SPECTER2 batch (~1.5GB, loaded ONLY here) + embedder + reduced Postgres `shared_buffers`. |
| **WRITEBACK-WINDOW** | async loop enrichment, **semaphore-gated** | **~54.5GB** | SERVE baseline + writeback DuckDB `memory_limit='4GB'` + SPECTER2 reload (~1.5GB). |

**Why three regimes, chosen over one "headroom" figure.** The prior single headroom figure was
**triple-counted** (interactive burst + DuckDB spill + a now-eliminated second vLLM). Three
mutually-exclusive regimes make each budget **provably fit**. Contention rules: exactly one regime at
a time; ingestion runs serving-paused; serialize LLM generation vs heavy embedding batches; gate
generation so the CRDT editor stays responsive; confidential KV isolation = prefix-caching-off +
serialization on the one shared generator, **no MIG**.

**See** `03-architecture-and-orin-constraints.md`, `CONVENTIONS-single-box.md §5.1`,
`_design-brief.json → memory_budget`, `D13`, `D10`.

### Tiered storage (HDD cold / NVMe hot / RAM transient)

**Definition.** Three storage tiers with strict roles (D13):
- **HDD** = **cold archive ONLY** — raw CC0 gzip snapshots, read **SEQUENTIALLY** at ingest.
- **NVMe** (PCIe Gen4 M.2, **effectively mandatory in the BOM**) = the **hot tier** — Postgres data
  dir + WAL, live shared/confidential indexes, Parquet working sets.
- **RAM** = transient + model weights + index hot pages.

**The load-bearing guardrail:** the live HNSW index and the **authz/RLS hot path** must **NEVER**
incur HDD random seeks. HNSW is pure random I/O; serving it off HDD yields 10s+ queries, and
per-request authz off HDD would dominate latency.

**Why, chosen over all-on-HDD / all-on-NVMe / in-RAM-only.** All-on-HDD: random I/O kills query +
authz latency. All-on-NVMe: raw corpora too large/expensive. In-RAM-only: competes with the GPU for
the unified 64GB. DuckDB out-of-core reads HDD **sequentially** at ingest and writes Parquet to NVMe.

**See** `03-architecture-and-orin-constraints.md`, `CONVENTIONS-single-box.md §5.1`,
`_design-brief.json → memory_budget`, `D13`. NVMe absence is a named open_risk.

### Modular monolith

**Definition.** The architecture: **one** FastAPI application + **one** Postgres 16 + a small fixed
set of model-serving processes, all co-resident on **one** box, with **in-process** module
boundaries and an in-process event bus. **No Kubernetes, no microservices, no second deployable, no
second region, no second box.** Code splits into `packages/` (importable libraries) and `services/`
(deployables).

**Why, chosen over microservices/K8s.** The deploy target is literally one box; microservices / K8s
/ multi-region waste the scarce 64GB. Clean kernel Protocol seams make *much* of a future federation
layer a transport addition (but honestly **not everything** — see the federation note).

**See** `CONVENTIONS-single-box.md §2`, `03-architecture-and-orin-constraints.md`, `D2`. K8s /
microservices are **FORBIDDEN**.

### The kernel (`contracts`)

**Definition.** The near-frozen `tigerexchange_contracts` package: the **single shared vocabulary**
of types, enums, pure functions, and `I*` Protocols that **every** package imports and that itself
imports **nothing feature-side**. It contains the Tier lattice, `TenantContext`, `Entitlement`,
`Capability`, `ClassificationResult`, `Decision`, `PublishableProjection`, the PEP request/response
types, `AuditEvent`, the value objects, and all `I*` Protocols.

**Kernel fitness function (all three CI-enforced):** (1) zero feature dependencies (stdlib +
`pydantic` + `typing` only); (2) no persistent state, no I/O; (3) referenced by ≥ 2 packages. A
symbol that does I/O, holds state, or names a feature does **not** belong in the kernel — it belongs
behind a Protocol.

**See** `05-kernel-contracts.md` (the whole doc), `CONVENTIONS-single-box.md §3–4`.

### `I*` Protocol (seam)

**Definition.** A `typing.Protocol` interface (structural typing, `@runtime_checkable`) that defines
a capability's *shape* without coupling implementations to the kernel by inheritance. The full set:
`IPolicyEnforcement`, `IEntitlementEvaluator`, `IClassifier`, `IRetrievalStrategy`, `IVectorStore`,
`ILexicalIndex`, `IGraph`, `IModelRouter`, `IModelProvider`, `IKms`, `IGrantStore`, `IAuditSink`,
plus the **deferred federation stubs** `IRevocationAuthority` and `IExchangeFeed`.

**Why Protocols over ABCs.** Protocols give structural typing with **zero import coupling** — an
implementation matches the shape without importing/subclassing a kernel ABC, so dependency arrows all
point one way (everyone → kernel) and a future implementation can be swapped without touching the
kernel.

**See** `05-kernel-contracts.md §10`, `D2` (deferred stubs).

### Walking skeleton

**Definition.** The build philosophy: **prove the end-to-end loop with the full security spine on the
simplest possible substrate first**, then add breadth. The P0 walking skeleton =
**one tenant pair**, **real-time editing only**, **binary allow/quarantine** classification,
**drop-encrypted-tablespace crypto-shred**, **single embedding space**, **pgvector HNSW only**.
Deferred to P1: suggesting-mode, anchored comments, HippoRAG2, probabilistic identity resolution,
the OP-TEE hardware anchor, RaBitQ >RAM index.

**Why, chosen over building everything at once.** The full P0 surface (security kernel + retrieval +
router + ingestion + CRDT + write-back) would overwhelm a mid-size local builder; the walking
skeleton proves the loop and the security path on the smallest substrate, then breadth is additive.

**See** `_design-brief.json → product_summary` + `open_risks`, `00-START-HERE.md`,
`14-build-runbook-and-phases.md`.

### Create-if-absent

**Definition.** The pinned rule that all collection / index / tablespace bring-up code is
**idempotent**: create only if it does not already exist, **never** `recreate_collection`, never
drop-on-create, never wipe-and-rebuild as a startup side effect. The one allowed drop is the
**crypto-shred drop-and-rebuild** of a per-tenant confidential tablespace after its DEK is destroyed
(an explicit, audited erasure).

**Why.** An old retrieval sub-plan used Qdrant's destructive `recreate_collection`, which wipes data
on every run. **`recreate_collection` / drop-on-create is FORBIDDEN.**

**See** `CONVENTIONS-single-box.md §9`, `05-kernel-contracts.md §10.2`
(`create_collection_if_absent`).

### Federation (designed, not built) — and the two known rewrites

**Definition.** Cross-BOX federation is **DESIGNED behind clean kernel Protocol seams but NOT BUILT**
in Phase-0 (D2). Be honest about which seams carry forward:

| Seam / mechanism | Federation status |
|---|---|
| `PublishableProjection.discoverability_scope` | **Carry-forward-clean** |
| `IExchangeFeed` | **Carry-forward-clean** (a transport addition later) |
| Owner-authoritative re-derivation | **Carry-forward-clean** |
| **Encrypted-tablespace crypto-shred (D7)** | **KNOWN FEDERATION-BOUNDARY REWRITE** — node-local; cannot crypto-shred another node's tablespace |
| **Recursive-CTE ReBAC `Check()` (D4)** | **KNOWN FEDERATION-BOUNDARY REWRITE** — resolves LOCAL tables only |

**Why honest.** Do **not** claim "everything is just a transport addition" — two single-box
mechanisms are semantically node-local and would be real rewrites.

**See** `15-future-federation-interfaces.md`, `CONVENTIONS-single-box.md §12`, `D2`.

---

## 10. Quick-reference tables

### 10.1 The crypto-shred split (memorize this)

| Confidential data | Searchable? | Mechanism | Crypto-shred |
|---|---|---|---|
| Per-tenant vector / BM25 / graph indexes | **Yes** | Plaintext-at-rest **inside an encrypted tablespace / LUKS volume** | **Destroy the per-tenant DEK** that unlocks the volume, then drop-and-rebuild (PRIMARY) |
| CRDT draft snapshots, autosave, version history, eval traces, cache values | **No** | **AES-256-GCM** under the per-tenant DEK | `destroy_kek()` makes the ciphertext undecryptable |

**Never** AES-GCM the vectors/BM25/graph (unsearchable). **Never** use the encrypted-tablespace for
the only protection of blobs that also need ALE. Both paths are covered by the same `destroy_kek()`
and the same post-shred zero-decryptable-hits gate.

### 10.2 The PEP decision order (memorize this)

| Step | Check | Engine | Fail-closed behavior |
|---|---|---|---|
| 1 | entitlement / edition gate | in-Python | error/abstain → DENY |
| 2 | capability gate | in-Python | required capability absent → DENY |
| 3 | ABAC tier check | in-Python lattice (MAX-rule, `permits_tier`) | tier not permitted → DENY |
| 4 | ReBAC relation Check | Postgres recursive CTE (LOCAL-only) | relation absent → DENY |
| 5 | durable tombstone read | Postgres durable log | tombstoned → **authoritative** DENY |
| 6 | short-TTL lease | narrow-only positive cache | (cache is positive-only; never widens) |

### 10.3 What is FORBIDDEN (and what replaces it)

| Forbidden | Replaced by | Decision |
|---|---|---|
| A second resident 30B copy | ONE shared generator + prefix-caching-off + serialization | D10 |
| AES-GCM on vectors / BM25 / graph | Encrypted-tablespace + DEK-destroy | D7 |
| OP-TEE / EKB as a build deliverable | fTPM (tpm2-tools) or passphrase-KDF (P0 default) | D7 |
| GPU MIG | Prefix-caching-off + serialization on one generator | D10 |
| OPA Go daemon / Cedar | In-Python ABAC | D4 |
| SpiceDB / OpenFGA cluster | Postgres recursive-CTE `Check()` | D4 |
| CloudHSM / cloud-KMS | In-process `LocalKms` + fTPM/passphrase anchor | D7 |
| Qdrant / OpenSearch as P0 stores | Single Postgres (pgvector + native BM25 + RRF + edge-graph) | D8 |
| Apache AGE | Edge table + recursive CTE | D8 |
| Kubernetes / microservices | Modular monolith (one FastAPI app) | D2 |
| Built cross-box federation | Designed-behind-seams, not built | D2 |
| `recreate_collection` / drop-on-create | Create-if-absent | conventions §9 |
| Python 3.12 | Python 3.11 | conventions §7 |
| A second resident SPECTER2 at serve | SPECTER2 ingest-only, then unloaded | D8 |
| Ollama as the production reranker / LLM | vLLM score process or ST CrossEncoder | D8/D9 |
| GTM / COGS / pricing model | (dropped entirely) | D1 |
| Phantom decision labels (`D-AI`, `D15`, …) | `D1`..`D14` only | conventions §13 |

### 10.4 Decision-ID → primary glossary terms

| ID | Decision (summary) | Terms it owns |
|---|---|---|
| D1 | Research Collaboration Loop Engine; no economics | collaboration loop, Pursuit, two-axis ranking |
| D2 | Single-box monolith; federation designed-not-built | modular monolith, federation, deferred stubs |
| D3 | Single PEP + broker chokepoint | PEP, broker, PublishableProjection |
| D4 | Fixed fail-closed PEP order; ABAC in-Python, ReBAC Postgres-CTE | PEP order, ABAC, ReBAC, MAX-rule, fail-closed |
| D5 | Per-tenant isolation = FORCE-RLS + SET LOCAL + leading index | Tenant, RLS, SET LOCAL, TenantContext |
| D6 | Classify-gates-index (shared) + per-tenant confidential surface | classify-gates-index, confidential retrieval surface, dual-source grounding |
| D7 | Crypto-shred split; fTPM/passphrase anchor | KEK, DEK, crypto-shred, encrypted tablespace, AES-GCM blob, LocalKms |
| D8 | Single-Postgres hybrid retrieval; SPECTER2 ingest-only | two-stage retrieval, RRF, BM25, pgvector HNSW, rerank, HippoRAG2, embedder, SPECTER2 |
| D9 | vLLM as 3 processes (or ST saver); 30B in one process | generator, embedder, reranker, IModelRouter |
| D10 | Confidential KV isolation, one shared generator, no MIG/second copy | confidential KV isolation, generator |
| D11 | mod-workspace first-class; real-time edit only at P0 | CRDT / real-time mode, Team/TeamMember, SharingGrant, Proposal |
| D12 | Compounding write-back edge, memory-gated async | write-back edge, monotonic applier, ExpertiseFingerprint, CollaborationEdge, LoopEvent |
| D13 | HDD-cold / NVMe-hot / RAM-transient; three memory regimes | three memory regimes, tiered storage |
| D14 | Depth-within-tenant corpus; OpenAlex quarterly + delta | ORCID, SciENcv, ROR, OpenAlex, Crossref, Grants.gov, RePORTER, NSF, provenance/license gate |

---

*End of `02-glossary-and-domain-primer.md`. This file defines terms; for exact types see
`05-kernel-contracts.md`, for exact DDL see `13-data-model-and-schemas.md`, for the authoritative
pins see `CONVENTIONS-single-box.md`. If a definition here drifts from those, those win.*
