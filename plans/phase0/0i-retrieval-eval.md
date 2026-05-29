I have everything I need. The `tigerexchange/` directory does not yet exist (it's scaffolded by dependency sub-plans `0a`–`0h`). My plan builds the retrieval + PEP-gated eval layer on top of the canonical kernel and those dependencies. Now I'll write the complete implementation plan.

# Hybrid Retrieval (Qdrant + OpenSearch + RRF + Reranker) + PEP-Gated RAGAS Eval Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the Phase-0 hybrid retrieval core behind `IRetrievalStrategy` (Qdrant vector + OpenSearch BM25 + RRF k≈60 + local BGE/Qwen3 reranker top-50→top-8), expose it for `mod-lit-intelligence` proposal grounding, and ship a RAGAS-in-CI release gate that is a first-class PEP-gated confidential flow (per-tenant gold-sets, eval traces, and judge I/O are confidential-tier artifacts living in the cell, KEK-encrypted, in-boundary-judge-only).

**Architecture:** Two engine adapters (`QdrantVectorStore`, `OpenSearchLexicalIndex`) sit behind kernel interfaces; a `HybridRetriever` fuses their results with RRF, reranks with a local cross-encoder, and returns already-PEP-gated `PublishableProjection`s by routing every candidate through `IPolicyEnforcement.authorize`. The eval harness mirrors the *same* PEP/router controls onto the measurement path: gold-sets/traces/judge-I-O are written only via the KEK-encrypted confidential derivative store, the judge model is selected via `IModelRouter.route` (which fails closed to in-boundary), and a per-subject erasure hook crypto-shreds eval artifacts. RAGAS metrics + nDCG@k/Recall@k run in CI as a regression gate.

**Tech Stack:** Python 3.11+, Pydantic v2, Qdrant (`qdrant-client`), OpenSearch (`opensearch-py`), FlagEmbedding/sentence-transformers reranker (BGE-reranker-v2-m3), RAGAS, FastAPI, pytest/ruff/mypy. All engines run via testcontainers/local in CI; the confidential judge runs on vLLM (never the M4 Max).

**Depends on:** `0c-pep-broker-chokepoint`, `0f-model-router`, `0g-confidential-kek-stores`, `0h-ingestion-pipelines`

---

## File Structure

| File | Created/Modified | Single responsibility |
|---|---|---|
| `tigerexchange/packages/retrieval/pyproject.toml` | Create | Package metadata + deps (qdrant-client, opensearch-py, FlagEmbedding, ragas) + import-linter contract forbidding raw-store/classifier imports from feature modules. |
| `tigerexchange/packages/retrieval/src/retrieval/__init__.py` | Create | Public import surface for the retrieval package. |
| `tigerexchange/packages/retrieval/src/retrieval/config.py` | Create | Frozen `RetrievalConfig` (RRF k, top_n candidate, top_k rerank, collection/index names, embed/rerank model ids). |
| `tigerexchange/packages/retrieval/src/retrieval/vector_store.py` | Create | `QdrantVectorStore` adapter — vector search returning scored candidate refs. |
| `tigerexchange/packages/retrieval/src/retrieval/lexical_index.py` | Create | `OpenSearchLexicalIndex` adapter — BM25 search returning scored candidate refs. |
| `tigerexchange/packages/retrieval/src/retrieval/rrf.py` | Create | Pure RRF fusion (k≈60) over ranked candidate lists. |
| `tigerexchange/packages/retrieval/src/retrieval/reranker.py` | Create | `LocalCrossEncoderReranker` (BGE/Qwen3) implementing `IReranker`, top-50→top-8. |
| `tigerexchange/packages/retrieval/src/retrieval/hybrid_retriever.py` | Create | `HybridRetriever` implementing `IRetrievalStrategy` — fuse → rerank → PEP-gate → project. |
| `tigerexchange/packages/retrieval/src/retrieval/types.py` | Create | `Candidate` value object (engine-agnostic scored ref shared by stores/RRF/reranker). |
| `tigerexchange/packages/retrieval/src/eval/__init__.py` | Create | Public import surface for the eval harness. |
| `tigerexchange/packages/retrieval/src/eval/types.py` | Create | `GoldItem`, `EvalTrace`, `JudgeIO`, `EvalReport` confidential-tier value objects. |
| `tigerexchange/packages/retrieval/src/eval/confidential_store.py` | Create | `ConfidentialEvalStore` — KEK-encrypted persistence of gold-sets/traces/judge-I-O + per-subject crypto-shred. |
| `tigerexchange/packages/retrieval/src/eval/judge_router.py` | Create | `route_judge` — binds judge-model selection to `IModelRouter` (fails closed to in-boundary on confidential). |
| `tigerexchange/packages/retrieval/src/eval/harness.py` | Create | `EvalHarness` — runs RAGAS + nDCG@k/Recall@k per-tenant/per-route through the PEP, persists traces via the confidential store, emits `EvalReport`. |
| `tigerexchange/packages/retrieval/src/eval/gate.py` | Create | `assert_no_regression` — release-gate comparison against pinned baseline thresholds. |
| `tigerexchange/packages/retrieval/tests/conftest.py` | Create | Shared fakes: `FakePEP`, `FakeModelRouter`, `FakeKEKStore`, fixture tenants. |
| `tigerexchange/packages/retrieval/tests/test_rrf.py` | Create | RRF fusion unit tests. |
| `tigerexchange/packages/retrieval/tests/test_reranker.py` | Create | Reranker ordering + top_k truncation tests. |
| `tigerexchange/packages/retrieval/tests/test_hybrid_retriever.py` | Create | Retriever PEP-gating + projection tests (quarantined/denied excluded). |
| `tigerexchange/packages/retrieval/tests/test_eval_confidential_store.py` | Create | KEK-encryption + crypto-shred + per-subject erasure contract tests. |
| `tigerexchange/packages/retrieval/tests/test_eval_judge_routing.py` | Create | Contract test: confidential eval cannot route to a cloud judge. |
| `tigerexchange/packages/retrieval/tests/test_eval_harness.py` | Create | Harness runs through PEP, persists confidential traces, emits report. |
| `tigerexchange/packages/retrieval/tests/test_eval_gate.py` | Create | Release-gate regression-fail tests. |
| `tigerexchange/packages/retrieval/tests/test_import_linter.py` | Create | Asserts import-linter contracts pass (kernel/raw-store discipline). |
| `tigerexchange/packages/retrieval/eval/baseline.json` | Create | Pinned baseline thresholds for the CI release gate. |
| `tigerexchange/.github/workflows/eval-gate.yml` | Modify | Add the `retrieval-eval-gate` CI job. |

---

## Tasks

### Task 1: Package scaffold + import-linter discipline

**Files:** Create `tigerexchange/packages/retrieval/pyproject.toml`, `tigerexchange/packages/retrieval/src/retrieval/__init__.py`, `tigerexchange/packages/retrieval/tests/test_import_linter.py`

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_import_linter.py`:
```python
"""The retrieval package must satisfy the kernel chokepoint discipline (§4.2):
feature-facing modules import only the kernel `contracts` package + insulated
engine adapters; they never import the classifier or construct raw-store creds
outside the broker. We assert the import-linter contracts pass."""
import subprocess
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]


