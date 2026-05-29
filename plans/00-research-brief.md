# Consolidated Research Brief

This is a synthesis task — no codebase work needed. I'll consolidate the five reports into one decision-ready brief directly.

# Consolidated Architecture Brief — Federated Multi-University Research Collaboration & Discovery Platform

*Synthesizes five research reports (market, federation/compliance, retrieval/AI, identity/authz/security, OSS stack). Decision-ready. Opinionated. Build order is sequenced; architecture is constant.*

---

## 0. The Thesis (one paragraph)

The market splits into six silos that each solve one pillar partially: incumbents own the profile/data layer (Elsevier **Pure**, Clarivate **Converis/Esploro**, **Symplectic**, **Academic Analytics**, **Dimensions**, open-source **VIVO**); VC-backed startups own AI workflows over **public** literature only (**Elicit, Consensus, Scite, SciSpace, Undermind, Scholar-QA**); research-admin incumbents own grants/compliance (**Cayuse, Kuali, Pivot-RP, GrantForward, Instrumentl**, plus the fast-follow AI threat **Atom Grants / GrantsAI**); and confidential federation exists *only* in commercial clean rooms (**Decentriq, BeeKeeperAI, Snowflake/Databricks/Azure clean rooms, Duality**) or in academic **public-LOD** federation (**VIVO CTSAsearch / Direct2Experts**, 64 institutions). **Nobody federates confidential cross-institution research data with revocable grants + AI-native grounded Q&A on top.** That precise intersection is the white space, and it is technically de-risked (Secure Multifaceted-RAG, arXiv 2504.13425; TEEs; Zanzibar ReBAC).

---

## (a) HARD CONSTRAINTS

### Compliance (designed-in, enforced as attributes — not bolt-ons)
- **FERPA** — position as **"school official"** under institutional control; encryption, ReBAC/ABAC, audit logs, annual notification. School stays liable; you are its agent.
- **GDPR** — university = controller, you = **processor**; mandatory **DPA**; right-to-erasure in ~30 days (reconcile with retention via **crypto-shred**); cross-border transfer needs valid mechanism (adequacy/SCCs) → **EU data stays in-region cell**. Adopt **REFEDS CoCo v2** for EU IdP attribute release.
- **Export controls (ITAR 22 CFR 120–130 / EAR)** — **deemed export**: granting a foreign national in-country access can require a license → *nationality/citizenship is an access attribute even within the US*. **Fundamental Research Exclusion (FRE)** covers published/openly-shared results but **is lost the moment you impose access/publication restrictions** — so the export-control gate must be **opt-in per controlled project, never blanket**. Controlled technical data → **US-stored, US-person-access-only**.
- **HIPAA / IRB / DUAs** — Limited Data Sets need a **DUA**; de-identified (45 CFR 164.514) falls outside HIPAA. Every inter-institutional transfer of identifiable data references a **DUA artifact**.
- **GTM gate:** **HECVAT** (full toolkit = 321 questions) is mandatory before any pilot/purchase; **SOC 2 Type II** (~3–6 mo readiness) is the de facto floor; add **ISO 27001** for EU/international. Start SOC 2 day one — it gates the first institutional contract.

### Licensing (these dictate stack choices — non-negotiable)
- **AVOID Elasticsearch** (AGPLv3 network-copyleft, hostile to commercial SaaS) → **OpenSearch** (Apache-2.0, LF-governed).
- **AVOID KuzuDB** — *archived 10 Oct 2025, read-only, team went to Apple.* (TigerBuddy uses it today — must replace.) → **Apache AGE**.
- **AVOID HuggingFace TGI** for new builds (maintenance mode Dec 2025) → **vLLM**.
- **AVOID Permify** (AGPL-3.0) → OpenFGA/SpiceDB (Apache-2.0).
- **Neo4j Community = GPLv3** (no clustering, copyleft distribution risk); **Memgraph = BSL** — fallbacks only, isolated behind a service boundary.
- **ORCID Public API is non-commercial (verbatim ToS)** → ship the **CC0 annual Public Data File**, not the live API. Buy Member API only for real-time writes.
- **OpenAlex live API is metered** (Apr 2025; per-credit price quote-gated) → **self-host the free monthly CC0 snapshot; never put the metered API on a hot path.**
- **Semantic Scholar bulk = ODC-BY** (attribution required); **SPECTER2 = Apache-2.0** (clean).
- **PMC/Europe PMC full text is license-tiered** → programmatically gate to commercial-OK OA subset (CC0/BY/BY-SA/BY-ND); exclude NC-only.
- **CORE** commercial use is membership-gated; **CILogon** commercial deployment requires a paid subscription (COGS line, not a blocker).

