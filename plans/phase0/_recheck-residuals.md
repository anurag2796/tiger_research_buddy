# Phase-0 Residuals Re-Check (pass 2, wf wia31g16j)

All symbols `table_b.py` imports (`CogsLineItem`, `CogsTable`, `GpuAmortization`) and the gate functions (`d7_ratio`, `passes_d7_floor`, `gross_margin`, `passes_margin_gate`) are defined in 0g Task 7's `cogs_model.py`. No dangling imports. The `__init__.py` re-exports them. COGS internally consistent: $42k shared (passes D7 2.86x, margin 65%), $66k dedicated (fails D7 at $120k, passes at $150k).

All three fixes verified. Here is the status.

## TigerExchange Phase-0 Residual-Fix Re-Verification

| # | Fix | Status | Evidence |
|---|-----|--------|----------|
| 1 | PEP path + ctor consistent across 0c/0d | **RESOLVED** | Both use module `mod_pep.policy_enforcement_point`, class `PolicyEnforcementPoint` (`0c:9,29,1537,1639`; `0d:30,980,1136,1927`). Canonical keyword-only ctor `(*, entitlement_evaluator, classifier, rebac, abac, tombstone, lease, broker, pooled_authz)` stated identically (`0c:1903`; `0d:30,1139,2208`). 0d's two instantiations match it exactly (`0d:1063-1072` and `0d:2016-2025`). No `services/pep`/`PepService`/second PEP class in either plan body. |
| 2 | 0f Task 8 & 0g Task 8 COGS = one corrected band-based block; numbers match | **RESOLVED** | 0f Task 8 (`0f:1602-1711`) is a single clean `gpu_isolation.py` block: bands `_SHARED_BASIS_ANNUAL_USD=(36_000,43_000)` and `_DEDICATED_BASIS_ANNUAL_USD=(66_000,72_000)` (`0f:1634-1635`); no provisional/recompute-then-delete scaffolding. 0g Task 8 (`0g:1666-1723`) is a single clean `table_b.py` computing COGS from line-item data: shared K=2 → $42k/yr (in 36-43k), dedicated K=1 → $66k/yr (in 66-72k) (`0g:1683-1684,1707-1708`). |
| 3 | No `IRerankerLike :=` walrus; one clean canonical `__init__.py`; 0a Task 9 reproduces clean form | **RESOLVED** | Grep for `IRerankerLike` / `:=` returns **zero hits** in both `00-kernel-contracts.md` and `0a-foundation.md`. 00's `__init__.py` block is one clean canonical block (`00:978-1053`). 0a Task 9 reproduces it cleanly with `INTERFACE_LOCUS/KERNEL_API_VERSION/InterfaceLocus` imported from `contracts.interfaces` and a clean `__all__` (`0a:1345-1423`), no artifact reference. |

### New-breakage scan
- **No dangling imports:** Every symbol `0g table_b.py` imports (`CogsLineItem`, `CogsTable`, `GpuAmortization`) and every gate function the tests call (`d7_ratio`, `passes_d7_floor`, `gross_margin`, `passes_margin_gate`) is defined in 0g Task 7 `cogs_model.py` (`0g:1480-1539`) and re-exported via `__init__.py` (`0g:1551-1565`).
- **No broken numbering:** 0f Tasks 7→8→9 and 0g Tasks 7→8→9 are sequential and unduplicated.
- **No COGS arithmetic drift:** 0f's in-line arithmetic check (`0f:1713`) and 0g's ($42k shared passes D7 2.86x / margin 65%; $66k dedicated fails D7 at $120k=1.82x, passes at $150k) are mutually consistent; `SOVEREIGN_MIN_ACV == 150_000` (`0g:1653,1694`).
- **No leftover stale class names in plan bodies:** `services/pep`, `PepService`, and the old `requested_tier` kwarg appear **only** in the historical review-tracking files (`README.md:61`, `_recheck-after-fixup.md`, `_consistency-check.md:15`), which describe the now-fixed prior state — they are not part of the executable 0c/0d/0f/0g/0a/00 plan bodies. No action needed unless those tracking docs are meant to be refreshed.