def test_import_linter_contracts_pass():
    result = subprocess.run(
        ["lint-imports", "--config", str(PKG_ROOT / "pyproject.toml")],
        cwd=PKG_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"import-linter failed:\n{result.stdout}\n{result.stderr}"
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_import_linter.py -q
```
Expected: FAIL — `lint-imports` not found / no `pyproject.toml` (`FileNotFoundError` or non-zero return).

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/pyproject.toml`:
```toml
[project]
name = "tigerexchange-retrieval"
version = "0.0.0"
description = "TigerExchange Phase-0 hybrid retrieval (Qdrant+OpenSearch+RRF+reranker) + PEP-gated RAGAS eval harness."
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6,<3",
    "tigerexchange-contracts",
    "qdrant-client>=1.9,<2",
    "opensearch-py>=2.5,<3",
    "FlagEmbedding>=1.2,<2",
    "ragas>=0.2,<0.3",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.5", "mypy>=1.10", "import-linter>=2.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/retrieval", "src/eval"]

[tool.importlinter]
root_packages = ["retrieval", "eval"]

# §4.2: feature-facing retrieval modules never import the classifier; enforcement
# is consumed only as the IPolicyEnforcement/IModelRouter Protocols from the kernel.
[[tool.importlinter.contracts]]
name = "retrieval-does-not-import-classifier-impls"
type = "forbidden"
source_modules = ["retrieval", "eval"]
forbidden_modules = [
    "classification.engine",
    "broker.credentials",
]

# §9.1: engine choice is insulated; only the adapter modules touch raw engine SDKs.
[[tool.importlinter.contracts]]
name = "only-adapters-touch-engine-sdks"
type = "forbidden"
source_modules = [
    "retrieval.hybrid_retriever",
    "retrieval.rrf",
    "retrieval.reranker",
    "eval.harness",
    "eval.gate",
]
forbidden_modules = ["qdrant_client", "opensearchpy"]
```

`tigerexchange/packages/retrieval/src/retrieval/__init__.py`:
```python
"""TigerExchange hybrid retrieval package (plan §9.1)."""
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && pip install -e ".[dev]" && python -m pytest tests/test_import_linter.py -q
```
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/pyproject.toml tigerexchange/packages/retrieval/src/retrieval/__init__.py tigerexchange/packages/retrieval/tests/test_import_linter.py
git commit -m "feat(retrieval): scaffold retrieval package with import-linter chokepoint discipline

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Engine-agnostic Candidate type + RetrievalConfig

**Files:** Create `tigerexchange/packages/retrieval/src/retrieval/types.py`, `tigerexchange/packages/retrieval/src/retrieval/config.py`, `tigerexchange/packages/retrieval/tests/test_rrf.py` (config portion)

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_rrf.py` (initial — config + Candidate only; RRF added in Task 3):
```python
from retrieval.config import RetrievalConfig
from retrieval.types import Candidate


def test_config_defaults_match_spec_91():
    cfg = RetrievalConfig()
    assert cfg.rrf_k == 60                # §9.1 RRF k≈60
    assert cfg.candidate_top_n == 50      # §9.1 top-50 into reranker
    assert cfg.rerank_top_k == 8          # §9.1 → top-8
    assert cfg.reranker_model_id == "BAAI/bge-reranker-v2-m3"


def test_config_is_frozen():
    cfg = RetrievalConfig()
    try:
        cfg.rrf_k = 10  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised


def test_candidate_is_frozen_and_carries_artifact_ref():
    c = Candidate(artifact_id="a1", owner_tenant_id="t1", score=0.9, text="hello")
    assert c.artifact_id == "a1"
    assert c.owner_tenant_id == "t1"
    try:
        c.score = 0.1  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_rrf.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'retrieval.config'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/retrieval/types.py`:
```python
"""Engine-agnostic scored candidate (plan §9.1).

A Candidate is the insulated unit passed between the vector/lexical adapters,
RRF fusion, and the reranker. It carries enough to (a) fuse/rerank and (b) build
the PepRequest the broker authorizes. It is NEVER returned to a feature module:
the retriever returns PublishableProjections only, after the PEP gates."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Candidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    owner_tenant_id: str
    score: float
    # Snippet/text used for reranking + RAGAS context; NEVER egressed without PEP.
    text: str = ""
    # Subject ids this candidate's source content concerns (for per-subject erasure).
    subject_ids: frozenset[str] = frozenset()
```

`tigerexchange/packages/retrieval/src/retrieval/config.py`:
```python
"""Frozen retrieval tuning config (plan §9.1)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    rrf_k: int = 60                 # §9.1 RRF k≈60
    candidate_top_n: int = 50       # §9.1 top-50 fused candidates into reranker
    rerank_top_k: int = 8           # §9.1 reranker → top-8
    vector_collection: str = "research_cards"
    lexical_index: str = "research_cards"
    embed_model_id: str = "allenai/specter2_base"
    reranker_model_id: str = "BAAI/bge-reranker-v2-m3"
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_rrf.py -q
```
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/retrieval/types.py tigerexchange/packages/retrieval/src/retrieval/config.py tigerexchange/packages/retrieval/tests/test_rrf.py
git commit -m "feat(retrieval): add frozen Candidate type and RetrievalConfig (RRF k=60, top-50->top-8)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: RRF fusion (k≈60)

**Files:** Create `tigerexchange/packages/retrieval/src/retrieval/rrf.py`; extend `tigerexchange/packages/retrieval/tests/test_rrf.py`

- [ ] **Step 1: Write the failing test**

Append to `tigerexchange/packages/retrieval/tests/test_rrf.py`:
```python
from retrieval.rrf import reciprocal_rank_fusion


def _c(aid: str, score: float) -> Candidate:
    return Candidate(artifact_id=aid, owner_tenant_id="t1", score=score, text=aid)


def test_rrf_rewards_items_ranked_high_in_both_lists():
    vec = [_c("a", 0.9), _c("b", 0.8), _c("c", 0.1)]
    lex = [_c("b", 5.0), _c("a", 4.0), _c("d", 1.0)]
    fused = reciprocal_rank_fusion([vec, lex], k=60, top_n=50)
    ids = [c.artifact_id for c in fused]
    # a and b appear high in both → ranked above c (vec-only tail) and d (lex-only tail)
    assert ids[0] in {"a", "b"} and ids[1] in {"a", "b"}
    assert set(ids) == {"a", "b", "c", "d"}


def test_rrf_uses_k_constant_in_denominator():
    # single list: rank-0 score = 1/(k+1); rank-1 = 1/(k+2)
    fused = reciprocal_rank_fusion([[_c("x", 1.0), _c("y", 1.0)]], k=60, top_n=50)
    assert fused[0].artifact_id == "x"
    assert abs(fused[0].score - 1.0 / 61) < 1e-9
    assert abs(fused[1].score - 1.0 / 62) < 1e-9


def test_rrf_truncates_to_top_n():
    big = [_c(f"a{i}", float(100 - i)) for i in range(100)]
    fused = reciprocal_rank_fusion([big], k=60, top_n=50)
    assert len(fused) == 50
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_rrf.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'retrieval.rrf'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/retrieval/rrf.py`:
```python
"""Reciprocal Rank Fusion (plan §9.1, k≈60).

Pure function: fuses N ranked candidate lists by sum of 1/(k + rank). The fused
candidate's `score` becomes the RRF score; its other fields come from the first
list in which the artifact appears. No engine SDK imports (import-linter §4.2)."""
from __future__ import annotations

from collections.abc import Sequence

from retrieval.types import Candidate


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[Candidate]],
    *,
    k: int = 60,
    top_n: int = 50,
) -> list[Candidate]:
    rrf_score: dict[str, float] = {}
    representative: dict[str, Candidate] = {}
    for ranked in ranked_lists:
        for rank, cand in enumerate(ranked):
            rrf_score[cand.artifact_id] = rrf_score.get(cand.artifact_id, 0.0) + 1.0 / (
                k + rank + 1
            )
            representative.setdefault(cand.artifact_id, cand)
    ordered = sorted(rrf_score.items(), key=lambda kv: kv[1], reverse=True)
    fused: list[Candidate] = []
    for artifact_id, score in ordered[:top_n]:
        fused.append(representative[artifact_id].model_copy(update={"score": score}))
    return fused
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_rrf.py -q
```
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/retrieval/rrf.py tigerexchange/packages/retrieval/tests/test_rrf.py
git commit -m "feat(retrieval): add RRF fusion (k=60, top-n truncation)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Local cross-encoder reranker (BGE/Qwen3) implementing IReranker

**Files:** Create `tigerexchange/packages/retrieval/src/retrieval/reranker.py`, `tigerexchange/packages/retrieval/tests/test_reranker.py`

The kernel `IReranker.rerank(query, candidates: Sequence[PublishableProjection], *, top_k=8) -> list[PublishableProjection]` operates on projections. Our internal reranker operates on `Candidate`s before projection (we must rerank candidate text, then the retriever projects). We therefore provide a `LocalCrossEncoderReranker` with a `rerank_candidates(query, candidates, top_k)` method plus a thin `IReranker` adapter `rerank(...)` that satisfies the kernel signature over already-projected hits (used by callers that re-rank projections). A pluggable `score_fn` lets tests avoid loading the model weights (no M4 Max inference in CI per §15.2).

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_reranker.py`:
```python
from contracts import PublishableProjection, Tier, DiscoverabilityScope
from retrieval.reranker import LocalCrossEncoderReranker
from retrieval.types import Candidate


def _c(aid: str, text: str) -> Candidate:
    return Candidate(artifact_id=aid, owner_tenant_id="t1", score=0.0, text=text)


def _fake_score(query: str, texts: list[str]) -> list[float]:
    # deterministic stand-in for the cross-encoder: score = term overlap count
    q = set(query.lower().split())
    return [float(len(q & set(t.lower().split()))) for t in texts]


def test_rerank_candidates_orders_by_cross_encoder_score_and_truncates():
    rr = LocalCrossEncoderReranker(score_fn=_fake_score)
    cands = [
        _c("a", "graph neural networks"),
        _c("b", "federated learning privacy"),
        _c("c", "graph learning privacy methods"),
    ]
    out = rr.rerank_candidates("privacy learning", cands, top_k=2)
    assert [c.artifact_id for c in out] == ["c", "b"]   # c overlaps 2, b overlaps 2->stable, a 1
    assert len(out) == 2
    assert out[0].score >= out[1].score


def test_rerank_projection_adapter_satisfies_kernel_signature():
    rr = LocalCrossEncoderReranker(score_fn=_fake_score)
    projs = [
        PublishableProjection(projection_id="p1", artifact_id="a", owner_tenant_id="t1",
                              tier=Tier.public, discoverability_scope=DiscoverabilityScope.PUBLIC_WEB,
                              fields={"text": "graph privacy"}),
        PublishableProjection(projection_id="p2", artifact_id="b", owner_tenant_id="t1",
                              tier=Tier.public, discoverability_scope=DiscoverabilityScope.PUBLIC_WEB,
                              fields={"text": "unrelated"}),
    ]
    out = rr.rerank("graph privacy", projs, top_k=1)
    assert len(out) == 1
    assert out[0].artifact_id == "a"
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_reranker.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'retrieval.reranker'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/retrieval/reranker.py`:
```python
"""Local cross-encoder reranker (plan §9.1): BGE-reranker-v2-m3 / Qwen3-Reranker,
top-50 -> top-8. Confidential-tier reranking is LOCAL by construction (in-boundary
model only). A pluggable `score_fn` keeps CI off the M4 Max / model weights (§15.2)."""
from __future__ import annotations

from collections.abc import Callable, Sequence

from contracts import IReranker, PublishableProjection

from retrieval.config import RetrievalConfig
from retrieval.types import Candidate

ScoreFn = Callable[[str, list[str]], list[float]]


def _load_bge_score_fn(model_id: str) -> ScoreFn:
    """Real cross-encoder scorer. Imported lazily so CI never loads weights."""
    from FlagEmbedding import FlagReranker  # noqa: PLC0415

    reranker = FlagReranker(model_id, use_fp16=True)

    def _score(query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        pairs = [[query, t] for t in texts]
        scores = reranker.compute_score(pairs, normalize=True)
        return [float(s) for s in (scores if isinstance(scores, list) else [scores])]

    return _score


class LocalCrossEncoderReranker(IReranker):
    def __init__(
        self,
        *,
        config: RetrievalConfig | None = None,
        score_fn: ScoreFn | None = None,
    ) -> None:
        self._cfg = config or RetrievalConfig()
        self._score_fn = score_fn

    def _scorer(self) -> ScoreFn:
        if self._score_fn is None:
            self._score_fn = _load_bge_score_fn(self._cfg.reranker_model_id)
        return self._score_fn

    def rerank_candidates(
        self, query: str, candidates: Sequence[Candidate], *, top_k: int = 8
    ) -> list[Candidate]:
        if not candidates:
            return []
        scores = self._scorer()(query, [c.text for c in candidates])
        scored = [c.model_copy(update={"score": s}) for c, s in zip(candidates, scores)]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    def rerank(
        self,
        query: str,
        candidates: Sequence[PublishableProjection],
        *,
        top_k: int = 8,
    ) -> list[PublishableProjection]:
        """Kernel IReranker adapter over already-projected hits."""
        if not candidates:
            return []
        texts = [str(p.fields.get("text", "")) for p in candidates]
        scores = self._scorer()(query, texts)
        order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
        return [candidates[i] for i in order[:top_k]]
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_reranker.py -q
```
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/retrieval/reranker.py tigerexchange/packages/retrieval/tests/test_reranker.py
git commit -m "feat(retrieval): add local cross-encoder reranker (BGE-reranker-v2-m3) implementing IReranker

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Vector + lexical engine adapters (Qdrant, OpenSearch)

