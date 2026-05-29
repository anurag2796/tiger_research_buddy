# Research: retrieval-rag-kg

I now have comprehensive, well-sourced coverage across all eight topic areas with concrete numbers, arXiv IDs, and licensing/self-hostability details. Let me synthesize the final report.

---

# State of the Art for the AI/Retrieval Core (2023–2026)
## Federated Multi-University Research Discovery Platform

This report covers the eight requested areas, mapping each to the locked platform constraints: **federated hybrid deployment**, **public/private/confidential data tiers**, a **provider-agnostic model router** (local vLLM/Ollama for confidential, cloud frontier for public, BYO-key per institution), and **modular-to-the-bone** architecture. Every recommendation is tagged MVP-essential vs overkill at the end.

A recurring theme: because confidential data must stay inside each institution's boundary and route to **self-hosted models**, the architecture is constrained to **open, self-hostable** components for the confidential tier. Cloud frontier models (and Voyage/Cohere APIs) are usable only for the **public tier** or where an institution explicitly opts in via BYO-key. This single constraint disqualifies several otherwise-leading proprietary choices for the confidential path, so I weight open models heavily.

---

## 1. Hybrid Retrieval: Dense + Sparse, RRF vs Learned Fusion

**Consensus (2023–2026):** Hybrid (dense vector + sparse lexical) consistently beats either alone, with reported recall improvements of **15–30%** over single-method retrieval. The two signals are complementary: dense embeddings capture semantic/paraphrase matches; sparse (BM25 / learned-sparse SPLADE) captures exact terms, rare entities, acronyms, author names, grant numbers, gene names — exactly the high-precision tokens that dominate scientific and institutional corpora.

**When hybrid wins most:** out-of-domain queries, queries with rare named entities (faculty names, lab names, specific instruments/datasets), and short keyword queries. This is squarely your domain — academic search is entity-heavy, so **sparse is not optional**.

**RRF vs learned fusion:**
- **RRF (Reciprocal Rank Fusion, k≈60)** is the parameter-free, zero-tuning industry baseline. It uses ranks not scores, so it sidesteps the score-normalization problem (cosine similarity vs BM25 scores are not comparable). It rewards cross-retriever agreement and prevents any single retriever from dominating. Robust in zero-shot/cold-start.
- **Learned / convex score combination** (weighted normalized blend) can edge out RRF when you have in-domain training data — one 2024–2025 result shows convex combination at **Recall@5 = 0.726 vs RRF's 0.695**. LambdaMART-style learned rerankers over fused candidate sets are the next step up but require labeled relevance data you won't have at launch.

