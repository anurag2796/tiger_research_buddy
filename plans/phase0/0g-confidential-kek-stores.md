I have full grounding now. Writing the complete plan.

# Confidential-Tier KEK/DEK Derivative-Store Encryption + Crypto-Shred + Table-B COGS Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Encrypt ALL confidential-tier derivative stores (Qdrant vectors, OpenSearch BM25 postings, Apache AGE graph nodes/edges, object storage, per-tenant caches, generated drafts, eval traces) under a per-tenant KEK/DEK so a single crypto-shred renders every searchable copy undecryptable, with tenant-CMK volume-key and delete-and-rebuild fallbacks, proven by a CI gate that returns zero decryptable hits across vector+BM25+graph after shred — and reconcile the Table-B steady-state confidential COGS from its own line items so the D7 ratio and the >=60% gross-margin gate are computed honestly.

**Architecture:** A `mod-confidential-crypto` module provides a per-tenant envelope-encryption authority (KEK wraps DEK; DEK encrypts derivative records) backed by a pluggable KMS interface (`InMemoryKms` for CI, cloud-KMS seam for prod), plus a `DerivativeStoreEncryptor` that every confidential derivative store routes writes/reads through, plus a `CryptoShredder` that destroys the wrapped DEK (and triggers volume-key revoke / delete-and-rebuild fallbacks for engines lacking customer-held-KEK at-rest). A `confidential-cogs` module encodes Table-B line items as data and recomputes the per-tenant COGS total, the D7 ratio, and the gross-margin gate from those line items. All confidentiality decisions flow through the canonical PEP (§4.2/D4): shred and re-key operations are PEP-authorized `DERIVE`/`EGRESS` actions, and the post-shred search runs through the broker so the test exercises the real retrieval chokepoint.

**Tech Stack:** Python 3.11+, Pydantic v2, `cryptography` (AES-256-GCM envelope), the canonical `contracts` kernel package, pytest, ruff, mypy. KMS is an interface (in-memory for CI; cloud-KMS per-tenant + CloudHSM HYOK is the prod seam, NOT built in Phase-0). Qdrant/OpenSearch/AGE are represented by thin in-cell adapter seams whose at-rest reality (no customer-held-KEK) is encoded as the documented fallback path.

**Depends on:** `0a-foundation` (monorepo scaffold, `TenantContext`, FastAPI app, CI), `0c-pep-broker-chokepoint` (the single PEP + data-access broker; shred/search route through it), `0f-model-router` (router/eval path that produces confidential derivatives — eval traces are folded into the shred contract).

---

## File Structure

| File | Created/Modified | Single responsibility |
|---|---|---|
| `tigerexchange/packages/mod-confidential-crypto/pyproject.toml` | Create | Package metadata + import-linter contract (no feature/persistence deps beyond `contracts` + `cryptography`) |
| `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py` | Create | Public import surface for the crypto module |
| `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/keys.py` | Create | `DekGranularity`, `WrappedDek`, `KeyState`, `ShredReceipt` value objects |
| `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/kms.py` | Create | `IKms` protocol + `InMemoryKms` (CI) implementing KEK wrap/unwrap/destroy |
| `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/envelope.py` | Create | `EnvelopeAuthority`: per-tenant DEK lifecycle (provision, wrap, rotate, encrypt/decrypt records) |
| `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/derivative_store.py` | Create | `DerivativeKind` enum, `IConfidentialDerivativeStore` protocol, `EncryptedDerivativeStore` wrapper, `VolumeKeyFallbackStore`, `DeleteAndRebuildStore` |
| `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/shredder.py` | Create | `CryptoShredder`: PEP-gated KEK shred across all registered derivative stores + fallbacks, emits audit + `ShredReceipt` |
| `tigerexchange/packages/mod-confidential-crypto/tests/test_keys.py` | Create | Tests for key value objects + granularity invariants |
| `tigerexchange/packages/mod-confidential-crypto/tests/test_kms.py` | Create | Tests for `InMemoryKms` wrap/unwrap/destroy fail-closed behavior |
| `tigerexchange/packages/mod-confidential-crypto/tests/test_envelope.py` | Create | Tests for DEK provision/rotate/encrypt/decrypt + per-record granularity |
| `tigerexchange/packages/mod-confidential-crypto/tests/test_derivative_store.py` | Create | Tests for encrypted-store wrapper + volume-key + delete-and-rebuild fallbacks |
| `tigerexchange/packages/mod-confidential-crypto/tests/test_shredder.py` | Create | Tests for PEP-gated shred + audit emission + receipt |
| `tigerexchange/packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py` | Create | **CI gate (§15.2/§11.3b):** post-KEK-shred search across vector+BM25+graph returns zero decryptable hits |
| `tigerexchange/packages/mod-confidential-cogs/pyproject.toml` | Create | Package metadata (pure data + arithmetic; `contracts` only) |
| `tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/__init__.py` | Create | Public import surface for the COGS module |
| `tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/cogs_model.py` | Create | `CogsLineItem`, `GpuAmortization`, `CogsTable`, reconciliation + D7-ratio + margin-gate functions |
| `tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/table_b.py` | Create | Frozen Table-B steady-state confidential line items (§16.1) as data |
| `tigerexchange/packages/mod-confidential-cogs/tests/test_cogs_model.py` | Create | Tests for line-item sum, GPU-density amortization, D7 ratio, margin gate |
| `tigerexchange/packages/mod-confidential-cogs/tests/test_table_b_reconciliation.py` | Create | **Gate (Finding 10/11):** Table-B line items sum to stated total; D7 ratio + >=60% margin recomputed honestly |
| `tigerexchange/ci/import_linter_confidential.toml` | Create | import-linter contract pinning kernel isolation for both new packages (CI gate) |

---

## Tasks

### Task 1: Key value objects (granularity, wrapped DEK, key state, shred receipt)

**Files:**
- Create `tigerexchange/packages/mod-confidential-crypto/pyproject.toml`
- Create `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/keys.py`
- Create `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py`
- Test `tigerexchange/packages/mod-confidential-crypto/tests/test_keys.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-crypto/tests/test_keys.py
"""Key value-object invariants (plan §11.3b)."""

import pytest

from confidential_crypto.keys import (
    DekGranularity,
    KeyState,
    ShredReceipt,
    WrappedDek,
)


def test_dek_granularity_values_are_stable_wire_strings():
    assert DekGranularity.PER_TENANT.value == "per-tenant"
    assert DekGranularity.PER_RECORD.value == "per-record"


def test_wrapped_dek_is_frozen():
    w = WrappedDek(
        dek_id="dek-1",
        tenant_id="tenantA",
        kek_id="kek-tenantA",
        granularity=DekGranularity.PER_TENANT,
        ciphertext=b"wrapped-bytes",
        record_id=None,
    )
    with pytest.raises(Exception):
        w.dek_id = "dek-2"  # frozen models reject mutation


def test_per_record_dek_requires_record_id():
    with pytest.raises(ValueError):
        WrappedDek(
            dek_id="dek-1",
            tenant_id="tenantA",
            kek_id="kek-tenantA",
            granularity=DekGranularity.PER_RECORD,
            ciphertext=b"x",
            record_id=None,  # per-record MUST bind a record_id
        )


def test_per_tenant_dek_forbids_record_id():
    with pytest.raises(ValueError):
        WrappedDek(
            dek_id="dek-1",
            tenant_id="tenantA",
            kek_id="kek-tenantA",
            granularity=DekGranularity.PER_TENANT,
            ciphertext=b"x",
            record_id="rec-99",  # per-tenant MUST NOT bind a record
        )


def test_key_state_default_is_active_and_shred_transition():
    assert KeyState.ACTIVE.value == "active"
    assert KeyState.SHREDDED.value == "shredded"


def test_shred_receipt_records_what_was_destroyed():
    r = ShredReceipt(
        tenant_id="tenantA",
        kek_id="kek-tenantA",
        shredded_dek_ids=("dek-1", "dek-2"),
        volume_keys_revoked=("vol-qdrant",),
        rebuilt_stores=("graph-age",),
        residual_window_seconds=900,
    )
    assert r.tenant_id == "tenantA"
    assert "dek-1" in r.shredded_dek_ids
    assert r.residual_window_seconds == 900
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_keys.py -q
```
Expected: `ModuleNotFoundError: No module named 'confidential_crypto'` (package not yet created).

- [ ] **Step 3: Write minimal implementation**

```toml
# tigerexchange/packages/mod-confidential-crypto/pyproject.toml
[project]
name = "tigerexchange-mod-confidential-crypto"
version = "0.0.0"
description = "Per-tenant KEK/DEK envelope encryption + crypto-shred for ALL confidential derivative stores (plan §11.3b)."
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6,<3",
    "cryptography>=42,<46",
    "tigerexchange-contracts",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/confidential_crypto"]
```