**Files:** Create `tigerexchange/packages/retrieval/src/retrieval/vector_store.py`, `tigerexchange/packages/retrieval/src/retrieval/lexical_index.py`; add adapter tests in `tigerexchange/packages/retrieval/tests/test_hybrid_retriever.py` (adapter portion).

Adapters take an injected client object so CI uses a fake (no live Qdrant/OpenSearch needed for unit tests; integration tests use testcontainers, marked `integration`). Both expose `search(query_vector_or_text, tenant_id, limit) -> list[Candidate]`.

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_hybrid_retriever.py` (initial — adapters only):
```python
from retrieval.vector_store import QdrantVectorStore
from retrieval.lexical_index import OpenSearchLexicalIndex


class _FakeQdrantHit:
    def __init__(self, aid, score, text):
        self.payload = {"artifact_id": aid, "owner_tenant_id": "t1", "text": text,
                        "subject_ids": ["s1"]}
        self.score = score


class _FakeQdrantClient:
    def __init__(self, hits): self._hits = hits; self.last_filter = None
    def search(self, *, collection_name, query_vector, limit, query_filter=None):
        self.last_filter = query_filter
        return self._hits[:limit]


def test_qdrant_adapter_maps_hits_and_filters_by_tenant():
    client = _FakeQdrantClient([_FakeQdrantHit("a", 0.9, "alpha"),
                               _FakeQdrantHit("b", 0.7, "beta")])
    vs = QdrantVectorStore(client=client, collection="research_cards")
    out = vs.search([0.1, 0.2], tenant_id="t1", limit=2)
    assert [c.artifact_id for c in out] == ["a", "b"]
    assert out[0].owner_tenant_id == "t1"
    assert "s1" in out[0].subject_ids
    # tenant scoping must be pushed into the engine query (defense-in-depth)
    assert client.last_filter is not None


class _FakeOpenSearchClient:
    def __init__(self, hits): self._hits = hits; self.last_body = None
    def search(self, *, index, body):
        self.last_body = body
        return {"hits": {"hits": self._hits}}


def test_opensearch_adapter_maps_bm25_hits_and_scopes_tenant():
    hits = [{"_score": 5.0, "_source": {"artifact_id": "b", "owner_tenant_id": "t1",
                                        "text": "beta", "subject_ids": ["s2"]}}]
    client = _FakeOpenSearchClient(hits)
    li = OpenSearchLexicalIndex(client=client, index="research_cards")
    out = li.search("beta", tenant_id="t1", limit=10)
    assert out[0].artifact_id == "b"
    assert out[0].score == 5.0
    # tenant filter present in the query body
    assert "t1" in str(client.last_body)
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_hybrid_retriever.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'retrieval.vector_store'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/retrieval/vector_store.py`:
```python
"""Qdrant vector adapter (plan §9.1, §12). Engine choice insulated behind this
adapter; only this module imports qdrant_client (import-linter §9.1). Tenant
scoping is pushed into the query as defense-in-depth (the PEP is the primary
boundary; this is belt-and-suspenders, §7.7). Confidential collections live on
tenant-KEK/volume-key-encrypted storage per §11.3b (provisioned by 0g)."""
from __future__ import annotations

from typing import Any

from retrieval.types import Candidate


class QdrantVectorStore:
    def __init__(self, *, client: Any, collection: str) -> None:
        self._client = client
        self._collection = collection

    def _tenant_filter(self, tenant_id: str) -> Any:
        from qdrant_client.models import FieldCondition, Filter, MatchValue  # noqa: PLC0415

        return Filter(
            must=[FieldCondition(key="owner_tenant_id", match=MatchValue(value=tenant_id))]
        )

    def search(
        self, query_vector: list[float], *, tenant_id: str, limit: int
    ) -> list[Candidate]:
        hits = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=self._tenant_filter(tenant_id),
        )
        out: list[Candidate] = []
        for h in hits:
            p = h.payload
            out.append(
                Candidate(
                    artifact_id=p["artifact_id"],
                    owner_tenant_id=p["owner_tenant_id"],
                    score=float(h.score),
                    text=p.get("text", ""),
                    subject_ids=frozenset(p.get("subject_ids", [])),
                )
            )
        return out
```

`tigerexchange/packages/retrieval/src/retrieval/lexical_index.py`:
```python
"""OpenSearch BM25 adapter (plan §9.1, §12). Academic corpora are entity-heavy
(author names, acronyms, grant numbers, gene names) → exact lexical match matters.
Only this module imports opensearchpy (import-linter §9.1). Tenant scoping is a
filter clause (defense-in-depth, §7.7); confidential postings are tenant-KEK/
volume-key-encrypted per §11.3b (provisioned by 0g)."""
from __future__ import annotations

from typing import Any

from retrieval.types import Candidate


class OpenSearchLexicalIndex:
    def __init__(self, *, client: Any, index: str) -> None:
        self._client = client
        self._index = index

    def search(self, query: str, *, tenant_id: str, limit: int) -> list[Candidate]:
        body = {
            "size": limit,
            "query": {
                "bool": {
                    "must": [{"match": {"text": query}}],
                    "filter": [{"term": {"owner_tenant_id": tenant_id}}],
                }
            },
        }
        resp = self._client.search(index=self._index, body=body)
        out: list[Candidate] = []
        for h in resp["hits"]["hits"]:
            src = h["_source"]
            out.append(
                Candidate(
                    artifact_id=src["artifact_id"],
                    owner_tenant_id=src["owner_tenant_id"],
                    score=float(h["_score"]),
                    text=src.get("text", ""),
                    subject_ids=frozenset(src.get("subject_ids", [])),
                )
            )
        return out
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_hybrid_retriever.py -q
```
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/retrieval/vector_store.py tigerexchange/packages/retrieval/src/retrieval/lexical_index.py tigerexchange/packages/retrieval/tests/test_hybrid_retriever.py
git commit -m "feat(retrieval): add Qdrant vector + OpenSearch BM25 adapters with tenant-scoped queries

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Shared test fakes (PEP, router, KEK store)

**Files:** Create `tigerexchange/packages/retrieval/tests/conftest.py`

These fakes implement the canonical kernel Protocols verbatim so the retriever/eval code is tested against the real contract surface without standing up OPA/SpiceDB/vLLM/KMS.

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/conftest.py`:
```python
"""Shared fakes implementing the canonical kernel Protocols (plan §5.1).
No real OPA/SpiceDB/vLLM/KMS in unit tests; these satisfy the verbatim
signatures from `contracts`."""
from __future__ import annotations

import pytest

from contracts import (
    Capability,
    ClassificationResult,
    Decision,
    DiscoverabilityScope,
    Edition,
    Entitlement,
    IModelProvider,
    IsolationPosture,
    PepRequest,
    PepResponse,
    PublishableProjection,
    TenantContext,
    Tier,
)


class FakePEP:
    """Implements IPolicyEnforcement.authorize (§4.2). Denies any artifact_id
    listed in `denied`; otherwise ALLOWs and returns a single projected row."""

    def __init__(self, denied: set[str] | None = None) -> None:
        self.denied = denied or set()
        self.calls: list[PepRequest] = []

    def authorize(self, request: PepRequest) -> PepResponse:
        self.calls.append(request)
        rid = str((request.attributes or {}).get("artifact_id", request.resource_id))
        if rid in self.denied:
            return PepResponse(request_id=request.request_id, decision=Decision.DENY,
                               effective_tier=request.tenant.entitlement.max_tier,
                               reason="denied-by-test")
        return PepResponse(
            request_id=request.request_id,
            decision=Decision.ALLOW,
            effective_tier=request.tenant.entitlement.max_tier,
            payload=[{
                "projection_id": f"proj-{rid}",
                "artifact_id": rid,
                "owner_tenant_id": request.tenant.tenant_id,
                "tier": (request.attributes or {}).get("tier", Tier.public.wire),
                "discoverability_scope": DiscoverabilityScope.FEDERATION_WIDE.value,
                "fields": {"text": (request.attributes or {}).get("text", "")},
            }],
        )


class _Provider(IModelProvider):
    def __init__(self, pid: str, local: bool) -> None:
        self._pid = pid
        self._local = local

    @property
    def provider_id(self) -> str:
        return self._pid

    def satisfies_locality(self, tier: Tier) -> bool:
        return self._local or tier is Tier.public

    def no_retention_attested(self) -> bool:
        return self._local


class FakeModelRouter:
    """Implements IModelRouter.route (§8). Returns the in-boundary provider for
    any non-public classification; only public may select the cloud provider."""

    def __init__(self) -> None:
        self.local = _Provider("vllm-in-boundary", local=True)
        self.cloud = _Provider("cloud-frontier", local=False)

    def route(self, classification: ClassificationResult, tenant: TenantContext) -> IModelProvider:
        if classification.tier is Tier.public:
            return self.cloud
        return self.local


class FakeKEKStore:
    """Stand-in for the 0g confidential KEK derivative store: XOR-with-key 'encrypt'
    keyed per tenant; crypto-shred forgets the key so ciphertext is undecryptable."""

    def __init__(self) -> None:
        self._keys: dict[str, int] = {}
        self.blobs: dict[str, bytes] = {}

    def _key(self, tenant_id: str) -> int:
        return self._keys.setdefault(tenant_id, (hash(tenant_id) & 0xFF) or 0x5A)

    def _xor(self, data: bytes, k: int) -> bytes:
        return bytes(b ^ k for b in data)

    def put(self, tenant_id: str, blob_id: str, plaintext: bytes) -> None:
        self.blobs[blob_id] = self._xor(plaintext, self._key(tenant_id))

    def get(self, tenant_id: str, blob_id: str) -> bytes | None:
        if tenant_id not in self._keys:   # key shredded → undecryptable
            return None
        ct = self.blobs.get(blob_id)
        return None if ct is None else self._xor(ct, self._key(tenant_id))

    def crypto_shred(self, tenant_id: str) -> None:
        self._keys.pop(tenant_id, None)


def _entitlement(edition: Edition, max_tier: Tier, caps: set[Capability]) -> Entitlement:
    return Entitlement(edition=edition, capabilities=frozenset(caps),
                       isolation=IsolationPosture.DEDICATED_CELL, max_tier=max_tier)


@pytest.fixture
def confidential_tenant() -> TenantContext:
    return TenantContext(
        tenant_id="anchor-center", subject_id="pi-1",
        entitlement=_entitlement(Edition.CONSORTIUM_ANCHOR, Tier.confidential,
                                 {Capability.CONFIDENTIAL_WORKSPACE, Capability.OWN_MATERIALS}),
    )


@pytest.fixture
def public_tenant() -> TenantContext:
    return TenantContext(
        tenant_id="plg-1", subject_id="pi-2",
        entitlement=_entitlement(Edition.PLG, Tier.private,
                                 {Capability.PUBLIC_RETRIEVAL, Capability.OWN_MATERIALS}),
    )


@pytest.fixture
def fake_pep() -> FakePEP:
    return FakePEP()


@pytest.fixture
def fake_router() -> FakeModelRouter:
    return FakeModelRouter()


@pytest.fixture
def fake_kek() -> FakeKEKStore:
    return FakeKEKStore()
```

