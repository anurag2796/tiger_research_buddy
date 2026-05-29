# Phase-0 Consistency Re-Check (after fix-up wf w0j0cd0j8)

Confirmed:
- **R6 zero-hits test path is RESOLVED**: both 0g and 0k now reference the identical path `packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py`.
- **R6 stray paths RESOLVED**: 0k no longer references `tigerexchange/modules/` or `app/main.py` or `app.dependencies` (grep returned nothing for those — only `api.dependencies` is used, owned by 0a, and the `services/api/src/api/app.py` mount path).

Now let me confirm the last two items: R8 (0a builds INTERFACE_LOCUS/KERNEL_API_VERSION as canonical) and R6 `get_pep` returns `IPolicyEnforcement`. I already saw 0a Task 8 explicitly states these are "canonical kernel symbols (defined in 00-kernel-contracts.md)" and the kernel `interfaces.py` now contains them (lines 924-967 of kernel). And 0a Task 13b defines `get_pep() -> IPolicyEnforcement`. Both confirmed from earlier reads. I have all evidence needed.

One last verification — the kernel `__init__.py` walrus artifact (R11): the kernel file at lines 1005-1007 still contains the `IRerankerLike := IReranker` walrus, but it's flagged as "an editing artifact" with a corrected block immediately after, and 0a Task 9 explicitly instructs to use the corrected version. Let me confirm 0a's instruction is unambiguous (it is — line 1343: "do **not** include the `IRerankerLike :=` walrus artifact"). That's a known-wrong-then-corrected pattern but it's in the canonical kernel doc, not a plan that ships it. I'll note it as a minor residual.

I have sufficient evidence for all R-items. Final report:

---

# TigerExchange Phase-0 Cross-Plan Consistency Re-Review (post-fixup)

Read: kernel `00-kernel-contracts.md` + all 11 sub-plans (`0a`–`0k`) + `_consistency-check.md` (the original punch-list). Verdicts below.

| Issue | Status | Evidence / needed follow-up |
|---|---|---|
| **R1** single `PolicyEnforcementPoint` + one `authorize` sig + one decision order (0c/0d) | **PARTIAL** | Class name (`PolicyEnforcementPoint`), kernel sig `authorize(request)->PepResponse`, no `PepService`, no `requested_tier` kwarg on `authorize`, and the 6-step order (entitlement→capability→ReBAC→ABAC→tombstone→lease) are now identical in 0c (`0c:9,1513,1836`) and 0d (`0d:9,961,2194`). **BUT a NEW break:** 0c builds the PEP at `services/pep/src/pep/pep.py` (module `pep.pep`) with ctor `(entitlement, classifier, rebac, abac, tombstone, lease, broker)` (`0c:1336,1398,1592`); 0d imports `from mod_pep.policy_enforcement_point import PolicyEnforcementPoint` at `packages/mod-pep/...` with ctor `(entitlement_evaluator, pooled_authz, classifier)` (`0d:959,980,1025,1096,1949`). Two different module paths/packages AND two incompatible constructor signatures for the one class → 0d's import + instantiation cannot resolve against 0c's PEP. Follow-up: pick one path (`pep.pep` vs `mod_pep.policy_enforcement_point`) and one ctor parameter set across 0c and 0d. |
| **R2** object classification not hardcoded confidential (0c) | **RESOLVED** | `PolicyEnforcementPoint._object_classification` resolves real `(tier, flags)` via injected `_ClassificationLookup`; unknown→confidential fail-closed (`0c:1567,1673,1841`). Test `test_public_object_resolves_non_confidential_tier_not_hardcoded` (`0c:1484`). |
| **R3** `IAuditSink.append` one-arg + no fabricated TenantContext (0e) | **RESOLVED** | Sink `append(event)` matches kernel; store method renamed `persist(event, tenant_id)` (string id, no TenantContext); explicit note "NO TenantContext is fabricated on the audit write path" (`0e:1391,1413,615`). Worker instructed to edit prior `append(event, tenant)` tests to one-arg. |
| **R4** `satisfies_locality(tier: Tier)` on concrete providers (0f) consistent with 0i | **RESOLVED** | 0f `InBoundaryProvider`/`CloudFrontierProvider`/`_ByoProvider` all implement `satisfies_locality(self, tier: Tier)` (kernel sig); `LocalityClass` is internal behind `serves_locality_class()` + `tier_required_localities()` (`0f:549,577,1255`). Matches kernel and 0i's `FakeModelRouter._Provider.satisfies_locality(tier)` and `IModelProvider` usage. |
| **R5** single central-index read PEP = 0j (0c dup dropped) | **RESOLVED** | 0j is sole `CentralIndexReadPEP` owner (`0j:12`); 0c Task 10 drops `filter_by_discoverability`/`_scope_permits` and asserts their absence (`0c:1711-1772`). `discoverability_scope` passed as enum throughout 0j. |
| **R6** packages/+services/ layout; `api.dependencies` factories by 0a, used by 0k; zero-hits test path consistent | **RESOLVED** | 0a Task 13b defines all `get_*` factories in `services/api/src/api/dependencies.py` returning kernel Protocols, fail-closed `NotWiredError` (`0a:2007-2136`). 0k imports only from `api.dependencies`, no `modules/`/`app.main`/`app.dependencies` stray paths remain. Zero-hits test path identical in 0g and 0k: `packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py` (`0g:1210`, `0k:44,1425,1505`). |
| **R7** `classification.classifier` everywhere | **RESOLVED** | Every reference uses `classification.classifier`; no `classifier.engine`/`classification.engine`/`classification_engine` variants remain (0b authoritative; 0c/0e/0k import-linter forbidden_modules all match; 0c:1844 explicit note). |
| **R8** `KERNEL_API_VERSION`/`InterfaceLocus`/`INTERFACE_LOCUS` canonical in kernel + 0a | **RESOLVED** | Kernel `interfaces.py` now defines all three with a comment "They are part of the canonical kernel; 0a legitimately re-exports them" (kernel:924-967, `__all__` 1050-1051). 0a Task 8 builds them verbatim, explicitly labeled "canonical kernel symbols ... NOT non-canonical additions" (`0a:1072,1149,1397`). |
| **R9** single-tenant scope notes on 0g/0c/0e | **RESOLVED** | Explicit "Phase-0 scope = SINGLE-TENANT own-data only" blocks: 0c Task 5 (`0c:709`), 0e Task 5 (`0e:872`), 0g (per-tenant own-data, `IRevocationAuthority`/`IExchangeFeed` stubbed). Also echoed in 0d:2195 and 0k:9. |
| **R11** no known-wrong-then-patch / conditional placeholders | **PARTIAL** | 0f Task 8 COGS "validate-then-rewrite" and 0g Task 8 "provisional then delete/replace" patterns — could not fully verify removal (those task bodies not in the pages read); flagged in original punch-list (`_consistency-check:47-49`) as must-fix. 0b Task 1 placeholder guidance similar. Kernel `__init__.py` still literally contains the `IRerankerLike := IReranker` walrus artifact (kernel:1005), though flagged as "editing artifact" with a corrected block after, and 0a Task 9 explicitly says "do not include the walrus artifact" (`0a:1343`) — so it cannot ship, but the canonical doc still carries the wrong line inline. Follow-up: confirm 0f Task 8 / 0g Task 8 ship only the reconciled arithmetic in one block, and scrub the kernel doc's walrus line. |

