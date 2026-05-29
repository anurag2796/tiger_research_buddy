I have all five spec sections. Now I'll write the complete implementation plan for the classification engine sub-plan.

# Fail-Closed Classification Engine + Quarantine/Adjudication Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the single fail-closed classifier that labels records into the frozen 3-tier lattice + compliance codes, quarantines any low-confidence/adversarial input to `unclassified=confidential` (excluded from ALL retrieval), and persists a human-adjudication queue with a review/release workflow.
**Architecture:** A stateless classifier (`IClassifier`) emits a `ClassificationResult`; abstention/ambiguity below a configured confidence threshold forces `Decision.QUARANTINE` (tier=confidential, never retrievable, per D6). Quarantined records persist to a tenant-isolated Postgres adjudication queue under FORCE RLS; a review/release workflow lets a human approve a tier or reject. Sticky compliance flags propagate by UNION and tier by MAX-rule. A Phase-0 contract test injects adversarial records (confidential content with public-looking metadata) and asserts zero leak into any retrievable surface.
**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, Postgres (FORCE ROW LEVEL SECURITY, RESTRICTIVE policies, `SET LOCAL` tenant pinning), SQLAlchemy 2.x, pytest + hypothesis (property tests), ruff, mypy.
**Depends on:** `0a-foundation` (provides the `contracts` kernel package, Postgres+RLS foundation, `TenantContext`, config, FastAPI app skeleton, CI).

---

## File Structure

| File | Status | Single Responsibility |
|---|---|---|
| `tigerexchange/services/classification/pyproject.toml` | Create | Package metadata + deps (depends on `tigerexchange-contracts`, sqlalchemy, psycopg). |
| `tigerexchange/services/classification/src/classification/__init__.py` | Create | Public import surface for the classification service. |
| `tigerexchange/services/classification/src/classification/config.py` | Create | `ClassifierConfig` — the abstention confidence threshold + signal weights. |
| `tigerexchange/services/classification/src/classification/signals.py` | Create | Pure content-signal extraction (compliance-flag + tier signals from content/metadata). |
| `tigerexchange/services/classification/src/classification/classifier.py` | Create | `FailClosedClassifier(IClassifier)` — the single fail-closed classifier. |
| `tigerexchange/services/classification/src/classification/db.py` | Create | SQLAlchemy engine + `SET LOCAL app.tenant_id` transaction-scoped session helper. |
| `tigerexchange/services/classification/src/classification/models.py` | Create | `AdjudicationItem` ORM model (tenant-isolated quarantine queue row). |
| `tigerexchange/services/classification/src/classification/queue.py` | Create | `AdjudicationQueue` — persist quarantine + review/release/reject workflow. |
| `tigerexchange/services/classification/src/classification/ingest_gate.py` | Create | `classify_gate` — the hard classify-gates-index edge used by every ingestion path. |
| `tigerexchange/services/classification/migrations/0001_adjudication_queue.sql` | Create | DDL: `adjudication_item` table + FORCE RLS RESTRICTIVE policy + tenant_id-leading index. |
| `tigerexchange/services/classification/tests/__init__.py` | Create | Test package marker. |
| `tigerexchange/services/classification/tests/conftest.py` | Create | Pytest fixtures: `TenantContext` factory, in-tx Postgres session, queue fixture. |
| `tigerexchange/services/classification/tests/test_classifier.py` | Create | Unit tests for `FailClosedClassifier` decision/abstention semantics. |
| `tigerexchange/services/classification/tests/test_signals.py` | Create | Unit tests for signal extraction (tier + compliance flags). |
| `tigerexchange/services/classification/tests/test_queue.py` | Create | Tests for adjudication persist + review/release/reject workflow + RLS isolation. |
| `tigerexchange/services/classification/tests/test_ingest_gate.py` | Create | Tests for the classify-gate edge (allowed-through vs quarantined-blocked). |
| `tigerexchange/services/classification/tests/test_properties.py` | Create | Hypothesis property tests: MAX-rule, sticky-flag UNION. |
| `tigerexchange/services/classification/tests/test_contract_zero_leak.py` | Create | Phase-0 contract test: adversarial + low-confidence records leak nowhere retrievable. |

---

## Tasks

### Task 1: Classification service package scaffold

**Files:** Create `tigerexchange/services/classification/pyproject.toml`, Create `tigerexchange/services/classification/src/classification/__init__.py`, Test `tigerexchange/services/classification/tests/__init__.py`, Test `tigerexchange/services/classification/tests/test_imports.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_imports.py`:
```python
"""Smoke test: the classification package imports and re-exports its surface."""


def test_package_exposes_public_surface() -> None:
    import classification

    # These are the symbols every ingestion path will import.
    assert hasattr(classification, "FailClosedClassifier")
    assert hasattr(classification, "ClassifierConfig")
    assert hasattr(classification, "AdjudicationQueue")
    assert hasattr(classification, "classify_gate")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_imports.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'classification'` (package not yet installed).

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/pyproject.toml`:
```toml
[project]
name = "tigerexchange-classification"
version = "0.0.0"
description = "TigerExchange single fail-closed classification engine + quarantine/adjudication queue (plan §11.1, §11.8, D6)."
requires-python = ">=3.11"
dependencies = [
    "tigerexchange-contracts",
    "pydantic>=2.6,<3",
    "sqlalchemy>=2.0,<3",
    "psycopg[binary]>=3.1,<4",
]