```python
# tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/keys.py
"""Key lifecycle value objects (plan §11.3b).

Frozen value objects for the envelope-encryption authority: a DEK (per-tenant
default, per-record for the highest-isolation Confidential-Sovereign edition)
is wrapped by the tenant KEK in KMS. Crypto-shred destroys the KEK/wrapping so
the ciphertext (and every searchable derivative) becomes undecryptable.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class DekGranularity(StrEnum):
    """DEK granularity (plan §11.3b).

    PER_TENANT is the default (one envelope key per confidential tenant).
    PER_RECORD is offered for the Confidential-Sovereign edition where
    per-subject crypto-erasure granularity is required.
    """

    PER_TENANT = "per-tenant"
    PER_RECORD = "per-record"


class KeyState(StrEnum):
    """Lifecycle state of a key in KMS."""

    ACTIVE = "active"
    SHREDDED = "shredded"


class WrappedDek(BaseModel):
    """A DEK ciphertext wrapped under the tenant KEK (plan §11.3b)."""

    model_config = ConfigDict(frozen=True)

    dek_id: str
    tenant_id: str
    kek_id: str
    granularity: DekGranularity
    ciphertext: bytes
    record_id: str | None = None

    @model_validator(mode="after")
    def _record_id_matches_granularity(self) -> "WrappedDek":
        if self.granularity is DekGranularity.PER_RECORD and self.record_id is None:
            raise ValueError("per-record DEK requires a record_id (§11.3b).")
        if self.granularity is DekGranularity.PER_TENANT and self.record_id is not None:
            raise ValueError("per-tenant DEK must not bind a record_id (§11.3b).")
        return self


class ShredReceipt(BaseModel):
    """Auditable proof of what a crypto-shred destroyed (plan §11.3b, §11.7)."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    kek_id: str
    shredded_dek_ids: tuple[str, ...]
    volume_keys_revoked: tuple[str, ...] = ()
    rebuilt_stores: tuple[str, ...] = ()
    # Stated residual window for delete-and-rebuild fallback (time-to-rebuild).
    residual_window_seconds: int = 0
```

```python
# tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py
"""mod-confidential-crypto public surface (plan §11.3b)."""

from confidential_crypto.keys import (
    DekGranularity,
    KeyState,
    ShredReceipt,
    WrappedDek,
)

__all__ = ["DekGranularity", "KeyState", "ShredReceipt", "WrappedDek"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && pip install -e . -q && python -m pytest tests/test_keys.py -q
```
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-crypto && git commit -m "feat(confidential-crypto): key lifecycle value objects (WrappedDek/ShredReceipt, §11.3b)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: KMS interface + in-memory KEK authority (wrap / unwrap / destroy)

**Files:**
- Create `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/kms.py`
- Modify `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py`
- Test `tigerexchange/packages/mod-confidential-crypto/tests/test_kms.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-crypto/tests/test_kms.py
"""InMemoryKms wrap/unwrap/destroy (plan §11.3b).

The CI KMS stands in for cloud-KMS-per-tenant + CloudHSM HYOK (the prod seam,
NOT built Phase-0). Destroy is the crypto-shred primitive: once the KEK is
destroyed, unwrap MUST fail closed -> the wrapped DEK is undecryptable forever.
"""

import pytest

from confidential_crypto.kms import InMemoryKms, KmsKeyDestroyedError


def test_create_and_wrap_unwrap_roundtrip():
    kms = InMemoryKms()
    kms.create_kek("kek-tenantA")
    dek = b"0123456789abcdef0123456789abcdef"  # 32-byte AES-256 key
    wrapped = kms.wrap("kek-tenantA", dek)
    assert wrapped != dek
    assert kms.unwrap("kek-tenantA", wrapped) == dek


def test_unwrap_with_unknown_kek_fails_closed():
    kms = InMemoryKms()
    with pytest.raises(KmsKeyDestroyedError):
        kms.unwrap("kek-missing", b"anything")


def test_destroy_makes_unwrap_fail_closed_forever():
    kms = InMemoryKms()
    kms.create_kek("kek-tenantA")
    wrapped = kms.wrap("kek-tenantA", b"0123456789abcdef0123456789abcdef")
    kms.destroy_kek("kek-tenantA")
    with pytest.raises(KmsKeyDestroyedError):
        kms.unwrap("kek-tenantA", wrapped)


def test_destroy_is_idempotent_and_recorded():
    kms = InMemoryKms()
    kms.create_kek("kek-tenantA")
    kms.destroy_kek("kek-tenantA")
    kms.destroy_kek("kek-tenantA")  # idempotent
    assert kms.is_destroyed("kek-tenantA") is True


def test_rewrap_under_rotated_kek_does_not_touch_plaintext_data():
    # KEK rotation re-wraps DEK cheaply without re-encrypting data (§11.3b).
    kms = InMemoryKms()
    kms.create_kek("kek-v1")
    kms.create_kek("kek-v2")
    dek = b"0123456789abcdef0123456789abcdef"
    w1 = kms.wrap("kek-v1", dek)
    w2 = kms.rewrap(src_kek_id="kek-v1", dst_kek_id="kek-v2", wrapped=w1)
    assert kms.unwrap("kek-v2", w2) == dek
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_kms.py -q
```
Expected: `ImportError: cannot import name 'InMemoryKms' from 'confidential_crypto.kms'` (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/kms.py
"""KMS seam: per-tenant KEK wrap/unwrap/destroy (plan §11.3b, §12 Secrets/keys).

IKms is the interface; InMemoryKms is the CI implementation. Production uses
cloud-KMS-per-tenant + CloudHSM (HYOK) behind the SAME interface — that prod
adapter is NOT built in Phase-0 (the sandbox uses de-identified data, §16.1
Table A). destroy_kek() is the crypto-shred primitive: it is irreversible and
unwrap fails closed afterward.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class KmsKeyDestroyedError(Exception):
    """Raised when unwrapping under a missing/destroyed KEK (fail-closed shred)."""


@runtime_checkable
class IKms(Protocol):
    """Key-management seam (plan §12). Prod = cloud-KMS/HYOK; CI = in-memory."""

    def create_kek(self, kek_id: str) -> None: ...
    def wrap(self, kek_id: str, dek: bytes) -> bytes: ...
    def unwrap(self, kek_id: str, wrapped: bytes) -> bytes: ...
    def rewrap(self, src_kek_id: str, dst_kek_id: str, wrapped: bytes) -> bytes: ...
    def destroy_kek(self, kek_id: str) -> None: ...
    def is_destroyed(self, kek_id: str) -> bool: ...


class InMemoryKms:
    """In-process KEK store for CI (AES-256-GCM wrapping). NOT for prod."""

    _NONCE_LEN = 12

    def __init__(self) -> None:
        self._keks: dict[str, bytes] = {}
        self._destroyed: set[str] = set()

    def create_kek(self, kek_id: str) -> None:
        if kek_id in self._destroyed:
            raise KmsKeyDestroyedError(f"KEK {kek_id} was destroyed; cannot recreate.")
        self._keks.setdefault(kek_id, AESGCM.generate_key(bit_length=256))

    def _require(self, kek_id: str) -> bytes:
        if kek_id in self._destroyed or kek_id not in self._keks:
            raise KmsKeyDestroyedError(f"KEK {kek_id} is destroyed or unknown (fail-closed).")
        return self._keks[kek_id]

    def wrap(self, kek_id: str, dek: bytes) -> bytes:
        key = self._require(kek_id)
        nonce = os.urandom(self._NONCE_LEN)
        return nonce + AESGCM(key).encrypt(nonce, dek, kek_id.encode())

    def unwrap(self, kek_id: str, wrapped: bytes) -> bytes:
        key = self._require(kek_id)
        nonce, ct = wrapped[: self._NONCE_LEN], wrapped[self._NONCE_LEN :]
        return AESGCM(key).decrypt(nonce, ct, kek_id.encode())

    def rewrap(self, src_kek_id: str, dst_kek_id: str, wrapped: bytes) -> bytes:
        return self.wrap(dst_kek_id, self.unwrap(src_kek_id, wrapped))

    def destroy_kek(self, kek_id: str) -> None:
        self._destroyed.add(kek_id)
        self._keks.pop(kek_id, None)  # irreversible

    def is_destroyed(self, kek_id: str) -> bool:
        return kek_id in self._destroyed
```

```python
# tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py
"""mod-confidential-crypto public surface (plan §11.3b)."""

from confidential_crypto.keys import (
    DekGranularity,
    KeyState,
    ShredReceipt,
    WrappedDek,
)
from confidential_crypto.kms import IKms, InMemoryKms, KmsKeyDestroyedError

__all__ = [
    "DekGranularity",
    "KeyState",
    "ShredReceipt",
    "WrappedDek",
    "IKms",
    "InMemoryKms",
    "KmsKeyDestroyedError",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_kms.py -q
```
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-crypto && git commit -m "feat(confidential-crypto): InMemoryKms KEK wrap/unwrap/destroy seam (§11.3b)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Envelope authority (per-tenant DEK provision, rotate, encrypt/decrypt records)

**Files:**
- Create `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/envelope.py`
- Modify `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py`
- Test `tigerexchange/packages/mod-confidential-crypto/tests/test_envelope.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-crypto/tests/test_envelope.py
"""EnvelopeAuthority: DEK lifecycle + record crypto (plan §11.3b)."""

import pytest

from confidential_crypto.envelope import EnvelopeAuthority
from confidential_crypto.keys import DekGranularity
from confidential_crypto.kms import InMemoryKms, KmsKeyDestroyedError


def _authority(granularity=DekGranularity.PER_TENANT):
    kms = InMemoryKms()
    return EnvelopeAuthority(kms=kms, tenant_id="tenantA", granularity=granularity), kms


def test_provision_then_encrypt_decrypt_roundtrip_per_tenant():
    auth, _ = _authority()
    auth.provision()
    ct = auth.encrypt_record(b"confidential proposal section", record_id="rec-1")
    assert ct != b"confidential proposal section"
    assert auth.decrypt_record(ct, record_id="rec-1") == b"confidential proposal section"


def test_kek_destroy_makes_every_record_undecryptable():
    auth, kms = _authority()
    auth.provision()
    ct = auth.encrypt_record(b"secret", record_id="rec-1")
    kms.destroy_kek(auth.kek_id)
    auth.forget_unwrapped()  # drop any in-process cached DEK on shred
    with pytest.raises(KmsKeyDestroyedError):
        auth.decrypt_record(ct, record_id="rec-1")


def test_per_record_granularity_uses_distinct_dek_per_record():
    auth, _ = _authority(DekGranularity.PER_RECORD)
    auth.provision()
    c1 = auth.encrypt_record(b"subject-1 data", record_id="subj-1")
    c2 = auth.encrypt_record(b"subject-2 data", record_id="subj-2")
    # Distinct per-record DEKs -> two wrapped DEKs tracked
    assert len(auth.wrapped_dek_ids()) == 2
    assert auth.decrypt_record(c1, record_id="subj-1") == b"subject-1 data"


def test_per_record_shred_of_one_record_leaves_others_decryptable():
    auth, _ = _authority(DekGranularity.PER_RECORD)
    auth.provision()
    c1 = auth.encrypt_record(b"subj-1", record_id="subj-1")
    c2 = auth.encrypt_record(b"subj-2", record_id="subj-2")
    auth.shred_record("subj-1")  # per-subject erasure (§11.7)
    with pytest.raises(KmsKeyDestroyedError):
        auth.decrypt_record(c1, record_id="subj-1")
    assert auth.decrypt_record(c2, record_id="subj-2") == b"subj-2"


def test_rotate_dek_reencrypts_data_and_old_ciphertext_still_old_dek():
    auth, _ = _authority()
    auth.provision()
    ct_v1 = auth.encrypt_record(b"data", record_id="rec-1")
    auth.rotate_dek()
    ct_v2 = auth.encrypt_record(b"data", record_id="rec-1")
    assert ct_v1 != ct_v2  # new DEK -> new ciphertext
    assert auth.decrypt_record(ct_v2, record_id="rec-1") == b"data"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_envelope.py -q
```
Expected: `ModuleNotFoundError: No module named 'confidential_crypto.envelope'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/envelope.py
"""Per-tenant envelope-encryption authority (plan §11.3b).

Holds one wrapped DEK per tenant (PER_TENANT default), or one wrapped DEK per
record (PER_RECORD, Confidential-Sovereign edition). The DEK encrypts derivative
records with AES-256-GCM. KEK destroy (crypto-shred) renders every ciphertext
undecryptable. Per-record shred destroys one subject's DEK (per-subject erasure,
§11.7). Rotation generates a fresh DEK; KEK rotation is handled in KMS.rewrap.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from confidential_crypto.keys import DekGranularity, WrappedDek
from confidential_crypto.kms import IKms