- [ ] **Step 2: Run test to verify it fails**

Add a sentinel that imports the fixtures so a collection error surfaces:
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/conftest.py -q
```
Expected: FAIL/ERROR at collection — `contracts` symbols must import cleanly; if `IModelProvider`/etc. resolve, conftest imports succeed but there are no tests (pytest exits with "no tests ran", code 5). That confirms the fakes import against the real kernel. (A green "no tests collected" here is the pass signal for this scaffolding file; the next tasks consume the fixtures.)

- [ ] **Step 3: Write minimal implementation**

(Implementation is the conftest above — no separate impl module; the fixtures ARE the deliverable. Verify the kernel import surface resolves.)
```bash
cd tigerexchange/packages/retrieval && python -c "import tests.conftest" 2>&1 | head
```
Expected: no ImportError.

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/ -q
```
Expected: PASS — Tasks 1-5 tests still pass; conftest fixtures available (8 passed from prior tasks).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/tests/conftest.py
git commit -m "test(retrieval): add shared kernel-Protocol fakes (FakePEP, FakeModelRouter, FakeKEKStore)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: HybridRetriever implementing IRetrievalStrategy (fuse → rerank → PEP-gate → project)

**Files:** Create `tigerexchange/packages/retrieval/src/retrieval/hybrid_retriever.py`; extend `tigerexchange/packages/retrieval/tests/test_hybrid_retriever.py`

The retriever embeds the query, hits both engines for `candidate_top_n`, fuses via RRF, reranks to `rerank_top_k`, then routes EVERY surviving candidate through `IPolicyEnforcement.authorize` (PepAction.RETRIEVE). Only ALLOW responses are projected into `PublishableProjection`s and returned. Denied/quarantined candidates are dropped (§4.2, D6 — never enters any retrieval path). This is the deliverable's "fused, reranked, PEP-projected results."

- [ ] **Step 1: Write the failing test**

Append to `tigerexchange/packages/retrieval/tests/test_hybrid_retriever.py`:
```python
from contracts import PublishableProjection, PepAction, Capability
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.config import RetrievalConfig
from retrieval.reranker import LocalCrossEncoderReranker
from retrieval.types import Candidate
from tests.conftest import FakePEP


class _StubVector:
    def __init__(self, cands): self._c = cands
    def search(self, query_vector, *, tenant_id, limit): return self._c[:limit]


class _StubLexical:
    def __init__(self, cands): self._c = cands
    def search(self, query, *, tenant_id, limit): return self._c[:limit]


def _embed(_q): return [0.0, 0.0]
def _score(query, texts):
    q = set(query.lower().split())
    return [float(len(q & set(t.lower().split()))) for t in texts]


def _retriever(pep, vec, lex):
    return HybridRetriever(
        vector_store=_StubVector(vec), lexical_index=_StubLexical(lex),
        reranker=LocalCrossEncoderReranker(score_fn=_score),
        pep=pep, embed_fn=_embed,
        config=RetrievalConfig(candidate_top_n=50, rerank_top_k=8),
    )


def test_retriever_returns_pep_projected_results(confidential_tenant):
    vec = [Candidate(artifact_id="a", owner_tenant_id="anchor-center", score=0.9, text="graph privacy")]
    lex = [Candidate(artifact_id="b", owner_tenant_id="anchor-center", score=4.0, text="privacy learning")]
    pep = FakePEP()
    out = _retriever(pep, vec, lex).retrieve("privacy", confidential_tenant, top_k=8)
    assert all(isinstance(p, PublishableProjection) for p in out)
    assert {p.artifact_id for p in out} == {"a", "b"}
    # every returned hit went through the PEP with RETRIEVE action
    assert pep.calls and all(c.action is PepAction.RETRIEVE for c in pep.calls)
    assert all(c.required_capability is Capability.OWN_MATERIALS for c in pep.calls)


def test_retriever_excludes_denied_and_quarantined(confidential_tenant):
    vec = [Candidate(artifact_id="a", owner_tenant_id="anchor-center", score=0.9, text="x")]
    lex = [Candidate(artifact_id="b", owner_tenant_id="anchor-center", score=4.0, text="x")]
    pep = FakePEP(denied={"b"})           # 'b' is quarantined/denied at the PEP (D6)
    out = _retriever(pep, vec, lex).retrieve("x", confidential_tenant, top_k=8)
    assert {p.artifact_id for p in out} == {"a"}     # denied 'b' never enters results


def test_retriever_truncates_to_top_k(confidential_tenant):
    vec = [Candidate(artifact_id=f"a{i}", owner_tenant_id="anchor-center", score=float(i), text="q")
           for i in range(20)]
    pep = FakePEP()
    out = _retriever(pep, vec, []).retrieve("q", confidential_tenant, top_k=8)
    assert len(out) == 8
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_hybrid_retriever.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'retrieval.hybrid_retriever'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/retrieval/hybrid_retriever.py`:
```python
"""HybridRetriever implementing IRetrievalStrategy (plan §9.1, §4.2, D6).

Flow: embed query -> Qdrant vector + OpenSearch BM25 (top-N each) -> RRF fuse
(k≈60) -> local rerank (top-50 -> top-8) -> route EVERY survivor through the PEP
(PepAction.RETRIEVE) -> project ALLOWs into PublishableProjections. DENY/QUARANTINE
candidates are dropped: confidential/quarantined content NEVER enters the retrieval
result set (D6). Engine choice is insulated behind the injected adapters (§9.1)."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from contracts import (
    Capability,
    Decision,
    IPolicyEnforcement,
    IReranker,
    IRetrievalStrategy,
    PepAction,
    PepRequest,
    PublishableProjection,
    TenantContext,
    Tier,
)

from retrieval.config import RetrievalConfig
from retrieval.rrf import reciprocal_rank_fusion
from retrieval.types import Candidate

EmbedFn = Callable[[str], list[float]]


class HybridRetriever(IRetrievalStrategy):
    def __init__(
        self,
        *,
        vector_store: Any,
        lexical_index: Any,
        reranker: IReranker,
        pep: IPolicyEnforcement,
        embed_fn: EmbedFn,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._vec = vector_store
        self._lex = lexical_index
        self._reranker = reranker
        self._pep = pep
        self._embed = embed_fn
        self._cfg = config or RetrievalConfig()

    def retrieve(
        self, query: str, tenant: TenantContext, *, top_k: int = 8
    ) -> list[PublishableProjection]:
        n = self._cfg.candidate_top_n
        vector_hits = self._vec.search(self._embed(query), tenant_id=tenant.tenant_id, limit=n)
        lexical_hits = self._lex.search(query, tenant_id=tenant.tenant_id, limit=n)
        fused = reciprocal_rank_fusion(
            [vector_hits, lexical_hits], k=self._cfg.rrf_k, top_n=n
        )
        reranked = self._reranker.rerank_candidates(query, fused, top_k=top_k)
        return self._pep_gate(query, reranked, tenant)

    def _pep_gate(
        self, query: str, candidates: Sequence[Candidate], tenant: TenantContext
    ) -> list[PublishableProjection]:
        results: list[PublishableProjection] = []
        for cand in candidates:
            req = PepRequest(
                request_id=f"retrieve-{cand.artifact_id}",
                tenant=tenant,
                action=PepAction.RETRIEVE,
                required_capability=Capability.OWN_MATERIALS,
                resource_id=cand.artifact_id,
                attributes={"artifact_id": cand.artifact_id, "text": cand.text,
                            "tier": tenant.entitlement.max_tier.wire, "query": query},
            )
            resp = self._pep.authorize(req)
            if resp.decision is not Decision.ALLOW or not resp.payload:
                continue  # D6: denied/quarantined never enters results
            for row in resp.payload:
                results.append(
                    PublishableProjection(
                        projection_id=str(row["projection_id"]),
                        artifact_id=str(row["artifact_id"]),
                        owner_tenant_id=str(row["owner_tenant_id"]),
                        tier=Tier.parse(row.get("tier")),
                        discoverability_scope=row["discoverability_scope"],
                        fields=dict(row.get("fields", {})),
                    )
                )
        return results
```

Note: `PublishableProjection` validation rejects `confidential` tier (D6, kernel `projection.py`). The PEP's projected rows for own-tier confidential retrieval are returned as the broker's *projected* (public/shared) view — `FakePEP` returns `tier=public` by default; production broker projects confidential reads to a non-confidential in-cell result envelope. The retriever passes the PEP-supplied tier through verbatim; it never upgrades to confidential.

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_hybrid_retriever.py -q
```
Expected: PASS (5 passed — 2 adapter + 3 retriever).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/retrieval/hybrid_retriever.py tigerexchange/packages/retrieval/tests/test_hybrid_retriever.py
git commit -m "feat(retrieval): add HybridRetriever (RRF+rerank+PEP-gated projection) implementing IRetrievalStrategy

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Eval value types (gold-set, trace, judge I/O, report)

**Files:** Create `tigerexchange/packages/retrieval/src/eval/__init__.py`, `tigerexchange/packages/retrieval/src/eval/types.py`, `tigerexchange/packages/retrieval/tests/test_eval_confidential_store.py` (types portion)

Every eval artifact is tagged `tier` + `compliance_flags` (confidential by default) so it can be routed/encrypted/erased like any other confidential derivative (resolves the HIGH: gold-sets/traces/judge-I-O are confidential-tier artifacts).

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_eval_confidential_store.py` (initial — types only):
```python
from contracts import Tier
from eval.types import GoldItem, EvalTrace, JudgeIO, EvalReport


def test_gold_item_defaults_to_confidential_tier():
    g = GoldItem(item_id="g1", tenant_id="t1", question="q?", ground_truth="a",
                 relevant_artifact_ids=frozenset({"a1"}))
    assert g.tier is Tier.confidential          # HIGH: gold-sets are confidential-tier
    assert g.subject_ids == frozenset()


def test_eval_trace_carries_retrieved_context_and_is_confidential():
    t = EvalTrace(trace_id="tr1", tenant_id="t1", item_id="g1",
                  question="q?", retrieved_contexts=("ctx",), generated_answer="ans",
                  subject_ids=frozenset({"s1"}))
    assert t.tier is Tier.confidential          # RAGAS context/answer verbatim = confidential
    assert "ctx" in t.retrieved_contexts
    assert "s1" in t.subject_ids


def test_judge_io_is_confidential_and_records_provider():
    j = JudgeIO(judge_io_id="j1", tenant_id="t1", item_id="g1",
                judge_prompt="grade this", judge_output="0.9",
                judge_provider_id="vllm-in-boundary")
    assert j.tier is Tier.confidential
    assert j.judge_provider_id == "vllm-in-boundary"


def test_eval_report_holds_metrics():
    r = EvalReport(tenant_id="t1", model_route="vllm-in-boundary",
                   metrics={"faithfulness": 0.9, "ndcg@8": 0.7})
    assert r.metrics["faithfulness"] == 0.9
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_confidential_store.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.types'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/eval/__init__.py`:
```python
"""TigerExchange PEP-gated RAGAS eval harness (plan §9.3, §15.2, convergence HIGH)."""
```

