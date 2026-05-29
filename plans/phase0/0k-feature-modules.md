The `tigerexchange/` tree is created by the dependency sub-plans (0c-0i). My plan builds the three feature modules atop it. Now I'll write the complete plan.

# Feature Modules (mod-lit-intelligence / mod-discovery / mod-funding-lite) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the three Phase-0 feature modules atop the PEP/broker chokepoint — `mod-lit-intelligence` (grounded, cited proposal drafting + classification-enforced hybrid search whose draft and ALL its persistence inherit the MAX-rule tier and live only in tenant-KEK derivative stores), `mod-discovery` (public-tier OpenAlex expert discovery, zero confidentiality machinery), and `mod-funding-lite` (ranked grant-opportunity match over Grants.gov/RePORTER/NSF).

**Architecture:** Three pluggable modules that consume ONLY kernel interfaces (`contracts.*`) and the broker — they never import a raw store, the classifier, or the projection constructor. `mod-lit-intelligence` retrieves via `IRetrievalStrategy` (already PEP-gated/projected), routes via `IModelRouter`, synthesizes a cited draft, gates it on RAGAS faithfulness, then derives the draft's tier with the kernel MAX-rule (`tier_join_all`) and persists draft + autosave + version-history + synthesizer buffers + RAG cache exclusively through a tenant-KEK-bound derivative store that is registered into the post-crypto-shred zero-decryptable-hits contract suite. `mod-discovery` and `mod-funding-lite` operate purely over public-tier projections.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, the `contracts` kernel package, Qdrant (vector, KEK-volume-bound for confidential), OpenSearch (BM25), Apache AGE (graph), RAGAS-in-CI, pytest/ruff/mypy.

**Depends on:** `0c-pep-broker-chokepoint`, `0f-model-router`, `0g-confidential-kek-stores`, `0h-ingestion-pipelines`, `0i-retrieval-eval`

---

## File Structure

| File | Created/Modified | Single responsibility |
|---|---|---|
| `tigerexchange/modules/__init__.py` | Create | Namespace package marker for feature modules. |
| `tigerexchange/modules/lit_intelligence/__init__.py` | Create | Public surface of `mod-lit-intelligence` (`build_module`, request/response types). |
| `tigerexchange/modules/lit_intelligence/models.py` | Create | Frozen Pydantic request/response/draft DTOs: `DraftRequest`, `Citation`, `ProposalDraft`, `SearchRequest`, `SearchHit`. |
| `tigerexchange/modules/lit_intelligence/draft_store.py` | Create | `IDraftStore` protocol + `TenantKekDraftStore`: persists draft + autosave + version-history under a tenant-KEK-bound DEK; the ONLY persistence path for generated content. |
| `tigerexchange/modules/lit_intelligence/synthesizer_buffer.py` | Create | `KekScratchBuffer`: tenant-KEK-bound ephemeral store for synthesizer intermediate buffers + RAG cache of confidential context (no plaintext at rest). |
| `tigerexchange/modules/lit_intelligence/faithfulness.py` | Create | `FaithfulnessGate` protocol + `RagasFaithfulnessGate`: RAGAS faithfulness scoring + release-gate threshold. |
| `tigerexchange/modules/lit_intelligence/service.py` | Create | `LitIntelligenceService`: orchestrates retrieve→route→synthesize→faithfulness-gate→MAX-rule-tier→KEK-persist; consumes only kernel interfaces + broker. |
| `tigerexchange/modules/lit_intelligence/router.py` | Create | FastAPI `APIRouter` wiring `/v1/lit/search` and `/v1/lit/draft` to the service with `TenantContext` + entitlement enforcement. |
| `tigerexchange/modules/discovery/__init__.py` | Create | Public surface of `mod-discovery`. |
| `tigerexchange/modules/discovery/models.py` | Create | Frozen DTOs: `ExpertQuery`, `Expert`, `ExpertResult`. |
| `tigerexchange/modules/discovery/service.py` | Create | `DiscoveryService`: public-tier expertise fingerprint + collaboration-graph ranking. Zero confidentiality machinery. |
| `tigerexchange/modules/discovery/router.py` | Create | FastAPI `APIRouter` for `/v1/discovery/experts`. |
| `tigerexchange/modules/funding_lite/__init__.py` | Create | Public surface of `mod-funding-lite`. |
| `tigerexchange/modules/funding_lite/models.py` | Create | Frozen DTOs: `FundingQuery`, `GrantOpportunity`, `FundingMatch`, `FundingResult`. |
| `tigerexchange/modules/funding_lite/service.py` | Create | `FundingLiteService`: ranked grant-opportunity match over public grant projections. |
| `tigerexchange/modules/funding_lite/router.py` | Create | FastAPI `APIRouter` for `/v1/funding/match`. |
| `tigerexchange/app/main.py` | Modify | Mount the three module routers onto the FastAPI app skeleton. |
| `tigerexchange/tests/modules/lit_intelligence/test_draft_store.py` | Create | Draft store + autosave/version-history are tenant-KEK-bound; crypto-shred leaves no decryptable hit. |
| `tigerexchange/tests/modules/lit_intelligence/test_synthesizer_buffer.py` | Create | Synthesizer buffers + RAG cache are KEK-bound and shred. |
| `tigerexchange/tests/modules/lit_intelligence/test_faithfulness.py` | Create | RAGAS faithfulness gate accepts/rejects on threshold. |
| `tigerexchange/tests/modules/lit_intelligence/test_service.py` | Create | End-to-end: cited draft, MAX-rule tier, KEK-only persistence, p95<4s budget, only-kernel-imports. |
| `tigerexchange/tests/modules/discovery/test_service.py` | Create | Public-tier expert ranking; no confidential machinery imported. |
| `tigerexchange/tests/modules/funding_lite/test_service.py` | Create | Ranked grant matches over public projections. |
| `tigerexchange/tests/modules/test_module_import_boundaries.py` | Create | import-linter-style assertion: modules import no raw-store/classifier/projection-constructor. |
| `tigerexchange/tests/contract/test_post_crypto_shred_zero_hits.py` | Modify | Add generated-draft + draft-history store to the zero-decryptable-hits contract suite. |
| `tigerexchange/pyproject.toml` | Modify | Add `[tool.importlinter]` contract forbidding modules → raw store / classifier / projection. |

---

## Tasks

### Task 1: mod-lit-intelligence DTOs (frozen request/response/draft models)

**Files:**
- Create `tigerexchange/modules/__init__.py`
- Create `tigerexchange/modules/lit_intelligence/__init__.py`
- Create `tigerexchange/modules/lit_intelligence/models.py`
- Test `tigerexchange/tests/modules/lit_intelligence/__init__.py`, `tigerexchange/tests/modules/lit_intelligence/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/lit_intelligence/test_models.py
import pytest
from pydantic import ValidationError

from contracts import Tier
from modules.lit_intelligence.models import (
    Citation,
    DraftRequest,
    ProposalDraft,
    SearchHit,
    SearchRequest,
)


def test_draft_request_is_frozen_and_typed():
    req = DraftRequest(section="Specific Aims", prompt="Draft aims for a CRISPR delivery study", top_k=8)
    assert req.section == "Specific Aims"
    assert req.top_k == 8
    with pytest.raises(ValidationError):
        DraftRequest(section="x", prompt="y", top_k=0)  # top_k must be >= 1
    with pytest.raises((TypeError, ValidationError)):
        req.section = "mutated"  # frozen


def test_citation_binds_source_and_span():
    c = Citation(source_id="paper:openalex:W123", snippet="lipid nanoparticles...", projection_id="proj-1")
    assert c.source_id == "paper:openalex:W123"


def test_proposal_draft_carries_max_rule_tier_and_citations():
    draft = ProposalDraft(
        draft_id="d-1",
        section="Specific Aims",
        body="Aim 1 ...[1]",
        citations=(Citation(source_id="s1", snippet="...", projection_id="p1"),),
        tier=Tier.confidential,
        faithfulness=0.91,
    )
    assert draft.tier is Tier.confidential
    assert len(draft.citations) == 1
    with pytest.raises((TypeError, ValidationError)):
        draft.body = "x"  # frozen


def test_search_hit_carries_tier_and_score():
    hit = SearchHit(projection_id="p1", title="t", snippet="s", tier=Tier.public, score=0.7)
    assert hit.tier is Tier.public
    req = SearchRequest(query="gene editing", top_k=5)
    assert req.top_k == 5
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_models.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.lit_intelligence.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/__init__.py
"""TigerExchange Phase-0 feature modules. Each module consumes ONLY the kernel
(`contracts`) interfaces + the data-access broker — never a raw store, the
classifier, or the PublishableProjection constructor (enforced by import-linter)."""
```

