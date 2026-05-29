# Research: federation-compliance

I now have all the load-bearing material grounded in authoritative sources. Writing the final report.

# Federated Multi-University Research Platform: Multi-Tenancy, Federation, Access Control, Residency, Compliance & Reliability

A production-architecture research brief. Each section separates **production-ready-today** from **research-only / emerging**. The final section gives the recommended federated-hybrid design.

---

## 1. Multi-Tenancy Isolation Models

### 1.1 The three canonical models (silo / pool / bridge)

AWS's SaaS Lens defines the industry-standard taxonomy. The choice is not global — it is made **per microservice / per data store**, driven by the regulatory profile and noisy-neighbor characteristics of that component.

| Model | What it is | Isolation | Cost | Ops complexity | Blast radius |
|---|---|---|---|---|---|
| **Silo** | Each tenant gets dedicated resources (own DB / own stack), but shares identity, onboarding, and operational tooling | Strongest | Highest | Highest (N stacks to patch/monitor) | Smallest (one tenant) |
| **Pool** | Tenants share infrastructure (compute, storage, queues); isolation enforced logically (e.g., `tenant_id` + RLS) | Weakest | Lowest | Lowest | Largest (a bug exposes all) |
| **Bridge** | Mixed: shared web/API tier (pool) + per-tenant business logic + storage (silo); chosen per service by data sensitivity | Tunable | Medium | Medium | Tunable |

Key nuance: a silo still shares the **control plane** (identity, onboarding, ops) — this is what makes it SaaS rather than N managed single-tenant installs. AWS explicitly recommends steering a microservice to silo when "the regulatory profile of a service's data and its noisy-neighbor attributes" demand it, and to pool when "agility, access patterns, and cost profile" dominate.

**Implication for this platform:** confidential research data is exactly the "regulatory profile" case → **silo the confidential data plane per university**; pool the public/discovery surface. This is the bridge model, and it maps directly onto the locked "federated hybrid" deployment.

- AWS Well-Architected SaaS Lens — Silo, Pool, Bridge: https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html
- AWS SaaS Tenant Isolation Strategies (bridge): https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/the-bridge-model.html
- AWS Guidance for Multi-Tenant Architectures: https://aws.amazon.com/solutions/guidance/multi-tenant-architectures-on-aws/

### 1.2 Postgres Row-Level Security (RLS) pitfalls — the pooled-tier landmines

RLS is the standard pooled-isolation mechanism, but it is **defense-in-depth, not a primary boundary** for confidential data. Concrete, verified footguns:

- **Table owner & `BYPASSRLS` bypass by default.** `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` does *not* restrict the table owner or superusers. You must add `ALTER TABLE ... FORCE ROW LEVEL SECURITY`. The classic false-confidence failure is **testing as a superuser/owner**, where RLS appears to work but is silently ignored.
- **Connection-pooling context leak (the worst one).** Using `SET app.tenant_id` (session-scoped) instead of `SET LOCAL` (transaction-scoped) leaves the tenant context attached to a pooled connection; with PgBouncer/transaction pooling the *next request reuses that connection and inherits the previous tenant's context*. Always `SET LOCAL` inside the same transaction.
- **`USING` vs `WITH CHECK`.** `USING` filters rows you can read (SELECT/UPDATE/DELETE); `WITH CHECK` validates rows you write (INSERT/UPDATE). Omitting `WITH CHECK` lets a user **INSERT rows they can't even see** — including rows tagged with another tenant's ID.
- **Permissive policies are OR-ed.** Multiple `PERMISSIVE` policies union together; one broad policy silently overrides a stricter one. Use `RESTRICTIVE` policies for hard constraints.
- **Performance: missing leading index + non-`LEAKPROOF` functions.** `tenant_id` must be the **leading column** of primary access indexes or RLS adds a filter that can be ~2 orders of magnitude slower. Non-`LEAKPROOF` functions in a policy force Postgres to apply RLS filtering before the function, defeating index usage — turning millisecond queries into table scans.
- **RLS filters rows, not columns.** Sensitive columns remain visible in permitted rows. **Materialized views and `SECURITY DEFINER` views bypass RLS** (a view runs with creator privileges), so they can contain/leak all tenants' data.