_NONCE_LEN = 12


class EnvelopeAuthority:
    """Manages a confidential tenant's DEK(s) and record-level crypto (§11.3b)."""

    def __init__(self, kms: IKms, tenant_id: str, granularity: DekGranularity) -> None:
        self._kms = kms
        self.tenant_id = tenant_id
        self.granularity = granularity
        self.kek_id = f"kek-{tenant_id}"
        # record_key None == the single per-tenant DEK; else per-record DEK id.
        self._wrapped: dict[str | None, WrappedDek] = {}
        self._cache: dict[str | None, bytes] = {}  # in-process unwrapped DEK cache

    def provision(self) -> None:
        self._kms.create_kek(self.kek_id)
        if self.granularity is DekGranularity.PER_TENANT:
            self._provision_dek(None)

    def _dek_key(self, record_id: str | None) -> str | None:
        return record_id if self.granularity is DekGranularity.PER_RECORD else None

    def _provision_dek(self, record_id: str | None) -> bytes:
        dek = AESGCM.generate_key(bit_length=256)
        suffix = record_id if record_id is not None else "tenant"
        wrapped = WrappedDek(
            dek_id=f"dek-{self.tenant_id}-{suffix}",
            tenant_id=self.tenant_id,
            kek_id=self.kek_id,
            granularity=self.granularity,
            ciphertext=self._kms.wrap(self.kek_id, dek),
            record_id=record_id if self.granularity is DekGranularity.PER_RECORD else None,
        )
        self._wrapped[record_id] = wrapped
        self._cache[record_id] = dek
        return dek

    def _dek(self, record_id: str | None) -> bytes:
        key = self._dek_key(record_id)
        if key in self._cache:
            return self._cache[key]
        if key not in self._wrapped:
            return self._provision_dek(key)
        dek = self._kms.unwrap(self.kek_id, self._wrapped[key].ciphertext)
        self._cache[key] = dek
        return dek

    def encrypt_record(self, plaintext: bytes, record_id: str) -> bytes:
        dek = self._dek(record_id)
        nonce = os.urandom(_NONCE_LEN)
        return nonce + AESGCM(dek).encrypt(nonce, plaintext, record_id.encode())

    def decrypt_record(self, ciphertext: bytes, record_id: str) -> bytes:
        dek = self._dek(record_id)
        nonce, ct = ciphertext[:_NONCE_LEN], ciphertext[_NONCE_LEN:]
        return AESGCM(dek).decrypt(nonce, ct, record_id.encode())

    def rotate_dek(self) -> None:
        """Fresh per-tenant DEK on a fixed cadence / membership change (§11.3b)."""
        if self.granularity is DekGranularity.PER_TENANT:
            self._provision_dek(None)

    def shred_record(self, record_id: str) -> None:
        """Per-subject crypto-erasure: destroy that record's DEK (§11.7)."""
        if self.granularity is not DekGranularity.PER_RECORD:
            raise ValueError("per-record shred requires PER_RECORD granularity (§11.3b).")
        # Per-record DEKs are wrapped under per-record sub-KEKs in prod; in CI we
        # model destruction by dropping the wrapped DEK and forcing fail-closed.
        self._wrapped.pop(record_id, None)
        self._cache.pop(record_id, None)
        self._kms.destroy_kek(self.kek_id) if False else None
        # Force fail-closed on subsequent decrypt of the shredded record:
        self._shredded_records.add(record_id)

    def forget_unwrapped(self) -> None:
        """Drop in-process DEK cache (called on KEK shred)."""
        self._cache.clear()

    def wrapped_dek_ids(self) -> tuple[str, ...]:
        return tuple(w.dek_id for w in self._wrapped.values())

    _shredded_records: set[str] = set()
```

Fix the per-record shred to fail closed deterministically by checking the shredded set in `_dek`. Replace the `_dek` method and class init so shred is correct:

```python
# Replace __init__ tail and _dek in envelope.py:
```
Update `__init__` to add `self._shredded_records: set[str] = set()` (instance-level), remove the class-level `_shredded_records`, and guard `_dek`:

```python
    def __init__(self, kms: IKms, tenant_id: str, granularity: DekGranularity) -> None:
        self._kms = kms
        self.tenant_id = tenant_id
        self.granularity = granularity
        self.kek_id = f"kek-{tenant_id}"
        self._wrapped: dict[str | None, WrappedDek] = {}
        self._cache: dict[str | None, bytes] = {}
        self._shredded_records: set[str] = set()

    def _dek(self, record_id: str | None) -> bytes:
        from confidential_crypto.kms import KmsKeyDestroyedError
        if record_id is not None and record_id in self._shredded_records:
            raise KmsKeyDestroyedError(f"record {record_id} DEK shredded (§11.7).")
        key = self._dek_key(record_id)
        if key in self._cache:
            return self._cache[key]
        if key not in self._wrapped:
            return self._provision_dek(key)
        dek = self._kms.unwrap(self.kek_id, self._wrapped[key].ciphertext)
        self._cache[key] = dek
        return dek
```

And simplify `shred_record`:

```python
    def shred_record(self, record_id: str) -> None:
        """Per-subject crypto-erasure: destroy that record's DEK (§11.7)."""
        if self.granularity is not DekGranularity.PER_RECORD:
            raise ValueError("per-record shred requires PER_RECORD granularity (§11.3b).")
        self._wrapped.pop(record_id, None)
        self._cache.pop(record_id, None)
        self._shredded_records.add(record_id)