```python
# tigerexchange/modules/lit_intelligence/__init__.py
"""mod-lit-intelligence: grounded, cited proposal drafting + classification-enforced
hybrid search over the tenant's own corpus + public scholarly data (plan §3.1, §8.5, §9.1).

The generated draft and ALL its persistence (autosave, version history, synthesizer
intermediate buffers, RAG cache of confidential context) inherit the MAX-rule tier of
their grounding sources and live ONLY in tenant-KEK-bound derivative stores (§11.3b)."""

from modules.lit_intelligence.models import (
    Citation,
    DraftRequest,
    ProposalDraft,
    SearchHit,
    SearchRequest,
)

__all__ = ["Citation", "DraftRequest", "ProposalDraft", "SearchHit", "SearchRequest"]
```

```python
# tigerexchange/modules/lit_intelligence/models.py
"""Frozen DTOs for mod-lit-intelligence. No persistence, no kernel-rule logic here."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from contracts import Tier


class SearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    query: str
    top_k: int = Field(default=8, ge=1, le=50)


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)
    projection_id: str
    title: str
    snippet: str
    tier: Tier
    score: float


class Citation(BaseModel):
    """A grounding citation bound to the projection it was retrieved from."""

    model_config = ConfigDict(frozen=True)
    source_id: str
    snippet: str
    projection_id: str


class DraftRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    section: str
    prompt: str
    top_k: int = Field(default=8, ge=1, le=50)


class ProposalDraft(BaseModel):
    """A generated proposal section. `tier` is the MAX-rule join over grounding
    sources (§11.5); the draft is persisted only in tenant-KEK stores (§11.3b)."""

    model_config = ConfigDict(frozen=True)
    draft_id: str
    section: str
    body: str
    citations: tuple[Citation, ...]
    tier: Tier
    faithfulness: float = Field(ge=0.0, le=1.0)
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_models.py -q`
  - Expected: `5 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/__init__.py modules/lit_intelligence/__init__.py modules/lit_intelligence/models.py tests/modules/lit_intelligence/__init__.py tests/modules/lit_intelligence/test_models.py`
  - `git commit -m "feat(mod-lit): add frozen request/response/draft DTOs with MAX-rule tier field"`

---

### Task 2: Tenant-KEK draft store (draft + autosave + version history)

Implements the highs_addressed core: the generated draft + draft-history store is tenant-KEK-bound so crypto-shred reaches it (convergence-report lines 25-27, §11.3b).

**Files:**
- Create `tigerexchange/modules/lit_intelligence/draft_store.py`
- Test `tigerexchange/tests/modules/lit_intelligence/test_draft_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/lit_intelligence/test_draft_store.py
import pytest

from contracts import Tier
from modules.lit_intelligence.draft_store import TenantKekDraftStore
from modules.lit_intelligence.models import Citation, ProposalDraft


class FakeKek:
    """Test double for the tenant KEK/DEK envelope (0g-confidential-kek-stores).

    Encryption XORs with a per-tenant key byte; crypto-shred drops the key so
    stored ciphertext becomes undecryptable (models §11.3b crypto-shred)."""

    def __init__(self):
        self._keys: dict[str, int] = {}

    def ensure_dek(self, tenant_id: str) -> None:
        self._keys.setdefault(tenant_id, (hash(tenant_id) % 250) + 1)

    def encrypt(self, tenant_id: str, plaintext: bytes) -> bytes:
        k = self._keys[tenant_id]
        return bytes(b ^ k for b in plaintext)

    def decrypt(self, tenant_id: str, ciphertext: bytes) -> bytes:
        if tenant_id not in self._keys:
            raise KeyError("DEK crypto-shredded; ciphertext undecryptable")
        k = self._keys[tenant_id]
        return bytes(b ^ k for b in ciphertext)

    def crypto_shred(self, tenant_id: str) -> None:
        self._keys.pop(tenant_id, None)


def _draft(draft_id: str, body: str) -> ProposalDraft:
    return ProposalDraft(
        draft_id=draft_id,
        section="Aims",
        body=body,
        citations=(Citation(source_id="s1", snippet="x", projection_id="p1"),),
        tier=Tier.confidential,
        faithfulness=0.9,
    )


def test_save_and_load_roundtrips_through_kek():
    kek = FakeKek()
    store = TenantKekDraftStore(kek=kek)
    store.save("tenant-A", _draft("d1", "Aim 1 body"))
    loaded = store.load("tenant-A", "d1")
    assert loaded.body == "Aim 1 body"
    assert loaded.tier is Tier.confidential


def test_autosave_appends_version_history():
    kek = FakeKek()
    store = TenantKekDraftStore(kek=kek)
    store.save("tenant-A", _draft("d1", "v1"))
    store.autosave("tenant-A", "d1", "v2")
    store.autosave("tenant-A", "d1", "v3")
    history = store.version_history("tenant-A", "d1")
    assert [h.body for h in history] == ["v1", "v2", "v3"]


def test_nothing_persisted_in_plaintext():
    kek = FakeKek()
    store = TenantKekDraftStore(kek=kek)
    store.save("tenant-A", _draft("d1", "SECRET-AIM"))
    raw = store.raw_bytes_for_test("tenant-A")
    assert b"SECRET-AIM" not in raw  # only ciphertext at rest


def test_crypto_shred_leaves_no_decryptable_draft_or_history():
    kek = FakeKek()
    store = TenantKekDraftStore(kek=kek)
    store.save("tenant-A", _draft("d1", "v1"))
    store.autosave("tenant-A", "d1", "v2")
    kek.crypto_shred("tenant-A")
    with pytest.raises(KeyError):
        store.load("tenant-A", "d1")
    assert store.decryptable_hits("tenant-A") == 0


def test_tenant_isolation_no_cross_tenant_read():
    kek = FakeKek()
    store = TenantKekDraftStore(kek=kek)
    store.save("tenant-A", _draft("d1", "A-secret"))
    with pytest.raises(KeyError):
        store.load("tenant-B", "d1")
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_draft_store.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.lit_intelligence.draft_store'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/lit_intelligence/draft_store.py
"""Tenant-KEK-bound persistence for generated proposal drafts + autosave +
version history (§11.3b, convergence-report HIGH).

The generated draft is the highest-value confidential artifact. It is persisted
ONLY here, encrypted under the tenant KEK/DEK, so KEK crypto-shred (§11.3) and
per-subject erasure (§11.7) cryptographically shred it and its history. Nothing
is written in plaintext at rest. This store is registered into the
post-crypto-shred zero-decryptable-hits contract test."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from contracts import Tier
from modules.lit_intelligence.models import ProposalDraft


@runtime_checkable
class TenantKek(Protocol):
    """The tenant KEK/DEK envelope provided by 0g-confidential-kek-stores."""

    def ensure_dek(self, tenant_id: str) -> None: ...
    def encrypt(self, tenant_id: str, plaintext: bytes) -> bytes: ...
    def decrypt(self, tenant_id: str, ciphertext: bytes) -> bytes: ...
    def crypto_shred(self, tenant_id: str) -> None: ...


@runtime_checkable
class IDraftStore(Protocol):
    def save(self, tenant_id: str, draft: ProposalDraft) -> None: ...
    def load(self, tenant_id: str, draft_id: str) -> ProposalDraft: ...
    def autosave(self, tenant_id: str, draft_id: str, body: str) -> None: ...
    def version_history(self, tenant_id: str, draft_id: str) -> list[ProposalDraft]: ...
    def decryptable_hits(self, tenant_id: str) -> int: ...


class TenantKekDraftStore:
    """Phase-0 in-cell draft store. Backing bytes are ALWAYS KEK-encrypted.

    The container is keyed by tenant; the only way to read a draft is via the
    tenant's live DEK. After crypto-shred the DEK is gone and every entry is
    undecryptable (zero decryptable hits)."""

    def __init__(self, kek: TenantKek) -> None:
        self._kek = kek
        # tenant_id -> draft_id -> list[ciphertext] (version history, newest last)
        self._blobs: dict[str, dict[str, list[bytes]]] = {}

    def _serialize(self, draft: ProposalDraft) -> bytes:
        return draft.model_dump_json().encode("utf-8")

    def _deserialize(self, raw: bytes) -> ProposalDraft:
        return ProposalDraft.model_validate_json(raw.decode("utf-8"))

    def save(self, tenant_id: str, draft: ProposalDraft) -> None:
        self._kek.ensure_dek(tenant_id)
        ct = self._kek.encrypt(tenant_id, self._serialize(draft))
        self._blobs.setdefault(tenant_id, {})[draft.draft_id] = [ct]

    def load(self, tenant_id: str, draft_id: str) -> ProposalDraft:
        versions = self._blobs.get(tenant_id, {}).get(draft_id)
        if not versions:
            raise KeyError(f"no draft {draft_id} for tenant {tenant_id}")
        pt = self._kek.decrypt(tenant_id, versions[-1])  # raises if shredded
        return self._deserialize(pt)

    def autosave(self, tenant_id: str, draft_id: str, body: str) -> None:
        current = self.load(tenant_id, draft_id)
        new_version = current.model_copy(update={"body": body})
        ct = self._kek.encrypt(tenant_id, self._serialize(new_version))
        self._blobs[tenant_id][draft_id].append(ct)

    def version_history(self, tenant_id: str, draft_id: str) -> list[ProposalDraft]:
        versions = self._blobs.get(tenant_id, {}).get(draft_id, [])
        return [self._deserialize(self._kek.decrypt(tenant_id, ct)) for ct in versions]

    def decryptable_hits(self, tenant_id: str) -> int:
        hits = 0
        for versions in self._blobs.get(tenant_id, {}).values():
            for ct in versions:
                try:
                    self._kek.decrypt(tenant_id, ct)
                    hits += 1
                except KeyError:
                    pass
        return hits

    def raw_bytes_for_test(self, tenant_id: str) -> bytes:
        out = b""
        for versions in self._blobs.get(tenant_id, {}).values():
            for ct in versions:
                out += ct
        return out
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_draft_store.py -q`
  - Expected: `5 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/lit_intelligence/draft_store.py tests/modules/lit_intelligence/test_draft_store.py`
  - `git commit -m "feat(mod-lit): KEK-bound draft store with autosave/version-history; crypto-shred leaves zero decryptable hits"`

