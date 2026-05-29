# Plan v6 (decision-locked rebuild)

> Bounded adversarial verify-1: **0 critical / 11 high** in-scope.

---

I have both grounding documents fully. The prior `final-plan.md` is already deep and resolves most clusters, but it is anchored on the **confidentiality-RAG appliance** wedge (Phase-0 = `mod-lit-intelligence`), not the **locked D1 grant-intelligence wedge**. The locked decisions require a substantial re-anchor: grant intelligence as the primary wedge, anchor consortium (not NDA lab) as the day-one buyer, the other three wedges as the *decomposition* of the grant workflow, and the ACV/COGS and phasing reframed accordingly. I'll write the full re-anchored plan now.

I have everything needed. Producing the deliverable directly as my final response.

---

# TigerExchange — Grant Intelligence as a Federated Cross-Institution Team-Assembly & Secure-Proposal-Collaboration Platform
## Architecture & Business Plan v6 (Re-Anchored on Locked Decisions D1–D7)

*Self-contained. Re-anchored on the grant-intelligence wedge (D1) sold into one existing federally-funded multi-site center (D3), with confidentiality enforced through a single Policy Enforcement Point + data-access broker chokepoint (D4), the owning node as the sole local fail-closed revocation authority (D5), confidential content never entering the shared index (D6), and institutional ACV ≥ 2–3× per-tenant COGS as the revenue anchor (D7). The architecture is modular and constant across phases; build order, isolation posture, and which decomposed wedge is lit are the levers.*

---

## 1. Vision & Positioning

**Product.** A federated grant-intelligence platform for multi-institution research. The wedge is **cross-institution team assembly + secure proposal co-authoring** for funded, recurring grant cycles. Each institution runs a strongly-isolated node holding its public, private, and confidential data. A thin shared **Exchange** enables revocable, classification-enforced cross-institution discovery and collaboration **without centralizing confidential data**.

**The moat is NOT the grant database** (Grants.gov, RePORTER, NSF awards are commodity CC0/public feeds; Pivot-RP, GrantForward, Instrumentl, and the AI fast-follow Atom Grants/GrantsAI already index them). The moat is three compounding assets the database vendors structurally cannot build:

1. **Cross-institution expertise graph** — who can co-PI what, resolved across institutional boundaries, accumulating entity-resolution + collaboration-history trust artifacts per dyad.
2. **Confidential proposal workspace** — pre-submission proposals are the *most* confidential artifacts in the academy (unfunded ideas, budgets, preliminary data); no public-data grant tool can host them, and no enterprise secure-RAG tool (Glean/NotebookLM) federates them across institutional trust boundaries.
3. **Federation network** — revocable cross-institution sharing grants + audit history + tuned eval gold-sets that grow super-linearly with connected nodes and active grant cycles.

**The white space (precise, unoccupied intersection):**

| Category | Examples | Owns | Structural blind spot |
|---|---|---|---|
| Grant DB / discovery | Pivot-RP, GrantForward, Instrumentl, **Atom Grants/GrantsAI** | Funding-opportunity index + (Atom) AI co-PI match | **Single-tenant, public-data-only**; no confidential proposal hosting; no federation; no institutional trust fabric |
| Research-admin / CRIS | Cayuse, Kuali, Pure, Symplectic | Grant *administration* + faculty/publication data inside one research office | Centralized SaaS; **confidential cross-institution sharing cannibalizes their data-monetization**; no AI-native team assembly |
| Enterprise secure-RAG | Glean, NotebookLM Ent., Copilot, Azure-OpenAI-on-your-data | Single-tenant grounded Q&A over internal docs | No federation, no cross-institution trust fabric, no scholarly/grant graph |
| Confidential federation | Decentriq, BeeKeeperAI, cloud clean rooms | Confidential multi-party compute | Generic clean rooms; no grant workflow, no scholarly graph, no PI-facing product |
| Academic LOD federation | VIVO CTSAsearch / Direct2Experts (64 inst.) | Public-tier cross-institution expert search | Public-only; no confidentiality tier, no grounded AI, no grant workflow |

**Nobody assembles cross-institution grant teams over a confidential, revocably-shared proposal workspace with classification-routed AI.** That is the wedge.

**Defensibility thesis (raced, not resting on incumbent inaction).** Two compounding *measurable* switching-cost mechanisms + a certification lead:

1. **Data-gravity from trust artifacts** — sharing grants, audit chains, per-dyad entity-resolution decisions, accumulated grant histories, per-tenant tuned gold-sets. **Pulled forward to N=2:** even one dyad inside the anchor consortium accrues grant history + audit chain + tuned gold-sets a replacement cannot reproduce.
2. **Network effect** — team-assembly quality and discovery value grow super-linearly with connected nodes and active grant cycles.
3. **Certification depth** — FERPA/GDPR/export-control readiness incumbents acquire over 4–6 quarters.

**Incumbent time-to-replicate.** Atom Grants can bolt on a thin "private" tier in ~1 quarter; the *federated confidential trust fabric* (cross-tenant authz, revocation correctness, owner-side re-derivation, audit anchoring) is a 4–6 quarter security program even for a well-resourced team — and the CRIS incumbents must do it without breaking their centralized data-monetization model. **Race condition (R17):** reach **defensible N** before that window closes (defined in §17, reachability confirmed in §18). Per Triage C2/C23 (item 23), if the race window cannot be met on the modeled ramp, the stated moat **falls back to the network-effect lock-in** (switching cost compounding with N nodes × accumulated sharing grants), not the race.

**Why now.** (a) Multi-site federally-funded research (NIH U54/U01, NSF AI Institutes) is structurally cross-institutional, runs recurring funded grant cycles, and is underserved by single-tenant tools — this is exactly the anchor (D3). (b) Open scholarly + grant corpora (OpenAlex, Crossref, ROR, ORCID-dump, SPECTER2; Grants.gov, RePORTER, NSF awards) are redistributable at scale. (c) Open-weight models on commodity GPUs make in-boundary confidential inference economical. (d) Export-control + data-sovereignty regimes make "confidential data stays in-boundary" a hard procurement requirement.

---

## 2. Users, Buyers & Packaging

### 2.1 Personas
- **PI / co-PI** — finds collaborators, assembles a cross-institution team, co-authors the proposal. **Budget authority ≈ $0; champion + PLG top-of-funnel, does not sign.**
- **Center / consortium RD office (anchor buyer, D1)** — owns the recurring multi-site grant strategy, the master DUA, and the budget. **The institutional, mid-ACV economic buyer.**
- **Sponsored-programs / grants administrator** — pre-award compliance, budget, submission; co-champion inside the RD office.
- **Library / scholarly comms** — corpus, public profiles, OA strategy; frequent co-buyer.
- **IT / CISO / privacy / export-control officer** — security/compliance gatekeeper; can veto.
- **Consortium / alliance director** — multi-institution governance buyer at scale.

### 2.2 The buyers, honestly mapped (per D1/D7)

| Motion | Budget owner | Deal size (ACV) | Cycle | Security depth | Revenue phase |
|---|---|---|---|---|---|
| **ANCHOR: existing multi-site center RD office** (NIH U54/U01, NSF AI Institute) | Center admin / RD office | **$120–250k/yr** (≥2–3× per-tenant COGS, §16) | 4–9 mo (existing-relationship + funded-need shortens) | High (rides existing DUA) | **Phase 0–1** |
| Top-down institutional (research office/library/IT) | VP Research / Library / CIO | $150–600k/yr | 6–12 mo | High | Phase 2 |
| Consortia / alliances | Consortium director | $300k–1.5M/yr | 9–18 mo | High + governance | Phase 2–3 |
| Campus-wide | CIO / Provost | enterprise license | 9–18 mo | High + SAML/eduGAIN | Phase 2–3 |
| **PLG top-of-funnel (individual PIs)** | Individual | **$179/mo** (loss-leader) | self-serve | Low (public + own-materials only) | Phase 1+ (acquisition channel) |

**Locked-requirement reconciliation (D7, explicit).** The **$179/mo individual tier is explicitly top-of-funnel / loss-leader**, not the margin driver. The **revenue anchor is the institutional/center sale priced so ACV ≥ 2–3× per-tenant COGS.** "Sellable to PLG" is satisfied by a PLG land-and-expand surface whose purpose is to seed champions inside target consortia. If a stakeholder requires standalone PLG profitability, that is a *new* requirement surfaced now (§19 Q21), not in Phase 3.

### 2.3 Editions = entitlement config, not forks
One platform; editions resolve through a first-class **Entitlement/Edition** module (§5) mapping a tenant to a capability set, evaluated centrally **at the PEP**. Modules consume capabilities as a contract and **physically cannot** enable a tier they are not entitled to.

| Edition | Capabilities | Target |
|---|---|---|
| **Consortium-Anchor** | confidential proposal workspace, HYOK, in-boundary inference, **exchange participation + cross-institution grants + team assembly**, N≥2 cells | anchor center (D3) |
| **Institutional** | + private tier, library RBAC, OIDC/SAML, full discovery | research office |
| **Campus** | + campus-wide SSO (eduGAIN), seats at scale | campus |
| **PLG (individual, $179/mo)** | **public + own-materials ONLY; confidential/exchange hard-OFF** | individual PIs |

**Contract test (CI-enforced, Triage item 17/§2.3):** *"A PLG-edition tenant cannot construct a confidential-tier or exchange-participation request."* Entitlements evaluate at the PEP, not per-module — an edition can never open a tier ad hoc.

### 2.4 Value metric & metering (D7-aligned; designed in day one)
Metered axes chosen to **not tax the network effect**: **seats** (institutional/campus), **confidential proposal workspaces** (anchor/consortium), **node/data-plane** (institutional/managed), **grant-team assemblies** (consortium add-on). We deliberately **do NOT meter per cross-institution sharing grant** — that would tax the exact bootstrapping behavior. **Non-confidential workloads run on multi-tenant pooled infra; dedicated isolation (and its cost) is billed only on the confidential tier (D7).** The metering module is pluggable (§5).

### 2.5 GTM sequencing
Phase 0: anchor-center BD + two kill-gates + single-cell MVP with a **federation-flavored public-tier differentiator** (Triage item 20). Phase 1: light up the federation seam inside the anchor center's existing DUA (D3), then one revocable confidential grant. Phase 2: institutional + consortium broadening. Phase 3: PLG funnel + full grant-monetization across consortia.

---

## 3. Feature Catalog & MVP Sequencing

### 3.1 The grant wedge IS the product; the other three wedges are its decomposition (D2)

The locked decision D2 reframes the four pillars not as separate products but as the **natural decomposition of one grant workflow**:

```mermaid
flowchart LR
  G["GRANT WORKFLOW (the wedge, D1)"]
  G --> A["Team assembly\n= cross-institution EXPERT DISCOVERY\n(mod-discovery)"]
  G --> B["Proposal grounding\n= LITERATURE INTELLIGENCE\n(mod-lit-intelligence)"]
  G --> C["Confidential cross-institution co-editing\n= SECURE WORKSPACES\n(mod-workspace)"]
  G --> D["Opportunity match + budget/compliance\n= FUNDING INTELLIGENCE\n(mod-funding)"]
```

| Decomposed wedge | Module | Consumes (interfaces) | Phase |
|---|---|---|---|
| **Team assembly = expert discovery** | `mod-discovery` | `IRetrievalStrategy`, `ICollaborationGraph`, `IExpertiseFingerprint`, `IExchangeFeed` | **0 (public-tier)**, 1 (cross-inst.), 2 (PSI overlap) |
| **Proposal grounding = literature intel** | `mod-lit-intelligence` | `IRetrievalStrategy`, `IModelRouter`, `IPolicyEnforcement` | **0 (own-corpus grounded drafting)** |
| **Confidential co-editing = secure workspaces** | `mod-workspace` | `IGrantStore`, `IRevocationAuthority`, `IPolicyEnforcement`, `IAuditSink` | 1 (single grant), 2 (full) |
| **Opportunity match + team assembly = funding intel** | `mod-funding` | `IExpertiseFingerprint`, `ICollaborationGraph`, `IExchangeFeed`, grant feeds | 1 (opportunity match), 3 (full assembly + budget) |