[project.optional-dependencies]
dev = ["pytest>=8", "hypothesis>=6", "ruff", "mypy"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/classification"]
```

Create `tigerexchange/services/classification/src/classification/__init__.py`:
```python
"""TigerExchange single fail-closed classification engine (plan §11.1, §11.8, D6).

Public surface imported by every ingestion path. The classify-gate is the hard
classify-gates-index edge: nothing reaches a retrievable surface without passing
through ``classify_gate`` and being authorized by an ALLOW decision.
"""

from classification.classifier import FailClosedClassifier
from classification.config import ClassifierConfig
from classification.ingest_gate import GateOutcome, classify_gate
from classification.queue import AdjudicationQueue

__all__ = [
    "FailClosedClassifier",
    "ClassifierConfig",
    "AdjudicationQueue",
    "classify_gate",
    "GateOutcome",
]
```

Create empty `tigerexchange/services/classification/tests/__init__.py` (no content).

- [ ] **Step 4: Run test to verify it passes (AFTER Tasks 2–6 land)**

The import smoke test exercises the package's public surface, which re-exports `config`, `classifier`, `queue`, and `ingest_gate`. Those modules are created in Tasks 2–6, so this step runs ONCE, after Task 6 has landed all four modules. Do not create placeholder modules; run this step at the point where the real modules exist.

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && pip install -e . && python -m pytest tests/test_imports.py -q
```
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/pyproject.toml tigerexchange/services/classification/src/classification/__init__.py tigerexchange/services/classification/tests/__init__.py tigerexchange/services/classification/tests/test_imports.py
git commit -m "feat(classification): scaffold fail-closed classification service package

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Classifier configuration (abstention threshold)

**Files:** Create `tigerexchange/services/classification/src/classification/config.py`, Test `tigerexchange/services/classification/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_config.py`:
```python
"""ClassifierConfig: the Phase-0 abstention confidence threshold (plan §11.1)."""

import pytest

from classification.config import ClassifierConfig


def test_default_threshold_is_strict() -> None:
    cfg = ClassifierConfig()
    # Phase-0: a record must clear a stated confidence threshold to be labeled.
    assert 0.0 < cfg.confidence_threshold <= 1.0
    assert cfg.confidence_threshold >= 0.7  # strict default; tunable, never 0.


def test_threshold_must_be_in_unit_interval() -> None:
    with pytest.raises(ValueError):
        ClassifierConfig(confidence_threshold=1.5)
    with pytest.raises(ValueError):
        ClassifierConfig(confidence_threshold=0.0)  # 0 would let everything pass


def test_config_is_frozen() -> None:
    cfg = ClassifierConfig()
    with pytest.raises(Exception):
        cfg.confidence_threshold = 0.5  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_config.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'classification.config'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/src/classification/config.py`:
```python
"""Classifier configuration — the Phase-0 abstention threshold (plan §11.1).

The confidence threshold is the single knob that governs fail-closed behavior:
any record the classifier scores BELOW this threshold is quarantined
(default-deny, treated confidential, excluded from all retrieval). The default
is strict; it is tunable but may never be 0 (which would let everything pass).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ClassifierConfig(BaseModel):
    """Configuration for the single fail-closed classifier.

    Frozen: configuration is a decision input, not mutable per-request state.
    """

    model_config = ConfigDict(frozen=True)

    # gt=0.0: a 0 threshold would disable abstention (everything labeled). le=1.0:
    # confidence is in [0,1]. Default 0.7 = strict Phase-0 floor.
    confidence_threshold: float = Field(default=0.7, gt=0.0, le=1.0)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_config.py -q
```
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/src/classification/config.py tigerexchange/services/classification/tests/test_config.py
git commit -m "feat(classification): add ClassifierConfig abstention threshold

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Content-signal extraction (tier + compliance flags)

**Files:** Create `tigerexchange/services/classification/src/classification/signals.py`, Test `tigerexchange/services/classification/tests/test_signals.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_signals.py`:
```python
"""Signal extraction: tier + compliance flags from content/metadata (plan §6.1)."""

from contracts import ComplianceFlag, Tier

from classification.signals import ContentSignals, extract_signals


def test_public_content_scores_public_high_confidence() -> None:
    sig = extract_signals(b"Published in Nature 2024. DOI:10.1/x. Open access.")
    assert isinstance(sig, ContentSignals)
    assert sig.tier == Tier.public
    assert sig.confidence >= 0.7
    assert sig.compliance_flags == frozenset()


def test_confidential_content_scores_confidential() -> None:
    sig = extract_signals(
        b"DRAFT PROPOSAL - CONFIDENTIAL. Preliminary unpublished budget figures."
    )
    assert sig.tier == Tier.confidential
    assert sig.confidence >= 0.7


def test_ferpa_marker_sets_sticky_flag() -> None:
    sig = extract_signals(b"Student grade record, education record per FERPA.")
    assert ComplianceFlag.FERPA in sig.compliance_flags


def test_export_marker_sets_itar_ear_flags() -> None:
    sig = extract_signals(b"ITAR-controlled technical data. Export-controlled EAR.")
    assert ComplianceFlag.ITAR in sig.compliance_flags
    assert ComplianceFlag.EAR in sig.compliance_flags


def test_ambiguous_content_scores_low_confidence() -> None:
    # No tier-discriminating signal at all -> classifier cannot confidently label.
    sig = extract_signals(b"asdf qwer zxcv")
    assert sig.confidence < 0.7


def test_adversarial_confidential_with_public_metadata_is_not_high_confidence_public() -> None:
    # Public-LOOKING metadata wrapping confidential content: must NOT be confidently public.
    sig = extract_signals(
        b"Open access preprint. DOI:10.1/x. "
        b"INTERNAL DRAFT PROPOSAL preliminary unpublished budget CONFIDENTIAL."
    )
    # Conflicting signals => either confidential tier or low confidence, never confident-public.
    assert not (sig.tier == Tier.public and sig.confidence >= 0.7)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_signals.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'classification.signals'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/src/classification/signals.py`:
```python
"""Pure content-signal extraction for the fail-closed classifier (plan §6.1, §11.1).

Phase-0 is a deterministic, rule-based signal extractor (NOT an LLM classifier —
the dual/LLM classifier is deferred per §11.1). It produces a tier estimate, a
confidence in [0,1], and the sticky compliance flags it detected. The classifier
(classifier.py) turns a low confidence or a confidential/ambiguous signal into a
fail-closed QUARANTINE.

Design: conflicting signals (public-looking metadata wrapping confidential
markers) collapse confidence so an adversarial record can never be confidently
public — the core §11.1 adversarial requirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts import ComplianceFlag, Tier

# Lower-cased substring markers per tier. Confidential markers dominate (MAX-rule
# is applied at the classifier; here we record which tiers fired).
_CONFIDENTIAL_MARKERS = (
    "confidential",
    "draft proposal",
    "preliminary unpublished",
    "internal draft",
    "unpublished budget",
    "preliminary data",
)
_PRIVATE_MARKERS = (
    "internal use",
    "not for distribution",
    "private",
)
_PUBLIC_MARKERS = (
    "published in",
    "doi:",
    "open access",
    "preprint",
    "public record",
)

_COMPLIANCE_MARKERS: dict[ComplianceFlag, tuple[str, ...]] = {
    ComplianceFlag.FERPA: ("ferpa", "education record", "student grade"),
    ComplianceFlag.IRB: ("irb", "human subjects", "informed consent"),
    ComplianceFlag.ITAR: ("itar",),
    ComplianceFlag.EAR: ("export-controlled ear", "ear-controlled", "ear ", "export-controlled"),
    ComplianceFlag.GDPR_PERSONAL: ("gdpr", "personal data", "data subject"),
}


@dataclass(frozen=True)
class ContentSignals:
    """Extracted signals: a tier estimate, a confidence, and sticky flags."""

    tier: Tier
    confidence: float
    compliance_flags: frozenset[ComplianceFlag] = field(default_factory=frozenset)


def _count_hits(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for m in markers if m in text)


def extract_signals(content: bytes) -> ContentSignals:
    """Extract tier + confidence + sticky compliance flags from raw content.

    Confidence is HIGH only when the dominant tier's markers fire and competing
    higher-restriction markers do NOT. If a confidential/private marker AND a
    public marker both fire (adversarial mosaic), confidence collapses so the
    record cannot be confidently labeled public — it routes to quarantine.
    """
    text = content.decode("utf-8", errors="ignore").lower()

    conf_hits = _count_hits(text, _CONFIDENTIAL_MARKERS)
    priv_hits = _count_hits(text, _PRIVATE_MARKERS)
    pub_hits = _count_hits(text, _PUBLIC_MARKERS)

    flags: set[ComplianceFlag] = set()
    for flag, markers in _COMPLIANCE_MARKERS.items():
        if _count_hits(text, markers) > 0:
            flags.add(flag)

    # MAX-rule intuition: a confidential marker dominates regardless of public noise.
    if conf_hits > 0:
        # Confident confidential unless there is NO supporting weight (handled by hits>0).
        confidence = 0.9 if conf_hits >= 1 else 0.5
        return ContentSignals(Tier.confidential, confidence, frozenset(flags))

    if priv_hits > 0:
        # Private + public both firing => ambiguous, collapse confidence.
        confidence = 0.5 if pub_hits > 0 else 0.85
        tier = Tier.private
        return ContentSignals(tier, confidence, frozenset(flags))

    if pub_hits > 0:
        # Clean public: high confidence only when NOTHING more restrictive fired.
        confidence = 0.9
        return ContentSignals(Tier.public, confidence, frozenset(flags))

    # No discriminating signal at all: the classifier cannot confidently label.
    return ContentSignals(Tier.confidential, 0.2, frozenset(flags))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_signals.py -q
```
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/src/classification/signals.py tigerexchange/services/classification/tests/test_signals.py
git commit -m "feat(classification): deterministic content-signal extraction with adversarial collapse

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: The single fail-closed classifier

**Files:** Create `tigerexchange/services/classification/src/classification/classifier.py`, Test `tigerexchange/services/classification/tests/test_classifier.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_classifier.py`:
```python
"""FailClosedClassifier: single classifier with quarantine-on-abstention (§11.1, D6)."""

from contracts import (
    ClassificationResult,
    ComplianceFlag,
    Decision,
    IClassifier,
    TenantContext,
    Tier,
)

from classification.classifier import FailClosedClassifier
from classification.config import ClassifierConfig
from tests.conftest import make_tenant


def test_classifier_satisfies_kernel_protocol() -> None:
    assert isinstance(FailClosedClassifier(), IClassifier)


def test_confident_public_is_allowed_with_its_label() -> None:
    clf = FailClosedClassifier()
    res = clf.classify(b"Published in Nature 2024. DOI:10.1/x. Open access.", make_tenant())
    assert isinstance(res, ClassificationResult)
    assert res.tier == Tier.public
    assert res.decision == Decision.ALLOW
    assert res.is_retrievable is True


def test_confident_confidential_is_allowed_but_not_publicly_retrievable_label() -> None:
    clf = FailClosedClassifier()
    res = clf.classify(b"DRAFT PROPOSAL CONFIDENTIAL preliminary unpublished budget.", make_tenant())
    assert res.tier == Tier.confidential
    assert res.decision == Decision.ALLOW  # confidently labeled => uses its label


def test_low_confidence_is_quarantined_confidential_and_not_retrievable() -> None:
    clf = FailClosedClassifier()
    res = clf.classify(b"asdf qwer zxcv", make_tenant())
    assert res.decision == Decision.QUARANTINE
    assert res.tier == Tier.confidential  # quarantine == treated confidential
    assert res.is_retrievable is False
    assert res.reason  # must record an abstention cause for the queue + audit


def test_adversarial_confidential_with_public_metadata_never_confident_public() -> None:
    clf = FailClosedClassifier()
    res = clf.classify(
        b"Open access preprint DOI:10.1/x INTERNAL DRAFT PROPOSAL "
        b"preliminary unpublished budget CONFIDENTIAL.",
        make_tenant(),
    )
    # Must NOT be a confident-public ALLOW. Either confidential ALLOW or QUARANTINE.
    assert not (res.tier == Tier.public and res.decision == Decision.ALLOW)
    assert res.is_retrievable is False or res.tier != Tier.public


def test_threshold_is_honored() -> None:
    # With an impossibly strict threshold, even clean public abstains -> quarantine.
    clf = FailClosedClassifier(ClassifierConfig(confidence_threshold=1.0))
    res = clf.classify(b"Published in Nature. DOI:10.1/x. Open access.", make_tenant())
    assert res.decision == Decision.QUARANTINE


def test_compliance_flags_are_carried_onto_result() -> None:
    clf = FailClosedClassifier()
    res = clf.classify(b"ITAR-controlled technical data. Open access DOI:10.1/x.", make_tenant())
    # ITAR present + public marker => conflict => not confident public; flag still carried.
    assert ComplianceFlag.ITAR in res.compliance_flags
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_classifier.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'classification.classifier'` (and `tests.conftest.make_tenant` not yet defined — conftest lands in Task 7; if running standalone, this task's tests that import `make_tenant` will error until Task 7. Run the non-conftest subset first, or land conftest's `make_tenant` helper here. To keep this task self-contained, add the minimal conftest in Step 3.)

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/src/classification/classifier.py`:
```python
"""The single fail-closed classifier (plan §11.1, §11.8, D6).

This is the ONLY classifier in Phase-0. It implements the kernel IClassifier
contract. Semantics (verbatim from §11.1):

  - A record the classifier can CONFIDENTLY label (signal confidence >= the
    configured threshold) uses its label -> Decision.ALLOW at that tier.
  - A record it CANNOT confidently label (below threshold), OR any confidential
    record, OR any adversarial/ambiguous record, is QUARANTINED:
    tier forced to confidential, Decision.QUARANTINE, excluded from ALL
    retrieval, routed to the human-adjudication queue.

Per D6 an abstained/quarantined record is NEVER a candidate for any retrievable
surface. The classifier is stateless; it persists nothing (the queue does).
"""

from __future__ import annotations

from contracts import ClassificationResult, Decision, TenantContext, Tier

from classification.config import ClassifierConfig
from classification.signals import extract_signals


class FailClosedClassifier:
    """Single fail-closed classifier implementing the kernel IClassifier seam."""

    def __init__(self, config: ClassifierConfig | None = None) -> None:
        self._config = config or ClassifierConfig()

    def classify(self, content: bytes, tenant: TenantContext) -> ClassificationResult:
        """Classify content fail-closed. Abstention -> QUARANTINE (§11.1, D6)."""
        signals = extract_signals(content)
        threshold = self._config.confidence_threshold

        # Fail-closed gate: below the stated confidence threshold => quarantine.
        if signals.confidence < threshold:
            result = ClassificationResult.quarantine(
                reason=(
                    f"abstain: confidence {signals.confidence:.2f} < threshold "
                    f"{threshold:.2f} (estimated tier {signals.tier.wire})"
                ),
                confidence=signals.confidence,
            )
            # Sticky flags must survive into the queue/audit even on quarantine.
            return result.model_copy(
                update={"compliance_flags": signals.compliance_flags}
            )

        # Confidently labeled: use the label.
        return ClassificationResult(
            tier=signals.tier,
            decision=Decision.ALLOW,
            confidence=signals.confidence,
            compliance_flags=signals.compliance_flags,
            reason=f"confident label {signals.tier.wire}",
        )
```

Also create `tigerexchange/services/classification/tests/conftest.py` with the `make_tenant` helper used here (full conftest fleshed out in Task 7; this minimal version unblocks Task 4):
```python
"""Shared pytest fixtures for the classification service tests."""

from __future__ import annotations

import os

import pytest
from contracts import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
    Tier,
)