---

### Task 3: KEK-bound synthesizer scratch buffer + RAG cache

Folds in the highs_addressed clause: synthesizer intermediate buffers + RAG cache of confidential context are KEK-bound and shred (§11.3b).

**Files:**
- Create `tigerexchange/modules/lit_intelligence/synthesizer_buffer.py`
- Test `tigerexchange/tests/modules/lit_intelligence/test_synthesizer_buffer.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/lit_intelligence/test_synthesizer_buffer.py
import pytest

from modules.lit_intelligence.synthesizer_buffer import KekScratchBuffer
from tests.modules.lit_intelligence.test_draft_store import FakeKek


def test_buffer_roundtrips_intermediate_and_cache():
    kek = FakeKek()
    buf = KekScratchBuffer(kek=kek)
    buf.put_intermediate("tenant-A", "step-1", b"partial-synthesis")
    buf.put_rag_cache("tenant-A", "ctxhash", b"confidential-context")
    assert buf.get_intermediate("tenant-A", "step-1") == b"partial-synthesis"
    assert buf.get_rag_cache("tenant-A", "ctxhash") == b"confidential-context"


def test_nothing_in_plaintext():
    kek = FakeKek()
    buf = KekScratchBuffer(kek=kek)
    buf.put_rag_cache("tenant-A", "h", b"TOP-SECRET-CTX")
    assert b"TOP-SECRET-CTX" not in buf.raw_bytes_for_test("tenant-A")


def test_crypto_shred_shreds_buffers_and_cache():
    kek = FakeKek()
    buf = KekScratchBuffer(kek=kek)
    buf.put_intermediate("tenant-A", "s", b"x")
    buf.put_rag_cache("tenant-A", "h", b"y")
    kek.crypto_shred("tenant-A")
    assert buf.decryptable_hits("tenant-A") == 0
    with pytest.raises(KeyError):
        buf.get_intermediate("tenant-A", "s")
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_synthesizer_buffer.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.lit_intelligence.synthesizer_buffer'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/lit_intelligence/synthesizer_buffer.py
"""Tenant-KEK-bound ephemeral store for synthesizer intermediate buffers and the
RAG cache of confidential grounding context (§11.3b, convergence-report HIGH).

These are derivatives of confidential content; per the MAX-rule they inherit the
confidential tier and MUST be KEK-bound so crypto-shred reaches them. No plaintext
at rest; covered by the post-crypto-shred zero-decryptable-hits contract test."""

from __future__ import annotations

from modules.lit_intelligence.draft_store import TenantKek


class KekScratchBuffer:
    def __init__(self, kek: TenantKek) -> None:
        self._kek = kek
        self._intermediate: dict[str, dict[str, bytes]] = {}
        self._rag_cache: dict[str, dict[str, bytes]] = {}

    def put_intermediate(self, tenant_id: str, key: str, data: bytes) -> None:
        self._kek.ensure_dek(tenant_id)
        self._intermediate.setdefault(tenant_id, {})[key] = self._kek.encrypt(tenant_id, data)

    def get_intermediate(self, tenant_id: str, key: str) -> bytes:
        ct = self._intermediate.get(tenant_id, {})[key]
        return self._kek.decrypt(tenant_id, ct)

    def put_rag_cache(self, tenant_id: str, key: str, data: bytes) -> None:
        self._kek.ensure_dek(tenant_id)
        self._rag_cache.setdefault(tenant_id, {})[key] = self._kek.encrypt(tenant_id, data)

    def get_rag_cache(self, tenant_id: str, key: str) -> bytes:
        ct = self._rag_cache.get(tenant_id, {})[key]
        return self._kek.decrypt(tenant_id, ct)

    def decryptable_hits(self, tenant_id: str) -> int:
        hits = 0
        for store in (self._intermediate, self._rag_cache):
            for ct in store.get(tenant_id, {}).values():
                try:
                    self._kek.decrypt(tenant_id, ct)
                    hits += 1
                except KeyError:
                    pass
        return hits

    def raw_bytes_for_test(self, tenant_id: str) -> bytes:
        out = b""
        for store in (self._intermediate, self._rag_cache):
            for ct in store.get(tenant_id, {}).values():
                out += ct
        return out
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_synthesizer_buffer.py -q`
  - Expected: `3 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/lit_intelligence/synthesizer_buffer.py tests/modules/lit_intelligence/test_synthesizer_buffer.py`
  - `git commit -m "feat(mod-lit): KEK-bound synthesizer scratch buffer + RAG cache for confidential context"`

---

### Task 4: RAGAS faithfulness release gate

**Files:**
- Create `tigerexchange/modules/lit_intelligence/faithfulness.py`
- Test `tigerexchange/tests/modules/lit_intelligence/test_faithfulness.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/lit_intelligence/test_faithfulness.py
import pytest

from modules.lit_intelligence.faithfulness import FaithfulnessVerdict, RagasFaithfulnessGate


class StubScorer:
    """Stands in for the RAGAS faithfulness scorer (router-aware, local judge §9.3)."""

    def __init__(self, score: float) -> None:
        self._score = score

    def score(self, answer: str, contexts: list[str]) -> float:
        return self._score


def test_gate_passes_above_threshold():
    gate = RagasFaithfulnessGate(scorer=StubScorer(0.85), threshold=0.80)
    verdict = gate.evaluate(answer="grounded answer [1]", contexts=["ctx a", "ctx b"])
    assert isinstance(verdict, FaithfulnessVerdict)
    assert verdict.passed is True
    assert verdict.score == 0.85


def test_gate_fails_below_threshold():
    gate = RagasFaithfulnessGate(scorer=StubScorer(0.50), threshold=0.80)
    verdict = gate.evaluate(answer="hallucinated", contexts=["ctx"])
    assert verdict.passed is False


def test_gate_fails_closed_on_empty_contexts():
    gate = RagasFaithfulnessGate(scorer=StubScorer(0.99), threshold=0.80)
    verdict = gate.evaluate(answer="ungrounded", contexts=[])
    assert verdict.passed is False
    assert verdict.score == 0.0
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_faithfulness.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.lit_intelligence.faithfulness'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/lit_intelligence/faithfulness.py
"""RAGAS faithfulness release gate for grounded proposal drafting (§8.5, §9.3).

A grounded draft must be faithful to its retrieved contexts before it is returned
or persisted. The judge LLM is the LOCAL model on the confidential tier (§9.3); the
scorer is injected so the route is decided by the model router, not hardcoded here.
Fail-closed: no contexts => not faithful (score 0.0, fail)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


@runtime_checkable
class FaithfulnessScorer(Protocol):
    def score(self, answer: str, contexts: list[str]) -> float: ...


class FaithfulnessVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)
    score: float
    threshold: float
    passed: bool


class RagasFaithfulnessGate:
    def __init__(self, scorer: FaithfulnessScorer, threshold: float = 0.80) -> None:
        self._scorer = scorer
        self._threshold = threshold

    def evaluate(self, answer: str, contexts: list[str]) -> FaithfulnessVerdict:
        if not contexts:
            return FaithfulnessVerdict(score=0.0, threshold=self._threshold, passed=False)
        score = self._scorer.score(answer, contexts)
        return FaithfulnessVerdict(
            score=score, threshold=self._threshold, passed=score >= self._threshold
        )
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_faithfulness.py -q`
  - Expected: `3 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/lit_intelligence/faithfulness.py tests/modules/lit_intelligence/test_faithfulness.py`
  - `git commit -m "feat(mod-lit): RAGAS faithfulness release gate, fail-closed on empty contexts"`