`tigerexchange/packages/retrieval/src/eval/types.py`:
```python
"""Eval artifact value types (plan §9.3, convergence HIGH).

Gold-sets, eval traces, and judge I/O are FIRST-CLASS CONFIDENTIAL-TIER artifacts:
RAGAS context-precision/recall store retrieved context + the generated answer
verbatim, and the judge prompt/output carry the same confidential payload. They
default to Tier.confidential so they (a) KEK-encrypt per §11.3b, (b) route to an
in-boundary judge per §8.2, and (c) are covered by per-subject erasure (§11.7)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from contracts import ComplianceFlag, Tier


class GoldItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    tenant_id: str
    question: str
    ground_truth: str
    relevant_artifact_ids: frozenset[str]
    subject_ids: frozenset[str] = Field(default_factory=frozenset)
    tier: Tier = Tier.confidential
    compliance_flags: frozenset[ComplianceFlag] = Field(default_factory=frozenset)


class EvalTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    trace_id: str
    tenant_id: str
    item_id: str
    question: str
    retrieved_contexts: tuple[str, ...]
    generated_answer: str
    retrieved_artifact_ids: tuple[str, ...] = ()
    subject_ids: frozenset[str] = Field(default_factory=frozenset)
    tier: Tier = Tier.confidential
    compliance_flags: frozenset[ComplianceFlag] = Field(default_factory=frozenset)


class JudgeIO(BaseModel):
    model_config = ConfigDict(frozen=True)

    judge_io_id: str
    tenant_id: str
    item_id: str
    judge_prompt: str
    judge_output: str
    judge_provider_id: str
    subject_ids: frozenset[str] = Field(default_factory=frozenset)
    tier: Tier = Tier.confidential


class EvalReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: str
    model_route: str
    metrics: dict[str, float]
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_confidential_store.py -q
```
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/eval/__init__.py tigerexchange/packages/retrieval/src/eval/types.py tigerexchange/packages/retrieval/tests/test_eval_confidential_store.py
git commit -m "feat(eval): add confidential-tier eval value types (gold-set, trace, judge I/O, report)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: ConfidentialEvalStore — KEK-encrypted persistence + crypto-shred + per-subject erasure

**Files:** Create `tigerexchange/packages/retrieval/src/eval/confidential_store.py`; extend `tigerexchange/packages/retrieval/tests/test_eval_confidential_store.py`

This is the core HIGH fix: eval artifacts live in the cell, KEK-encrypted via the 0g store, crypto-shred with the tenant KEK, and are covered by per-subject erasure (§11.3b, §11.7). It writes ONLY through the injected KEK store (no plaintext CI/observability side-door).

- [ ] **Step 1: Write the failing test**

Append to `tigerexchange/packages/retrieval/tests/test_eval_confidential_store.py`:
```python
from eval.confidential_store import ConfidentialEvalStore
from tests.conftest import FakeKEKStore


def _store(kek): return ConfidentialEvalStore(kek_store=kek, tenant_id="t1")


def test_traces_are_kek_encrypted_at_rest(fake_kek):
    store = _store(fake_kek)
    tr = EvalTrace(trace_id="tr1", tenant_id="t1", item_id="g1", question="secret proposal?",
                   retrieved_contexts=("confidential budget",), generated_answer="ans",
                   subject_ids=frozenset({"s1"}))
    store.put_trace(tr)
    # raw bytes at rest must NOT contain the plaintext payload
    blob = next(iter(fake_kek.blobs.values()))
    assert b"confidential budget" not in blob
    # round-trips while the KEK exists
    assert store.get_trace("tr1").retrieved_contexts == ("confidential budget",)


def test_crypto_shred_makes_eval_traces_undecryptable(fake_kek):
    store = _store(fake_kek)
    store.put_trace(EvalTrace(trace_id="tr1", tenant_id="t1", item_id="g1", question="q",
                              retrieved_contexts=("ctx",), generated_answer="a"))
    fake_kek.crypto_shred("t1")                     # §11.3b crypto-shred
    assert store.get_trace("tr1") is None           # no decryptable hit post-shred


def test_per_subject_erasure_removes_only_that_subjects_artifacts(fake_kek):
    store = _store(fake_kek)
    store.put_trace(EvalTrace(trace_id="trA", tenant_id="t1", item_id="g1", question="q",
                              retrieved_contexts=("c",), generated_answer="a",
                              subject_ids=frozenset({"s1"})))
    store.put_trace(EvalTrace(trace_id="trB", tenant_id="t1", item_id="g2", question="q",
                              retrieved_contexts=("c",), generated_answer="a",
                              subject_ids=frozenset({"s2"})))
    erased = store.erase_subject("s1")              # §11.7 per-subject erasure
    assert erased == 1
    assert store.get_trace("trA") is None
    assert store.get_trace("trB") is not None
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_confidential_store.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.confidential_store'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/eval/confidential_store.py`:
```python
"""Confidential eval-artifact store (plan §9.3, §11.3b, §11.7; convergence HIGH).

Gold-sets, eval traces, and judge I/O are written ONLY through the per-tenant
KEK-encrypted derivative store (0g), so they (a) crypto-shred with the tenant KEK
on revocation/offboarding (§11.3b) and (b) are covered by per-subject erasure
(§11.7). There is NO plaintext CI/observability side-door: the harness persists
exclusively through this store. The injected `kek_store` is the 0g component;
this module never holds raw keys."""
from __future__ import annotations

import json
from typing import Any

from eval.types import EvalTrace, GoldItem, JudgeIO


class ConfidentialEvalStore:
    def __init__(self, *, kek_store: Any, tenant_id: str) -> None:
        self._kek = kek_store
        self._tenant_id = tenant_id
        # subject -> blob_ids index (kept so per-subject erasure is targeted, §11.7)
        self._subject_index: dict[str, set[str]] = {}
        self._traces: set[str] = set()

    def _blob_id(self, kind: str, key: str) -> str:
        return f"{self._tenant_id}:{kind}:{key}"

    def _put(self, blob_id: str, model: Any, subject_ids: frozenset[str]) -> None:
        self._kek.put(self._tenant_id, blob_id, model.model_dump_json().encode("utf-8"))
        for sid in subject_ids:
            self._subject_index.setdefault(sid, set()).add(blob_id)

    def _get(self, blob_id: str) -> dict[str, Any] | None:
        raw = self._kek.get(self._tenant_id, blob_id)
        return None if raw is None else json.loads(raw.decode("utf-8"))

    def put_gold_item(self, item: GoldItem) -> None:
        self._put(self._blob_id("gold", item.item_id), item, item.subject_ids)

    def get_gold_item(self, item_id: str) -> GoldItem | None:
        d = self._get(self._blob_id("gold", item_id))
        return None if d is None else GoldItem(**d)

    def put_trace(self, trace: EvalTrace) -> None:
        bid = self._blob_id("trace", trace.trace_id)
        self._put(bid, trace, trace.subject_ids)
        self._traces.add(bid)

    def get_trace(self, trace_id: str) -> EvalTrace | None:
        d = self._get(self._blob_id("trace", trace_id))
        return None if d is None else EvalTrace(**d)

    def put_judge_io(self, jio: JudgeIO) -> None:
        self._put(self._blob_id("judge", jio.judge_io_id), jio, jio.subject_ids)

    def get_judge_io(self, judge_io_id: str) -> JudgeIO | None:
        d = self._get(self._blob_id("judge", judge_io_id))
        return None if d is None else JudgeIO(**d)

    def crypto_shred(self) -> None:
        """KEK crypto-shred (§11.3b): forget the tenant key → all eval artifacts
        become undecryptable in one operation."""
        self._kek.crypto_shred(self._tenant_id)

    def erase_subject(self, subject_id: str) -> int:
        """Per-subject erasure (§11.7): hard-delete this subject's eval artifacts."""
        blob_ids = self._subject_index.pop(subject_id, set())
        for bid in blob_ids:
            self._kek.blobs.pop(bid, None)
            self._traces.discard(bid)
        return len(blob_ids)
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_confidential_store.py -q
```
Expected: PASS (7 passed — 4 types + 3 store).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/eval/confidential_store.py tigerexchange/packages/retrieval/tests/test_eval_confidential_store.py
git commit -m "feat(eval): KEK-encrypted confidential eval store with crypto-shred + per-subject erasure (§11.3b/§11.7)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: PEP-gated judge routing — confidential eval cannot route to a cloud judge

**Files:** Create `tigerexchange/packages/retrieval/src/eval/judge_router.py`, `tigerexchange/packages/retrieval/tests/test_eval_judge_routing.py`

This makes the "router-aware eval" an **enforced routing rule with a contract test** (the exact HIGH-addressed item): judge selection goes through `IModelRouter.route` with a `ClassificationResult` derived from the eval artifact's tier; for confidential, the router returns in-boundary; the function additionally asserts the chosen provider `satisfies_locality(tier)` and raises `JudgeRoutingError` (fail-closed) if a non-local provider is ever selected for a non-public tier.

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_eval_judge_routing.py`:
```python
import pytest

from contracts import IModelProvider, ClassificationResult, Decision, Tier, TenantContext
from eval.judge_router import route_judge, JudgeRoutingError


def test_confidential_eval_routes_to_in_boundary_judge(confidential_tenant, fake_router):
    provider = route_judge(tier=Tier.confidential, tenant=confidential_tenant, router=fake_router)
    assert provider.provider_id == "vllm-in-boundary"
    assert provider.satisfies_locality(Tier.confidential)