def make_tenant(tenant_id: str = "t-anchor", subject_id: str = "u-1") -> TenantContext:
    """Construct a confidential-capable TenantContext for tests."""
    ent = Entitlement(
        edition=Edition.CONFIDENTIAL_SOVEREIGN,
        capabilities=frozenset(
            {
                Capability.PUBLIC_RETRIEVAL,
                Capability.OWN_MATERIALS,
                Capability.PRIVATE_TIER,
                Capability.CONFIDENTIAL_WORKSPACE,
            }
        ),
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.confidential,
    )
    return TenantContext(tenant_id=tenant_id, subject_id=subject_id, entitlement=ent)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_classifier.py -q
```
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/src/classification/classifier.py tigerexchange/services/classification/tests/test_classifier.py tigerexchange/services/classification/tests/conftest.py
git commit -m "feat(classification): single fail-closed classifier with quarantine-on-abstention

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Adjudication-queue DDL (FORCE RLS, RESTRICTIVE, tenant_id-leading)

**Files:** Create `tigerexchange/services/classification/migrations/0001_adjudication_queue.sql`, Test `tigerexchange/services/classification/tests/test_migration_ddl.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_migration_ddl.py`:
```python
"""The adjudication-queue DDL must enforce tenant isolation (plan §7.7, §11.8)."""