---

### Task 5: LitIntelligenceService — retrieve→route→synthesize→gate→MAX-rule→KEK-persist

**Files:**
- Create `tigerexchange/modules/lit_intelligence/service.py`
- Test `tigerexchange/tests/modules/lit_intelligence/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/lit_intelligence/test_service.py
import time

import pytest

from contracts import (
    Capability,
    ClassificationResult,
    Decision,
    Edition,
    Entitlement,
    IsolationPosture,
    PublishableProjection,
    Tier,
    TenantContext,
)
from modules.lit_intelligence.models import DraftRequest, SearchRequest
from modules.lit_intelligence.draft_store import TenantKekDraftStore
from modules.lit_intelligence.faithfulness import RagasFaithfulnessGate
from modules.lit_intelligence.service import LitIntelligenceService
from modules.lit_intelligence.synthesizer_buffer import KekScratchBuffer
from tests.modules.lit_intelligence.test_draft_store import FakeKek


def _tenant() -> TenantContext:
    ent = Entitlement(
        edition=Edition.INSTITUTIONAL,
        capabilities=frozenset({Capability.OWN_MATERIALS, Capability.PUBLIC_RETRIEVAL}),
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.confidential,
    )
    return TenantContext(tenant_id="tenant-A", subject_id="pi-1", entitlement=ent)


def _proj(pid: str, tier: Tier) -> PublishableProjection:
    return PublishableProjection(
        projection_id=pid,
        artifact_id=f"art-{pid}",
        owner_tenant_id="tenant-A",
        tier=tier,
        discoverability_scope="federation-wide",
        fields={"title": f"title-{pid}", "snippet": f"snippet-{pid}"},
    )


class FakeRetrieval:
    """IRetrievalStrategy double: returns already-PEP-gated, already-projected hits.

    NOTE: PublishableProjection caps at private (D6 forbids confidential). The
    grounding sources here carry public + private projections; the service derives
    the DRAFT tier with the kernel MAX-rule over the source tiers + the classifier
    result for the prompt itself."""

    def __init__(self, projections):
        self._projections = projections

    def retrieve(self, query, tenant, *, top_k=8):
        return list(self._projections)[:top_k]


class FakeProvider:
    provider_id = "local-vllm"

    def satisfies_locality(self, tier):
        return True

    def no_retention_attested(self):
        return True

    def generate(self, prompt: str, contexts: list[str]) -> str:
        return "Aim 1 grounded on the corpus [1][2]."


class FakeRouter:
    def __init__(self, provider):
        self._provider = provider

    def route(self, classification, tenant):
        return self._provider


class FakeClassifier:
    """The prompt itself is classified; here it lands at private (own-corpus draft)."""

    def classify(self, content, tenant):
        return ClassificationResult(tier=Tier.private, decision=Decision.ALLOW, confidence=0.95)


class StubScorer:
    def score(self, answer, contexts):
        return 0.92


def _service(projections, *, kek=None):
    kek = kek or FakeKek()
    return LitIntelligenceService(
        retrieval=FakeRetrieval(projections),
        router=FakeRouter(FakeProvider()),
        classifier=FakeClassifier(),
        gate=RagasFaithfulnessGate(scorer=StubScorer(), threshold=0.80),
        draft_store=TenantKekDraftStore(kek=kek),
        scratch=KekScratchBuffer(kek=kek),
    )


def test_search_returns_classification_enforced_hits():
    svc = _service([_proj("p1", Tier.public), _proj("p2", Tier.private)])
    hits = svc.search(_tenant(), SearchRequest(query="gene editing", top_k=5))
    assert {h.projection_id for h in hits} == {"p1", "p2"}
    assert all(h.snippet for h in hits)


def test_draft_is_cited_and_persisted_kek_bound():
    svc = _service([_proj("p1", Tier.public), _proj("p2", Tier.private)])
    draft = svc.draft(_tenant(), DraftRequest(section="Aims", prompt="draft aims", top_k=2))
    assert draft.body  # grounded text
    assert len(draft.citations) == 2  # one per grounding source
    # MAX-rule: join(public, private, prompt=private) == private
    assert draft.tier is Tier.private
    # persisted and re-loadable through the KEK store
    reloaded = svc.load_draft(_tenant(), draft.draft_id)
    assert reloaded.body == draft.body


def test_draft_tier_uses_max_rule_when_classifier_tightens():
    # classifier returns confidential for the prompt -> draft tier MUST be confidential
    svc = _service([_proj("p1", Tier.public)])
    svc._classifier = type(
        "C", (), {"classify": lambda self, c, t: ClassificationResult(
            tier=Tier.confidential, decision=Decision.ALLOW, confidence=0.99)}
    )()
    draft = svc.draft(_tenant(), DraftRequest(section="Aims", prompt="confidential", top_k=1))
    assert draft.tier is Tier.confidential


def test_draft_rejected_when_faithfulness_below_threshold():
    svc = _service([_proj("p1", Tier.public)])
    svc._gate = RagasFaithfulnessGate(scorer=type("S", (), {"score": lambda s, a, c: 0.10})(), threshold=0.80)
    with pytest.raises(ValueError, match="faithfulness"):
        svc.draft(_tenant(), DraftRequest(section="Aims", prompt="x", top_k=1))


def test_draft_p95_under_4s_budget():
    svc = _service([_proj(f"p{i}", Tier.public) for i in range(8)])
    latencies = []
    for _ in range(20):
        t0 = time.perf_counter()
        svc.draft(_tenant(), DraftRequest(section="Aims", prompt="draft", top_k=8))
        latencies.append(time.perf_counter() - t0)
    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies)) - 1]
    assert p95 < 4.0  # deliverable: grounded cited draft at p95<4s
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_service.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.lit_intelligence.service'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/lit_intelligence/service.py
"""mod-lit-intelligence orchestration (plan §8.5, §9.1, §11.5, §11.3b).

Flow: retrieve (already PEP-gated/projected) -> route to a locality-compliant
provider -> synthesize a cited section grounded ONLY in retrieved contexts ->
RAGAS faithfulness gate -> derive the DRAFT tier via the kernel MAX-rule
(tier_join_all over source tiers + the classifier's tier for the prompt) ->
persist draft + buffers + RAG cache ONLY in tenant-KEK stores.

This module imports ONLY the kernel (`contracts`) + its own KEK stores. It never
imports a raw store, the classifier impl, or the PublishableProjection constructor."""

from __future__ import annotations

import uuid

from contracts import (
    Capability,
    IClassifier,
    IModelRouter,
    IRetrievalStrategy,
    Tier,
    TenantContext,
    tier_join_all,
)
from modules.lit_intelligence.draft_store import IDraftStore
from modules.lit_intelligence.faithfulness import RagasFaithfulnessGate
from modules.lit_intelligence.models import (
    Citation,
    DraftRequest,
    ProposalDraft,
    SearchHit,
    SearchRequest,
)
from modules.lit_intelligence.synthesizer_buffer import KekScratchBuffer


class _Provider:
    """Structural type for a routed provider that can generate text."""

    provider_id: str

    def generate(self, prompt: str, contexts: list[str]) -> str: ...


class LitIntelligenceService:
    def __init__(
        self,
        retrieval: IRetrievalStrategy,
        router: IModelRouter,
        classifier: IClassifier,
        gate: RagasFaithfulnessGate,
        draft_store: IDraftStore,
        scratch: KekScratchBuffer,
    ) -> None:
        self._retrieval = retrieval
        self._router = router
        self._classifier = classifier
        self._gate = gate
        self._draft_store = draft_store
        self._scratch = scratch

    def _require(self, tenant: TenantContext, cap: Capability) -> None:
        if not tenant.entitlement.has(cap):
            raise PermissionError(f"tenant {tenant.tenant_id} lacks capability {cap}")

    def search(self, tenant: TenantContext, req: SearchRequest) -> list[SearchHit]:
        self._require(tenant, Capability.PUBLIC_RETRIEVAL)
        projections = self._retrieval.retrieve(req.query, tenant, top_k=req.top_k)
        hits: list[SearchHit] = []
        for rank, p in enumerate(projections):
            hits.append(
                SearchHit(
                    projection_id=p.projection_id,
                    title=str(p.fields.get("title", "")),
                    snippet=str(p.fields.get("snippet", "")),
                    tier=p.tier,
                    score=1.0 / (rank + 1),
                )
            )
        return hits

    def draft(self, tenant: TenantContext, req: DraftRequest) -> ProposalDraft:
        # OWN_MATERIALS gates grounded drafting over the tenant's own corpus.
        self._require(tenant, Capability.OWN_MATERIALS)
        projections = self._retrieval.retrieve(req.prompt, tenant, top_k=req.top_k)

        contexts = [str(p.fields.get("snippet", "")) for p in projections]
        citations = tuple(
            Citation(
                source_id=p.artifact_id,
                snippet=str(p.fields.get("snippet", "")),
                projection_id=p.projection_id,
            )
            for p in projections
        )

        # Classify the prompt; route to a locality-compliant provider.
        classification = self._classifier.classify(req.prompt.encode("utf-8"), tenant)
        provider: _Provider = self._router.route(classification, tenant)  # type: ignore[assignment]

        body = provider.generate(req.prompt, contexts)

        # KEK-bound RAG cache of the (confidential) grounding context + buffer.
        draft_id = f"draft-{uuid.uuid4().hex}"
        self._scratch.put_rag_cache(
            tenant.tenant_id, draft_id, "\n".join(contexts).encode("utf-8")
        )
        self._scratch.put_intermediate(tenant.tenant_id, draft_id, body.encode("utf-8"))

        # Faithfulness release gate (§9.3).
        verdict = self._gate.evaluate(answer=body, contexts=contexts)
        if not verdict.passed:
            raise ValueError(
                f"draft rejected: faithfulness {verdict.score} < {verdict.threshold}"
            )

        # MAX-rule tier (§11.5): join source tiers with the prompt's classified tier.
        source_tiers = [p.tier for p in projections] + [classification.tier]
        draft_tier: Tier = tier_join_all(source_tiers)

        draft = ProposalDraft(
            draft_id=draft_id,
            section=req.section,
            body=body,
            citations=citations,
            tier=draft_tier,
            faithfulness=verdict.score,
        )
        # Persist ONLY in the tenant-KEK store (§11.3b).
        self._draft_store.save(tenant.tenant_id, draft)
        return draft

    def load_draft(self, tenant: TenantContext, draft_id: str) -> ProposalDraft:
        self._require(tenant, Capability.OWN_MATERIALS)
        return self._draft_store.load(tenant.tenant_id, draft_id)
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/lit_intelligence/test_service.py -q`
  - Expected: `5 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/lit_intelligence/service.py tests/modules/lit_intelligence/test_service.py`
  - `git commit -m "feat(mod-lit): grounded cited drafting service with MAX-rule tier, faithfulness gate, KEK-only persistence, p95<4s"`

