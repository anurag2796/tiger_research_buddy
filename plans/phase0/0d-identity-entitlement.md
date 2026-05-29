No existing sub-plan markdown files for 0a/0c to import conventions from, and no scaffold yet. I have the canonical kernel contracts verbatim in the prompt and all needed spec sections. I'll write the plan now, building on the assumed foundation (0a) and PEP/broker chokepoint (0c) per the dependency declaration, and using the kernel signatures verbatim.

# Identity (Keycloak + CILogon OIDC) + Entitlement/Edition at the PEP + Pooled-Plane Object-Authz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Wire Direct OIDC/CILogon federated identity (carrying `eduPersonScopedAffiliation` + stable `eduPersonUniqueId`) into a request-scoped `TenantContext`, resolve `Edition`→`Entitlement` capability sets evaluated centrally at the PEP (PLG = public + own-materials ONLY, confidential/exchange hard-OFF), and enforce the pooled-plane per-tenant isolation boundary: object-authz `Check` as the deny-by-default primary boundary plus FORCE-RLS / SET-LOCAL / WITH CHECK / RESTRICTIVE / tenant_id-leading defense-in-depth, with SECURITY DEFINER and materialized-view bypasses CI-forbidden.

**Architecture:** A `mod_identity` package translates a verified OIDC token (Keycloak control-plane broker → buyer IdP) into a frozen `TenantContext` whose `Entitlement` is the PEP's authoritative capability set. The single `PolicyEnforcementPoint` (owned by 0c, implementing the kernel `IPolicyEnforcement.authorize(request: PepRequest) -> PepResponse`) gains an injected `EntitlementEvaluator` that runs as the **entitlement step** inside `authorize()` — physically denying any `Capability`/`Tier` the edition lacks. This plan adds NO second PEP class and NO extra `requested_tier` kwarg on the kernel `authorize`. The canonical decision order inside `PolicyEnforcementPoint.authorize` is: (1) entitlement/edition gate → (2) capability gate → (3) ReBAC check (SpiceDB) → (4) ABAC tier check (OPA) → (5) owner-local durable tombstone check → (6) lease cache; this plan contributes step (1) and the pooled-plane object-authz that feeds the ReBAC step. The pooled-plane data path layers object-authz `Check` (SpiceDB `tenant#member`) as the primary boundary in front of Postgres tables hardened with FORCE RLS, RESTRICTIVE policies, WITH CHECK, `SET LOCAL app.tenant_id` per transaction, and `tenant_id`-leading indexes — with a CI lint forbidding SECURITY DEFINER / matview bypass.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Authlib (OIDC), Keycloak (broker), CILogon (OIDC), Postgres 16 (FORCE RLS), PgBouncer (transaction mode, SET LOCAL-compatible), SpiceDB/OpenFGA ReBAC `Check`, OPA (ABAC tier), psycopg 3, pytest, ruff, mypy, import-linter.

**Depends on:** `0a-foundation` (monorepo scaffold, Postgres+FORCE-RLS session helper, `TenantContext` wiring, FastAPI skeleton, CI), `0c-pep-broker-chokepoint` (the single `IPolicyEnforcement` PEP + `IDataAccessBroker`, OPA/SpiceDB clients, audit sink).

---

## File Structure

| File | Create/Modify | Single responsibility |
|---|---|---|
| `tigerexchange/packages/contracts/src/contracts/tenancy.py` | Modify | Use canonical kernel `TenantContext`/`Edition`/`Entitlement`/`Capability`/`IsolationPosture` verbatim (already pinned by 0b kernel; this plan only imports). |
| `tigerexchange/packages/mod-identity/pyproject.toml` | Create | Package metadata + import-linter contract (`classification.classifier` aware; mod-identity may import `contracts` + the PEP via DI, never raw stores). |
| `tigerexchange/packages/mod-identity/src/mod_identity/__init__.py` | Create | Package marker + public export surface. |
| `tigerexchange/packages/mod-identity/src/mod_identity/oidc_claims.py` | Create | Parse/validate `eduPersonScopedAffiliation` + `eduPersonUniqueId` from verified OIDC claims; fail-closed on missing subject id. |
| `tigerexchange/packages/mod-identity/src/mod_identity/entitlement_catalog.py` | Create | Frozen `Edition`→`Entitlement` capability mapping (PLG hard-OFF rules); single source of truth. |
| `tigerexchange/packages/mod-identity/src/mod_identity/context_builder.py` | Create | Build a frozen `TenantContext` from verified claims + resolved `Entitlement`. |
| `tigerexchange/packages/mod-identity/src/mod_identity/keycloak_broker.py` | Create | Direct OIDC/CILogon discovery + token verification via Keycloak broker config (Phase-0: Direct OIDC only). |
| `tigerexchange/packages/mod-identity/src/mod_identity/entitlement_evaluator.py` | Create | `EntitlementEvaluator`: the entitlement step the `PolicyEnforcementPoint` (0c) calls — denies any capability/tier the edition lacks. Composed INTO the PEP, NOT a second PEP class. |
| `tigerexchange/packages/mod-identity/src/mod_identity/pooled_authz.py` | Create | Pooled-plane object-authz `Check` (SpiceDB `tenant#member`) — deny-by-default boundary feeding the PEP ReBAC step. |
| `tigerexchange/packages/contracts/src/contracts/` (PEP lives in 0c) | Reference | 0c owns `PolicyEnforcementPoint.authorize(request: PepRequest) -> PepResponse`; 0d injects `EntitlementEvaluator` + pooled `Check` into it. This plan does NOT define or modify a PEP class. |
| `tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/__init__.py` | Create | Pooled-plane package marker. |
| `tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/tenant_session.py` | Create | `SET LOCAL app.tenant_id` transaction-scoped session (PgBouncer-safe), never `SET`. |
| `tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/own_materials_repo.py` | Create | Pooled own-materials repo: authz `Check` first, then RLS-protected query. |
| `tigerexchange/db/migrations/0d_pooled_own_materials.sql` | Create | `own_materials` table: FORCE RLS, RESTRICTIVE policies, WITH CHECK, tenant_id-leading index. |
| `tigerexchange/db/migrations/0d_app_role.sql` | Create | Non-superuser `app_pooled` role (subject to RLS) + the `app.tenant_id` GUC convention. |
| `tigerexchange/tools/ci/forbid_security_definer.py` | Create | CI lint: fail on `SECURITY DEFINER` / `MATERIALIZED VIEW` over tenant-scoped tables. |
| `tigerexchange/packages/mod-identity/tests/test_oidc_claims.py` | Create | Test claim parsing + fail-closed on missing `eduPersonUniqueId`. |
| `tigerexchange/packages/mod-identity/tests/test_entitlement_catalog.py` | Create | Test PLG hard-OFF + edition capability sets. |
| `tigerexchange/packages/mod-identity/tests/test_context_builder.py` | Create | Test end-to-end claims→`TenantContext`. |
| `tigerexchange/packages/mod-identity/tests/test_entitlement_evaluator.py` | Create | Test PLG cannot construct confidential/exchange request (contract test §2.3). |
| `tigerexchange/packages/mod-identity/tests/test_pooled_authz.py` | Create | Test object-authz Check deny-by-default. |
| `tigerexchange/packages/mod-pooled-plane/tests/test_tenant_session.py` | Create | Test SET LOCAL transaction-scope + no cross-borrow leak. |
| `tigerexchange/packages/mod-pooled-plane/tests/test_cross_tenant_read_denied.py` | Create | The §7.7 contract test: BOLA / direct / SECURITY DEFINER / borrowed PgBouncer connection — all denied. |
| `tigerexchange/tools/ci/tests/test_forbid_security_definer.py` | Create | Test the CI lint catches a SECURITY DEFINER violation. |

---

## Tasks

### Task 1: OIDC claim extraction (eduPersonScopedAffiliation + eduPersonUniqueId), fail-closed

**Files:** Create `tigerexchange/packages/mod-identity/pyproject.toml`, `tigerexchange/packages/mod-identity/src/mod_identity/__init__.py`, `tigerexchange/packages/mod-identity/src/mod_identity/oidc_claims.py`, Test `tigerexchange/packages/mod-identity/tests/test_oidc_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-identity/tests/test_oidc_claims.py
import pytest

from mod_identity.oidc_claims import VerifiedSubject, extract_subject, ClaimError


def test_extracts_subject_id_and_affiliations() -> None:
    claims = {
        "sub": "kc-internal-uuid",
        "eduPersonUniqueId": "abc123@rit.edu",
        "eduPersonScopedAffiliation": ["faculty@rit.edu", "member@rit.edu"],
    }
    subj = extract_subject(claims)
    assert isinstance(subj, VerifiedSubject)
    assert subj.subject_id == "abc123@rit.edu"
    assert subj.affiliations == frozenset({"faculty@rit.edu", "member@rit.edu"})


def test_accepts_single_string_affiliation() -> None:
    claims = {
        "eduPersonUniqueId": "x@rit.edu",
        "eduPersonScopedAffiliation": "faculty@rit.edu",
    }
    subj = extract_subject(claims)
    assert subj.affiliations == frozenset({"faculty@rit.edu"})


def test_missing_unique_id_fails_closed() -> None:
    # ORCID is a correlation key, NOT the auth root of trust (§7.1).
    # No eduPersonUniqueId and no OIDC sub -> hard fail, never a guessed identity.
    with pytest.raises(ClaimError):
        extract_subject({"orcid": "0000-0002-1825-0097"})


def test_falls_back_to_oidc_sub_when_no_edu_unique_id() -> None:
    subj = extract_subject({"sub": "okta-sub-1"})
    assert subj.subject_id == "okta-sub-1"
    assert subj.affiliations == frozenset()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_oidc_claims.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_identity.oidc_claims'` (or collection error) — fails because the module does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```toml
# tigerexchange/packages/mod-identity/pyproject.toml
[project]
name = "tigerexchange-mod-identity"
version = "0.0.0"
description = "Federated identity: Direct OIDC/CILogon -> TenantContext; entitlement resolution at the PEP (Phase-0)."
requires-python = ">=3.11"
dependencies = [
    "tigerexchange-contracts",
    "authlib>=1.3,<2",
    "httpx>=0.27,<1",
    "pydantic>=2.6,<3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mod_identity"]

# Fitness: identity may import the kernel + PEP client; never a raw store engine.
[tool.importlinter]
root_package = "mod_identity"

[[tool.importlinter.contracts]]
name = "identity-has-no-raw-store-deps"
type = "forbidden"
source_modules = ["mod_identity"]
forbidden_modules = ["psycopg", "qdrant_client", "opensearchpy", "kuzu", "neo4j"]
```

