# Research: data-oss-stack

I now have enough verified material across all angles. The ground-truth flags are confirmed; OpenAlex's exact per-credit dollar figure is quote-gated (contact-for-quote), which I'll note honestly rather than fabricate. Synthesizing the final cited report.

---

# Build-vs-Buy: Federated Multi-University Research Collaboration Platform

**Scope:** self-hosted, multi-tenant, commercial-friendly. Federated hybrid (per-university isolated node + thin shared exchange). Data tiers public/private/confidential with revocable cross-institution grants. Provider-agnostic model router. Tags: **USE** (adopt now), **CONSIDER** (viable, conditions apply), **AVOID** (don't adopt).

**Verification note:** All KNOWN VERIFIED FLAGS were re-checked against primary sources and **all held true** (details below). The one number I could not pin down is OpenAlex's exact per-credit dollar cost — it is quote-gated ("contact us for a quote"), so I report it as unknown rather than guess.

---

## (A) Scholarly Open Data / APIs

| Source | Coverage | API limits | Bulk / snapshot | License | Commercial? | Tag |
|---|---|---|---|---|---|---|
| **OpenAlex** | ~250M+ works, authors, institutions, venues, concepts; the broadest open graph | Metered: ~$1 free/day. Single-entity lookups unlimited; list+filter 10k calls/1M results/day; search 1k calls/100k results/day; 100 PDF dl/day. Beyond that = paid usage credits | **Monthly full snapshot, free, CC0** (S3/AWS). Premium adds hourly updates | CC0 (data) | **Yes** | **USE** (self-host the snapshot; never depend on the live metered API in product) |
| **Semantic Scholar (S2AG / S2ORC)** | ~200M+ papers, citation graph, **SPECTER2 prebuilt embeddings** | Unauthenticated 5,000 req/5min (shared 1k RPS pool); free API key = dedicated ~1 RPS | Bulk datasets via Datasets API; S2ORC corpus | **ODC-BY 1.0** (attribution) for bulk; some API-delivered records carry CC-BY-NC | Bulk **yes** (with attribution). API ToS prohibits *reselling the API itself* — fine for our use | **USE** (best prebuilt scientific vectors; attribute) |
| **SPECTER2 model** | Scientific doc embeddings (title+abstract → vector) + task adapters | n/a (self-hosted) | HF download | **Apache-2.0** | **Yes, no restriction** | **USE** (primary scientific embedding model — verified Apache-2.0) |
| **Crossref** | ~180M DOI records, refs, funders, ORCID/ROR links | Public/polite pools; **rate limits tightened 1 Dec 2025**. Polite pool (mailto header) recommended | **Annual public data file (free)**; Metadata Plus = monthly dumps + high limits (paid) | Metadata treated as **facts / public-domain**, freely redistributable | **Yes** | **USE** (polite pool + annual file; Plus only if you need fresh production SLAs) |
| **OpenCitations (COCI/Meta/INDEX)** | ~1B+ DOI-to-DOI citation links | REST API + token; modest | Full dumps (CSV/JSON-LD), e.g. COCI ~50GB+ | **CC0** | **Yes** | **USE** (CC0 citation graph; complements Crossref refs) |
| **arXiv** | ~2.4M preprints (CS/physics/math heavy) | API rate-limited (be polite); ToS forbids abuse | **Full bulk via Kaggle dataset + S3 requester-pays**; OAI-PMH for metadata | Metadata **CC0 1.0**; full-text per-article license varies | Metadata **yes**; full-text varies | **USE** (metadata CC0; full-text check per-paper) |
| **PubMed / PMC / Europe PMC** | PubMed ~37M cites; Europe PMC ~33M+ pubs; PMC OA full text | **NCBI E-utilities: 3 req/s no key, 10 req/s with key**; Europe PMC RESTful generous | PMC FTP/Cloud/OAI-PMH; **only sanctioned endpoints** may be used for bulk | PMC OA subset tiered: **commercial-OK (CC0/BY/BY-SA/BY-ND)** vs **NC-only** vs custom — must filter by per-article license | **Mixed — must enforce per-record license** | **CONSIDER** (USE the commercial-OK OA subset; gate biomedical full-text by license tier) |
| **Unpaywall** | OA-location lookup for ~30M+ works (via DOI) | REST (mailto); generous | **Full DB snapshot** available | CC-BY-style / open | **Yes (attribution)** | **CONSIDER** (great OA-link enrichment; OpenAlex already embeds much of this) |
| **CORE** | ~250M+ OA full-text aggregations | Free key limited; **commercial tier requires CORE membership** | Data dumps via membership | Mixed; commercial use gated behind paid membership | **Gated** | **CONSIDER** (only if you need aggregated OA full text beyond PMC/arXiv) |
| **ORCID** | Researcher identity, affiliations, works (~16M+ iDs) | **Public API: non-commercial only**, 12 req/s, 100k reads/day/client. **Member API: commercial-OK**, 24 req/s, no quota (paid membership) | **Annual Public Data File = CC0**, downloadable by **everyone** (not members-only) | Public Data File **CC0**; Public *API* ToS non-commercial | **API no / Data File yes** | **USE the CC0 annual Public Data File**; **AVOID the live Public API in product**. Buy Premium membership only if you need real-time writes/reads |
| **ROR** | ~100k+ research-org identifiers (institution disambiguation) | Public API, lightweight | **Full data dump, CC0** (Zenodo) | **CC0** | **Yes** | **USE** (canonical institution IDs — backbone of cross-institution joins) |

**Verified flags (A):**
- **OpenAlex metered Apr 2025 → confirmed.** Live API now metered ($1/day free, then paid credits; exact per-credit price is quote-gated). **Monthly snapshot remains free + CC0.** → self-host the snapshot.
- **ORCID Public API non-commercial → confirmed verbatim** ("you may not make use of the Public API in connection with any revenue-generating product or service"). **Public Data File is CC0, annual, open to all.** Member API removes the restriction for paying members.
- **Semantic Scholar bulk ODC-BY + SPECTER2 Apache-2.0 → both confirmed** (SPECTER2 model card states "License: Apache 2.0").

---

## (B) Infra OSS by Category

### Identity / Federation
- **CILogon** — **USE.** Verified: bridges **5,000+ InCommon/eduGAIN IdPs + Google/GitHub/ORCID/Microsoft** into a single OIDC/OAuth2 endpoint. Free for academic research; **paid subscription for commercial/SLA** — contact required (factor into COGS). Lowest-effort path to onboard already-SSO universities.
- **Keycloak** — **USE.** Apache-2.0, batteries-included OIDC/SAML, identity brokering, home-realm discovery. Heavier to scale but the pragmatic broker. Pair: **CILogon → Keycloak broker → per-tenant realms.**
- **Ory (Kratos/Hydra/Keto/Oathkeeper)** — **CONSIDER.** Apache-2.0, composable/cloud-native; Hydra excels at spinning up hundreds of OIDC clients (multi-tenant edge). More assembly required; choose if Keycloak's monolith becomes a scaling bottleneck.
- **Shibboleth** — **CONSIDER (interop only).** The incumbent SAML SP/IdP in academia; you'll *speak to* it via CILogon/Keycloak rather than run it.
- **InCommon / eduGAIN** — these are **federations, not software** — reached through CILogon. Not a build target.

### Authz / Policy
- **OPA (Rego)** — **USE** for **ABAC** over the data-tier sensitivity label (public/private/confidential) + FERPA/ITAR attributes. Apache-2.0, CNCF-graduated, mature.
- **OpenFGA** — **USE** for **ReBAC** (Zanzibar-style) cross-institution **sharing grants** (revocable relationships). Apache-2.0, CNCF, Auth0/Okta-backed.
- **SpiceDB (Authzed)** — **CONSIDER** as the OpenFGA alternative: most Zanzibar-faithful, Watch API, strong consistency, used by OpenAI ChatGPT Enterprise at tens-of-billions scale. Apache-2.0. Pick if you need stronger consistency guarantees than OpenFGA.
- **Cedar (AWS)** — **CONSIDER.** Clean policy language, verifiable; weaker for nested-group/list-filtering at scale than Zanzibar models. Viable OPA alternative for simpler ABAC.
- **Verdict:** OPA (ABAC sensitivity) **+** OpenFGA (ReBAC grants) — exactly the flagged pattern, **confirmed sound**.

### Vector Search
- **Qdrant** — **USE (primary).** Apache-2.0; **best-in-class multi-tenancy** (flexible sharding, per-tenant payload isolation) — directly serves per-university isolation. Rust, fast, production-proven.
- **pgvector** — **USE (fallback / small-tenant).** PostgreSQL-License; collapses stack when a tenant is already on Postgres (and Apache AGE graph + OpenFGA store can share the same PG). Lower ceiling at very high scale.
- **Weaviate** — **CONSIDER.** BSD-3; good hybrid search but operational complexity rises with modules + multi-tenancy.
- **Milvus** — **CONSIDER.** Apache-2.0; scales to billions but heavy operationally — overkill until corpus is huge.
- **LanceDB** — **CONSIDER (embedded/dev).** Apache-2.0, embedded; great for the M4 Max dev node, not the multi-tenant prod plane.

### Graph DB
- **KuzuDB** — **AVOID. Confirmed archived 10 Oct 2025** (repo read-only; team "working on something new," went to Apple). MIT-licensed so forks are legal (LadybugDB, Vela fork) but **no corporate backing/longevity** — do not adopt for production.
- **Apache AGE** — **USE (primary).** Apache-2.0 Postgres extension, openCypher via `cypher()`. Inherits Postgres maturity/HA/backup/observability and **co-locates with pgvector + OpenFGA in one Postgres** — strong fit for per-tenant isolation and ops simplicity. Caveat: slower on deep traversals than native engines.
- **Neo4j Community** — **CONSIDER (fallback).** **GPLv3** — copyleft; usable self-hosted but a distribution/embedding risk for a commercial product (no clustering in Community; HA/clustering is Enterprise-only/paid). Use only if AGE traversal perf is insufficient *and* you can isolate it as a service.
- **Memgraph** — **CONSIDER.** **BSL** (source-available, converts to Apache-2.0 after delay) — review production terms before commercial ship. In-memory speed for real-time/streaming graphs; not needed for our batch-built knowledge graph.

### Search / BM25
- **OpenSearch** — **USE (primary).** **Apache-2.0** under the Linux Foundation (no single-vendor control). Ships **hybrid BM25 + vector (HNSW/Faiss) + neural sparse + ML Commons** — can serve BM25 *and* be a vector fallback. Verified license/governance.
- **Elasticsearch** — **AVOID (license risk).** Now offers **AGPLv3** (plus SSPL/Elastic License). AGPL's network-copyleft is a hazard for a SaaS/commercial product — OpenSearch avoids it. No reason to take the risk.
- **Tantivy / Quickwit** — **CONSIDER.** Tantivy = Rust BM25 library; Quickwit (Apache-2.0, Datadog-owned since Jan 2025) for log-scale search. Use Tantivy only for an embedded lightweight BM25 path; OpenSearch covers prod.
- **Typesense** — **CONSIDER.** GPLv3; fast/simple typo-tolerant search, but weaker hybrid/scale story than OpenSearch.

### LLM Serving + Embeddings
- **vLLM** — **USE (prod serving).** Apache-2.0; PagedAttention → up to ~24x throughput vs TGI under concurrency. The de-facto open-weight serving standard. Core of the **self-hosted confidential-data router branch**.
- **Ollama** — **USE (dev/local).** MIT; ideal on the M4 Max 36GB dev node. Sequential under load — not for multi-tenant prod (use vLLM there).
- **HuggingFace TGI** — **AVOID (new builds). Confirmed maintenance mode (Dec 2025)**; HF itself now recommends vLLM/SGLang/llama.cpp.
- **Embeddings:** **SPECTER2 (Apache-2.0) — USE** for scientific papers (primary). **nomic-embed-text-v1.5 — USE** for long-context general docs (8k ctx, Apache-2.0). **BGE-M3 / GTE — CONSIDER** (multilingual / general retrieval, free local). Route embedding model by content type, same as the LLM router.
- **SGLang** — **CONSIDER** as a vLLM alternative for heavy structured/agentic decoding.

### Orchestration
- **Dagster** — **USE (data pipelines).** Apache-2.0; asset-based lineage fits the crawl→distill→embed→index→graph ingestion DAG and per-tenant materialization. Already your TigerBuddy idiom.
- **Temporal** — **USE (durable workflows).** MIT (server) / Apache-2.0 (SDKs); durable, resumable, long-running — exactly right for **cross-institution sharing-grant lifecycles, revocations, and multi-party workspace coordination** that must survive failures for days/months.
- **Prefect** — **CONSIDER.** Apache-2.0, Python-native; overlaps Dagster — no need if Dagster is in.
- **Airflow** — **CONSIDER.** Apache-2.0, dominant/mature scheduler; heavier, less asset-native than Dagster. Adopt only if an institution mandates it.
- **Division of labor: Dagster = data assets; Temporal = stateful cross-institution business workflows. Confirmed complementary, not redundant.**

### App / API
- **FastAPI** — **USE.** MIT; async, typed (Pydantic), OpenAPI-native — clean module boundaries for the pluggable-feature requirement. Standard, no risk.

---

## (C) RAG / Agent Frameworks

- **LlamaIndex** — **USE** for ingestion + retrieval orchestration (connectors, chunking, query engines, hybrid retrieval). MIT core; low overhead. Keep its cloud/credit tier out of the self-hosted path.
- **LangGraph** — **USE** for agentic/multi-step orchestration (expert-discovery + grant-team-assembly agents, long-running stateful graphs). MIT (LangChain ecosystem). Note higher per-call overhead — fine for agent workflows, not hot-path retrieval.
- **Haystack (deepset)** — **CONSIDER.** Apache-2.0; explicit, auditable pipelines favored in regulated settings — attractive given FERPA/ITAR. Viable alternative to LlamaIndex if you want stricter pipeline determinism.
- **Microsoft GraphRAG** — **CONSIDER (selectively).** MIT; strong for global/thematic multi-hop QA over a knowledge graph, but indexing is LLM-token-expensive. Use its *technique* (graph-grounded synthesis) on your AGE knowledge graph rather than adopting wholesale; avoid running its costly global-index build over confidential corpora.
- **Build vs. framework note:** keep retrieval (Qdrant/OpenSearch/AGE + RRF) as your own thin, swappable interface; use LlamaIndex/LangGraph as *libraries behind* that interface, not as the architecture — preserves the "pluggable modules, minimal blast radius" mandate and avoids framework lock-in.

---

## Recommended Default Stack

| Layer | Primary | Fallback | Rationale |
|---|---|---|---|
| Federation entry | **CILogon** | direct Keycloak SAML/OIDC brokering | One OIDC endpoint for 5,000+ academic IdPs; least onboarding effort |
| IdP / broker | **Keycloak** (Apache-2.0) | Ory (Kratos/Hydra) | Per-tenant realms; Ory if client-count scaling bites |
| Authz – ABAC (sensitivity) | **OPA/Rego** (Apache-2.0) | Cedar | Enforce public/private/confidential + FERPA/ITAR attributes |
| Authz – ReBAC (grants) | **OpenFGA** (Apache-2.0) | SpiceDB | Revocable cross-institution sharing relationships |
| Vector search | **Qdrant** (Apache-2.0) | pgvector | Best multi-tenant isolation/sharding; PG fallback for small tenants |
| Graph DB | **Apache AGE** (Apache-2.0) | Neo4j Community (GPLv3, isolate) / Memgraph (BSL) | Cypher-on-Postgres; co-locates w/ pgvector+OpenFGA; AVOID archived KuzuDB |
| Search / BM25 | **OpenSearch** (Apache-2.0) | Tantivy/Quickwit | Hybrid BM25+vector, LF-governed, no AGPL risk (vs Elasticsearch) |
| LLM serving (prod) | **vLLM** (Apache-2.0) | SGLang | Highest throughput; confidential-data self-host branch |
| LLM serving (dev) | **Ollama** (MIT) | llama.cpp | M4 Max local dev; not for multi-tenant prod |
| Embeddings | **SPECTER2** (sci) + **nomic-embed-v1.5** (general), both Apache-2.0 | BGE-M3 / GTE | Route by content type; all commercial-safe |
| Data orchestration | **Dagster** (Apache-2.0) | Prefect / Airflow | Asset-lineage fit for ingestion DAG |
| Durable workflows | **Temporal** (MIT/Apache-2.0) | — | Long-lived grant/revocation/workspace coordination |
| API | **FastAPI** (MIT) | — | Async, typed, OpenAPI; clean module boundaries |
| RAG ingestion/retrieval | **LlamaIndex** (MIT) | Haystack (Apache-2.0) | Library behind your own retrieval interface |
| Agent orchestration | **LangGraph** (MIT) | — | Expert-discovery & grant-team agents |
| Graph-grounded synthesis | **GraphRAG technique** (MIT) | native synthesizer | Use the method, not the costly global index, on confidential data |
| **Scholarly data (self-hosted)** | **OpenAlex snapshot (CC0)** + **Crossref annual file** + **OpenCitations (CC0)** + **arXiv metadata (CC0)** + **ROR (CC0)** + **ORCID Public Data File (CC0)** + **Semantic Scholar bulk (ODC-BY)** + **SPECTER2 vectors** | live polite-pool APIs for freshness | Own the corpus; avoid metering/non-commercial API traps |

---

## License / Risk Flags

- **AVOID Elasticsearch** — AGPLv3 network-copyleft is hostile to a commercial SaaS; OpenSearch (Apache-2.0) is the clean substitute.
- **AVOID KuzuDB** — archived 10 Oct 2025, read-only, no backing. MIT lets forks exist but assume zero support. Use Apache AGE.
- **AVOID HF TGI for new builds** — maintenance mode (Dec 2025); HF recommends vLLM/SGLang.
- **ORCID:** the **Public API is non-commercial** (verified verbatim). Use the **CC0 annual Public Data File** in-product; buy **Premium membership** only if you need live reads/writes. Do not ship the Public API.
- **OpenAlex:** live API is **metered** (per-credit price quote-gated — treat as unknown/contact-for-quote). **Self-host the free monthly CC0 snapshot**; never put the metered API on a hot path.
- **Semantic Scholar bulk = ODC-BY → attribution required**, and the API ToS forbids *reselling the API itself* (fine for our usage, but document attribution). SPECTER2 model = Apache-2.0 (no restriction).
- **PMC / Europe PMC full text is license-tiered** — programmatically gate to the **commercial-OK OA subset (CC0/BY/BY-SA/BY-ND)**; exclude NC-only records from any commercial feature. Bulk only via sanctioned endpoints (FTP/Cloud/OAI-PMH/E-utils).
- **CORE** commercial use is **membership-gated** — adopt only if you genuinely need its aggregated OA full text.
- **Neo4j Community = GPLv3** (copyleft, no clustering) and **Memgraph = BSL** (review prod terms; converts to Apache-2.0 after delay). If used, isolate behind a service boundary and keep them as fallbacks, not defaults.
- **Permify (authz)** is **AGPL-3.0** — excluded from the recommendation for that reason; OpenFGA/SpiceDB (Apache-2.0) preferred.
- **CILogon** is free for academic research but a **commercial deployment requires a paid subscription** — confirm pricing with CILogon and put it in COGS; not a license blocker, a cost line.
- **Crossref rate limits tightened 1 Dec 2025** — use the polite pool (mailto) and the annual public file; budget Metadata Plus if you need production freshness SLAs.
- **Export-control (ITAR/EAR):** the confidential tier must pin to the **self-hosted vLLM branch** with no cloud egress; enforce via OPA sensitivity policy at the model-router boundary. Treat any cloud-frontier routing of confidential data as a compliance defect, not a config choice.

**Net:** the verified-flag stack holds end-to-end. The dominant license hazards to design around are **Elasticsearch (AGPL), Neo4j (GPLv3), Memgraph (BSL), Permify (AGPL), the ORCID Public API (non-commercial), and OpenAlex API metering** — all avoidable via the Apache-2.0/CC0 primaries above.

**Key source URLs:** OpenAlex pricing/snapshot ([help.openalex.org](https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing), [developers.openalex.org](https://developers.openalex.org/how-to-use-the-api/rate-limits-and-authentication)); Semantic Scholar license ([api.semanticscholar.org/license](https://api.semanticscholar.org/license/)); SPECTER2 ([huggingface.co/allenai/specter2](https://huggingface.co/allenai/specter2)); ORCID API terms ([info.orcid.org integration guide](https://info.orcid.org/documentation/integration-guide/registering-a-public-api-client/)) + Public Data File ([info.orcid.org public-data-file](https://info.orcid.org/about/what-is-orcid/public-data-file)); KuzuDB archived ([github.com/kuzudb/kuzu](https://github.com/kuzudb/kuzu)); Crossref rate limits/license ([crossref.org rate-limits](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/), [metadata license](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-metadata-license-information/)); OpenCitations ([opencitations.net](https://opencitations.net/)); arXiv bulk ([info.arxiv.org/help/bulk_data](https://info.arxiv.org/help/bulk_data.html)); PMC OA subset ([pmc.ncbi.nlm.nih.gov/tools/openftlist](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/)), E-utils limits ([Europe PMC](https://europepmc.org/RestfulWebService)); CILogon ([cilogon.org/faq](https://www.cilogon.org/faq), [oidc](https://www.cilogon.org/oidc)); authz ([authzed.com](https://authzed.com/learn/openfga-alternatives), [auth0 ReBAC/ABAC](https://auth0.com/blog/rebac-abac-openfga-cedar/)); vector DBs ([callsphere benchmark](https://callsphere.ai/blog/vector-database-benchmarks-2026-pgvector-qdrant-weaviate-milvus-lancedb)); Apache AGE vs Neo4j/Memgraph ([gdotv](https://gdotv.com/blog/apache-age-explained/), [arcadedb](https://arcadedb.com/blog/neo4j-alternatives-in-2026-a-fair-look-at-the-open-source-options/)); OpenSearch vs ES license ([pureinsights](https://pureinsights.com/blog/2025/elasticsearch-vs-opensearch-in-2025-what-the-fork/)); vLLM/TGI ([buildwithmatija](https://www.buildwithmatija.com/blog/vllm-vs-ollama-vs-tgi-choose-llm-inference-engine), [HF TGI multi-backend](https://huggingface.co/blog/tgi-multi-backend)); orchestration ([pracdata state-of-orchestration](https://www.pracdata.io/p/state-of-workflow-orchestration-ecosystem-2025)); RAG frameworks ([alphacorp](https://alphacorp.ai/top-5-rag-frameworks-november-2025/), [aimultiple](https://aimultiple.com/rag-frameworks)).