---

### Task 6: mod-discovery — public-tier expert discovery over OpenAlex

Zero confidentiality machinery (§3.1/§3.2): expertise fingerprint similarity + collaboration-graph context, public-tier only.

**Files:**
- Create `tigerexchange/modules/discovery/__init__.py`
- Create `tigerexchange/modules/discovery/models.py`
- Create `tigerexchange/modules/discovery/service.py`
- Test `tigerexchange/tests/modules/discovery/__init__.py`, `tigerexchange/tests/modules/discovery/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/discovery/test_service.py
from modules.discovery.models import ExpertQuery
from modules.discovery.service import DiscoveryService


class FakeFingerprint:
    """IExpertiseFingerprint double over public OpenAlex SPECTER2 vectors (§9.2)."""

    def __init__(self):
        self._sim = {("seed", "r1"): 0.9, ("seed", "r2"): 0.4, ("seed", "r3"): 0.7}

    def fingerprint(self, researcher_id):
        return [0.0]

    def similarity(self, a, b):
        return self._sim.get((a, b), 0.0)


class FakeGraph:
    """ICollaborationGraph double: public cross-institution collaboration edges (§9.2)."""

    def neighbors(self, researcher_id, *, hops=1):
        return {"seed": ["r1"]}.get(researcher_id, [])

    def candidate_collaborators(self, researcher_id, *, limit=50):
        return ["r1", "r2", "r3"][:limit]


def test_returns_ranked_public_experts_by_fingerprint_similarity():
    svc = DiscoveryService(fingerprint=FakeFingerprint(), graph=FakeGraph())
    result = svc.find_experts(ExpertQuery(seed_researcher_id="seed", top_k=3))
    ranked = [e.researcher_id for e in result.experts]
    assert ranked == ["r1", "r3", "r2"]  # 0.9, 0.7, 0.4
    assert all(e.tier == "public" for e in result.experts)


def test_collaboration_context_flag_set_for_existing_collaborators():
    svc = DiscoveryService(fingerprint=FakeFingerprint(), graph=FakeGraph())
    result = svc.find_experts(ExpertQuery(seed_researcher_id="seed", top_k=3))
    by_id = {e.researcher_id: e for e in result.experts}
    assert by_id["r1"].prior_collaborator is True
    assert by_id["r2"].prior_collaborator is False


def test_top_k_truncates():
    svc = DiscoveryService(fingerprint=FakeFingerprint(), graph=FakeGraph())
    result = svc.find_experts(ExpertQuery(seed_researcher_id="seed", top_k=2))
    assert len(result.experts) == 2
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/discovery/test_service.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.discovery.service'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/discovery/__init__.py
"""mod-discovery: cross-institution PUBLIC-tier expert discovery over OpenAlex
(expertise fingerprint + collaboration graph). ZERO confidentiality machinery
(plan §3.1, §3.2, §9.2) — no KEK, no PEP, no classifier."""

from modules.discovery.models import Expert, ExpertQuery, ExpertResult

__all__ = ["Expert", "ExpertQuery", "ExpertResult"]
```

```python
# tigerexchange/modules/discovery/models.py
"""Frozen DTOs for mod-discovery. Public-tier only."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExpertQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    seed_researcher_id: str
    top_k: int = Field(default=10, ge=1, le=100)


class Expert(BaseModel):
    model_config = ConfigDict(frozen=True)
    researcher_id: str
    similarity: float
    prior_collaborator: bool
    tier: Literal["public"] = "public"  # public-tier by construction (§6.3)


class ExpertResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    experts: tuple[Expert, ...]
```

```python
# tigerexchange/modules/discovery/service.py
"""Public-tier expert discovery (plan §3.2, §9.2).

Consumes ONLY the kernel IExpertiseFingerprint + ICollaborationGraph interfaces.
Public-tier by construction (§6.3): confidential records never contribute, so this
module has zero KEK/PEP/classifier dependencies."""

from __future__ import annotations

from contracts import ICollaborationGraph, IExpertiseFingerprint
from modules.discovery.models import Expert, ExpertQuery, ExpertResult


class DiscoveryService:
    def __init__(
        self, fingerprint: IExpertiseFingerprint, graph: ICollaborationGraph
    ) -> None:
        self._fingerprint = fingerprint
        self._graph = graph

    def find_experts(self, query: ExpertQuery) -> ExpertResult:
        candidates = self._graph.candidate_collaborators(
            query.seed_researcher_id, limit=max(query.top_k * 5, query.top_k)
        )
        prior = set(self._graph.neighbors(query.seed_researcher_id, hops=1))
        scored = [
            Expert(
                researcher_id=cid,
                similarity=self._fingerprint.similarity(query.seed_researcher_id, cid),
                prior_collaborator=cid in prior,
            )
            for cid in candidates
            if cid != query.seed_researcher_id
        ]
        scored.sort(key=lambda e: e.similarity, reverse=True)
        return ExpertResult(experts=tuple(scored[: query.top_k]))
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/discovery/test_service.py -q`
  - Expected: `3 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/discovery/ tests/modules/discovery/`
  - `git commit -m "feat(mod-discovery): public-tier OpenAlex expert discovery (fingerprint + collaboration graph), zero confidentiality machinery"`

---