**Guidance: Use RRF at MVP because** you have no labeled relevance data on day one, it needs zero tuning, and it is robust across the heterogeneous corpora of many institutions (each tenant has a different term distribution — a tuned weight set wouldn't transfer). **Move to learned convex fusion (or LambdaMART) per-tenant later**, once click/relevance feedback accumulates inside a node. Critically, fusion weights should be **tenant-local** — learned fusion is a per-node refinement, never a global one, which fits the federated isolation model cleanly.

Sources: [When to use Graphs in RAG (arXiv:2506.05690)](https://arxiv.org/html/2506.05690v3), [RRF hybrid dense-sparse (CEUR Vol-4173)](https://ceur-ws.org/Vol-4173/T3-7.pdf), [From BM25 to Corrective RAG benchmarking](https://arxiv.org/pdf/2604.01733), [TREC TOT 2025 fusion+learned reranking (arXiv:2601.15518)](https://arxiv.org/pdf/2601.15518)

---

## 2. Embeddings for Scientific Text

The tension is **domain-specialized scientific models** (SPECTER2, SciNCL) vs **general-purpose SOTA models** (BGE, GTE/Qwen3, E5, nomic, Voyage, Cohere). For scientific retrieval the answer is nuanced.

### Domain-specialized
- **SPECTER2** (allenai, Apache-2.0, SciBERT base, 768-dim): trained on **6M citation triplets across 23 fields**, with task-specific **adapters** (proximity/retrieval, classification, regression, ad-hoc search). Best-in-class for **paper-to-paper / citation-proximity** ("find related papers to this one") and document-level scientific representation on SciRepEval (24 tasks). Fully open and self-hostable (HF + GitHub). Limitation: older SciBERT backbone, 512-token cap, single-vector; underperforms modern large general models on *ad-hoc natural-language query → passage* retrieval.
- **SciNCL** (SciBERT base): SOTA on SciDocs via nearest-neighbor (rather than hard-citation) contrastive sampling. Same era/limitations as SPECTER2; strong for document similarity, weaker for free-text Q&A retrieval.
- Both inherit a **CS/BioMed training-data skew (~70%)** — flag distribution risk for under-represented fields.

### General-purpose SOTA (these dominate ad-hoc query→passage retrieval, which is what RAG Q&A needs)
- **Qwen3-Embedding** (0.6B / 4B / 8B, **Apache-2.0**): 8B hit **#1 MTEB multilingual = 70.58** (June 2025), beating Gemini-Embedding; 100+ languages, code, MRL support, instruction-aware. The strongest **open, self-hostable** option — directly usable on the confidential path via vLLM. The **0.6B** variant is the practical pick for the M4 Max dev box / smaller nodes.
- **BGE-M3** (BAAI, MIT, ~568M): the workhorse — **multi-vector + dense + sparse in one model**, 100+ languages, 8192-token context, MRL. Its built-in learned-sparse output can serve as your sparse leg, simplifying the hybrid stack into one model. ~63 MTEB.
- **GTE-Qwen2 / GTE-large**: strong open mid-tier.
- **nomic-embed-text-v1.5** (Apache-2.0, 137M, MRL 64–768, 8192 ctx): currently in TigerResearchBuddy. Excellent efficiency/latency on Apple Silicon; good MVP default but materially behind Qwen3/BGE-M3 on quality.
- **E5 / multilingual-E5**: solid open baseline, now eclipsed by Qwen3.
- **Voyage (voyage-3/4 family) and Cohere embed-v4 (~65.2 MTEB)**: top-tier *quality*, but **API/proprietary** → **public-tier or BYO-key only**, never the confidential path.

### Matryoshka (MRL)
MRL trains nested embeddings usable after truncation (e.g., 768→256→128→64) with minimal quality loss — OpenAI's 256-dim beats old ada-002 at 1536-dim. **Operationally essential for a federated multi-tenant system:** store full-dim for quality, truncate for cheap candidate generation, cut vector-index storage/RAM per node. Supported by Qwen3, BGE-M3, nomic-v1.5, Gemini. Use the **MRL adaptive-retrieval pattern**: shortlist on truncated dims, re-score top-k on full dims.

**Guidance:**
- **Confidential path (self-hosted, required):** **Qwen3-Embedding (0.6B dev / 4B–8B prod via vLLM)** as the primary RAG retriever, **because** it is Apache-2.0, MTEB-leading, multilingual, and MRL-capable.
- **Scientific paper-similarity / citation features:** add **SPECTER2** as a *second, purpose-built embedding space* for the "related work / similar papers / expertise fingerprint" features — it beats general models on citation-proximity. This is a modular plug-in retriever, not the main one.
- **BGE-M3** is the strong alternative if you want **dense+sparse from a single model** to reduce moving parts.
- **Public tier / BYO-key:** allow Voyage/Cohere/Gemini through the router as opt-in quality upgrades.

Sources: [SPECTER2 (Ai2)](https://allenai.org/blog/specter2-adapting-scientific-document-embeddings-to-multiple-fields-and-task-formats-c95686c06567), [SciRepEval (arXiv:2211.13308)](https://arxiv.org/pdf/2211.13308), [Qwen3-Embedding (arXiv:2506.05176)](https://arxiv.org/abs/2506.05176), [MTEB leaderboard shakeup (VentureBeat)](https://venturebeat.com/ai/new-embedding-model-leaderboard-shakeup-google-takes-1-while-alibabas-open-source-alternative-closes-gap), [Nomic Embed Matryoshka](https://www.nomic.ai/news/nomic-embed-matryoshka), [Scientific Paper Retrieval EMNLP 2025 Findings](https://aclanthology.org/2025.findings-emnlp.108.pdf)

---

## 3. Reranking

Reranking is the single highest-ROI quality lever after hybrid retrieval: typical **+5 to +15 nDCG@10**, up to **+20 on lexically hard sets**, for **<200ms** added latency on a small/mid cross-encoder.

| Type | Examples | Quality | Latency / Cost | Self-host |
|---|---|---|---|---|
| **Cross-encoder** | BGE-reranker-v2-m3, Qwen3-Reranker-0.6B/4B, Jina-reranker-v2/v3 | Highest per-pair | 3.5–11s for large depth; ~sub-200ms for small model at depth ~50 | Yes (Apache/MIT) |
| **Late interaction** | ColBERTv2 + PLAID | Near cross-encoder | 2 orders of magnitude faster than cross-encoder; PLAID 7× GPU / 45× CPU vs vanilla ColBERTv2 | Yes |
| **LLM reranker** | GPT/Claude/Qwen as judge, RankGPT | Very high, reasoning-aware | Slow + costly; confidential→local LLM | Local only for confidential |
| **API reranker** | Cohere Rerank 3.5 (~$2/1k SU) | Top hosted | Fast, no infra | No → public/BYO only |

- **Cross-encoder is the default reranker.** For the confidential path: **BGE-reranker-v2-m3** (multilingual, Apache-2.0, the self-hosted default) or **Qwen3-Reranker-0.6B/4B** (Apache-2.0, pairs with Qwen3 embeddings — single model family reduces ops surface).
- **ColBERTv2/PLAID** is the late-interaction middle ground: cross-encoder-ish quality at dense-retrieval-ish latency, with residual compression cutting index from 256→**20–36 bytes/vector** (6–10× smaller). But it adds a *whole separate index type* per tenant. Note the 2026 practitioner view: for most teams **bi-encoder + cross-encoder reranker is simpler and roughly equivalent** — ColBERT is increasingly niche. Skip at MVP.
- **LLM rerankers**: reserve for top-5 reordering in high-stakes flows; on confidential data they must run on the local model, so budget latency. Overkill for MVP.

**Guidance: rerank top-50→top-8 with BGE-reranker-v2-m3 (or Qwen3-Reranker) on the confidential path; allow Cohere Rerank 3.5 as a public/BYO upgrade.** This is MVP-essential — it is the cheapest large quality win. Run the reranker as a **router-managed module** so a node can swap local↔hosted by data tier.

Sources: [Open-source alternatives to Cohere Rerank (ZeroEntropy)](https://zeroentropy.dev/articles/open-source-alternatives-to-cohere-rerank/), [Reranking guide (Local AI Master)](https://localaimaster.com/blog/reranking-cross-encoders-guide), [jina-reranker-v3 LBNL (arXiv:2509.25085)](https://arxiv.org/html/2509.25085v2), [Qwen3-Reranker HF](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B/blob/main/README.md), [PLAID (arXiv:2205.09707)](https://arxiv.org/pdf/2205.09707), [ColBERT in Practice (Sease)](https://sease.io/2025/11/colbert-in-practice-bridging-research-and-industry.html)

---

## 4. GraphRAG / KG-Augmented Retrieval

The 2025 **GraphRAG-Bench** ("When to use Graphs in RAG", arXiv:2506.05690, ICLR'26) gives the clearest evidence-based answer, and it cuts against over-using graphs.

**When KG+RAG genuinely helps:**
- **Multi-hop reasoning** across disconnected segments (HippoRAG2 **61.98%** vs RAG **58.64%** on a medical set; HippoRAG up to **+20%** on multi-hop QA).
- **Contextual summarization / sense-making** (GraphRAG ~63–67%).
- **Creative/synthesis generation** (RAPTOR **70.85%** faithfulness vs RAG **36.74%**).

**When it does NOT help (and adds cost):**
- **Simple fact retrieval** — vanilla RAG matches or beats graphs (RAG ~**87.83%** evidence recall).
- The token/cost penalty is severe: **MS-GraphRAG global ≈ 331k tokens/query** and offline indexing is expensive; **LightRAG ≈ 100k**; **HippoRAG2 ≈ 1k**; standard RAG ≈ 900. Indexing cost (LLM entity/relation extraction over the whole corpus) is the real tax, and it recurs on every update.

**Architecture comparison:**
- **Microsoft GraphRAG**: community detection + hierarchical summarization; best for global "what are the themes across the corpus" questions; highest cost; sparse graphs hurt (MS-GraphRAG 1.82 avg degree → 5.67% context relevance).
- **LightRAG**: dual-level retrieval, merges neighboring subgraphs; cheaper, lower latency than MS-GraphRAG; good multi-hop/scalability balance.
- **HippoRAG / HippoRAG2** (NeurIPS'24, arXiv:2405.14831 / 2502.14802): KG + **Personalized PageRank** mimicking hippocampal indexing; **best cost/quality trade-off** — strong multi-hop with **~1k tokens/query** and far cheaper offline indexing than GraphRAG/RAPTOR/LightRAG. Graph density matters (denser graph → better recall). Designed for **continual knowledge integration**, which fits an ever-growing research corpus.

**Entity/relation extraction from papers:** all graph methods depend on LLM-extracted entities/relations; quality is gated by extraction and by **author/entity resolution** (see §6). Ontology choice matters (arXiv:2511.05991). For scientific corpora, lean on existing structure (citations, authorship, affiliations, venues, grants) as a **deterministic backbone graph** before adding LLM-extracted concept edges — this avoids paying full GraphRAG indexing tax for relationships you already have for free in metadata.

**Guidance for this platform:** Your **knowledge graph is dual-purpose**: (a) a *product feature* (collaborator/expert discovery, cross-institution team assembly — §7) and (b) a *retrieval augmentation*. For (a) the graph is mandatory regardless. For (b), **do NOT adopt MS-GraphRAG-style full corpus summarization at MVP** — the per-query token cost and re-indexing burden are unjustified for mostly-factual Q&A and are punishing in a multi-tenant federated setting. Instead:
- Build a **metadata-backbone graph** (authors, papers, citations, affiliations, venues, grants, topics) — cheap, deterministic, no LLM tax.
- Add **HippoRAG2-style PPR retrieval** as the graph-augmentation path **because** it delivers multi-hop gains at ~1k tokens and the lowest indexing cost — the only graph method whose economics survive per-tenant deployment.
- Treat community-summarization GraphRAG as a **later, opt-in module** for "global synthesis" queries.

Per-tenant note: each node builds its own graph over its own data; the **exchange layer** federates only *grant-scoped* nodes/edges, never the full graph. Graph augmentation must therefore be a node-local module with a federation adapter.

Sources: [GraphRAG-Bench / When to use Graphs (arXiv:2506.05690)](https://arxiv.org/html/2506.05690v3), [GraphRAG-Bench repo](https://github.com/GraphRAG-Benchmark/GraphRAG-Benchmark), [HippoRAG (arXiv:2405.14831)](https://arxiv.org/abs/2405.14831), [HippoRAG2 / From RAG to Memory (arXiv:2502.14802)](https://arxiv.org/html/2502.14802v1), [GraphRAG vs LightRAG (Maarga)](https://www.maargasystems.com/2025/05/12/understanding-graphrag-vs-lightrag-a-comparative-analysis-for-enhanced-knowledge-retrieval/), [Ontology learning + RAG (arXiv:2511.05991)](https://arxiv.org/pdf/2511.05991)

---

## 5. Agentic / Multi-Step RAG

The reference survey is **"Agentic RAG: A Survey" (arXiv:2501.09136)**, which formalizes the taxonomy: single-agent router, multi-agent, hierarchical, **Corrective RAG (CRAG)**, **Adaptive RAG**, **Self-RAG**, graph-based agentic, and agentic document workflows.

Key patterns and when to use:
- **Self-RAG** (Asai et al., ICLR 2024, arXiv:2310.11511): reflection tokens (IsREL/IsSUP/IsUSE) let the model decide *whether* to retrieve and *self-critique* grounding. Reduces hallucination; needs a model trained/prompted for reflection.
- **Corrective RAG / CRAG** (Yan et al., arXiv:2401.15884): lightweight retrieval evaluator scores docs as correct/ambiguous/incorrect → triggers query rewrite or fallback retrieval. **~15–25% added latency**, but high-value for **high-factuality** domains. Most relevant to your **literature-intelligence** feature where wrong citations are unacceptable.
- **Adaptive RAG**: a small classifier predicts query difficulty → no-retrieval / single-step / multi-step. The **cost-control workhorse** — avoids paying multi-hop cost on trivial queries. Pairs perfectly with your model router (it's effectively a *retrieval-strategy* router alongside the *model* router).
- **Query decomposition / planning**: break complex queries ("find me a co-PI for an NSF proposal on federated learning for medical imaging across institutions") into sub-queries — directly enables grant/team-assembly (§7).
- **Multi-agent / hierarchical**: specialized agents per source with a coordinator; useful when querying across heterogeneous tiers/institutions, but coordination cost is real.

**When agentic is worth it (per the survey):** multi-hop reasoning, high error-cost domains, mixed simple/complex workloads (Adaptive saves cost), real-time/changing context. **When simple single-shot RAG suffices:** homogeneous fact lookups, single-source, latency-critical, low error tolerance.

**Guidance:** Ship **single-shot hybrid+rerank RAG first.** Add **Adaptive RAG routing** early (cheap, big cost savings, and it dovetails with the model router). Add **CRAG-style corrective loop** for the literature-intelligence module **because** citation faithfulness is the credibility differentiator for a research tool. Reserve full **multi-agent / query-decomposition planning** for the **grant/team-assembly** feature (genuinely multi-step). On the confidential path every agent step runs against the local model — budget latency accordingly and cap loop iterations. Build each pattern as an **interchangeable orchestration module** behind one retrieval interface.

Sources: [Agentic RAG Survey (arXiv:2501.09136)](https://arxiv.org/html/2501.09136v4), [Reasoning Agentic RAG survey (arXiv:2506.10408)](https://arxiv.org/html/2506.10408v1), [Self-RAG (arXiv:2310.11511)], [CRAG (arXiv:2401.15884)], [AgenticRAG-Survey repo](https://github.com/asinghcsu/AgenticRAG-Survey)

---

## 6. Entity Resolution + Author Disambiguation Across Institutions

This is **foundational, not optional**: your graph, expertise model, and cross-institution discovery all collapse if "J. Smith @ RIT" and "John Smith @ MIT" are mishandled. Multi-affiliation and name collisions are the core problem, amplified in a *federated* setting where each node sees only partial publication history.

State of the art (2016–2024 deep-learning survey, Springer IJDL 2025; arXiv:2503.13448):
- **Use ORCID as the deterministic anchor wherever present** — it resolves ambiguity at the source. Build the resolution layer to prefer ORCID/DOI/author-ID, then fall back to ML only for unmatched records.
- **Graph + embedding methods** dominate: co-authorship topology + content (titles/abstracts) features; heterogeneous network representation learning (NAND-style neural disambiguators) scale to large libraries with sparse metadata.
- **LLM-enhanced disambiguation — LEAD (arXiv:2511.07168)**: LLMs reason over **co-author networks, affiliations, research topics, and publication metadata** to merge/split identities; evaluated on Scopus + Italian university records; open-source (`fossr-project/LEAD`). The 2024–2026 direction is **hybrid: deterministic ID anchors + graph features + LLM adjudication on hard cases**.

**Federated wrinkle (critical):** disambiguation across institutions must happen **without centralizing private records**. Options: (a) resolve **public-tier identity only** in the exchange layer (publications, ORCID, public profiles) and keep private attributes node-local; (b) **privacy-preserving / blocking-based matching** so candidate pairs are compared on minimal shared features through explicit sharing grants. Treat the cross-institution identity graph as **public-tier by construction** — never let disambiguation become a confidentiality leak.

**Guidance:** MVP — **deterministic resolution (ORCID/DOI/Semantic Scholar/OpenAlex author IDs) + blocking + a graph-feature classifier**; this gets you most of the way using already-public scholarly identifiers. Add **LLM adjudication (LEAD-style)** for hard collisions in a later phase. Implement as a standalone **Identity Resolution service** with a clean interface — it is consumed by graph build, expertise modeling, and discovery alike (modularity requirement).

Sources: [DL for Author Name Disambiguation survey (Springer IJDL 2025)](https://link.springer.com/article/10.1007/s00799-025-00428-6), [Recent Developments in DL-based AND (arXiv:2503.13448)](https://arxiv.org/pdf/2503.13448), [LEAD (arXiv:2511.07168)](https://arxiv.org/pdf/2511.07168)

---

## 7. Expertise Modeling + Collaborator Recommendation

This is your **differentiated product surface** (features 1 and 4), and it reduces to **retrieval + ranking + link prediction** over the academic graph.

State of the art (2024–2025):
- **Expertise modeling = profile-as-retrieval.** Aggregate each researcher's corpus (papers, abstracts, grants, distilled research cards) into an **expertise embedding/fingerprint**; "find an expert for X" becomes embedding retrieval + reranking over researcher profiles. WISER-style entity-linking grounds expertise to a concept vocabulary. SPECTER2 fingerprints (§2) are well-suited here because they're citation-aware.
- **Collaborator recommendation = link prediction on heterogeneous academic graphs.** 2024 SOTA uses **GNNs over heterogeneous networks** combining co-authorship + citation topology with **multi-dimensional node attributes** (the MAH method; SIGIR/ICTIR 2025 "Expert Finding Revisited"). Content-based + structure-based features fused beat either alone — the same dense+structure complementarity as §1/§4.
- "Find a collaborator for grant X" is a **two-stage retrieve-then-rank**: (1) retrieve candidate experts by topical match; (2) re-rank by complementarity, collaboration likelihood (link prediction), availability, and **cross-institution eligibility**.

**Federated/cross-institution angle (your moat):** the highest-value query — "assemble a cross-institution team for this funding call" — requires link prediction across the **federated public-tier graph**, ranking on topical fit + predicted collaboration success + funding-history signals, while respecting that confidential signals stay node-local. This is feature (4) and the strongest defensibility vs single-institution tools.

**Guidance:** MVP — **expertise fingerprints (SPECTER2/Qwen3 profile embeddings) + retrieval + reranker** for "find an expert" (reuses the §2/§3 stack — minimal new infra). Phase 2 — **GNN link prediction** over the heterogeneous graph for "recommend a collaborator." Phase 3 — **cross-institution team assembly** over the federated graph for grant intelligence. Build as a **Discovery module** consuming the Identity service (§6) and the graph (§4).

Sources: [Academic collaboration recommendation via GNN + multi-attribute embedding (SAGE 2024)](https://journals.sagepub.com/doi/abs/10.1177/01655515241287635), [Expert Finding Revisited (SIGIR/ICTIR 2025)](https://dl.acm.org/doi/10.1145/3731120.3744618), [Predicting scholar collaboration (Scientometrics 2024)](https://ideas.repec.org/a/spr/scient/v129y2024i6d10.1007_s11192-024-05012-4.html), [WISER expert finding (arXiv:1805.03947)](https://arxiv.org/pdf/1805.03947)

---

## 8. Evaluation

Without an eval harness you cannot prove non-regression across tenants, model-router swaps, or feature toggles — and in a federated/compliance context you must be able to demonstrate quality per node. Split into **retrieval** and **generation** metrics.

**Retrieval (offline, with labels):** **Recall@k, Precision@k, MRR, nDCG@k**. nDCG correlates best with end-to-end RAG quality, so make it the headline retrieval metric. Use **BEIR/MTEB** for component selection; build a **small in-domain labeled set per representative corpus** for regression gates.

**Generation (RAG-specific):** **RAGAS** (YC W24) is the de-facto framework — **Faithfulness/Groundedness** (every claim supported by retrieved context), **Context Precision**, **Context Recall**, **Answer Relevance**, all via **LLM-as-judge**. Faithfulness is the metric to gate on for a research tool (no fabricated citations).

**LLM-as-judge caveats:** controversial but accepted; mitigate with reference answers where possible, pairwise comparison, and a fixed judge model. **Confidentiality wrinkle:** on the confidential tier the **judge LLM must also be the local/self-hosted model** — you cannot send confidential answers/contexts to a cloud judge. So your eval harness must be **router-aware**, picking the judge by data tier exactly like inference.

**2025 best practice:** offline test runs + **node-level (granular) evals** + automated log evaluation + **CI/CD quality gates** that block regressions. For this platform: run eval **per tenant and per model-route**, so swapping a node's local model or toggling a module is gated by measured quality.

**Guidance:** MVP — **RAGAS (faithfulness, context precision/recall) + nDCG@k/Recall@k on a small in-domain gold set, wired into CI as a regression gate, with a tier-aware (local) judge.** This is MVP-essential precisely because the whole pitch is "trustworthy, grounded research intelligence" — you must measure it.

Sources: [RAGAS deep dive (Cohorte)](https://cohorte.co/blog/evaluating-rag-systems-in-2025-ragas-deep-dive-giskard-showdown-and-the-future-of-context), [Complete Guide to RAG Evaluation 2025 (Maxim)](https://www.getmaxim.ai/articles/complete-guide-to-rag-evaluation-metrics-methods-and-best-practices-for-2025/), [RAG evaluation guide (Evidently)](https://www.evidentlyai.com/llm-guide/rag-evaluation), [MTEB (arXiv:2210.07316)](https://arxiv.org/abs/2210.07316)

---

# Recommended Retrieval Architecture

A single **tenant-local retrieval engine** behind one clean interface, with a **model router** selecting local-vs-cloud per data tier, and a thin **federation/exchange adapter** for cross-institution (public-tier) discovery. Confidential data and its models never leave the node.

| Layer | Recommendation | Why | MVP vs Overkill |
|---|---|---|---|
| **Primary embedding** | **Qwen3-Embedding** (0.6B dev / 4B–8B prod, vLLM), MRL-truncated for shortlist | Apache-2.0, MTEB-leading, multilingual, self-hostable on confidential path | **MVP-essential** |
| **Scientific/citation embedding** | **SPECTER2** as second space for paper-similarity & expertise fingerprints | Beats general models on citation-proximity; open | **MVP-essential** (powers discovery wedge) |
| **Sparse leg** | **BM25** (or BGE-M3 learned-sparse) | Entity/acronym/name precision; no labels needed | **MVP-essential** |
| **Index** | Per-tenant vector DB (Qdrant/Milvus/pgvector) + BM25; HNSW; MRL two-stage (truncated shortlist → full re-score) | Horizontal scale, isolation, RAM control per node | **MVP-essential** |
| **Hybrid fusion** | **RRF (k≈60)** now; **per-tenant learned convex fusion** later | Zero-tuning, robust cold-start, no transfer issues across tenants | **MVP-essential** (RRF); learned = later |
| **Reranker** | **BGE-reranker-v2-m3** or **Qwen3-Reranker** (local); Cohere Rerank 3.5 as public/BYO upgrade | +5–15 nDCG@10 for <200ms; biggest cheap win; tier-routable | **MVP-essential** |
| **Graph backbone** | Deterministic metadata graph (authors/papers/citations/affiliations/grants/venues) | Cheap, no LLM-extraction tax; powers discovery + augmentation | **MVP-essential** |
| **Graph augmentation** | **HippoRAG2-style PPR** for multi-hop; community-summarization GraphRAG opt-in later | ~1k tokens/query, lowest indexing cost — only graph economics that survive per-tenant | **Phase 2**; MS-GraphRAG global = **overkill at MVP** |
| **Agentic orchestration** | Single-shot first → **Adaptive RAG** routing → **CRAG** for lit-intel → query-decomposition for grants | Pay multi-step cost only when query complexity/error-cost justifies | Adaptive = early; CRAG = Phase 2; multi-agent = **later** |
| **Identity resolution** | Deterministic (ORCID/DOI/OpenAlex IDs) + blocking + graph classifier; **LEAD-style LLM** for hard cases later | Foundational for graph/discovery; public-tier-only to avoid leakage | **MVP-essential** (deterministic); LLM adjudication = later |
| **Expertise / collaborator** | Profile fingerprints + retrieve+rerank (MVP) → GNN link prediction → cross-institution team assembly | Reuses embedding+reranker stack; differentiator | "Find expert" = **MVP**; GNN/team-assembly = **Phase 2–3** |
| **Eval harness** | **RAGAS** (faithfulness, context P/R) + **nDCG@k/Recall@k** gold set, CI gate, **tier-aware local judge**, per-tenant | Proves grounding + non-regression across model-router swaps | **MVP-essential** |

### MVP wedge recommendation
**Beachhead = bottom-up PLG: "grounded literature intelligence + expert discovery" for individual researchers/labs inside one institution** (single-tenant, public + private tiers; confidential tier via local model from day one to prove the isolation story without needing the federation layer live).

Ship: **Qwen3 + SPECTER2 embeddings → BM25+RRF hybrid → BGE/Qwen3 reranker → metadata graph → single-shot RAG → RAGAS+nDCG eval gate → deterministic identity resolution → "find an expert" retrieve+rerank.**

Defer (architecture stays identical, only build order changes): HippoRAG graph augmentation, CRAG/Adaptive/multi-agent orchestration, GNN link prediction, the **cross-institution exchange layer**, and learned fusion. Each is a pluggable module behind the established interfaces, satisfying the modular-to-the-bone and "one product, configurable editions" constraints.

### Explicitly flagged as overkill at MVP
- **Microsoft GraphRAG global community summarization** — ~331k tokens/query + heavy recurring indexing; unjustified for mostly-factual Q&A and brutal in multi-tenant.
- **ColBERTv2/PLAID** — separate index type per tenant; bi-encoder + cross-encoder reranker is simpler with comparable quality in 2026.
- **Multi-agent/hierarchical orchestration** — coordination cost without payoff until grant/team-assembly is in scope.
- **LLM rerankers on every query** — reserve for top-5 high-stakes reordering only.
- **Learned/LambdaMART fusion** — needs per-tenant labels you won't have at launch; RRF first.

Key arXiv references: 2506.05690 (GraphRAG-Bench), 2405.14831 / 2502.14802 (HippoRAG / HippoRAG2), 2501.09136 (Agentic RAG survey), 2310.11511 (Self-RAG), 2401.15884 (CRAG), 2506.05176 (Qwen3-Embedding), 2211.13308 (SciRepEval/SPECTER2), 2511.07168 (LEAD author disambiguation), 2503.13448 (AND survey), 2205.09707 (PLAID), 2210.07316 (MTEB).