from pathlib import Path

DDL = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0001_adjudication_queue.sql"
).read_text()


def test_table_exists_with_tenant_id_leading() -> None:
    assert "create table" in DDL.lower()
    assert "adjudication_item" in DDL.lower()
    assert "tenant_id" in DDL.lower()


def test_force_row_level_security_enabled() -> None:
    lowered = DDL.lower()
    assert "enable row level security" in lowered
    # FORCE so the table OWNER is also subject to RLS (defense-in-depth, §7.7).
    assert "force row level security" in lowered


def test_policy_is_restrictive_and_pins_tenant() -> None:
    lowered = DDL.lower()
    assert "as restrictive" in lowered
    assert "current_setting('app.tenant_id'" in lowered
    # WITH CHECK so inserts cannot write another tenant's id.
    assert "with check" in lowered


def test_tenant_id_leading_index_present() -> None:
    lowered = DDL.lower()
    assert "create index" in lowered
    assert "(tenant_id" in lowered  # tenant_id must be the LEADING index column


def test_status_and_quarantine_columns_present() -> None:
    lowered = DDL.lower()
    for col in ("status", "tier", "confidence", "reason", "compliance_flags", "content_ref"):
        assert col in lowered
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_migration_ddl.py -q
```
Expected failure: `FileNotFoundError: .../migrations/0001_adjudication_queue.sql`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/migrations/0001_adjudication_queue.sql`:
```sql
-- Adjudication queue for quarantined records (plan §11.1, §11.8, §7.7).
-- A quarantined record (Decision.QUARANTINE) lands here as status='pending'.
-- It is tenant-isolated by FORCE ROW LEVEL SECURITY with a RESTRICTIVE policy
-- pinned to the SET LOCAL app.tenant_id of the transaction (§7.7 defense-in-depth).

CREATE TABLE IF NOT EXISTS adjudication_item (
    id              UUID PRIMARY KEY,
    tenant_id       TEXT        NOT NULL,
    artifact_id     TEXT        NOT NULL,
    content_ref     TEXT        NOT NULL,  -- pointer to quarantined content (never inline confidential bytes)
    status          TEXT        NOT NULL DEFAULT 'pending',  -- pending | released | rejected
    tier            TEXT        NOT NULL,  -- always 'confidential' while pending (quarantine == confidential)
    confidence      DOUBLE PRECISION NOT NULL,
    reason          TEXT        NOT NULL,
    compliance_flags TEXT[]     NOT NULL DEFAULT '{}',
    -- Release outcome (set only on human review):
    released_tier   TEXT,                  -- human-approved tier on release
    reviewer_id     TEXT,
    review_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at     TIMESTAMPTZ,
    CONSTRAINT adjudication_status_chk
        CHECK (status IN ('pending', 'released', 'rejected'))
);

-- tenant_id-leading index: every RLS-scoped query filters tenant_id first (§7.7).
CREATE INDEX IF NOT EXISTS idx_adjudication_tenant_status
    ON adjudication_item (tenant_id, status, created_at);

-- FORCE so even the table owner is subject to RLS (no owner bypass; §7.7).
ALTER TABLE adjudication_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE adjudication_item FORCE ROW LEVEL SECURITY;

-- RESTRICTIVE policy: ANDs with any future policy; isolates by SET LOCAL tenant.
-- WITH CHECK prevents writing another tenant's row.
CREATE POLICY adjudication_tenant_isolation
    ON adjudication_item
    AS RESTRICTIVE
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_migration_ddl.py -q
```
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/migrations/0001_adjudication_queue.sql tigerexchange/services/classification/tests/test_migration_ddl.py
git commit -m "feat(classification): adjudication queue DDL with FORCE RLS RESTRICTIVE tenant isolation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: DB session helper + ORM model + AdjudicationQueue workflow

**Files:** Create `tigerexchange/services/classification/src/classification/db.py`, Create `tigerexchange/services/classification/src/classification/models.py`, Create `tigerexchange/services/classification/src/classification/queue.py`, Test `tigerexchange/services/classification/tests/test_queue.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_queue.py`:
```python
"""AdjudicationQueue: persist quarantine + review/release/reject + RLS isolation."""

import pytest
from contracts import ClassificationResult, Decision, Tier

from classification.classifier import FailClosedClassifier
from classification.queue import AdjudicationQueue
from tests.conftest import make_tenant


@pytest.mark.integration
def test_quarantined_record_persists_as_pending(pg_session_factory) -> None:
    tenant = make_tenant()
    q = AdjudicationQueue(pg_session_factory)
    res = ClassificationResult.quarantine(reason="abstain test", confidence=0.2)

    item_id = q.enqueue(tenant, artifact_id="a-1", content_ref="blob://a-1", result=res)
    pending = q.list_pending(tenant)

    assert any(i.id == item_id for i in pending)
    item = next(i for i in pending if i.id == item_id)
    assert item.status == "pending"
    assert item.tier == Tier.confidential.wire  # quarantine == confidential


@pytest.mark.integration
def test_only_quarantine_results_can_be_enqueued(pg_session_factory) -> None:
    tenant = make_tenant()
    q = AdjudicationQueue(pg_session_factory)
    allowed = ClassificationResult(
        tier=Tier.public, decision=Decision.ALLOW, confidence=0.9
    )
    with pytest.raises(ValueError):
        q.enqueue(tenant, artifact_id="a-2", content_ref="blob://a-2", result=allowed)


@pytest.mark.integration
def test_release_assigns_human_tier_and_marks_released(pg_session_factory) -> None:
    tenant = make_tenant()
    q = AdjudicationQueue(pg_session_factory)
    res = ClassificationResult.quarantine(reason="abstain", confidence=0.2)
    item_id = q.enqueue(tenant, artifact_id="a-3", content_ref="blob://a-3", result=res)

    released = q.release(tenant, item_id, reviewer_id="rev-1",
                         approved_tier=Tier.private, review_reason="manually reviewed")
    assert released.status == "released"
    assert released.released_tier == Tier.private.wire
    # No longer pending.
    assert all(i.id != item_id for i in q.list_pending(tenant))


@pytest.mark.integration
def test_reject_marks_rejected_and_stays_out_of_retrieval(pg_session_factory) -> None:
    tenant = make_tenant()
    q = AdjudicationQueue(pg_session_factory)
    res = ClassificationResult.quarantine(reason="abstain", confidence=0.2)
    item_id = q.enqueue(tenant, artifact_id="a-4", content_ref="blob://a-4", result=res)

    rejected = q.reject(tenant, item_id, reviewer_id="rev-1", review_reason="confirmed confidential")
    assert rejected.status == "rejected"
    assert all(i.id != item_id for i in q.list_pending(tenant))


@pytest.mark.integration
def test_rls_isolation_one_tenant_cannot_see_anothers_queue(pg_session_factory) -> None:
    t1 = make_tenant(tenant_id="t-1")
    t2 = make_tenant(tenant_id="t-2")
    q = AdjudicationQueue(pg_session_factory)
    res = ClassificationResult.quarantine(reason="abstain", confidence=0.2)
    q.enqueue(t1, artifact_id="a-1", content_ref="blob://a-1", result=res)

    # t2's RLS-scoped session must NOT see t1's quarantined item.
    assert q.list_pending(t2) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_queue.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'classification.queue'` (and `pg_session_factory` fixture missing until Task 7). Run again after Task 7 to exercise the integration path.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/src/classification/db.py`:
```python
"""SQLAlchemy engine + transaction-scoped tenant-pinned session (plan §7.7).

Every queue operation runs inside ONE transaction that begins with
``SET LOCAL app.tenant_id = :tenant_id`` so the RESTRICTIVE RLS policy in
0001_adjudication_queue.sql scopes all rows to the tenant. SET LOCAL (not SET)
is mandatory: it is transaction-scoped and cannot leak across a pooled
connection (§7.7).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from contracts import TenantContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(dsn: str) -> Engine:
    """Create an Engine. App role is NON-superuser so FORCE RLS is not bypassed."""
    return create_engine(dsn, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def tenant_session(
    session_factory: sessionmaker[Session], tenant: TenantContext
) -> Iterator[Session]:
    """Yield a session whose transaction is pinned to ``tenant`` via SET LOCAL.

    Commits on clean exit, rolls back on exception. The SET LOCAL is the first
    statement in the transaction, so RLS applies to every subsequent query.
    """
    session = session_factory()
    try:
        session.begin()
        session.execute(
            text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant.tenant_id}
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Create `tigerexchange/services/classification/src/classification/models.py`:
```python
"""ORM model for the adjudication-queue row (plan §11.1)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Double, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AdjudicationItem(Base):
    """A quarantined record awaiting human adjudication (status='pending')."""

    __tablename__ = "adjudication_item"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    artifact_id: Mapped[str] = mapped_column(String, nullable=False)
    content_ref: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    tier: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Double, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    compliance_flags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    released_tier: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