## NEW breakage introduced by the edits
1. **R1 PEP module-path + constructor divergence (real, blocking).** 0c → `pep.pep.PolicyEnforcementPoint(entitlement=, classifier=, rebac=, abac=, tombstone=, lease=, broker=)`; 0d → `mod_pep.policy_enforcement_point.PolicyEnforcementPoint(entitlement_evaluator=, pooled_authz=, classifier=)`. The class name/signature collision was fixed but a path+ctor collision was substituted in its place. 0d's `test_pep_entitlement_wired.py` and `test_auth_dependency.py` import a module 0c never creates.
2. **0j `PepResponse.action` — RESOLVED, no longer a break.** The `read_pep.py` comment notes `PepResponse` has no `action` field; 0j Task 6 Step 3 explicitly instructs removing `assert resp.action is PepAction.DISCOVER` and the unused `PepAction` import before running (`0j:1279-1298`). Clean, but relies on the worker applying that edit.

## Residual fixes needed
- **Reconcile the single PEP's module path and constructor across 0c and 0d** (highest leverage; the only blocking break). Decide `pep.pep` vs `mod_pep.policy_enforcement_point` and one ctor parameter set; update 0d's two imports + `_pep(...)`/`PolicyEnforcementPoint(...)` calls and `pip install -e .../mod-pep` lines, or update 0c's path/package.
- **Confirm 0f Task 8 and 0g Task 8 ship only the reconciled COGS arithmetic** (no superseded-then-rewritten block in one step) — R11 partial.
- **Scrub the canonical kernel `00-kernel-contracts.md` `__init__.py` walrus artifact** (`IRerankerLike := IReranker`) so the authoritative doc doesn't carry a known-wrong line, even though 0a is instructed to skip it.

Net: 8 of 10 R-items RESOLVED (R2, R3, R4, R5, R6, R7, R8, R9); R1 and R11 PARTIAL. One new blocking inconsistency (PEP path/ctor mismatch 0c↔0d) introduced during the fix-up.


---

# Per-file fix changelogs


## 00-kernel-contracts.md

All R8 edits are applied. Changelog below.

Changelog for /home/anurag/codebase/tiger_research_buddy/plans/phase0/00-kernel-contracts.md:

- **R8 (interfaces.py code block):** Added a new "Kernel-interface versioning / evolution contract" section after the deferred-seam `IRevocationAuthority` stub, defining `KERNEL_API_VERSION: int = 1`, the `InterfaceLocus` StrEnum with members `intra_cell`/`cross_node`, and the frozen `INTERFACE_LOCUS: dict[str, InterfaceLocus]` mapping every kernel interface name to its locus (the two deferred federation seams → `cross_node`; all Phase-0-active interfaces → `intra_cell`).
- **R8 (interfaces.py imports):** Added `from enum import StrEnum` to the `interfaces.py` import header (it previously imported only from `typing`), so `InterfaceLocus` can subclass `StrEnum`. Added a short clarifying note after the new mapping confirming the import.
- **R8 (`__init__.py` — first/active import block):** Added `from contracts.interfaces import (INTERFACE_LOCUS, KERNEL_API_VERSION, InterfaceLocus)`.
- **R8 (`__init__.py` — `__all__`):** Appended `"KERNEL_API_VERSION", "InterfaceLocus", "INTERFACE_LOCUS"` under a new "kernel-interface versioning / evolution contract (R8)" comment, exporting them from the contracts package.
- **R8 (`__init__.py` — corrected/duplicate import block):** Added the same three-symbol import to the second (post-walrus-artifact) `__init__.py` block shown later in the doc, so both displayed blocks remain consistent.
- **R8 (Summary section):** Added a bullet documenting the new versioning contract so the prose summary matches the code.

Fixes NOT applied (out of scope for this file — they target other sub-plan files 0a–0k, not the canonical kernel contracts):
- **R1–R7, R9, R10, R11:** All target PEP/classifier/audit-store/provider/layout/naming concerns in the 0a–0k sub-plan files. None of those constructs (PolicyEnforcementPoint, PepService, filter_by_discoverability, COGS tasks, classifier-module-name references, DI factories, scope notes, etc.) exist in 00-kernel-contracts.md, so there was nothing to change here. Per instructions, these are skipped for this file. The kernel was kept otherwise frozen — only the R8 amendment was added.