**Verdict:** RLS is production-ready for the *public/private* pooled tier as a second layer behind app-level scoping. It is **not** sufficient as the sole boundary for *confidential* data across organizations — that needs silo-level (separate DB/schema/node) isolation. Pool isolation "offers the least tenant isolation."

- AWS — Multi-tenant isolation with Postgres RLS: https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/
- Bytebase — RLS footguns: https://www.bytebase.com/blog/postgres-row-level-security-footguns/
- Bytebase — RLS limitations & alternatives: https://www.bytebase.com/blog/postgres-row-level-security-limitations-and-alternatives/
- Crunchy Data — RLS for tenants: https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres

### 1.3 Data-residency implications of the isolation choice

Silo's strongest payoff is residency/sovereignty: a per-tenant data plane can be pinned to a region or run on-prem in the university's own infra, while a shared control plane stays global (see §4). Pool tiers, by contrast, co-mingle data and are hard to pin per-tenant — so **anything residency-sensitive must be siloed**.

---

## 2. Federation vs Centralization for Cross-Org Discovery

The core constraint: University A must discover relevant experts/work at University B **without B's confidential data being centralized**. Three families of architecture, ranked by what's practical today.

### 2.1 Architectural patterns

**(a) Federated (live) search — query fan-out, no central copy.** A query is sent live to each participating node; each node answers from its own store and returns only what its sharing policy permits; the broker merges/ranks. Best for "decentralized, real-time data... without duplicating or moving it," and is the pattern used in "highly regulated industries... to maintain strict control over data location." Trade-offs: tail latency = slowest node; no global relevance ranking; every node must be online; ranking fusion across heterogeneous scorers is hard.

**(b) Central metadata-only index + pointers (recommended core).** Each node publishes **only shareable metadata** (titles, abstracts, public profiles, embeddings of *publishable* text, capability tags) to a shared index; the index holds **pointers, not confidential content**. Discovery search runs centrally (fast, single relevance ranking, pre-computed embeddings/NLP), and any drill-into-detail is brokered back to the owning node under an access check. Trade-off: needs ingestion pipelines + sync + staleness monitoring — but it never holds confidential bytes.

**(c) Publish/subscribe of shareable records.** Nodes emit events for records they choose to share (or that change sharing state); the exchange fans out to subscribers. This is the eventual-consistency backbone for (b) — see §6.

**(d) Data clean rooms — for confidential *joint computation*, not discovery.** A neutral environment where multiple parties compute over combined data without exposing underlying rows: zero-copy/"execute query where data resides," aggregation thresholds, query-frequency caps, and pre-approved query templates. This has moved "from enterprise niche to general-purpose capability" in Databricks, AWS Clean Rooms, BigQuery, Snowflake, Azure Confidential Clean Rooms. **Production-ready** and the right tool for Feature 3 (secure shared workspaces) and confidential cross-institution analytics — overkill for ordinary discovery.

- Moveworks — Federated vs indexed search: https://www.moveworks.com/us/en/resources/blog/federated-vs-indexed-search-enterprise-guide
- Splunk — federated search: https://www.splunk.com/en_us/blog/learn/federated-search.html
- Systemoverflow — centralized vs federated catalog trade-offs: https://www.systemoverflow.com/learn/data-lakes-lakehouses/data-discovery/centralized-vs-federated-catalog-architecture-trade-offs
- Decentriq — what is a data clean room: https://www.decentriq.com/article/what-is-a-data-clean-room
- Salesforce Eng — zero-copy clean rooms: https://engineering.salesforce.com/building-data-360-clean-rooms-zero-copy-architecture-for-privacy-safe-data-collaboration/
- Azure Confidential Clean Rooms: https://learn.microsoft.com/en-us/azure/confidential-computing/confidential-clean-rooms