**Residual follow-up:** None blocking. Optional only: the three meta/review docs (`README.md`, `_recheck-after-fixup.md`, `_consistency-check.md`) still narrate the pre-fix `services/pep`/`PepService` mismatch as an open item; if they are intended to reflect current state, update their status lines — but they do not affect any plan's correctness.


---

# Per-fix changelogs


## pep-0c-0d

Both files have balanced code fences. All edits are complete and consistent.

## Summary

Reconciled both Phase-0 plan files to the single canonical PEP decision (module path `tigerexchange/packages/mod-pep/src/mod_pep/policy_enforcement_point.py`, package `mod-pep`, class `PolicyEnforcementPoint`, keyword-only ctor `(*, entitlement_evaluator, classifier, rebac, abac, tombstone, lease, broker, pooled_authz)`, kernel `authorize(request)` with no `requested_tier`).

### `0c-pep-broker-chokepoint.md` — edits
- **Architecture paragraph (line 9):** stated the canonical module path/package/import and noted `pooled_authz` is the pooled-plane object-authz step.
- **File Structure table (lines 21-39):** rewrote all 19 rows from `tigerexchange/services/pep/src/pep/...` to `tigerexchange/packages/mod-pep/src/mod_mod_pep/...`; `pep.py` → `policy_enforcement_point.py`; migrations/tests dirs moved under the package.
- **All file paths (≈70 occurrences):** `tigerexchange/services/pep/` → `tigerexchange/packages/mod-pep/`, `src/pep/` → `src/mod_pep/`, `pep.py` → `policy_enforcement_point.py`.
- **All Python imports/module refs:** `from pep.pep import` / `import pep.pep` / bare `pep.pep` → `mod_pep.policy_enforcement_point`; `pep.{abac,broker,broker_db,decision_order,rebac,revocation}` → `mod_pep.*`.
- **pyproject.toml:** `name = "tigerexchange-pep"` → `tigerexchange-mod-pep`; `packages = ["src/pep"]` → `["src/mod_pep"]`; `root_package = "pep"` → `mod_pep`; added `tigerexchange-mod-identity` dependency; import-linter `source_modules`/`forbidden_modules` now `mod_pep.*`.
- **Constructor (Task 9):** renamed `entitlement` → `entitlement_evaluator` and **added `pooled_authz`** (now 8 keyword-only params); added `self._pooled_authz`; added a `_PooledObjectAuthz` structural Protocol and `IsolationPosture` import.
- **`authorize` decision order:** threaded `pooled_authz.require_object_access(...)` into the ReBAC step for `IsolationPosture.POOLED` tenants (deny-by-default, catches `AuthzDenied`); updated module docstring step list.
- **Test (`test_pep_compose.py`):** renamed the `_FakeEntitlement` ctor kwarg to `entitlement_evaluator=`, added a permissive `_FakePooledAuthz` fake, and added `pooled_authz=` to the `_build` factory.
- **Notes section:** updated the R1 note with the canonical path and full constructor signature.

### `0d-identity-entitlement.md` — edits
- **Removed the divergent second PEP definition (Task 7 Step 3):** deleted the competing `class PolicyEnforcementPoint` with its thin 3-arg ctor; replaced with prose stating 0c owns the single class/constructor and 0d only injects collaborators (no code defined in 0d).
- **`_pep(...)` factory (Task 7):** changed the thin 3-arg call to the full canonical 8-arg call; reconciled `FakeClassifier` from `tier_of(...)` to 0c's `classify_resource(...) -> (Tier, frozenset)` surface; added permissive fakes (`_AllowSpice`, `_AllowOpa`, `_EmptyLog`, `_FakeStore`) for the unexercised collaborators.
- **API test (`test_auth_dependency.py`, Task 13):** same fixes — `FakeClassifier` → `classify_resource`, added permissive fakes + `mod_pep.*` imports, and expanded the `PolicyEnforcementPoint(...)` call to the canonical 8-arg form.
- **File Structure Reference row (line 30):** corrected the PEP location from `contracts/src/contracts/` to the canonical `mod_pep/policy_enforcement_point.py` and listed the full constructor signature.
- **Notes section:** updated the "ONE PEP class" note to "ONE PEP class + ONE constructor," citing the canonical signature and that 0d defines no constructor.