```

Update `__init__.py` to export `EnvelopeAuthority`:

```python
# append to imports/__all__ in confidential_crypto/__init__.py
from confidential_crypto.envelope import EnvelopeAuthority
# add "EnvelopeAuthority" to __all__
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_envelope.py -q
```
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-crypto && git commit -m "feat(confidential-crypto): EnvelopeAuthority per-tenant/per-record DEK crypto (§11.3b/§11.7)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Derivative-store wrapper + volume-key and delete-and-rebuild fallbacks

**Files:**
- Create `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/derivative_store.py`
- Modify `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py`
- Test `tigerexchange/packages/mod-confidential-crypto/tests/test_derivative_store.py`

This task enumerates EVERY confidential derivative kind including the generated-draft and eval-trace artifacts the convergence report adds to §11.3b.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-crypto/tests/test_derivative_store.py
"""Confidential derivative stores: encrypted wrapper + fallbacks (plan §11.3b).

Enumerates ALL confidential derivative kinds: vector (Qdrant), BM25 postings
(OpenSearch), graph nodes/edges (AGE), object storage, per-tenant cache, AND
the convergence-report additions: generated drafts + draft history, eval traces.
"""

import pytest

from confidential_crypto.derivative_store import (
    DeleteAndRebuildStore,
    DerivativeKind,
    EncryptedDerivativeStore,
    VolumeKeyFallbackStore,
)
from confidential_crypto.envelope import EnvelopeAuthority
from confidential_crypto.keys import DekGranularity
from confidential_crypto.kms import InMemoryKms, KmsKeyDestroyedError


def _auth():
    kms = InMemoryKms()
    a = EnvelopeAuthority(kms=kms, tenant_id="tenantA", granularity=DekGranularity.PER_TENANT)
    a.provision()
    return a, kms


def test_all_required_derivative_kinds_enumerated():
    kinds = {k.value for k in DerivativeKind}
    assert kinds == {
        "vector",            # Qdrant
        "bm25-postings",     # OpenSearch
        "graph",             # Apache AGE nodes/edges
        "object",            # object storage
        "cache",             # per-tenant cache
        "generated-draft",   # convergence-report: highest-value confidential artifact
        "eval-trace",        # convergence-report: RAGAS context/answer traces
    }


def test_encrypted_store_roundtrip_then_shred_blinds_reads():
    auth, kms = _auth()
    store = EncryptedDerivativeStore(DerivativeKind.VECTOR, auth)
    store.put("rec-1", b"[0.12, 0.98, ...]")  # embedding bytes
    assert store.get("rec-1") == b"[0.12, 0.98, ...]"
    kms.destroy_kek(auth.kek_id)
    auth.forget_unwrapped()
    with pytest.raises(KmsKeyDestroyedError):
        store.get("rec-1")


def test_volume_key_fallback_marks_unreadable_after_shred():
    # Engines lacking customer-held-KEK at-rest (Qdrant/OpenSearch/AGE today):
    # the whole volume is bound to a tenant-CMK; KEK shred -> on-disk unreadable.
    auth, kms = _auth()
    store = VolumeKeyFallbackStore(DerivativeKind.GRAPH, auth, volume_key_id="vol-age")
    store.put("edge-1", b"(:Author)-[:WROTE]->(:Paper)")
    assert store.get("edge-1") == b"(:Author)-[:WROTE]->(:Paper)"
    kms.destroy_kek(auth.kek_id)
    auth.forget_unwrapped()
    with pytest.raises(KmsKeyDestroyedError):
        store.get("edge-1")
    assert store.volume_key_id == "vol-age"


def test_delete_and_rebuild_fallback_states_residual_window():
    auth, _ = _auth()
    store = DeleteAndRebuildStore(
        DerivativeKind.BM25_POSTINGS, auth, residual_window_seconds=600
    )
    store.put("doc-1", b"posting-list")
    assert store.get("doc-1") == b"posting-list"
    store.delete_and_rebuild()  # on KEK shred / erasure
    assert store.is_unavailable() is True
    assert store.residual_window_seconds == 600
    with pytest.raises(KeyError):
        store.get("doc-1")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_derivative_store.py -q
```
Expected: `ModuleNotFoundError: No module named 'confidential_crypto.derivative_store'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/derivative_store.py
"""Confidential derivative stores under tenant KEK/DEK (plan §11.3b).

EVERY confidential-tier derivative is encrypted under the tenant DEK so KEK
crypto-shred renders it undecryptable. Three enforced postures:
  - EncryptedDerivativeStore: per-record DEK encryption (engine supports
    customer-held-KEK at-rest).
  - VolumeKeyFallbackStore: tenant-CMK volume encryption (LUKS/dm-crypt/cloud
    block CMK) for engines WITHOUT customer-held-KEK at-rest (the common
    Qdrant/OpenSearch/AGE reality). Modeled in CI by binding records to the
    tenant DEK at the store boundary; in prod the binding is the volume key.
  - DeleteAndRebuildStore: for any derivative not covered above; on shred the
    index is deleted+rebuilt from the (now-undecryptable) source with a STATED
    residual window.

DerivativeKind enumerates all confidential derivatives INCLUDING generated
drafts/draft-history and eval traces (convergence-report additions to §11.3b).
"""

from __future__ import annotations

from enum import StrEnum

from confidential_crypto.envelope import EnvelopeAuthority


class DerivativeKind(StrEnum):
    """Every confidential-tier derivative store covered by crypto-shred (§11.3b)."""

    VECTOR = "vector"
    BM25_POSTINGS = "bm25-postings"
    GRAPH = "graph"
    OBJECT = "object"
    CACHE = "cache"
    GENERATED_DRAFT = "generated-draft"
    EVAL_TRACE = "eval-trace"


class IConfidentialDerivativeStore:
    """Base contract: every confidential derivative routes through DEK crypto."""

    def __init__(self, kind: DerivativeKind, authority: EnvelopeAuthority) -> None:
        self.kind = kind
        self._auth = authority
        self._blob: dict[str, bytes] = {}

    def put(self, record_id: str, plaintext: bytes) -> None:
        self._blob[record_id] = self._auth.encrypt_record(plaintext, record_id=record_id)

    def get(self, record_id: str) -> bytes:
        return self._auth.decrypt_record(self._blob[record_id], record_id=record_id)


class EncryptedDerivativeStore(IConfidentialDerivativeStore):
    """Customer-held-KEK at-rest posture (engine supports it)."""


class VolumeKeyFallbackStore(IConfidentialDerivativeStore):
    """tenant-CMK volume-encryption fallback (§11.3b path a)."""

    def __init__(
        self, kind: DerivativeKind, authority: EnvelopeAuthority, volume_key_id: str
    ) -> None:
        super().__init__(kind, authority)
        self.volume_key_id = volume_key_id


class DeleteAndRebuildStore(IConfidentialDerivativeStore):
    """Delete-and-rebuild fallback with a stated residual window (§11.3b path b)."""

    def __init__(
        self,
        kind: DerivativeKind,
        authority: EnvelopeAuthority,
        residual_window_seconds: int,
    ) -> None:
        super().__init__(kind, authority)
        self.residual_window_seconds = residual_window_seconds
        self._unavailable = False

    def delete_and_rebuild(self) -> None:
        self._blob.clear()
        self._unavailable = True

    def is_unavailable(self) -> bool:
        return self._unavailable
```

Update `__init__.py` to export the new symbols:

```python
# append imports + __all__ entries in confidential_crypto/__init__.py
from confidential_crypto.derivative_store import (
    DeleteAndRebuildStore,
    DerivativeKind,
    EncryptedDerivativeStore,
    IConfidentialDerivativeStore,
    VolumeKeyFallbackStore,
)
# add: "DeleteAndRebuildStore", "DerivativeKind", "EncryptedDerivativeStore",
#      "IConfidentialDerivativeStore", "VolumeKeyFallbackStore"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_derivative_store.py -q
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-crypto && git commit -m "feat(confidential-crypto): derivative-store encryption + volume-key/delete-rebuild fallbacks (§11.3b)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: PEP-gated CryptoShredder across all registered stores

**Files:**
- Create `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/shredder.py`
- Modify `tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/__init__.py`
- Test `tigerexchange/packages/mod-confidential-crypto/tests/test_shredder.py`

The shred operation is a PEP-authorized action (D4): it constructs a `PepRequest(action=EGRESS, required_capability=CONFIDENTIAL_WORKSPACE)` and proceeds only on `Decision.ALLOW`, emitting an `AuditEvent`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-crypto/tests/test_shredder.py
"""CryptoShredder: PEP-gated KEK shred across all stores (plan §11.3b, D4)."""

import pytest

from contracts import (
    AuditEvent,
    Capability,
    Decision,
    Edition,
    Entitlement,
    IsolationPosture,
    PepRequest,
    PepResponse,
    Tier,
    TenantContext,
)

from confidential_crypto.derivative_store import (
    DerivativeKind,
    EncryptedDerivativeStore,
)
from confidential_crypto.envelope import EnvelopeAuthority
from confidential_crypto.keys import DekGranularity
from confidential_crypto.kms import InMemoryKms, KmsKeyDestroyedError
from confidential_crypto.shredder import CryptoShredder


class _AllowPep:
    def authorize(self, request: PepRequest) -> PepResponse:
        return PepResponse(
            request_id=request.request_id,
            decision=Decision.ALLOW,
            effective_tier=Tier.confidential,
        )


class _DenyPep:
    def authorize(self, request: PepRequest) -> PepResponse:
        return PepResponse(
            request_id=request.request_id,
            decision=Decision.DENY,
            effective_tier=Tier.confidential,
            reason="not entitled",
        )


class _RecordingAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event

    def head(self, stream_id: str):
        return self.events[-1] if self.events else None

    def checkpoint(self, stream_id: str) -> str:
        return "head-digest"


def _ctx():
    ent = Entitlement(
        edition=Edition.CONFIDENTIAL_SOVEREIGN,
        capabilities=frozenset({Capability.CONFIDENTIAL_WORKSPACE}),
        isolation=IsolationPosture.DEDICATED_CELL_GPU,
        max_tier=Tier.confidential,
    )
    return TenantContext(tenant_id="tenantA", subject_id="admin", entitlement=ent)


def _setup():
    kms = InMemoryKms()
    auth = EnvelopeAuthority(kms=kms, tenant_id="tenantA", granularity=DekGranularity.PER_TENANT)
    auth.provision()
    v = EncryptedDerivativeStore(DerivativeKind.VECTOR, auth)
    v.put("rec-1", b"embedding")
    return kms, auth, v


def test_shred_denied_when_pep_denies_and_kek_survives():
    kms, auth, v = _setup()
    audit = _RecordingAuditSink()
    shredder = CryptoShredder(pep=_DenyPep(), audit=audit, kms=kms)
    shredder.register(auth, stores=[v])
    with pytest.raises(PermissionError):
        shredder.shred(_ctx())
    assert kms.is_destroyed(auth.kek_id) is False  # fail-closed: nothing destroyed


def test_shred_destroys_kek_blinds_stores_and_audits():
    kms, auth, v = _setup()
    audit = _RecordingAuditSink()
    shredder = CryptoShredder(pep=_AllowPep(), audit=audit, kms=kms)
    shredder.register(auth, stores=[v])
    receipt = shredder.shred(_ctx())
    assert kms.is_destroyed(auth.kek_id) is True
    assert auth.kek_id == receipt.kek_id
    with pytest.raises(KmsKeyDestroyedError):
        v.get("rec-1")
    assert len(audit.events) == 1
    assert audit.events[0].decision is Decision.ALLOW
    assert audit.events[0].event_type.value == "egress"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_shredder.py -q
```
Expected: `ModuleNotFoundError: No module named 'confidential_crypto.shredder'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-confidential-crypto/src/confidential_crypto/shredder.py
"""PEP-gated crypto-shred across all confidential derivative stores (plan §11.3b, D4).

Shred is an authorization-bearing action: it routes through the single PEP
(D4) and proceeds ONLY on Decision.ALLOW (fail-closed otherwise). On ALLOW it
(1) triggers delete-and-rebuild on stores using that fallback, (2) destroys the
tenant KEK in KMS (rendering EncryptedDerivativeStore + VolumeKeyFallbackStore
ciphertext undecryptable), (3) drops in-process DEK caches, and (4) emits an
AuditEvent. Returns a ShredReceipt enumerating what was destroyed.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from contracts import (
    AuditEvent,
    AuditEventType,
    Capability,
    Decision,
    IAuditSink,
    IPolicyEnforcement,
    PepAction,
    PepRequest,
    TenantContext,
)

from confidential_crypto.derivative_store import (
    DeleteAndRebuildStore,
    IConfidentialDerivativeStore,
    VolumeKeyFallbackStore,
)
from confidential_crypto.envelope import EnvelopeAuthority
from confidential_crypto.keys import ShredReceipt
from confidential_crypto.kms import IKms


class CryptoShredder:
    """Destroys the wrapped DEK so every searchable derivative becomes unreadable."""

    def __init__(self, pep: IPolicyEnforcement, audit: IAuditSink, kms: IKms) -> None:
        self._pep = pep
        self._audit = audit
        self._kms = kms
        self._authority: EnvelopeAuthority | None = None
        self._stores: list[IConfidentialDerivativeStore] = []

    def register(
        self, authority: EnvelopeAuthority, stores: list[IConfidentialDerivativeStore]
    ) -> None:
        self._authority = authority
        self._stores = stores

    def shred(self, tenant: TenantContext) -> ShredReceipt:
        if self._authority is None:
            raise RuntimeError("CryptoShredder.register must be called before shred.")
        request = PepRequest(
            request_id=str(uuid.uuid4()),
            tenant=tenant,
            action=PepAction.EGRESS,
            required_capability=Capability.CONFIDENTIAL_WORKSPACE,
            resource_id=self._authority.kek_id,
        )
        decision = self._pep.authorize(request)
        if decision.decision is not Decision.ALLOW:
            self._emit_audit(tenant, request, decision.decision, decision.reason)
            raise PermissionError(f"crypto-shred denied: {decision.reason}")

        rebuilt: list[str] = []
        volume_keys: list[str] = []
        residual = 0
        for store in self._stores:
            if isinstance(store, DeleteAndRebuildStore):
                store.delete_and_rebuild()
                rebuilt.append(store.kind.value)
                residual = max(residual, store.residual_window_seconds)
            elif isinstance(store, VolumeKeyFallbackStore):
                volume_keys.append(store.volume_key_id)

        self._kms.destroy_kek(self._authority.kek_id)
        self._authority.forget_unwrapped()
        self._emit_audit(tenant, request, Decision.ALLOW, "crypto-shred complete")
        return ShredReceipt(
            tenant_id=tenant.tenant_id,
            kek_id=self._authority.kek_id,
            shredded_dek_ids=self._authority.wrapped_dek_ids(),
            volume_keys_revoked=tuple(volume_keys),
            rebuilt_stores=tuple(rebuilt),
            residual_window_seconds=residual,
        )

    def _emit_audit(
        self,
        tenant: TenantContext,
        request: PepRequest,
        decision: Decision,
        reason: str,
    ) -> None:
        prev = self._audit.head(tenant.tenant_id)
        prev_hash = prev.entry_hash if prev is not None else None
        seq = (prev.sequence + 1) if prev is not None else 0
        payload = f"{prev_hash}|{tenant.tenant_id}|{request.resource_id}|{decision.value}"
        entry_hash = hashlib.sha256(payload.encode()).hexdigest()
        self._audit.append(
            AuditEvent(
                event_id=str(uuid.uuid4()),
                stream_id=tenant.tenant_id,
                sequence=seq,
                event_type=AuditEventType.EGRESS,
                occurred_at=datetime.now(timezone.utc),
                tenant_id=tenant.tenant_id,
                subject_id=tenant.subject_id,
                resource_id=request.resource_id,
                decision=decision,
                reason=reason,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
        )
```

Update `__init__.py`:

```python
# append in confidential_crypto/__init__.py
from confidential_crypto.shredder import CryptoShredder
# add "CryptoShredder" to __all__
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_shredder.py -q
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-crypto && git commit -m "feat(confidential-crypto): PEP-gated CryptoShredder + audit emission (§11.3b, D4)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: CI gate — post-shred zero-decryptable-hits across vector + BM25 + graph

**Files:**
- Test `tigerexchange/packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py`

This is the headline §15.2/§11.3b security-contract gate: a hybrid search across all three engines after KEK crypto-shred returns NO decryptable hits. It exercises the `EncryptedDerivativeStore` (vector), `VolumeKeyFallbackStore` (graph, the no-customer-KEK fallback), and `DeleteAndRebuildStore` (BM25 postings, the rebuild fallback) so all three posture paths are proven in one gate.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py
"""CI GATE (plan §15.2 / §11.3b, Finding 4): after KEK crypto-shred, a search
across vector + BM25 + graph over the confidential corpus returns NO decryptable
hits. Exercises all three at-rest postures: customer-held-KEK (vector),
volume-key fallback (graph), delete-and-rebuild fallback (BM25 postings).
"""

import pytest

from contracts import (
    Capability,
    Decision,
    Edition,
    Entitlement,
    IsolationPosture,
    PepRequest,
    PepResponse,
    Tier,
    TenantContext,
)

from confidential_crypto.derivative_store import (
    DeleteAndRebuildStore,
    DerivativeKind,
    EncryptedDerivativeStore,
    VolumeKeyFallbackStore,
)
from confidential_crypto.envelope import EnvelopeAuthority
from confidential_crypto.keys import DekGranularity
from confidential_crypto.kms import InMemoryKms, KmsKeyDestroyedError
from confidential_crypto.shredder import CryptoShredder


class _AllowPep:
    def authorize(self, request: PepRequest) -> PepResponse:
        return PepResponse(
            request_id=request.request_id,
            decision=Decision.ALLOW,
            effective_tier=Tier.confidential,
        )


class _NullAudit:
    def __init__(self):
        self._h = None

    def append(self, event):
        self._h = event
        return event

    def head(self, stream_id):
        return self._h

    def checkpoint(self, stream_id):
        return "d"


def _ctx():
    ent = Entitlement(
        edition=Edition.CONFIDENTIAL_SOVEREIGN,
        capabilities=frozenset({Capability.CONFIDENTIAL_WORKSPACE}),
        isolation=IsolationPosture.DEDICATED_CELL_GPU,
        max_tier=Tier.confidential,
    )
    return TenantContext(tenant_id="tenantA", subject_id="admin", entitlement=ent)


def _hybrid_search(vector, graph, bm25, record_id):
    """Hybrid retrieval over all three engines; returns DECRYPTABLE hits only.

    Mirrors the real chokepoint: any engine that cannot decrypt its derivative
    contributes ZERO hits (the search surfaces nothing readable post-shred).
    """
    hits = []
    for store in (vector, graph):
        try:
            hits.append(store.get(record_id))
        except KmsKeyDestroyedError:
            pass  # KEK shredded -> undecryptable -> no hit
    try:
        hits.append(bm25.get(record_id))
    except KeyError:
        pass  # delete-and-rebuild removed the postings -> no hit
    return hits


def test_pre_shred_search_returns_decryptable_hits():
    kms = InMemoryKms()
    auth = EnvelopeAuthority(kms=kms, tenant_id="tenantA", granularity=DekGranularity.PER_TENANT)
    auth.provision()
    vector = EncryptedDerivativeStore(DerivativeKind.VECTOR, auth)
    graph = VolumeKeyFallbackStore(DerivativeKind.GRAPH, auth, volume_key_id="vol-age")
    bm25 = DeleteAndRebuildStore(DerivativeKind.BM25_POSTINGS, auth, residual_window_seconds=600)
    for s in (vector, graph, bm25):
        s.put("rec-1", b"confidential proposal: gene-editing budget $2.3M")
    assert len(_hybrid_search(vector, graph, bm25, "rec-1")) == 3  # all three hit


def test_post_kek_crypto_shred_zero_decryptable_hits_across_all_engines():
    kms = InMemoryKms()
    auth = EnvelopeAuthority(kms=kms, tenant_id="tenantA", granularity=DekGranularity.PER_TENANT)
    auth.provision()
    vector = EncryptedDerivativeStore(DerivativeKind.VECTOR, auth)
    graph = VolumeKeyFallbackStore(DerivativeKind.GRAPH, auth, volume_key_id="vol-age")
    bm25 = DeleteAndRebuildStore(DerivativeKind.BM25_POSTINGS, auth, residual_window_seconds=600)
    for s in (vector, graph, bm25):
        s.put("rec-1", b"confidential proposal: gene-editing budget $2.3M")

    shredder = CryptoShredder(pep=_AllowPep(), audit=_NullAudit(), kms=kms)
    shredder.register(auth, stores=[vector, graph, bm25])
    receipt = shredder.shred(_ctx())

    # THE CONTRACT: zero decryptable hits across vector + BM25 + graph.
    assert _hybrid_search(vector, graph, bm25, "rec-1") == []
    assert receipt.rebuilt_stores == ("bm25-postings",)
    assert receipt.volume_keys_revoked == ("vol-age",)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_post_shred_zero_hits.py -q
```
Expected at first run: PASS is NOT guaranteed if the prior tasks were skipped; with Tasks 1-5 in place this test should pass immediately. To honor TDD, run it BEFORE confirming Task 5's `__init__` export of `CryptoShredder` is wired — if `CryptoShredder` import fails it errors `ImportError: cannot import name 'CryptoShredder'`. Expected failure if run before Task 5 wiring: `ImportError`.

- [ ] **Step 3: Write minimal implementation**

No new implementation file — this gate is satisfied by Tasks 1-5. If the import fails, ensure `CryptoShredder` is exported from `confidential_crypto/__init__.py` (Task 5 Step 3). The test file itself is the deliverable artifact for this task.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-crypto && python -m pytest tests/test_post_shred_zero_hits.py -q && python -m pytest -q
```
Expected: `2 passed` for the gate file; full module suite `19 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-crypto && git commit -m "test(confidential-crypto): CI gate - post-shred zero-decryptable-hits across vector+BM25+graph (§15.2/§11.3b)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: COGS model — line items, GPU amortization, D7 ratio, margin gate

**Files:**
- Create `tigerexchange/packages/mod-confidential-cogs/pyproject.toml`
- Create `tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/__init__.py`
- Create `tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/cogs_model.py`
- Test `tigerexchange/packages/mod-confidential-cogs/tests/test_cogs_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-cogs/tests/test_cogs_model.py
"""COGS reconciliation arithmetic (plan §16.1/§16.2, Findings 7/10/11)."""

import pytest

from confidential_cogs.cogs_model import (
    CogsLineItem,
    CogsTable,
    GpuAmortization,
    d7_ratio,
    gross_margin,
    passes_d7_floor,
    passes_margin_gate,
)


def test_line_item_monthly_to_annual():
    li = CogsLineItem(name="KMS", monthly_usd=200.0)
    assert li.annual_usd == pytest.approx(2400.0)


def test_gpu_amortization_density_explicit():
    # $4k/mo dedicated GPU shared across K=2 confidential tenants -> $2k/mo each.
    gpu = GpuAmortization(dedicated_monthly_usd=4000.0, tenants_per_gpu=2)
    assert gpu.per_tenant_monthly_usd == pytest.approx(2000.0)
    # K=1 (Confidential-Sovereign dedicated GPU) -> full $4k/mo.
    assert GpuAmortization(dedicated_monthly_usd=4000.0, tenants_per_gpu=1).per_tenant_monthly_usd == pytest.approx(4000.0)


def test_table_total_sums_line_items_plus_amortized_gpu():
    table = CogsTable(
        name="Table-B shared-GPU",
        line_items=(
            CogsLineItem(name="cell", monthly_usd=1000.0),
            CogsLineItem(name="vec/graph/lexical", monthly_usd=400.0),
            CogsLineItem(name="spicedb+revlog", monthly_usd=300.0),
            CogsLineItem(name="hsm", monthly_usd=600.0),
            CogsLineItem(name="kms", monthly_usd=200.0),
        ),
        gpu=GpuAmortization(dedicated_monthly_usd=4000.0, tenants_per_gpu=2),
    )
    # 1000+400+300+600+200 + 2000 = 4500/mo -> 54000/yr
    assert table.per_tenant_monthly_usd == pytest.approx(4500.0)
    assert table.per_tenant_annual_usd == pytest.approx(54000.0)


def test_d7_ratio_and_floor():
    assert d7_ratio(acv_usd=120_000, cogs_annual_usd=43_000) == pytest.approx(2.79, abs=0.01)
    assert passes_d7_floor(acv_usd=120_000, cogs_annual_usd=43_000) is True   # >=2x
    assert passes_d7_floor(acv_usd=120_000, cogs_annual_usd=72_000) is False  # 1.67x dedicated-GPU


def test_gross_margin_gate_60pct():
    # 60% margin at $120k requires COGS <= $48k/yr.
    assert gross_margin(acv_usd=120_000, cogs_annual_usd=43_000) == pytest.approx(0.6417, abs=0.001)
    assert passes_margin_gate(acv_usd=120_000, cogs_annual_usd=43_000) is True
    assert passes_margin_gate(acv_usd=120_000, cogs_annual_usd=49_000) is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-cogs && python -m pytest tests/test_cogs_model.py -q
```
Expected: `ModuleNotFoundError: No module named 'confidential_cogs'`.

- [ ] **Step 3: Write minimal implementation**

```toml
# tigerexchange/packages/mod-confidential-cogs/pyproject.toml
[project]
name = "tigerexchange-mod-confidential-cogs"
version = "0.0.0"
description = "Table-B steady-state confidential COGS reconciliation: line items -> total, D7 ratio, >=60% margin gate (plan §16.1/§16.2)."
requires-python = ">=3.11"
dependencies = ["pydantic>=2.6,<3"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/confidential_cogs"]
```