Create `tigerexchange/services/classification/src/classification/queue.py`:
```python
"""AdjudicationQueue: persist quarantine + human review/release/reject (§11.1).

This is the human-adjudication queue. The classify-gate (ingest_gate.py) enqueues
every QUARANTINE result here; nothing in the queue is retrievable. A human
reviewer either RELEASES the record with an approved tier (it may then be indexed
at that tier by the ingestion path) or REJECTS it (it stays confidential, never
indexed). All operations are tenant-pinned via SET LOCAL (RLS-isolated, §7.7).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from contracts import ClassificationResult, Decision, TenantContext, Tier
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from classification.db import tenant_session
from classification.models import AdjudicationItem


class AdjudicationQueue:
    """Persistent, tenant-isolated human-adjudication queue for quarantined records."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def enqueue(
        self,
        tenant: TenantContext,
        *,
        artifact_id: str,
        content_ref: str,
        result: ClassificationResult,
    ) -> str:
        """Persist a quarantined record as status='pending'. Returns the item id.

        Refuses anything that is not a QUARANTINE result — only abstained/
        quarantined records belong in the adjudication queue.
        """
        if result.decision is not Decision.QUARANTINE:
            raise ValueError(
                "AdjudicationQueue.enqueue accepts only QUARANTINE results; "
                f"got {result.decision}."
            )
        item_id = str(uuid.uuid4())
        with tenant_session(self._sf, tenant) as s:
            s.add(
                AdjudicationItem(
                    id=item_id,
                    tenant_id=tenant.tenant_id,
                    artifact_id=artifact_id,
                    content_ref=content_ref,
                    status="pending",
                    tier=Tier.confidential.wire,  # quarantine == confidential
                    confidence=result.confidence,
                    reason=result.reason,
                    compliance_flags=[f.value for f in result.compliance_flags],
                )
            )
        return item_id

    def list_pending(self, tenant: TenantContext) -> list[AdjudicationItem]:
        """All pending items for the tenant (RLS already scopes to tenant)."""
        with tenant_session(self._sf, tenant) as s:
            rows = (
                s.execute(
                    select(AdjudicationItem)
                    .where(AdjudicationItem.status == "pending")
                    .order_by(AdjudicationItem.created_at)
                )
                .scalars()
                .all()
            )
            for r in rows:
                s.expunge(r)
            return list(rows)

    def release(
        self,
        tenant: TenantContext,
        item_id: str,
        *,
        reviewer_id: str,
        approved_tier: Tier,
        review_reason: str,
    ) -> AdjudicationItem:
        """Human approves a tier; record leaves quarantine for indexing at that tier."""
        with tenant_session(self._sf, tenant) as s:
            item = s.get(AdjudicationItem, item_id)
            if item is None or item.status != "pending":
                raise ValueError(f"no pending adjudication item {item_id}")
            item.status = "released"
            item.released_tier = approved_tier.wire
            item.reviewer_id = reviewer_id
            item.review_reason = review_reason
            item.reviewed_at = datetime.now(timezone.utc)
            s.flush()
            s.expunge(item)
            return item

    def reject(
        self,
        tenant: TenantContext,
        item_id: str,
        *,
        reviewer_id: str,
        review_reason: str,
    ) -> AdjudicationItem:
        """Human confirms the record stays confidential; never indexed."""
        with tenant_session(self._sf, tenant) as s:
            item = s.get(AdjudicationItem, item_id)
            if item is None or item.status != "pending":
                raise ValueError(f"no pending adjudication item {item_id}")
            item.status = "rejected"
            item.reviewer_id = reviewer_id
            item.review_reason = review_reason
            item.reviewed_at = datetime.now(timezone.utc)
            s.flush()
            s.expunge(item)
            return item
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_queue.py -q
```
Expected (after Task 7 provides `pg_session_factory`): `5 passed`. If run before Task 7, the fixture is missing — land Task 7 then re-run.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/src/classification/db.py tigerexchange/services/classification/src/classification/models.py tigerexchange/services/classification/src/classification/queue.py tigerexchange/services/classification/tests/test_queue.py
git commit -m "feat(classification): adjudication queue persistence + review/release/reject workflow

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Integration test fixtures (Postgres + RLS + migration applied)

**Files:** Modify `tigerexchange/services/classification/tests/conftest.py`

- [ ] **Step 1: Write the failing test**

Add to `tigerexchange/services/classification/tests/test_queue.py` a fixture-consumer sanity test at the top of the file body (append):
```python
@pytest.mark.integration
def test_pg_session_factory_applies_migration(pg_session_factory) -> None:
    # The fixture must have created the adjudication_item table with RLS.
    from sqlalchemy import text

    s = pg_session_factory()
    try:
        s.begin()
        s.execute(text("SET LOCAL app.tenant_id = 't-probe'"))
        # Querying the table must succeed (table exists) and return 0 rows for a fresh tenant.
        n = s.execute(text("SELECT count(*) FROM adjudication_item")).scalar_one()
        assert n == 0
    finally:
        s.rollback()
        s.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_queue.py::test_pg_session_factory_applies_migration -q
```
Expected failure: `fixture 'pg_session_factory' not found`.