Note: the file's pre-existing `IRerankerLike :=` walrus editing-artifact in the first `__init__.py` block was left untouched (it is already flagged in-document with a corrected block and was not part of these fixes).

## 0a-foundation.md

All edits complete. Let me do a final consistency check on the `__all__` block ordering and the import block — specifically that `KERNEL_API_VERSION` appears in `__all__` (it does, line 1404) and that the import from `contracts.interfaces` now includes it.

The edits are internally consistent. Here is the changelog.

## Changelog — `plans/phase0/0a-foundation.md`

**R8 (KERNEL_API_VERSION / InterfaceLocus / INTERFACE_LOCUS as CANONICAL exports — aligned to amended kernel):**
- **Task 8 intro prose** (~line 1072): reframed the locus structure from "operationalizes the convergence-report HIGH" (an addition) to **canonical kernel symbols** defined in `00-kernel-contracts.md` under the R8 amendment, which 0a builds verbatim and re-exports — explicitly "NOT non-canonical additions."
- **Task 8 test (`test_interfaces.py`)**: removed the now-unused `from typing import get_args` import; updated `test_locus_values_are_valid` to iterate the `InterfaceLocus` StrEnum and assert values `{"intra_cell", "cross_node"}` (was the hyphenated `Literal` form); updated `test_federation_seam_interfaces_are_cross_node` to assert `IExchangeFeed`/`IRevocationAuthority` are `cross_node` (was asserting `IModelProvider` cross-node, which contradicts the amended kernel where `IModelProvider` is `intra_cell`); updated `test_cell_local_pep_is_intra_cell` to use `is InterfaceLocus.intra_cell`.
- **Task 8 Step 3 implementation block**: replaced the `Literal["intra-cell","cross-node"]` locus appendix with the canonical block from `00-kernel-contracts.md` verbatim — `KERNEL_API_VERSION: int = 1`, `class InterfaceLocus(StrEnum)` with members `intra_cell`/`cross_node`, and the `INTERFACE_LOCUS` mapping (all Phase-0-active interfaces `intra_cell` including `IModelProvider`; only `IExchangeFeed`/`IRevocationAuthority` `cross_node`). Noted `StrEnum` is already imported.
- **Task 9 `__init__.py` block**: now imports `KERNEL_API_VERSION` (alongside `INTERFACE_LOCUS`, `InterfaceLocus`) **from `contracts.interfaces`** rather than re-declaring it locally; replaced the local `KERNEL_API_VERSION: int = 1` definition with a comment stating these three are canonical kernel symbols re-exported here. `__all__` already lists all three.

**R6 (0a OWNS `services/api/src/api/dependencies.py` + every `get_*` DI factory; app path):**
- **File Structure table**: added `services/api/src/api/dependencies.py` (0a-owned DI factory module) and `tests/test_dependencies.py` rows.
- **New Task 13b** (inserted between Task 13 and Task 14, preserving all existing numbering): full TDD task creating `api/dependencies.py` defining all eight required factories — `get_pep`, `get_model_router`, `get_lit_retrieval`, `get_draft_store`, `get_discovery`, `get_funding`, `get_audit_sink`, `get_classifier` — as fail-closed `NotWiredError` stubs typed against the kernel Protocols, with failing-test → run → implement → pass → commit structure.
- **App path**: already `services/api/src/api/app.py` (Task 13 / File Structure) — verified correct, no change needed. No `app/main.py` or top-level `modules/` references exist in this file (verified).
- **Task 19 acceptance checklist**: added a line item asserting the `api.dependencies` DI seam defines every factory and is fail-closed when un-wired (`test_dependencies.py`).

**R7 (classifier uses `classification.classifier`):**
- No `classifier.engine` / `classification.engine` / `classification_engine` variants exist in this file. The only new classifier reference (the `get_classifier` factory docstring in Task 13b) is written as `classification.classifier` per spec.

**Fixes NOT applicable to this file (correctly skipped):**
- R1 (PEP unification), R2 (object classification), R3 (audit sink arity / store `persist`), R4 (model provider locality), R5 (central-index read PEP), R9 (single-tenant scope notes), R10 (DiscoverabilityScope/epoch naming), R11 (no known-wrong-then-patch / placeholders): these target sub-plans 0b–0k. 0a is the foundation (monorepo, kernel types, RLS, FastAPI skeleton, CI) and contains none of those constructs — no PEP class, no audit store, no model providers, no classifier impl, no COGS tasks, no `DiscoverabilityScope`-string passing.

**Flag (no change made):** Task 9's `test_kernel_size_bounded` enforces `total_lines <= 900`. The R8 StrEnum locus block is slightly larger than the prior `Literal` form, but it mirrors `00-kernel-contracts.md` verbatim, so 0a stays consistent with the canonical source. If the assembled kernel ever trips the 900-line ceiling, that ceiling (not the canonical content) is what should be adjusted.

## 0b-classification-engine.md

No module-name variants exist (R7 already satisfied), and the only remaining "placeholder" mention is the new explicit instruction NOT to create placeholders. 

Let me also check the other R11-adjacent conditional language in Task 9 Step 3 and Task 10 Step 3 ("Apply this edit ONLY if..."). The task scope for R11 in this file is explicitly limited to "Task 1 Step 4" — Task 9/10's conditional edits are part of the failing-test-then-harden TDD loop, not the known-wrong-then-patch antipattern that R11 targets (which the spec scopes to 0f/0g Task 8 and 0b Task 1 Step 4). I'll leave those untouched as they're out of the assigned scope. The R7/R11 fixes assigned to this file are complete.

Changelog:

- **R11 (Task 1, Step 4) — APPLIED.** Lines ~121–128. Removed the conditional placeholder guidance: deleted the parenthetical claiming the test is "deferred" / green-via-later-tasks, and deleted the entire "NOTE for the worker: ...create stub modules / one-line placeholders ONLY if you run Step 4 before Task 6" paragraph. Reordered so the import smoke test explicitly runs ONCE after Tasks 2–6 land all four re-exported modules (`config`, `classifier`, `queue`, `ingest_gate`), with an explicit "Do not create placeholder modules" instruction. Step header retitled to "Run test to verify it passes (AFTER Tasks 2–6 land)". The TDD step structure (failing test -> run -> implement -> pass -> commit), section numbering, and all other content preserved.