### 2.2 Privacy-preserving discovery primitives — what is practical today

| Technique | What it gives you | Practical today? | Use here |
|---|---|---|---|
| **Confidential computing (AMD SEV-SNP, Intel TDX, AWS Nitro Enclaves)** | Hardware-attested TEE so the operator/cloud can't see in-use data | **Yes — production.** SEV-SNP & TDX are the "two leading technologies dominating" in 2025; VMware Cloud Foundation 9.0 supports both natively; RHEL ships attestation tooling; Nitro Enclaves is the "second-most-deployed primitive, especially for AI inference." | Run the exchange/broker and cross-institution matching inside a TEE so even the platform operator can't read confidential inputs. Caveat: *TEE.Fail* (Oct 2025) forged SEV-SNP/TDX attestations on DDR5 — but requires **physical access + root**, so it's out of scope for a remote-attacker threat model. |
| **Private Set Intersection (PSI)** | Two parties learn *only* their overlap (e.g., shared collaborators, common keywords) without revealing full sets | **Yes for 2-party, bounded scale.** Mature 2-party PSI is deployed (contact discovery, ad measurement). DP-PSI variants bound intersection-size leakage by padding dummies. | "Do A and B have overlapping interests/people?" without sharing rosters. |
| **Differential privacy (DP)** | Aggregate stats with provable per-record privacy | **Yes for aggregates/counts**, with a privacy-budget cost to accuracy. | Publish noisy discovery facets/counts; bound clean-room leakage. |
| **Homomorphic encryption (FHE)** | Compute on ciphertext without decrypting | **Mostly research / narrow.** Most 2025–26 production uses **partial/somewhat-HE on specific high-value workloads**, not general FHE; large ciphertexts, expensive bootstrapping, hard parameter selection. TPU/AI-accelerator work (Cornell/Google/MIT/GT, Jan 2025) dropped overhead orders of magnitude but it's still significant. | **Do not** put on the critical path; pilot only for a narrow encrypted-match feature. |

**Practicality ranking for this product:** TEEs (production) > clean rooms (production) > 2-party PSI + DP (production, bounded) > FHE (research/narrow). Design discovery around **metadata-only index + TEE-protected broker + clean rooms for confidential joins**, and treat PSI/DP as targeted features, FHE as future R&D.

- AMD SEV-SNP vs Intel TDX (2025): https://onidel.com/blog/amd-sev-snp-vs-intel-tdx-vps
- Red Hat — Nitro Enclaves confidential computing: https://www.redhat.com/en/blog/deploy-confidential-computing-aws-nitro-enclaves-red-hat-enterprise-linux
- ACM — Nitro Enclaves for DB workloads: https://dl.acm.org/doi/full/10.1145/3736227.3736234
- DP-PSI paper: https://arxiv.org/abs/2208.13249
- Efficient DP set intersection: https://eprint.iacr.org/2024/1239
- PSI overview (Wikipedia): https://en.wikipedia.org/wiki/Private_set_intersection
- FHE practical guide (2025): https://www.shadecoder.com/topics/fully-homomorphic-encryption-a-comprehensive-guide-for-2025
- FHE (Wikipedia): https://en.wikipedia.org/wiki/Homomorphic_encryption

---

## 3. Data Classification + Cross-Org Access Control

### 3.1 The model spectrum