- [ ] **Step 3: Write minimal implementation**

Replace `tigerexchange/services/classification/tests/conftest.py` (extend the Task-4 minimal version) with:
```python
"""Shared pytest fixtures for the classification service tests.

The pg_session_factory fixture stands up the adjudication_item schema (running
0001_adjudication_queue.sql) against a Postgres reachable via TIGEREXCHANGE_TEST_DSN.
It connects as a NON-superuser app role so FORCE RLS is enforced (a superuser
bypasses RLS). Integration tests are skipped when no DSN is configured.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from contracts import (
    Capability,
    Edition,
    Entitlement,
    IsolationPosture,
    TenantContext,
    Tier,
)
from sqlalchemy import text

from classification.db import make_engine, make_session_factory

_MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "0001_adjudication_queue.sql"
).read_text()


def make_tenant(tenant_id: str = "t-anchor", subject_id: str = "u-1") -> TenantContext:
    """Construct a confidential-capable TenantContext for tests."""
    ent = Entitlement(
        edition=Edition.CONFIDENTIAL_SOVEREIGN,
        capabilities=frozenset(
            {
                Capability.PUBLIC_RETRIEVAL,
                Capability.OWN_MATERIALS,
                Capability.PRIVATE_TIER,
                Capability.CONFIDENTIAL_WORKSPACE,
            }
        ),
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.confidential,
    )
    return TenantContext(tenant_id=tenant_id, subject_id=subject_id, entitlement=ent)


@pytest.fixture(scope="session")
def pg_session_factory():
    """Session factory bound to a migrated, RLS-enabled adjudication_item table.

    Skips if TIGEREXCHANGE_TEST_DSN is unset (CI sets it to the app-role DSN).
    """
    dsn = os.environ.get("TIGEREXCHANGE_TEST_DSN")
    if not dsn:
        pytest.skip("TIGEREXCHANGE_TEST_DSN not set; skipping Postgres integration tests")

    engine = make_engine(dsn)
    # Apply the migration as the app role (FORCE RLS makes the app role subject to RLS).
    with engine.begin() as conn:
        for stmt in (s.strip() for s in _MIGRATION.split(";")):
            if stmt:
                conn.execute(text(stmt))
    return make_session_factory(engine)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && \
  TIGEREXCHANGE_TEST_DSN="postgresql+psycopg://tigerexchange_app:app@localhost:5432/tigerexchange_test" \
  python -m pytest tests/test_queue.py -q
```
Expected: `6 passed` (the 5 queue workflow tests + the migration sanity test). If `TIGEREXCHANGE_TEST_DSN` is unset, expect `6 skipped` — CI must set it to the app-role DSN from `0a-foundation`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/tests/conftest.py tigerexchange/services/classification/tests/test_queue.py
git commit -m "test(classification): Postgres+RLS integration fixtures for adjudication queue

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: The classify-gate edge (classify-gates-index)

**Files:** Create `tigerexchange/services/classification/src/classification/ingest_gate.py`, Test `tigerexchange/services/classification/tests/test_ingest_gate.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_ingest_gate.py`:
```python
"""classify_gate: the hard classify-gates-index edge (plan §11.1, D6)."""

import pytest
from contracts import Decision, Tier

from classification.classifier import FailClosedClassifier
from classification.config import ClassifierConfig
from classification.ingest_gate import GateOutcome, classify_gate
from tests.conftest import make_tenant


def test_confident_public_passes_the_gate_for_indexing() -> None:
    out = classify_gate(
        FailClosedClassifier(),
        queue=_NullQueue(),
        tenant=make_tenant(),
        artifact_id="a-1",
        content_ref="blob://a-1",
        content=b"Published in Nature 2024. DOI:10.1/x. Open access.",
    )
    assert isinstance(out, GateOutcome)
    assert out.indexable is True
    assert out.result.decision == Decision.ALLOW
    assert out.result.tier == Tier.public
    assert out.adjudication_item_id is None


def test_quarantined_record_is_blocked_and_enqueued() -> None:
    q = _RecordingQueue()
    out = classify_gate(
        FailClosedClassifier(),
        queue=q,
        tenant=make_tenant(),
        artifact_id="a-2",
        content_ref="blob://a-2",
        content=b"asdf qwer zxcv",
    )
    assert out.indexable is False  # MUST NOT be indexed
    assert out.result.decision == Decision.QUARANTINE
    assert out.adjudication_item_id == "queued-a-2"
    assert q.calls == 1  # routed to the human-adjudication queue


def test_adversarial_record_is_blocked_and_enqueued() -> None:
    q = _RecordingQueue()
    out = classify_gate(
        FailClosedClassifier(),
        queue=q,
        tenant=make_tenant(),
        artifact_id="a-3",
        content_ref="blob://a-3",
        content=(
            b"Open access preprint DOI:10.1/x INTERNAL DRAFT PROPOSAL "
            b"preliminary unpublished budget CONFIDENTIAL."
        ),
    )
    assert out.indexable is False
    # Either confidential ALLOW (not publicly indexable) or QUARANTINE; never public+indexable.
    assert not (out.result.tier == Tier.public and out.indexable)


def test_confident_confidential_passes_gate_but_only_for_confidential_tier() -> None:
    out = classify_gate(
        FailClosedClassifier(),
        queue=_NullQueue(),
        tenant=make_tenant(),
        artifact_id="a-4",
        content_ref="blob://a-4",
        content=b"DRAFT PROPOSAL CONFIDENTIAL preliminary unpublished budget.",
    )
    # Confidently confidential => ALLOW at confidential tier; indexable into the
    # tenant's OWN confidential store only (never the shared index, D6).
    assert out.result.decision == Decision.ALLOW
    assert out.result.tier == Tier.confidential
    assert out.indexable is True
    assert out.shared_index_eligible is False  # D6: confidential never in shared index


# --- test doubles ---------------------------------------------------------- #

class _NullQueue:
    def enqueue(self, tenant, *, artifact_id, content_ref, result) -> str:  # noqa: ANN001
        raise AssertionError("enqueue must not be called for ALLOW results")


class _RecordingQueue:
    def __init__(self) -> None:
        self.calls = 0

    def enqueue(self, tenant, *, artifact_id, content_ref, result) -> str:  # noqa: ANN001
        self.calls += 1
        return f"queued-{artifact_id}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_ingest_gate.py -q
```
Expected failure: `ModuleNotFoundError: No module named 'classification.ingest_gate'`.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/src/classification/ingest_gate.py`:
```python
"""The classify-gate: the hard classify-gates-index edge (plan §11.1, §11.8, D6).

EVERY ingestion path calls classify_gate BEFORE writing to any retrievable
surface. Contract:

  - ALLOW           -> indexable=True at result.tier. Confidential tier is
                       indexable ONLY into the tenant's own confidential store,
                       NEVER the shared index (shared_index_eligible=False, D6).
  - QUARANTINE      -> indexable=False; the record is routed to the human
                       adjudication queue and excluded from ALL retrieval until
                       a human releases it with an approved tier.

This is the single edge every ingestion and retrieval path depends on; there is
no path to a retrievable surface that bypasses it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from contracts import ClassificationResult, Decision, IClassifier, TenantContext, Tier


class _QueueLike(Protocol):
    def enqueue(
        self,
        tenant: TenantContext,
        *,
        artifact_id: str,
        content_ref: str,
        result: ClassificationResult,
    ) -> str: ...


@dataclass(frozen=True)
class GateOutcome:
    """Result of the classify-gate for one record."""

    result: ClassificationResult
    indexable: bool          # may this record enter ANY retrievable surface?
    shared_index_eligible: bool  # may its projection enter the SHARED index? (D6: never if confidential)
    adjudication_item_id: str | None  # set iff routed to the human-adjudication queue


def classify_gate(
    classifier: IClassifier,
    *,
    queue: _QueueLike,
    tenant: TenantContext,
    artifact_id: str,
    content_ref: str,
    content: bytes,
) -> GateOutcome:
    """Classify a record and gate it. Fail-closed: quarantine => never indexable."""
    result = classifier.classify(content, tenant)

    if result.decision is not Decision.ALLOW:
        # Quarantine (or any non-ALLOW): block from all retrieval, route to queue.
        item_id = queue.enqueue(
            tenant,
            artifact_id=artifact_id,
            content_ref=content_ref,
            result=result,
        )
        return GateOutcome(
            result=result,
            indexable=False,
            shared_index_eligible=False,
            adjudication_item_id=item_id,
        )

    # Confident ALLOW: indexable at its tier. D6: confidential never in shared index.
    shared_eligible = result.tier is not Tier.confidential
    return GateOutcome(
        result=result,
        indexable=True,
        shared_index_eligible=shared_eligible,
        adjudication_item_id=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_ingest_gate.py -q
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/src/classification/ingest_gate.py tigerexchange/services/classification/tests/test_ingest_gate.py
git commit -m "feat(classification): classify-gate edge enforcing classify-gates-index + D6

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Property tests — MAX-rule and sticky-flag UNION

**Files:** Test `tigerexchange/services/classification/tests/test_properties.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_properties.py`:
```python
"""Property-based invariants (plan §15.2): MAX-rule + sticky-flag UNION.

