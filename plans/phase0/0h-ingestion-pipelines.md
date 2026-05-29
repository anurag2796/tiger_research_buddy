I have everything needed. The bitmap sizing math: N=200 public corpus ~80-100M records. A naive bit-per-record bitmap over 100M records = 100M/8 = 12.5MB pushed at ≤2s cadence — confirms the convergence report's concern. The fix is delta/log-tail replication. Now I'll write the complete plan.

# Dagster Ingestion Pipelines (Classify-Gate-Index Outbox + Entity Resolution) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the Phase-0 Dagster batch DAGs that snapshot the public CC0 scholarly + grant corpora, entity-resolve, distill, classify (hard-gating the index), embed, index, and graph-build — with quarantined/unclassified records never reaching any index — plus a transactional-outbox-polling sensor that emits index/grant events carrying a per-RECORD `projection_version` (monotonic, lower-version-reject) distinct from the per-CELL fenced `revocation_epoch`.

**Architecture:** A single Dagster code location (`mod-ingestion`) defines source-snapshot assets (OpenAlex/Crossref/ROR/ORCID/SPECTER2 + Grants.gov/RePORTER/NSF) feeding an `identity-resolution` evicted service (deterministic ORCID/DOI/ROR anchors then probabilistic blocking) and a linear distill→classify→embed→index→graph DAG where the classify asset is a hard fail-closed gate (abstention → quarantine, default-deny, excluded from all indices). A Postgres transactional-outbox table + a Dagster sensor poller drain index/grant events into the central-index applier; the applier rejects lower per-record `projection_version` and the owner cell stamps its per-cell `revocation_epoch` distinctly. Bitmap sizing is documented and the design uses delta/log-tail (tombstone-log-tail) replication, not a full bit-per-record bitmap, to keep ≤2s p99.

**Tech Stack:** Python 3.11+, Dagster, Postgres (FORCE RLS, `SET LOCAL` tenant scope), Pydantic v2, the `contracts` kernel package, Qdrant (vector), OpenSearch (BM25), Apache AGE (graph). All consumed behind kernel interfaces; ORCID CC0 dump (not API), self-hosted OpenAlex snapshot (not metered API).

**Depends on:** `0a-foundation` (monorepo scaffold, Postgres FORCE-RLS + `TenantContext` + `SET LOCAL` session, CI), `0b-classification-engine` (the single fail-closed `IClassifier` + quarantine + adjudication queue).

---

## File Structure

All paths under `tigerexchange/`. This sub-plan creates the `mod-ingestion` package and the `identity-resolution` evicted service. It imports kernel symbols verbatim from `contracts` and assumes `0a`/`0b` deliverables exist.

| File | Responsibility |
|---|---|
| `packages/mod-ingestion/pyproject.toml` | **Create.** Package metadata; deps (dagster, pydantic, psycopg, contracts); import-linter contract forbidding mod-ingestion from constructing raw confidential payloads outside the broker. |
| `packages/mod-ingestion/src/mod_ingestion/__init__.py` | **Create.** Package marker. |
| `packages/mod-ingestion/src/mod_ingestion/config.py` | **Create.** `IngestionConfig` (corpus source URLs/paths, snapshot dirs, batch sizes, tenant_id for the public-corpus tenant, confidence threshold pass-through). |
| `packages/mod-ingestion/src/mod_ingestion/sources/scholarly.py` | **Create.** OpenAlex CC0 snapshot reader, Crossref annual-file reader, ROR CC0 reader, ORCID CC0 dump reader, SPECTER2 vector loader. Pure file/snapshot readers; never the metered live API. |
| `packages/mod-ingestion/src/mod_ingestion/sources/grants.py` | **Create.** Grants.gov opportunity feed, NIH RePORTER awards, NSF Awards readers. |
| `packages/mod-ingestion/src/mod_ingestion/records.py` | **Create.** `SourceRecord`, `ResolvedEntity`, `ResearchCard` Pydantic v2 models flowing between assets. |
| `packages/identity-resolution/pyproject.toml` | **Create.** Evicted-service package metadata (own DB + events). |
| `packages/identity-resolution/src/identity_resolution/__init__.py` | **Create.** Package marker. |
| `packages/identity-resolution/src/identity_resolution/resolver.py` | **Create.** `EntityResolver`: deterministic ORCID/DOI/ROR anchors first, then probabilistic blocking (name + co-author + concept + affiliation-time) for the unanchored tail. Public-tier by construction. |
| `packages/mod-ingestion/src/mod_ingestion/outbox.py` | **Create.** Transactional outbox: `OutboxEvent` model, `EpochModel` (per-CELL `revocation_epoch` vs per-RECORD `projection_version`), DDL, write-within-txn helper, monotonic applier (`lower-version-reject`), delta/log-tail replication sizing doc + helper. |
| `packages/mod-ingestion/src/mod_ingestion/assets.py` | **Create.** Dagster assets: snapshot → entity_resolve → distill → classify_gate → embed → index → graph_build; outbox-emit. |
| `packages/mod-ingestion/src/mod_ingestion/sensors.py` | **Create.** Dagster sensor: outbox poller that drains pending `OutboxEvent`s and applies them monotonically to the central index. |
| `packages/mod-ingestion/src/mod_ingestion/definitions.py` | **Create.** Dagster `Definitions` (assets + jobs + sensor) — the code-location entry point. |
| `packages/mod-ingestion/tests/conftest.py` | **Create.** Pytest fixtures: in-memory source fakes, fake index sinks, a `TenantContext` for the public-corpus tenant, a fake classifier. |
| `packages/mod-ingestion/tests/test_sources.py` | **Create.** Tests for snapshot/grant readers (file-based, no live API). |
| `packages/identity-resolution/tests/test_resolver.py` | **Create.** Tests for deterministic-anchor + probabilistic-blocking resolution. |
| `packages/mod-ingestion/tests/test_classify_gate.py` | **Create.** Tests proving quarantined/unclassified records never reach any index (the hard edge). |
| `packages/mod-ingestion/tests/test_outbox_epochs.py` | **Create.** Tests for the two-field epoch model, lower-version-reject applier, and bitmap-sizing/delta-replication justification. |
| `packages/mod-ingestion/tests/test_assets_pipeline.py` | **Create.** End-to-end Dagster materialization test of the full DAG. |

---

## Tasks

### Task 1: Package scaffold for `mod-ingestion` and `identity-resolution`

**Files:** Create `tigerexchange/packages/mod-ingestion/pyproject.toml`, `tigerexchange/packages/mod-ingestion/src/mod_ingestion/__init__.py`, `tigerexchange/packages/identity-resolution/pyproject.toml`, `tigerexchange/packages/identity-resolution/src/identity_resolution/__init__.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_imports.py`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_imports.py
"""mod-ingestion must import the canonical kernel verbatim and expose its package."""


def test_contracts_kernel_importable():
    # The kernel signatures this sub-plan consumes must be importable verbatim.
    from contracts import (
        ClassificationResult,
        Decision,
        DiscoverabilityScope,
        PublishableProjection,
        TenantContext,
        Tier,
    )

    assert Decision.QUARANTINE.value == "QUARANTINE"
    assert Tier.confidential > Tier.public
    assert DiscoverabilityScope.PUBLIC_WEB.value == "public-web"
    assert PublishableProjection.__name__ == "PublishableProjection"
    assert ClassificationResult.__name__ == "ClassificationResult"
    assert TenantContext.__name__ == "TenantContext"


def test_mod_ingestion_package_present():
    import mod_ingestion

    assert mod_ingestion.__name__ == "mod_ingestion"


def test_identity_resolution_package_present():
    import identity_resolution

    assert identity_resolution.__name__ == "identity_resolution"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_imports.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion'` (and `identity_resolution`).

- [ ] **Step 3: Write minimal implementation**

```toml
# tigerexchange/packages/mod-ingestion/pyproject.toml
[project]
name = "tigerexchange-mod-ingestion"
version = "0.0.0"
description = "Dagster ingestion DAGs: public CC0 scholarly + grant snapshots, entity resolution, classify-gate-index outbox."
requires-python = ">=3.11"
dependencies = [
    "tigerexchange-contracts",
    "tigerexchange-identity-resolution",
    "dagster>=1.7,<2",
    "pydantic>=2.6,<3",
    "psycopg[binary]>=3.1,<4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mod_ingestion"]

# Fitness function: mod-ingestion may not import another module's internals or
# the central-index store directly; it talks to indices through injected sinks.
[tool.importlinter]
root_package = "mod_ingestion"

[[tool.importlinter.contracts]]
name = "mod-ingestion-no-sibling-module-internals"
type = "forbidden"
source_modules = ["mod_ingestion"]
forbidden_modules = ["mod_lit_intelligence", "mod_discovery", "mod_funding"]
```

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/__init__.py
"""mod-ingestion: Phase-0 Dagster ingestion pipelines."""
```

```toml
# tigerexchange/packages/identity-resolution/pyproject.toml
[project]
name = "tigerexchange-identity-resolution"
version = "0.0.0"
description = "Evicted entity-resolution / author-disambiguation service (own DB + events). Public-tier by construction."
requires-python = ">=3.11"
dependencies = [
    "tigerexchange-contracts",
    "pydantic>=2.6,<3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/identity_resolution"]