- **R7 (package `classification` / module `classification.classifier`) — ALREADY SATISFIED, no edit needed.** The file already uses package `classification` and module `classification.classifier` verbatim everywhere (e.g. `from classification.classifier import FailClosedClassifier`, file-structure table, `__init__.py`). A grep confirmed ZERO occurrences of the banned variants `classifier.engine`, `classification.engine`, or `classification_engine`. This file contains no import-linter / `forbidden_modules` contract, so there is no import-linter reference to reconcile here.

Fixes NOT applied (out of scope for this file's assigned fixes):
- The reconciliation spec's R6 (canonical layout `tigerexchange/packages/...` vs. this file's `tigerexchange/services/classification/...`) was NOT touched — only R7 and R11 were assigned to this file. The directory layout discrepancy exists but is an R6 concern not listed in this file's fix set.
- Task 9 Step 3 and Task 10 Step 3 contain "Apply this edit ONLY if the test reveals..." conditional language, but these are part of the legitimate TDD harden-on-failure loop, not the known-wrong-then-patch antipattern; R11's stated scope for this file is limited to Task 1 Step 4, so they were left unchanged.

## 0c-pep-broker-chokepoint.md

All fixes applied. Here is the changelog.

## Changelog for `/home/anurag/codebase/tiger_research_buddy/plans/phase0/0c-pep-broker-chokepoint.md`

**R1 — PEP unification (single `PolicyEnforcementPoint`, kernel `authorize`, canonical decision order with injected entitlement step):**
- Updated the top **Goal** and **Architecture** paragraphs to state there is ONE PEP class `PolicyEnforcementPoint` implementing kernel `IPolicyEnforcement.authorize(request) -> PepResponse`, explicitly noting NO `PepService` and NO `requested_tier` kwarg, and listing the full 6-step canonical order (entitlement/edition → capability → ReBAC → ABAC → durable tombstone → lease).
- Rewrote the `pep.py` module docstring (Task 9) to the canonical 6-step order and the "0d entitlement logic composed INTO this PEP, not a second PEP class" framing.
- Added an injected `_EntitlementEvaluator` Protocol; added `entitlement=` to `PolicyEnforcementPoint.__init__`; inserted the entitlement/edition gate as decision step 1 (before the capability gate) in `authorize`.
- Updated the Task 9 test harness: added `_FakeEntitlement`, threaded `entitled=` through `_build`, and added `test_entitlement_gate_short_circuits_before_capability_and_rebac`.

**R2 — real per-object classification (no hardcoded confidential):**
- Replaced `_object_classification`'s hardcoded `return Tier.confidential, frozenset()` with a lookup via an injected `_ClassificationLookup` Protocol (0b classifier/broker table); unknown/missing resolves fail-closed to confidential, public/private resolve to true tier.
- Added `classifier=` to `__init__`, imported `ComplianceFlag`/`TenantContext`/`Tier` in `pep.py`.
- Updated Task 9 test: added `_FakeClassifier`, `tier_table=` in `_build`, and `test_public_object_resolves_non_confidential_tier_not_hardcoded`.

**R5 — drop duplicate `filter_by_discoverability`:**
- Rewrote Task 10 to DELETE the duplicate free function and its `_scope_permits` helper from `pep.pep`; the task now asserts (via `test_central_index_pep.py`) that 0c has no duplicate and that the sole scope filter lives in 0j's `CentralIndexReadPEP` (using `pytest.importorskip` for the 0j seam). Updated the two File-Structure table rows accordingly.

**R7 — `classification.classifier` in import-linter:**
- Changed `forbidden_modules` from `classifier.engine` to `classification.classifier` (Task 1 pyproject + test assertion), the pyproject D4 comment, and the Task 11 verification-gate prose.

**R9 — single-tenant scope note on tombstone/lease:**
- Added the explicit "Phase-0 scope = SINGLE-TENANT own-data only … cross-institution revocation AUTHORITY is Phase-1+ (kernel interfaces stubbed, not active here)" note to Task 5 (revocation tombstone/lease).

**Supporting:** updated expected pass counts (Task 9: 9→11) and the "Notes on decisions encoded" section to add bullets for R1/R2/R5/R7/R9, replacing the old note that documented the hardcoded-confidential behavior.

**Not applied:** R3, R4, R6, R8, R10, R11 — these target other files (0a/0b/0d/0e/0f/0g/0h/0j/0k and the kernel doc); none had a matching construct in 0c, so they were correctly out of scope for this file. Section numbering and the failing-test → run → implement → pass → commit TDD structure were preserved throughout.

## 0d-identity-entitlement.md

All 14 tasks retain the full TDD 5-step structure. All edits are complete.

## Changelog

Fixed `plans/phase0/0d-identity-entitlement.md` in place. All 14 tasks and the TDD failing-test → run → implement → pass → commit structure preserved.

**R1 — PEP unification (primary fix):**
- Architecture paragraph rewritten: states there is ONE `PolicyEnforcementPoint` (0c) implementing kernel `IPolicyEnforcement.authorize(request: PepRequest) -> PepResponse`; 0d injects an `EntitlementEvaluator` + pooled object-authz as the entitlement/ReBAC steps; spells out the canonical 6-step decision order; explicitly states NO second PEP and NO `requested_tier` kwarg.
- Task 7 fully rewritten: removed the `PepService` class and the non-kernel `authorize(request, *, requested_tier=...)` signature. Now shows the `EntitlementEvaluator` + `PooledObjectAuthz` injected INTO 0c's `PolicyEnforcementPoint`, with kernel-conformant `authorize(request)` (one arg). Tests construct the PEP via injection and call `pep.authorize(req)`.
- Task 5 header + evaluator docstring reframed as the injected internal entitlement step (not a PEP, does not implement the kernel interface); clarified its `requested_tier` is the PEP-resolved tier, not a kernel-authorize kwarg.
- Task 13 test: replaced `PepService()` + `pep.authorize(req, requested_tier=...)` with `PolicyEnforcementPoint(...)` injection + `pep.authorize(req)`.
- Added a "ONE PEP class (R1)" note to the Notes section.
- File Structure table: dropped the `pep_service.py` create/modify row; entitlement/pooled-authz rows moved into `mod-identity`; added a reference row noting the PEP is 0c-owned.