```python
# tigerexchange/packages/mod-identity/src/mod_identity/__init__.py
"""Federated identity module (Direct OIDC/CILogon, Phase-0)."""
```

```python
# tigerexchange/packages/mod-identity/src/mod_identity/oidc_claims.py
"""Extract the canonical federation identity claims from a VERIFIED OIDC token.

Phase-0 (§7.1): authorize on `eduPersonScopedAffiliation` + stable
`eduPersonUniqueId`. ORCID is a correlation key, NEVER the auth root of trust.
Token signature/issuer/audience verification happens upstream in
keycloak_broker.verify_token; this module only reads ALREADY-VERIFIED claims.

Fail-closed: a token that carries no stable subject id (neither
eduPersonUniqueId nor the OIDC `sub`) raises ClaimError. We never invent or
guess a subject identity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ClaimError(ValueError):
    """Raised when a verified token lacks a usable stable subject identity."""


class VerifiedSubject(BaseModel):
    """The identity facts the PEP authorizes against (§7.1/§7.3)."""

    model_config = ConfigDict(frozen=True)

    subject_id: str
    affiliations: frozenset[str]


def _coerce_affiliations(value: object) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset({value})
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(v) for v in value if v)
    return frozenset()


def extract_subject(claims: dict[str, object]) -> VerifiedSubject:
    """Build a VerifiedSubject from verified OIDC claims, fail-closed."""
    edu_unique = claims.get("eduPersonUniqueId")
    oidc_sub = claims.get("sub")
    subject_id = edu_unique or oidc_sub
    if not isinstance(subject_id, str) or not subject_id.strip():
        raise ClaimError(
            "No stable subject id: token has neither eduPersonUniqueId nor sub. "
            "ORCID is a correlation key, not an auth root of trust (§7.1)."
        )
    return VerifiedSubject(
        subject_id=subject_id.strip(),
        affiliations=_coerce_affiliations(claims.get("eduPersonScopedAffiliation")),
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && pip install -e . -q && python -m pytest tests/test_oidc_claims.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-identity && git commit -m "feat(identity): extract eduPersonScopedAffiliation + eduPersonUniqueId from verified OIDC, fail-closed

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Edition→Entitlement catalog (PLG hard-OFF)

**Files:** Create `tigerexchange/packages/mod-identity/src/mod_identity/entitlement_catalog.py`, Test `tigerexchange/packages/mod-identity/tests/test_entitlement_catalog.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-identity/tests/test_entitlement_catalog.py
import pytest

from contracts import Capability, Edition, IsolationPosture, Tier
from mod_identity.entitlement_catalog import entitlement_for


def test_plg_is_public_plus_own_materials_only() -> None:
    ent = entitlement_for(Edition.PLG)
    assert ent.has(Capability.PUBLIC_RETRIEVAL)
    assert ent.has(Capability.OWN_MATERIALS)
    # Hard-OFF for PLG (§2.3):
    assert not ent.has(Capability.CONFIDENTIAL_WORKSPACE)
    assert not ent.has(Capability.EXCHANGE_PARTICIPATION)
    assert not ent.has(Capability.CROSS_INSTITUTION_GRANTS)


def test_plg_tier_ceiling_is_private_pooled_isolation() -> None:
    ent = entitlement_for(Edition.PLG)
    assert ent.max_tier == Tier.private
    assert ent.permits_tier(Tier.private)
    assert not ent.permits_tier(Tier.confidential)
    assert ent.isolation == IsolationPosture.POOLED


def test_consortium_anchor_has_confidential_and_exchange() -> None:
    ent = entitlement_for(Edition.CONSORTIUM_ANCHOR)
    assert ent.has(Capability.CONFIDENTIAL_WORKSPACE)
    assert ent.has(Capability.EXCHANGE_PARTICIPATION)
    assert ent.max_tier == Tier.confidential
    assert ent.isolation == IsolationPosture.DEDICATED_CELL


def test_every_edition_is_mapped() -> None:
    for edition in Edition:
        ent = entitlement_for(edition)
        assert ent.edition == edition


def test_catalog_entitlements_are_frozen() -> None:
    ent = entitlement_for(Edition.PLG)
    with pytest.raises(Exception):
        ent.capabilities = frozenset()  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_entitlement_catalog.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_identity.entitlement_catalog'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-identity/src/mod_identity/entitlement_catalog.py
"""Frozen Edition -> Entitlement capability mapping (plan §2.3).

Single source of truth for which capabilities/tier each edition grants. The PEP
(not feature modules) evaluates these entitlements (§2.3). PLG is capped at
public + own-materials (Tier.private ceiling) on the pooled plane;
confidential-workspace / exchange-participation / cross-institution-grants are
HARD-OFF for PLG. Editions are entitlement CONFIG, not forks.
"""

from __future__ import annotations

from contracts import Capability, Edition, Entitlement, IsolationPosture, Tier

# Capability bundles, smallest -> largest. Each higher edition is a superset.
_PLG_CAPS: frozenset[Capability] = frozenset(
    {Capability.PUBLIC_RETRIEVAL, Capability.OWN_MATERIALS}
)
_INSTITUTIONAL_CAPS: frozenset[Capability] = _PLG_CAPS | frozenset(
    {Capability.PRIVATE_TIER, Capability.TEAM_ASSEMBLY}
)
_CAMPUS_CAPS: frozenset[Capability] = _INSTITUTIONAL_CAPS
_CONSORTIUM_ANCHOR_CAPS: frozenset[Capability] = _INSTITUTIONAL_CAPS | frozenset(
    {
        Capability.CONFIDENTIAL_WORKSPACE,
        Capability.EXCHANGE_PARTICIPATION,
        Capability.CROSS_INSTITUTION_GRANTS,
        Capability.BYO_PROVIDER,
    }
)
_CONFIDENTIAL_SOVEREIGN_CAPS: frozenset[Capability] = (
    _CONSORTIUM_ANCHOR_CAPS | frozenset({Capability.DEDICATED_GPU})
)

_CATALOG: dict[Edition, Entitlement] = {
    Edition.PLG: Entitlement(
        edition=Edition.PLG,
        capabilities=_PLG_CAPS,
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.private,
    ),
    Edition.INSTITUTIONAL: Entitlement(
        edition=Edition.INSTITUTIONAL,
        capabilities=_INSTITUTIONAL_CAPS,
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.private,
    ),
    Edition.CAMPUS: Entitlement(
        edition=Edition.CAMPUS,
        capabilities=_CAMPUS_CAPS,
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.private,
    ),
    Edition.CONSORTIUM_ANCHOR: Entitlement(
        edition=Edition.CONSORTIUM_ANCHOR,
        capabilities=_CONSORTIUM_ANCHOR_CAPS,
        isolation=IsolationPosture.DEDICATED_CELL,
        max_tier=Tier.confidential,
    ),
    Edition.CONFIDENTIAL_SOVEREIGN: Entitlement(
        edition=Edition.CONFIDENTIAL_SOVEREIGN,
        capabilities=_CONFIDENTIAL_SOVEREIGN_CAPS,
        isolation=IsolationPosture.DEDICATED_CELL_GPU,
        max_tier=Tier.confidential,
    ),
}


def entitlement_for(edition: Edition) -> Entitlement:
    """Resolve the frozen capability set for an edition (§2.3)."""
    return _CATALOG[edition]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_entitlement_catalog.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-identity && git commit -m "feat(identity): frozen Edition->Entitlement catalog with PLG confidential/exchange hard-OFF

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Build a frozen TenantContext from verified claims + resolved entitlement

**Files:** Create `tigerexchange/packages/mod-identity/src/mod_identity/context_builder.py`, Test `tigerexchange/packages/mod-identity/tests/test_context_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-identity/tests/test_context_builder.py
import pytest

from contracts import Capability, Edition, IsolationPosture, TenantContext, Tier
from mod_identity.context_builder import build_tenant_context


def _claims() -> dict[str, object]:
    return {
        "eduPersonUniqueId": "abc123@rit.edu",
        "eduPersonScopedAffiliation": ["faculty@rit.edu"],
    }


def test_builds_frozen_plg_context() -> None:
    ctx = build_tenant_context(
        claims=_claims(),
        tenant_id="rit",
        edition=Edition.PLG,
        consortium_ids=frozenset(),
        subject_active=True,
    )
    assert isinstance(ctx, TenantContext)
    assert ctx.tenant_id == "rit"
    assert ctx.subject_id == "abc123@rit.edu"
    assert ctx.affiliations == frozenset({"faculty@rit.edu"})
    assert ctx.entitlement.edition == Edition.PLG
    assert ctx.entitlement.isolation == IsolationPosture.POOLED
    assert ctx.entitlement.has(Capability.OWN_MATERIALS)
    assert not ctx.entitlement.has(Capability.CONFIDENTIAL_WORKSPACE)
    assert ctx.entitlement.max_tier == Tier.private


def test_context_is_immutable_for_request_lifetime() -> None:
    ctx = build_tenant_context(
        claims=_claims(), tenant_id="rit", edition=Edition.PLG,
        consortium_ids=frozenset(), subject_active=True,
    )
    with pytest.raises(Exception):
        ctx.tenant_id = "evil"  # type: ignore[misc]


def test_consortium_membership_carried() -> None:
    ctx = build_tenant_context(
        claims=_claims(), tenant_id="rit", edition=Edition.CONSORTIUM_ANCHOR,
        consortium_ids=frozenset({"ctsa"}), subject_active=True,
    )
    assert ctx.consortium_ids == frozenset({"ctsa"})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_context_builder.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_identity.context_builder'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-identity/src/mod_identity/context_builder.py
"""Assemble the request-scoped, frozen TenantContext (plan §4, §7.1).

Combines the verified OIDC subject (oidc_claims) with the tenant's resolved
Entitlement (entitlement_catalog) into the single TenantContext object the PEP
authorizes against and the RLS layer pins via SET LOCAL (§7.7). The context is
frozen so no downstream code can re-scope an in-flight request.
"""

from __future__ import annotations

from contracts import Edition, TenantContext

from mod_identity.entitlement_catalog import entitlement_for
from mod_identity.oidc_claims import extract_subject


def build_tenant_context(
    *,
    claims: dict[str, object],
    tenant_id: str,
    edition: Edition,
    consortium_ids: frozenset[str],
    subject_active: bool,
) -> TenantContext:
    """Build the frozen TenantContext for the request (§7.1/§7.3)."""
    subject = extract_subject(claims)
    return TenantContext(
        tenant_id=tenant_id,
        subject_id=subject.subject_id,
        entitlement=entitlement_for(edition),
        consortium_ids=consortium_ids,
        affiliations=subject.affiliations,
        subject_active=subject_active,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_context_builder.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-identity && git commit -m "feat(identity): build frozen TenantContext from verified claims + resolved entitlement

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Keycloak broker — Direct OIDC/CILogon discovery + token verification (Phase-0)

**Files:** Create `tigerexchange/packages/mod-identity/src/mod_identity/keycloak_broker.py`, Test `tigerexchange/packages/mod-identity/tests/test_keycloak_broker.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-identity/tests/test_keycloak_broker.py
import time