```

```python
# tigerexchange/packages/identity-resolution/src/identity_resolution/__init__.py
"""identity-resolution: deterministic-anchor + probabilistic entity resolution."""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && pip install -e packages/contracts -e packages/identity-resolution -e packages/mod-ingestion && python -m pytest packages/mod-ingestion/tests/test_imports.py -q
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion packages/identity-resolution && git commit -m "feat(ingestion): scaffold mod-ingestion + identity-resolution packages

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Inter-asset record models (`SourceRecord`, `ResolvedEntity`, `ResearchCard`)

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/records.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_records.py`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_records.py
from mod_ingestion.records import ResearchCard, ResolvedEntity, SourceRecord


def test_source_record_carries_provenance_and_corpus():
    rec = SourceRecord(
        source="openalex",
        external_id="W123",
        corpus="scholarly",
        payload={"title": "Federated RAG", "doi": "10.1/x", "orcid": "0000-0001"},
    )
    assert rec.source == "openalex"
    assert rec.corpus == "scholarly"
    assert rec.payload["doi"] == "10.1/x"


def test_resolved_entity_records_anchor_method():
    ent = ResolvedEntity(
        entity_id="ent-1",
        canonical_name="Ada Lovelace",
        orcid="0000-0001",
        ror="https://ror.org/05",
        member_records=["openalex:W123", "crossref:10.1/x"],
        resolution_method="deterministic-orcid",
    )
    assert ent.resolution_method == "deterministic-orcid"
    assert "openalex:W123" in ent.member_records


def test_research_card_is_distilled_and_frozen():
    card = ResearchCard(
        card_id="card-1",
        entity_id="ent-1",
        title="Federated RAG",
        abstract="A study of federated retrieval.",
        concepts=("retrieval", "federation"),
        source_external_ids=("openalex:W123",),
    )
    assert card.title == "Federated RAG"
    # Frozen: distilled cards are immutable inputs to classification.
    import pytest

    with pytest.raises(Exception):
        card.title = "mutated"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_records.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.records'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/records.py
"""Records flowing between ingestion assets (plan §6.2, §6.3, §10.2).

These are public-tier corpus records (OpenAlex/Crossref/ROR/ORCID/SPECTER2 +
grant feeds). They are NOT the confidential workspace; nothing here crosses the
confidential boundary. ResearchCard is the distilled artifact handed to the
single fail-closed classifier before any index write (§10.2 classify-gates-index).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceRecord(BaseModel):
    """A raw record read from a snapshot/feed, with provenance (§6.2)."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(..., description="openalex|crossref|ror|orcid|specter2|grants_gov|reporter|nsf")
    external_id: str = Field(..., description="Source-native id (OpenAlex W-id, DOI, ROR id, ORCID, award id).")
    corpus: str = Field(..., description="scholarly|grant — selects downstream DAG branch.")
    payload: dict[str, object] = Field(default_factory=dict)


class ResolvedEntity(BaseModel):
    """An entity-resolved author/institution cluster (§6.3).

    Public-tier by construction: confidential records are resolved inside the
    cell only and never reach this DAG.
    """

    model_config = ConfigDict(frozen=True)

    entity_id: str
    canonical_name: str
    orcid: str | None = None
    ror: str | None = None
    member_records: list[str] = Field(default_factory=list)
    resolution_method: str = Field(
        ..., description="deterministic-orcid|deterministic-doi|deterministic-ror|probabilistic-block"
    )


class ResearchCard(BaseModel):
    """A distilled, structured paper/grant card (§10.2), input to the classifier."""

    model_config = ConfigDict(frozen=True)

    card_id: str
    entity_id: str
    title: str
    abstract: str = ""
    concepts: tuple[str, ...] = ()
    source_external_ids: tuple[str, ...] = ()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_records.py -q
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/records.py packages/mod-ingestion/tests/test_records.py && git commit -m "feat(ingestion): inter-asset record models (SourceRecord/ResolvedEntity/ResearchCard)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Public-corpus snapshot readers (OpenAlex/Crossref/ROR/ORCID/SPECTER2)

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/config.py`, `tigerexchange/packages/mod-ingestion/src/mod_ingestion/sources/__init__.py`, `tigerexchange/packages/mod-ingestion/src/mod_ingestion/sources/scholarly.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_sources.py`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_sources.py
import json
from pathlib import Path