### 3.2 The MVP wedge + anchor buyer
**MVP wedge (Phase 0):** for the anchor center's PIs — **(a)** grounded proposal drafting + semantic search over the center's own documents + public scholarly corpus (`mod-lit-intelligence`, classification-enforced in-boundary inference, HYOK-at-rest), **plus (b)** the federation-flavored differentiator (Triage item 20): **cross-institution PUBLIC-tier expert discovery over OpenAlex** (`mod-discovery`, zero confidentiality machinery) **plus (c)** grant-opportunity match (`mod-funding` lite) over Grants.gov/RePORTER/NSF. This makes first-dollar a *grant-flavored, federation-flavored* product, not commodity secure-RAG.

**Anchor buyer (D3):** **ONE existing federally-funded multi-site center** (NIH U54/U01, NSF AI Institute, or established consortium) that already shares confidential data under an existing DUA → day-one N≥2 + legal basis + recurring funded grant need.

### 3.3 Two independent kill-gates (Triage C1/C22; D3)

Phase-0 carries one federation-flavored differentiator so first revenue is not pure commodity (item 20), but we still split validation into **two independent demand gates with independent pivots** — *not* a build-order continuation:

- **Gate A (Week 1) — anchor-grant-wedge demand:** the anchor center's RD office gives a **written price indication with ACV ≥ 2–3× modeled per-tenant COGS (≥$120k/yr, §16)** against a concrete grant-program budget line; funds a paid sandbox pilot. *Fail → pivot the wedge before engineering.*
- **Gate B (Week 1, SAME interviews) — federation/cold-start basis:** confirm in writing **(i)** an existing confidential cross-institution sharing relationship + **its legal vehicle (DUA)** in force, **(ii)** N≥2 sites already collaborating, **(iii)** a recurring funded grant need (D3's three conditions). *Fail → the anchor isn't real; do not commit to the federation build — Phase 1 becomes an independent kill-gate, not an automatic continuation.*

Passing A while failing B means we have a sellable single-cell grant-assistant and an unproven federation. That is a decision point, not a green light.

### 3.4 Cold-start: anchor on a pre-existing legal vehicle (D3)
Federated platforms die in the dyad cold-start gap. **We do not create a new sharing relationship.** The first dyad **digitizes the anchor center's existing DUA.** **Hard Phase-1 entry gate (ranked above the consortium-BD hire):** *"Anchor center selected; its existing DUA + N≥2 sites + recurring funded grant need confirmed in writing."* Anchor-center **selection criteria are a gate, not aspiration:** (1) ≥2 sites already sharing confidential data, (2) a master DUA/consortium agreement in force, (3) a recurring (annual/biennial) funded grant cycle, (4) a named RD/center-admin budget owner.

### 3.5 Deferred & why
- **F4 full grant team assembly + budget intelligence** → Phase 3 (needs mature graph + N≥several); **opportunity-match lite ships Phase 1.**
- **PSI collaborator-overlap** → Phase 2, but **usability spiked in Phase 1**.
- **Multi-agent retrieval** → Phase 3 (cost/safety).
- **TEE-at-use, sovereign hosting, customer self-host** → Phase 2+ (separately funded line, §13).

---

## 4. System Architecture

### 4.1 Control-plane / data-plane split & federation topology

```mermaid
flowchart TB
  subgraph CP["CONTROL PLANE (regional-pinned: US / EU instances)"]
    EX["Exchange: federated discovery broker + GRANT registry index + team-assembly broker"]
    RA["Revocation Authority (lease-issuing; owning node is sole local authority — D5)"]
    ENT["Entitlement/Edition service"]
    IDP["Identity broker (Keycloak + CILogon/eduGAIN)"]
    TLR["TierLattice version registry (additive, fail-closed)"]
    CIDX["Managed central index + materialized PUBLIC-tier graph (sharded) + public grant feeds"]
    TXP["Cross-tenant transparency log (audit anchor)"]
  end

  subgraph CELL_A["DATA PLANE — Center Site A cell (isolated tenant)"]
    PEPa["Egress PEP + Data-access broker (SINGLE chokepoint — D4)"]
    STOREa["Per-tenant stores: Postgres / vector / graph / lexical"]
    GRANTa["Authoritative GrantStore (A) — sole local revocation authority (D5)"]
    AUTHa["Cell-local SpiceDB replica + lease cache"]
    INFa["In-boundary inference (vLLM) + KMS/HYOK"]
    AUDa["Hash-chained audit (per-stream) + checkpointer"]
  end

  subgraph CELL_B["DATA PLANE — Center Site B cell"]
    PEPb["Egress PEP + broker"]
    STOREb["Per-tenant stores"]
    GRANTb["Authoritative GrantStore (B)"]
    AUTHb["SpiceDB replica + lease cache"]
  end

  subgraph POOL["MULTI-TENANT POOLED PLANE (non-confidential only — D7)"]
    PLGc["PLG + public-discovery shared cells (pooled GPU/index)"]
  end

  IDP --> PEPa & PEPb & PLGc
  ENT --> PEPa & PEPb & PLGc
  TLR --> PEPa & PEPb
  PEPa -- "PUBLIC/SHARED projections only (CDC)" --> CIDX
  PEPb -- "PUBLIC/SHARED projections only (CDC)" --> CIDX
  EX <-- "discovery (no confidential payload)" --> PEPa & PEPb
  PEPa -- "brokered drill-down (deadline-propagated)" --> EX
  EX -- "owner-side re-derivation (D5)" --> PEPb
  RA -- "fenced leases (LOCAL read at owning node)" --> AUTHa & AUTHb
  AUDa -- "periodic signed chain-head checkpoints" --> TXP
```

**Invariant (D6):** confidential payloads NEVER enter the control plane or shared index. The Exchange holds only **PublishableProjections** (public/shared-tier, MAX-rule-bounded — §6/§11) and **grant *references*** (not contents) + public grant-opportunity feeds. Cross-institution discovery and team assembly operate on public/shared projections; **confidential collaboration happens via brokered, owner-mediated drill-down where the OWNER node serves its own data after re-deriving authority** (§4.3, D5).

### 4.2 The single confidentiality chokepoint (D4)
**Every** retrieval, egress, and derivation in a cell flows through **one Policy Enforcement Point + Data-Access Broker.** Feature modules receive **already-projected, already-tier-checked result objects** and **never see raw classification logic or the raw store.** This is the structural resolution of Triage C10 ("pluggable module impossibility"): modules never re-implement enforcement. Enforced:
- Import-linter forbids feature modules from importing the raw store, the classifier, or constructing a `PublishableProjection`.
- Runtime: the broker is the **only** holder of raw-store credentials (per-module DB-role isolation, §5/§7).
- The egress PEP **re-evaluates classification against a publishable allowlist schema at the boundary** (Triage C11): the outbox is *checked, not trusted* — the same PEP is the deny-by-default egress validator.

Adding `mod-funding` (Phase 3) therefore **inherits enforcement for free** — it cannot leak because it never touches classified data except through the broker.

### 4.3 How cross-institution discovery & team assembly work WITHOUT centralizing confidential data (D5/D6)

**Discovery + team assembly (public/shared).** Owner cells publish MAX-rule-bounded projections to the central index via CDC (§10). Team-assembly candidate ranking runs over the central public-tier expertise graph + public grant feeds; **shared-tier hits are post-filtered at query time against the owner's live revocation epoch** (§4.4) so CDC lag never yields a stale hit.

**Confidential collaboration (proposal workspace) — brokered, owner-authoritative drill-down.**

**Universal invariant (Triage C15, generalized to ALL cross-tenant access):** *Owner-side authoritative re-derivation. Broker and grantee assertions are untrusted hints.* Every brokered request carries a **grant-ID**; the **owner node** looks the grant up in its **own authoritative GrantStore** (D5 — sole local authority), re-derives scope + tier + caveats + revocation status, and **ignores any scope claim in the token.** The broker is a deputy with credentials to many tenants; it can never be confused into widening scope because the owner never trusts the presented scope. **Caveats are sticky and re-evaluated at grantee-side access** (`transfer_legality`, `export_attestation`, `FERPA_role` — §11.5).

**Token security:** per-tenant-signed, HSM-DPoP-bound, **audience-bound, single-use, short-TTL.** A replayed token hits the synchronous revocation check (§4.4) → live deny.

**Per-hop deadline-propagated latency budget (composite SLO = 6.5s; reconciles Triage C14 worst-case US→EU):**

| Hop | Budget (p99) | Notes |
|---|---|---|
| Client → query cell | 150 ms | TLS + ingress |
| Query cell → Exchange broker | 120 ms | intra-region |
| Broker → owner cell (cross-region worst case, US→EU) | 350 ms | RTT + queueing |
| Owner-side SpiceDB Check (**local replica read**, §7) | 20 ms | not cross-region (D5) |
| Owner-side revocation lease read (**local fenced lease**, §4.4) | 15 ms | **not a consensus round trip** (D5) |
| Owner-side retrieval + synthesis (in-boundary vLLM TTFT+gen) | 4,500 ms | dominant |
| HSM sign (fair-exchange receipt) | 80 ms | §11.4 |
| Return path | 400 ms | |
| **Subtotal** | **5,635 ms** | |
| **Reserved slack** | **865 ms** | absorbs jitter |
| **Composite SLO** | **6,500 ms** | |

**Worst-case cross-region table (Triage item 28, C14):** US-subject requester → EU-resident confidential artifact → generated answer = the row above with the 350ms cross-region hop. Because D5 makes authority **local at the owner**, there is **no added consensus hop**; the residual cross-region cost is one RTT to reach the owner + the owner's local checks. This reconciles against the 6.5s Q&A SLO with 865ms slack.

**Deadline propagation:** each hop passes a **shrinking deadline**; a hop that cannot meet its remaining budget **fails-closed-fast.** **Circuit-breaker trip threshold = the hop's deadline fraction** — a *slow* owner node (gray failure, the dominant federation failure mode) trips at its budget boundary, not only when fully offline. Gray-failure (injected owner-node latency) is a **Phase-2 milestone test.**

### 4.4 The revocation authority: lease-based LOCAL reads at the owning node (D5)

**D5 locks this:** *the owning institution node is the SOLE, LOCAL, fail-closed authority for access/revocation of its confidential artifacts. No global multi-region consensus on the hot path.* This resolves the largest finding cluster (Triage C6/C7).

**Design.** Each owner cell is the authority for *its own* artifacts. The hot-path check is a **local read** of the cell's lease cache: `lease.valid && now < lease.expiry && grant not in local tombstone-since-lease`. **No cross-region hop on the read path** (the 15ms in §4.3).
- For ordering of *its own* revocations, the cell uses a **local monotonic fenced counter** (no cross-region consensus). Revocation = local tombstone commit + local lease invalidation.
- The control-plane Revocation Authority does **not** adjudicate access; it only **replicates revocation epochs/tombstones for shared-tier discovery post-filtering** (eventually consistent, §10.3) and issues **fenced grant-validity leases** the owner cell reads locally. **It is never on the confidential read hot path.**

**CAP posture (Triage item 27, C13).**
- Confidential reads serve against the **local lease** until TTL; then **fail-closed-deny** (correct). A control-plane partition is **NOT** an instant total outage; it is **TTL-bounded graceful degradation, then deny**, scoped to the partitioned cell only (D5 bounds the blast radius to one owner node).
- **Published number (release gate):** expected confidential deny-minutes/year at a measured inter-region partition rate, with the cell's local-authority SLO and 2s TTL, is **derived from the Phase-1 spike and published** (Q4) — a measured number, not a target.

**Separate SLOs + honest compound availability (Triage item 27).** Index-path discovery and the brokered confidential-drill-down path have **separate SLOs.** The brokered path is **multiplicative** across (broker × token-mint × owner authority × watermark feed) which share a control-plane failure domain → its honest compound availability under correlated control-plane degradation is **lower than any single component** and is published. **Explicit degraded mode:** *owner node unreachable → publishable metadata only, confidential detail unavailable* (never a stale allow).

### 4.5 Revocation by *reason*, not just tier (Triage C19, item 4)
The allow-window distinguishes **reason**, not only tier:
- **Security / consent-withdrawal / compromise / GDPR Art. 7(3) / FERPA-revocation** → **synchronous deny-correct path at the owning node, zero allow-window, regardless of tier.**
- **Benign administrative revocation of low-sensitivity public/shared data** → bounded allow-window (lease-TTL, default **2s**) acceptable.
- Per-tier, per-reason **maximum-staleness commitment** stated explicitly; confirmed with DPO (Q13) and registrar (Q14).

### 4.6 Skew & ordering
No self-asserted timestamp orders a security decision; ordering uses the **owning cell's local fenced monotonic counter** (D5 — no global clock needed). A node whose clock skew exceeds `max_skew_bound` **fails-closed-deny for its own security decisions + alarms.** The local fenced-counter write path is confirmed to sustain the worst-case bulk-revoke rate via **tombstone coalescing** (tenant/scope-version supersedes N); the **revocations/sec ceiling is published** and tied to bulk-revoke saturation handling (deny-wider on saturation, never global-stall).

---

## 5. Modularity Model

### 5.1 Canonical module map
A committed artifact `shared/contracts/MODULE_MAP.md` is the single source of truth; the **import-linter config is its executable mirror.**

```mermaid
flowchart TB
  subgraph KERNEL["kernel (near-frozen, zero outbound feature deps, no persistence)"]
    K1["TierLattice (3 tiers + ordering, formally specified) — owned in shared/contracts"]
    K2["PublishableProjection type + MAX-rule"]
    K3["Interface defs: IPolicyEnforcement, IModelRouter, IRetrievalStrategy, IGrantStore, IRevocationAuthority, IAuditSink, IExpertiseFingerprint, ICollaborationGraph, IExchangeFeed, IEntitlement, IVectorStore, IGraphStore, ILexicalIndex, IModelProvider, IIndexProfile"]
  end
  subgraph PLANE["enforcement plane (the SINGLE chokepoint — D4)"]
    PEP["Egress PEP + Data-access broker"]
    CLS["Classifier (+ quarantine/adjudication)"]
    ENT2["Entitlement evaluation"]
  end
  subgraph FEAT["feature modules (pluggable)"]
    M1["mod-lit-intelligence (proposal grounding)"]
    M2["mod-discovery (team assembly)"]
    M3["mod-workspace (confidential co-editing)"]
    M4["mod-funding (opportunity match + team assembly)"]
  end
  subgraph SVC["evicted services (own DB + event-bus only)"]
    S1["identity-resolution"]
    S2["read-models"]
  end
  FEAT --> PLANE
  PLANE --> KERNEL
  FEAT --> KERNEL
  FEAT -. "domain events (versioned)" .-> SVC
```

### 5.2 Module definition, isolation, versioning, communication
- **A module** = an owned schema + owned DB role + published domain events + consumed/published interfaces. It owns its data; no other module reads its tables.
- **Isolation from day one (Triage item 16):** even inside the Phase-0 modular monolith, **per-module Postgres schemas + per-module DB roles with `REVOKE` on other schemas** are enforced (DDL + GRANT, nearly free) — *import-linter alone cannot stop shared-table reads.* Paired with import-linter + a no-cross-schema-query lint/runtime check.
- **Communication = published domain EVENTS with a versioned schema (Triage item 15):** an **in-process event bus in Phase 0 using the same versioned contract** (Protobuf/Avro + schema registry + compatibility rules) that Kafka will carry later — so the extraction escape-hatch genuinely exists from Phase 0. Each topic states **idempotency, ordering, and replay guarantees** explicitly. **CDC/Debezium is permitted ONLY for replicating a module's OWN data to its OWN read store — never as a cross-module integration API.**

### 5.3 Add/remove a module with minimal blast radius
- **Add:** register edition capabilities; declare consumed interfaces; receive already-projected objects from the broker. No confidentiality re-threading (chokepoint, §4.2).
- **Remove:** disable its capability in Entitlement; drop its schema; deregister its events. Blast radius bounded by its owned schema + enumerated event consumers.

### 5.4 Extraction trigger (concrete)
Extract to its own service **when EITHER:** (a) measured CPU/QPS exceeds 40% of cell budget while siblings idle, **OR** (b) change-frequency exceeds 2× the cell median for 2 consecutive months. Extraction = own DB (already true) + event-bus-only (already true) → mechanical. **Honest MVP posture (Triage item 17): a modular monolith — single deployable, in-process boundaries — NOT "independently-deployed services."**

### 5.5 Bounded kernel — checkable fitness function
A type/interface belongs in the kernel iff **(a) zero deps on feature modules, (b) no persistent state, (c) referenced by ≥2 features.** Failing these → **evicted** (identity-resolution, read-models). Enforced by import-linter contracts + a CI check on kernel package fan-in and size.

### 5.6 TierLattice: additive, safe-by-construction (Triage item 13)
We **DROP "control plane refuses activation until all attest"** (a global liveness barrier). Replaced with **additive, versioned, fail-closed-by-construction:**
- The **tier set is a tiny, near-frozen, formally-specified lattice (3 tiers + ordering + MAX-rule)** owned in `shared/contracts`. **Per-feature classification CODES live in an extensible registry mapping onto the frozen lattice** (SAFETY semantics separated from EXTENSIBILITY).
- We do **NOT** claim compiler-enforced exhaustiveness across distributed consumers. Instead: a **versioned artifact + per-consumer conformance registry + min-node-version floor** where an **unknown tier is treated MOST-restrictive** (safe-by-construction, not blocked-by-barrier).
- **Version negotiation:** nodes advertise supported lattice versions; the Exchange operates at the **min-common version.** New tiers/codes are additive with default-deny.
- **Two-phase rollout:** all nodes RECOGNIZE a value (fail-closed default) *before* any node EMITS it.
- **Reclassification recall:** every PublishableProjection is **stamped with the lattice-version it was derived under**; a tightening change triggers a re-derivation/withdrawal pass (recallable by construction).

### 5.7 Defer governance machinery until needed (Triage C22)
Conformance-attestation activation gates, formal multi-consumer deprecation lifecycles, and version-matrix caps **solve coordination problems that only exist at many-consumer scale** → **explicitly deferred to N≥5 (Phase 2).** Phase 0–1 use a modular monolith + `mypy assert_never` + ordinary contract tests + the additive-lattice rule above.

### 5.8 Swappable AI router & retrieval via interfaces (Triage item 14)
- **`IModelProvider`** declares: capabilities (context window, **embedding dim**, tool-use, structured-output), **which locality-classes it satisfies**, cost, and a **no-train/retention attestation.** The router selects over a **registry of providers that DECLARE the locality classes they satisfy** — *not* a hardcoded tier→provider table. BYO endpoints register with **attested** locality (§8).
- **Single owned `tier→locality routing-policy table` consulted by BOTH the router and the transport/egress layer** — never two independent re-derivations. Disagreement = "router violated given policy" → hard-fail.
- **`IVectorStore`, `IGraphStore`, `ILexicalIndex`, `IRetrievalStrategy`** insulate callers from engine choice; RRF fusion and the planner consume only these. A **conformance suite** (multi-hop/PPR correctness) gates any `IGraphStore` impl → Neo4j/Memgraph is a drop-in (Triage item 10 fallback).
- **`IIndexProfile`** = (embedding-model-version, engine, DP params). The **central-index privacy bound is pinned to an IIndexProfile**, so an embedding swap **forces re-validation through a gate** (§8/§11).

---

## 6. Data Model & Knowledge Graph

### 6.1 Core entities & ER

```mermaid
erDiagram
  INSTITUTION ||--o{ RESEARCHER : employs
  INSTITUTION ||--o{ CELL : owns
  RESEARCHER ||--o{ AUTHORSHIP : has
  PAPER ||--o{ AUTHORSHIP : has
  PAPER ||--o{ CONCEPT : tagged
  RESEARCHER }o--o{ GRANT_AWARD : participates
  FUNDING_OPP ||--o{ GRANT_AWARD : realizes
  PROPOSAL ||--o{ ARTIFACT : contains
  PROPOSAL ||--o{ TEAM_ROLE : staffs
  RESEARCHER ||--o{ TEAM_ROLE : fills
  ARTIFACT ||--|| CLASSIFICATION : has
  CLASSIFICATION ||--o{ COMPLIANCE_FLAG : carries
  SHARING_GRANT ||--|| ARTIFACT : scopes
  SHARING_GRANT ||--|| INSTITUTION : grantor
  SHARING_GRANT ||--|| INSTITUTION : grantee
  PUBLISHABLE_PROJECTION ||--|| ARTIFACT : derives
  PUBLISHABLE_PROJECTION ||--|| LATTICE_VERSION : stamped
  RESEARCHER }o--o{ RESEARCHER : collaborates
```

- **PROPOSAL** = the confidential proposal workspace (the wedge artifact): team roles, draft sections, budget, preliminary data — almost always tier=confidential.
- **FUNDING_OPP** = a grant opportunity from Grants.gov/RePORTER/NSF (public-tier).
- **CLASSIFICATION** = `{tier: public|private|confidential, codes: [...], compliance_flags: [FERPA|IRB|ITAR|EAR|GDPR-personal], lattice_version}`. **COMPLIANCE_FLAG** is sticky (UNION on join, §11). **SHARING_GRANT** is explicit, revocable, scope-bounded, owner-authoritative (§4.3).

### 6.2 Scholarly + grant ingestion (public-tier, redistributable; licensing-clean)
**Scholarly (per research brief licensing traps):**
- **OpenAlex** — *self-host the free monthly CC0 snapshot;* the live API is metered (never on a hot path).
- **Crossref** — DOI metadata + references (annual file).
- **ROR** — institution disambiguation (CC0).
- **ORCID** — *ship the CC0 annual Public Data File, NOT the non-commercial live API.*
- **Semantic Scholar bulk (ODC-BY, attribution) / SPECTER2 (Apache-2.0)** — paper embeddings for similarity/expertise fingerprints.
- **PMC / Europe PMC OA-subset** — full text under a **commercial-OK OA filter** (CC0/BY/BY-SA/BY-ND; exclude NC) — Q16 sizes the usable corpus.

**Grant (public/CC0/US-gov):**
- **Grants.gov** opportunity feed, **NIH RePORTER** awards, **NSF Awards** — public-tier funding-opportunity + award graph powering `mod-funding` and team-assembly priors.

### 6.3 Entity resolution / author disambiguation across institutions
Deterministic anchors (ORCID, DOI, ROR) first; probabilistic blocking (name + co-author + concept + affiliation-time) for the unanchored tail. **`identity-resolution` is an evicted service** (own DB + events). Cross-institution resolution decisions are **trust artifacts that accumulate as data-gravity** (§1) — the disambiguation graph is **public-tier by construction**; confidential records are resolved **inside the cell only** (resolution never crosses the boundary).

---

## 7. Identity & Access Control

### 7.1 Federated identity
- **Keycloak** per-cell + control-plane broker.
- **CILogon / eduGAIN / InCommon (SAML)** for university federation (commercial CILogon subscription = COGS line, Q10). REFEDS R&S + Sirtfi + CoCo v2 to industrialize attribute release.
- **Phase-0 reality:** the anchor center's sites use plain **OIDC (Okta/Entra)** or CILogon — confirmed in Gate B. **ANY campus-wide/consortium buyer triggers SAML/eduGAIN brokering**, sized now in engineer-weeks (Q10) and gated behind that line being built. Phase-0 ships **Direct OIDC/CILogon to the buyer's IdP** only. Authorize on `eduPersonScopedAffiliation` + stable `eduPersonUniqueId`; ORCID = correlation key, not auth root of trust.

### 7.2 Authz model: ABAC (Cedar/OPA) + ReBAC (SpiceDB/OpenFGA)
- **ABAC (tiers + attributes)** via **Cedar** (deterministic, validated; OPA/Rego fallback) — evaluates classification tier × subject attributes (FERPA authorization, US-person status, edition capability).
- **ReBAC (sharing grants)** via **SpiceDB** (ZedToken; OpenFGA `HIGHER_CONSISTENCY` fallback) — relationship graph for grants, workspaces, membership.

### 7.3 Authz data model (concrete)
```
// ReBAC (SpiceDB schema sketch) — proposal workspace + cross-institution grant
definition institution { relation member: user }
definition proposal { relation owner: institution; relation collaborator: user | institution#member }
definition artifact  { relation parent: proposal; relation grantee: user | institution#member
  permission view = grantee + parent->collaborator + parent->owner->member }
// every sharing_grant carries: grant_id, scope, tier, caveats{transfer_legality, export_attestation, FERPA_role},
//   lattice_version, revocation_epoch
```

**ABAC composition invariants (Triage item 2, C16) — inside the single PEP:**
- A `view` permission is **necessary but not sufficient** — the PEP additionally evaluates Cedar (tier vs requester attributes vs edition) **and** the revocation lease (§4.4) before release.
- **Missing/indeterminate ABAC attribute → DENY for confidential + export tiers.**
- **ABAC may only NARROW a ReBAC grant, never widen** (property-tested invariant, §15).
- **PIP unavailability on a confidential check → DENY, no cache-fallback.**

### 7.4 Subject deprovisioning is a first-class PEP check on ALL non-public tiers (Triage item 3, C18)
The **subject-not-deprovisioned freshness check is extended to ALL non-public tiers AND to the discovery PEP** (not just confidential drill-down). Subject-revocation (SCIM deprovision / affiliation loss / session-kill) is a **first-class check in the standard PEP decision flow on every request touching private/confidential** — checked at the owning node (D5-compatible), evaluated inside the single PEP (D4-compatible).

### 7.5 Cell-local SpiceDB: go/no-go fork, not a free config (Triage item 25, C7)
ZedToken→local-revision translation is a **Phase-1 go/no-go architectural fork, prototyped Week 1, MEASURED** against SpiceDB's actual primitives — **treated as a likely bespoke build, not a free configuration choice.**
- **Prototype:** SpiceDB replication (`Watch`/`LookupResources` + local materialized cache with a stated staleness bound); measure replication lag + fail-closed-on-lag.
- **If monotonic reads under lag CANNOT be guaranteed:** we do **NOT** ship "synchronous cross-region Check on every request" (blows both SLOs). Instead: **cache authz decisions cell-locally with a short bounded TTL** (the staleness bound becomes a first-class consistency guarantee) + a synchronous re-check **only on the confidential-sensitive subset** — collapsing into the §4.4 lease design. **D5 reduces but does not eliminate** the need for grant-tuple availability at the owning node, so this fork is still required.

### 7.6 PDP location
The **PDP sits at the cell-local PEP** for all in-cell access. For cross-tenant access, the **PDP is the OWNER cell's PEP** (owner-side re-derivation, D5/§4.3) — never the broker, never the requester's cell.

---

## 8. AI / Model-Router Layer

### 8.1 Classification-routed, provider-agnostic router (Triage item 14)
The router selects over the **`IModelProvider` registry** (§5.8). Each provider **declares the locality classes it satisfies**; the router matches the data's classification to a provider that satisfies the required locality **and** capability/cost. **Single source of truth:** one owned policy table consulted by both router and transport (egress); disagreement → hard-fail. A precedence change is a single-table edit.

### 8.2 Routing rules (fail-closed)
| Data class | Allowed providers |
|---|---|
| **confidential (e.g., proposal drafts/budgets)** | in-boundary self-hosted ONLY (vLLM prod / Ollama dev) |
| **export-controlled (ITAR/EAR)** | in-boundary self-hosted on an **export-conformant cell** (§11.6) ONLY; **BYO refused unless TEE-attested + jurisdiction-proven** |
| **private (institution-internal)** | in-boundary, or BYO endpoint with attested locality |
| **public / low-risk** | cloud frontier (Anthropic/OpenAI/Google) or local |

### 8.3 BYO provider/keys per institution (Triage item 26, C12)
- BYO endpoints register as `IModelProvider` with **attested** locality.
- **"No-retention" is a CONTRACTUAL control**, not cryptographically enforceable, with a **TEE-remote-attestation technical upgrade path.** mTLS proves endpoint identity; in-boundary network proof shows traffic stays in a controlled boundary — **but neither cryptographically prevents a BYO provider from logging prompts. We do not overclaim.**
- **For export-controlled / EU-personal data:** the BYO endpoint **MUST present TEE-with-remote-attestation** (enclave + no-log proof + jurisdiction proof + named-person access = the concrete definition of "sovereign-verified" in `shared/contracts/`). **If the BYO provider cannot attest, the router fails closed and falls back to the in-boundary self-hosted model** — a fail-closed routing rule in the policy table, not a contractual caveat.
- BYO constrained to a **pre-certified matrix (2–3 clouds, 2–3 providers)** early; priced as a higher-touch edition with services attach.

### 8.4 Embeddings & serving
- **Embeddings:** SPECTER2 (scholarly/citation space, expertise fingerprints) + BGE/Qwen3 (general ad-hoc RAG); nomic fallback. **Embedding-model identity is a versioned `IIndexProfile` property** with an explicit re-embed migration contract; a swap is **gated** (re-validates the membership-inference bound, §11), never silent.
- **Serving:** vLLM (prod, multi-GPU tensor-parallel; ~24× TGI throughput, avoids TGI maintenance-mode trap); Ollama (dev, M4 Max 36GB — **UI/pipeline dev only, never the confidential-path test target**, §15).

### 8.5 Grounded generation for proposal drafting + guardrails
- **Grounded drafting (the wedge):** proposal-section drafts are generated **grounded in the confidential workspace + public scholarly corpus**, with citations, on the in-boundary model only. RAGAS faithfulness is a release gate (§9.3).
- **Guardrails:** output-channel egress check (§11.5 — completions grounded in tainted sources re-checked against requester attributes), prompt-injection filtering on retrieved context, tier-pinned tool use, PEP-on-every-agent-action (Phase 3 multi-agent).

---

## 9. Retrieval Architecture

### 9.1 Hybrid retrieval (MVP-essential)
Vector (`IVectorStore`, Qdrant) + BM25 (`ILexicalIndex`, OpenSearch — academic corpora are entity-heavy: author names, acronyms, grant numbers, gene names) + **RRF fusion (k≈60, tenant-local weights)**, behind `IRetrievalStrategy`. **Reranking** (BGE-reranker-v2-m3 / Qwen3-Reranker, local) top-50→top-8. This is the Phase-0 `mod-lit-intelligence` core for proposal grounding.

### 9.2 GraphRAG & agentic (later, justified) — with the AGE benchmark gate (Triage item 10, C21b)
- **Deterministic metadata-backbone graph** (authors/papers/citations/affiliations/venues/grants/topics) first — cheap, no LLM-extraction tax.
- **Ego-graph traversal** for collaborator/team-assembly context — Phase 1.
- **HippoRAG2 / personalized PageRank (~1k tokens/query)** — Phase 2, **post-AGE-verdict.** **Apache AGE multi-hop + PPR is BENCHMARKED at realistic R1 graph scale (N=200: ~300M nodes / ~1.6B edges, §14.2) BEFORE it is locked** (Q6); concrete fallback switch criterion → **Neo4j (GPLv3, isolate) / Memgraph (BSL)** behind the `IGraphStore` conformance suite. **Microsoft GraphRAG global community summarization (~331k tokens/query) is explicitly overkill** — a later opt-in module only.
- **Bounded-candidate team assembly** (no global PPR over the central graph) — Phase 2/3.
- **Agentic/planner strategies (Adaptive RAG → CRAG → multi-hop)** — Phase 3, capped + tier-pinned + PEP-on-every-action.

### 9.3 Evaluation harness
**RAGAS-in-CI** (faithfulness, context-precision/recall) + nDCG@k/Recall@k on a small in-domain gold set, **a release gate** for retrieval quality (§15), run **per-tenant and per-model-route.** The **judge LLM is the local model on the confidential tier** (router-aware eval — you cannot send confidential answers to a cloud judge). Per-tenant gold-sets (data-gravity) built **inside the cell** (Q20), GPU-staging prod-size judge.

### 9.4 Discovery correctness under partial failure
The **common public/shared discovery path uses per-shard partial-results-with-honest-completeness-indicator** (coarse + DP-noised), **NOT whole-query-fail-closed** — one slow/partitioned shard degrades a *bounded fraction* of results with an explicit completeness flag, never empties the query. **Whole-query-fail-closed is reserved for the confidential path only.** DP-noise impact on top-k recall is **quantified** (measured number); shard-failure blast radius stated (one shard down = which fraction degraded). Per-shard `incomplete` is not exposed per-topic (covert-channel decoupled from topology).

---

## 10. Data Pipelines & Orchestration

### 10.1 Orchestration substrate ownership (one-line rules)
| Substrate | Owns ONLY |
|---|---|
| **Dagster** | ingestion / distillation / index **batch DAGs** + grant-feed sync |
| **Temporal** | durable, compensating, long-lived **business workflows** (grant lifecycle, revocation-propagation side-effects) |
| **Kafka/CDC** | **data replication to read stores** — never business logic |

**Phase-0 simplification (Triage item 18, C22):** **Dagster ONLY.** **Defer Temporal + Debezium + Kafka + schema-registry**; Phase-0 grant-lifecycle uses a **Dagster sensor + transactional-outbox-polling** (not log-based CDC). Temporal is introduced only when a customer contract requires durable compensation.

### 10.2 Ingestion/distillation
Dagster DAGs: crawl/snapshot (OpenAlex/Crossref/ROR/ORCID-dump + Grants.gov/RePORTER/NSF) → entity-resolve → distill (research cards) → **classify (gates index)** → embed → index → graph-build. **Classify-gates-index** is a hard edge: unclassified/quarantined records (§11.1) **never enter any index.**

### 10.3 Cell↔Exchange sync: consistency contract (per D5/D6)
Phase 0–1: **transactional-outbox-polling.** Phase 2+: Debezium + Kafka, **CDC ordering keyed per-(tenant, record)** so grant/revoke/republish for one record are totally ordered. The **index consistency contract:**
- (a) Every index record carries `PublishableProjection.version + grant_epoch`. The applier is **idempotent and MONOTONIC** — it **rejects lower-epoch applies**, so replays/snapshots **cannot resurrect** a revoked/downgraded record (Triage C6 tombstone ordering).
- (b) **Shared-tier discovery results are post-filtered at query time against the owner's live revocation epoch/bitmap** — promoted from perf-only to a **correctness gate for shared-tier discovery**, so CDC lag never yields a stale HIT.
- (c) **Lease-liveness is decoupled from full re-publish (Triage item 12, C21d):** a lightweight **per-record-version TTL index** carries liveness; we do not re-publish the whole projection to refresh a lease.
- (d) **Bounded staleness SLO:** share→discoverable ≤ 30s; **revoke→undiscoverable: synchronous via query-time epoch filter (effectively immediate for hits); CDC index removal ≤ 30s.**

### 10.4 Consistency model (D5)
- Within a cell: **strong** (transactional Postgres + read-your-writes).
- Cell→central index: **eventual with bounded staleness** + query-time epoch post-filter for correctness.
- **Confidentiality decisions: strongly consistent at the OWNING NODE only (D5); discovery metadata eventually-consistent.** Revocation: **deny-correct** (synchronous for security-reason/high-sensitivity at the owner; lease-TTL-bounded for benign low-sensitivity — §4.4/§4.5).

---

## 11. Security, Privacy & Compliance

### 11.1 Classifier abstention = quarantine, Phase 0 (Triage item 8, C9; D6)
**Explicit fail-closed semantics (Phase 0, NOT deferred):** any record the single classifier **cannot confidently label** (below a stated confidence threshold) is **quarantined to `unclassified = confidential, excluded-from-ALL-retrieval`** and routed to a **human adjudication queue** before it can enter any index. The confidence threshold + review queue are **Phase-0 build items.** A confidently-labeled record uses its label. (The dual classifier — agreement-for-tier-down — is deferred to Phase 1; **default-deny-on-abstention + adjudication is Phase 0.**)
**Phase-0 contract test:** inject low-confidence and **adversarial records (confidential content with public-looking metadata)**; assert **zero leak** into any retrievable surface.

### 11.2 Central-index privacy bound proven BEFORE real embeddings ship (Triage item 8, C8; D6)
The index is a **one-way door.** The membership-inference + embedding-inversion + **cross-tenant-linkage** red-team is a **GATE on the index DESIGN — proven on SYNTHETIC/de-identified corpora BEFORE any real embedding is written** (a Phase-2 GA gate would be past the point of no return). Per D6, **confidential content NEVER enters the shared index** (public + explicitly-shared metadata + non-reversible signals only).
- The **quantified resistance bound (ε, k, churn-noise) is specified in `shared/contracts/` pinned to an `IIndexProfile`.**
- **Cross-tenant co-occurrence/linkage is explicitly in the threat model:** correlating public-tier presence/churn across consortium members to infer the *existence* of an undisclosed confidential collaboration is a metadata leak even with a perfect MAX-rule. Mitigations: presence/count/churn DP-noise, k-anonymity, **per-consortium scope-keys**, decoupling churn signals from tenant identity.
- A **rollback/re-embed procedure** is specified if the bound is later insufficient (versioned, provenance-carrying projections = recallable by construction).
- **Classifier abstention → quarantine default-deny (D6):** abstained records are *never* candidates for a shared-index write.

### 11.3 Confidential-tier crypto & key lifecycle (Triage item 24, C5/C7 hygiene; D7)
- **At rest:** **default to cloud KMS per-tenant keys** (managed; no namespaces, no unseal toil). **Self-run Vault reserved for sovereign/on-prem only** — we do **NOT** assume Vault Community namespaces (Enterprise-only). HYOK (customer-held keys, vendor-blind-at-rest) for the confidential tier; **HYOK NOT overclaimed for at-use** — plaintext-at-use residual stated; TEE-at-use is the upgrade path.
- **Envelope encryption** for confidential shared artifacts: revocation/offboarding triggers **crypto-shred of the data-key wrapping** → retained ciphertext becomes undecryptable.
- **Per-consortium scope-keys ROTATE on membership change**; consortium dissolution rotates keys (crypto-shred).
- **`allow_durable_copy` (default false):** if a durable copy was granted, the UI/audit state plainly that revocation is **best-effort and the copy is permanent.**

### 11.4 Audit: anchored against the node operator (Triage items 6, 7; C17)
- **Hash-chained, tamper-evident per-(tenant/stream) PARALLEL chains** (not one global serial chain) — removes the per-cell single-writer throughput ceiling; **append-rate ceiling stated and confirmed to exceed peak served-operation rate per cell.**
- **External anchoring against the operator (C17b, insider/compelled-access in the model):** every node's audit chain emits **periodic signed chain-head checkpoints to the control-plane transparency log and/or an RFC-3161 TSA / public transparency log** → tamper-evident even for internal-only access and even against a compelled operator. **Checkpoint interval = the maximum undetectable-rewrite window** (a compliance-tier parameter).
- **Fair-exchange disclosure (C17a):** the **owner issues a signed access-receipt binding `(grant_id, grant_version, scope, token_jti, watermark, ts)` and obtains a signed request-receipt BEFORE serving bytes** (commit-then-serve). **Divergence response is a control, not just detection:** auto **freeze the grant + P1 + suspend pending investigation.**

### 11.5 Sticky taint flows to the COMPLETION (Triage item 1; C15)
Compliance flags are **sticky (UNION on join).** **The taint flows to the AI completion:** a grounded answer over tainted sources is a confidentiality/export event **at generation time.** **The egress PEP covers the model OUTPUT channel to the user** (not only cross-node publication): at generation/response time it re-checks **requester attributes** (FERPA authorization, US-person status).
- **Export-controlled access is gated by an institution-attested US-person SIGNED grantor caveat (export-control-officer assertion) — NEVER an SSO-carried nationality attribute (C15).** **Owner-side authoritative re-derivation of grant scope is the universal invariant for ALL cross-tenant access**; grantee/broker assertions are untrusted hints. Caveats (`transfer_legality`, `export_attestation`, `FERPA_role`) are **sticky and re-evaluated at grantee-side access.**
- **Contract test:** a foreign-person requester gets deny/redaction when the grounded answer would reveal export-tainted content, even though they could retrieve the differently-classified surrounding context.

### 11.6 Export control: operational-access surface, not just end-users
Export-controlled data is **FORBIDDEN on any non-export-conformant cell.** An **export-conformant cell requires:** US-person-only **vendor operational staff**, **US-region hosting**, **TEE-at-use** (removes vendor operational access from the deemed-export surface). The router/cell-placement policy **refuses to place export-classified data on a non-conformant cell.** **FRE caveat (research brief):** the export gate is **opt-in per controlled project, never blanket** — imposing access restrictions on ordinary fundamental research can itself strip the Fundamental Research Exclusion. Until export-conformant cells exist (Phase 2+), **export-controlled data is not accepted** (Q12).

### 11.7 GDPR / FERPA + per-data-subject erasure (Triage item 5, C20)
- **Every cross-region/cross-border flow mapped to a transfer mechanism** (adequacy/SCCs) as a Phase-1/2 design artifact. **EU control-plane + EU Exchange pinned to EU regions** — EU confidential-path lease consultations + brokered-drill-down metadata never leave the EEA.
- **Per-plane controllership:** cell = **processor**; Exchange = **joint-controller** (Art. 26 arrangements + lawful basis as an EU-index release gate). FERPA: vendor positioned as **"school official" under institutional control.**
- **Per-data-subject erasure workflow distinct from tenant-KEK crypto-shred (C20):** GDPR Art. 17 / FERPA erasure = **targeted hard-delete + tombstone of that subject's published projections/embeddings in the shared index** (subject-keyed reuse of the revocation-tombstone path), **plus Art. 19 recipient-notification to consumers that pulled the projection.** This is required because the central index holds *published* projections (researcher names/affiliations = personal data) even though D6 keeps *confidential* content out. Public-tier graph: confirm with DPO whether **opt-out-default vs opt-in/legitimate-interest-balancing** is required for EU subjects (Q13).

### 11.8 Threat model & top mitigations
| Threat | Mitigation |
|---|---|
| Misclassification (root leak) | quarantine-on-abstention Phase 0 + adversarial zero-leak contract test (§11.1) |
| Federation-seam leak | single PEP chokepoint (D4) + structural PublishableProjection + MAX-rule incl. codes; confidential never in index (D6) |
| Revocation fail-open | owning-node local-lease deny-correct (D5/§4.4); synchronous for security-reason regardless of tier (§4.5) |
| Confused-deputy / cross-tenant IDOR | owner-side re-derivation UNIVERSAL invariant + grant-ID lookup + audience-bound single-use DPoP tokens (§4.3) |
| Export-controlled access via unverified nationality | institution-attested US-person signed grantor caveat, never SSO attribute (§11.5) |
| Subject deprovisioned but still served | all-tier + discovery-PEP freshness check (§7.4) |
| Cross-tenant linkage inference | DP-noise + k-anon + scope-keys + churn decoupling (§11.2) |
| Operator audit rewrite (insider/compelled) | external chain-head anchoring + fair-exchange receipts + divergence freeze (§11.4) |
| RAG output leak / export taint | output-channel PEP re-check at generation (§11.5) |
| GDPR/FERPA erasure not satisfied | per-subject hard-delete + tombstone + Art. 19 notification (§11.7) |
| Deemed export (operational) | export-conformant cells only (§11.6) |
| Retained-ciphertext after revocation | envelope crypto-shred (§11.3) |
| ABAC PIP fail-open / widen | DENY on missing attr (conf/export); ABAC narrows-only; no cache-fallback (§7.3) |

### 11.9 SOC2 / ISO readiness + HECVAT
**HECVAT** (full toolkit) is mandatory before any pilot/purchase. **SOC2 Type I is sequenced first (point-in-time), targeted at the Phase-0/1 boundary** (deferrable if the sandbox/de-identified pilot doesn't require it — validated with a named buyer's CISO/contracts officer as a **Week-1 kill-gate sub-condition**, Q17). SOC2 Type II → Phase 2; ISO 27001 → Phase 3 (EU). The **"sandbox pilot avoids full security review" claim is validated in writing** with the anchor center's CISO before runway is modeled against the fast path.

---

## 12. Technology Stack

| Layer | Primary | Fallback | Licensing flag |
|---|---|---|---|
| Backend | Python 3.12 / FastAPI | — | — |
| Module isolation | per-schema + DB-role + import-linter | — | — |
| ABAC | Cedar | OPA/Rego | both OSS |
| ReBAC | SpiceDB | OpenFGA (`HIGHER_CONSISTENCY`) | SpiceDB Apache-2; **AuthZed managed = paid**; **avoid Permify (AGPL)** |
| Vector store | Qdrant | pgvector (small tenants) / OpenSearch kNN | Apache-2 |
| Lexical | OpenSearch BM25 | Tantivy/Quickwit | Apache-2; **NOT Elasticsearch (AGPL)** |
| Graph | Apache AGE (on Postgres) | Neo4j (**GPLv3 — isolate**) / Memgraph (**BSL**) | **Kuzu archived — replaced by AGE** |
| Embeddings | SPECTER2 + BGE/Qwen3 | nomic | Semantic Scholar bulk = ODC-BY (attribution); SPECTER2 Apache-2 |
| LLM serving (prod) | vLLM | SGLang | **NOT TGI (maintenance mode)**; Apache-2 |
| LLM serving (dev) | Ollama (M4 Max 36GB) | llama.cpp | dev-only |
| Orchestration | Dagster | — | Apache-2 |
| Durable workflows | Temporal (**deferred to contract-demand**) | Dagster sensor | **Temporal Cloud metered** |
| CDC/stream | Debezium + Kafka (Phase 2) | outbox-polling (Phase 0–1) | **MSK/Confluent monthly floor** |
| Identity | Keycloak + CILogon/eduGAIN | Ory | **CILogon commercial quote — Q10** |
| Secrets/keys | **Cloud KMS per-tenant** + CloudHSM; HYOK | self-run Vault (sovereign only) | **NOT Vault Community namespaces (Enterprise-only)** |
| Scholarly/grant data | OpenAlex CC0 snapshot + Crossref + ROR + **ORCID CC0 dump** + S2/SPECTER2 + Grants.gov/RePORTER/NSF | live polite-pool APIs (freshness only) | **ORCID live API non-commercial; OpenAlex live API metered — both avoided on hot path** |
| IaC/orchestration | Terraform + Kubernetes | — | — |
| Eval | RAGAS in CI | — | — |
| Frontend | Next.js + React | — | — |

(Engine choices are insulated behind §5.8 interfaces; the central-index privacy bound is pinned to `IIndexProfile`, so swaps are gated.)

---

## 13. Deployment & Infrastructure

### 13.1 Topology (D7 pooled-vs-dedicated)
Control plane (US + EU regional instances) + **per-tenant/per-region confidential data-plane cells** + a **multi-tenant POOLED plane for all non-confidential workloads (PLG, public discovery) — D7.** Each confidential cell: isolated namespace, per-tenant KMS/HYOK, SpiceDB replica + lease cache, vector/graph/lexical stores, in-boundary vLLM, per-stream audit. **Dedicated isolation cost lands ONLY on the priced confidential tier**; PLG and public discovery share pooled infra (resolves Triage C5 — PLG cannot afford a dedicated GPU cell).

### 13.2 Managed vs self-host
- **Phase 0–2 = MANAGED-cell-only (startup-operated).** No installer, no field SRE.
- **Customer self-host (on-prem / customer-cloud) = an explicitly-deferred, separately-priced edition with its OWN engineering line** (installer, upgrade CD, version-skew management, support SLA) that does **not** exist until Phase 2+.
- **Export/CMMC/sovereign buyers most often mandate self-host AND export-conformant cells (§11.6); deferred until that line is funded.** We do not promise these buyers in Phase 0–1.

### 13.3 Hot-tenant cell-split protocol
The largest anchor-center site is provisioned in a **DEDICATED cell from day one** — so we never split it; a **per-cell tenant-size ceiling is stated.** When cell-split is needed (Phase 2), it is a specified migration protocol: how SpiceDB relationships + revision/lease tokens migrate **without breaking monotonic reads**; how the CDC stream is fenced/replayed; how active revocations are quiesced/carried across the cut.

### 13.4 Per-tenant cost shape (D7)
Each confidential cell's cost is `f(N, corpus-size)` (§14.2/§16), priced so **institutional/center ACV ≥ 2–3× per-tenant COGS.** Pooled PLG/public infra cost is amortized across all individual users (near-zero marginal per-user GPU on shared/burstable).

### 13.5 IaC/k8s posture
Terraform + k8s; per-cell Helm release; GitOps; **persistent cloud GPU staging** for confidential-path tests (§15), not the M4 Max.

---

## 14. Scalability & Reliability

### 14.1 Consistency model (D5)
Hot path = **local reads** (owner-node lease + cell-local cached authz); consensus is **never on the confidential read hot path** (D5). Per-tenant **noisy-neighbor quotas + fair-scheduling on shared-index write/query and shared-cell GPU/RAM (Triage item 12, C21d)** prevent a hot tenant from starving the pooled plane.

### 14.2 Central index/graph growth model — costed in the body (Triage item 9, C21a)
**The central index/graph is SHARDED + replicated (NOT a single managed instance).** Hybrid topical-macro + per-tenant sub-partition; a tenant's bitmap stays in a bounded shard set with per-shard admission control. **Ownership decision: self-managed sharded Qdrant + sharded property graph on k8s, owned by the ML/RAG engineer; managed (Qdrant Cloud) is the fallback once ops load exceeds 0.5 FTE.**

**Growth model (public-tier only — confidential never centralizes, D6):**

| Scale | Papers/profiles (public) | Embedding bytes (1024-dim fp16 ×2 models) | Graph nodes/edges | Index store (est.) |
|---|---|---|---|---|
| N=10 | ~5M | ~20 GB | ~15M / ~80M | ~60–100 GB |
| N=50 | ~25M | ~100 GB | ~75M / ~400M | ~300–500 GB |
| N=200 (R1) | ~80–100M | ~320–400 GB | ~300M / ~1.6B | ~1.2–2 TB |

- **Single-instance break point ~300–500 GB (N≈50) = the named trigger to shard.**
- **Whole-corpus re-embedding** (model upgrade) = multi-day GPU job scaling **linearly with corpus size**; **recurring cost modeled as f(corpus-size × upgrade-cadence)** and gated by `IIndexProfile` re-validation — **in the COGS model (§16), not the appendix.**
- **Topical-shard skew (Triage item 11, C21c):** OpenAlex topics are power-law; we **cost the skew + the re-clustering/re-embedding migration on synthetic OpenAlex** (Q7) and **do NOT assert "few shards per query"** — hot topics get sub-partitioned with admission control.
- **AGE multi-hop/PPR benchmarked at N=200 scale before lock** (Q6, §9.2); Neo4j/Memgraph fallback behind `IGraphStore` conformance.

### 14.3 Bottlenecks & levers
| Bottleneck | Lever |
|---|---|
| Revocation write throughput | local fenced counter + tombstone coalescing; published revocations/sec ceiling (§4.6) |
| Audit append | per-stream parallel chains (§11.4) |
| Central index size | shard at N≈50; per-shard admission control (§14.2) |
| Hot tenant | dedicated cell day one + cell-split protocol (§13.3) + noisy-neighbor quotas (§14.1) |
| Brokered drill-down latency | deadline propagation + circuit breakers (§4.3) |
| PSI scaling | Phase-1 usability spike; pairwise PSI is **O(N²)** — bounded set sizes; **documented fallback: k-anonymized bucketed overlap via the central index** (not architecturally PSI-dependent) |

### 14.4 Failure domains (bounded per D5)
Per-cell isolation = blast-radius containment. **Control-plane partition → TTL-bounded confidential degradation then deny, scoped to the affected owner cell only** (D5 — no global authority to take down). Gray-failure (slow owner node) → circuit-breaker trip at deadline boundary (§4.3). One shard down → bounded fraction of public discovery degraded with honest completeness flag (§9.4).

### 14.5 SLOs
- Grounded proposal-drafting Q&A (Phase 0): **p95 < 4s.**
- Federated discovery / team assembly (Phase 2): **p95 < 800ms** under continuous ingest (**index-path SLO**).
- Confidential brokered drill-down: **composite p99 < 6.5s** (**brokered-path SLO, separate; honest compound availability published — §4.4**).
- Revocation hot-path read (owner-node local lease): **p99 < 15ms.**
- Confidential allow-window = **lease-TTL (2s default; 0 for security-reason).**
- share→discoverable **≤ 30s**; revoke→undiscoverable hit-filter **immediate**, index-removal **≤ 30s.**

---

## 15. Observability, Testing & CI/CD

### 15.1 Telemetry
OpenTelemetry traces across cells + control plane; **deadline propagation surfaced in traces**; per-cell SLO dashboards; revocation-propagation lag metric; index-staleness metric; per-path (index vs brokered) availability dashboards.

### 15.2 Testing strategy (Triage item 17)
- **Consumer-driven contract tests (Pact-style) between EVERY cell and the Exchange — a CI gate** (both sides' expectations versioned).
- **Property-based tests (invariants):** TierLattice **MAX-rule**, sticky-flag **UNION**, **source-class re-derivation** — generate random tier/flag combinations, assert the published projection NEVER exceeds source class; assert **ABAC narrows-only, never widens.**
- **Deterministic simulation tests** (injected-clock + partition harness): clock-skew, owner-node partition, revoke-ordering, bulk-revoke saturation — **run EVERY CI.**
- **Eval-in-CI** (RAGAS) as a retrieval-quality release gate.
- **Confidential-path tests run against a vLLM container in CI + cloud GPU staging — never the M4 Max** (Ollama is UI/pipeline dev only).
- **Security contract tests:** zero-leak adversarial classifier; broker-over-assert-denied; grantee-over-assert-denied; replayed-token-for-revoked-grant-denied; foreign-person-completion-redacted; subject-deprovisioned-denied (all tiers); PLG-cannot-construct-confidential/exchange; missing-ABAC-attr→deny.

### 15.3 Release / rollback
GitOps; per-cell canary; lattice changes are **additive + two-phase (recognize-before-emit, §5.6)** so rollback never strands records; index changes are versioned + recallable (§5.6/§11.2).

---

## 16. Cost Model & Team

### 16.1 Per-service monthly floor table (D7 pooled-vs-dedicated)

| Service | Idle floor (N=1 confidential cell) | N=5 | Notes |
|---|---|---|---|
| Managed confidential cell compute + storage | ~$1.2k/mo | ~$5k/mo | |
| vLLM GPU (confidential inference) | ~$1.5k/mo (**shared/burstable** Phase 0) | ~$4k/mo (dedicated, confidential tier only) | **Pooled/burstable Phase 0**; dedicated reserved for confidential tier (D7) |
| Vector/graph/lexical (sharded public index, shared) | ~$0.5k/mo | ~$2k/mo | shard at N≈50; **re-embed = f(corpus×cadence)** |
| SpiceDB (self-host) | ~$0.3k/mo | ~$1k/mo | managed AuthZed avoided early |
| Kafka/CDC | $0 (Phase 0 — outbox) | ~$1k/mo (Phase 2) | deferred |
| CloudHSM (per-cell local authority + checkpoints) | $0 (Phase 0) | ~$2–4k/mo (Phase 2) | D5 = local authority per cell; no 3-region consensus authority |
| KMS (per-tenant cloud KMS) | ~$0.1k/mo | ~$0.3k/mo | cloud KMS default (§11.3) |
| **Per-confidential-tenant COGS** | **~$1.5–2.5k/mo (≈$18–30k/yr)** | | pooled PLG/public ≈ near-zero marginal per individual |

### 16.2 Unit economics reconciled (D7, Triage item 21, C4)
- **Kill-gate floor ASP = ≥ 2–3× modeled per-tenant COGS.** At ~$18–30k/yr COGS, the floor is **≥$120k/yr ACV** for the anchor consortium (Gate A, §3.3). The **$179/mo PLG tier is a loss-leader funnel, never the margin driver.**
- **Pooled non-confidential + dedicated-only-for-confidential (D7)** collapses fixed cost; dedicated GPU is reserved for the confidential tier whose price carries it.
- **Result:** contribution margin positive (~$120–250k ACV vs ~$18–30k/yr per-cell COGS) → **explicit Gate condition: ≥60% gross margin per confidential deal**; per-cell gross-margin floor enforced.
- **Phase-0 is a funded-loss validation phase** covered by seed until logos × ACV clears burn.

### 16.3 Monthly-burn model vs revenue (Triage item 22, C23)
- **Burn (loaded):** 3 founding eng @ ~$18k/mo = **$54k**; GTM founder $16k; **fractional GRC + counsel $12k**; managed-service + GPU floors $6k; **discrete compliance-cash line (SOC2 auditor, pen-test, Vanta/Drata) ~$6k/mo amortized.** ≈ **$94k/mo.**
- **Seed assumption: $3.0M → ~32-month runway.** Headcount ramp: 3 eng Phase 0; +security-eng/SRE + consortium-BD before Phase 1.
- **Logos to cover burn:** at $120k ACV, **~9–10 logos** cover $94k/mo; **Phase-0 target = anchor center + 2–4 paid sandbox→production logos** (funded-loss until then).
- **First-dollar / first-recurring overlay:** first paid sandbox ≈ month 3–6; **first regulated recurring close budgeted as a 6–9 month FOUNDER-LED motion** (conservative date in the runway model, not "fast sandbox cash"). SOC2 Type I sequenced at the Phase-0/1 boundary against this reality.
- **Phase-1 federation-build start tied to a runway checkpoint (≥18 months remaining) AND a confirmed anchor center**, not just "a second node."

### 16.4 Pilot→recurring conversion
Sandbox-pilot → recurring = **50% within 4 months** (validated, Q18). A **founder owns the regulated GTM motion full-time**; the hired GTM person is support.

### 16.5 Founding team

| Role | Phase-0 focus | Scale-up |
|---|---|---|
| **Eng — distributed systems** | per-schema/DB-role isolation, per-stream hash-chain audit + checkpointer, **owner-node-local revocation authority (D5)**, Dagster classify-gates-index + outbox-polling, transport egress block, KMS wiring | → lease-based multi-region replication, SpiceDB replication fork, CDC, cell-split protocol |
| **Eng — ML/RAG** | retrieval planner (single-shot hybrid+rerank), provider-registry router, embeddings/serving, RAGAS-in-CI (GPU-staging judge), quarantine hard-exclusion, **public-tier expert discovery over OpenAlex + grant-opportunity match**; owns sharded-index ops + snapshot-drift | → planner strategies, bounded team assembly, AGE/PPR + GNN |
| **Eng — security/infra** | single fail-closed classifier + abstention-quarantine + human-review queue, **single PEP (D4) + policy-table router + hard-fail**, KMS/HYOK, k8s/IaC, vLLM CI container + cloud GPU staging | → egress PEP + projection + dual classifier + 2-cell seam; security-eng/SRE split; TEE later |
| **GTM founder / domain** | **owns regulated/anchor-consortium sales full-time** (two kill-gates + first close); pricing/veto-graph mapping | → enterprise field sales |
| **Consortium/alliance BD** | (before Phase 1) | dyad + consortium monetization |
| **Fractional GRC + counsel** | FERPA/GDPR/ITAR review + DPA/DUA/SCC templates ≈ 20 hrs/wk; HECVAT pre-fill (**not** the GTM founder); SOC2 prep scoped to demand (§11.9) | — |

---

## 17. Risks & Mitigations

| # | Risk | Type | Mitigation |
|---|---|---|---|
| R1 | Federation-seam confidentiality leak (existential) | Tech | Single PEP chokepoint (D4) + structural PublishableProjection + MAX-rule incl. codes; confidential never in index (D6); membership red-team = pre-write design gate on synthetic data (§11.2) |
| R2 | Revocation fail-open | Tech/Comp | Owner-node local-lease deny-correct (D5/§4.4); synchronous for security-reason regardless of tier (§4.5) |
| R3 | Clock-skew ordering | Sec | Owner-cell local fenced counter; over-skewed node fails-closed-deny + alarm (§4.6) |
| R4 | Owner-node authority partition | Reliab | Local-lease reads → TTL-bounded degradation scoped to one cell (D5), not global outage; published deny-minutes/yr (§4.4) |
| R5 | Embedding inversion / membership / linkage | Sec | Cross-tenant linkage in threat model; bound proven on synthetic BEFORE real embeddings; ε/k/churn in contracts; rollback (§11.2) |
| R6 | Per-shard incomplete covert channel | Sec | Partial-results+honest-completeness for public path; whole-fail-closed confidential only; recall impact quantified (§9.4) |
| R7 | Confused-deputy / cross-tenant IDOR | Sec | Owner-side re-derivation UNIVERSAL invariant; grant-ID lookup; audience-bound single-use DPoP tokens (§4.3) |
| R8 | Export access via unverified nationality | Comp | Institution-attested US-person signed grantor caveat, never SSO attribute (§11.5/C15) |
| R9 | Deemed export via operational access | Comp | Export-conformant cells only (US-person ops + US-region + TEE); router refuses placement; opt-in-per-project (FRE) (§11.6) |
| R10 | Audit operator-rewrite (insider/compelled) | Comp | External chain-head anchoring + fair-exchange receipts + divergence freeze (§11.4/C17) |
| R11 | Subject deprovisioned but served | Sec | All-tier + discovery-PEP freshness check, first-class in PEP flow (§7.4/C18) |
| R12 | Classifier misclassification (root leak) | Sec | Quarantine-on-abstention Phase 0 + adjudication; adversarial zero-leak test (§11.1) |
| R13 | TierLattice barrier / heterogeneous lattice | Maint | Additive + default-deny + two-phase recognize-before-emit; min-node-version unknown→most-restrictive; NO all-attest barrier (§5.6/C13) |
| R14 | Modularity vs confidentiality coupling | Maint | Single PEP chokepoint (D4) = modules inherit enforcement; import-linter forbids raw-store access (§4.2/C10) |
| R15 | Event-contract / distributed monolith | Maint | Versioned domain events from Phase 0; per-schema+DB-role isolation; CDC only for own read-store (§5.2/C15-maint) |
| R16 | SpiceDB cell-local replication = bespoke | Tech | Go/no-go fork, Week-1 measured against actual primitives; fallback cell-local cached authz (§7.5/C7) |
| R17 | Defensibility race lost | Market | Data-gravity at N=2 + network effect + cert depth; incumbent time-to-replicate 4–6 quarters; **fallback moat = network-effect lock-in if race window unmet** (§1); regulated-niche down-scope is PRIMARY plan-B |
| R18 | Incumbent (Atom Grants) adds thin private tier | Market | Not resting on inaction; data-gravity + cert depth raced; quantified replicate window (§1) |
| R19 | Phase-0 undifferentiated (commodity secure-RAG) | Market | Wedge = grant intelligence (D1); ONE federation differentiator in Phase 0 = cross-institution PUBLIC-tier expert discovery over OpenAlex + grant-opportunity match (§3.2/C1 item 20) |
| R20 | WTP < COGS | Business | Floor ASP ≥2–3× COGS (≥$120k); pooled non-confidential + dedicated-only-confidential (D7); ≥60% margin gate (§16/C4) |
| R21 | Cold-start (federation network effect) | Market | Anchor on existing federally-funded center + its DUA (D3); hard Phase-1 entry gate (§3.4/C2) |
| R22 | Phase 1 = multi-year monolith | Execution | Decomposed into 1.0/1.1/1.2 sub-phases with own gates (§18); owner-local authority first; Temporal/Cedar/fair-exchange deferred to contract-demand (C22) |
| R23 | Phase-0 not buildable by 3 eng | Execution | Engineer-weeks per item (§18); thin PEP over RBAC, append-only audit (defer hash-chain), classification column + if/else router, Dagster only, outbox-polling; HYOK deferred to first-real-confidential-data customer; ~6-month calendar (C22) |
| R24 | Self-host/per-node ops uncosted | Cost | Phase 0–2 managed-only; self-host separately-funded Phase-2+; export/sovereign deferred until funded (§13.2) |
| R25 | Compliance cash trap | Cost | Discrete compliance-cash line in burn; SOC2 Type I first, buyer-demand-driven, deferrable to Phase-0/1 boundary (§11.9/§16.3/C23) |
| R26 | Over-engineered governance machinery | Execution | Conformance attestation / deprecation lifecycle / version-matrix deferred to N≥5 (§5.7) |
| R27 | Central index growth uncosted | Tech/Cost | Growth model + dollar line in body; sharded at N≈50; re-embed = f(corpus×cadence); ownership assigned (§14.2/C21a) |
| R28 | Four-buyer / PLG reconciliation | Market | $179/mo PLG = explicit loss-leader top-of-funnel; institutional ACV is the anchor (D7); per-buyer table (§2.2) |
| R29 | BYO cost/CAC amplifier | Business | Pre-certified matrix; BYO = higher-touch edition + services attach; fail-closed to in-boundary (§8.3) |
| R30 | Bulk-revoke saturates security lane | Tech | Tombstone coalescing; published revocations/sec ceiling; deny-wider never global-stall (§4.6) |
| R31 | Hot-tenant cell-split brutal | Tech | Largest site dedicated cell day one; split = specified migration protocol (§13.3) |
| R32 | GPU dev parity (Mac ≠ vLLM+TEE) | Execution | Confidential-path CI on vLLM container + cloud GPU staging; M4 Max = UI/pipeline only (§15.2) |
| R33 | Procurement stalls pilot | Execution | Sandbox/de-identified pilot; Week-1 written confirmation a paid sandbox can sign without full review/BAA (hard gate sub-condition, Q17) |
| R34 | AGE multi-hop/PPR fails at scale | Tech | Synthetic benchmark at N=200 before lock; Neo4j(GPLv3-isolated)/Memgraph(BSL) fallback behind IGraphStore conformance (§9.2/C21b) |
| R35 | Topical-shard skew / re-cluster cost | Tech/Cost | Costed on synthetic OpenAlex; hot-topic sub-partition + admission control; no "few shards" assertion (§14.2/C21c) |
| R36 | GDPR/FERPA erasure unmet by crypto-shred | Comp | Per-subject hard-delete + tombstone + Art. 19 notification distinct from KEK-shred (§11.7/C20) |
| R37 | Vault unseal/namespace toil | Cost/Ops | Cloud KMS per-tenant default; self-run Vault sovereign-only; no Community namespaces (§11.3/item 24) |
| R38 | Lease-liveness coupled to re-publish | Tech | Lightweight per-record-version TTL index decoupled from projection re-write; noisy-neighbor quotas (§10.3/§14.1/C21d) |

**Defensible-N (decision).** Defensible at **N≥2 connected nodes within the anchor center's existing legal vehicle + ≥1 accumulated grant history + per-tenant tuned gold-set** (data-gravity), target **N≥5 + ≥1 multi-year consortium by month 24** to clear the 4–6 quarter incumbent window. **Explicit plan-B / down-scope trigger:** if N≥2-with-gravity is not reachable inside the race window on the modeled ramp, trigger the **regulated-niche down-scope (PRIMARY plan-B)** *and* re-state the moat as network-effect lock-in rather than the race (Triage item 23).

---

## 18. Phased Roadmap & Milestones

```mermaid
graph LR
  P0["Phase 0: Single-cell grant-intelligence MVP (proposal grounding + public-tier expert discovery + grant-opp match) + TWO kill-gates (~6 mo)"]
  P0 --> P10["Phase 1.0: 2-node PUBLIC-tier cross-institution discovery + team-assembly (no grants/no authority) — cheap federation-seam proof"]
  P10 --> P11["Phase 1.1: ONE revocable confidential proposal grant + owner-node-local authority (D5)"]
  P11 --> P12["Phase 1.2: lease replication + SpiceDB replication (only if N>2 / SLO demands)"]
  P12 --> P2["Phase 2: Scale federation + sharded central index (privacy-gated in P1) + CDC + SOC2 II + cell-split + export-conformant cells"]
  P2 --> P3["Phase 3: PLG funnel ($179/mo) + full grant team assembly + consortium monetization"]
```

### Phase 0 — Single-cell grant-intelligence MVP (~6 months; engineer-weeks attached)
**Build (walking skeleton, Triage item 18):** single fail-closed classifier + **abstention-quarantine + human-review queue** (4 wk) · **thin PEP over library RBAC** + policy-table router + transport hard-fail (4 wk) · **append-only Postgres audit (defer hash-chain/merkle to Phase 1)** (1 wk) · **per-schema + DB-role isolation** (1 wk) · `mod-lit-intelligence` proposal-grounding retrieval planner (single-shot hybrid+rerank) + RAGAS-in-CI (5 wk) · functional confidential tier: vLLM (shared/burstable GPU), egress-blocked, **cloud KMS per-tenant** (4 wk) · **HYOK DEFERRED to first-real-confidential-data customer** (sandbox uses de-identified data) · **federation differentiator: cross-institution PUBLIC-tier expert discovery over OpenAlex + grant-opportunity match over Grants.gov/RePORTER/NSF** (no confidentiality machinery) (4 wk) · **Dagster ONLY + transactional-outbox-polling** (defer Temporal/Debezium/Kafka) (2 wk) · Direct OIDC · vLLM CI container + cloud GPU staging (2 wk). **NO** second cell, central shared index, egress PEP/projection, dual classifier, hash-chain audit, governance machinery, Kafka, Temporal, TEE, multi-region authority. **Calendar ≈ 6 months for 3 engineers.**
**Gates/Milestones (all Week 1):** **Gate A (anchor ACV ≥2–3× COGS, ≥$120k/yr)** + **Gate B (D3 three-conditions confirmed in writing)** + **Q17 (paid sandbox signs without full review/BAA — written from anchor CISO)** + **Q4-spike (owner-node lease latency + partition deny-minutes)** + **Q5 (SpiceDB replication go/no-go)** · first paid sandbox pilot · grounded Q&A p95<4s · confidential egress-block green (vLLM CI) · router-violation hard-fail green · adversarial-classifier zero-leak test green · RAGAS faithfulness gate green.

### Phase 1.0 — 2-node public-tier discovery + team assembly (cheap seam proof)
**Build:** PublishableProjection (versioned, provenance, MAX-rule incl. codes) + dual classifier + owned TierLattice (additive/two-phase) + per-module schemas + **2-node public-tier federated discovery + cross-institution team-assembly** + consumer-driven contract tests + deterministic-sim harness. **NO grants, NO revocation authority, NO SpiceDB replication** (proves the federation seam cheaply — Triage item 19, C22).
**Milestones:** federation seam green; tier-propagation property tests green; **membership/linkage red-team PASSED on synthetic corpora (pre-write index design gate — §11.2/D6)**; public-tier cross-institution discovery + team-assembly live; **anchor-center DUA + N≥2 + funded need confirmed (cold-start gate, §3.4/D3)**; consortium-BD in place.

### Phase 1.1 — One revocable confidential proposal grant + owner-node-local authority
**Build:** brokered drill-down (owner-side re-derivation, HSM-DPoP, audience-bound single-use) + **owner-node-LOCAL revocation authority (D5 — local fenced counter + lease cache; NO global consensus)** + one revocable confidential proposal grant with sticky caveats + **all-tier subject-deprovision + SCIM session-kill (§7.4)** + revocation-by-reason (§4.5) + HYOK + envelope crypto-shred + export US-person signed-caveat gate + FERPA approval + compliance-flag flow-down + output-channel egress PEP + **hash-chained per-stream audit + external checkpoint anchoring + fair-exchange receipts**. SOC2 Type I (if buyer-demanded). **Cedar ABAC, Temporal = deferred until a contract requires.**
**Milestones:** first dyad confidential proposal co-authored; synchronous-revocation **deny-correct (commit-1s-ago)** + confused-deputy/broker-over-assert + replayed-token + foreign-person-redaction + all-tier-deprovision + missing-ABAC→deny tests green; revocation-by-reason verified; bulk-revoke coalescing verified; per-subject GDPR/FERPA erasure verified.

### Phase 1.2 — Lease replication + SpiceDB replication (only if N>2 / SLO demands)
**Build:** lease replication fabric + cell-local SpiceDB replication+revision-translation (per Q5 verdict) + min-skew enforcement. (D5 keeps authority local; this phase only hardens replication/availability.)
**Milestones:** hot-path lease read p99<15ms; fail-closed-under-partition deny-minutes published (release gate); cross-region drill-down latency table verified against 6.5s SLO.

### Phase 2 — Scale federation + sharded central index + CDC + SOC2 II
**Build:** sharded hybrid topical-macro central index (public/shared only, **privacy-bound proven in P1**, presence DP-noised, per-consortium scope-keys, opt-out default) + materialized public-tier graph (bounded-candidate team assembly, no global PPR) + Debezium/Kafka CDC (per-record key, idempotent-monotonic applier, query-time epoch post-filter, **lease-liveness via TTL index**) + per-shard admission control + noisy-neighbor quotas + re-clustering/re-embedding tooling + brokered-path circuit-breakers + **gray-failure injection test** + zero-copy confidential workspaces + HippoRAG2 PPR (post-AGE-verdict) + GNN team-assembly (data-gated) + Qdrant/OpenSearch shard split + **hot-tenant cell-split protocol** + PSI (post Phase-1 usability spike) + k-anon-bucketed-overlap fallback + GDPR joint-controller arrangements + key-rotation-on-offboarding + SOC2 Type II + **export-conformant cell line + self-host edition engineering line (separately funded)** + governance machinery (N≥5).
**Milestones:** N≥5; discovery p95<800ms under ingest; gray-failure circuit-breaker verified; central-index privacy re-validated post-scale; SOC2 Type II; PSI useful within DP ledger (or fallback shipped); cell-split exercised on synthetic; AGE/PPR benchmark verdict acted on; **defensible-N reached.**

### Phase 3 — PLG funnel + full grant monetization
**Build:** **PLG self-serve $179/mo** (public + own-materials, **loss-leader top-of-funnel — D7**) + `mod-funding` full (grant intelligence + bounded-candidate team assembly + budget/compliance) + capped tier-pinned multi-agent (PEP-on-every-action) + per-tenant learned fusion + ISO 27001 (EU) + multi-axis pricing.
**Milestones:** ≥2 consortia under multi-year contracts (or framework LOIs signed in Phase 0–1 per Triage item 23); first cross-institution grant team assembled + funded.

---

## 19. Open Questions & Decisions to Validate

*Locked by D1–D7: grant-intelligence wedge; anchor on existing federally-funded center + DUA; single PEP chokepoint; owner-node-local fail-closed authority (no global consensus); confidential never in shared index + pre-write red-team gate; quarantine-on-abstention default-deny; ACV ≥2–3× COGS with $179/mo PLG loss-leader; pooled non-confidential + dedicated confidential.*

1. **Gate A — anchor-grant-wedge demand (Week 1, HARD):** anchor RD office writes **ACV ≥2–3× COGS (≥$120k/yr)** vs a grant-program budget line; funds a paid sandbox. *Fail → pivot.*
2. **Gate B — federation/cold-start basis (Week 1, HARD):** D3 three conditions (existing DUA + N≥2 sites + recurring funded need) confirmed in writing. *Fail → Phase 1 is an independent kill-gate.*
3. **Anchor-center selection (before Phase 1, HARD):** named center meeting all four selection criteria (§3.4).
4. **Owner-node lease latency + partition deny-minutes (Phase-1 spike, RELEASE GATE):** measure local-lease read p99 + publish measured confidential deny-minutes/year at realistic partition rates — measured, not target.
5. **SpiceDB replication go/no-go (Week 1):** can ZedToken→local-revision guarantee monotonic reads under measured lag against actual primitives? If no → cell-local cached authz + confidential-subset sync re-check (§7.5).
6. **AGE multi-hop/PPR at R1 scale (synthetic):** benchmark at N=200 graph; exercise Neo4j/Memgraph switch via IGraphStore conformance (§9.2/§14.2).
7. **Index skew/drift/bitmap locality (synthetic OpenAlex):** topical concentration of corpus AND queries; bounded shard set; re-cluster/re-embed cost (§14.2).
8. **Central-index privacy red-team (Phase-1 pre-write DESIGN GATE, on synthetic):** membership-inference + embedding-inversion + cross-tenant linkage; ε/k/churn bound in `shared/contracts/`; rollback procedure.
9. **Central graph cost + team-assembly quality at N=10/50/200:** validate sharding triggers + bounded-candidate assembly.
10. **CILogon cost & eduGAIN/SAML brokering effort:** hard quote; engineer-weeks for SAML (gates campus/consortium buyers).
11. **PSI usability + scaling (Phase-1 spike):** pairwise O(N²) vs multiparty; bounded sets; confirm k-anon-bucketed fallback returns useful answers.
12. **Export-control operational surface (officer):** US-person ops + US-region + TEE conformance accepted; operational-access covered; opt-in-per-project FRE preserved.
13. **GDPR controllership + transfers + lawful basis (DPO):** EU-region pinning; is opt-out-default defensible for EU subjects or is opt-in/legitimate-interest-balancing required?; per-tier/per-reason max-staleness for withdrawn consent.
14. **FERPA gating + flow-down (registrar):** owner-side + role re-check + sticky flag + audit authz sufficient; per-tier/per-reason allow-window acceptability.
15. **BYO endpoint verification + sovereign-tier definition:** in-boundary proof + mTLS + TEE-attestation matrix per pre-certified cloud.
16. **PMC/Europe PMC OA-subset:** commercial-OK filter yields a usefully large corpus; ingestion/embedding cost line.
17. **Procurement (HARD Week-1 sub-condition):** named anchor CISO/contracts officer confirms **in writing** a paid sandbox pilot can sign **without full vendor security review / BAA.** If not → re-baseline runway against full-review cycle.
18. **Runway/conversion (validate):** sandbox→recurring % and months; founder-led 6–9 month first-close; consortium-BD before Phase 1.
19. **TEE deployment surface:** Nitro vs SEV-SNP/TDX abstraction + attestation; spike when first export-class buyer's threat model demands.
20. **Eval gold-set bootstrapping per tenant:** built inside the cell, who labels; GPU-staging judge cost.
21. **PLG locked-requirement sign-off:** confirm "individual PIs as PLG top-of-funnel" at $179/mo is a loss-leader acquisition channel (per D7), not standalone revenue — surface now if a stakeholder disagrees.
22. **Race-window vs network-effect moat (Triage item 23):** decide in Phase 0–1 whether to compress (sign multi-year framework LOIs with the anchor + one peer consortium early) or formally replace the race-window defensibility claim with network-effect lock-in.
23. **Vault/KMS isolation (Triage item 24):** confirm cloud-KMS per-tenant keys satisfy the anchor's key-isolation requirement; reserve self-run Vault for sovereign/on-prem only (no Community namespaces).

---

*End of plan v6 (re-anchored). Headline changes from the prior draft, driven by the locked decisions: the wedge is now **grant intelligence** (D1) — proposal grounding, cross-institution team assembly, confidential proposal co-editing, and funding match are the **decomposition of one grant workflow** (D2), not four separate products; the day-one buyer is **one existing federally-funded multi-site center with an in-force DUA, N≥2 sites, and a recurring funded need** (D3), collapsing the cold-start gap; confidentiality is enforced through a **single PEP + data-access broker chokepoint** (D4) so feature modules never re-implement enforcement; the **owning node is the sole local fail-closed revocation authority with NO global consensus on the hot path** (D5) — the confidential read is a ~15ms local lease read and a control-plane partition is a TTL-bounded degradation scoped to one cell, not a global outage; **confidential content never enters the shared index** and the membership-inference/embedding-inversion/linkage red-team is a **pre-write gate on synthetic data** with classifier-abstention defaulting to quarantine (D6); and unit economics are anchored on **institutional ACV ≥2–3× per-tenant COGS (≥$120k/yr) with the $179/mo individual tier as an explicit loss-leader funnel**, non-confidential workloads pooled and dedicated isolation reserved for the confidential tier (D7). Every FIXABLE-GAP (C15–C20 enforcement details, C21 scale/cost models, C22 walking-skeleton phasing, C23 burn model) is implemented in the body, and every ACCEPTED-TRADEOFF (C12 processor-not-zero-trust, C13 compound brokered availability, C14 cross-region latency table) is written down explicitly.*