import pytest
from authlib.jose import jwt
from authlib.jose import JsonWebKey

from mod_identity.keycloak_broker import BrokerConfig, OidcBroker, TokenError


@pytest.fixture()
def rsa_key() -> JsonWebKey:
    return JsonWebKey.generate_key("RSA", 2048, is_private=True)


def _make_broker(rsa_key: JsonWebKey) -> OidcBroker:
    pub = rsa_key.as_dict(is_private=False)
    pub["kid"] = "test-kid"
    cfg = BrokerConfig(
        issuer="https://idp.example.edu",
        audience="tigerexchange",
        jwks={"keys": [pub]},
    )
    return OidcBroker(cfg)


def _sign(rsa_key: JsonWebKey, claims: dict) -> str:
    header = {"alg": "RS256", "kid": "test-kid"}
    return jwt.encode(header, claims, rsa_key).decode("ascii")


def test_verifies_valid_token_and_returns_claims(rsa_key: JsonWebKey) -> None:
    broker = _make_broker(rsa_key)
    token = _sign(rsa_key, {
        "iss": "https://idp.example.edu",
        "aud": "tigerexchange",
        "exp": int(time.time()) + 300,
        "eduPersonUniqueId": "abc@example.edu",
    })
    claims = broker.verify_token(token)
    assert claims["eduPersonUniqueId"] == "abc@example.edu"


def test_rejects_wrong_audience(rsa_key: JsonWebKey) -> None:
    broker = _make_broker(rsa_key)
    token = _sign(rsa_key, {
        "iss": "https://idp.example.edu",
        "aud": "someone-else",
        "exp": int(time.time()) + 300,
        "eduPersonUniqueId": "abc@example.edu",
    })
    with pytest.raises(TokenError):
        broker.verify_token(token)


def test_rejects_expired_token(rsa_key: JsonWebKey) -> None:
    broker = _make_broker(rsa_key)
    token = _sign(rsa_key, {
        "iss": "https://idp.example.edu",
        "aud": "tigerexchange",
        "exp": int(time.time()) - 10,
        "eduPersonUniqueId": "abc@example.edu",
    })
    with pytest.raises(TokenError):
        broker.verify_token(token)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_keycloak_broker.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_identity.keycloak_broker'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-identity/src/mod_identity/keycloak_broker.py
"""Direct OIDC/CILogon token verification via the Keycloak broker (plan §7.1).

Phase-0 reality (§7.1): ship Direct OIDC/CILogon to the buyer's IdP ONLY.
Keycloak is the control-plane broker; SAML/eduGAIN brokering is a later,
separately-sized line and is NOT shipped here. This verifies the token's
issuer, audience, signature (against the IdP JWKS), and expiry, then returns the
verified claims dict for oidc_claims.extract_subject. It does NOT trust an
unverified token.
"""

from __future__ import annotations

from dataclasses import dataclass

from authlib.jose import JsonWebKey, jwt
from authlib.jose.errors import JoseError


class TokenError(ValueError):
    """Raised when a presented OIDC token fails verification (fail-closed)."""


@dataclass(frozen=True)
class BrokerConfig:
    """Verification config for one IdP connection (Direct OIDC/CILogon)."""

    issuer: str
    audience: str
    jwks: dict  # JWKS document fetched from the IdP discovery endpoint.


class OidcBroker:
    """Verifies tokens issued (or brokered via Keycloak) by the buyer's IdP."""

    def __init__(self, config: BrokerConfig) -> None:
        self._config = config
        self._key_set = JsonWebKey.import_key_set(config.jwks)
        self._claims_options = {
            "iss": {"essential": True, "value": config.issuer},
            "aud": {"essential": True, "value": config.audience},
            "exp": {"essential": True},
        }

    def verify_token(self, raw_token: str) -> dict[str, object]:
        """Verify signature/issuer/audience/expiry; return verified claims."""
        try:
            claims = jwt.decode(
                raw_token,
                self._key_set,
                claims_options=self._claims_options,
            )
            claims.validate()
        except JoseError as exc:
            raise TokenError(f"OIDC token verification failed: {exc}") from exc
        return dict(claims)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_keycloak_broker.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-identity && git commit -m "feat(identity): Keycloak broker Direct OIDC/CILogon token verification (Phase-0, no SAML)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `EntitlementEvaluator` — the entitlement step the PEP calls (deny any capability/tier the edition lacks, contract test §2.3)

**Files:** Create `tigerexchange/packages/mod-identity/src/mod_identity/entitlement_evaluator.py`, Test `tigerexchange/packages/mod-identity/tests/test_entitlement_evaluator.py`

> This is the entitlement step from §2.3, composed INTO the single `PolicyEnforcementPoint` (0c) as an injected dependency (Task 7) — NOT a second PEP. A PLG tenant **physically cannot** construct a confidential-tier or exchange-participation request because this gate, run first inside `PolicyEnforcementPoint.authorize`, denies it. It is an internal helper (not the kernel `IPolicyEnforcement`), so it takes the PEP-resolved object tier as a parameter; the kernel `authorize(request)` signature is unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-identity/tests/test_entitlement_evaluator.py
import pytest

from contracts import (
    Capability,
    Decision,
    Edition,
    Entitlement,
    IsolationPosture,
    PepAction,
    PepRequest,
    TenantContext,
    Tier,
)
from mod_identity.entitlement_evaluator import EntitlementEvaluator


def _plg_ctx() -> TenantContext:
    ent = Entitlement(
        edition=Edition.PLG,
        capabilities=frozenset(
            {Capability.PUBLIC_RETRIEVAL, Capability.OWN_MATERIALS}
        ),
        isolation=IsolationPosture.POOLED,
        max_tier=Tier.private,
    )
    return TenantContext(tenant_id="indiv", subject_id="pi@x.edu", entitlement=ent)


def _req(ctx: TenantContext, cap: Capability, action: PepAction) -> PepRequest:
    return PepRequest(
        request_id="r1",
        tenant=ctx,
        action=action,
        required_capability=cap,
        resource_id="obj-1",
    )


def test_plg_cannot_construct_confidential_request() -> None:
    ev = EntitlementEvaluator()
    req = _req(_plg_ctx(), Capability.CONFIDENTIAL_WORKSPACE, PepAction.RETRIEVE)
    resp = ev.evaluate(req, requested_tier=Tier.confidential)
    assert resp.decision is Decision.DENY
    assert resp.payload is None
    assert "entitlement" in resp.reason.lower()


def test_plg_cannot_construct_exchange_request() -> None:
    ev = EntitlementEvaluator()
    req = _req(_plg_ctx(), Capability.EXCHANGE_PARTICIPATION, PepAction.DISCOVER)
    resp = ev.evaluate(req, requested_tier=Tier.public)
    assert resp.decision is Decision.DENY


def test_plg_own_materials_private_tier_allowed_through_entitlement_gate() -> None:
    ev = EntitlementEvaluator()
    req = _req(_plg_ctx(), Capability.OWN_MATERIALS, PepAction.RETRIEVE)
    resp = ev.evaluate(req, requested_tier=Tier.private)
    assert resp.decision is Decision.ALLOW


def test_tier_above_ceiling_denied_even_with_capability() -> None:
    # PLG holds OWN_MATERIALS but is capped at private; a confidential tier
    # request must be denied on the tier ceiling alone.
    ev = EntitlementEvaluator()
    req = _req(_plg_ctx(), Capability.OWN_MATERIALS, PepAction.RETRIEVE)
    resp = ev.evaluate(req, requested_tier=Tier.confidential)
    assert resp.decision is Decision.DENY
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_entitlement_evaluator.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_identity.entitlement_evaluator'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-identity/src/mod_identity/entitlement_evaluator.py
"""Entitlement step injected into the single PolicyEnforcementPoint (plan §2.3, §2.4).

Entitlements are evaluated CENTRALLY at the PEP, not per-module (§2.3). This is
the entitlement step composed INTO 0c's `PolicyEnforcementPoint.authorize` (it
is NOT a PEP itself and does not implement the kernel `IPolicyEnforcement`). It
makes "a PLG tenant cannot construct a confidential-tier or exchange-participation
request" structurally true: a capability the edition lacks, or a tier above the
edition's ceiling, is physically denied here BEFORE any ReBAC/ABAC/store access.
The PEP resolves the object tier from the classifier/broker (R2) and passes it as
`requested_tier`; this helper never reads a caller kwarg off the kernel
`authorize`. Fail-closed: deny carries no payload (consistent with
PepResponse.model_post_init).
"""

from __future__ import annotations

from contracts import Decision, PepRequest, PepResponse, Tier