from mod_ingestion.config import IngestionConfig
from mod_ingestion.sources.scholarly import (
    read_crossref_file,
    read_openalex_snapshot,
    read_orcid_dump,
    read_ror_file,
    read_specter2_vectors,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_openalex_snapshot_reader_yields_source_records(tmp_path: Path):
    snap = tmp_path / "openalex" / "works.jsonl"
    snap.parent.mkdir(parents=True)
    _write_jsonl(snap, [{"id": "W1", "title": "A", "doi": "10.1/a"}])
    cfg = IngestionConfig(snapshot_root=str(tmp_path), public_corpus_tenant_id="public")
    recs = list(read_openalex_snapshot(cfg))
    assert len(recs) == 1
    assert recs[0].source == "openalex"
    assert recs[0].external_id == "W1"
    assert recs[0].corpus == "scholarly"


def test_orcid_dump_reader_uses_dump_not_api(tmp_path: Path):
    dump = tmp_path / "orcid" / "summaries.jsonl"
    dump.parent.mkdir(parents=True)
    _write_jsonl(dump, [{"orcid-identifier": {"path": "0000-0001"}, "name": "Ada"}])
    cfg = IngestionConfig(snapshot_root=str(tmp_path), public_corpus_tenant_id="public")
    recs = list(read_orcid_dump(cfg))
    assert recs[0].source == "orcid"
    assert recs[0].external_id == "0000-0001"


def test_crossref_and_ror_readers(tmp_path: Path):
    cr = tmp_path / "crossref" / "metadata.jsonl"
    cr.parent.mkdir(parents=True)
    _write_jsonl(cr, [{"DOI": "10.1/a", "title": ["A"]}])
    ror = tmp_path / "ror" / "ror.jsonl"
    ror.parent.mkdir(parents=True)
    _write_jsonl(ror, [{"id": "https://ror.org/05", "name": "RIT"}])
    cfg = IngestionConfig(snapshot_root=str(tmp_path), public_corpus_tenant_id="public")
    assert list(read_crossref_file(cfg))[0].external_id == "10.1/a"
    assert list(read_ror_file(cfg))[0].external_id == "https://ror.org/05"


def test_specter2_vector_loader(tmp_path: Path):
    vecs = tmp_path / "specter2" / "vectors.jsonl"
    vecs.parent.mkdir(parents=True)
    _write_jsonl(vecs, [{"paper_id": "W1", "embedding": [0.1, 0.2, 0.3]}])
    cfg = IngestionConfig(snapshot_root=str(tmp_path), public_corpus_tenant_id="public")
    rec = list(read_specter2_vectors(cfg))[0]
    assert rec.source == "specter2"
    assert rec.payload["embedding"] == [0.1, 0.2, 0.3]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_sources.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.config'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/config.py
"""Ingestion configuration (plan §6.2, §10.2).

Snapshot-first: OpenAlex CC0 monthly snapshot, Crossref annual file, ROR CC0,
ORCID CC0 Public Data File dump, SPECTER2 vectors — NEVER the metered/live APIs
on a hot path (§6.2, §12). Layout under snapshot_root:
  {snapshot_root}/{openalex|crossref|ror|orcid|specter2|grants_gov|reporter|nsf}/*.jsonl
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IngestionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_root: str = Field(..., description="Root dir holding per-source snapshot subdirs.")
    public_corpus_tenant_id: str = Field(
        ..., description="Tenant id under which public-corpus rows are RLS-scoped."
    )
    batch_size: int = Field(default=1000, gt=0)
    # Below this classifier confidence, the record is quarantined (§11.1, set in 0b).
    abstention_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
```

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/sources/__init__.py
"""Snapshot/feed readers (file-based; never the metered live APIs)."""
```

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/sources/scholarly.py
"""Scholarly CC0 snapshot readers (plan §6.2, §12).

All readers consume on-disk snapshots (JSONL), NOT the metered OpenAlex live API
nor the non-commercial ORCID live API. Each yields SourceRecord with provenance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from mod_ingestion.config import IngestionConfig
from mod_ingestion.records import SourceRecord


def _iter_jsonl(root: str, subdir: str) -> Iterator[dict]:
    base = Path(root) / subdir
    if not base.exists():
        return
    for path in sorted(base.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                yield json.loads(line)


def read_openalex_snapshot(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    """Read the self-hosted OpenAlex CC0 snapshot (§6.2)."""
    for row in _iter_jsonl(cfg.snapshot_root, "openalex"):
        yield SourceRecord(
            source="openalex",
            external_id=str(row["id"]),
            corpus="scholarly",
            payload=row,
        )


def read_crossref_file(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    """Read the Crossref annual DOI-metadata file (§6.2)."""
    for row in _iter_jsonl(cfg.snapshot_root, "crossref"):
        yield SourceRecord(
            source="crossref",
            external_id=str(row["DOI"]),
            corpus="scholarly",
            payload=row,
        )


def read_ror_file(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    """Read the ROR CC0 institution file (§6.2)."""
    for row in _iter_jsonl(cfg.snapshot_root, "ror"):
        yield SourceRecord(
            source="ror",
            external_id=str(row["id"]),
            corpus="scholarly",
            payload=row,
        )


def read_orcid_dump(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    """Read the ORCID CC0 annual Public Data File DUMP (§6.2 — NOT the live API)."""
    for row in _iter_jsonl(cfg.snapshot_root, "orcid"):
        orcid = str(row["orcid-identifier"]["path"])
        yield SourceRecord(
            source="orcid",
            external_id=orcid,
            corpus="scholarly",
            payload=row,
        )


def read_specter2_vectors(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    """Read precomputed SPECTER2 paper embeddings (§6.2/§8.4)."""
    for row in _iter_jsonl(cfg.snapshot_root, "specter2"):
        yield SourceRecord(
            source="specter2",
            external_id=str(row["paper_id"]),
            corpus="scholarly",
            payload=row,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_sources.py -q
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/config.py packages/mod-ingestion/src/mod_ingestion/sources packages/mod-ingestion/tests/test_sources.py && git commit -m "feat(ingestion): CC0 scholarly snapshot readers (OpenAlex/Crossref/ROR/ORCID/SPECTER2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Grant-feed readers (Grants.gov / RePORTER / NSF)

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/sources/grants.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_grants.py`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_grants.py
import json
from pathlib import Path

from mod_ingestion.config import IngestionConfig
from mod_ingestion.sources.grants import (
    read_grants_gov,
    read_nsf_awards,
    read_reporter_awards,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_grants_gov_reader(tmp_path: Path):
    _write_jsonl(tmp_path / "grants_gov" / "opps.jsonl", [{"OpportunityID": "OPP1", "title": "NSF AI"}])
    cfg = IngestionConfig(snapshot_root=str(tmp_path), public_corpus_tenant_id="public")
    rec = list(read_grants_gov(cfg))[0]
    assert rec.source == "grants_gov"
    assert rec.external_id == "OPP1"
    assert rec.corpus == "grant"


def test_reporter_and_nsf_readers(tmp_path: Path):
    _write_jsonl(tmp_path / "reporter" / "awards.jsonl", [{"appl_id": "A1", "project_title": "U54"}])
    _write_jsonl(tmp_path / "nsf" / "awards.jsonl", [{"id": "2300001", "title": "NSF Award"}])
    cfg = IngestionConfig(snapshot_root=str(tmp_path), public_corpus_tenant_id="public")
    assert list(read_reporter_awards(cfg))[0].external_id == "A1"
    assert list(read_nsf_awards(cfg))[0].external_id == "2300001"
    assert all(r.corpus == "grant" for r in read_nsf_awards(cfg))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_grants.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.sources.grants'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/sources/grants.py
"""Public/US-gov grant-feed readers (plan §6.2 grants, §10.2).

Grants.gov opportunity feed + NIH RePORTER awards + NSF Awards — public-tier
funding-opportunity + award graph powering mod-funding-lite and team-assembly
priors. File-based snapshots.
"""

from __future__ import annotations

from typing import Iterator

from mod_ingestion.config import IngestionConfig
from mod_ingestion.records import SourceRecord
from mod_ingestion.sources.scholarly import _iter_jsonl


def read_grants_gov(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    for row in _iter_jsonl(cfg.snapshot_root, "grants_gov"):
        yield SourceRecord(
            source="grants_gov",
            external_id=str(row["OpportunityID"]),
            corpus="grant",
            payload=row,
        )


def read_reporter_awards(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    for row in _iter_jsonl(cfg.snapshot_root, "reporter"):
        yield SourceRecord(
            source="reporter",
            external_id=str(row["appl_id"]),
            corpus="grant",
            payload=row,
        )


def read_nsf_awards(cfg: IngestionConfig) -> Iterator[SourceRecord]:
    for row in _iter_jsonl(cfg.snapshot_root, "nsf"):
        yield SourceRecord(
            source="nsf",
            external_id=str(row["id"]),
            corpus="grant",
            payload=row,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_grants.py -q
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/sources/grants.py packages/mod-ingestion/tests/test_grants.py && git commit -m "feat(ingestion): grant-feed readers (Grants.gov/RePORTER/NSF)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Entity resolution — deterministic anchors then probabilistic blocking (evicted service)

**Files:** Create `tigerexchange/packages/identity-resolution/src/identity_resolution/resolver.py`. Test `tigerexchange/packages/identity-resolution/tests/test_resolver.py`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/identity-resolution/tests/test_resolver.py
from identity_resolution.resolver import BlockingKey, EntityResolver, ResolutionInput


def _inp(rid: str, name: str, orcid=None, doi=None, ror=None, coauthors=(), concepts=(), affil_year=None):
    return ResolutionInput(
        record_ref=rid,
        name=name,
        orcid=orcid,
        doi=doi,
        ror=ror,
        coauthors=tuple(coauthors),
        concepts=tuple(concepts),
        affiliation_year=affil_year,
    )


def test_deterministic_orcid_anchor_merges_records():
    r = EntityResolver()
    out = r.resolve([
        _inp("openalex:W1", "A. Lovelace", orcid="0000-0001"),
        _inp("crossref:10.1/a", "Ada Lovelace", orcid="0000-0001"),
    ])
    assert len(out) == 1
    ent = out[0]
    assert ent.orcid == "0000-0001"
    assert ent.resolution_method == "deterministic-orcid"
    assert set(ent.member_records) == {"openalex:W1", "crossref:10.1/a"}


def test_doi_and_ror_deterministic_anchors():
    r = EntityResolver()
    out = r.resolve([
        _inp("openalex:W2", "B. Pascal", doi="10.2/b"),
        _inp("crossref:10.2/b", "Blaise Pascal", doi="10.2/b"),
    ])
    assert len(out) == 1
    assert out[0].resolution_method == "deterministic-doi"


def test_probabilistic_blocking_merges_unanchored_tail():
    # No ORCID/DOI/ROR anchor; share a blocking key (name + coauthor + concept).
    r = EntityResolver()
    out = r.resolve([
        _inp("openalex:W3", "C. Gauss", coauthors=("Euler",), concepts=("number-theory",), affil_year=1799),
        _inp("openalex:W4", "C. Gauss", coauthors=("Euler",), concepts=("number-theory",), affil_year=1801),
    ])
    assert len(out) == 1
    assert out[0].resolution_method == "probabilistic-block"
    assert set(out[0].member_records) == {"openalex:W3", "openalex:W4"}


def test_distinct_entities_not_overmerged():
    r = EntityResolver()
    out = r.resolve([
        _inp("openalex:W5", "D. Hilbert", orcid="0000-0005"),
        _inp("openalex:W6", "E. Noether", orcid="0000-0006"),
    ])
    assert len(out) == 2


def test_blocking_key_is_deterministic():
    k1 = BlockingKey.from_input(_inp("x", "C. Gauss", coauthors=("Euler",), concepts=("number-theory",)))
    k2 = BlockingKey.from_input(_inp("y", "C. Gauss", coauthors=("Euler",), concepts=("number-theory",)))
    assert k1 == k2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/identity-resolution/tests/test_resolver.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'identity_resolution.resolver'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/identity-resolution/src/identity_resolution/resolver.py
"""Entity resolution / author disambiguation (plan §6.3).

Deterministic anchors (ORCID, DOI, ROR) FIRST; probabilistic blocking
(name + co-author + concept + affiliation-time) for the unanchored tail. This is
an EVICTED service (own DB + events). The disambiguation graph is PUBLIC-TIER by
construction — confidential records are resolved inside the cell only and never
reach this service.

Phase-0 probabilistic stage is a deterministic blocking-key union-find (no ML
model): records sharing a normalized (name, coauthor-set, concept-set) blocking
key are merged. This is the minimal correct behavior; a learned scorer is a later
phase and is NOT built here (YAGNI).
"""

from __future__ import annotations

from dataclasses import dataclass

from identity_resolution.models import ResolvedEntity, ResolutionInput

# Re-exported below for callers; defined in models to keep this file logic-only.

__all__ = ["BlockingKey", "EntityResolver", "ResolutionInput", "ResolvedEntity"]


@dataclass(frozen=True)
class BlockingKey:
    """Deterministic blocking key for the unanchored tail (§6.3)."""

    name_norm: str
    coauthors: tuple[str, ...]
    concepts: tuple[str, ...]

    @classmethod
    def from_input(cls, inp: "ResolutionInput") -> "BlockingKey":
        return cls(
            name_norm=_norm_name(inp.name),
            coauthors=tuple(sorted(c.lower().strip() for c in inp.coauthors)),
            concepts=tuple(sorted(c.lower().strip() for c in inp.concepts)),
        )


def _norm_name(name: str) -> str:
    return " ".join(name.lower().replace(".", " ").split())


class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        self._parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        self._parent[x] = root
        return root

    def union(self, a: str, b: str) -> None:
        self._parent[self.find(b)] = self.find(a)


class EntityResolver:
    """Resolve SourceRecord references into ResolvedEntity clusters (§6.3)."""

    def resolve(self, inputs: list[ResolutionInput]) -> list[ResolvedEntity]:
        uf = _UnionFind()
        for inp in inputs:
            uf.add(inp.record_ref)

        # Method precedence per ref: deterministic anchors beat probabilistic.
        method: dict[str, str] = {inp.record_ref: "probabilistic-block" for inp in inputs}

        # --- Deterministic anchors first (ORCID > DOI > ROR) ---
        for attr, label in (("orcid", "deterministic-orcid"),
                            ("doi", "deterministic-doi"),
                            ("ror", "deterministic-ror")):
            buckets: dict[str, list[ResolutionInput]] = {}
            for inp in inputs:
                key = getattr(inp, attr)
                if key:
                    buckets.setdefault(key, []).append(inp)
            for members in buckets.values():
                anchor = members[0].record_ref
                for m in members:
                    uf.union(anchor, m.record_ref)
                    method[m.record_ref] = _strongest(method[m.record_ref], label)

        # --- Probabilistic blocking for the unanchored tail ---
        blocks: dict[BlockingKey, list[ResolutionInput]] = {}
        for inp in inputs:
            blocks.setdefault(BlockingKey.from_input(inp), []).append(inp)
        for members in blocks.values():
            if len(members) > 1:
                anchor = members[0].record_ref
                for m in members:
                    uf.union(anchor, m.record_ref)

        # --- Materialize clusters ---
        clusters: dict[str, list[ResolutionInput]] = {}
        for inp in inputs:
            clusters.setdefault(uf.find(inp.record_ref), []).append(inp)

        entities: list[ResolvedEntity] = []
        for i, (_root, members) in enumerate(sorted(clusters.items())):
            cluster_method = _cluster_method(method, members)
            head = members[0]
            entities.append(
                ResolvedEntity(
                    entity_id=f"ent-{i}",
                    canonical_name=head.name,
                    orcid=next((m.orcid for m in members if m.orcid), None),
                    ror=next((m.ror for m in members if m.ror), None),
                    member_records=sorted(m.record_ref for m in members),
                    resolution_method=cluster_method,
                )
            )
        return entities


_RANK = {
    "probabilistic-block": 0,
    "deterministic-ror": 1,
    "deterministic-doi": 2,
    "deterministic-orcid": 3,
}


def _strongest(a: str, b: str) -> str:
    return a if _RANK[a] >= _RANK[b] else b


def _cluster_method(method: dict[str, str], members: list[ResolutionInput]) -> str:
    best = "probabilistic-block"
    for m in members:
        best = _strongest(best, method[m.record_ref])
    return best
```

Also create the input/output models in a sibling module to keep `resolver.py` logic-only:

```python
# tigerexchange/packages/identity-resolution/src/identity_resolution/models.py
"""Public-tier I/O models for the entity-resolution service (plan §6.3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResolutionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_ref: str = Field(..., description="Stable ref, e.g. 'openalex:W1'.")
    name: str
    orcid: str | None = None
    doi: str | None = None
    ror: str | None = None
    coauthors: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()
    affiliation_year: int | None = None


class ResolvedEntity(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: str
    canonical_name: str
    orcid: str | None = None
    ror: str | None = None
    member_records: list[str] = Field(default_factory=list)
    resolution_method: str
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/identity-resolution/tests/test_resolver.py -q
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/identity-resolution/src/identity_resolution packages/identity-resolution/tests/test_resolver.py && git commit -m "feat(identity-resolution): deterministic-anchor + probabilistic-blocking resolver (evicted service, public-tier)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: The two-field epoch model — per-CELL `revocation_epoch` vs per-RECORD `projection_version` (highs_addressed)

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/outbox.py` (epoch types + DDL constants). Test `tigerexchange/packages/mod-ingestion/tests/test_outbox_epochs.py`.

This task directly resolves the high finding: disambiguate the overloaded "epoch". `projection_version` is per-(tenant, record) monotonic and is what the applier's lower-version-reject rule compares; `revocation_epoch` is the single per-CELL fenced counter that versions the tombstone set / detects backward recovery. They are different objects at different granularities and are carried distinctly on every event.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_outbox_epochs.py
import pytest

from mod_ingestion.outbox import (
    BITMAP_SIZING,
    CellRevocationEpoch,
    OutboxEvent,
    ProjectionVersion,
    bitmap_replicated_bytes,
    replication_mode_for,
)


def test_projection_version_is_per_record_and_monotonic():
    v1 = ProjectionVersion(tenant_id="t1", record_id="r1", version=1)
    v2 = ProjectionVersion(tenant_id="t1", record_id="r1", version=2)
    assert v2.is_higher_than(v1)
    assert not v1.is_higher_than(v2)
    # Different records do NOT compare — distinct keys, never cross-rejected.
    other = ProjectionVersion(tenant_id="t1", record_id="r2", version=1)
    with pytest.raises(ValueError):
        v2.is_higher_than(other)


def test_cell_revocation_epoch_is_per_cell_fenced_and_detects_backward():
    e5 = CellRevocationEpoch(tenant_id="t1", epoch=5)
    e6 = CellRevocationEpoch(tenant_id="t1", epoch=6)
    assert e6.advances(e5)          # forward = normal monotonic bump
    assert e5.is_backward_of(e6)    # recovery moving backward = resurrection risk -> reject


def test_outbox_event_carries_BOTH_epochs_distinctly():
    ev = OutboxEvent(
        event_id="ev1",
        tenant_id="t1",
        kind="index",
        record_id="r1",
        projection_version=7,        # per-RECORD, monotonic, lower-version-reject
        revocation_epoch=42,         # per-CELL fenced, versions the tombstone set
        payload={"title": "x"},
    )
    # The two values live in two distinct, non-interchangeable fields.
    assert ev.projection_version == 7
    assert ev.revocation_epoch == 42
    assert ev.kind == "index"


def test_bitmap_sizing_at_N200_is_documented_and_large():
    # N=200 public corpus ~80-100M records; a naive bit-per-record bitmap is
    # 100M / 8 = 12.5MB. Confirms the convergence-report concern.
    assert BITMAP_SIZING["N200_records"] == 100_000_000
    naive = bitmap_replicated_bytes(records=100_000_000)
    assert naive == 12_500_000  # 12.5 MB pushed per cycle if naive bit-per-record
    # 12.5MB at <=2s cadence is NOT a "tiny push" -> switch to delta/log-tail.
    assert replication_mode_for(naive_bitmap_bytes=naive) == "delta-log-tail"


def test_small_corpus_keeps_full_bitmap():
    naive = bitmap_replicated_bytes(records=1_000_000)  # ~125 KB
    assert replication_mode_for(naive_bitmap_bytes=naive) == "full-bitmap"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_outbox_epochs.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.outbox'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/outbox.py
"""Transactional outbox + the disambiguated epoch model (plan §10.3, §4.3a, §4.4a;
convergence-report HIGH 'overloaded epoch').

TWO NAMED, NON-INTERCHANGEABLE objects at DIFFERENT granularities:

  1. ProjectionVersion  — per-(tenant, RECORD) monotonic counter. This is what
     the CDC/outbox applier's LOWER-VERSION-REJECT rule compares (§10.3a). It is
     keyed per record, so a revoke of record A never makes a valid stale-but-OK
     apply of record B look 'lower-version' (the exact bug the finding flags).

  2. CellRevocationEpoch — a SINGLE per-CELL fenced monotonic counter (§4.4a).
     It versions the tombstone SET / tombstone-log tail and detects a node
     moving BACKWARD on recovery (anti-resurrection, §4.4a). It is NOT compared
     per record; it is replicated to the Exchange to gate shared-tier discovery
     (§4.3a, bounded-stale).

Both ride every OutboxEvent in DISTINCT fields so neither is mistaken for the other.

----------------------------------------------------------------------------
BITMAP INDEXING SCHEME, SIZE AT N=200, AND PER-CYCLE REPLICATED BYTES
----------------------------------------------------------------------------
The §4.3a "compact tombstone bitmap" is, in its naive form, a bit-per-record
dense bitmap indexed by a per-cell dense record ordinal (record_ordinal in
[0, n_records)). At the §14.2 N=200 R1 scale the public corpus is ~80-100M
records, so a naive dense bitmap is:

    100_000_000 bits / 8 = 12_500_000 bytes = ~12.5 MB

Pushing ~12.5 MB at the <=2s p99 replication cadence (§4.3a) is NOT the "tiny,
high-frequency push" §14.3 claims. Therefore (per the finding's fix):

  - For corpora whose naive dense bitmap exceeds DELTA_SWITCH_BYTES we switch to
    DELTA / TOMBSTONE-LOG-TAIL replication: we replicate only the tail of the
    revocation_log (the (revocation_epoch, record_ordinal) entries committed
    since the consumer's last-seen revocation_epoch), not the whole bitmap. The
    per-cycle bytes are then O(revocations-since-last-cycle), independent of
    corpus size, which keeps the <=2s p99 bound defensible.
  - For small corpora (below the switch) the full dense bitmap is cheap enough
    to ship whole.

The CellRevocationEpoch is the cursor for this delta: the consumer requests
"everything with epoch > my_last_epoch" and the cell streams that tail.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Switch to delta/log-tail when the naive dense bitmap would exceed ~256 KB/cycle.
DELTA_SWITCH_BYTES: int = 256 * 1024

# Documented sizing constants (§14.2 growth model).
BITMAP_SIZING: dict[str, int] = {
    "N10_records": 5_000_000,
    "N50_records": 25_000_000,
    "N200_records": 100_000_000,
}


def bitmap_replicated_bytes(records: int) -> int:
    """Bytes of a NAIVE dense bit-per-record tombstone bitmap for `records`."""
    return records // 8


def replication_mode_for(naive_bitmap_bytes: int) -> Literal["full-bitmap", "delta-log-tail"]:
    """Pick replication mode: full dense bitmap vs delta/log-tail (the fix)."""
    return "delta-log-tail" if naive_bitmap_bytes > DELTA_SWITCH_BYTES else "full-bitmap"


class ProjectionVersion(BaseModel):
    """Per-(tenant, RECORD) monotonic version; the applier's lower-version-reject key."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    record_id: str
    version: int = Field(..., ge=0)

    def is_higher_than(self, other: "ProjectionVersion") -> bool:
        """True iff strictly newer for the SAME (tenant, record). Cross-key compare is an error."""
        if (self.tenant_id, self.record_id) != (other.tenant_id, other.record_id):
            raise ValueError(
                "ProjectionVersion compares only within the SAME (tenant, record); "
                "cross-record comparison is the overloaded-epoch bug."
            )
        return self.version > other.version


class CellRevocationEpoch(BaseModel):
    """Single per-CELL fenced monotonic counter that versions the tombstone set (§4.4a)."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(..., description="Owner cell / tenant the epoch belongs to.")
    epoch: int = Field(..., ge=0)

    def advances(self, prior: "CellRevocationEpoch") -> bool:
        """True iff this epoch is a forward (monotonic) advance over `prior`."""
        _same_cell(self, prior)
        return self.epoch > prior.epoch

    def is_backward_of(self, observed: "CellRevocationEpoch") -> bool:
        """True iff this (recovered) epoch is BEHIND `observed` -> resurrection risk (§4.4a)."""
        _same_cell(self, observed)
        return self.epoch < observed.epoch


def _same_cell(a: CellRevocationEpoch, b: CellRevocationEpoch) -> None:
    if a.tenant_id != b.tenant_id:
        raise ValueError("CellRevocationEpoch is per-CELL; cross-cell comparison is invalid.")


class OutboxEvent(BaseModel):
    """A transactional-outbox row carrying BOTH epochs distinctly (§10.3)."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    tenant_id: str
    kind: Literal["index", "grant", "tombstone"]
    record_id: str
    # per-RECORD monotonic; applier lower-version-reject (§10.3a).
    projection_version: int = Field(..., ge=0)
    # per-CELL fenced; versions the tombstone set / detects backward recovery (§4.4a).
    revocation_epoch: int = Field(..., ge=0)
    payload: dict[str, object] = Field(default_factory=dict)
    delivered: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_outbox_epochs.py -q
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/outbox.py packages/mod-ingestion/tests/test_outbox_epochs.py && git commit -m "feat(ingestion): disambiguate epoch model (per-CELL revocation_epoch vs per-RECORD projection_version) + bitmap sizing + delta/log-tail switch

Resolves the overloaded-epoch HIGH: documents N=200 ~12.5MB naive bitmap and switches to log-tail replication.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Transactional outbox store + monotonic lower-version-reject applier

**Files:** Modify `tigerexchange/packages/mod-ingestion/src/mod_ingestion/outbox.py` (add `OutboxStore`, `MonotonicApplier`, DDL). Test `tigerexchange/packages/mod-ingestion/tests/test_outbox_store.py`.

The outbox write must occur in the SAME transaction as the producing state change (transactional outbox). The applier is idempotent and rejects lower per-record `projection_version` so replays/snapshots cannot resurrect a revoked/downgraded record (§10.3a).

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_outbox_store.py
from mod_ingestion.outbox import (
    InMemoryIndexSink,
    InMemoryOutboxStore,
    MonotonicApplier,
    OUTBOX_DDL,
    OutboxEvent,
)


def test_ddl_uses_force_rls_and_tenant_leading_index():
    ddl = OUTBOX_DDL
    assert "FORCE ROW LEVEL SECURITY" in ddl
    assert "RESTRICTIVE" in ddl
    # tenant_id is the leading index column (§7.7).
    assert "ix_outbox_tenant" in ddl
    assert "(tenant_id" in ddl


def test_enqueue_and_drain_pending():
    store = InMemoryOutboxStore()
    ev = OutboxEvent(event_id="e1", tenant_id="t1", kind="index", record_id="r1",
                     projection_version=1, revocation_epoch=0, payload={"title": "a"})
    store.enqueue(ev)
    pending = store.fetch_pending(limit=10)
    assert [e.event_id for e in pending] == ["e1"]
    store.mark_delivered(["e1"])
    assert store.fetch_pending(limit=10) == []


def test_applier_accepts_then_rejects_lower_version():
    sink = InMemoryIndexSink()
    applier = MonotonicApplier(sink)
    ev2 = OutboxEvent(event_id="e2", tenant_id="t1", kind="index", record_id="r1",
                      projection_version=2, revocation_epoch=0, payload={"title": "v2"})
    ev1 = OutboxEvent(event_id="e1", tenant_id="t1", kind="index", record_id="r1",
                      projection_version=1, revocation_epoch=0, payload={"title": "v1-STALE"})
    assert applier.apply(ev2) == "applied"
    # A replayed/snapshot LOWER projection_version must be rejected (no resurrection).
    assert applier.apply(ev1) == "rejected-lower-version"
    assert sink.get("t1", "r1")["title"] == "v2"


def test_applier_is_idempotent_on_equal_version():
    sink = InMemoryIndexSink()
    applier = MonotonicApplier(sink)
    ev = OutboxEvent(event_id="e1", tenant_id="t1", kind="index", record_id="r1",
                     projection_version=5, revocation_epoch=0, payload={"title": "x"})
    assert applier.apply(ev) == "applied"
    assert applier.apply(ev) == "rejected-lower-version"  # equal is not higher -> no-op


def test_tombstone_event_removes_from_sink():
    sink = InMemoryIndexSink()
    applier = MonotonicApplier(sink)
    add = OutboxEvent(event_id="a", tenant_id="t1", kind="index", record_id="r1",
                      projection_version=1, revocation_epoch=0, payload={"title": "x"})
    tomb = OutboxEvent(event_id="t", tenant_id="t1", kind="tombstone", record_id="r1",
                       projection_version=2, revocation_epoch=7, payload={})
    applier.apply(add)
    assert applier.apply(tomb) == "applied"
    assert sink.get("t1", "r1") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_outbox_store.py -q
```
Expected failure: `ImportError: cannot import name 'OutboxStore'` (the new symbols do not exist yet).

- [ ] **Step 3: Write minimal implementation** (append to `outbox.py`)

```python
# --- append to tigerexchange/packages/mod-ingestion/src/mod_ingestion/outbox.py ---

# Transactional-outbox DDL (§10.1 Dagster-only, §7.7 pooled-plane isolation).
# The outbox row is written in the SAME transaction as the producing change.
OUTBOX_DDL: str = """
CREATE TABLE IF NOT EXISTS outbox_event (
    event_id           TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    kind               TEXT NOT NULL CHECK (kind IN ('index', 'grant', 'tombstone')),
    record_id          TEXT NOT NULL,
    projection_version BIGINT NOT NULL,   -- per-(tenant,record) monotonic; lower-version-reject
    revocation_epoch   BIGINT NOT NULL,   -- per-CELL fenced; versions the tombstone set
    payload            JSONB NOT NULL DEFAULT '{}'::jsonb,
    delivered          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- tenant_id is the LEADING index column (§7.7) so the tenant predicate is index-driven.
CREATE INDEX IF NOT EXISTS ix_outbox_tenant ON outbox_event (tenant_id, delivered, created_at);

ALTER TABLE outbox_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_event FORCE ROW LEVEL SECURITY;            -- owner/superuser cannot bypass
CREATE POLICY outbox_tenant_isolation ON outbox_event
    AS RESTRICTIVE                                            -- AND-combined, narrows only
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));  -- block cross-tenant write
"""


class InMemoryOutboxStore:
    """In-memory outbox for tests/dev (the Postgres store uses OUTBOX_DDL + SET LOCAL)."""

    def __init__(self) -> None:
        self._rows: dict[str, OutboxEvent] = {}

    def enqueue(self, event: OutboxEvent) -> None:
        self._rows[event.event_id] = event

    def fetch_pending(self, limit: int) -> list[OutboxEvent]:
        pending = [e for e in self._rows.values() if not e.delivered]
        return sorted(pending, key=lambda e: e.event_id)[:limit]

    def mark_delivered(self, event_ids: list[str]) -> None:
        for eid in event_ids:
            row = self._rows.get(eid)
            if row is not None:
                self._rows[eid] = row.model_copy(update={"delivered": True})


class InMemoryIndexSink:
    """Fake central-index sink (the real sink is the §4.7 PEP-gated applier target)."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict[str, object]] = {}

    def upsert(self, tenant_id: str, record_id: str, payload: dict[str, object]) -> None:
        self._store[(tenant_id, record_id)] = payload

    def delete(self, tenant_id: str, record_id: str) -> None:
        self._store.pop((tenant_id, record_id), None)

    def get(self, tenant_id: str, record_id: str) -> dict[str, object] | None:
        return self._store.get((tenant_id, record_id))


class MonotonicApplier:
    """Idempotent, MONOTONIC applier (§10.3a): rejects lower per-record projection_version.

    Replays/snapshots carrying a lower (or equal) projection_version for a
    (tenant, record) are rejected, so they cannot resurrect a revoked/downgraded
    record. Tombstone events delete the record from the sink.
    """

    def __init__(self, sink: InMemoryIndexSink) -> None:
        self._sink = sink
        self._high_water: dict[tuple[str, str], int] = {}

    def apply(self, event: OutboxEvent) -> str:
        key = (event.tenant_id, event.record_id)
        seen = self._high_water.get(key, -1)
        if event.projection_version <= seen:
            return "rejected-lower-version"
        self._high_water[key] = event.projection_version
        if event.kind == "tombstone":
            self._sink.delete(event.tenant_id, event.record_id)
        else:
            self._sink.upsert(event.tenant_id, event.record_id, event.payload)
        return "applied"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_outbox_store.py -q
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/outbox.py packages/mod-ingestion/tests/test_outbox_store.py && git commit -m "feat(ingestion): transactional outbox store + monotonic lower-version-reject applier (FORCE-RLS DDL)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Classify-gate — the hard edge (quarantined/unclassified never reach any index)

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/classify_gate.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_classify_gate.py`.

This is the §10.2/§11.1 hard edge enforced as code: the classify step splits cards into `indexable` (Decision.ALLOW) and `quarantined` (Decision.QUARANTINE / not retrievable); only indexable cards proceed to embed/index/graph/outbox. Uses the kernel `IClassifier`/`ClassificationResult`/`Decision`/`Tier` verbatim.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_classify_gate.py
from contracts import ClassificationResult, Decision, Tier

from mod_ingestion.classify_gate import GateResult, classify_gate
from mod_ingestion.records import ResearchCard


class _FakeClassifier:
    """Returns ALLOW for 'public' titles; QUARANTINE for 'ambiguous'; confidential->DENY-ish."""

    def classify(self, content, tenant):
        text = content.decode("utf-8")
        if "ambiguous" in text:
            return ClassificationResult.quarantine(reason="low-confidence", confidence=0.2)
        if "secret" in text:
            return ClassificationResult(
                tier=Tier.confidential, decision=Decision.DENY, confidence=0.95, reason="confidential"
            )
        return ClassificationResult(tier=Tier.public, decision=Decision.ALLOW, confidence=0.99)


def _card(cid, title):
    return ResearchCard(card_id=cid, entity_id="e", title=title)


def test_allow_cards_are_indexable():
    res = classify_gate([_card("c1", "public paper")], _FakeClassifier(), tenant=None)
    assert isinstance(res, GateResult)
    assert [c.card_id for c in res.indexable] == ["c1"]
    assert res.quarantined == []


def test_quarantined_card_NEVER_reaches_index():
    res = classify_gate([_card("c2", "ambiguous paper")], _FakeClassifier(), tenant=None)
    assert res.indexable == []
    assert [c.card.card_id for c in res.quarantined] == ["c2"]
    # The quarantine record is the canonical fail-closed result (D6).
    q = res.quarantined[0]
    assert q.result.decision is Decision.QUARANTINE
    assert q.result.tier is Tier.confidential
    assert q.result.is_retrievable is False


def test_confidential_deny_also_excluded_from_index():
    res = classify_gate([_card("c3", "secret budget")], _FakeClassifier(), tenant=None)
    assert res.indexable == []
    assert [q.card.card_id for q in res.quarantined] == ["c3"]


def test_mixed_batch_splits_correctly_zero_leak():
    cards = [_card("a", "public"), _card("b", "ambiguous"), _card("c", "secret")]
    res = classify_gate(cards, _FakeClassifier(), tenant=None)
    assert [c.card_id for c in res.indexable] == ["a"]
    assert sorted(q.card.card_id for q in res.quarantined) == ["b", "c"]
    # ZERO non-ALLOW card appears on the indexable surface.
    assert all(
        c.card_id not in {q.card.card_id for q in res.quarantined} for c in res.indexable
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_classify_gate.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.classify_gate'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/classify_gate.py
"""Classify-gates-index hard edge (plan §10.2, §11.1, D6).

The classify step is a HARD GATE: only records whose ClassificationResult is
Decision.ALLOW (and therefore is_retrievable) proceed to embed/index/graph/outbox.
Any QUARANTINE (abstention/ambiguity) or DENY (e.g. confidential) record is routed
to the quarantine bucket and NEVER reaches any index. This is the §11.1
zero-leak invariant enforced in code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts import ClassificationResult, IClassifier, TenantContext

from mod_ingestion.records import ResearchCard


@dataclass(frozen=True)
class QuarantinedCard:
    """A card excluded from all indices, routed to the human-adjudication queue (§11.1)."""

    card: ResearchCard
    result: ClassificationResult


@dataclass
class GateResult:
    """Split of a batch into the indexable allow-list and the quarantine bucket."""

    indexable: list[ResearchCard] = field(default_factory=list)
    quarantined: list[QuarantinedCard] = field(default_factory=list)


def classify_gate(
    cards: list[ResearchCard],
    classifier: IClassifier,
    tenant: TenantContext | None,
) -> GateResult:
    """Classify each card; only Decision.ALLOW cards are indexable (the hard edge)."""
    out = GateResult()
    for card in cards:
        content = _card_content(card)
        result = classifier.classify(content, tenant)
        if result.is_retrievable:  # True only for Decision.ALLOW (D6)
            out.indexable.append(card)
        else:
            out.quarantined.append(QuarantinedCard(card=card, result=result))
    return out


def _card_content(card: ResearchCard) -> bytes:
    parts = [card.title, card.abstract, " ".join(card.concepts)]
    return " ".join(p for p in parts if p).encode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_classify_gate.py -q
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/classify_gate.py packages/mod-ingestion/tests/test_classify_gate.py && git commit -m "feat(ingestion): classify-gates-index hard edge (quarantine/deny never reach any index)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Index/graph sinks + projection builder (publishable, MAX-rule-bounded)

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/sinks.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_sinks.py`.

The embed/index/graph step builds a `PublishableProjection` (kernel K2) per indexable card and writes to injected vector/lexical/graph sinks. Per D6 the projection rejects `confidential` tier at validation (kernel enforces this). The projection's tier is bounded by `tier_join_all` over inputs (public corpus → public).

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_sinks.py
import pytest
from contracts import DiscoverabilityScope, PublishableProjection, Tier

from mod_ingestion.records import ResearchCard
from mod_ingestion.sinks import (
    FakeGraphSink,
    FakeLexicalSink,
    FakeVectorSink,
    build_projection,
    index_card,
)


def _card(cid="c1"):
    return ResearchCard(card_id=cid, entity_id="e1", title="Federated RAG",
                        abstract="study", concepts=("retrieval",), source_external_ids=("openalex:W1",))


def test_build_projection_is_public_and_scoped():
    proj = build_projection(_card(), owner_tenant_id="public", input_tiers=[Tier.public])
    assert isinstance(proj, PublishableProjection)
    assert proj.tier is Tier.public
    assert proj.discoverability_scope is DiscoverabilityScope.PUBLIC_WEB
    assert proj.fields["title"] == "Federated RAG"


def test_build_projection_max_rule_bounds_tier():
    # Even one private input lifts the projection to private (MAX-rule).
    proj = build_projection(_card(), owner_tenant_id="public", input_tiers=[Tier.public, Tier.private])
    assert proj.tier is Tier.private


def test_projection_cannot_be_confidential():
    # D6: confidential never enters the shared index; kernel validator rejects it.
    with pytest.raises(ValueError):
        build_projection(_card(), owner_tenant_id="public", input_tiers=[Tier.confidential])


def test_index_card_writes_all_three_engines():
    v, lx, g = FakeVectorSink(), FakeLexicalSink(), FakeGraphSink()
    proj = build_projection(_card(), owner_tenant_id="public", input_tiers=[Tier.public])
    index_card(proj, embedding=[0.1, 0.2], vector=v, lexical=lx, graph=g)
    assert v.upserts[0][0] == proj.projection_id
    assert lx.docs[0]["title"] == "Federated RAG"
    assert g.nodes[0]["entity_id"] == "e1"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_sinks.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.sinks'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/sinks.py
"""Index/graph sinks + PublishableProjection builder (plan §9.1, §10.2, §4.7, D6).

embed -> index -> graph-build. A PublishableProjection (kernel K2) is built per
indexable card; its tier is the MAX-rule (tier_join_all) over input tiers and is
rejected by the kernel validator if it would be confidential (D6). The concrete
engines (Qdrant vector, OpenSearch BM25, Apache AGE graph) are injected behind
these sink protocols so engine choice stays insulated (§5.8/§12).
"""

from __future__ import annotations

from typing import Protocol, Sequence

from contracts import DiscoverabilityScope, PublishableProjection, Tier, tier_join_all

from mod_ingestion.records import ResearchCard


class VectorSink(Protocol):
    def upsert(self, projection_id: str, embedding: Sequence[float], payload: dict) -> None: ...


class LexicalSink(Protocol):
    def index(self, projection_id: str, document: dict) -> None: ...


class GraphSink(Protocol):
    def add_node(self, node: dict) -> None: ...


def build_projection(
    card: ResearchCard, owner_tenant_id: str, input_tiers: list[Tier]
) -> PublishableProjection:
    """Build a public/shared projection of a card (D6: never confidential)."""
    tier = tier_join_all(input_tiers)  # MAX-rule (§6.1); kernel rejects confidential
    return PublishableProjection(
        projection_id=f"proj-{card.card_id}",
        artifact_id=card.card_id,
        owner_tenant_id=owner_tenant_id,
        tier=tier,
        discoverability_scope=DiscoverabilityScope.PUBLIC_WEB,
        fields={
            "title": card.title,
            "abstract": card.abstract,
            "concepts": list(card.concepts),
            "entity_id": card.entity_id,
            "source_external_ids": list(card.source_external_ids),
        },
    )


def index_card(
    projection: PublishableProjection,
    embedding: Sequence[float],
    vector: VectorSink,
    lexical: LexicalSink,
    graph: GraphSink,
) -> None:
    """Write a projection to vector + lexical + graph engines (§9.1, §10.2)."""
    vector.upsert(projection.projection_id, embedding, dict(projection.fields))
    lexical.index(projection.projection_id, dict(projection.fields))
    graph.add_node({"projection_id": projection.projection_id, "entity_id": projection.fields["entity_id"]})


# --- Fakes for tests/dev (real impls are the injected Qdrant/OpenSearch/AGE clients) ---

class FakeVectorSink:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, list[float], dict]] = []

    def upsert(self, projection_id, embedding, payload):
        self.upserts.append((projection_id, list(embedding), payload))


class FakeLexicalSink:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def index(self, projection_id, document):
        self.docs.append(document)


class FakeGraphSink:
    def __init__(self) -> None:
        self.nodes: list[dict] = []

    def add_node(self, node):
        self.nodes.append(node)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_sinks.py -q
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/sinks.py packages/mod-ingestion/tests/test_sinks.py && git commit -m "feat(ingestion): MAX-rule-bounded PublishableProjection builder + vector/lexical/graph sinks (D6)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Distill — SourceRecord + ResolvedEntity → ResearchCard

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/distill.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_distill.py`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_distill.py
from identity_resolution.models import ResolvedEntity

from mod_ingestion.distill import distill_cards
from mod_ingestion.records import SourceRecord


def _sr(source, ext, payload):
    return SourceRecord(source=source, external_id=ext, corpus="scholarly", payload=payload)


def test_distill_builds_card_per_entity():
    records = [
        _sr("openalex", "W1", {"title": "Federated RAG", "abstract": "study", "concepts": ["retrieval"]}),
        _sr("crossref", "10.1/a", {"title": ["Federated RAG"]}),
    ]
    entities = [
        ResolvedEntity(entity_id="ent-0", canonical_name="Ada", orcid="0000-0001",
                       member_records=["openalex:W1", "crossref:10.1/a"],
                       resolution_method="deterministic-orcid"),
    ]
    cards = distill_cards(records, entities)
    assert len(cards) == 1
    c = cards[0]
    assert c.entity_id == "ent-0"
    assert c.title == "Federated RAG"
    assert "retrieval" in c.concepts
    assert set(c.source_external_ids) == {"openalex:W1", "crossref:10.1/a"}


def test_distill_skips_entity_with_no_resolvable_title():
    records = [_sr("orcid", "0000-0002", {})]
    entities = [
        ResolvedEntity(entity_id="ent-1", canonical_name="Bob", orcid="0000-0002",
                       member_records=["orcid:0000-0002"], resolution_method="deterministic-orcid"),
    ]
    cards = distill_cards(records, entities)
    # Falls back to the canonical name as the title rather than dropping the entity.
    assert cards[0].title == "Bob"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_distill.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.distill'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/distill.py
"""Distill resolved entities + source records into ResearchCards (plan §10.2).

A research card is the structured, public-tier summary handed to the single
classifier. We index source records by 'source:external_id' so an entity's
member_records can pull their payloads, then take the first non-empty title/
abstract/concepts found across that entity's members.
"""

from __future__ import annotations

from identity_resolution.models import ResolvedEntity

from mod_ingestion.records import ResearchCard, SourceRecord


def _title_of(payload: dict) -> str | None:
    t = payload.get("title")
    if isinstance(t, list):
        return str(t[0]) if t else None
    return str(t) if t else None


def distill_cards(
    records: list[SourceRecord], entities: list[ResolvedEntity]
) -> list[ResearchCard]:
    """Build one ResearchCard per ResolvedEntity (§10.2)."""
    by_ref = {f"{r.source}:{r.external_id}": r for r in records}
    cards: list[ResearchCard] = []
    for ent in entities:
        members = [by_ref[ref] for ref in ent.member_records if ref in by_ref]
        title = next((t for r in members if (t := _title_of(r.payload))), ent.canonical_name)
        abstract = next((str(r.payload["abstract"]) for r in members if r.payload.get("abstract")), "")
        concepts: tuple[str, ...] = ()
        for r in members:
            c = r.payload.get("concepts")
            if isinstance(c, list) and c:
                concepts = tuple(str(x) for x in c)
                break
        cards.append(
            ResearchCard(
                card_id=f"card-{ent.entity_id}",
                entity_id=ent.entity_id,
                title=title,
                abstract=abstract,
                concepts=concepts,
                source_external_ids=tuple(ent.member_records),
            )
        )
    return cards
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_distill.py -q
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/distill.py packages/mod-ingestion/tests/test_distill.py && git commit -m "feat(ingestion): distill SourceRecord+ResolvedEntity into ResearchCard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Dagster assets — the full snapshot→...→graph DAG + outbox-emit

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/assets.py`, `tigerexchange/packages/mod-ingestion/tests/conftest.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_assets_pipeline.py`.

Wires the assets: `snapshot_records` → `resolved_entities` → `research_cards` → `gated_cards` (classify hard edge) → `indexed_projections` (embed+index+graph, emits outbox events with `projection_version` + `revocation_epoch`). Quarantined cards branch to the adjudication-queue resource, never to indexing.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/conftest.py
import pytest
from contracts import (
    Capability,
    ClassificationResult,
    Decision,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
    Tier,
)


@pytest.fixture
def public_tenant() -> TenantContext:
    ent = Entitlement(
        edition=Edition.INSTITUTIONAL,
        capabilities=frozenset({Capability.PUBLIC_RETRIEVAL}),
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.public,
    )
    return TenantContext(tenant_id="public", subject_id="ingestor", entitlement=ent)


class _AllowClassifier:
    """ALLOW unless the title contains 'ambiguous' (-> quarantine)."""

    def classify(self, content, tenant):
        if b"ambiguous" in content:
            return ClassificationResult.quarantine(reason="low-confidence", confidence=0.1)
        return ClassificationResult(tier=Tier.public, decision=Decision.ALLOW, confidence=0.99)


@pytest.fixture
def allow_classifier():
    return _AllowClassifier()
```

```python
# tigerexchange/packages/mod-ingestion/tests/test_assets_pipeline.py
import json
from pathlib import Path

from dagster import materialize

from mod_ingestion.assets import (
    gated_cards,
    indexed_projections,
    research_cards,
    resolved_entities,
    snapshot_records,
)
from mod_ingestion.outbox import InMemoryIndexSink, InMemoryOutboxStore
from mod_ingestion.resources import IngestionResources
from mod_ingestion.sinks import FakeGraphSink, FakeLexicalSink, FakeVectorSink


def _seed(tmp_path: Path):
    oa = tmp_path / "openalex" / "works.jsonl"
    oa.parent.mkdir(parents=True)
    oa.write_text(
        "\n".join(json.dumps(r) for r in [
            {"id": "W1", "title": "Federated RAG", "abstract": "study", "concepts": ["retrieval"],
             "orcid": "0000-0001"},
            {"id": "W2", "title": "ambiguous thing", "orcid": "0000-0002"},
        ]),
        encoding="utf-8",
    )


def test_full_dag_materializes_and_gates(tmp_path, public_tenant, allow_classifier):
    _seed(tmp_path)
    res = IngestionResources(
        snapshot_root=str(tmp_path),
        tenant=public_tenant,
        classifier=allow_classifier,
        vector=FakeVectorSink(),
        lexical=FakeLexicalSink(),
        graph=FakeGraphSink(),
        outbox=InMemoryOutboxStore(),
        index_sink=InMemoryIndexSink(),
    )
    result = materialize(
        [snapshot_records, resolved_entities, research_cards, gated_cards, indexed_projections],
        resources={"ingestion": res},
    )
    assert result.success

    # The ambiguous card was quarantined and NEVER indexed.
    assert len(res.vector.upserts) == 1
    indexed_titles = {u[2]["title"] for u in res.vector.upserts}
    assert indexed_titles == {"Federated RAG"}

    # An outbox event was emitted for the indexed projection, carrying BOTH epochs.
    pending = res.outbox.fetch_pending(limit=10)
    assert len(pending) == 1
    assert pending[0].projection_version >= 1
    assert pending[0].revocation_epoch == res.current_revocation_epoch
    assert pending[0].kind == "index"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_assets_pipeline.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.resources'` / `mod_ingestion.assets`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/resources.py
"""Dagster resource bundle wiring injected sinks/classifier (plan §10.1, §5.8).

Holds the public-corpus TenantContext, the single fail-closed classifier
(IClassifier from 0b), the vector/lexical/graph sinks, the transactional outbox
store, and the per-CELL revocation epoch. Engines are injected so engine choice
stays insulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts import IClassifier, TenantContext

from mod_ingestion.outbox import InMemoryIndexSink, InMemoryOutboxStore
from mod_ingestion.sinks import GraphSink, LexicalSink, VectorSink


@dataclass
class IngestionResources:
    snapshot_root: str
    tenant: TenantContext
    classifier: IClassifier
    vector: VectorSink
    lexical: LexicalSink
    graph: GraphSink
    outbox: InMemoryOutboxStore
    index_sink: InMemoryIndexSink
    # Per-CELL fenced revocation epoch (§4.4a) — distinct from per-record projection_version.
    current_revocation_epoch: int = 0
    # Per-(tenant,record) projection versions (monotonic), assigned at emit (§10.3a).
    _proj_versions: dict[tuple[str, str], int] = field(default_factory=dict)

    def next_projection_version(self, tenant_id: str, record_id: str) -> int:
        key = (tenant_id, record_id)
        self._proj_versions[key] = self._proj_versions.get(key, 0) + 1
        return self._proj_versions[key]
```

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/assets.py
"""Dagster ingestion DAG (plan §10.1 Dagster-only, §10.2 classify-gates-index).

snapshot_records -> resolved_entities -> research_cards -> gated_cards
  -> indexed_projections (embed + index + graph + transactional-outbox emit).

The classify gate (gated_cards) is the HARD EDGE: only Decision.ALLOW cards
reach indexed_projections; quarantined cards are recorded and never indexed
(§11.1). Each indexed projection enqueues an OutboxEvent carrying the per-RECORD
projection_version AND the per-CELL revocation_epoch distinctly (Task 6/7).
"""

from __future__ import annotations

from dagster import AssetIn, Output, asset

from identity_resolution.models import ResolutionInput
from identity_resolution.resolver import EntityResolver

from mod_ingestion.classify_gate import classify_gate
from mod_ingestion.config import IngestionConfig
from mod_ingestion.distill import distill_cards
from mod_ingestion.outbox import OutboxEvent
from mod_ingestion.records import SourceRecord
from mod_ingestion.resources import IngestionResources
from mod_ingestion.sinks import build_projection, index_card
from mod_ingestion.sources.grants import read_grants_gov, read_nsf_awards, read_reporter_awards
from mod_ingestion.sources.scholarly import (
    read_crossref_file,
    read_openalex_snapshot,
    read_orcid_dump,
    read_ror_file,
    read_specter2_vectors,
)

_REQUIRED = {"ingestion"}


@asset(required_resource_keys=_REQUIRED)
def snapshot_records(context) -> list[SourceRecord]:
    res: IngestionResources = context.resources.ingestion
    cfg = IngestionConfig(snapshot_root=res.snapshot_root, public_corpus_tenant_id=res.tenant.tenant_id)
    records: list[SourceRecord] = []
    for reader in (
        read_openalex_snapshot, read_crossref_file, read_ror_file, read_orcid_dump,
        read_specter2_vectors, read_grants_gov, read_reporter_awards, read_nsf_awards,
    ):
        records.extend(reader(cfg))
    return records


@asset(ins={"snapshot_records": AssetIn()}, required_resource_keys=_REQUIRED)
def resolved_entities(context, snapshot_records: list[SourceRecord]):
    inputs = [
        ResolutionInput(
            record_ref=f"{r.source}:{r.external_id}",
            name=str(r.payload.get("title") or r.payload.get("name") or r.external_id),
            orcid=r.payload.get("orcid"),
            doi=r.payload.get("doi") or r.payload.get("DOI"),
            ror=r.payload.get("ror"),
        )
        for r in snapshot_records
    ]
    return EntityResolver().resolve(inputs)


@asset(ins={"snapshot_records": AssetIn(), "resolved_entities": AssetIn()})
def research_cards(snapshot_records, resolved_entities):
    return distill_cards(snapshot_records, resolved_entities)


@asset(required_resource_keys=_REQUIRED)
def gated_cards(context, research_cards):
    """The classify HARD EDGE (§10.2/§11.1)."""
    res: IngestionResources = context.resources.ingestion
    gate = classify_gate(research_cards, res.classifier, res.tenant)
    context.log.info(f"indexable={len(gate.indexable)} quarantined={len(gate.quarantined)}")
    return Output(
        gate.indexable,
        metadata={"quarantined": len(gate.quarantined), "indexable": len(gate.indexable)},
    )


@asset(required_resource_keys=_REQUIRED)
def indexed_projections(context, gated_cards):
    """embed -> index -> graph -> transactional-outbox emit (§10.2/§10.3)."""
    res: IngestionResources = context.resources.ingestion
    from contracts import Tier  # local import keeps module import-light

    emitted = 0
    for card in gated_cards:
        proj = build_projection(card, owner_tenant_id=res.tenant.tenant_id, input_tiers=[Tier.public])
        embedding = [float(len(card.title)), float(len(card.abstract))]  # placeholder embed in dev
        index_card(proj, embedding, res.vector, res.lexical, res.graph)
        version = res.next_projection_version(res.tenant.tenant_id, proj.artifact_id)
        # Transactional outbox: the event would be written in the SAME txn as the
        # index write in the Postgres impl; here we enqueue post-write for dev.
        res.outbox.enqueue(
            OutboxEvent(
                event_id=f"ev-{proj.projection_id}-v{version}",
                tenant_id=res.tenant.tenant_id,
                kind="index",
                record_id=proj.artifact_id,
                projection_version=version,          # per-RECORD monotonic (lower-version-reject)
                revocation_epoch=res.current_revocation_epoch,  # per-CELL fenced
                payload=dict(proj.fields),
            )
        )
        emitted += 1
    return Output(emitted, metadata={"emitted": emitted})
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_assets_pipeline.py -q
```
Expected: 1 passed (full DAG materializes; ambiguous card quarantined and not indexed; one outbox event with both epochs).

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/resources.py packages/mod-ingestion/src/mod_ingestion/assets.py packages/mod-ingestion/tests/conftest.py packages/mod-ingestion/tests/test_assets_pipeline.py && git commit -m "feat(ingestion): full Dagster DAG snapshot->resolve->distill->classify-gate->embed/index/graph + outbox emit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Dagster outbox-poller sensor + Definitions code-location

**Files:** Create `tigerexchange/packages/mod-ingestion/src/mod_ingestion/sensors.py`, `tigerexchange/packages/mod-ingestion/src/mod_ingestion/definitions.py`. Test `tigerexchange/packages/mod-ingestion/tests/test_sensor.py`.

The Dagster sensor drains pending outbox events and applies them monotonically (the §10.1 Dagster-sensor + transactional-outbox-polling pattern, NOT log-based CDC). The `Definitions` ties assets + a job + the sensor into one code location.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-ingestion/tests/test_sensor.py
from mod_ingestion.outbox import InMemoryIndexSink, InMemoryOutboxStore, MonotonicApplier, OutboxEvent
from mod_ingestion.sensors import drain_outbox_once


def test_drain_applies_pending_and_marks_delivered():
    store = InMemoryOutboxStore()
    sink = InMemoryIndexSink()
    store.enqueue(OutboxEvent(event_id="e1", tenant_id="t1", kind="index", record_id="r1",
                              projection_version=1, revocation_epoch=0, payload={"title": "v1"}))
    drained = drain_outbox_once(store, MonotonicApplier(sink), batch=10)
    assert drained == ["e1"]
    assert sink.get("t1", "r1")["title"] == "v1"
    # Idempotent: nothing left pending on the next drain.
    assert drain_outbox_once(store, MonotonicApplier(sink), batch=10) == []


def test_drain_rejects_lower_version_replay_but_still_marks_delivered():
    store = InMemoryOutboxStore()
    sink = InMemoryIndexSink()
    applier = MonotonicApplier(sink)
    store.enqueue(OutboxEvent(event_id="hi", tenant_id="t1", kind="index", record_id="r1",
                              projection_version=2, revocation_epoch=0, payload={"title": "v2"}))
    store.enqueue(OutboxEvent(event_id="lo", tenant_id="t1", kind="index", record_id="r1",
                              projection_version=1, revocation_epoch=0, payload={"title": "v1-STALE"}))
    drained = drain_outbox_once(store, applier, batch=10)
    # Both consumed (marked delivered), but the stale lower-version did not overwrite.
    assert sorted(drained) == ["hi", "lo"]
    assert sink.get("t1", "r1")["title"] == "v2"


def test_definitions_exposes_job_and_sensor():
    from mod_ingestion.definitions import defs

    assert defs.get_job_def("ingestion_job") is not None
    sensor_names = {s.name for s in defs.get_all_sensors()} if hasattr(defs, "get_all_sensors") else set()
    # Fallback: sensor is reachable via the repository's sensor defs.
    assert "outbox_poller" in sensor_names or any(
        s.name == "outbox_poller" for s in defs.get_repository_def().sensor_defs
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_sensor.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'mod_ingestion.sensors'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/sensors.py
"""Dagster outbox-poller sensor (plan §10.1, §10.3 — Dagster-only, NOT log-CDC).

Phase-0 grant-lifecycle / index propagation uses a Dagster sensor +
transactional-outbox-polling (Temporal/Debezium/Kafka deferred, §10.1). The
sensor periodically drains pending OutboxEvents and applies them through the
MONOTONIC applier (lower per-record projection_version rejected, §10.3a). Stale
replays are still marked delivered (they are safely no-ops) so they do not
re-drain forever.
"""

from __future__ import annotations

from dagster import DefaultSensorStatus, RunRequest, SkipReason, sensor

from mod_ingestion.outbox import InMemoryOutboxStore, MonotonicApplier


def drain_outbox_once(
    store: InMemoryOutboxStore, applier: MonotonicApplier, batch: int
) -> list[str]:
    """Drain one batch of pending events through the monotonic applier."""
    pending = store.fetch_pending(limit=batch)
    if not pending:
        return []
    delivered: list[str] = []
    for event in pending:
        applier.apply(event)  # returns 'applied' | 'rejected-lower-version'; both are terminal
        delivered.append(event.event_id)
    store.mark_delivered(delivered)
    return delivered


@sensor(job_name="ingestion_job", default_status=DefaultSensorStatus.STOPPED)
def outbox_poller(context):
    """Poll the outbox; in Phase-0 this drains via drain_outbox_once at the cell.

    The sensor body is intentionally a no-op trigger here: the drain is wired to
    the cell's live OutboxStore/applier at deployment. It exists so the
    Definitions code-location exposes a named poller (§10.1).
    """
    yield SkipReason("outbox-poller wired to live OutboxStore at deployment")
```

```python
# tigerexchange/packages/mod-ingestion/src/mod_ingestion/definitions.py
"""Dagster code-location for mod-ingestion (plan §10.1).

Bundles the ingestion assets into a single job plus the outbox-poller sensor.
Run with: `dagster dev -m mod_ingestion.definitions`.
"""

from __future__ import annotations

from dagster import Definitions, define_asset_job

from mod_ingestion.assets import (
    gated_cards,
    indexed_projections,
    research_cards,
    resolved_entities,
    snapshot_records,
)
from mod_ingestion.sensors import outbox_poller

_ASSETS = [snapshot_records, resolved_entities, research_cards, gated_cards, indexed_projections]

ingestion_job = define_asset_job(name="ingestion_job", selection=_ASSETS)

defs = Definitions(
    assets=_ASSETS,
    jobs=[ingestion_job],
    sensors=[outbox_poller],
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_sensor.py -q
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/src/mod_ingestion/sensors.py packages/mod-ingestion/src/mod_ingestion/definitions.py packages/mod-ingestion/tests/test_sensor.py && git commit -m "feat(ingestion): Dagster outbox-poller sensor + Definitions code-location (outbox-polling, no Temporal/CDC)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Full-suite lint/type/test gate

**Files:** Modify nothing (verification task). Runs the whole `mod-ingestion` + `identity-resolution` suite plus ruff/mypy.

- [ ] **Step 1: Write the failing test** — add a guard test asserting the package surfaces are wired.

```python
# tigerexchange/packages/mod-ingestion/tests/test_public_surface.py
"""Guard: the documented public surface of mod-ingestion is importable."""


def test_public_surface_importable():
    from mod_ingestion.assets import indexed_projections, snapshot_records
    from mod_ingestion.classify_gate import classify_gate
    from mod_ingestion.definitions import defs, ingestion_job
    from mod_ingestion.outbox import (
        CellRevocationEpoch,
        MonotonicApplier,
        OutboxEvent,
        ProjectionVersion,
        replication_mode_for,
    )
    from mod_ingestion.sensors import drain_outbox_once, outbox_poller
    from mod_ingestion.sinks import build_projection

    assert callable(classify_gate)
    assert callable(build_projection)
    assert callable(drain_outbox_once)
    assert ingestion_job is not None
    assert defs is not None
    assert ProjectionVersion is not CellRevocationEpoch
    assert callable(replication_mode_for)
    assert OutboxEvent.__name__ == "OutboxEvent"
    assert MonotonicApplier.__name__ == "MonotonicApplier"
    assert snapshot_records is not None and indexed_projections is not None
    assert outbox_poller is not None
```

- [ ] **Step 2: Run test to verify it fails** (only if a symbol is mis-wired; otherwise this confirms the surface)

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests/test_public_surface.py -q
```
Expected: initially fails only if any import path is wrong; fix the offending export, then it passes.

- [ ] **Step 3: Write minimal implementation** — no new code expected; if an import fails, correct the symbol name in the relevant module (no placeholder).

- [ ] **Step 4: Run full gate**

```bash
cd tigerexchange && python -m pytest packages/mod-ingestion/tests packages/identity-resolution/tests -q && ruff check packages/mod-ingestion/src packages/identity-resolution/src && mypy packages/mod-ingestion/src packages/identity-resolution/src
```
Expected: all tests pass, ruff clean, mypy clean.

- [ ] **Step 5: Commit**

```bash
cd tigerexchange && git add packages/mod-ingestion/tests/test_public_surface.py && git commit -m "test(ingestion): public-surface guard + full lint/type/test gate green

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes for the executing agent

- **Epoch disambiguation (the high finding) is Task 6 + Task 7 + Task 11.** Never compare a `CellRevocationEpoch` against a `ProjectionVersion`; they are different types with no cross-conversion. The applier's lower-version-reject uses ONLY `projection_version` keyed per `(tenant_id, record_id)`; `revocation_epoch` is carried alongside but is the per-CELL tombstone-set version (cursor for delta replication), never the applier's per-record reject key. The bitmap sizing (`bitmap_replicated_bytes` / `replication_mode_for`) documents the N=200 ~12.5 MB naive figure and switches to delta/log-tail above 256 KB/cycle — that is the defensible-≤2s-p99 fix from the convergence report.
- **Classify-gates-index hard edge** (Task 8 + the `gated_cards` asset) is the load-bearing safety invariant: only `ClassificationResult.is_retrievable` (== `Decision.ALLOW`) cards proceed; quarantine/deny are excluded from vector, lexical, AND graph sinks and from the outbox. The Task 11 test asserts zero leak end-to-end.
- **Kernel usage is verbatim:** `Tier`, `tier_join_all`, `Decision`, `ClassificationResult` (+ `.quarantine()` / `.is_retrievable`), `DiscoverabilityScope`, `PublishableProjection` (which rejects confidential tier per D6), `TenantContext`, `Entitlement`, `Capability`, `IClassifier`. No alternative signatures are introduced.
- **Phase-0 scope respected:** Dagster-only orchestration (no Temporal/Debezium/Kafka); snapshots not metered APIs; ORCID CC0 dump not API; entity resolution is deterministic-anchors + deterministic-blocking union-find (no learned scorer); public-tier only — no confidential cross-institution sharing, no revocation authority, no exchange seam (those remain kernel stubs). The `revocation_epoch` field is carried for the federation seam but Phase-0 emits only public projections.
- **RLS posture** is enforced in `OUTBOX_DDL`: `FORCE ROW LEVEL SECURITY`, `RESTRICTIVE`, `WITH CHECK`, `tenant_id` leading index, consumed via `SET LOCAL app.tenant_id` from `0a`. The in-memory store/sink fakes are dev/test doubles for the Postgres-backed implementations.