**R2 — object classification:** Task 7 PEP impl + tests now resolve each object's tier from an injected classifier (`tier_of`), explicitly NOT hardcoding `(Tier.confidential, frozenset())`. Added a test asserting a public object resolves to `Tier.public` and takes the non-confidential branch. Reflected in the architecture and R1 notes.

**R6 — project layout + DI:** Migrated all paths from `tigerexchange/services/mod_identity` → `packages/mod-identity`, `services/pooled_plane` → `packages/mod-pooled-plane` (Python pkg `pooled_plane` → `mod_pooled_plane`), and the PEP-injected modules into `packages/mod-identity`. PEP class placed at `packages/mod-pep/`. Task 13 auth helper moved from `api/src/api/deps.py` → `api/src/api/dependencies.py` (the 0a-owned DI module), with a note tying it to `get_pep` and the other `get_*` factories. CI install steps and package-dep lists updated (`tigerexchange-pep` → `tigerexchange-mod-pep`, added `mod-pooled-plane`). The conftest sys.path siblings updated to the new package dirs. FastAPI app remains under `services/api/` per the canonical layout.

**R9 — single-tenant scope note:** Added explicit "Phase-0 scope = SINGLE-TENANT own-data only; cross-institution sharing/exchange and revocation authority are Phase-1+ (kernel interfaces stubbed, not active here)" note to the Notes section.

**Fixes NOT applied (do not apply to this file):**
- R3 (audit sink arity), R4 (model-provider locality), R5 (central-index read PEP / `filter_by_discoverability`), R8 (kernel `KERNEL_API_VERSION`/`InterfaceLocus`), R10 (`discoverability_scope`/`revocation_epoch` vs `projection_version`), R11 (0f/0g/0b known-wrong-then-patch): none of these constructs appear in 0d — they target 0a/0b/0c/0e/0f/0g/0h/0i/0j/0k.
- R7 (classifier module name `classification.classifier`): no `classifier.engine`/`classification.engine`/`classification_engine` variant or classifier import-linter contract exists in 0d, so there was no verbatim string to correct; the classifier is referenced only via a fake/stand-in in Task 7.

## 0e-audit-spine.md

All edits are in place and consistent. The `store.head(tenant_id, stream_id)` already took two strings and no TenantContext, so that part of R3 was already correct.

Changelog of edits applied to `/home/anurag/codebase/tiger_research_buddy/plans/phase0/0e-audit-spine.md`:

**R3 — Audit sink arity (primary fix, applied):**
- Task 1 minimal store stub (`store.py`): renamed Protocol method `append(event, tenant: TenantContext)` → `persist(event, tenant_id: str)`; dropped the `TenantContext` import; added a comment explaining the rename avoids conflation with the kernel one-arg `IAuditSink.append(event)`.
- Task 3 store test (`test_sink_append.py`): removed the now-unused `_ctx()` helper that built a full `TenantContext`; rewrote all five store-level calls from `store.append(event, _ctx())` to `store.persist(event, "<tenant_id>")`; renamed three test functions (`test_persist_increments_sequence_per_stream`, `test_head_returns_last_persisted`, `test_persist_rejects_nonmonotonic_sequence`).
- Task 3 complete store (`store.py`): renamed Protocol `append` → `persist(event, tenant_id: str)`, dropped `TenantContext` import, expanded the Protocol docstring; renamed `InMemoryAuditChainStore.append` → `persist`, changed its guard to compare against the `tenant_id` string.
- Task 6 sink (`sink.py`): updated the intermediate two-arg `append` to call `self._store.persist(finalized, tenant.tenant_id)`; in the kernel one-arg `append` replacement, changed `self._store.append(...)` → `self._store.persist(finalized, event.tenant_id)` and **deleted the fabricated `_bound_tenant_context` static helper** (the synthesized TenantContext with fake Edition/Entitlement) entirely; updated the surrounding prose note about the store-level signature to say `persist(event, tenant_id)`, never `append`.
- Task 8 Postgres store (`store.py`): dropped `TenantContext` import; renamed `PostgresAuditChainStore.append(event, tenant)` → `persist(event, tenant_id: str)`, updated the guard and `self._pin(cur, tenant_id)` call.
- Task 8 Postgres test (`test_postgres_rls.py`): removed the unused `make_tenant` import; rewrote all `store.append(event, make_tenant(...))` calls to `store.persist(event, "<tenant_id>")`; renamed `test_append_and_read_under_rls` → `test_persist_and_read_under_rls`.
- `store.head(tenant_id, stream_id)` already took no TenantContext (two strings) — verified, no change needed.

**R7 — Classifier module name:** Not applicable to this file. No references to `classification.classifier` or the forbidden variants (`classifier.engine`, `classification.engine`, `classification_engine`) exist; the only `forbidden_modules` list (Task 1 import-linter contract) names `mod_lit_intelligence/mod_discovery/mod_funding_lite/mod_pep` and no classifier module. Skipped.

**R9 — Single-tenant scope note on signed-checkpoint tasks (applied):** Added an explicit blockquote note to Task 5 ("Signed chain-head checkpoints + control-plane sink") stating Phase-0 scope = SINGLE-TENANT own-data only, that cross-institution sharing/exchange and cross-institution revocation authority are Phase-1+ with `IExchangeFeed`/`IRevocationAuthority` stubbed-not-active, and that the control-plane sink is in-process (no external/cross-institution anchoring wired).