### Task 7: mod-funding-lite — ranked grant-opportunity match

Grant-opportunity match over Grants.gov/RePORTER/NSF public projections (§3.2, §3.5: opportunity-match lite).

**Files:**
- Create `tigerexchange/modules/funding_lite/__init__.py`
- Create `tigerexchange/modules/funding_lite/models.py`
- Create `tigerexchange/modules/funding_lite/service.py`
- Test `tigerexchange/tests/modules/funding_lite/__init__.py`, `tigerexchange/tests/modules/funding_lite/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/funding_lite/test_service.py
from contracts import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    PublishableProjection,
    Tier,
    TenantContext,
)
from modules.funding_lite.models import FundingQuery
from modules.funding_lite.service import FundingLiteService


def _tenant() -> TenantContext:
    ent = Entitlement(
        edition=Edition.PLG,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL}),
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.private,
    )
    return TenantContext(tenant_id="t", subject_id="s", entitlement=ent)


def _opp(pid: str, title: str, snippet: str) -> PublishableProjection:
    return PublishableProjection(
        projection_id=pid,
        artifact_id=f"grant-{pid}",
        owner_tenant_id="public",
        tier=Tier.public,
        discoverability_scope="public-web",
        fields={"title": title, "snippet": snippet, "source": "grants.gov"},
    )


class FakeRetrieval:
    def __init__(self, opps):
        self._opps = opps

    def retrieve(self, query, tenant, *, top_k=8):
        # naive lexical overlap score, highest first (engine is insulated)
        terms = set(query.lower().split())
        scored = sorted(
            self._opps,
            key=lambda p: len(terms & set(str(p.fields["snippet"]).lower().split())),
            reverse=True,
        )
        return scored[:top_k]


def test_returns_ranked_grant_matches():
    opps = [
        _opp("o1", "AI Institute", "machine learning artificial intelligence"),
        _opp("o2", "Plant Genomics", "plant gene sequencing"),
        _opp("o3", "ML Health", "machine learning health diagnostics"),
    ]
    svc = FundingLiteService(retrieval=FakeRetrieval(opps))
    result = svc.match(_tenant(), FundingQuery(query="machine learning", top_k=3))
    top = [m.opportunity.opportunity_id for m in result.matches]
    assert top[0] in {"o1", "o3"}  # ML opportunities rank above plant genomics
    assert top[-1] == "o2"
    assert all(m.opportunity.source for m in result.matches)


def test_top_k_truncates_and_scores_descending():
    opps = [_opp(f"o{i}", f"t{i}", f"grant funding {i}") for i in range(5)]
    svc = FundingLiteService(retrieval=FakeRetrieval(opps))
    result = svc.match(_tenant(), FundingQuery(query="grant funding", top_k=2))
    assert len(result.matches) == 2
    scores = [m.score for m in result.matches]
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/funding_lite/test_service.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.funding_lite.service'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/funding_lite/__init__.py
"""mod-funding-lite: ranked grant-opportunity match over Grants.gov/RePORTER/NSF
public grant feeds (plan §3.2, §3.5). Public-tier only; no confidentiality machinery."""

from modules.funding_lite.models import FundingMatch, FundingQuery, FundingResult, GrantOpportunity

__all__ = ["FundingMatch", "FundingQuery", "FundingResult", "GrantOpportunity"]
```

```python
# tigerexchange/modules/funding_lite/models.py
"""Frozen DTOs for mod-funding-lite. Public-tier grant opportunities only."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FundingQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    query: str
    top_k: int = Field(default=10, ge=1, le=100)


class GrantOpportunity(BaseModel):
    model_config = ConfigDict(frozen=True)
    opportunity_id: str
    title: str
    snippet: str
    source: str  # grants.gov | reporter | nsf


class FundingMatch(BaseModel):
    model_config = ConfigDict(frozen=True)
    opportunity: GrantOpportunity
    score: float


class FundingResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    matches: tuple[FundingMatch, ...]
```

```python
# tigerexchange/modules/funding_lite/service.py
"""Ranked grant-opportunity match (plan §3.2, §3.5).

Consumes ONLY the kernel IRetrievalStrategy over PUBLIC-tier grant projections
produced by the ingestion pipeline (Grants.gov/RePORTER/NSF). No KEK/PEP/classifier
machinery: grant feeds are commodity CC0/public."""

from __future__ import annotations

from contracts import Capability, IRetrievalStrategy, TenantContext
from modules.funding_lite.models import FundingMatch, FundingQuery, FundingResult, GrantOpportunity


class FundingLiteService:
    def __init__(self, retrieval: IRetrievalStrategy) -> None:
        self._retrieval = retrieval

    def match(self, tenant: TenantContext, query: FundingQuery) -> FundingResult:
        if not tenant.entitlement.has(Capability.PUBLIC_RETRIEVAL):
            raise PermissionError(f"tenant {tenant.tenant_id} lacks public-retrieval")
        projections = self._retrieval.retrieve(query.query, tenant, top_k=query.top_k)
        matches: list[FundingMatch] = []
        for rank, p in enumerate(projections):
            opp = GrantOpportunity(
                opportunity_id=p.projection_id,
                title=str(p.fields.get("title", "")),
                snippet=str(p.fields.get("snippet", "")),
                source=str(p.fields.get("source", "unknown")),
            )
            matches.append(FundingMatch(opportunity=opp, score=1.0 / (rank + 1)))
        return FundingResult(matches=tuple(matches))
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/funding_lite/test_service.py -q`
  - Expected: `2 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/funding_lite/ tests/modules/funding_lite/`
  - `git commit -m "feat(mod-funding-lite): ranked grant-opportunity match over public Grants.gov/RePORTER/NSF projections"`

---

### Task 8: Module import-boundary enforcement (no raw-store/classifier/projection-constructor imports)

Enforces the deliverable constraint: "modules consuming only kernel interfaces and the broker (no raw-store/classifier/projection imports)" (§4.2, §5.3).

**Files:**
- Modify `tigerexchange/pyproject.toml`
- Test `tigerexchange/tests/modules/test_module_import_boundaries.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/test_module_import_boundaries.py
"""The three feature modules may import ONLY the kernel (`contracts`) + each other's
own subpackage + stdlib/pydantic. They MUST NOT import raw stores, the classifier
impl, the PEP/broker impl, or construct PublishableProjection (§4.2, §5.3)."""

import ast
import pathlib

MODULES_ROOT = pathlib.Path(__file__).resolve().parents[2] / "modules"

# Substrings that, if imported by a feature module, violate the chokepoint contract.
FORBIDDEN_IMPORT_PREFIXES = (
    "qdrant_client",
    "opensearchpy",
    "psycopg",
    "sqlalchemy",
    "age",          # apache age driver
    "tigerexchange.stores",
    "stores",       # raw per-tenant store package
    "pep",          # PEP/broker impl package
    "broker",
    "classification_engine",  # the classifier impl (not the kernel result type)
)


def _imported_names(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_modules_do_not_import_forbidden_packages():
    offenders: list[str] = []
    for py in MODULES_ROOT.rglob("*.py"):
        for name in _imported_names(py):
            if name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                offenders.append(f"{py.relative_to(MODULES_ROOT)} imports {name}")
    assert not offenders, f"forbidden imports in feature modules: {offenders}"


def test_modules_do_not_construct_publishable_projection():
    offenders: list[str] = []
    for py in MODULES_ROOT.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name == "PublishableProjection":
                    offenders.append(str(py.relative_to(MODULES_ROOT)))
    assert not offenders, f"modules must not construct PublishableProjection: {offenders}"
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/test_module_import_boundaries.py -q`
  - Expected: `FileNotFoundError` for `tests/modules/__init__.py` is absent OR (after adding it) the test runs. First run fails because `tests/modules/__init__.py` does not yet exist — create it as part of Step 3. (If it already passes vacuously, the implementation step below adds the import-linter config so the boundary is also enforced in CI.)

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/tests/modules/__init__.py` (empty package marker):

```python
# tigerexchange/tests/modules/__init__.py
```

Add the import-linter contract to `tigerexchange/pyproject.toml` (append under the existing `[tool.importlinter]` block; if the root package is `tigerexchange`, adjust accordingly):

```toml
[[tool.importlinter.contracts]]
name = "feature-modules-consume-only-kernel-and-broker"
type = "forbidden"
source_modules = [
    "modules.lit_intelligence",
    "modules.discovery",
    "modules.funding_lite",
]
forbidden_modules = [
    "qdrant_client",
    "opensearchpy",
    "psycopg",
    "sqlalchemy",
    "stores",
    "pep",
    "broker",
    "classification_engine",
]
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/test_module_import_boundaries.py -q && lint-imports`
  - Expected: `2 passed` and `lint-imports` reports the new contract KEPT.

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add tests/modules/__init__.py tests/modules/test_module_import_boundaries.py pyproject.toml`
  - `git commit -m "test(modules): enforce modules consume only kernel + broker (no raw-store/classifier/projection imports)"`