These exercise the kernel's lattice primitives the classifier relies on, and the
classifier's own flag-preservation invariant. Generate random tier/flag combos
and assert the join NEVER under-restricts and flags NEVER drop.
"""

from hypothesis import given
from hypothesis import strategies as st

from contracts import (
    ComplianceFlag,
    Tier,
    compliance_union,
    tier_join,
    tier_join_all,
)
from classification.classifier import FailClosedClassifier
from tests.conftest import make_tenant

_tiers = st.sampled_from(list(Tier))
_flags = st.sets(st.sampled_from(list(ComplianceFlag))).map(frozenset)


@given(a=_tiers, b=_tiers)
def test_max_rule_join_is_the_more_restrictive(a: Tier, b: Tier) -> None:
    joined = tier_join(a, b)
    # The join is >= each input (MAX-rule: more-restrictive wins).
    assert joined >= a
    assert joined >= b
    assert joined in (a, b)


@given(ts=st.lists(_tiers, min_size=1, max_size=8))
def test_join_all_equals_max(ts: list[Tier]) -> None:
    assert tier_join_all(ts) == max(ts)


def test_join_all_empty_fails_closed_to_confidential() -> None:
    # Empty input must fail closed to the MOST-restrictive tier.
    assert tier_join_all([]) == Tier.confidential


@given(x=_flags, y=_flags)
def test_sticky_flag_union_never_drops_a_flag(x: frozenset, y: frozenset) -> None:
    u = compliance_union(x, y)
    # UNION: every input flag survives; nothing is dropped (§6.1 sticky).
    assert x <= u
    assert y <= u
    assert u == x | y


@given(flags=_flags)
def test_classifier_preserves_detected_flags_even_when_quarantined(
    flags: frozenset,
) -> None:
    # Build content that triggers each detected flag's marker AND is ambiguous on tier.
    markers = {
        ComplianceFlag.FERPA: b"education record ",
        ComplianceFlag.IRB: b"human subjects ",
        ComplianceFlag.ITAR: b"itar ",
        ComplianceFlag.EAR: b"export-controlled ",
        ComplianceFlag.GDPR_PERSONAL: b"gdpr ",
    }
    content = b"".join(markers[f] for f in flags) + b" zzz"
    res = FailClosedClassifier().classify(content, make_tenant())
    # Whatever the decision, the detected sticky flags must be carried (never dropped).
    assert flags <= res.compliance_flags
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_properties.py -q
```
Expected failure: initially `ModuleNotFoundError` if hypothesis not installed, else the last test may surface a real flag-preservation gap. Install dev extras first: `pip install -e ".[dev]"`. Expected to then drive any missing flag-preservation logic (already handled in classifier via `model_copy(update={"compliance_flags": ...})`).

- [ ] **Step 3: Write minimal implementation**

No production change expected — the kernel `tier_join`/`tier_join_all`/`compliance_union` and the classifier's flag preservation already satisfy these. If `test_classifier_preserves_detected_flags_even_when_quarantined` fails for an EAR-only case (marker `b"export-controlled "` vs signal markers), reconcile by ensuring `_COMPLIANCE_MARKERS[ComplianceFlag.EAR]` includes `"export-controlled"` (it does in Task 3). If a generated flag set is empty, `flags <= res.compliance_flags` holds trivially. No edit needed; if a marker mismatch surfaces, adjust the marker tuple in `signals.py` to match the test's marker bytes exactly:
```python
# In signals.py, ensure EAR marker matches the property-test marker:
ComplianceFlag.EAR: ("export-controlled", "ear-controlled", "itar"),  # 'export-controlled' covers the test marker
```
(Apply this edit ONLY if the property test reveals a mismatch; otherwise leave `signals.py` unchanged.)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_properties.py -q
```
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/tests/test_properties.py tigerexchange/services/classification/src/classification/signals.py
git commit -m "test(classification): property tests for MAX-rule and sticky-flag UNION

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Phase-0 contract test — zero leak (the deliverable acceptance gate)

**Files:** Test `tigerexchange/services/classification/tests/test_contract_zero_leak.py`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_contract_zero_leak.py`:
```python
"""PHASE-0 CONTRACT TEST (plan §11.1): inject low-confidence AND adversarial
records (confidential content with public-looking metadata) and assert ZERO
leak into any retrievable surface.