### Technical (locked + load-bearing)
- Confidential data + confidential AI inference **never leave the tenant boundary**; cloud egress for confidential-tagged data is a **compliance defect, not a config choice**, enforced cryptographically (per-tenant keys) and at the network layer.
- **Postgres RLS is defense-in-depth only**, never the sole boundary for confidential data. Footguns: must `FORCE ROW LEVEL SECURITY` (owner/superuser bypass by default); use `SET LOCAL` not `SET` (PgBouncer connection-context leak); specify `WITH CHECK` (else INSERT cross-tenant rows you can't see); use `RESTRICTIVE` policies (PERMISSIVE OR-union); `tenant_id` must be the **leading index column**; materialized/`SECURITY DEFINER` views bypass RLS.
- **Eventual consistency is allowed for discovery metadata; confidentiality decisions must be strongly consistent and re-checked at the owning node** (the hard one-line rule).
- Confidential tier is constrained to **open, self-hostable** components → disqualifies proprietary embedding/rerank/LLM APIs (Voyage/Cohere/Gemini/frontier) from the confidential path (public-tier or explicit BYO-key only).

---

## (b) WHITE-SPACE + MVP WEDGE + BEACHHEAD

**White space (precise, unoccupied intersection):** federated cross-institution discovery over **confidential** data + AI-native grounded Q&A that **routes by data classification** + all-four-pillars in one modular product + one product sellable to all four buyers via packaging + FERPA/GDPR/ITAR-EAR designed-in. The closest unifier (**Atom Grants**, pillars 1+4, ~$179/mo into RD offices, 50+ institutions) is **single-tenant, public-data-only** — it validates the buyer and wedge but lacks confidentiality/federation.

**Recommended MVP wedge — RESOLVING a contradiction between reports.** The market report argues the *easiest security review* is a **confidential, local-model-only single-lab corpus** (data never leaves → HECVAT friction collapses). The security report argues to lead with **public+private discovery** (lowest data sensitivity, defers BYOK/HYOK/AI-boundary/SOC2). **Resolution — these are sequential phases of one wedge, not a conflict:**

> **MVP = AI-native research/literature intelligence + expert discovery over a single research-active lab/department's OWN corpus, single-tenant, bottom-up PLG.** Run **public + private** tiers fully; **define the confidential tier in the schema and prove the local-model isolation story from day one** (it's the demo that wins the room), but gate the heavy confidential machinery (HYOK, full export-control gate, cross-institution grants) as the immediately-following phase. This exercises the kernel (classification engine + model router + tenant isolation + ReBAC + audit spine) with the smallest procurement surface, and the federation/exchange layer lights up in Phase 2 with **zero re-architecture**.

**Beachhead buyer:** a **single research-active department or lab at one R1** (bottom-up PLG, $179–$499/mo department band — Instrumentl/Atom benchmark), with an **export-controlled engineering/defense lab as the high-value, low-competition variant** (ITAR/EAR-aware sharing is genuinely novel; no AI-assistant competitor can touch it).