Section numbering, TDD step structure, and all unrelated content preserved. Code fences verified balanced in both files.

### Flag (pre-existing, out of scope)
There is a latent interface mismatch between the entitlement evaluator's method name: 0c's `authorize` calls `self._entitlement.permits(request) -> (bool, str)` (0c Task 9, line ~1668), but 0d's real `EntitlementEvaluator` exposes `evaluate(request, *, requested_tier) -> PepResponse` (0d Task 5). This divergence predates this task and is outside the residual's stated scope (module-path + constructor + `pooled_authz`). I did not alter it; it should be reconciled separately if the evaluator is to drop into the PEP unchanged.

## cogs-0f-0g

This is the key finding. The `_recheck-after-fixup.md` document (lines 209 and 222) confirms that **the residual #2 anti-pattern has ALREADY been fixed in BOTH files** by a prior pass:

- **0f Task 8** (line 209): the wrong first-version `recompute_confidential_cogs` (the `gpu_share`/`_NON_GPU_MONTHLY_USD` body) and the "validate-then-rewrite" prose were already deleted; the single remaining version is the correct band-based one.
- **0g Task 8** (line 222): the provisional `_NON_GPU_LINE_ITEMS` block (summing to $2,500/mo) and the throwaway "replace" comment were already deleted; it now ships the reconciled band-based line items once.

This matches exactly what I observed when reading the live files: both COGS tasks currently ship a single clean reconciled block with bands matching the authoritative numbers, and no provisional-then-replace scaffolding.

Let me do a final verification that the current shipped numbers in both files exactly match the authoritative bands from §16.1 Table B, since the instruction says "if it does not, make the single shipped block match these bands."

**0f Task 8** (live, lines 1634-1709): `_SHARED_BASIS_ANNUAL_USD = (36_000, 43_000)`, `_DEDICATED_BASIS_ANNUAL_USD = (66_000, 72_000)`. Matches.

**0g Task 8** (live, lines 1699-1722): non-GPU = $1,500/mo; shared K=2 → $3,500/mo = $42k/yr (band $3.0-3.6k/$36-43k); dedicated K=1 → $5,500/mo = $66k/yr (band $5.5-6k/$66-72k). Matches.

Both are already correct. No edits are needed. The residual was already closed by the documented prior fixup pass.

---

**Residual #2 — already resolved; no edits required.**

I read both target files in full (the COGS tasks) and cross-checked against the authoritative §16.1 Table B in `/home/anurag/codebase/tiger_research_buddy/plans/final-plan-v2.md`. The "known-wrong-then-rewrite" anti-pattern that this residual targets has **already been removed from both files by a prior fixup pass**, documented at `/home/anurag/codebase/tiger_research_buddy/plans/phase0/_recheck-after-fixup.md:209` (0f) and `:222` (0g).

What the current (live) files ship:

- **`/home/anurag/codebase/tiger_research_buddy/plans/phase0/0f-model-router.md`, Task 8 (lines 1514-1731):** A single clean `gpu_isolation.py` block. `recompute_confidential_cogs` uses `_SHARED_BASIS_ANNUAL_USD = (36_000, 43_000)` and `_DEDICATED_BASIS_ANNUAL_USD = (66_000, 72_000)` (lines 1634-1635), returning band-midpoints. Followed by one concise arithmetic-check sentence (line 1713). No superseded provisional block, no "now recompute/replace/delete" instruction. Five code fences total (test/impl/commands only).
- **`/home/anurag/codebase/tiger_research_buddy/plans/phase0/0g-confidential-kek-stores.md`, Task 8 (lines 1590-1751):** A single clean `table_b.py` block. One `_NON_GPU_LINE_ITEMS` tuple summing to $1,500/mo (lines 1699-1708), yielding shared-GPU K=2 = $3,500/mo / $42k/yr and dedicated K=1 = $5,500/mo / $66k/yr. The reconciliation rationale lives in the module docstring; no provisional-then-replace scaffolding.

Both shipped blocks already match the authoritative bands (shared-GPU K=2 ~$3.0-3.6k/mo / ~$36-43k/yr; Confidential-Sovereign dedicated ~$5.5-6k/mo / ~$66-72k/yr), so per the instruction ("if the existing corrected block already matches these, just remove the provisional-then-replace scaffolding") there is nothing left to remove. Section numbering and TDD structure are intact.

**Edits made: none** — the residual was already closed; making changes would have risked re-introducing churn into a correct, reconciled state.

Note (out of scope, flagging only): the same anti-pattern still genuinely exists in two *non-COGS* locations not covered by this residual — `0g` Task 3 (`envelope.py` "Replace `_dek`/`__init__`" at lines 641-682) and `0j` Task 6 (`PepAction.DISCOVER` known-wrong test, per `_recheck-after-fixup.md:281`). Those are separate from Residual #2.

## walrus-kernel-0a

No remaining references to the artifact in either file. Residual #3 is closed.

Edits made:

1. `/home/anurag/codebase/tiger_research_buddy/plans/phase0/00-kernel-contracts.md`
   - In the `__init__.py` code block: removed the walrus line `IRerankerLike := IReranker,  # noqa: F821  (see below)` and the standalone `from contracts.interfaces import IReranker, IRetrievalStrategy, IRevocationAuthority` line; folded `IReranker`, `IRetrievalStrategy`, `IRevocationAuthority` into the single canonical `from contracts.interfaces import (...)` block so it imports `IReranker` normally.
   - Removed the redundant prose note + the entire "corrected `__init__.py` import block" that followed the code block (the "drop the `IRerankerLike :=` walrus line above — it was an editing artifact … use the corrected import block" passage and its duplicated import snippet).
   - Removed the trailing summary caveat line that flagged the editing artifact ("One caveat flagged: the first `__init__.py` block contains an editing artifact …").

2. `/home/anurag/codebase/tiger_research_buddy/plans/phase0/0a-foundation.md`
   - Task 9, Step 3 instruction (line 1343): removed the now-unnecessary parenthetical "(the CORRECTED version — do **not** include the `IRerankerLike :=` walrus artifact)", leaving "Replace … with the canonical single-import-surface block, and add `KERNEL_API_VERSION`:".

Note: 0a Task 9's reproduced `__init__.py` block already imported `IReranker` normally (no walrus artifact present), so it required no change and is now consistent with the kernel doc. Verified via grep that no `IRerankerLike`, `walrus`, "editing artifact", or "corrected" references remain in either file.


---

## Follow-up: entitlement collaborator reconciled (post pass-2)

The PEP reconciliation surfaced a 4th mismatch: 0c's PEP called `self._entitlement.permits(request) -> (bool, str)` while 0d's `EntitlementEvaluator` exposes `evaluate(request, *, requested_tier) -> PepResponse`. Closed by editing 0c only (Protocol + authorize call + `_FakeEntitlement` test fake) to use `evaluate(request, requested_tier=tier) -> PepResponse`, short-circuiting on non-`Decision.ALLOW`. Verified: no `.permits(` references remain in 0c; 0d unchanged and consistent; kernel `PepResponse`/`Decision` field names matched.