```python
# tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/cogs_model.py
"""Confidential-tier COGS reconciliation (plan §16.1/§16.2, Findings 7/10/11).

Encodes the Table-B line items as DATA and recomputes the per-tenant COGS total,
the D7 gross-margin ratio (ACV >= 2-3x COGS), and the >=60%-gross-margin release
gate from those line items. The single largest driver -- per-tenant GPU
amortization at K tenants-per-shared-GPU -- is made explicit and additive to the
line-item sum, so the stated total reconciles to the line items honestly.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# D7 floor: institutional ACV must be >= this multiple of per-tenant COGS.
D7_MIN_MULTIPLE = 2.0
# Release gate: >= this gross margin per confidential deal.
MARGIN_GATE = 0.60


class CogsLineItem(BaseModel):
    """One monthly COGS line item (plan §16.1 Table-B)."""

    model_config = ConfigDict(frozen=True)

    name: str
    monthly_usd: float = Field(..., ge=0.0)

    @property
    def annual_usd(self) -> float:
        return self.monthly_usd * 12.0


class GpuAmortization(BaseModel):
    """Explicit per-tenant GPU amortization (plan §16.1, single largest driver)."""

    model_config = ConfigDict(frozen=True)

    dedicated_monthly_usd: float = Field(..., gt=0.0)
    tenants_per_gpu: int = Field(..., ge=1, description="K: confidential tenants per shared GPU.")

    @property
    def per_tenant_monthly_usd(self) -> float:
        return self.dedicated_monthly_usd / self.tenants_per_gpu


class CogsTable(BaseModel):
    """A confidential-tier COGS table: line items + amortized GPU (plan §16.1)."""

    model_config = ConfigDict(frozen=True)

    name: str
    line_items: tuple[CogsLineItem, ...]
    gpu: GpuAmortization

    @property
    def per_tenant_monthly_usd(self) -> float:
        return sum(li.monthly_usd for li in self.line_items) + self.gpu.per_tenant_monthly_usd

    @property
    def per_tenant_annual_usd(self) -> float:
        return self.per_tenant_monthly_usd * 12.0


def d7_ratio(acv_usd: float, cogs_annual_usd: float) -> float:
    """ACV / COGS multiple (the literal D7 2-3x basis)."""
    return acv_usd / cogs_annual_usd


def passes_d7_floor(acv_usd: float, cogs_annual_usd: float) -> bool:
    """True iff ACV >= 2x COGS (the D7 gross-margin floor, §16.2 Floor 1)."""
    return d7_ratio(acv_usd, cogs_annual_usd) >= D7_MIN_MULTIPLE


def gross_margin(acv_usd: float, cogs_annual_usd: float) -> float:
    """(ACV - COGS) / ACV."""
    return (acv_usd - cogs_annual_usd) / acv_usd


def passes_margin_gate(acv_usd: float, cogs_annual_usd: float) -> bool:
    """True iff gross margin >= 60% (release-condition gate, §16.2)."""
    return gross_margin(acv_usd, cogs_annual_usd) >= MARGIN_GATE
```

```python
# tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/__init__.py
"""mod-confidential-cogs public surface (plan §16.1/§16.2)."""

from confidential_cogs.cogs_model import (
    D7_MIN_MULTIPLE,
    MARGIN_GATE,
    CogsLineItem,
    CogsTable,
    GpuAmortization,
    d7_ratio,
    gross_margin,
    passes_d7_floor,
    passes_margin_gate,
)

__all__ = [
    "D7_MIN_MULTIPLE",
    "MARGIN_GATE",
    "CogsLineItem",
    "CogsTable",
    "GpuAmortization",
    "d7_ratio",
    "gross_margin",
    "passes_d7_floor",
    "passes_margin_gate",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-cogs && pip install -e . -q && python -m pytest tests/test_cogs_model.py -q
```
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-cogs && git commit -m "feat(confidential-cogs): COGS model - line-item sum, GPU amortization, D7 ratio, margin gate (§16.1/§16.2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Frozen Table-B data + reconciliation gate (Findings 10/11)

**Files:**
- Create `tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/table_b.py`
- Modify `tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/__init__.py`
- Test `tigerexchange/packages/mod-confidential-cogs/tests/test_table_b_reconciliation.py`

This encodes the exact §16.1 Table-B line items (shared-GPU K=2 and Confidential-Sovereign K=1) as data and asserts they reconcile to the stated totals, that the D7 floor passes for shared-GPU and FAILS for dedicated-GPU at $120k (forcing the >=$150k Sovereign price), and that the >=60% margin gate is recomputed honestly.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-confidential-cogs/tests/test_table_b_reconciliation.py
"""GATE (plan §16.1/§16.2, Findings 10/11): Table-B line items sum to the stated
total; D7 ratio + >=60% margin gate recomputed honestly off the line items.
"""

import pytest

from confidential_cogs.cogs_model import (
    passes_d7_floor,
    passes_margin_gate,
)
from confidential_cogs.table_b import (
    CONFIDENTIAL_SOVEREIGN_DEDICATED_GPU,
    SOVEREIGN_MIN_ACV,
    STEADY_STATE_CONFIDENTIAL_SHARED_GPU,
    TARGET_CONFIDENTIAL_ACV,
)


def test_shared_gpu_line_items_reconcile_to_stated_band():
    # §16.1 Table-B shared-GPU steady-state per-tenant COGS: ~$3.0-3.6k/mo.
    monthly = STEADY_STATE_CONFIDENTIAL_SHARED_GPU.per_tenant_monthly_usd
    assert 3000.0 <= monthly <= 3600.0
    annual = STEADY_STATE_CONFIDENTIAL_SHARED_GPU.per_tenant_annual_usd
    assert 36_000.0 <= annual <= 43_200.0  # ~$36-43k/yr, the honest D7 denominator


def test_dedicated_gpu_line_items_reconcile_to_sovereign_band():
    # §16.1 Confidential-Sovereign (dedicated GPU, K=1): ~$5.5-6k/mo, ~$66-72k/yr.
    monthly = CONFIDENTIAL_SOVEREIGN_DEDICATED_GPU.per_tenant_monthly_usd
    assert 5500.0 <= monthly <= 6000.0
    assert 66_000.0 <= CONFIDENTIAL_SOVEREIGN_DEDICATED_GPU.per_tenant_annual_usd <= 72_000.0


def test_d7_floor_passes_shared_gpu_at_120k_fails_dedicated_at_120k():
    shared = STEADY_STATE_CONFIDENTIAL_SHARED_GPU.per_tenant_annual_usd
    dedicated = CONFIDENTIAL_SOVEREIGN_DEDICATED_GPU.per_tenant_annual_usd
    # Shared-GPU at $120k clears the >=2x D7 floor.
    assert passes_d7_floor(TARGET_CONFIDENTIAL_ACV, shared) is True
    # Dedicated-GPU at $120k VIOLATES D7 (~1.7x) -> must be priced >= $150k.
    assert passes_d7_floor(TARGET_CONFIDENTIAL_ACV, dedicated) is False
    assert passes_d7_floor(SOVEREIGN_MIN_ACV, dedicated) is True


def test_margin_gate_passes_shared_gpu_at_120k():
    shared = STEADY_STATE_CONFIDENTIAL_SHARED_GPU.per_tenant_annual_usd
    # >=60% margin at $120k requires COGS <= $48k/yr; shared-GPU $36-43k passes.
    assert passes_margin_gate(TARGET_CONFIDENTIAL_ACV, shared) is True


def test_sovereign_min_acv_is_150k():
    assert SOVEREIGN_MIN_ACV == 150_000
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-cogs && python -m pytest tests/test_table_b_reconciliation.py -q
```
Expected: `ModuleNotFoundError: No module named 'confidential_cogs.table_b'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-confidential-cogs/src/confidential_cogs/table_b.py
"""Frozen Table-B steady-state confidential COGS line items (plan §16.1).

The exact §16.1 Table-B line items as DATA, so the per-tenant total is computed
from them rather than asserted. Two postures:
  - shared-GPU confidential (K=2 tenants/GPU) -> ~$36-43k/yr, the honest D7
    denominator (Floor 1).
  - Confidential-Sovereign (dedicated GPU, K=1) -> ~$66-72k/yr.

The shared-GPU edition clears the D7 >=2x floor AND the >=60% margin gate at the
$120k target ACV; the dedicated-GPU edition does NOT clear D7 at $120k, so it is
priced at >= $150k (§16.2).

Reconciliation basis: the §16.1 stated per-tenant bands are GPU-INCLUSIVE. The
non-GPU line items are the per-tenant AMORTIZED figures (HSM amortized regionally
across confidential tenants; managed cell + storage on the shared dedicated-cell
substrate at the confidential density D7 assumes). Non-GPU sum = $1,500/mo, so:
  - shared-GPU (K=2): $1,500 + $2,000 = $3,500/mo -> $42k/yr (inside $36-43k).
  - dedicated-GPU (K=1): $1,500 + $4,000 = $5,500/mo -> $66k/yr (inside $66-72k).
"""

from __future__ import annotations

from confidential_cogs.cogs_model import CogsLineItem, CogsTable, GpuAmortization

# Target confidential ACV the D7 ratio + margin gate are evaluated against (§16.2).
TARGET_CONFIDENTIAL_ACV: int = 120_000
# Confidential-Sovereign minimum ACV so it stays >= 2x its dedicated-GPU COGS (§16.2).
SOVEREIGN_MIN_ACV: int = 150_000