---

### Task 9: Add generated-draft + draft-history store to the post-crypto-shred zero-decryptable-hits contract test

Directly folds in highs_addressed: "added to the post-crypto-shred zero-decryptable-hits contract test" (§11.3b, convergence-report line 27).

**Files:**
- Modify `tigerexchange/tests/contract/test_post_crypto_shred_zero_hits.py` (created by `0g-confidential-kek-stores`)

- [ ] **Step 1: Write the failing test** — append a new parametrized case covering the draft + history + synthesizer-buffer/RAG-cache stores to the existing suite.

```python
# tigerexchange/tests/contract/test_post_crypto_shred_zero_hits.py
# --- APPENDED: generated-draft + draft-history + synthesizer-buffer/RAG-cache ---
# (resolves convergence-report HIGH: the generated draft is the highest-value
#  confidential artifact and MUST be in the post-crypto-shred zero-hits contract.)

from contracts import Tier
from modules.lit_intelligence.draft_store import TenantKekDraftStore
from modules.lit_intelligence.models import Citation, ProposalDraft
from modules.lit_intelligence.synthesizer_buffer import KekScratchBuffer
from tests.modules.lit_intelligence.test_draft_store import FakeKek


def _confidential_draft() -> ProposalDraft:
    return ProposalDraft(
        draft_id="d-conf",
        section="Aims",
        body="confidential preliminary data and budget",
        citations=(Citation(source_id="s1", snippet="x", projection_id="p1"),),
        tier=Tier.confidential,
        faithfulness=0.9,
    )


def test_generated_draft_and_history_yield_zero_decryptable_hits_after_shred():
    kek = FakeKek()
    drafts = TenantKekDraftStore(kek=kek)
    scratch = KekScratchBuffer(kek=kek)

    drafts.save("tenant-conf", _confidential_draft())
    drafts.autosave("tenant-conf", "d-conf", "revised confidential aims")
    scratch.put_intermediate("tenant-conf", "d-conf", b"partial synthesis")
    scratch.put_rag_cache("tenant-conf", "d-conf", b"confidential grounding context")

    # sanity: decryptable before shred
    assert drafts.decryptable_hits("tenant-conf") > 0
    assert scratch.decryptable_hits("tenant-conf") > 0

    # crypto-shred the tenant KEK/DEK (§11.3 revocation/offboarding)
    kek.crypto_shred("tenant-conf")

    # CONTRACT: a search over draft + history + buffers + cache returns no decryptable hits
    assert drafts.decryptable_hits("tenant-conf") == 0
    assert scratch.decryptable_hits("tenant-conf") == 0
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/contract/test_post_crypto_shred_zero_hits.py -q -k "generated_draft"`
  - Expected: before appending, the function does not exist (`no tests ran` / `0 selected`); after appending it must run and PASS (the stores from Tasks 2-3 already enforce shred). If the draft store were NOT KEK-bound, this would FAIL with `decryptable_hits > 0`.

- [ ] **Step 3: Write minimal implementation**
  - No production code change required — Tasks 2 and 3 already make the draft, autosave, version-history, synthesizer buffers, and RAG cache tenant-KEK-bound. This task wires those stores into the canonical contract suite so the guarantee is regression-locked. If `tests/contract/__init__.py` is missing, create it:

```python
# tigerexchange/tests/contract/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/contract/test_post_crypto_shred_zero_hits.py -q`
  - Expected: all cases including `test_generated_draft_and_history_yield_zero_decryptable_hits_after_shred` show `PASSED`.

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add tests/contract/test_post_crypto_shred_zero_hits.py tests/contract/__init__.py`
  - `git commit -m "test(contract): add generated-draft + draft-history + synth-buffer/RAG-cache to post-crypto-shred zero-decryptable-hits suite"`

---

### Task 10: FastAPI routers for the three modules

**Files:**
- Create `tigerexchange/modules/lit_intelligence/router.py`
- Create `tigerexchange/modules/discovery/router.py`
- Create `tigerexchange/modules/funding_lite/router.py`
- Test `tigerexchange/tests/modules/test_routers.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/test_routers.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from contracts import (
    Capability,
    ClassificationResult,
    Decision,
    Edition,
    Entitlement,
    IsolationPosture,
    PublishableProjection,
    Tier,
    TenantContext,
)
from modules.discovery.router import build_discovery_router
from modules.discovery.service import DiscoveryService
from modules.funding_lite.router import build_funding_router
from modules.funding_lite.service import FundingLiteService
from modules.lit_intelligence.draft_store import TenantKekDraftStore
from modules.lit_intelligence.faithfulness import RagasFaithfulnessGate
from modules.lit_intelligence.router import build_lit_router
from modules.lit_intelligence.service import LitIntelligenceService
from modules.lit_intelligence.synthesizer_buffer import KekScratchBuffer
from tests.modules.discovery.test_service import FakeFingerprint, FakeGraph
from tests.modules.funding_lite.test_service import FakeRetrieval as FundingRetrieval, _opp
from tests.modules.lit_intelligence.test_draft_store import FakeKek
from tests.modules.lit_intelligence.test_service import (
    FakeClassifier,
    FakeRetrieval as LitRetrieval,
    FakeRouter,
    FakeProvider,
    StubScorer,
    _proj,
)


def _tenant() -> TenantContext:
    ent = Entitlement(
        edition=Edition.INSTITUTIONAL,
        capabilities=frozenset({Capability.OWN_MATERIALS, Capability.PUBLIC_RETRIEVAL}),
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.confidential,
    )
    return TenantContext(tenant_id="t", subject_id="s", entitlement=ent)


def _client() -> TestClient:
    app = FastAPI()
    tenant = _tenant()
    kek = FakeKek()
    lit = LitIntelligenceService(
        retrieval=LitRetrieval([_proj("p1", Tier.public)]),
        router=FakeRouter(FakeProvider()),
        classifier=FakeClassifier(),
        gate=RagasFaithfulnessGate(scorer=StubScorer(), threshold=0.80),
        draft_store=TenantKekDraftStore(kek=kek),
        scratch=KekScratchBuffer(kek=kek),
    )
    disc = DiscoveryService(fingerprint=FakeFingerprint(), graph=FakeGraph())
    fund = FundingLiteService(retrieval=FundingRetrieval([_opp("o1", "t", "machine learning")]))
    app.include_router(build_lit_router(lit, lambda: tenant))
    app.include_router(build_discovery_router(disc))
    app.include_router(build_funding_router(fund, lambda: tenant))
    return TestClient(app)