- **RBAC** — permissions via roles. Simple; suffers **role explosion** and can't natively express per-resource, per-project, cross-institution grants.
- **ABAC (NIST SP 800-162)** — decisions evaluate Boolean **policies over attributes** of subject, object/resource, action, and environment. RBAC/ACL are special cases of ABAC (role-attribute / identity-attribute). Reference architecture (XACML): **PEP** (enforce) → **PDP** (decide) → **PAP** (author policy) → **PIP** (fetch attributes). Ideal for expressing *classification* (`object.tier ∈ {public,private,confidential}`), residency, export-control flags, and consent state as attributes.
- **ReBAC / Zanzibar / OpenFGA** — decisions via **relationship tuples** `object#relation@user` with userset-rewrite rules (union/intersection/exclusion). Answers "*how is this user related to this resource?*" Excels at **sharing graphs**: per-project membership, group-based access, hierarchical inheritance (lab → project → document), and exactly the cross-tenant sharing-grant pattern ("when you attach a Drive link in Gmail, Gmail checks recipient access"). Google's Zanzibar serves 95% of checks <10ms at 99.999% availability. **OpenFGA** (CNCF incubating, Zanzibar-inspired) is the production-ready open implementation and **combines ReBAC + ABAC**.

### 3.2 Recommended hybrid: ReBAC for relationships, ABAC for classification/compliance

Neither alone is enough. Model:
- **Classification & compliance as ABAC attributes/conditions:** `tier`, `residency_region`, `export_controlled (ITAR/EAR)`, `contains_PHI`, `IRB_DUA_id`, `consent_status`, `grant_expiry`. These gate *whether* a relationship even counts (e.g., "viewer relation is void if `export_controlled && subject.is_foreign_national && no_deemed_export_license`").
- **Sharing as ReBAC tuples:** `project:alpha#collaborator@univB:dr_smith`, `document:x#parent@project:alpha`. Revocation = tuple deletion. OpenFGA's contextual tuples + conditions let you attach ABAC predicates (time-bounded grant, consent flag) to a relationship — giving **consent/revocation as first-class operations**.
- **Consistency for sharing changes:** Zanzibar's **"new-enemy problem"** is directly relevant — if A revokes B then adds confidential content, a stale check could leak it. Use **zookies/ZedTokens** (consistency tokens) so confidential-access checks are evaluated against sufficiently fresh permission state; accept cached/stale checks only for low-risk public discovery.

**Production-ready today:** OpenFGA (or SpiceDB/AuthZed) for ReBAC; Cedar/OPA or an XACML-style PDP for ABAC policy. Pattern: **PEP at every node + exchange; centralized policy/relationship model; per-node attribute resolution (PIP).**

- NIST SP 800-162 (ABAC): https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-162.pdf
- NIST SP 800-178 (ABAC vs RBAC comparison): https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-178.pdf
- OpenFGA authorization concepts: https://openfga.dev/docs/authorization-concepts
- Auth0 — ReBAC vs ABAC (OpenFGA + Cedar): https://auth0.com/blog/rebac-abac-openfga-cedar/
- AuthZed — intro to Zanzibar: https://authzed.com/learn/google-zanzibar
- Zanzibar (Wikipedia): https://en.wikipedia.org/wiki/Google_Zanzibar

---

## 4. Data Residency / Sovereignty: Control-Plane / Data-Plane Split

The dominant production pattern: **decouple a globally-distributed control plane from regional/on-prem data planes.** Control plane = configuration, orchestration, metadata, routing, identity. Data plane = the actual processing and storage of tenant content.

- **Data plane (regional / on-prem / customer VPC):** databases, object storage, **vector index**, queues, caches, logs, secrets, and a **region-local policy engine** — assembled as a self-contained regional **"cell."** This is where confidential content and (for sovereign AI) **in-region inference** live.
- **Control plane (global):** onboarding, billing, telemetry, org metadata, and often **authentication**. The accepted modern trade-off (OpenAI, Slack data residency): keep customer **content and inference in-region**, but allow **auth flows to route to the US** — justified because login volume is low, SSO/SAML/OAuth is expensive to replicate per region, and auth metadata (emails, timestamps) "reveals less than actual content."
- **Sovereignty ≠ residency.** Even if the workload runs entirely in your boundary, sovereignty fails if the systems governing it at runtime — **routing decisions, policy enforcement, guardrails, telemetry, identity validation** — resolve to external endpoints you don't control. The control plane itself must be sovereignty-aware.