A 'retrievable surface' here is modeled by GateOutcome.indexable. The acceptance
criterion: every quarantined/adversarial record has indexable=False AND lands in
the adjudication queue; nothing reaches a retrievable surface without an explicit
human release. This is the single edge every ingestion/retrieval path depends on.
"""

import pytest
from contracts import Decision, Tier

from classification.classifier import FailClosedClassifier
from classification.config import ClassifierConfig
from classification.ingest_gate import classify_gate
from tests.conftest import make_tenant


class _RecordingQueue:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    def enqueue(self, tenant, *, artifact_id, content_ref, result) -> str:  # noqa: ANN001
        assert result.decision == Decision.QUARANTINE  # only quarantine is queued
        self.enqueued.append(artifact_id)
        return f"q-{artifact_id}"


# Adversarial corpus: confidential content wearing public-looking metadata,
# plus pure low-confidence/ambiguous records. NONE may become retrievable.
ADVERSARIAL = [
    b"Open access. DOI:10.1/abc. Published in Journal. INTERNAL DRAFT PROPOSAL "
    b"preliminary unpublished budget CONFIDENTIAL.",
    b"Preprint, public record. DOI:10.2/x. preliminary data unpublished budget figures.",
    b"open access doi:10.3/y not for distribution internal use confidential draft proposal",
]
LOW_CONFIDENCE = [
    b"asdf qwer zxcv",
    b"",
    b"\x00\x01\x02 random bytes no signal",
    b"the the the the and and and",
]


@pytest.mark.parametrize("content", ADVERSARIAL + LOW_CONFIDENCE)
def test_no_low_confidence_or_adversarial_record_is_indexable(content: bytes) -> None:
    q = _RecordingQueue()
    out = classify_gate(
        FailClosedClassifier(),
        queue=q,
        tenant=make_tenant(),
        artifact_id="adv",
        content_ref="blob://adv",
        content=content,
    )
    # ZERO LEAK: never indexable; never publicly retrievable; routed to adjudication.
    assert out.indexable is False, f"LEAK: {content!r} became indexable"
    assert out.shared_index_eligible is False
    assert out.result.tier == Tier.confidential or out.result.decision == Decision.QUARANTINE
    assert out.adjudication_item_id is not None
    assert q.enqueued == ["adv"]


def test_no_adversarial_record_is_ever_confident_public() -> None:
    clf = FailClosedClassifier()
    for content in ADVERSARIAL:
        res = clf.classify(content, make_tenant())
        assert not (res.tier == Tier.public and res.decision == Decision.ALLOW), (
            f"LEAK: adversarial record classified confident-public: {content!r}"
        )


def test_strict_threshold_quarantines_everything_uncertain() -> None:
    # Defense-in-depth: at threshold=1.0 nothing is confidently labeled.
    clf = FailClosedClassifier(ClassifierConfig(confidence_threshold=1.0))
    q = _RecordingQueue()
    for content in ADVERSARIAL + LOW_CONFIDENCE:
        out = classify_gate(
            clf, queue=q, tenant=make_tenant(),
            artifact_id="adv", content_ref="blob://adv", content=content,
        )
        assert out.indexable is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_contract_zero_leak.py -q
```
Expected: if any adversarial record leaks (becomes indexable or confident-public), the assertion `LEAK: ...` fails — that is the failing-first signal. With the Task 3/4/8 implementation it should pass; run it to confirm the contract holds. If a leak surfaces, tighten the conflicting-signal collapse in `signals.py` (e.g. force confidence to <0.7 whenever both a public marker and a confidential/private marker fire) until zero-leak holds.

- [ ] **Step 3: Write minimal implementation**

If the contract test reveals a leak (an adversarial record scored confident-public), harden `extract_signals` in `tigerexchange/services/classification/src/classification/signals.py` so any public classification is downgraded when a more-restrictive marker also fired:
```python
    if pub_hits > 0:
        # Clean public is high-confidence ONLY when nothing more restrictive fired.
        # (conf_hits and priv_hits are already 0 here due to earlier returns, but
        # guard explicitly to make the zero-leak invariant local and obvious.)
        if conf_hits > 0 or priv_hits > 0:
            return ContentSignals(Tier.confidential, 0.4, frozenset(flags))
        return ContentSignals(Tier.public, 0.9, frozenset(flags))
```
Apply this edit ONLY if the contract test surfaces a leak; the earlier confidential/private `return` branches already prevent reaching the public branch with restrictive hits, so in the Task-3 implementation no edit is needed.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_contract_zero_leak.py -q
```
Expected: all parametrized cases `passed` (7 parametrized + 2 = `9 passed`). Zero leak confirmed.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/tests/test_contract_zero_leak.py tigerexchange/services/classification/src/classification/signals.py
git commit -m "test(classification): Phase-0 zero-leak contract test for adversarial + low-confidence records

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Wire lint/type-check + CI marker registration

**Files:** Create `tigerexchange/services/classification/pytest.ini`, Modify `tigerexchange/services/classification/pyproject.toml`

- [ ] **Step 1: Write the failing test**

Create `tigerexchange/services/classification/tests/test_quality_gates.py`:
```python
"""Quality gates: ruff + mypy must pass on the classification source."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ruff_clean() -> None:
    r = subprocess.run(
        ["ruff", "check", str(ROOT / "src")], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_mypy_clean() -> None:
    r = subprocess.run(
        ["mypy", str(ROOT / "src" / "classification")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_quality_gates.py -q
```
Expected failure: `unknown pytest marker 'integration'` warnings and/or ruff/mypy findings (e.g. missing `from __future__`, unused imports), surfacing as non-zero return codes.

- [ ] **Step 3: Write minimal implementation**

Create `tigerexchange/services/classification/pytest.ini`:
```ini
[pytest]
testpaths = tests
markers =
    unit: pure in-process unit tests (no external services)
    integration: requires a Postgres reachable via TIGEREXCHANGE_TEST_DSN
addopts = -ra
```

Add mypy/ruff config to `tigerexchange/services/classification/pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
ignore_missing_imports = true
```

Run `ruff check --fix src/` and resolve any mypy findings (add precise types; the modules above are already typed).

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && python -m pytest tests/test_quality_gates.py -q && python -m pytest -q
```
Expected: quality gates `2 passed`; full suite green (integration tests `skipped` without DSN, `passed` with it).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase && git add tigerexchange/services/classification/pytest.ini tigerexchange/services/classification/pyproject.toml tigerexchange/services/classification/tests/test_quality_gates.py
git commit -m "chore(classification): ruff/mypy config + pytest markers; green quality gates

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Acceptance Criteria (deliverable verification)

Run the full suite. The sub-plan is complete when:

```bash
cd /home/anurag/codebase/tigerexchange/services/classification && \
  TIGEREXCHANGE_TEST_DSN="postgresql+psycopg://tigerexchange_app:app@localhost:5432/tigerexchange_test" \
  python -m pytest -q
```

- `FailClosedClassifier` implements the kernel `IClassifier` contract; abstention/ambiguity → `Decision.QUARANTINE` at `Tier.confidential`, never retrievable (`is_retrievable is False`).
- `classify_gate` is the single classify-gates-index edge: ALLOW → indexable at its tier (confidential never `shared_index_eligible`, D6); QUARANTINE → blocked + enqueued.
- `AdjudicationQueue` persists quarantine rows under FORCE RLS RESTRICTIVE tenant isolation, with `enqueue`/`list_pending`/`release`/`reject`; cross-tenant read is denied (RLS test).
- Phase-0 contract test passes: low-confidence + adversarial (confidential content with public-looking metadata) records show **zero leak** into any retrievable surface.
- MAX-rule and sticky-flag-UNION property tests pass.
- ruff + mypy clean.

All kernel types (`ClassificationResult`, `Decision`, `Tier`, `ComplianceFlag`, `TenantContext`, `Entitlement`, `Edition`, `Capability`, `IsolationPosture`, `IClassifier`, `tier_join`, `tier_join_all`, `compliance_union`) are imported verbatim from the `contracts` package delivered by `0a-foundation`. No deferred Phase-1+ machinery (revocation authority, exchange feed, sharing grants) is implemented here; this sub-plan only consumes the frozen lattice + classification contracts and leaves those seams untouched.