def test_lit_draft_endpoint_returns_cited_draft():
    r = _client().post("/v1/lit/draft", json={"section": "Aims", "prompt": "draft", "top_k": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["citations"]
    assert body["tier"] in ("public", "private", "confidential")


def test_discovery_endpoint_returns_public_experts():
    r = _client().post("/v1/discovery/experts", json={"seed_researcher_id": "seed", "top_k": 3})
    assert r.status_code == 200
    assert all(e["tier"] == "public" for e in r.json()["experts"])


def test_funding_endpoint_returns_matches():
    r = _client().post("/v1/funding/match", json={"query": "machine learning", "top_k": 1})
    assert r.status_code == 200
    assert r.json()["matches"]
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/test_routers.py -q`
  - Expected: `ModuleNotFoundError: No module named 'modules.lit_intelligence.router'`

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/modules/lit_intelligence/router.py
"""FastAPI router for mod-lit-intelligence. TenantContext is supplied by the app's
identity dependency (Keycloak/CILogon-backed); injected here for testability."""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends

from contracts import TenantContext
from modules.lit_intelligence.models import DraftRequest, ProposalDraft, SearchHit, SearchRequest
from modules.lit_intelligence.service import LitIntelligenceService


def build_lit_router(
    service: LitIntelligenceService, tenant_provider: Callable[[], TenantContext]
) -> APIRouter:
    router = APIRouter(prefix="/v1/lit", tags=["lit-intelligence"])

    @router.post("/search", response_model=list[SearchHit])
    def search(req: SearchRequest, tenant: TenantContext = Depends(tenant_provider)):
        return service.search(tenant, req)

    @router.post("/draft", response_model=ProposalDraft)
    def draft(req: DraftRequest, tenant: TenantContext = Depends(tenant_provider)):
        return service.draft(tenant, req)

    return router
```

```python
# tigerexchange/modules/discovery/router.py
"""FastAPI router for mod-discovery. Public-tier; no tenant credentials required."""

from __future__ import annotations

from fastapi import APIRouter

from modules.discovery.models import ExpertQuery, ExpertResult
from modules.discovery.service import DiscoveryService


def build_discovery_router(service: DiscoveryService) -> APIRouter:
    router = APIRouter(prefix="/v1/discovery", tags=["discovery"])

    @router.post("/experts", response_model=ExpertResult)
    def experts(query: ExpertQuery):
        return service.find_experts(query)

    return router
```

```python
# tigerexchange/modules/funding_lite/router.py
"""FastAPI router for mod-funding-lite."""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends

from contracts import TenantContext
from modules.funding_lite.models import FundingQuery, FundingResult
from modules.funding_lite.service import FundingLiteService


def build_funding_router(
    service: FundingLiteService, tenant_provider: Callable[[], TenantContext]
) -> APIRouter:
    router = APIRouter(prefix="/v1/funding", tags=["funding-lite"])

    @router.post("/match", response_model=FundingResult)
    def match(query: FundingQuery, tenant: TenantContext = Depends(tenant_provider)):
        return service.match(tenant, query)

    return router
```

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/test_routers.py -q`
  - Expected: `3 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add modules/*/router.py tests/modules/test_routers.py`
  - `git commit -m "feat(modules): FastAPI routers for lit/search, lit/draft, discovery/experts, funding/match"`

---

### Task 11: Mount module routers on the FastAPI app skeleton

**Files:**
- Modify `tigerexchange/app/main.py` (the app skeleton from the tenant-isolation foundation sub-plan)
- Test `tigerexchange/tests/modules/test_app_mount.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tests/modules/test_app_mount.py
from fastapi.testclient import TestClient

from app.main import app


def test_module_routes_are_mounted():
    client = TestClient(app)
    paths = {route.path for route in app.routes}
    assert "/v1/lit/draft" in paths
    assert "/v1/lit/search" in paths
    assert "/v1/discovery/experts" in paths
    assert "/v1/funding/match" in paths
```

- [ ] **Step 2: Run test to verify it fails**
  - Command: `cd tigerexchange && pytest tests/modules/test_app_mount.py -q`
  - Expected: `AssertionError: '/v1/lit/draft' not in paths` (routers not yet mounted).

- [ ] **Step 3: Write minimal implementation** — add a module-wiring block to `app/main.py`. This wires concrete dependency adapters built by the dependency sub-plans (0c broker, 0f router, 0g KEK, 0i retrieval). Use the dependency-injection factory that those sub-plans expose; the snippet below shows the exact mount calls and the identity dependency.

```python
# tigerexchange/app/main.py  (append after `app = FastAPI(...)`)

from app.dependencies import (  # provided by 0c/0f/0g/0i wiring
    get_classifier,
    get_collaboration_graph,
    get_draft_store,
    get_expertise_fingerprint,
    get_faithfulness_gate,
    get_funding_retrieval,
    get_lit_retrieval,
    get_model_router,
    get_scratch_buffer,
    get_tenant_context,
)
from modules.discovery.router import build_discovery_router
from modules.discovery.service import DiscoveryService
from modules.funding_lite.router import build_funding_router
from modules.funding_lite.service import FundingLiteService
from modules.lit_intelligence.router import build_lit_router
from modules.lit_intelligence.service import LitIntelligenceService

_lit_service = LitIntelligenceService(
    retrieval=get_lit_retrieval(),
    router=get_model_router(),
    classifier=get_classifier(),
    gate=get_faithfulness_gate(),
    draft_store=get_draft_store(),
    scratch=get_scratch_buffer(),
)
_discovery_service = DiscoveryService(
    fingerprint=get_expertise_fingerprint(),
    graph=get_collaboration_graph(),
)
_funding_service = FundingLiteService(retrieval=get_funding_retrieval())

app.include_router(build_lit_router(_lit_service, get_tenant_context))
app.include_router(build_discovery_router(_discovery_service))
app.include_router(build_funding_router(_funding_service, get_tenant_context))
```

If `app/dependencies.py` does not yet expose these factories, add thin factory functions there that return the concrete adapters built by 0c/0f/0g/0i (broker-backed `IRetrievalStrategy`, registry-backed `IModelRouter`, the single `IClassifier`, KEK-backed `TenantKekDraftStore`/`KekScratchBuffer`, OpenAlex `IExpertiseFingerprint`/`ICollaborationGraph`, and a `RagasFaithfulnessGate` with the local judge). Keep each factory a one-liner that constructs the already-built adapter; do not re-implement the adapters here.

- [ ] **Step 4: Run test to verify it passes**
  - Command: `cd tigerexchange && pytest tests/modules/test_app_mount.py -q`
  - Expected: `1 passed`

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add app/main.py app/dependencies.py tests/modules/test_app_mount.py`
  - `git commit -m "feat(app): mount mod-lit-intelligence, mod-discovery, mod-funding-lite routers on FastAPI app"`

---

### Task 12: Full module suite green + lint/type gates

**Files:** none (verification task)

- [ ] **Step 1: Write the failing test** — none; this is the aggregate verification gate. Run the whole module + contract suite.

- [ ] **Step 2: Run the suites**
  - Command: `cd tigerexchange && pytest tests/modules tests/contract/test_post_crypto_shred_zero_hits.py -q`
  - Expected: all module + contract tests `PASSED`, zero failures.

- [ ] **Step 3: Run lint, types, and import boundaries**
  - Command: `cd tigerexchange && ruff check modules/ && ruff format --check modules/ && mypy modules/ && lint-imports`
  - Expected: ruff clean, mypy `Success: no issues found`, import-linter all contracts `KEPT` (including `feature-modules-consume-only-kernel-and-broker`).

- [ ] **Step 4: Confirm deliverable assertions hold**
  - Verify by inspection of green tests: (a) `mod-lit-intelligence` drafts grounded, cited sections at p95<4s with draft+history KEK-bound (`test_service.py::test_draft_p95_under_4s_budget`, `test_draft_is_cited_and_persisted_kek_bound`); (b) draft+history is in the post-crypto-shred zero-decryptable-hits contract (`test_post_crypto_shred_zero_hits.py::test_generated_draft_and_history_yield_zero_decryptable_hits_after_shred`); (c) `mod-discovery` returns public-tier experts (`discovery/test_service.py`); (d) `mod-funding-lite` returns ranked matches (`funding_lite/test_service.py`); (e) modules import no raw-store/classifier/projection-constructor (`test_module_import_boundaries.py`).

- [ ] **Step 5: Commit**
  - `cd tigerexchange && git add -A`
  - `git commit -m "test(modules): green full feature-module + post-crypto-shred contract suite; ruff/mypy/import-linter clean"`

---

## Notes for the executing worker (load-bearing constraints, no new scope)

- **Kernel signatures are verbatim.** `tier_join_all`, `Tier`, `ClassificationResult`, `Decision`, `PublishableProjection`, `TenantContext`, `Entitlement`, `Capability`, `IRetrievalStrategy`, `IModelRouter`, `IClassifier`, `IExpertiseFingerprint`, `ICollaborationGraph` come from `contracts` exactly as defined in the canonical kernel. Do not redefine them.
- **D6 boundary:** `PublishableProjection.tier` can only be `public`/`private` (the kernel validator rejects `confidential`). Retrieved grounding projections therefore never carry `confidential`; the *draft's* confidential tier is derived by the MAX-rule join of source tiers with the prompt's classifier tier (§11.5) — that is why the draft store and synthesizer buffers must be tenant-KEK-bound even though no retrieved projection is itself confidential.
- **MAX-rule is the kernel join.** `tier_join_all([...])` with empty input fails closed to `confidential` (kernel contract); the service always includes at least the classifier's tier so the join is non-empty.
- **No raw store / classifier-impl / projection-constructor imports** in any `modules/**` file — enforced by Task 8's AST test *and* the import-linter contract. The `FakeKek`/`Fake*` doubles live in tests only.
- **Confidentiality machinery is asymmetric by design:** `mod-discovery` and `mod-funding-lite` carry *zero* KEK/PEP/classifier dependencies (public-tier by construction, §3.2/§6.3); only `mod-lit-intelligence` touches the KEK stores and classifier, because only it produces confidential-derivable artifacts.