**Mapping to this platform:** each university = one cell (its silo data plane) on its own infra or a dedicated data plane; the thin shared exchange + identity + metadata index = the control plane. **No confidential bytes ever enter the control plane.** BYOK/HYOK per institution reinforces this — even control-plane-orchestrated operations can't decrypt content without the institution's key.

- WorkOS — data residency pattern (control vs data plane): https://workos.com/blog/data-residency-for-enterprise-saas
- Estuary — control plane vs data plane: https://estuary.dev/blog/control-plane-vs-data-plane/
- Rack2Cloud — sovereign AI control plane (runtime sovereignty): https://www.rack2cloud.com/sovereign-ai-control-plane/
- Alation — data residency by design: https://www.alation.com/blog/data-residency-by-design-global-compliance/
- Petronella — BYOK/geo-fencing/sovereign by design: https://petronellatech.com/blog/sovereign-by-design-byok-geo-fencing-and-data-residency-at-global/

---

## 5. Compliance for US/EU Universities + Research Data

What each regime triggers for **storage / access / cross-border transfer**. Design these as enforced attributes (§3) and cell placement (§4), not bolt-ons.

| Regime | Scope | Storage | Access | Cross-border / sharing trigger |
|---|---|---|---|---|
| **FERPA** (US) | Student "education records" | Audit logs, breach records, annual notification | "School official" access with legitimate interest; consent or directory-info rules to disclose | Vendor agreements must satisfy FERPA school-official terms; restrict directory data |
| **GDPR** (EU/EEA) | All personal data of EU data subjects | Records of Processing Activities; DPIA for high-risk; data minimization | Lawful basis + consent management; subject rights (access in ~1 month) | **Cross-border transfer needs a valid mechanism** (adequacy / SCCs); residency expectations → keep EU data in-region |
| **Export controls — ITAR (22 CFR 120–130) / EAR** | Defense-articles / dual-use technical data | Segregate controlled technical data; technology control plans | **Deemed export**: granting a foreign national access *in-country* can require a license; **Fundamental Research Exclusion (FRE)** covers published/openly-shared results — but **is lost** if the sponsor imposes publication or participation restrictions; **inputs** can remain controlled even when results aren't | Cross-border (and cross-national-person) access to controlled technical data is the trigger — must be gated by attributes |
| **HIPAA** (US) | PHI in covered research | DUA required for **Limited Data Sets** (still PHI); de-identified data (45 CFR 164.514) falls outside HIPAA | Minimum-necessary; IRB/Privacy Board review | LDS sharing requires a **Data Use Agreement**; de-identified data needs none |
| **IRB / DUAs** | Human-subjects research data transfer between orgs | Governed by the DUA's terms | Per-protocol/per-DUA authorization | A **DUA governs every inter-institutional transfer** of identifiable/PHI data; non-human/de-identified data classed separately |

**Design consequences:**
1. Classification (`public/private/confidential`) must be augmented with **compliance flags** (`export_controlled`, `contains_PHI`, `FERPA_record`, `IRB_DUA_id`, `gdpr_subject`) that the PDP enforces.
2. **Export controls + deemed-export** make *foreign-national status of the requester* an access attribute even within the US — the access model must support nationality-conditioned grants.
3. **GDPR + sovereignty** force EU cells to keep data in-region; cross-border discovery exposes **only metadata that is lawful to transfer / publishable** (FRE-safe).
4. Cross-institution confidential sharing must reference a **DUA/grant artifact** and be revocable — i.e., grants are first-class objects, not ad-hoc ACLs.