def test_public_eval_may_route_to_cloud_judge(public_tenant, fake_router):
    provider = route_judge(tier=Tier.public, tenant=public_tenant, router=fake_router)
    assert provider.provider_id == "cloud-frontier"


class _MisroutingRouter:
    """Adversary: returns a cloud (non-local) provider even for confidential."""
    class _Cloud(IModelProvider):
        @property
        def provider_id(self): return "cloud-frontier"
        def satisfies_locality(self, tier): return tier is Tier.public
        def no_retention_attested(self): return False
    def route(self, classification, tenant): return self._Cloud()


def test_confidential_eval_cannot_route_to_cloud_judge_fails_closed(confidential_tenant):
    # CONTRACT TEST (convergence HIGH + §15.2): a confidential eval that would
    # select a cloud judge must fail closed, never silently send confidential
    # answers to a cloud provider.
    with pytest.raises(JudgeRoutingError):
        route_judge(tier=Tier.confidential, tenant=confidential_tenant,
                    router=_MisroutingRouter())
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_judge_routing.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.judge_router'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/eval/judge_router.py`:
```python
"""PEP-gated judge-model routing (plan §9.3, §8.2; convergence HIGH).

The eval judge is bound to the SAME §8.2 routing policy as production generation:
selection goes through IModelRouter.route, and the chosen provider MUST attest
locality for the eval artifact's tier. A confidential eval therefore CANNOT
select a cloud judge — if the router ever returns a non-local provider for a
non-public tier, this fails closed (JudgeRoutingError). This converts the prose
'judge LLM is the local model on the confidential tier' into an ENFORCED rule
with a contract test (§15.2)."""
from __future__ import annotations

from contracts import (
    ClassificationResult,
    Decision,
    IModelProvider,
    IModelRouter,
    TenantContext,
    Tier,
)


class JudgeRoutingError(RuntimeError):
    """Raised when judge selection would violate in-boundary routing (fail-closed)."""


def route_judge(
    *, tier: Tier, tenant: TenantContext, router: IModelRouter
) -> IModelProvider:
    classification = ClassificationResult(
        tier=tier, decision=Decision.ALLOW, confidence=1.0,
        reason="eval-judge-routing",
    )
    provider = router.route(classification, tenant)
    # Enforced in-boundary rule: non-public eval MUST resolve to a local provider.
    if tier is not Tier.public and not provider.satisfies_locality(tier):
        raise JudgeRoutingError(
            f"confidential/non-public eval (tier={tier.wire}) cannot route to "
            f"non-local judge provider '{provider.provider_id}'"
        )
    return provider
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_judge_routing.py -q
```
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/eval/judge_router.py tigerexchange/packages/retrieval/tests/test_eval_judge_routing.py
git commit -m "feat(eval): enforce in-boundary judge routing — confidential eval cannot route to cloud judge (§8.2 contract test)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: nDCG@k / Recall@k retrieval-quality metrics

**Files:** Extend `tigerexchange/packages/retrieval/src/eval/harness.py` (metrics functions), create `tigerexchange/packages/retrieval/tests/test_eval_harness.py` (metrics portion)

Pure ranking metrics computed from retrieved artifact ids vs gold `relevant_artifact_ids`. These are part of the §9.3 gate (nDCG@k/Recall@k) and need no LLM, so they're tested in isolation first.

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_eval_harness.py` (initial — metrics only):
```python
import math
from eval.harness import ndcg_at_k, recall_at_k


def test_recall_at_k_counts_relevant_in_topk():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"a", "c", "x"}        # x not retrieved
    assert recall_at_k(retrieved, relevant, k=4) == 2 / 3
    assert recall_at_k(retrieved, relevant, k=1) == 1 / 3   # only 'a' in top-1


def test_recall_at_k_empty_relevant_is_one():
    assert recall_at_k(["a"], set(), k=1) == 1.0


def test_ndcg_at_k_perfect_ranking_is_one():
    retrieved = ["a", "b"]
    relevant = {"a", "b"}
    assert abs(ndcg_at_k(retrieved, relevant, k=2) - 1.0) < 1e-9


def test_ndcg_at_k_rewards_higher_placement():
    relevant = {"a"}
    top = ndcg_at_k(["a", "b"], relevant, k=2)      # relevant at rank 1
    bottom = ndcg_at_k(["b", "a"], relevant, k=2)   # relevant at rank 2
    assert top > bottom
    assert abs(bottom - (1.0 / math.log2(3))) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_harness.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.harness'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/eval/harness.py` (metrics functions; harness class added in Task 12):
```python
"""RAGAS-in-CI eval harness (plan §9.3, §15.2). This module first defines the
pure ranking metrics (nDCG@k / Recall@k); the PEP-gated harness runner is added
alongside. RAGAS faithfulness/context-precision/recall are computed via the
judge model selected by route_judge (in-boundary on confidential)."""
from __future__ import annotations

import math
from collections.abc import Sequence


def recall_at_k(retrieved: Sequence[str], relevant: set[str], *, k: int) -> float:
    if not relevant:
        return 1.0
    topk = set(retrieved[:k])
    return len(topk & relevant) / len(relevant)


def ndcg_at_k(retrieved: Sequence[str], relevant: set[str], *, k: int) -> float:
    dcg = 0.0
    for i, aid in enumerate(retrieved[:k]):
        if aid in relevant:
            dcg += 1.0 / math.log2(i + 2)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return 0.0 if idcg == 0 else dcg / idcg
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_harness.py -q
```
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/eval/harness.py tigerexchange/packages/retrieval/tests/test_eval_harness.py
git commit -m "feat(eval): add nDCG@k and Recall@k retrieval-quality metrics

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: EvalHarness — PEP-gated run, confidential trace persistence, per-tenant/per-route report

**Files:** Extend `tigerexchange/packages/retrieval/src/eval/harness.py` (`EvalHarness` class); extend `tigerexchange/packages/retrieval/tests/test_eval_harness.py`

The harness ties it together: for each gold item it (1) retrieves via the **same** `IRetrievalStrategy` (which is itself PEP-gated), (2) selects the judge via `route_judge` (in-boundary on confidential), (3) computes RAGAS faithfulness/context-precision/recall via an injected `ragas_fn` (real RAGAS lazily; fake in CI to avoid model load), (4) persists the trace + judge I/O **only** through `ConfidentialEvalStore`, and (5) emits an `EvalReport` tagged with tenant + model route. This is the measurement path mirroring the production security controls.

- [ ] **Step 1: Write the failing test**

Append to `tigerexchange/packages/retrieval/tests/test_eval_harness.py`:
```python
from contracts import PublishableProjection, Tier, DiscoverabilityScope
from eval.harness import EvalHarness
from eval.types import GoldItem
from eval.confidential_store import ConfidentialEvalStore
from tests.conftest import FakeKEKStore


class _StubRetriever:
    def retrieve(self, query, tenant, *, top_k=8):
        return [PublishableProjection(
            projection_id="p1", artifact_id="a1", owner_tenant_id=tenant.tenant_id,
            tier=Tier.public, discoverability_scope=DiscoverabilityScope.FEDERATION_WIDE,
            fields={"text": "grounded context for the answer"})]


def _gen_fn(query, contexts): return "generated grounded answer"


def _ragas_fn(question, contexts, answer, ground_truth, judge_provider):
    # judge_provider must be in-boundary for confidential; record + return metrics
    assert judge_provider.provider_id == "vllm-in-boundary"
    return {"faithfulness": 0.95, "context_precision": 0.9, "context_recall": 0.88}


def test_harness_runs_pep_gated_and_persists_confidential_traces(confidential_tenant, fake_router, fake_kek):
    store = ConfidentialEvalStore(kek_store=fake_kek, tenant_id="anchor-center")
    harness = EvalHarness(retriever=_StubRetriever(), router=fake_router,
                          store=store, generate_fn=_gen_fn, ragas_fn=_ragas_fn)
    gold = [GoldItem(item_id="g1", tenant_id="anchor-center", question="what is X?",
                     ground_truth="X is Y", relevant_artifact_ids=frozenset({"a1"}),
                     subject_ids=frozenset({"s1"}), tier=Tier.confidential)]
    report = harness.run(tenant=confidential_tenant, gold_set=gold, top_k=8)

    assert report.tenant_id == "anchor-center"
    assert report.model_route == "vllm-in-boundary"          # in-boundary judge
    assert report.metrics["faithfulness"] == 0.95
    assert abs(report.metrics["recall@8"] - 1.0) < 1e-9      # a1 retrieved
    # the trace was persisted ONLY through the KEK store (no plaintext side-door)
    blob = next(iter(fake_kek.blobs.values()))
    assert b"grounded context for the answer" not in blob    # encrypted at rest
    # and it crypto-shreds with the tenant KEK
    fake_kek.crypto_shred("anchor-center")
    assert all(store.get_trace(t) is None for t in ("trace-g1",))
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_harness.py -q
```
Expected: FAIL — `ImportError: cannot import name 'EvalHarness'`.

- [ ] **Step 3: Write minimal implementation**