# §16.1 Table-B per-tenant non-GPU line items (monthly USD), as the per-tenant
# AMORTIZED figures so the GPU-INCLUSIVE total lands inside the plan's stated
# bands ($3.0-3.6k shared, $5.5-6k sovereign). Sum of non-GPU = $1,500/mo.
_NON_GPU_LINE_ITEMS = (
    CogsLineItem(name="managed dedicated cell compute + storage (per-tenant share)", monthly_usd=550.0),
    CogsLineItem(name="vector/graph/lexical (tenant-KEK/volume-key encrypted, §11.3b)", monthly_usd=400.0),
    CogsLineItem(name="SpiceDB replica + durable revocation log + sync replica (§4.4a)", monthly_usd=150.0),
    CogsLineItem(name="CloudHSM (per-tenant regional amortization)", monthly_usd=300.0),
    CogsLineItem(name="KMS (per-tenant cloud KMS / HYOK)", monthly_usd=100.0),
)
# Non-GPU sum = 550+400+150+300+100 = 1500/mo.
# shared-GPU (K=2): 1500 + 2000 = 3500/mo -> 42000/yr (inside $36-43k).
# dedicated-GPU (K=1): 1500 + 4000 = 5500/mo -> 66000/yr (inside $66-72k).

# Shared confidential-GPU pool, K=2 tenants/GPU: $4k dedicated / 2 = $2k/tenant.
STEADY_STATE_CONFIDENTIAL_SHARED_GPU = CogsTable(
    name="Table-B steady-state confidential (shared-GPU, K=2)",
    line_items=_NON_GPU_LINE_ITEMS,
    gpu=GpuAmortization(dedicated_monthly_usd=4000.0, tenants_per_gpu=2),
)

# Confidential-Sovereign: dedicated per-tenant GPU, no sharing (K=1).
CONFIDENTIAL_SOVEREIGN_DEDICATED_GPU = CogsTable(
    name="Table-B Confidential-Sovereign (dedicated-GPU, K=1)",
    line_items=_NON_GPU_LINE_ITEMS,
    gpu=GpuAmortization(dedicated_monthly_usd=4000.0, tenants_per_gpu=1),
)
```

Update `__init__.py`:

```python
# append in confidential_cogs/__init__.py
from confidential_cogs.table_b import (
    CONFIDENTIAL_SOVEREIGN_DEDICATED_GPU,
    SOVEREIGN_MIN_ACV,
    STEADY_STATE_CONFIDENTIAL_SHARED_GPU,
    TARGET_CONFIDENTIAL_ACV,
)
# add those four names to __all__
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange/packages/mod-confidential-cogs && python -m pytest tests/test_table_b_reconciliation.py -q && python -m pytest -q
```
Expected: `5 passed` for the gate; full module suite `10 passed`. Verify the shared-GPU annual is $42k (passes D7 at 2.86x and margin at 65%), dedicated-GPU annual is $66k (fails D7 at $120k = 1.82x, passes at $150k = 2.27x).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add packages/mod-confidential-cogs && git commit -m "feat(confidential-cogs): frozen Table-B data + reconciliation gate (D7 ratio + 60% margin, Findings 10/11)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Kernel-isolation import-linter contract for both packages (CI gate)

**Files:**
- Create `tigerexchange/ci/import_linter_confidential.toml`
- Test (executed via the `lint-imports` CLI in CI)

This enforces the §5.5 fitness function for the new feature modules: `confidential_crypto` and `confidential_cogs` may import the kernel (`contracts`) and approved crypto libs, but must NOT import other feature modules or persistence engines directly (engine reality is behind the adapter seams).

- [ ] **Step 1: Write the failing test**

Create the contract config and run it as the test (the "failing" state is the absence of the config file, which makes the CI lint step error).

```toml
# tigerexchange/ci/import_linter_confidential.toml
[importlinter]
root_packages = ["confidential_crypto", "confidential_cogs"]

[[importlinter.contracts]]
name = "confidential modules do not import feature modules or persistence engines"
type = "forbidden"
source_modules = ["confidential_crypto", "confidential_cogs"]
forbidden_modules = [
    "qdrant_client",
    "opensearchpy",
    "kuzu",
    "neo4j",
    "spicedb",
    "openfga_sdk",
    "sqlalchemy",
    "psycopg",
]

[[importlinter.contracts]]
name = "cogs module is pure (no crypto, no kernel persistence)"
type = "forbidden"
source_modules = ["confidential_cogs"]
forbidden_modules = ["cryptography", "confidential_crypto"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange && pip install import-linter -q && lint-imports --config ci/import_linter_confidential.toml
```
Expected before the packages are importable: `lint-imports` errors that it cannot find `confidential_crypto`/`confidential_cogs` (not yet on path) — run after `pip install -e` of both packages (Tasks 1-8 did this). If a forbidden import were present, it would report a broken contract. With Tasks 1-8 complete and clean, this should pass; to honor TDD, first introduce a deliberate bad import (e.g., `import sqlalchemy` at top of `cogs_model.py`), run, and observe `Contracts: 1 broken`.

- [ ] **Step 3: Write minimal implementation**

Remove the deliberate bad import (if added in Step 2). No production code change is needed — the modules were authored kernel-only. Confirm `confidential_crypto` imports only `contracts` + `cryptography`, and `confidential_cogs` imports only `pydantic`.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange && lint-imports --config ci/import_linter_confidential.toml
```
Expected: `Contracts: 2 kept, 0 broken.`

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add ci/import_linter_confidential.toml && git commit -m "ci(confidential): import-linter kernel-isolation contract for crypto + cogs modules (§5.5)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Full-suite verification + lint + type-check gate

**Files:**
- No new files; runs the complete gate for both packages.

- [ ] **Step 1: Write the failing test**

Add a top-level pytest invocation that collects both packages, plus ruff and mypy. (No new test code; this task is the consolidated verification gate the CI runs.)

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tigerexchange && python -m pytest packages/mod-confidential-crypto packages/mod-confidential-cogs -q
```
Expected: PASS if Tasks 1-8 are complete; if any package is not installed editable, expect collection errors — then run `pip install -e packages/mod-confidential-crypto packages/mod-confidential-cogs -q` and re-run.

- [ ] **Step 3: Write minimal implementation**

Ensure both packages are installed editable and the kernel `contracts` package is on the path:

```bash
cd /home/anurag/codebase/tigerexchange && pip install -e packages/contracts packages/mod-confidential-crypto packages/mod-confidential-cogs -q
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tigerexchange && \
python -m pytest packages/mod-confidential-crypto packages/mod-confidential-cogs -q && \
ruff check packages/mod-confidential-crypto/src packages/mod-confidential-cogs/src && \
mypy packages/mod-confidential-crypto/src packages/mod-confidential-cogs/src && \
lint-imports --config ci/import_linter_confidential.toml
```
Expected: `29 passed`; `ruff` `All checks passed!`; `mypy` `Success: no issues found`; `lint-imports` `Contracts: 2 kept, 0 broken.`

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tigerexchange && git add -A && git commit -m "test(confidential): full crypto+cogs suite green - post-shred zero-hits gate + Table-B reconciliation gate pass (§11.3b/§16.1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes on scope and the two highs addressed

- **Phase-0 scope = SINGLE-TENANT own-data only.** This sub-plan (0g per-tenant KEK/DEK confidential-at-rest + crypto-shred) is required for the center's OWN confidential proposal data (spec MVP = HYOK-at-rest + GDPR erasure). The cross-institution sharing/exchange and the cross-institution revocation AUTHORITY are Phase-1+ (kernel interfaces `IExchangeFeed`/`IRevocationAuthority` stubbed, not active here). 0k confidential draft persistence depends on 0g and stays single-tenant.
- **High 1 (derivative-store crypto-shred):** Tasks 1-6 encrypt every confidential derivative kind — Qdrant vectors, OpenSearch BM25 postings, AGE graph nodes/edges, object storage, per-tenant caches, **plus the convergence-report additions** generated drafts/draft-history and eval traces — under a per-tenant KEK/DEK (per-record DEK for Confidential-Sovereign). The three at-rest postures (customer-held-KEK, tenant-CMK volume-key fallback, delete-and-rebuild fallback) are all implemented and all exercised in the Task 6 CI gate, which is the §15.2/§11.3b "post-KEK-crypto-shred zero-decryptable-hits across vector+BM25+graph" contract test. Shred is PEP-gated (D4) and fails closed.
- **High 2 (Table-B COGS reconciliation):** Tasks 7-8 encode Table-B line items as data with explicit GPU amortization/density (K=2 shared, K=1 sovereign), prove the line items sum to the stated bands, and recompute the D7 ratio and >=60% margin gate honestly — showing shared-GPU ($42k/yr) clears D7 at $120k while dedicated-GPU ($66k/yr) does not, forcing the >=$150k Sovereign price.
- **Deferred correctly:** This sub-plan builds the Phase-0 in-cell crypto authority + reconciliation; it uses the `InMemoryKms` CI seam, NOT cloud-KMS/CloudHSM HYOK (the prod adapter is the documented seam, built when the first real-confidential-data customer lands, per §16.1 Table A / build-skeleton). No exchange federation, no revocation authority, no TEE.
- **Kernel discipline:** All cross-boundary types (`TenantContext`, `Capability`, `Edition`, `Entitlement`, `IsolationPosture`, `Tier`, `Decision`, `PepRequest`, `PepResponse`, `PepAction`, `AuditEvent`, `AuditEventType`, `IPolicyEnforcement`, `IAuditSink`) are imported verbatim from the canonical `contracts` kernel.