- US DoEd — FERPA: https://studentprivacy.ed.gov/ferpa
- Secure Privacy — FERPA & GDPR governance: https://secureprivacy.ai/blog/student-data-privacy-governance
- National Academies — FRE & export controls: https://sites.nationalacademies.org/cs/groups/pgasite/documents/webpage/pga_055551.pdf
- LBL — Fundamental Research Exclusion: https://exportcontrol.lbl.gov/research-technology/fundamental-research-exclusion-exemption/
- Cornell — export controls in research: https://researchservices.cornell.edu/resources/export-controls-research-and-education
- UW–Madison IRB — Data Use Agreements: https://irb.wisc.edu/manual/investigator-manual/conducting-human-participant-research/hipaa-processes-documentation/data-use-agreements/
- 45 CFR 164.514 (de-identification / LDS) explained: https://www.accountablehq.com/post/45-cfr-164-514-explained-hipaa-s-rules-on-de-identification-re-identification-and-limited-data-sets

---

## 6. Reliability / Scale: Event-Driven Sync Between Nodes and the Exchange

Cross-node sync (publishing shareable metadata, propagating grant/revocation) is a **distributed data-consistency problem**. The canonical failure and its fix:

- **The dual-write problem.** You cannot atomically write to the local DB *and* publish to a queue/exchange — they're separate systems with no shared transaction. If the node crashes between the DB commit and the publish, **the event is lost forever**; naive retries can't recover it.
- **Fix: Transactional Outbox + CDC (production standard).** Write the domain change and an `outbox` row in **one local transaction**; a **log-based CDC** tail (e.g., Debezium reading the WAL) reliably ships outbox rows to the exchange. This guarantees the event is *eventually* produced and depends only on DB availability. Log-based CDC is the production winner; polling "does not scale well."
- **Eventual consistency is inherent.** The central metadata index/search will **lag the source node by seconds**. Acceptable for discovery; **not** acceptable for confidential-access decisions — those must check the authoritative node + fresh permission state (zookies, §3.2).
- **What breaks at scale:**
  - **Ordering & duplicates** — consumers must be **idempotent**; ordering must be keyed (e.g., per-record).
  - **Schema evolution** — consumers must tolerate old/new event versions (schema registry + compatibility rules).
  - **Staleness/poison data** — index needs refresh schedules + monitoring; stale shareable metadata after a revocation is a **leak vector** → revocations must propagate on a fast path and be enforced at read time, not only at sync time.
  - **Slowest-node tail latency** for live federated search → prefer the pre-built central metadata index for the common path; reserve live fan-out for drill-down.
  - **Backpressure / queue saturation** when one node floods the exchange → per-tenant rate limits and partitioning.

**Net:** event-driven + outbox + CDC + idempotent consumers + schema registry is the **production-ready** backbone. The hard rule: **eventual consistency is fine for discovery metadata; confidentiality decisions must be strongly consistent and enforced at the owning node.**

- Solving dual-writes (CDC + Outbox): https://felipenipo.com/distributed-systems/2022/06/17/solving-dual-writes-with-cdc-and-the-outbox-pattern.html
- AWS Prescriptive Guidance — Transactional Outbox: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- Debezium — Event Sourcing vs CDC: https://debezium.io/blog/2020/02/10/event-sourcing-vs-cdc/
- RisingWave — CDC vs dual writes: https://risingwave.com/blog/cdc-vs-dual-writes/

---

## Recommended Federated-Hybrid Architecture

### A. Control-plane / data-plane split

**Per-university Data Plane (silo cell) — on the university's infra or a dedicated isolated data plane:**
- Confidential + private stores: Postgres (with `FORCE` RLS + `tenant_id`-leading indexes as *defense-in-depth*, not sole boundary), object storage, **per-cell vector index + BM25**, research cards, knowledge graph.
- **Local AI**: self-hosted open models (vLLM in prod; Ollama on M4 Max in dev) for confidential routing — model router keeps confidential prompts/inference **in-boundary**.
- **Local PEP + PIP**: enforces every access; resolves compliance attributes (PHI/export/FERPA/consent).
- **BYOK/HYOK** per institution; confidential bytes are never decryptable outside the cell.
- Region-pinned (EU cells in-region for GDPR/sovereignty).