**Expansion path (constant architecture, build-order only):** private-corpus intelligence → institution-wide expert discovery → **flip on the cross-institution exchange layer once ≥2 nodes are live** (the federated moat) → **cross-institution grant/team-assembly** to monetize the consortium (enter Atom Grants' territory *with* the confidentiality+federation they structurally lack).

**Packaging (one product, four GTM motions — copy Starmind's model):** per-institution **node/platform base fee** + **per-active-user pillar modules** (discovery, lit-intelligence, workspaces, funding) + **consortium/exchange add-on** (priced per connected institution) + **BYO-provider/key tier**. Serves PLG (one module/few seats), department, campus-wide (FTE-capped), and consortia from one SKU. Editions = config toggles, not forks. *(Benchmarks: Starmind $4k/mo base ≤500 profiles + $0.60–$2.20/active-user; Interfolio ~$28k/yr FTE; PLG $12–$20/seat.)*

**Strategic don'ts:** don't rebuild the public graph (OpenAlex free + ORCID identity); don't lead with public-literature AI (Elicit/SciSpace/Undermind have commoditized it and outfund you); **integrate, don't displace** incumbents early (ship connectors: ingest from Pure/Esploro/ORCID/OpenAlex, push to Cayuse/Kuali).

---

## (c) DEFAULT TECH STACK (primary + fallback per layer)

| Layer | Primary | Fallback | Notes |
|---|---|---|---|
| Federation entry | **CILogon** (5,000+ InCommon/eduGAIN IdPs + ORCID/social, one OIDC endpoint) | direct Keycloak SAML/OIDC brokering | Commercial needs paid CILogon subscription → COGS |
| IdP / broker / session | **Keycloak** (Apache-2.0, realm-per-tenant) | Ory (Kratos/Hydra) | CILogon front-door → Keycloak token issuer |
| Provisioning | **JIT** (first login) **+ SCIM** (RFC 7644) | — | SCIM deprovisioning is table-stakes; cascade revocation on affiliation loss |
| Authz — ReBAC core (sharing/isolation) | **SpiceDB** (ZedToken strong consistency) | **OpenFGA** (must opt into `HIGHER_CONSISTENCY` on confidential) | **Resolved contradiction below** |
| Authz — ABAC overlay (classification/residency/export/AI-routing) | **Cedar** (deterministic, validated) | OPA/Rego (only if you also need infra policy) | Two-stage check: SpiceDB path → Cedar caveat |
| Vector search | **Qdrant** (Apache-2.0, best multi-tenant isolation/sharding) | **pgvector** (small tenants; co-locates w/ AGE + authz store in one PG) | Per-tenant index in the cell |
| Graph DB | **Apache AGE** (Cypher-on-Postgres, co-locates pgvector+authz) | Neo4j Community (GPLv3, isolate) / Memgraph (BSL) | **Replaces archived KuzuDB** |
| Search / BM25 | **OpenSearch** (Apache-2.0, hybrid BM25+vector) | Tantivy/Quickwit (embedded) | Not Elasticsearch (AGPL) |
| LLM serving (prod) | **vLLM** (PagedAttention, ~24x TGI throughput) | SGLang | Confidential self-host branch |
| LLM serving (dev) | **Ollama** (M4 Max 36GB) | llama.cpp | Sequential under load → dev only |
| Embeddings | **Qwen3-Embedding** (0.6B dev / 4B–8B prod, Apache-2.0, MTEB #1) + **SPECTER2** (citation/scientific space) | BGE-M3 (dense+sparse in one model); nomic-embed-v1.5 | Voyage/Cohere/Gemini = public/BYO only |
| Reranker | **BGE-reranker-v2-m3** or **Qwen3-Reranker** (local) | Cohere Rerank 3.5 (public/BYO) | +5–15 nDCG@10 for <200ms |
| Data orchestration | **Dagster** (asset lineage, crawl→distill→embed→index→graph) | Prefect / Airflow | TigerBuddy idiom |
| Durable workflows | **Temporal** (grant/revocation/workspace lifecycles, days–months) | — | Complementary to Dagster, not redundant |
| API | **FastAPI** (async, typed, OpenAPI) | — | Clean module boundaries for pluggability |
| RAG ingestion/retrieval | **LlamaIndex** (library behind your own thin retrieval interface) | Haystack (deterministic pipelines for FERPA/ITAR) | Avoid framework lock-in |
| Agent orchestration | **LangGraph** | — | Expert-discovery & grant-team agents |
| Secrets / keys | **Vault** + per-tenant **envelope encryption (DEK/KEK)**; **BYOK mandatory (confidential)**, **HYOK offered** | cloud KMS | Revoke KEK = cryptographic lockout / crypto-shred |
| Scholarly data (self-hosted) | **OpenAlex snapshot (CC0)** + Crossref annual file + OpenCitations (CC0) + arXiv metadata (CC0) + **ROR (CC0)** + **ORCID Public Data File (CC0)** + Semantic Scholar bulk (ODC-BY) + SPECTER2 vectors | live polite-pool APIs for freshness only | Own the corpus; avoid metering/NC traps |

---

## (d) FEDERATED-HYBRID ARCHITECTURE + ACCESS-CONTROL MODEL

**Control-plane / data-plane split (the spine; maps 1:1 to the locked deployment):**

- **Per-university Data Plane = silo "cell"** (its own infra or dedicated isolated data plane), region-pinned (EU in-region): confidential+private Postgres (FORCE RLS + tenant_id-leading indexes as *defense-in-depth only*), object storage, per-cell vector index (Qdrant) + BM25 (OpenSearch), AGE knowledge graph, research cards. **Local AI** (vLLM prod / Ollama dev) for confidential routing. **Local PEP + PIP** (Cedar embedded — confidential classification checks execute inside the boundary, never depend on the shared plane). **BYOK/HYOK** per institution.
- **Thin shared Control/Exchange Plane (holds NO confidential bytes):** central **metadata-only discovery index** (publishable profiles, abstracts, capability tags, embeddings of *publishable* text, **pointers** back to owning nodes), populated via **Transactional Outbox + log-based CDC (Debezium)** from each cell (eventually consistent); **SpiceDB** relationship store (cross-tenant grants must be globally consistent); identity/SSO, onboarding, billing, telemetry, model-router policy. Run the **exchange/match broker inside a TEE (AMD SEV-SNP / Intel TDX / AWS Nitro Enclaves)** so even the operator can't read cross-institution match inputs. *(TEE.Fail caveat: forged SEV-SNP/TDX attestation needs physical access + root → out of scope for remote-attacker threat model.)*

This is AWS SaaS Lens' **bridge model**: pool the public/discovery surface, **silo the confidential data plane per university** — the isolation decision is made *per data store by regulatory profile.*

**How cross-institution discovery works without leaking confidential data:**
1. Search hits the **central metadata index** → answers from publishable metadata + pointers only (confidential bytes were never published; only FRE-safe / explicitly-shared records flow out via Outbox+CDC pub/sub).
2. Drill-into-detail is **brokered back to the owning node**, where its **local PEP** evaluates against *fresh* permissions (ZedToken-consistent) + compliance attributes (export-control nationality, PHI/DUA, GDPR lawful basis).
3. "Do A and B share collaborators/interests?" → **2-party PSI** or in the **TEE broker / clean room** (returns overlap/aggregate, never raw sets).
4. Confidential joint work (Feature 3 workspaces, Feature 4 grant assembly over confidential data) → **data clean rooms / TEE**, zero-copy, query-where-data-resides, aggregation thresholds + pre-approved query templates.
5. **Revocation** = delete the sharing tuple + fast-path propagate; reads re-check at the owning node → stale index entries can **never** grant access.

**Privacy-tech practicality ranking:** TEEs (production) > clean rooms (production) > 2-party PSI + DP for aggregates (production, bounded) > **FHE (research/narrow — keep OFF the critical path**, pilot only for a single encrypted-match feature).

**Access-control model — hybrid ReBAC + ABAC (both reports converge here):**
- **Classification & compliance = ABAC attributes/conditions** on every object: `tier{public|private|confidential}`, `residency_region`, `export_controlled{none|EAR|ITAR}`, `contains_PHI`, `IRB_DUA_id`, `consent_status`, `grant_expiry`; on subjects: `home_tenant`, `scoped_affiliation`, `nationality`/`country` (deemed-export, where lawfully collected). These gate *whether a relationship even counts*.
- **Sharing & membership = ReBAC tuples** (Zanzibar): `project:X#collaborator@univB:user`, hierarchical `document#parent@project`, `org_unit#parent` (lab→dept). **Cross-institution sharing grant is a first-class `sharing_grant` object** recording `grantor` (accountability), grantor/grantee tenants, resource ref, `revoked_marker`, with ABAC caveats (time-bound, consent-gated, DUA-referenced, `classification_ceiling` so a grant can share *private* but never auto-promote *confidential*). **Revocation = O(1) tuple delete → `is_active` flips → next consistent Check denies.**
- **Decision flow (XACML-shaped):** PEP at every node + exchange → PDP (SpiceDB graph walk + Cedar ABAC eval) → per-cell PIP supplies attributes → **ZedToken consistency for confidential checks; cached/eventual only for low-risk public discovery** (this is the **Zanzibar "new-enemy problem"** mitigation — a revoke-then-add must not leak via stale cache).
- **Tenant isolation is structural, not a column:** every resource has a `tenant` relation; cross-tenant access is reachable *only* through a `sharing_grant`. No grant ⇒ no path ⇒ deny-by-default. **Object-level `Check` on every request** (kills BOLA/IDOR, OWASP API #1).

**Why SpiceDB over OpenFGA (resolving the only stack contradiction — security report says SpiceDB, OSS report defaults OpenFGA):** for a confidentiality-first product where **revocation correctness is a security guarantee, not a UX nicety**, SpiceDB's ZedToken per-request consistency is the deciding factor (a stale "still allowed" after a revoked cross-institution share is an *incident*). OpenFGA is the acceptable lower-friction fallback **only if you commit to `HIGHER_CONSISTENCY` on every confidential-tier check.** **Recommendation: SpiceDB.**

**Federation security hardening:** SP in eduGAIN via **REFEDS R&S + Sirtfi + CoCo v2** (turns "negotiate attribute release with 200 universities" into "publish three entity-category tags"). Authorize on `eduPersonScopedAffiliation` + stable `subject_id`/`eduPersonUniqueId` (not recyclable eppn alone); ORCID = correlation key, **not** auth root of trust. **Prefer SP-initiated SSO**; strictly validate issuer/audience and scope every assertion to the asserting tenant (confused-deputy mitigation); short-lived + sender-constrained (DPoP) tokens for confidential APIs.

**Reliability backbone:** Outbox + log-based CDC + **idempotent consumers** + schema registry. Revocations propagate on a **fast path** and are enforced at read time (stale shareable metadata after revocation is a leak vector). Prefer the prebuilt central index for the common path; reserve live federated fan-out for drill-down (slowest-node tail latency). Per-tenant rate limits/partitioning against exchange backpressure.

**Modularity / blast radius:** every pillar (discovery, lit-intelligence, workspaces, funding) is a pluggable module behind the **same PEP/PDP contract + same publish-metadata interface**; bridge model means a new pool-tier module never touches the confidential silo. **GTM editions = packaging toggles over one architecture, not forks.**

---

## (e) RETRIEVAL / AI APPROACH

**Single tenant-local retrieval engine behind one clean interface; a model router selects local-vs-cloud per data tier; a thin exchange adapter federates only public-tier discovery. Confidential data and its models never leave the node.**

- **Hybrid retrieval (MVP-essential):** dense (Qwen3-Embedding, MRL-truncated for shortlist → full re-score) + sparse (**BM25**, mandatory — academic corpora are entity-heavy: author names, acronyms, grant numbers, gene names). Hybrid beats either alone by **15–30% recall**.
- **Fusion:** **RRF (k≈60)** at MVP — parameter-free, no labels, robust cold-start, and **fusion weights must be tenant-local** (term distributions don't transfer across institutions). Move to **per-tenant learned convex fusion** later once click/relevance feedback accrues inside a node (convex showed Recall@5 0.726 vs RRF 0.695).
- **Reranking (MVP-essential, highest cheap ROI):** rerank top-50→top-8 with **BGE-reranker-v2-m3** / Qwen3-Reranker (local); Cohere Rerank 3.5 as public/BYO upgrade. Run as a router-managed module (swap local↔hosted by tier).
- **Two embedding spaces:** Qwen3 (primary ad-hoc query→passage RAG) + **SPECTER2** (citation-proximity / "related papers" / expertise fingerprints — beats general models on paper-similarity). **Matryoshka (MRL)** is operationally essential for per-node RAM control.
- **Knowledge graph (dual-purpose):** build a **deterministic metadata-backbone graph** (authors/papers/citations/affiliations/venues/grants/topics — cheap, no LLM-extraction tax) first. Add **HippoRAG2-style Personalized-PageRank** for multi-hop augmentation (**~1k tokens/query** — the only graph economics that survive per-tenant deployment). **Explicitly overkill at MVP: Microsoft GraphRAG global community summarization (~331k tokens/query + heavy recurring indexing)** — make it a later opt-in module for global-synthesis queries only.
- **Agentic orchestration (phased):** single-shot hybrid+rerank first → **Adaptive RAG** routing early (cheap query-difficulty classifier; dovetails with the model router) → **CRAG corrective loop** for the literature-intelligence module (citation faithfulness is the credibility differentiator) → **query-decomposition / multi-agent** reserved for grant/team-assembly. Each is an interchangeable module behind one retrieval interface; on the confidential path every agent step runs the local model — cap loop iterations.
- **Identity resolution (foundational, not optional):** deterministic anchors (**ORCID/DOI/OpenAlex author IDs**) + blocking + graph-feature classifier; **LEAD-style LLM adjudication** for hard collisions later. **Critical federated wrinkle: treat the cross-institution identity graph as public-tier by construction** — disambiguation must never centralize private records or become a confidentiality leak. Standalone Identity Resolution service consumed by graph build, expertise modeling, and discovery alike.
- **Expertise / collaborator (the differentiated surface, Features 1+4):** expertise = profile-as-retrieval (SPECTER2/Qwen3 fingerprints + retrieve+rerank) at MVP → **GNN link prediction** over the heterogeneous graph (Phase 2) → **cross-institution team assembly** over the federated public-tier graph for grant intelligence (Phase 3 — the strongest defensibility vs single-institution tools).
- **Evaluation (MVP-essential — "trustworthy grounded intelligence" is the whole pitch):** **RAGAS** (Faithfulness/Groundedness + Context Precision/Recall) + **nDCG@k / Recall@k** on a small in-domain gold set, wired into **CI as a regression gate**, run **per-tenant and per-model-route**. **The judge LLM must itself be the local model on the confidential tier** (router-aware eval) — you can't send confidential answers to a cloud judge.

**Model router (the locked differentiator, validated by Secure Multifaceted-RAG arXiv 2504.13425):** classification → route binding is the kernel. Confidential ⇒ in-boundary local model only, network-egress-blocked, per-tenant key-scoped so cloud routing is *impossible* for confidential-tagged data. Public/low-risk ⇒ cloud frontier. Per-institution BYO-provider/keys throughout. **Build the data-classification engine + model router as the kernel FIRST** — every differentiator (confidential RAG, federation grants, compliance) hangs off classification.

---

## (f) TOP RISKS

1. **Confidentiality leak via the federation seam** (the existential one). Mitigations that must be invariant: publishable metadata only in the central index; confidential reads re-checked at the owning node under ZedToken consistency; revocation fast-path enforced at read time; structural deny-by-default isolation; per-tenant keys so a leaked row is ciphertext.
2. **Stale-grant / New-Enemy problem + dual-write loss.** Eventual consistency anywhere near a confidentiality decision = a leak. Enforce: SpiceDB ZedToken on confidential checks; Outbox+CDC (never naive dual-write — lost-event-forever failure); idempotent consumers; revocation on a separate fast path.
3. **Export-control self-sabotage (FRE loss).** Imposing the access controls ITAR/EAR demand can *itself* strip the Fundamental Research Exclusion. The export gate must be **opt-in per controlled project**, never default-on — or you convert ordinary fundamental research into controlled tech data.
4. **Procurement death-by-committee + HECVAT/SOC2 wall.** Four veto-holding buyers (research office/library/faculty affairs/IT-security). Mitigation: PLG private-corpus wedge stays *below* the committee threshold; SOC 2 Type II started day one; "confidential data never leaves your node" is the single strongest HECVAT answer — weaponize it.
5. **Fast-follow on pillars 1+4.** Atom Grants / GrantsAI already ship AI-native cross-institution co-PI matching at PLG pricing into RD offices — but single-tenant, public-data-only. Risk is they add a thin "private" story before you reach ≥2 federated nodes. Mitigation: enter funding/team-assembly *with* the confidentiality+federation moat they structurally lack; keep it Phase 3, not Phase 1.
6. **Over-engineering the AI core too early.** MS-GraphRAG global, ColBERTv2/PLAID per-tenant index, multi-agent orchestration, learned/LambdaMART fusion, FHE on the critical path — all overkill at MVP; each adds per-tenant cost/ops with no day-one payoff. Ship single-shot hybrid+rerank+RRF and defer the rest as pluggable modules.
7. **Foundational primitives that can't be retrofitted.** Author disambiguation, the classification engine, the authz graph, and the audit log are *interface-load-bearing from day one* — thin implementations are fine, but skipping their interfaces forces a re-architecture. Build the kernel and the audit spine in the MVP even if implementations are minimal.
8. **TigerBuddy inheritance traps:** KuzuDB is archived (replace with AGE); nomic-embed is materially behind Qwen3/BGE-M3; single-tenant NetworkX `tiger_brain.json` graph does not survive multi-tenancy. Treat TigerBuddy as inspiration, not a foundation.

---

**One-line invariant the whole platform enforces:** *publishable metadata is centralized for fast discovery; confidential bytes never leave their cell; every confidentiality decision is made fresh at the owning node under a ReBAC+ABAC policy; eventual consistency is permitted only where a leak is structurally impossible.*