Note on what was deliberately left intact: the section numbering, the TDD step structure, and the Task 6 "write two-arg sink, then correct to the kernel one-arg signature" narrative were preserved. R11 (known-wrong-then-patch removal) targets 0f/0g/0b per the spec and was not in this file's fix list, so the Task 6 two-version narrative was not collapsed. The intentionally-pre-migration `sink.append(event, tenant)` calls inside the Task 4/5 test bodies are left as the plan documents their one-arg migration during Task 6 (lines describing the `grep`/replace step).

## 0f-model-router.md

The COGS implementation is now a single, clean, correct band-based version. The `gpu_cost_per_month` parameter is retained in the signature (the docstring explains it documents the underlying list price for audit) which keeps the test calls valid.

Both fixes are complete. The `is_in_boundary()` helper and `tier_required_localities()` mapping keep `LocalityClass` internal behind the kernel `satisfies_locality(tier: Tier)` signature, and the COGS task ships one corrected computation.

Changelog:

**R4 — Model provider locality (kernel `satisfies_locality(tier: Tier) -> bool`):**
- `locality.py` (Task 1, Step 3): added `from contracts import Tier` and a new internal helper `tier_required_localities(tier: Tier) -> frozenset[LocalityClass]` that maps a tier to its permitted locality classes; expanded the module docstring to state `LocalityClass` is internal and sits behind the kernel signature. The Task 1 test was untouched (it only exercises `is_in_boundary()`).
- `providers.py` (Task 3, Step 3): `InBoundaryProvider`, `CloudFrontierProvider`, and `ProviderRegistry` reworked so each concrete provider exposes the kernel-conformant `satisfies_locality(self, tier: Tier) -> bool` (delegating through `tier_required_localities`) plus an internal `serves_locality_class(self, locality: LocalityClass) -> bool`. `ProviderRegistry.conformant` now filters via `serves_locality_class`. Imported `Tier` from contracts.
- `test_providers_registry.py` (Task 3, Step 1): assertions split into kernel `satisfies_locality(Tier.*)` checks and internal `serves_locality_class(LocalityClass.*)` checks.
- `router.py` (Task 4, Step 3): the non-public in-boundary-preference loop now calls `serves_locality_class` instead of `satisfies_locality(LocalityClass…)`.
- `test_router.py` (Task 4, Step 1): two locality-class assertions switched to `serves_locality_class`.
- `transport_guard.py` (Task 5, Step 3): `verify()` re-check now uses `provider.serves_locality_class(loc)`.
- `test_router_transport_agreement.py` (Task 5, Step 1): the cloud assertion switched to `serves_locality_class`.
- `byo.py` (Task 6, Step 3): `_ByoProvider` now implements kernel `satisfies_locality(tier: Tier)` plus internal `serves_locality_class`; imported `Tier` and `tier_required_localities`.
- `test_byo.py` (Task 6, Step 1): two provider locality assertions switched to `serves_locality_class`.

**R11 — COGS, ship corrected band-based `recompute_confidential_cogs` once (Task 8, Step 3):**
- Replaced the initial `_NON_GPU_MONTHLY_USD = 2_500.0` constant with the band constants `_SHARED_BASIS_ANNUAL_USD`/`_DEDICATED_BASIS_ANNUAL_USD` directly in the implementation block.
- Deleted the wrong first-version `recompute_confidential_cogs` (the `gpu_share` / `_NON_GPU_MONTHLY_USD` body), the "validate the arithmetic… that exceeds the $43k upper bound" prose, the duplicate band-constants snippet, the "then replace the body" rewrite snippet, and the "remove the unused constant/lines" note. The single remaining `recompute_confidential_cogs` is the correct band-based version; a one-line arithmetic-check sentence was kept.

Notes:
- No fixes were skipped; both R4 and R11 applied to this file.
- One residual typing nuance (not in scope of the two fixes): `ProviderRegistry.conformant`, `TransportEgressGuard.verify`, and `ModelRouter.route` call `serves_locality_class` on values typed as the kernel `IModelProvider` Protocol (which only declares `satisfies_locality(tier)`). This mirrors the file's pre-existing pattern of accessing concrete-provider attributes (`getattr(p, "is_fallback", …)`), so it is internally consistent, but a strict `mypy` run could flag `attr-defined` on those calls.
- File edited in place: `/home/anurag/codebase/tiger_research_buddy/plans/phase0/0f-model-router.md`. Section numbering, all 10 tasks, and the failing-test→run→implement→pass→commit TDD structure preserved.

## 0g-confidential-kek-stores.md

The contract-test path is consistent and already correct at every reference. No stray `tests/contract/...` paths exist. R6 requires no edit to this file.

Changelog:

- **R11 (Task 8 Step 3) — applied.** Replaced the known-wrong-then-patch sequence in `confidential_cogs/table_b.py` with a single reconciled implementation. Deleted the provisional `_NON_GPU_LINE_ITEMS` block (cell $1000 / spicedb $300 / HSM $600 / KMS $200, summing to $2,500/mo), the two prose paragraphs explaining why those figures were wrong, and the throwaway "replace the HSM line" comment block. Now ships the reconciled band-based line items ONCE (cell-share $550, vec/graph/lexical $400, spicedb+revlog $150, HSM $300, KMS $100 = $1,500/mo non-GPU), with both `CogsTable` definitions (shared-GPU K=2 -> $3,500/mo/$42k/yr; sovereign K=1 -> $5,500/mo/$66k/yr) and the reconciliation basis folded into the module docstring. TDD step structure (failing test -> run -> implement -> pass -> commit) preserved; only Step 3's implementation body changed.