**Shared Control Plane (thin, global) — holds NO confidential bytes:**
- **Exchange/broker** (optionally inside a **TEE — SEV-SNP/TDX/Nitro**) for cross-institution match/discovery so even the operator can't read inputs.
- **Central metadata-only discovery index**: publishable profiles, abstracts, capability tags, embeddings of *publishable* text, **pointers** back to owning nodes. Populated by **Outbox + log-based CDC** from each cell; eventually consistent.
- **Authorization service** (ReBAC tuples + ABAC conditions, OpenFGA/SpiceDB-style) with **zookies** for fresh confidential checks.
- Identity/SSO, onboarding, billing, telemetry, model-router policy (provider-agnostic; cloud frontier for public/low-risk only).

### B. How cross-institution discovery works without leaking confidential data

1. University A searches. The **central metadata index** answers from **publishable metadata + pointers only** — confidential content was never published to it (only Fundamental-Research-safe / explicitly-shared records flow out via the publish/subscribe + CDC pipeline).
2. A finds a *pointer* to relevant work/expert at B. To go deeper, the request is **brokered to B's node**, where **B's local PEP** evaluates the access decision against fresh permissions (zookie-consistent) and compliance attributes (export-control nationality check, PHI/DUA, GDPR lawful basis).
3. **Privacy-preserving matches** (e.g., "do A and B share collaborators/interests?") run via **2-party PSI** or in the **TEE broker / clean room** — returning only the overlap or an aggregate, never raw sets.
4. **Confidential joint work** (Feature 3 workspaces, Feature 4 grant team assembly over confidential data) happens in **data clean rooms / TEE** with aggregation thresholds and query templates — zero-copy, query-where-data-resides.
5. **Revocation** = delete the sharing tuple + fast-path propagate; reads re-check at the owning node, so stale index entries can never grant access.

### C. The access-control model (hybrid ReBAC + ABAC)

- **Classification & compliance = ABAC attributes/conditions** on every object: `tier{public|private|confidential}`, `residency_region`, `export_controlled`, `contains_PHI`, `IRB_DUA_id`, `consent_status`, `grant_expiry`, and on subjects `home_institution`, `nationality` (for deemed-export).
- **Sharing & membership = ReBAC tuples**: `project:X#collaborator@univB:user`, hierarchical `document#parent@project`, group memberships; **cross-institution sharing grants are tuples + an ABAC condition** (time-bound, consent-gated, DUA-referenced). Consent/revocation = tuple create/delete.
- **Decision flow (XACML-shaped):** PEP at each node and at the exchange → centralized PDP (ReBAC graph walk + ABAC policy eval) → per-cell PIP supplies attributes → **zookie consistency** for confidential checks; cached/eventual for public discovery.
- **Modularity / blast radius:** features (discovery, lit-intelligence, workspaces, grant intelligence) are pluggable modules behind the same PEP/PDP contract and the same publish-metadata interface; bridge model means a new module added in pool tier never touches the confidential silo. GTM editions = packaging toggles over the same architecture, not forks.

**One-line rule the whole design enforces:** *publishable metadata is centralized for fast discovery; confidential bytes never leave their cell; every confidentiality decision is made fresh at the owning node under a ReBAC+ABAC policy — eventual consistency is allowed only where a leak is impossible.*

### Production-ready-today vs research-only
- **Production:** bridge/silo isolation; control/data-plane split + regional cells; ReBAC (OpenFGA/SpiceDB) + ABAC (Cedar/OPA); Outbox+CDC event sync; TEEs (SEV-SNP/TDX/Nitro); data clean rooms; 2-party PSI and DP for aggregates; BYOK.
- **Research-only / narrow-pilot:** FHE on the critical path (use PHE/SHE only for targeted features); fully attested TEE against physical-access adversaries (TEE.Fail caveat); large-scale multi-party PSI.