class EntitlementEvaluator:
    """Deny-by-edition entitlement step the single PEP runs first (§2.3)."""

    def evaluate(self, request: PepRequest, *, requested_tier: Tier) -> PepResponse:
        """Deny if the edition lacks the capability OR exceeds its tier ceiling."""
        ent = request.tenant.entitlement

        if not ent.has(request.required_capability):
            return self._deny(
                request,
                requested_tier,
                f"entitlement: edition '{ent.edition.value}' lacks capability "
                f"'{request.required_capability.value}'",
            )

        if not ent.permits_tier(requested_tier):
            return self._deny(
                request,
                requested_tier,
                f"entitlement: edition '{ent.edition.value}' tier ceiling "
                f"'{ent.max_tier.wire}' < requested '{requested_tier.wire}'",
            )

        return PepResponse(
            request_id=request.request_id,
            decision=Decision.ALLOW,
            effective_tier=requested_tier,
            reason="entitlement gate passed",
        )

    @staticmethod
    def _deny(request: PepRequest, tier: Tier, reason: str) -> PepResponse:
        return PepResponse(
            request_id=request.request_id,
            decision=Decision.DENY,
            effective_tier=tier,
            payload=None,
            reason=reason,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_entitlement_evaluator.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-identity/src/mod_identity/entitlement_evaluator.py tigerexchange/packages/mod-identity/tests/test_entitlement_evaluator.py && git commit -m "feat(pep): central entitlement gate denies capability/tier the edition lacks (§2.3 contract test)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Pooled-plane object-authz Check — deny-by-default primary boundary

**Files:** Create `tigerexchange/packages/mod-identity/src/mod_identity/pooled_authz.py`, Test `tigerexchange/packages/mod-identity/tests/test_pooled_authz.py`

> Primary boundary (§7.7): every pooled-plane request resolves the target object's owning tenant and does a `Check` on relation `tenant#member` **before** any data access. No grant → no path.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-identity/tests/test_pooled_authz.py
import pytest

from mod_identity.pooled_authz import PooledObjectAuthz, AuthzDenied


class FakeRebac:
    """Stand-in for the SpiceDB/OpenFGA Check client (relation tenant#member)."""

    def __init__(self, grants: set[tuple[str, str]]) -> None:
        # grants: set of (tenant_id, object_id) that ARE owned/permitted.
        self._grants = grants
        self.calls: list[tuple[str, str]] = []

    def check(self, *, tenant_id: str, object_id: str) -> bool:
        self.calls.append((tenant_id, object_id))
        return (tenant_id, object_id) in self._grants


def test_check_passes_when_tenant_owns_object() -> None:
    rebac = FakeRebac(grants={("tenantA", "obj-1")})
    authz = PooledObjectAuthz(rebac)
    authz.require_object_access(tenant_id="tenantA", object_id="obj-1")
    assert rebac.calls == [("tenantA", "obj-1")]


def test_check_denies_cross_tenant_by_default() -> None:
    rebac = FakeRebac(grants={("tenantA", "obj-1")})
    authz = PooledObjectAuthz(rebac)
    # tenantB has NO grant on obj-1 -> deny-by-default, no data path.
    with pytest.raises(AuthzDenied):
        authz.require_object_access(tenant_id="tenantB", object_id="obj-1")


def test_check_runs_before_any_data_access_returns_object_id_on_allow() -> None:
    rebac = FakeRebac(grants={("tenantA", "obj-1")})
    authz = PooledObjectAuthz(rebac)
    allowed = authz.require_object_access(tenant_id="tenantA", object_id="obj-1")
    assert allowed == "obj-1"


def test_unknown_object_denied() -> None:
    rebac = FakeRebac(grants=set())
    authz = PooledObjectAuthz(rebac)
    with pytest.raises(AuthzDenied):
        authz.require_object_access(tenant_id="tenantA", object_id="ghost")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_pooled_authz.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_identity.pooled_authz'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-identity/src/mod_identity/pooled_authz.py
"""Pooled-plane object-level authz Check — the PRIMARY tenant boundary (plan §7.7).

D7 co-locates multiple PLG tenants' own-materials in a pooled plane, which is
exactly the OWASP-API-#1 (BOLA/IDOR) breach class. The PRIMARY boundary is an
object-level authz Check (SpiceDB/OpenFGA relation `tenant#member`) on EVERY
request, evaluated BEFORE any data access. Deny-by-default: no grant -> no path.
A query that omits the tenant predicate still cannot reach another tenant's
rows because the Check gates the request, not the SQL. Postgres RLS (§7.7) is
defense-in-depth BEHIND this, never the sole boundary.
"""

from __future__ import annotations

from typing import Protocol


class AuthzDenied(PermissionError):
    """Raised when the object-authz Check denies access (deny-by-default)."""


class RebacCheck(Protocol):
    """Structural client for the ReBAC Check (SpiceDB/OpenFGA)."""

    def check(self, *, tenant_id: str, object_id: str) -> bool: ...


class PooledObjectAuthz:
    """Enforces the object-authz Check before any pooled-plane data access."""

    def __init__(self, rebac: RebacCheck) -> None:
        self._rebac = rebac

    def require_object_access(self, *, tenant_id: str, object_id: str) -> str:
        """Check `tenant#member` on the object; raise AuthzDenied if no grant."""
        if not self._rebac.check(tenant_id=tenant_id, object_id=object_id):
            raise AuthzDenied(
                f"pooled-plane object-authz: tenant '{tenant_id}' has no grant "
                f"on object '{object_id}' (deny-by-default, §7.7)"
            )
        return object_id
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_pooled_authz.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-identity/src/mod_identity/pooled_authz.py tigerexchange/packages/mod-identity/tests/test_pooled_authz.py && git commit -m "feat(pep): pooled-plane object-authz Check as deny-by-default primary tenant boundary (§7.7)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Inject the entitlement step + pooled-authz INTO 0c's `PolicyEnforcementPoint.authorize`

**Files:** Modify 0c's `PolicyEnforcementPoint` (`tigerexchange/packages/mod-pep/src/mod_pep/policy_enforcement_point.py`, owned by 0c — this plan only injects dependencies), Test `tigerexchange/packages/mod-identity/tests/test_pep_entitlement_wired.py`

> There is ONE PEP class — `PolicyEnforcementPoint` (0c), implementing the kernel `IPolicyEnforcement.authorize(request: PepRequest) -> PepResponse`. This plan does NOT create a second PEP class and does NOT add a `requested_tier` kwarg to the kernel `authorize`. It injects an `EntitlementEvaluator` (step 1) and the pooled-plane object-authz `Check` (feeding step 3, ReBAC) into the PEP's existing canonical decision order: (1) entitlement/edition gate → (2) capability gate → (3) ReBAC check → (4) ABAC tier check → (5) durable tombstone → (6) lease cache. The PEP resolves the object's tier from the classifier/broker lookup (R2) and passes that resolved tier to the injected `EntitlementEvaluator`; the tier is NEVER a caller-supplied kwarg and is NEVER hardcoded to `confidential`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-identity/tests/test_pep_entitlement_wired.py
import pytest

from contracts import (
    Capability,
    Decision,
    Edition,
    Entitlement,
    IsolationPosture,
    PepAction,
    PepRequest,
    Tier,
    TenantContext,
)
from mod_pep.policy_enforcement_point import PolicyEnforcementPoint
from mod_identity.entitlement_evaluator import EntitlementEvaluator
from mod_identity.pooled_authz import PooledObjectAuthz


class FakeRebac:
    def __init__(self, grants: set[tuple[str, str]]) -> None:
        self._grants = grants

    def check(self, *, tenant_id: str, object_id: str) -> bool:
        return (tenant_id, object_id) in self._grants


class FakeClassifier:
    """Stand-in for the 0b classifier/broker tier lookup (R2).

    The PEP resolves each object's tier here — it does NOT hardcode confidential.
    Public/private objects MUST resolve to their real (non-confidential) tier so
    they take the correct ABAC branch (0i retrieval / 0k funding stay off the
    confidential path).
    """

    def __init__(self, tiers: dict[str, Tier]) -> None:
        self._tiers = tiers

    def tier_of(self, object_id: str | None) -> Tier:
        if object_id is None:
            return Tier.public
        return self._tiers[object_id]


def _ctx(edition: Edition, caps: set[Capability], max_tier: Tier) -> TenantContext:
    ent = Entitlement(
        edition=edition,
        capabilities=frozenset(caps),
        isolation=IsolationPosture.POOLED,
        max_tier=max_tier,
    )
    return TenantContext(tenant_id="tenantA", subject_id="pi@x.edu", entitlement=ent)


def _pep(grants: set[tuple[str, str]], tiers: dict[str, Tier]) -> PolicyEnforcementPoint:
    # 0d injects its entitlement step + pooled Check into the ONE 0c PEP; the
    # classifier supplies the resolved object tier (R2). 0c owns any further
    # constructor params (audit sink, OPA/SpiceDB clients) — pass via DI factory.
    return PolicyEnforcementPoint(
        entitlement_evaluator=EntitlementEvaluator(),
        pooled_authz=PooledObjectAuthz(FakeRebac(grants)),
        classifier=FakeClassifier(tiers),
    )


def test_plg_confidential_denied_at_entitlement_step() -> None:
    # obj-1 is a confidential object; the PEP resolves its tier from the
    # classifier and the entitlement step denies the PLG edition outright.
    pep = _pep(grants={("tenantA", "obj-1")}, tiers={"obj-1": Tier.confidential})
    ctx = _ctx(Edition.PLG, {Capability.OWN_MATERIALS}, Tier.private)
    req = PepRequest(
        request_id="r1", tenant=ctx, action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="obj-1",
    )
    resp = pep.authorize(req)  # kernel signature: one arg, no requested_tier
    assert resp.decision is Decision.DENY
    assert resp.payload is None


def test_own_materials_private_allowed_when_object_check_passes() -> None:
    pep = _pep(grants={("tenantA", "obj-1")}, tiers={"obj-1": Tier.private})
    ctx = _ctx(Edition.PLG, {Capability.OWN_MATERIALS}, Tier.private)
    req = PepRequest(
        request_id="r2", tenant=ctx, action=PepAction.RETRIEVE,
        required_capability=Capability.OWN_MATERIALS, resource_id="obj-1",
    )
    resp = pep.authorize(req)
    assert resp.decision is Decision.ALLOW


def test_public_object_takes_non_confidential_branch() -> None:
    # R2: a public object resolves to Tier.public, NOT confidential, so it does
    # not get forced onto the confidential ABAC path.
    pep = _pep(grants={("tenantA", "pub-1")}, tiers={"pub-1": Tier.public})
    ctx = _ctx(Edition.PLG, {Capability.PUBLIC_RETRIEVAL, Capability.OWN_MATERIALS}, Tier.private)
    req = PepRequest(
        request_id="r3", tenant=ctx, action=PepAction.RETRIEVE,
        required_capability=Capability.PUBLIC_RETRIEVAL, resource_id="pub-1",
    )
    resp = pep.authorize(req)
    assert resp.decision is Decision.ALLOW
    assert resp.effective_tier == Tier.public


def test_own_materials_denied_when_cross_tenant_object() -> None:
    # Entitlement passes, but tenantA has no grant on obj-2 -> denied by Check.
    pep = _pep(grants={("tenantA", "obj-1")}, tiers={"obj-2": Tier.private})
    ctx = _ctx(Edition.PLG, {Capability.OWN_MATERIALS}, Tier.private)
    req = PepRequest(
        request_id="r4", tenant=ctx, action=PepAction.RETRIEVE,
        required_capability=Capability.OWN_MATERIALS, resource_id="obj-2",
    )
    resp = pep.authorize(req)
    assert resp.decision is Decision.DENY
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_pep_entitlement_wired.py -q
```

Expected: failure — 0c's `PolicyEnforcementPoint` does not yet accept the `entitlement_evaluator` / `pooled_authz` / `classifier` injections, or does not yet run the entitlement step (TypeError or assertion mismatch).

- [ ] **Step 3: Write minimal implementation**

> 0c OWNS `PolicyEnforcementPoint` and its kernel-conformant `authorize(request: PepRequest) -> PepResponse`. 0d's contribution is the injected `EntitlementEvaluator` (the entitlement step) + the pooled-plane object-authz `Check`. Wire them into 0c's existing `authorize` decision order as steps (1) and (3). Do NOT add a `requested_tier` parameter to `authorize` — the PEP resolves the object's tier from the classifier/broker (R2) and hands it to the evaluator internally. The injected dependencies are provided by 0a's DI factory `get_pep` (`api.dependencies`).

```python
# tigerexchange/packages/mod-pep/src/mod_pep/policy_enforcement_point.py  (0c-owned; 0d injects steps)
from __future__ import annotations

from contracts import Decision, PepRequest, PepResponse, Tier

from mod_identity.entitlement_evaluator import EntitlementEvaluator
from mod_identity.pooled_authz import AuthzDenied, PooledObjectAuthz


class PolicyEnforcementPoint:
    """The SINGLE Policy Enforcement Point (D4, §4.2) — kernel IPolicyEnforcement.

    Canonical decision order inside authorize() (fail-closed, deny short-circuits):
      1. entitlement/edition gate (this plan's EntitlementEvaluator) — edition
         capability + tier ceiling, evaluated against the classifier-resolved
         object tier.
      2. capability gate.
      3. ReBAC check (SpiceDB) — pooled-plane object-authz Check feeds here.
      4. ABAC tier check (OPA).
      5. owner-local durable tombstone check (AUTHORITATIVE deny dimension).
      6. lease cache (narrow cache only).
    Steps 2,4,5,6 are 0c's; 0d injects steps 1 and the pooled Check (step 3).
    """

    def __init__(
        self,
        *,
        entitlement_evaluator: EntitlementEvaluator,
        pooled_authz: PooledObjectAuthz | None = None,
        classifier: object,  # 0b classifier/broker; .tier_of(object_id) -> Tier (R2)
        # ... 0c's own deps (audit sink, OPA client, SpiceDB client, tombstone
        # log, lease cache) continue here, unchanged.
    ) -> None:
        self._entitlement = entitlement_evaluator
        self._pooled_authz = pooled_authz
        self._classifier = classifier

    def authorize(self, request: PepRequest) -> PepResponse:
        # R2: resolve the object's REAL tier from the classifier/broker lookup —
        # never hardcode (Tier.confidential, frozenset()); public/private objects
        # must take their correct (non-confidential) branch.
        resolved_tier: Tier = self._classifier.tier_of(request.resource_id)

        # (1) Entitlement/edition gate.
        gate = self._entitlement.evaluate(request, requested_tier=resolved_tier)
        if gate.decision is not Decision.ALLOW:
            return gate

        # (3) ReBAC: pooled-plane object-authz Check (deny-by-default, before any
        # data access). 0c's capability gate (2) precedes this; ABAC (4),
        # durable tombstone (5), lease cache (6) follow on ALLOW — unchanged.
        if self._pooled_authz is not None and request.resource_id is not None:
            try:
                self._pooled_authz.require_object_access(
                    tenant_id=request.tenant.tenant_id,
                    object_id=request.resource_id,
                )
            except AuthzDenied as denied:
                return PepResponse(
                    request_id=request.request_id,
                    decision=Decision.DENY,
                    effective_tier=resolved_tier,
                    payload=None,
                    reason=str(denied),
                )

        return PepResponse(
            request_id=request.request_id,
            decision=Decision.ALLOW,
            effective_tier=resolved_tier,
            reason="entitlement + object-authz passed",
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-identity && python -m pytest tests/test_pep_entitlement_wired.py tests/test_entitlement_evaluator.py tests/test_pooled_authz.py -q
```

Expected: `12 passed` (4 wired + 4 evaluator + 4 pooled — adjust if 0c added more; all green).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-pep/src/mod_pep/policy_enforcement_point.py tigerexchange/packages/mod-identity/tests/test_pep_entitlement_wired.py && git commit -m "feat(pep): inject entitlement step + pooled object-authz Check into PolicyEnforcementPoint.authorize (one PEP, kernel signature)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Pooled own-materials migration — FORCE RLS, RESTRICTIVE, WITH CHECK, tenant_id-leading

**Files:** Create `tigerexchange/db/migrations/0d_pooled_own_materials.sql`, `tigerexchange/db/migrations/0d_app_role.sql`, Test `tigerexchange/packages/mod-pooled-plane/tests/test_rls_migration.py`

- [ ] **Step 1: Write the failing test**

> Requires a local Postgres (the 0a foundation provides `TIGEREX_TEST_DSN`, a superuser DSN to a disposable test DB). The test applies the migration and asserts every §7.7 footgun is closed.

```python
# tigerexchange/packages/mod-pooled-plane/tests/test_rls_migration.py
import os
import pathlib

import psycopg
import pytest

DSN = os.environ.get("TIGEREX_TEST_DSN")
MIG = pathlib.Path(__file__).parents[3] / "db" / "migrations"

pytestmark = pytest.mark.skipif(not DSN, reason="TIGEREX_TEST_DSN not set")


def _apply(conn: psycopg.Connection) -> None:
    for name in ("0d_app_role.sql", "0d_pooled_own_materials.sql"):
        conn.execute((MIG / name).read_text())
    conn.commit()


@pytest.fixture()
def conn():
    c = psycopg.connect(DSN)
    yield c
    c.execute("DROP TABLE IF EXISTS own_materials CASCADE")
    c.execute("DROP ROLE IF EXISTS app_pooled")
    c.commit()
    c.close()


def test_force_rls_enabled(conn) -> None:
    _apply(conn)
    row = conn.execute(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
        "WHERE relname = 'own_materials'"
    ).fetchone()
    assert row == (True, True)  # RLS enabled AND forced (owner not exempt)


def test_policies_are_restrictive_with_check(conn) -> None:
    _apply(conn)
    rows = conn.execute(
        "SELECT polpermissive, polwithcheck IS NOT NULL "
        "FROM pg_policy WHERE polrelid = 'own_materials'::regclass"
    ).fetchall()
    assert rows, "no policies found"
    # Every policy must be RESTRICTIVE (polpermissive = False).
    assert all(not permissive for permissive, _ in rows)
    # At least one policy carries a WITH CHECK (blocks cross-tenant INSERT/UPDATE).
    assert any(has_with_check for _, has_with_check in rows)


def test_tenant_id_is_leading_index_column(conn) -> None:
    _apply(conn)
    leading = conn.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
        WHERE i.indrelid = 'own_materials'::regclass
        ORDER BY i.indisprimary DESC
        LIMIT 1
        """
    ).fetchone()
    assert leading is not None and leading[0] == "tenant_id"


def test_app_pooled_role_is_not_superuser_and_no_bypassrls(conn) -> None:
    _apply(conn)
    row = conn.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app_pooled'"
    ).fetchone()
    assert row == (False, False)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && python -m pytest tests/test_rls_migration.py -q
```

Expected: failures (or skip if no DSN) — migration files do not exist, so `_apply` raises `FileNotFoundError`. If `TIGEREX_TEST_DSN` is set, the test collects and fails.

- [ ] **Step 3: Write minimal implementation**

```sql
-- tigerexchange/db/migrations/0d_app_role.sql
-- Non-superuser application role for the pooled plane. It is SUBJECT to RLS:
-- not a superuser and NOBYPASSRLS, so FORCE RLS actually constrains it (§7.7).
-- The tenant context is pinned per-transaction via:  SET LOCAL app.tenant_id = '<id>'
-- (see tenant_session.py). NEVER plain SET (would leak across PgBouncer borrows).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_pooled') THEN
        CREATE ROLE app_pooled NOLOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
```

```sql
-- tigerexchange/db/migrations/0d_pooled_own_materials.sql
-- Pooled-plane own-materials table with the §7.7 footguns ALL closed.
-- RLS here is DEFENSE-IN-DEPTH behind the object-authz Check (pooled_authz.py),
-- never the sole boundary.

CREATE TABLE IF NOT EXISTS own_materials (
    -- tenant_id LEADING so the tenant predicate is index-driven (no full-scan
    -- side channel) and the composite PK starts with tenant_id.
    tenant_id   text NOT NULL,
    object_id   text NOT NULL,
    title       text NOT NULL DEFAULT '',
    body        text NOT NULL DEFAULT '',
    PRIMARY KEY (tenant_id, object_id)
);

-- Explicit tenant_id-leading index (PK already leads with tenant_id; this makes
-- the intent unambiguous and survives PK changes).
CREATE INDEX IF NOT EXISTS ix_own_materials_tenant
    ON own_materials (tenant_id, object_id);

-- Enable AND FORCE RLS: FORCE so the table OWNER/superuser is NOT exempt.
ALTER TABLE own_materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE own_materials FORCE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON own_materials TO app_pooled;

-- RESTRICTIVE (AND-combined) policy: adding a policy can only NARROW access.
-- USING filters SELECT/UPDATE/DELETE rows; WITH CHECK blocks cross-tenant
-- INSERT/UPDATE (a row whose tenant_id != the session tenant is rejected).
DROP POLICY IF EXISTS p_tenant_isolation ON own_materials;
CREATE POLICY p_tenant_isolation ON own_materials
    AS RESTRICTIVE
    FOR ALL
    TO app_pooled
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && python -m pytest tests/test_rls_migration.py -q
```

Expected: `4 passed` (requires `TIGEREX_TEST_DSN`; without it the suite skips — run in CI where the DSN is set).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/db/migrations/0d_app_role.sql tigerexchange/db/migrations/0d_pooled_own_materials.sql tigerexchange/packages/mod-pooled-plane/tests/test_rls_migration.py && git commit -m "feat(pooled): own_materials table with FORCE RLS, RESTRICTIVE+WITH CHECK, tenant_id-leading index (§7.7)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: SET LOCAL transaction-scoped tenant session (PgBouncer-safe)

**Files:** Create `tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/__init__.py`, `tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/tenant_session.py`, `tigerexchange/packages/mod-pooled-plane/pyproject.toml`, Test `tigerexchange/packages/mod-pooled-plane/tests/test_tenant_session.py`

> §7.7 + §13.1: `SET LOCAL` (transaction-scoped), never `SET`, so a borrowed PgBouncer transaction-mode connection cannot leak tenant context to the next borrower.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-pooled-plane/tests/test_tenant_session.py
import os

import psycopg
import pytest

from mod_pooled_plane.tenant_session import tenant_transaction

DSN = os.environ.get("TIGEREX_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="TIGEREX_TEST_DSN not set")


@pytest.fixture()
def conn():
    c = psycopg.connect(DSN)
    yield c
    c.close()


def test_set_local_pins_tenant_inside_transaction(conn) -> None:
    with tenant_transaction(conn, "tenantA") as cur:
        got = cur.execute("SELECT current_setting('app.tenant_id', true)").fetchone()
        assert got[0] == "tenantA"


def test_tenant_context_does_not_leak_to_next_borrower(conn) -> None:
    # Simulate PgBouncer transaction-mode connection reuse: after the first
    # tenant's transaction COMMITs, SET LOCAL must NOT persist on the connection.
    with tenant_transaction(conn, "tenantA") as cur:
        cur.execute("SELECT 1")
    # New transaction (the "next borrower"): tenant context must be gone/empty.
    leaked = conn.execute(
        "SELECT current_setting('app.tenant_id', true)"
    ).fetchone()[0]
    assert leaked in (None, "")


def test_rejects_empty_tenant_id(conn) -> None:
    with pytest.raises(ValueError):
        with tenant_transaction(conn, ""):
            pass
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && python -m pytest tests/test_tenant_session.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_pooled_plane.tenant_session'`.

- [ ] **Step 3: Write minimal implementation**

```toml
# tigerexchange/packages/mod-pooled-plane/pyproject.toml
[project]
name = "tigerexchange-mod-pooled-plane"
version = "0.0.0"
description = "Pooled-plane per-tenant isolation: SET LOCAL tenant session + own-materials repo behind object-authz + RLS (§7.7)."
requires-python = ">=3.11"
dependencies = [
    "tigerexchange-contracts",
    "psycopg[binary]>=3.1,<4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mod_pooled_plane"]
```

```python
# tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/__init__.py
"""Pooled-plane per-tenant isolation (PLG own-materials), §7.7."""
```

```python
# tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/tenant_session.py
"""Transaction-scoped tenant pinning for the pooled plane (plan §7.7, §13.1).

Pins `app.tenant_id` via `SET LOCAL` (transaction-scoped) so PgBouncer in
transaction-pooling mode CANNOT leak tenant context to the next borrower of a
recycled connection. We NEVER use plain `SET` (session-scoped) here. The value
is bound as a parameter, not string-interpolated, to avoid injection.

This is DEFENSE-IN-DEPTH behind the object-authz Check (pooled_authz.py); the
RLS policy (§7.7) reads this GUC via current_setting('app.tenant_id').
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg


@contextmanager
def tenant_transaction(
    conn: psycopg.Connection, tenant_id: str
) -> Iterator[psycopg.Cursor]:
    """Open a transaction with `SET LOCAL app.tenant_id`, committing on exit."""
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id must be a non-empty string for SET LOCAL")
    with conn.transaction():
        with conn.cursor() as cur:
            # set_config(..., is_local => true) == SET LOCAL, parameter-bound.
            cur.execute(
                "SELECT set_config('app.tenant_id', %s, true)", (tenant_id,)
            )
            yield cur
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && pip install -e . -q && python -m pytest tests/test_tenant_session.py -q
```

Expected: `3 passed` (with `TIGEREX_TEST_DSN`; skips otherwise).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-pooled-plane && git commit -m "feat(pooled): SET LOCAL transaction-scoped tenant session, PgBouncer-safe (no cross-borrow leak, §7.7)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Own-materials repo — authz Check first, then RLS-protected query

**Files:** Create `tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/own_materials_repo.py`, Test `tigerexchange/packages/mod-pooled-plane/tests/test_own_materials_repo.py`

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-pooled-plane/tests/test_own_materials_repo.py
import os
import pathlib

import psycopg
import pytest

from mod_identity.pooled_authz import AuthzDenied, PooledObjectAuthz
from mod_pooled_plane.own_materials_repo import OwnMaterialsRepo

DSN = os.environ.get("TIGEREX_TEST_DSN")
MIG = pathlib.Path(__file__).parents[3] / "db" / "migrations"
pytestmark = pytest.mark.skipif(not DSN, reason="TIGEREX_TEST_DSN not set")


class FakeRebac:
    def __init__(self, grants: set[tuple[str, str]]) -> None:
        self._grants = grants

    def check(self, *, tenant_id: str, object_id: str) -> bool:
        return (tenant_id, object_id) in self._grants


@pytest.fixture()
def conn():
    c = psycopg.connect(DSN)
    for name in ("0d_app_role.sql", "0d_pooled_own_materials.sql"):
        c.execute((MIG / name).read_text())
    # seed two tenants' rows AS the owner (FORCE RLS still lets us seed via
    # explicit tenant context in a SET LOCAL transaction).
    for tid, oid in (("tenantA", "a1"), ("tenantB", "b1")):
        c.execute("SELECT set_config('app.tenant_id', %s, false)", (tid,))
        c.execute(
            "INSERT INTO own_materials (tenant_id, object_id, title) "
            "VALUES (%s, %s, %s)", (tid, oid, f"{tid}-title"),
        )
    c.execute("RESET app.tenant_id")
    c.commit()
    yield c
    c.execute("DROP TABLE IF EXISTS own_materials CASCADE")
    c.execute("DROP ROLE IF EXISTS app_pooled")
    c.commit()
    c.close()


def test_owner_reads_own_object(conn) -> None:
    authz = PooledObjectAuthz(FakeRebac({("tenantA", "a1")}))
    repo = OwnMaterialsRepo(conn, authz)
    row = repo.get("tenantA", "a1")
    assert row is not None and row["title"] == "tenantA-title"


def test_cross_tenant_denied_at_authz_check(conn) -> None:
    # tenantA tries tenantB's object: object-authz Check denies before any SQL.
    authz = PooledObjectAuthz(FakeRebac({("tenantA", "a1")}))
    repo = OwnMaterialsRepo(conn, authz)
    with pytest.raises(AuthzDenied):
        repo.get("tenantA", "b1")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && python -m pytest tests/test_own_materials_repo.py -q
```

Expected: `ModuleNotFoundError: No module named 'mod_pooled_plane.own_materials_repo'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/own_materials_repo.py
"""Pooled own-materials repository (plan §7.7).

Order: (1) object-authz Check (PRIMARY boundary, deny-by-default) then
(2) the RLS-protected query inside a SET LOCAL transaction (DEFENSE-IN-DEPTH).
Even if the Check were bypassed, FORCE-RLS + the tenant predicate would still
deny the row; even if the SQL omitted the tenant predicate, RLS filters it.
"""

from __future__ import annotations

import psycopg

from mod_identity.pooled_authz import PooledObjectAuthz

from mod_pooled_plane.tenant_session import tenant_transaction


class OwnMaterialsRepo:
    """Reads a tenant's own-materials behind object-authz + RLS."""

    def __init__(self, conn: psycopg.Connection, authz: PooledObjectAuthz) -> None:
        self._conn = conn
        self._authz = authz

    def get(self, tenant_id: str, object_id: str) -> dict[str, str] | None:
        # 1. PRIMARY boundary: object-authz Check (raises AuthzDenied on no grant).
        self._authz.require_object_access(tenant_id=tenant_id, object_id=object_id)
        # 2. DEFENSE-IN-DEPTH: RLS-scoped query inside a SET LOCAL transaction.
        with tenant_transaction(self._conn, tenant_id) as cur:
            row = cur.execute(
                "SELECT tenant_id, object_id, title, body FROM own_materials "
                "WHERE object_id = %s",
                (object_id,),
            ).fetchone()
        if row is None:
            return None
        return {"tenant_id": row[0], "object_id": row[1], "title": row[2], "body": row[3]}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && python -m pytest tests/test_own_materials_repo.py -q
```

Expected: `2 passed` (requires DSN + the `pep` package installed: `pip install -e ../pep`).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-pooled-plane/src/mod_pooled_plane/own_materials_repo.py tigerexchange/packages/mod-pooled-plane/tests/test_own_materials_repo.py && git commit -m "feat(pooled): own-materials repo runs object-authz Check before RLS-scoped query (§7.7)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: CI lint — forbid SECURITY DEFINER / materialized-view bypass over tenant-scoped tables

**Files:** Create `tigerexchange/tools/ci/forbid_security_definer.py`, Test `tigerexchange/tools/ci/tests/test_forbid_security_definer.py`

> §7.7: a lint/CI check must flag any `SECURITY DEFINER` function or materialized view over a tenant-scoped table (both can bypass the tenant predicate / RLS).

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/tools/ci/tests/test_forbid_security_definer.py
import pathlib

from ci.forbid_security_definer import scan_sql, Violation


def test_flags_security_definer(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "bad.sql"
    f.write_text(
        "CREATE FUNCTION leak() RETURNS setof own_materials\n"
        "LANGUAGE sql SECURITY DEFINER AS $$ SELECT * FROM own_materials $$;\n"
    )
    violations = scan_sql([f])
    assert any(v.kind == "SECURITY DEFINER" for v in violations)


def test_flags_materialized_view(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "mv.sql"
    f.write_text(
        "CREATE MATERIALIZED VIEW mv_all AS SELECT * FROM own_materials;\n"
    )
    violations = scan_sql([f])
    assert any(v.kind == "MATERIALIZED VIEW" for v in violations)


def test_clean_migration_passes(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "ok.sql"
    f.write_text(
        "CREATE TABLE own_materials (tenant_id text, object_id text);\n"
        "ALTER TABLE own_materials FORCE ROW LEVEL SECURITY;\n"
    )
    assert scan_sql([f]) == []


def test_comments_ignored(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "comment.sql"
    f.write_text("-- SECURITY DEFINER is forbidden; this is just a comment\n")
    assert scan_sql([f]) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/tools/ci && python -m pytest tests/test_forbid_security_definer.py -q
```

Expected: `ModuleNotFoundError: No module named 'ci.forbid_security_definer'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/tools/ci/forbid_security_definer.py
"""CI lint: forbid SECURITY DEFINER and materialized views in DB migrations (§7.7).

Both can bypass the tenant predicate / RLS. SECURITY DEFINER runs with the
function-owner's privileges (which may BYPASSRLS); a materialized view snapshots
rows OUTSIDE the requester's RLS context. This scanner fails CI on either over
the migration set, per the §7.7 forbidden-bypass hard-constraint.

Usage (CI):  python -m ci.forbid_security_definer tigerexchange/db/migrations
Exits non-zero and prints each violation if any are found.
"""

from __future__ import annotations

import pathlib
import re
import sys
from dataclasses import dataclass

_SECURITY_DEFINER = re.compile(r"\bSECURITY\s+DEFINER\b", re.IGNORECASE)
_MATERIALIZED_VIEW = re.compile(r"\bMATERIALIZED\s+VIEW\b", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    kind: str


def _strip_comment(line: str) -> str:
    idx = line.find("--")
    return line if idx == -1 else line[:idx]


def scan_sql(paths: list[pathlib.Path]) -> list[Violation]:
    """Return all SECURITY DEFINER / MATERIALIZED VIEW violations across files."""
    out: list[Violation] = []
    for path in paths:
        for n, raw in enumerate(path.read_text().splitlines(), start=1):
            code = _strip_comment(raw)
            if _SECURITY_DEFINER.search(code):
                out.append(Violation(str(path), n, "SECURITY DEFINER"))
            if _MATERIALIZED_VIEW.search(code):
                out.append(Violation(str(path), n, "MATERIALIZED VIEW"))
    return out


def main(argv: list[str]) -> int:
    roots = [pathlib.Path(a) for a in argv] or [pathlib.Path("tigerexchange/db/migrations")]
    files: list[pathlib.Path] = []
    for root in roots:
        files.extend(sorted(root.rglob("*.sql")) if root.is_dir() else [root])
    violations = scan_sql(files)
    for v in violations:
        print(f"FORBIDDEN {v.kind} at {v.path}:{v.line} (§7.7 tenant-bypass)")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

> Add `tigerexchange/tools/ci/__init__.py` and `tigerexchange/tools/ci/ci/__init__.py` as needed so `ci.forbid_security_definer` imports (place the module under a `ci/` package dir if your layout requires it; the test imports `from ci.forbid_security_definer`).

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/tools/ci && PYTHONPATH=. python -m pytest tests/test_forbid_security_definer.py -q && PYTHONPATH=. python -m ci.forbid_security_definer ../../db/migrations
```

Expected: `4 passed`, then the scanner over the real migrations prints nothing and exits 0 (the Task 8 migrations contain no SECURITY DEFINER / matview).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/tools/ci && git commit -m "feat(ci): forbid SECURITY DEFINER + materialized views over tenant-scoped tables (§7.7)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: The §7.7 cross-tenant-read-denied contract test (BOLA / direct / SECURITY DEFINER / borrowed PgBouncer)

**Files:** Create `tigerexchange/packages/mod-pooled-plane/tests/test_cross_tenant_read_denied.py`

> This is the headline contract test from §2.3/§7.7/§15.2. It must be in the same security-contract suite as the PLG-cannot-construct-confidential test (Task 5). It exercises all four attack paths and asserts every one is denied.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/packages/mod-pooled-plane/tests/test_cross_tenant_read_denied.py
"""§7.7 contract: pooled-plane cross-tenant read denied across ALL paths.

Tenant A is authenticated and attempts to read tenant B's own-materials object:
  (1) by-ID / BOLA via the repo's object-authz Check (primary boundary),
  (2) via a direct RLS-scoped query under A's tenant context (defense-in-depth),
  (3) via a SECURITY DEFINER path (forbidden bypass must not leak),
  (4) via a borrowed PgBouncer connection after A's transaction COMMITs
      (SET LOCAL must not leak tenant context to the next borrower).
All four MUST be denied.
"""

import os
import pathlib

import psycopg
import pytest

from mod_identity.pooled_authz import AuthzDenied, PooledObjectAuthz
from mod_pooled_plane.own_materials_repo import OwnMaterialsRepo
from mod_pooled_plane.tenant_session import tenant_transaction

DSN = os.environ.get("TIGEREX_TEST_DSN")
MIG = pathlib.Path(__file__).parents[3] / "db" / "migrations"
pytestmark = pytest.mark.skipif(not DSN, reason="TIGEREX_TEST_DSN not set")


class FakeRebac:
    def __init__(self, grants: set[tuple[str, str]]) -> None:
        self._grants = grants

    def check(self, *, tenant_id: str, object_id: str) -> bool:
        return (tenant_id, object_id) in self._grants


@pytest.fixture()
def conn():
    c = psycopg.connect(DSN)
    for name in ("0d_app_role.sql", "0d_pooled_own_materials.sql"):
        c.execute((MIG / name).read_text())
    for tid, oid in (("tenantA", "a1"), ("tenantB", "secretB")):
        c.execute("SELECT set_config('app.tenant_id', %s, false)", (tid,))
        c.execute(
            "INSERT INTO own_materials (tenant_id, object_id, title) "
            "VALUES (%s, %s, %s)", (tid, oid, f"{tid}-secret"),
        )
    c.execute("RESET app.tenant_id")
    c.commit()
    yield c
    c.execute("DROP TABLE IF EXISTS own_materials CASCADE")
    c.execute("DROP ROLE IF EXISTS app_pooled")
    c.commit()
    c.close()


def test_path1_bola_by_id_denied(conn) -> None:
    authz = PooledObjectAuthz(FakeRebac({("tenantA", "a1")}))
    repo = OwnMaterialsRepo(conn, authz)
    with pytest.raises(AuthzDenied):
        repo.get("tenantA", "secretB")  # A asks for B's object by ID


def test_path2_direct_rls_query_under_A_context_returns_no_B_rows(conn) -> None:
    # Even if the authz Check were skipped, RLS under A's tenant context must
    # filter B's row out. Direct query for B's object_id while pinned to A.
    with tenant_transaction(conn, "tenantA") as cur:
        row = cur.execute(
            "SELECT object_id FROM own_materials WHERE object_id = %s",
            ("secretB",),
        ).fetchone()
    assert row is None


def test_path3_security_definer_path_does_not_leak(conn) -> None:
    # We do not ship a SECURITY DEFINER function (CI forbids it, Task 11).
    # Assert the forbidden bypass would be caught: scan the migrations and the
    # live catalog for any SECURITY DEFINER function over the tenant table.
    from ci.forbid_security_definer import scan_sql

    mig_files = sorted(MIG.rglob("*.sql"))
    assert scan_sql(mig_files) == []  # no forbidden bypass ships
    proname = conn.execute(
        "SELECT count(*) FROM pg_proc WHERE prosecdef = true "
        "AND prosrc ILIKE '%own_materials%'"
    ).fetchone()[0]
    assert proname == 0  # no SECURITY DEFINER fn touches own_materials


def test_path4_borrowed_pgbouncer_connection_after_A_txn_denied(conn) -> None:
    # Simulate connection reuse: A runs a transaction, COMMITs. The SAME
    # connection is then borrowed by B's request. SET LOCAL must NOT have
    # leaked A's tenant context; B sees only B's rows, and a query for A's
    # object under B's context returns nothing.
    with tenant_transaction(conn, "tenantA") as cur:
        cur.execute("SELECT object_id FROM own_materials WHERE object_id = 'a1'")
    leaked = conn.execute(
        "SELECT current_setting('app.tenant_id', true)"
    ).fetchone()[0]
    assert leaked in (None, "")  # no cross-borrow leak
    with tenant_transaction(conn, "tenantB") as cur:
        a_row = cur.execute(
            "SELECT object_id FROM own_materials WHERE object_id = 'a1'"
        ).fetchone()
    assert a_row is None  # B cannot see A's object on the borrowed connection
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && python -m pytest tests/test_cross_tenant_read_denied.py -q
```

Expected (with DSN): collection/import error initially if `ci` is not on the path, or assertion failures if any path leaks; without DSN it skips. The intent is RED → GREEN once Tasks 8–11 are in place and the `pep`/`ci` packages are importable.

- [ ] **Step 3: Write minimal implementation**

> No new production code — Tasks 6, 8, 9, 10, 11 already implement every boundary this test exercises. The only work here is making the cross-package imports resolve in the test environment. Add a `conftest.py` that puts the sibling packages on `sys.path`:

```python
# tigerexchange/packages/mod-pooled-plane/tests/conftest.py
"""Make sibling packages importable for the cross-tenant contract suite."""

import pathlib
import sys

_ROOT = pathlib.Path(__file__).parents[3]
for rel in ("packages/mod-identity/src", "packages/mod-pep/src", "tools/ci"):
    p = str(_ROOT / rel)
    if p not in sys.path:
        sys.path.insert(0, p)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/packages/mod-pooled-plane && python -m pytest tests/test_cross_tenant_read_denied.py -q
```

Expected: `4 passed` (with `TIGEREX_TEST_DSN`; CI runs this as a gating security-contract test).

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/packages/mod-pooled-plane/tests/test_cross_tenant_read_denied.py tigerexchange/packages/mod-pooled-plane/tests/conftest.py && git commit -m "test(pooled): §7.7 cross-tenant-read-denied contract (BOLA, direct, SECURITY DEFINER, borrowed PgBouncer)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: FastAPI auth dependency — token→TenantContext→PEP, end to end

**Files:** Modify `tigerexchange/services/api/src/api/dependencies.py` (the DI factory module OWNED by 0a — this plan adds the `authenticate_request` helper alongside 0a's `get_pep`/`get_*` factories), Create `tigerexchange/services/api/tests/test_auth_dependency.py`

> Ties identity to the PEP: a request's bearer token is verified, mapped to a frozen `TenantContext`, and a PLG token attempting a confidential action is denied at the single `PolicyEnforcementPoint` (resolved via 0a's `get_pep` factory) — the full §2.3 contract surfaced through the API. The handler calls the kernel `authorize(request)` — one arg, no `requested_tier`.

- [ ] **Step 1: Write the failing test**

```python
# tigerexchange/services/api/tests/test_auth_dependency.py
import pytest

from contracts import Capability, Decision, Edition, PepAction, PepRequest, Tier
from api.dependencies import authenticate_request, AuthError
from mod_identity.entitlement_evaluator import EntitlementEvaluator
from mod_identity.pooled_authz import PooledObjectAuthz
from mod_pep.policy_enforcement_point import PolicyEnforcementPoint


class FakeBroker:
    def __init__(self, claims: dict) -> None:
        self._claims = claims

    def verify_token(self, raw_token: str) -> dict:
        if raw_token != "good-token":
            raise ValueError("bad token")
        return self._claims


class FakeRebac:
    def __init__(self, grants: set[tuple[str, str]]) -> None:
        self._grants = grants

    def check(self, *, tenant_id: str, object_id: str) -> bool:
        return (tenant_id, object_id) in self._grants


class FakeClassifier:
    def __init__(self, tiers: dict[str, Tier]) -> None:
        self._tiers = tiers

    def tier_of(self, object_id: str | None) -> Tier:
        return Tier.public if object_id is None else self._tiers[object_id]


def test_authenticate_builds_plg_context() -> None:
    broker = FakeBroker({"eduPersonUniqueId": "pi@x.edu",
                         "eduPersonScopedAffiliation": ["faculty@x.edu"]})
    ctx = authenticate_request(
        broker=broker, raw_token="good-token",
        tenant_id="indiv", edition=Edition.PLG,
        consortium_ids=frozenset(), subject_active=True,
    )
    assert ctx.tenant_id == "indiv"
    assert ctx.entitlement.edition == Edition.PLG


def test_bad_token_rejected() -> None:
    broker = FakeBroker({})
    with pytest.raises(AuthError):
        authenticate_request(
            broker=broker, raw_token="forged", tenant_id="indiv",
            edition=Edition.PLG, consortium_ids=frozenset(), subject_active=True,
        )


def test_plg_confidential_request_denied_at_pep() -> None:
    broker = FakeBroker({"eduPersonUniqueId": "pi@x.edu"})
    ctx = authenticate_request(
        broker=broker, raw_token="good-token", tenant_id="indiv",
        edition=Edition.PLG, consortium_ids=frozenset(), subject_active=True,
    )
    # The ONE PEP (0c), wired with 0d's entitlement step + classifier (R2).
    # In the app this is built by 0a's get_pep factory; here we build it directly.
    pep = PolicyEnforcementPoint(
        entitlement_evaluator=EntitlementEvaluator(),
        pooled_authz=PooledObjectAuthz(FakeRebac({("indiv", "x")})),
        classifier=FakeClassifier({"x": Tier.confidential}),
    )
    req = PepRequest(
        request_id="r1", tenant=ctx, action=PepAction.RETRIEVE,
        required_capability=Capability.CONFIDENTIAL_WORKSPACE, resource_id="x",
    )
    resp = pep.authorize(req)  # kernel signature: one arg, no requested_tier
    assert resp.decision is Decision.DENY
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/services/api && python -m pytest tests/test_auth_dependency.py -q
```

Expected: `ImportError`/`AttributeError` — `authenticate_request`/`AuthError` not defined in 0a's `api.dependencies`.

- [ ] **Step 3: Write minimal implementation**

```python
# tigerexchange/services/api/src/api/dependencies.py  (additions; module OWNED by 0a)
"""API auth dependency: verify token -> frozen TenantContext (plan §7.1).

Added alongside 0a's get_* DI factories (get_pep, get_model_router,
get_lit_retrieval, get_draft_store, get_discovery, get_funding, get_audit_sink,
get_classifier, ...). The verified TenantContext is handed to the single
PolicyEnforcementPoint (resolved via get_pep) for every action; no API handler
authorizes directly. This is the request entry to the §2.3 "entitlements
evaluate at the PEP" contract.
"""

from __future__ import annotations

from typing import Protocol

from contracts import Edition, TenantContext

from mod_identity.context_builder import build_tenant_context


class AuthError(PermissionError):
    """Raised when a request cannot be authenticated (fail-closed)."""


class TokenVerifier(Protocol):
    def verify_token(self, raw_token: str) -> dict: ...


def authenticate_request(
    *,
    broker: TokenVerifier,
    raw_token: str,
    tenant_id: str,
    edition: Edition,
    consortium_ids: frozenset[str],
    subject_active: bool,
) -> TenantContext:
    """Verify the bearer token and build the request-scoped TenantContext."""
    try:
        claims = broker.verify_token(raw_token)
    except Exception as exc:  # broker raises TokenError/ValueError on bad token
        raise AuthError(f"token verification failed: {exc}") from exc
    try:
        return build_tenant_context(
            claims=claims,
            tenant_id=tenant_id,
            edition=edition,
            consortium_ids=consortium_ids,
            subject_active=subject_active,
        )
    except ValueError as exc:  # ClaimError (missing stable subject id)
        raise AuthError(str(exc)) from exc
```

> Ensure the `api` service `pyproject.toml` depends on `tigerexchange-mod-identity`, `tigerexchange-mod-pep` (the 0c PEP), `tigerexchange-mod-pooled-plane`, and `tigerexchange-contracts`. The test uses a `FakeBroker`/`FakeClassifier`, so no live IdP or classifier is needed.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy/tigerexchange/services/api && pip install -e . -q && python -m pytest tests/test_auth_dependency.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/services/api && git commit -m "feat(api): auth dependency verifies token -> frozen TenantContext, PLG confidential denied at PEP (§7.1/§2.3)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Wire the CI gates (security-contract suite + SECURITY DEFINER lint + import-linter)

**Files:** Modify `tigerexchange/.github/workflows/ci.yml` (or 0a's CI config), Test: CI dry-run locally

> The security-contract suite (PLG-cannot-construct-confidential + cross-tenant-read-denied) and the SECURITY DEFINER lint must be CI-gating, with a Postgres service container so the RLS/borrowed-connection tests actually run (not skip).

- [ ] **Step 1: Write the failing test**

> The "test" here is the local CI dry-run: with no `security-contract` job and no SECURITY DEFINER lint step, the gate is absent.

```bash
cd /home/anurag/codebase/tiger_research_buddy && grep -c "forbid_security_definer\|cross_tenant_read_denied\|security-contract" tigerexchange/.github/workflows/ci.yml || echo "GATE ABSENT"
```

Expected: `GATE ABSENT` (or `0`).

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anurag/codebase/tiger_research_buddy && grep -q "forbid_security_definer" tigerexchange/.github/workflows/ci.yml && echo PRESENT || echo "ABSENT (expected)"
```

Expected: `ABSENT (expected)`.

- [ ] **Step 3: Write minimal implementation**

```yaml
# tigerexchange/.github/workflows/ci.yml  (add this job)
  security-contract:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: pg
          POSTGRES_DB: tigerex_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      TIGEREX_TEST_DSN: "postgresql://postgres:pg@localhost:5432/tigerex_test"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install packages
        run: |
          pip install -e tigerexchange/packages/contracts
          pip install -e tigerexchange/packages/mod-pep
          pip install -e tigerexchange/packages/mod-pooled-plane
          pip install -e tigerexchange/packages/mod-identity
      - name: Forbid SECURITY DEFINER / matview over tenant tables (§7.7)
        run: PYTHONPATH=tigerexchange/tools/ci python -m ci.forbid_security_definer tigerexchange/db/migrations
      - name: Security-contract suite (§2.3 + §7.7)
        run: |
          python -m pytest \
            tigerexchange/packages/mod-identity/tests/test_entitlement_evaluator.py \
            tigerexchange/packages/mod-pooled-plane/tests/test_rls_migration.py \
            tigerexchange/packages/mod-pooled-plane/tests/test_cross_tenant_read_denied.py \
            -q
      - name: Kernel + module import-linter fitness
        run: |
          pip install import-linter
          (cd tigerexchange/packages/contracts && lint-imports)
          (cd tigerexchange/packages/mod-identity && lint-imports)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anurag/codebase/tiger_research_buddy && grep -q "forbid_security_definer" tigerexchange/.github/workflows/ci.yml && grep -q "cross_tenant_read_denied" tigerexchange/.github/workflows/ci.yml && echo "GATE PRESENT"
```

Expected: `GATE PRESENT`. (Optionally validate YAML: `python -c "import yaml,sys; yaml.safe_load(open('tigerexchange/.github/workflows/ci.yml'))"`.)

- [ ] **Step 5: Commit**

```bash
cd /home/anurag/codebase/tiger_research_buddy && git add tigerexchange/.github/workflows/ci.yml && git commit -m "ci: gate security-contract suite (§2.3 PLG + §7.7 cross-tenant) + SECURITY DEFINER lint on a Postgres service

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes for the implementing agent

- **Kernel is imported, never redefined.** `TenantContext`, `Edition`, `Entitlement`, `Capability`, `IsolationPosture`, `Tier`, `Decision`, `PepRequest`, `PepResponse`, `PepAction` all come from `contracts` verbatim (0b kernel). Do not re-declare them.
- **ONE PEP class (R1).** There is exactly one Policy Enforcement Point: `PolicyEnforcementPoint` (owned by 0c), implementing the kernel `IPolicyEnforcement.authorize(request: PepRequest) -> PepResponse`. This plan defines NO `PepService` and adds NO `requested_tier` kwarg to the kernel `authorize`. 0d's entitlement/pooled-authz logic is composed INTO that single PEP via an injected `EntitlementEvaluator` (entitlement step) + pooled object-authz `Check` (ReBAC step). The PEP resolves each object's tier from the classifier/broker lookup (R2) — never hardcoding `(Tier.confidential, frozenset())`; public/private objects take their correct non-confidential ABAC branch.
- **Phase-0 scope = SINGLE-TENANT own-data only.** The cross-institution sharing/exchange and the cross-institution revocation AUTHORITY are Phase-1+ (kernel interfaces stubbed, not active here). 0d's pooled plane holds each PLG tenant's OWN materials only; PLG `EXCHANGE_PARTICIPATION` / `CROSS_INSTITUTION_GRANTS` are hard-OFF and the PEP denies them structurally.
- **PgBouncer mode (§13.1):** the pooled plane assumes PgBouncer in transaction-pooling mode. The `SET LOCAL` approach in `tenant_session.py` is exactly what makes that mode safe (no `RESET ALL` needed, context dies at COMMIT). Do not switch to plain `SET`.
- **RLS is defense-in-depth, never sole boundary (§7.7).** The object-authz `Check` (Task 6) is the primary boundary; every read path must call it before touching SQL (Task 10 enforces the order).
- **Deferred seams untouched:** `IExchangeFeed`, `IRevocationAuthority`, confidential cross-institution grants, HYOK — all out of Phase-0 scope here. PLG's `EXCHANGE_PARTICIPATION` / `CROSS_INSTITUTION_GRANTS` capabilities are hard-OFF and the PEP denies them structurally; no exchange code ships.
- **SAML/eduGAIN is NOT shipped** (§7.1). `keycloak_broker.py` does Direct OIDC/CILogon verification only. Any campus/consortium SAML need is a later, separately-sized line.
- **Test DSN:** the Postgres-backed tests (Tasks 8, 9, 10, 12) skip without `TIGEREX_TEST_DSN`; CI (Task 14) supplies it via a Postgres 16 service container so they actually gate. The `app_pooled` role must be `NOSUPERUSER NOBYPASSRLS` or FORCE RLS is meaningless.