Append to `tigerexchange/packages/retrieval/src/eval/harness.py`:
```python
from collections.abc import Callable, Sequence as _Seq
from typing import Any

from contracts import IModelRouter, IRetrievalStrategy, TenantContext, Tier

from eval.confidential_store import ConfidentialEvalStore
from eval.judge_router import route_judge
from eval.types import EvalReport, EvalTrace, GoldItem, JudgeIO

GenerateFn = Callable[[str, list[str]], str]
RagasFn = Callable[[str, list[str], str, str, Any], dict[str, float]]


def _load_ragas_fn() -> RagasFn:
    """Real RAGAS scorer (faithfulness, context_precision, context_recall),
    judge bound to the routed in-boundary provider. Imported lazily so CI never
    loads model weights on the M4 Max (§15.2)."""
    from ragas import evaluate  # noqa: PLC0415
    from ragas.metrics import context_precision, context_recall, faithfulness  # noqa: PLC0415
    from datasets import Dataset  # noqa: PLC0415

    def _score(question, contexts, answer, ground_truth, judge_provider) -> dict[str, float]:
        ds = Dataset.from_dict({
            "question": [question], "contexts": [list(contexts)],
            "answer": [answer], "ground_truth": [ground_truth],
        })
        result = evaluate(ds, metrics=[faithfulness, context_precision, context_recall],
                          llm=judge_provider)
        return {k: float(v) for k, v in result.items()}

    return _score


class EvalHarness:
    """PEP-gated RAGAS-in-CI harness (plan §9.3, convergence HIGH).

    Retrieval is PEP-gated (the injected IRetrievalStrategy). The judge is bound
    to the in-boundary router (route_judge). Every trace + judge I/O is persisted
    ONLY through the KEK-encrypted ConfidentialEvalStore. Run per-tenant and per
    model-route; emits an EvalReport with RAGAS + nDCG@k/Recall@k."""

    def __init__(
        self,
        *,
        retriever: IRetrievalStrategy,
        router: IModelRouter,
        store: ConfidentialEvalStore,
        generate_fn: GenerateFn,
        ragas_fn: RagasFn | None = None,
    ) -> None:
        self._retriever = retriever
        self._router = router
        self._store = store
        self._generate = generate_fn
        self._ragas = ragas_fn or _load_ragas_fn()

    def run(
        self, *, tenant: TenantContext, gold_set: _Seq[GoldItem], top_k: int = 8
    ) -> EvalReport:
        agg: dict[str, list[float]] = {}
        judge = None
        for item in gold_set:
            # In-boundary judge selection (fail-closed for confidential).
            judge = route_judge(tier=item.tier, tenant=tenant, router=self._router)

            hits = self._retriever.retrieve(item.question, tenant, top_k=top_k)
            contexts = [str(h.fields.get("text", "")) for h in hits]
            retrieved_ids = [h.artifact_id for h in hits]
            answer = self._generate(item.question, contexts)

            # Persist trace + judge I/O ONLY through the KEK-encrypted store.
            self._store.put_trace(EvalTrace(
                trace_id=f"trace-{item.item_id}", tenant_id=tenant.tenant_id,
                item_id=item.item_id, question=item.question,
                retrieved_contexts=tuple(contexts), generated_answer=answer,
                retrieved_artifact_ids=tuple(retrieved_ids),
                subject_ids=item.subject_ids, tier=item.tier,
                compliance_flags=item.compliance_flags,
            ))

            ragas_metrics = self._ragas(
                item.question, contexts, answer, item.ground_truth, judge
            )
            self._store.put_judge_io(JudgeIO(
                judge_io_id=f"judge-{item.item_id}", tenant_id=tenant.tenant_id,
                item_id=item.item_id, judge_prompt=item.question,
                judge_output=str(ragas_metrics), judge_provider_id=judge.provider_id,
                subject_ids=item.subject_ids, tier=item.tier,
            ))

            for name, val in ragas_metrics.items():
                agg.setdefault(name, []).append(val)
            agg.setdefault(f"recall@{top_k}", []).append(
                recall_at_k(retrieved_ids, set(item.relevant_artifact_ids), k=top_k)
            )
            agg.setdefault(f"ndcg@{top_k}", []).append(
                ndcg_at_k(retrieved_ids, set(item.relevant_artifact_ids), k=top_k)
            )

        metrics = {k: sum(v) / len(v) for k, v in agg.items()} if agg else {}
        route_id = judge.provider_id if judge is not None else "none"
        return EvalReport(tenant_id=tenant.tenant_id, model_route=route_id, metrics=metrics)
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_harness.py -q
```
Expected: PASS (5 passed — 4 metrics + 1 harness).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/eval/harness.py tigerexchange/packages/retrieval/tests/test_eval_harness.py
git commit -m "feat(eval): PEP-gated EvalHarness — in-boundary judge, KEK-encrypted traces, per-tenant/per-route RAGAS report

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Release gate — fail the build on regression

**Files:** Create `tigerexchange/packages/retrieval/src/eval/gate.py`, `tigerexchange/packages/retrieval/eval/baseline.json`, `tigerexchange/packages/retrieval/tests/test_eval_gate.py`

The gate compares an `EvalReport` to a pinned baseline; any metric below `baseline - tolerance` fails the build (§9.3 "a release gate"; §15.2 "Eval-in-CI as a retrieval-quality release gate").

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_eval_gate.py`:
```python
import pytest

from eval.types import EvalReport
from eval.gate import assert_no_regression, EvalRegressionError


_BASELINE = {"faithfulness": 0.90, "context_precision": 0.85, "recall@8": 0.80, "ndcg@8": 0.75}


def test_gate_passes_when_metrics_meet_baseline():
    report = EvalReport(tenant_id="t1", model_route="vllm-in-boundary",
                        metrics={"faithfulness": 0.91, "context_precision": 0.86,
                                 "recall@8": 0.82, "ndcg@8": 0.76})
    assert_no_regression(report, baseline=_BASELINE, tolerance=0.02)  # no raise


def test_gate_fails_on_regression_below_tolerance():
    report = EvalReport(tenant_id="t1", model_route="vllm-in-boundary",
                        metrics={"faithfulness": 0.80, "context_precision": 0.86,
                                 "recall@8": 0.82, "ndcg@8": 0.76})
    with pytest.raises(EvalRegressionError) as exc:
        assert_no_regression(report, baseline=_BASELINE, tolerance=0.02)
    assert "faithfulness" in str(exc.value)


def test_gate_fails_when_baseline_metric_missing_from_report():
    report = EvalReport(tenant_id="t1", model_route="vllm-in-boundary",
                        metrics={"faithfulness": 0.95})
    with pytest.raises(EvalRegressionError):
        assert_no_regression(report, baseline=_BASELINE, tolerance=0.02)
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_gate.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.gate'`.

- [ ] **Step 3: Write minimal implementation**

`tigerexchange/packages/retrieval/src/eval/gate.py`:
```python
"""Eval release gate (plan §9.3, §15.2). Fails the build on retrieval-quality
regression: any baseline metric absent from the report, or below
(baseline - tolerance), raises EvalRegressionError."""
from __future__ import annotations

from collections.abc import Mapping

from eval.types import EvalReport


class EvalRegressionError(RuntimeError):
    """Raised when an EvalReport regresses below the pinned baseline (CI gate)."""


def assert_no_regression(
    report: EvalReport, *, baseline: Mapping[str, float], tolerance: float = 0.02
) -> None:
    failures: list[str] = []
    for metric, floor in baseline.items():
        actual = report.metrics.get(metric)
        if actual is None:
            failures.append(f"{metric}: MISSING from report")
        elif actual < floor - tolerance:
            failures.append(f"{metric}: {actual:.3f} < {floor:.3f} - {tolerance:.3f}")
    if failures:
        raise EvalRegressionError(
            "retrieval-quality regression (release gate): " + "; ".join(failures)
        )
```

`tigerexchange/packages/retrieval/eval/baseline.json`:
```json
{
  "faithfulness": 0.90,
  "context_precision": 0.85,
  "context_recall": 0.85,
  "recall@8": 0.80,
  "ndcg@8": 0.75
}
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_eval_gate.py -q
```
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/eval/gate.py tigerexchange/packages/retrieval/eval/baseline.json tigerexchange/packages/retrieval/tests/test_eval_gate.py
git commit -m "feat(eval): add RAGAS-in-CI release gate (fail build on retrieval-quality regression)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Public import surface for retrieval + eval packages

**Files:** Modify `tigerexchange/packages/retrieval/src/retrieval/__init__.py`, `tigerexchange/packages/retrieval/src/eval/__init__.py`; create `tigerexchange/packages/retrieval/tests/test_public_surface.py`

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_public_surface.py`:
```python
def test_retrieval_public_surface():
    from retrieval import (
        HybridRetriever, LocalCrossEncoderReranker, QdrantVectorStore,
        OpenSearchLexicalIndex, RetrievalConfig, reciprocal_rank_fusion, Candidate,
    )
    assert all(x is not None for x in (
        HybridRetriever, LocalCrossEncoderReranker, QdrantVectorStore,
        OpenSearchLexicalIndex, RetrievalConfig, reciprocal_rank_fusion, Candidate))


def test_eval_public_surface():
    from eval import (
        EvalHarness, ConfidentialEvalStore, route_judge, JudgeRoutingError,
        assert_no_regression, EvalRegressionError, ndcg_at_k, recall_at_k,
        GoldItem, EvalTrace, JudgeIO, EvalReport,
    )
    assert all(x is not None for x in (
        EvalHarness, ConfidentialEvalStore, route_judge, JudgeRoutingError,
        assert_no_regression, EvalRegressionError, ndcg_at_k, recall_at_k,
        GoldItem, EvalTrace, JudgeIO, EvalReport))
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_public_surface.py -q
```
Expected: FAIL — `ImportError: cannot import name 'HybridRetriever' from 'retrieval'`.

- [ ] **Step 3: Write minimal implementation**

Overwrite `tigerexchange/packages/retrieval/src/retrieval/__init__.py`:
```python
"""TigerExchange hybrid retrieval package (plan §9.1)."""
from retrieval.config import RetrievalConfig
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.lexical_index import OpenSearchLexicalIndex
from retrieval.reranker import LocalCrossEncoderReranker
from retrieval.rrf import reciprocal_rank_fusion
from retrieval.types import Candidate
from retrieval.vector_store import QdrantVectorStore

__all__ = [
    "RetrievalConfig", "HybridRetriever", "OpenSearchLexicalIndex",
    "LocalCrossEncoderReranker", "reciprocal_rank_fusion", "Candidate",
    "QdrantVectorStore",
]
```

Overwrite `tigerexchange/packages/retrieval/src/eval/__init__.py`:
```python
"""TigerExchange PEP-gated RAGAS eval harness (plan §9.3, §15.2, convergence HIGH)."""
from eval.confidential_store import ConfidentialEvalStore
from eval.gate import EvalRegressionError, assert_no_regression
from eval.harness import EvalHarness, ndcg_at_k, recall_at_k
from eval.judge_router import JudgeRoutingError, route_judge
from eval.types import EvalReport, EvalTrace, GoldItem, JudgeIO

__all__ = [
    "ConfidentialEvalStore", "EvalRegressionError", "assert_no_regression",
    "EvalHarness", "ndcg_at_k", "recall_at_k", "JudgeRoutingError", "route_judge",
    "EvalReport", "EvalTrace", "GoldItem", "JudgeIO",
]
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_public_surface.py -q
```
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/src/retrieval/__init__.py tigerexchange/packages/retrieval/src/eval/__init__.py tigerexchange/packages/retrieval/tests/test_public_surface.py
git commit -m "feat(retrieval,eval): export public import surfaces

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: Full suite green + lint/type checks + import-linter

**Files:** No new source; verification only. (Modify nothing unless a check fails.)

- [ ] **Step 1: Write the failing test**

(No new test — this task verifies the assembled suite + static checks. The "failing" baseline is any lint/type error.) Run:
```bash
cd tigerexchange/packages/retrieval && ruff check src/ && mypy src/
```
Expected initially: any reported ruff/mypy finding is the failure to fix.

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/ -q && ruff check src/ tests/ && mypy src/ && lint-imports --config pyproject.toml
```
Expected: surfaces any residual lint/type/import-contract issue (e.g., unused import, missing annotation).