- **R9 (single-tenant scope note) — applied.** Added an explicit bullet at the top of the "Notes on scope and the two highs addressed" section carrying the canonical note: Phase-0 scope = SINGLE-TENANT own-data only; cross-institution sharing/exchange and cross-institution revocation AUTHORITY are Phase-1+ (`IExchangeFeed`/`IRevocationAuthority` stubbed, not active); 0k confidential draft persistence depends on 0g and stays single-tenant.

- **R6 (contract-test path) — already correct, no edit needed.** The zero-decryptable-hits contract test is already specified at exactly `tigerexchange/packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py` in the File Structure table (line 33) and throughout Task 6 (created by 0g). No `tests/contract/...` variant exists anywhere in the file.

Section numbering, the six-stage TDD step structure, and all other content were preserved.

## 0h-ingestion-pipelines.md

All edits landed. The grep at line 13 only matches because the new prohibition note lists the variant names as forbidden (inside the "never ..." clause) — no actual variant usage exists in code/imports. Section numbering, TDD step structure, and all other content are preserved.

Changelog for `/home/anurag/codebase/tiger_research_buddy/plans/phase0/0h-ingestion-pipelines.md`:

**R7 — classifier module name `classification.classifier` verbatim (incl. import-linter):**
- Edited the **Depends on** line (Goal/header area): made the 0b classifier reference verbatim — `IClassifier` "implemented in the `classification.classifier` module — the canonical classifier module name", plus an explicit prohibition of the variants `classifier.engine` / `classification.engine` / `classification_engine`.
- Edited the Task 1 import-linter contract comment (`[tool.importlinter]` in `pyproject.toml`): clarified the classifier is reached only via the kernel `IClassifier` Protocol injected from 0b's `classification.classifier` module, never by importing its internals; and added `"classification.classifier"` to the `forbidden_modules` list so the no-sibling-internals contract names the canonical module verbatim.
- Edited the `resources.py` docstring (Task 11): changed "(IClassifier from 0b)" to "(IClassifier, implemented by 0b's `classification.classifier` module)".
- No variant strings (`classifier.engine`, `classification.engine`, `classification_engine`) were present anywhere in the file, so there was nothing to rewrite/eliminate — only the canonical name to make explicit.

**R10 — per-CELL `revocation_epoch` vs per-RECORD `projection_version` distinct; `discoverability_scope` as the `DiscoverabilityScope` enum:**
- No edits needed — both sub-requirements were already satisfied:
  - The two-field epoch model is already kept rigorously distinct (Task 6 `ProjectionVersion` per-(tenant,record) vs `CellRevocationEpoch` per-cell; Task 7 applier rejects on `projection_version` only; Task 11 emits both in distinct `OutboxEvent` fields; the Notes section forbids cross-comparison). Verified no place conflates the two names.
  - `discoverability_scope` is already passed as the enum member `DiscoverabilityScope.PUBLIC_WEB` (Task 9 builder and test), never a raw string. Grep confirmed zero raw-string assignments.

No fixes were skipped due to inapplicability beyond the R10 items above, which were already compliant. Section numbering and the failing-test → run → implement → pass → commit structure are fully preserved.

## 0i-retrieval-eval.md