- [ ] **Step 3: Write minimal implementation**

Fix only what the tools report. Typical fixes: add `from __future__ import annotations` (already present), remove an unused import, or add a return annotation. Apply the smallest edit per finding. (No behavioral change.)

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/ -q && ruff check src/ tests/ && mypy src/ && lint-imports --config pyproject.toml
```
Expected: PASS — all tests green (test_rrf 6, test_reranker 2, test_hybrid_retriever 5, test_eval_confidential_store 7, test_eval_judge_routing 3, test_eval_harness 5, test_eval_gate 3, test_public_surface 2, test_import_linter 1 = 34 passed); ruff clean; mypy clean; import-linter contracts kept.

- [ ] **Step 5: Commit**
```bash
git add -A tigerexchange/packages/retrieval
git commit -m "chore(retrieval,eval): pass full suite + ruff + mypy + import-linter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: Wire the retrieval-eval gate into CI

**Files:** Modify `tigerexchange/.github/workflows/eval-gate.yml` (created/owned by the monorepo scaffold sub-plan; add this package's job)

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_ci_wiring.py`:
```python
"""Assert the retrieval-eval CI job exists and runs the gate-relevant steps."""
from pathlib import Path

WF = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "eval-gate.yml"


def test_eval_gate_workflow_runs_retrieval_eval_job():
    text = WF.read_text()
    assert "retrieval-eval-gate" in text
    assert "packages/retrieval" in text
    # the security-contract eval tests must be named so the gate cannot be skipped
    assert "test_eval_judge_routing.py" in text
    assert "test_eval_confidential_store.py" in text
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_ci_wiring.py -q
```
Expected: FAIL — `FileNotFoundError` (workflow missing the job) or `AssertionError`.

- [ ] **Step 3: Write minimal implementation**

Append a job to `tigerexchange/.github/workflows/eval-gate.yml` (if the file does not yet exist because the scaffold sub-plan defines workflows elsewhere, create it with this single job):
```yaml
  retrieval-eval-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install retrieval package
        working-directory: packages/retrieval
        run: pip install -e ".[dev]"
      # §15.2 retrieval-quality + security-contract gate. Confidential-path tests
      # run against vLLM/cloud GPU staging, never the M4 Max; CI uses injected fakes.
      - name: Run retrieval + PEP-gated eval tests
        working-directory: packages/retrieval
        run: |
          python -m pytest tests/ -q \
            tests/test_eval_judge_routing.py \
            tests/test_eval_confidential_store.py
      - name: Lint + types + import contracts
        working-directory: packages/retrieval
        run: |
          ruff check src/ tests/
          mypy src/
          lint-imports --config pyproject.toml
```

- [ ] **Step 4: Run test to verify it passes**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_ci_wiring.py -q
```
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/.github/workflows/eval-gate.yml tigerexchange/packages/retrieval/tests/test_ci_wiring.py
git commit -m "ci(eval): add retrieval-eval-gate job (RAGAS regression + PEP-gated eval contract tests)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: Integration smoke against live Qdrant + OpenSearch (testcontainers, marked integration)

**Files:** Create `tigerexchange/packages/retrieval/tests/test_engines_integration.py`

Validates the adapters against real engines (not CI fakes), gated behind the `integration` marker so the unit gate stays fast and off the M4 Max. This is the only place real engine SDKs run.

- [ ] **Step 1: Write the failing test**

`tigerexchange/packages/retrieval/tests/test_engines_integration.py`:
```python
"""Integration smoke: HybridRetriever over a live Qdrant + OpenSearch with a
tenant-scoped corpus. Marked `integration` — excluded from the fast unit gate.
Skips automatically if the engines are not reachable."""
import pytest

pytestmark = pytest.mark.integration

QDRANT_URL = "http://localhost:6333"
OS_URL = "http://localhost:9200"


def _qdrant():
    try:
        from qdrant_client import QdrantClient
        c = QdrantClient(url=QDRANT_URL, timeout=2.0)
        c.get_collections()
        return c
    except Exception:
        pytest.skip("Qdrant not reachable on localhost:6333")


def _opensearch():
    try:
        from opensearchpy import OpenSearch
        c = OpenSearch(hosts=[OS_URL], timeout=2)
        c.info()
        return c
    except Exception:
        pytest.skip("OpenSearch not reachable on localhost:9200")


def test_live_hybrid_retrieve_is_tenant_scoped_and_pep_gated(confidential_tenant):
    from retrieval.vector_store import QdrantVectorStore
    from retrieval.lexical_index import OpenSearchLexicalIndex
    from retrieval.hybrid_retriever import HybridRetriever
    from retrieval.reranker import LocalCrossEncoderReranker
    from retrieval.config import RetrievalConfig
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from tests.conftest import FakePEP

    qc = _qdrant()
    osc = _opensearch()
    tid = "anchor-center"

    qc.recreate_collection("research_cards",
                           vectors_config=VectorParams(size=2, distance=Distance.COSINE))
    qc.upsert("research_cards", points=[
        PointStruct(id=1, vector=[0.1, 0.9],
                    payload={"artifact_id": "a1", "owner_tenant_id": tid,
                             "text": "federated learning privacy", "subject_ids": ["s1"]}),
        PointStruct(id=2, vector=[0.9, 0.1],
                    payload={"artifact_id": "x9", "owner_tenant_id": "other",
                             "text": "unrelated", "subject_ids": []}),
    ])
    if osc.indices.exists(index="research_cards"):
        osc.indices.delete(index="research_cards")
    osc.indices.create(index="research_cards")
    osc.index(index="research_cards", id="a1", refresh=True,
              body={"artifact_id": "a1", "owner_tenant_id": tid,
                    "text": "federated learning privacy", "subject_ids": ["s1"]})

    retriever = HybridRetriever(
        vector_store=QdrantVectorStore(client=qc, collection="research_cards"),
        lexical_index=OpenSearchLexicalIndex(client=osc, index="research_cards"),
        reranker=LocalCrossEncoderReranker(score_fn=lambda q, ts: [1.0] * len(ts)),
        pep=FakePEP(), embed_fn=lambda q: [0.1, 0.9],
        config=RetrievalConfig(),
    )
    out = retriever.retrieve("federated learning privacy", confidential_tenant, top_k=8)
    ids = {p.artifact_id for p in out}
    assert "a1" in ids        # tenant's own artifact retrieved + PEP-allowed
    assert "x9" not in ids    # other tenant's artifact filtered at the engine
```

- [ ] **Step 2: Run test to verify it fails**
```bash
cd tigerexchange/packages/retrieval && python -m pytest tests/test_engines_integration.py -m integration -q
```
Expected: FAIL or SKIP — without engines it SKIPs; with engines but before `integration` marker is registered, pytest warns/errors on unknown marker. (The marker must be registered.)

- [ ] **Step 3: Write minimal implementation**

Register the marker in `tigerexchange/packages/retrieval/pyproject.toml` (append):
```toml
[tool.pytest.ini_options]
markers = [
    "integration: requires live Qdrant + OpenSearch (excluded from the fast unit gate)",
]
addopts = "-m 'not integration'"
```

- [ ] **Step 4: Run test to verify it passes**

Start engines, then run:
```bash
docker run -d -p 6333:6333 qdrant/qdrant
docker run -d -p 9200:9200 -e "discovery.type=single-node" -e "DISABLE_SECURITY_PLUGIN=true" opensearchproject/opensearch:2
cd tigerexchange/packages/retrieval && python -m pytest tests/test_engines_integration.py -m integration -q
```
Expected: PASS (1 passed) when engines are up; SKIP cleanly when not. Confirm the unit gate still excludes it: `python -m pytest tests/ -q` collects no integration test.

- [ ] **Step 5: Commit**
```bash
git add tigerexchange/packages/retrieval/tests/test_engines_integration.py tigerexchange/packages/retrieval/pyproject.toml
git commit -m "test(retrieval): add live Qdrant+OpenSearch integration smoke (tenant-scoped, PEP-gated)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes for the implementing worker

- **Kernel signatures are verbatim.** `IRetrievalStrategy.retrieve(query, tenant, *, top_k=8) -> list[PublishableProjection]`, `IReranker.rerank(query, candidates, *, top_k=8) -> list[PublishableProjection]`, `IModelRouter.route(classification, tenant) -> IModelProvider`, `IPolicyEnforcement.authorize(request) -> PepResponse`, `PepRequest`/`PepResponse`/`PepAction`, `ClassificationResult`/`Decision`/`Tier`/`Capability`/`PublishableProjection` are imported from `contracts` exactly as defined in the canonical kernel. The internal `Candidate` type and the `rerank_candidates`/`route_judge`/`assert_no_regression` helpers are package-local and are fully defined in Tasks 2/4/10/13.
- **D6 / fail-closed everywhere.** The retriever drops any non-ALLOW PEP response (Task 7); `PublishableProjection` itself rejects `confidential` tier at validation (kernel), so a confidential read is returned only via the broker's projected non-confidential envelope. The eval judge fails closed (`JudgeRoutingError`) on any non-local provider for non-public tiers (Task 10).
- **The HIGH item is addressed by Tasks 8–10, 12, 16:** eval artifacts are confidential-tier by default (Task 8), persisted only through the KEK-encrypted store with crypto-shred + per-subject erasure (Task 9), judged in-boundary with an enforced routing rule + contract test (Task 10), persisted via the harness with no plaintext side-door (Task 12), and the contract tests are named in the CI gate so they cannot be skipped (Task 16).
- **Dependency seams:** `0c` provides the real `IPolicyEnforcement`/broker (CI uses `FakePEP`), `0f` the real `IModelRouter` (CI uses `FakeModelRouter`), `0g` the real per-tenant KEK derivative store (CI uses `FakeKEKStore`), `0h` the indexed confidential/public corpora the engines query. Swap the fakes for the real injected components at integration time — no retrieval/eval code changes, since all are consumed through kernel Protocols.
- **CI discipline (§15.2):** confidential-path inference (real reranker/judge weights) runs on vLLM/cloud GPU staging, never the M4 Max; unit tests inject `score_fn`/`ragas_fn`/`generate_fn` stubs so the fast gate loads no weights.