All fixes verified. The remaining `.value` at line 1797 is `str(exc.value)` (an exception object's `.value` attribute in a pytest test), unrelated to discoverability — correctly left alone. All `discoverability_scope` usages now pass the `DiscoverabilityScope` enum member.

Changelog of edits to `/home/anurag/codebase/tiger_research_buddy/plans/phase0/0i-retrieval-eval.md`:

- **R7 (classifier module name)** — line 124, import-linter `forbidden_modules`: changed `"classification.engine"` → `"classification.classifier"` (the canonical 0b module name).
- **R10 / R5 (DiscoverabilityScope enum, not raw string)** — line 759, `FakePEP` payload row: changed `DiscoverabilityScope.FEDERATION_WIDE.value` → `DiscoverabilityScope.FEDERATION_WIDE` (pass the enum member, not its raw string `.value`).
- **R10 / R5 (DiscoverabilityScope enum coercion)** — `HybridRetriever._pep_gate` projection construction: changed `discoverability_scope=row["discoverability_scope"]` → `discoverability_scope=DiscoverabilityScope(row["discoverability_scope"])`, and added `DiscoverabilityScope` to the `from contracts import (...)` block in `hybrid_retriever.py` so the coercion resolves.
- **R5 (CentralIndexReadPEP delegation)** — "Notes for the implementing worker" → dependency-seams: added a note stating this package does cell-local `PepAction.RETRIEVE` gating only, that all `discoverability_scope`-based central-index read filtering is delegated to 0j's authoritative `CentralIndexReadPEP`, that this package carries no local copy of that scope-filter, and that `discoverability_scope` always crosses the seam as the enum member.

Fixes NOT requiring a change (already consistent, confirmed):

- **R4 (model-provider locality)** — The file already uses the kernel signature `satisfies_locality(tier: Tier) -> bool` verbatim (conftest `_Provider`, the `_MisroutingRouter._Cloud` adversary, and `judge_router.route_judge`). No `LocalityClass` symbol appears anywhere, and no concrete provider is defined here (providers come from 0f). No edit needed.
- **R5 (IReranker is the only kernel reranker surface)** — Task 4 already documents that the kernel `IReranker.rerank(...)` operates on `PublishableProjection`s while `rerank_candidates(...)` and the `Candidate` value object are package-local internals (also reaffirmed in the closing Notes). No edit needed.

All edits were targeted; section numbering, TDD step structure (failing test → run → implement → pass → commit), and all other content were preserved.

## 0j-central-index-read-pep.md

The R5 edit is in place and consistent with the rest of the file. The `CentralIndexReadPEP` class is the sole scope-filter implementation throughout; the new note pins it as authoritative and instructs 0c to drop its duplicate.

Changelog:

- **R5 applied** (the listed fix for this file): Inserted a `> **R5 — SOLE central-index read-PEP authority**` blockquote note immediately after the Architecture paragraph (line 12). It asserts that `0j`/`CentralIndexReadPEP` is the single authoritative central-index read PEP using the owner-committed monotonic scope-epoch (`ScopeRegistry.current_scope`), instructs `0c` to drop/thin-delegate its duplicate `filter_by_discoverability` free function so there is exactly one scope-filter codepath, and pins `discoverability_scope` to always be passed as the `DiscoverabilityScope` enum member (never a raw string).

- **R5/R10 enum-passing requirement — already satisfied, no edit needed:** Verified via grep that the file contains zero raw-string `discoverability_scope`/`scope=` passes in any logic layer. Every `ScopeCommit`, `PublishableProjection`, `DiscoveryQuery`, and `PepResponse` construction passes `DiscoverabilityScope.*` enum members; the only `.value` usage is in `api.py` for HTTP/JSON wire serialization, which is correct. The new note documents this as an invariant.

Fixes NOT applied (not in scope for this file):

- **R1, R2, R3, R4, R6, R7, R8, R9, R11** — These target other sub-plans (0c PEP unification/object classification, audit-sink/store in 0c/0e, model providers in 0f, project-layout/DI in 0a, classifier naming in 0b, kernel amendment in 0a/00, single-tenant scope notes in 0c/0e/0g, COGS/placeholder cleanup in 0f/0g/0b). None of those code paths exist in `0j`: this file does not import the classifier, touch the audit sink/store, define `PolicyEnforcementPoint`/`PepService`, hardcode `(Tier.confidential, frozenset())`, define model providers, or build the 0a DI factory module. The reconciliation spec lists only **R5** for this file, which is now applied.

One observation (not edited, since it falls under R11 which is explicitly scoped to 0f/0g/0b, not 0j): Task 6 Step 1/Step 3 contains a self-acknowledged known-wrong-then-patch pattern — the authz test is written with `assert resp.action is PepAction.DISCOVER` (a field the canonical `PepResponse` does not have), then a long note instructs removing that assertion before Step 4. This is the same anti-pattern R11 forbids elsewhere, but R11 does not list 0j, so I left it untouched per the "skip fixes that don't apply to this file" instruction. Flagging it in case you want a follow-up pass to fold the corrected test directly into Step 1.

## 0k-feature-modules.md

All 12 tasks and section structure intact. The fixes are complete.

Changelog of edits to `/home/anurag/codebase/tiger_research_buddy/plans/phase0/0k-feature-modules.md`:

**R6 — project layout + DI (applied throughout):**
- Architecture paragraph: rewrote to state modules live under `tigerexchange/packages/mod-*/`, dependencies come from the `api.dependencies` DI factory module owned by 0a, and the zero-hits suite is owned by 0g.
- File Structure table: relocated every path from `tigerexchange/modules/...` to `tigerexchange/packages/mod-{lit-intelligence,discovery,funding-lite}/src/mod_*/...`; tests to `packages/mod-*/tests/...`; app row from `tigerexchange/app/main.py` to `tigerexchange/services/api/src/api/app.py`; contract-test row to `tigerexchange/packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py`.
- All Python import statements: `modules.lit_intelligence` → `mod_lit_intelligence`, `modules.discovery` → `mod_discovery`, `modules.funding_lite` → `mod_funding_lite`; test-fixture imports `tests.modules.X` → `mod_X.tests.*`; `ModuleNotFoundError` expected strings updated to match.
- All code-block path comments, `Files:` bullets, `pytest` commands, and `git add` commands across Tasks 1-12 updated to the `packages/mod-*/src/mod_*` and `packages/mod-*/tests` layout.
- Removed the obsolete top-level `modules/__init__.py` namespace-marker code block; replaced with prose stating each mod-* is its own `src/`-layout installable package (no shared `modules` namespace), with deps injected via `api.dependencies`.
- Task 8 AST test: replaced single `MODULES_ROOT` with `MODULE_SRC_ROOTS` covering all three `packages/mod-*/src/mod_*` roots; loops updated accordingly.
- Import-linter contract: `source_modules` now `mod_lit_intelligence`/`mod_discovery`/`mod_funding_lite`.
- Task 9 zero-hits test references the exact 0g-owned path; removed the invented `tests/contract/__init__.py` creation step; replaced the cross-package `FakeKek` import with a locally-defined `FakeKek` double (0g owns the suite).

**Remove app/main.py (R6):**
- Task 11: app target is `tigerexchange/services/api/src/api/app.py`; test imports `from api.app import app`; wiring imports from `api.dependencies` (listing the canonical `get_*` factories incl. `get_lit_intelligence`, `get_pep`, `get_audit_sink`, etc.) owned by 0a. Removed the original `app.main`/`app.dependencies` references and a transiently-introduced broken placeholder block.

**R7 — classifier module name:**
- import-linter `forbidden_modules` and the AST `FORBIDDEN_IMPORT_PREFIXES`: `classification_engine` → `classification.classifier`. File Structure table and Notes section reference updated too.

**R9 — single-tenant scope notes:**
- Added explicit "Phase-0 scope = SINGLE-TENANT own-data only..." note to the Architecture paragraph, the draft_store table row, the Task 2 intro (blockquote), and the `draft_store.py` module docstring.

**Fix not applied (out of scope for this file):**
- R10 (`discoverability_scope` as `DiscoverabilityScope` enum vs raw strings; per-CELL `revocation_epoch` vs per-RECORD `projection_version`): the test fixtures here pass raw strings (e.g. `discoverability_scope="federation-wide"`) to `PublishableProjection`, but R10 names 0h as the owner and the per-file fix list for 0k specifies only R6/R7/R9 + app/main.py removal. Left to its owning files per instructions. Note: the reconciliation spec's "every file must agree" implies a future pass may want these test fixtures to use `DiscoverabilityScope.FEDERATION_WIDE` etc. — flagging for awareness.

All other content, the 12-task section numbering, and the TDD step structure (failing test → run → implement → pass → commit) are preserved.