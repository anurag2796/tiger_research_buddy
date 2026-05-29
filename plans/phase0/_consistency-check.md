# Phase-0 Cross-Plan Consistency Punch-List

I'll review the sub-plans against the canonical kernel and Phase-0 scope. Let me work through each category systematically.

Looking at the kernel's authoritative signatures, the SCOPE/DEFER boundaries, and cross-plan references, here is the punch-list.

# Cross-Plan Consistency Review — TigerExchange Phase-0

## (a) Interface / type / method-signature / property-name MISMATCHES

- **[0e-audit-spine / Task 3,6,8] `IAuditSink.append` signature mismatch.** Kernel: `append(self, event: AuditEvent) -> AuditEvent`. Plan stores/sink use `append(event, tenant)` (two-arg) throughout Task 3/6/8, then mid-Task-6 self-corrects the *sink* to one-arg but leaves `InMemoryAuditChainStore.append(event, tenant)` two-arg and tells the worker to hand-edit prior tests. -> Fix: freeze on kernel one-arg `append(event)` for `IAuditSink`; keep the store's two-arg as a clearly-distinct internal method name (e.g. `store.persist(event, tenant)`) so it is never confused with the kernel seam.

- **[0e-audit-spine / Task 1] `IAuditSink.head` argument vs kernel.** Kernel: `head(self, stream_id) -> AuditEvent | None`. Plan's store layer uses `head(tenant_id, stream_id)` and the sink resolves a bound tenant. Internally consistent but the `_bound_tenant_context` fabricates a full `TenantContext` (Edition/Capability/Entitlement) purely to satisfy the store — fabricated entitlement on an audit write path. -> Fix: give the store a `head(tenant_id, stream_id)` that needs no `TenantContext`; do not synthesize an Entitlement.

- **[0c-pep-broker / Task 9 + 0d-identity / Task 7] PEP class name + `authorize` signature collision.** 0c builds `PolicyEnforcementPoint.authorize(request) -> PepResponse` (kernel `IPolicyEnforcement`). 0d's Task 7 modifies a class it calls `PepService` with `authorize(request, *, requested_tier=Tier.public)`. These are two different class names for the one PEP, and the extra `requested_tier` kwarg is not on the kernel `IPolicyEnforcement.authorize`. -> Fix: single class name across 0c/0d; drop `requested_tier` from the public `authorize` (derive tier internally) or document it as a non-kernel internal entrypoint, not `IPolicyEnforcement`.

- **[0d-identity / Task 5] `EntitlementEvaluator.evaluate(request, *, requested_tier)` is not a kernel method** and 0c's PEP (Task 9) has no entitlement-evaluator step. The two PEP compositions diverge: 0c order = capability-gate→ReBAC→ABAC→tombstone→lease; 0d inserts entitlement-gate→pooled-authz first. -> Fix: reconcile one canonical decision order that includes both the entitlement gate and the ReBAC/ABAC/tombstone/lease chain; 0c and 0d currently describe different `authorize` bodies for the same single PEP.

- **[0c-pep-broker / Task 9] `PolicyEnforcementPoint._object_classification` returns hardcoded `(Tier.confidential, frozenset())`.** Flagged in-plan as a seam, but it means every `authorize` runs the confidential ABAC path regardless of resource — a correctness mismatch with 0i/0k which pass public/private resources through the same PEP. -> Fix: resolve per-object tier from the broker/classifier lookup, or scope this stub so non-confidential callers (0i retrieval, 0k funding) are not forced onto the confidential branch.

- **[0i-retrieval / Task 4,7] `IReranker.rerank` vs `rerank_candidates`.** Kernel `IReranker.rerank(query, candidates: Sequence[PublishableProjection], *, top_k) -> list[PublishableProjection]`. Plan adds a non-kernel `rerank_candidates(query, candidates: Sequence[Candidate], top_k)` and the `HybridRetriever` calls `rerank_candidates`, not the kernel `rerank`. Acceptable as an internal helper but `Candidate` is a package-local type not in the kernel — ensure no other plan expects `IReranker` to operate on `Candidate`. Clean within 0i; just confirm the kernel `rerank` adapter stays the only `IReranker` surface other plans import.

- **[0f-model-router / Task 1] `IModelProvider.satisfies_locality(tier: Tier)` vs router's `LocalityClass`.** Kernel signature takes a `Tier`. 0f's providers implement `satisfies_locality(locality: LocalityClass)` — a different parameter type than the kernel Protocol. 0i's `FakeModelRouter._Provider` correctly implements the kernel `satisfies_locality(tier: Tier)`. So 0f's concrete providers do NOT satisfy the kernel `IModelProvider` Protocol. -> Fix: 0f providers must implement `satisfies_locality(tier: Tier)` per the kernel; the `LocalityClass` mapping must live behind that kernel signature, not replace it.

- **[0d-identity / Task 13] `BrokerConfig` imported in test but unused / `TokenVerifier` Protocol vs `OidcBroker`.** Minor: `authenticate_request` takes a `TokenVerifier` Protocol; the real `OidcBroker.verify_token` matches. Consistent. No fix.

## (b) References to types/functions in NO plan and NOT in the kernel

- **[0d-identity / Task 13 + Task 11] `app/dependencies.py` / `app.main` wiring.** 0d Task 13 edits `api/deps.py`; 0k Task 11 imports a long list of factories from `app.dependencies` (`get_lit_retrieval`, `get_model_router`, `get_draft_store`, ...). No plan defines `app/dependencies.py` or these factories; 0a builds `services/api/src/api/app.py` with no such module. -> Fix: assign ownership of `app/dependencies.py` (likely 0a or a wiring task in 0k) and define every `get_*` factory, or 0k Task 11 references undefined symbols.

- **[0k-feature-modules] path mismatch `tigerexchange/modules/` and `tigerexchange/app/main.py`.** 0a establishes `services/api/` + `packages/`; every other plan uses `packages/` or `services/`. 0k introduces top-level `modules/` and `app/main.py` not created by 0a. -> Fix: relocate under the established `packages/`/`services/` layout or have 0a/0k create `modules/` + `app/main.py` explicitly.

- **[0k-feature-modules / Task 9] `tests/contract/test_post_crypto_shred_zero_hits.py` is "modified".** That file is owned by 0g, but 0g creates its zero-hit test at `tigerexchange/packages/mod-confidential-crypto/tests/test_post_shred_zero_hits.py` — a different path. 0k's "the post-crypto-shred zero-decryptable-hits contract test" references a `tests/contract/` suite that no plan creates. -> Fix: point 0k at 0g's actual test module path, or have 0g create the shared `tests/contract/` suite both reference.

- **[0c-pep-broker / Task 1] `classifier.engine` forbidden-import target.** import-linter contract forbids `classifier.engine`; 0b's package is `classification` with module `classification.classifier` (no `classifier.engine`). 0k forbids `classification_engine`. Three different names for the classifier module across plans. -> Fix: standardize the classifier package/module name (0b is authoritative: `classification.classifier`) and use it verbatim in all import-linter contracts.

- **[0h-ingestion / Task 11] `from contracts import Tier` local import inside assets** plus `discoverability_scope` passed as raw string `"federation-wide"` to `PublishableProjection` in 0h/0i/0j/0k tests. Kernel field is typed `DiscoverabilityScope`; Pydantic will coerce the StrEnum value, so functional, but inconsistent (some plans pass the enum, some the string). Not a hard break. -> Optional fix: pass `DiscoverabilityScope` members uniformly.

## (c) Placeholder / TBD / "similar to Task N" violations

- **[0a-foundation / Task 1] `contracts/__init__.py` "empty stub for now ... populated in Tasks 2-9".** Deliberate scaffolding, replaced in Task 9. Acceptable (each task lands real code), but the kernel's own `__init__.py` is canonical and frozen — 0a re-deriving it task-by-task risks drift from the authoritative surface. -> Fix: 0a Task 9 must reproduce the canonical `__init__.py` exactly (it adds `KERNEL_API_VERSION`, `INTERFACE_LOCUS`, `InterfaceLocus` not in the canonical surface — see (e)).

- **[0b-classification / Task 1, Step 4] "create one-line placeholder modules ONLY if you run Step 4 before Task 6 ... Do not leave placeholders after Task 6."** Explicit conditional placeholders. -> Fix: remove the placeholder guidance; order tasks so the import smoke test runs after the modules exist (no placeholder path).

- **[0c-pep-broker / Task 9 notes] `_object_classification` stub** "left as a clean seam, not stubbed with placeholder logic" — but it IS placeholder logic (`return Tier.confidential, frozenset()`). See (a). -> Fix as above.

- **[0f-model-router / Task 8] mid-task "Validate the arithmetic ... Adjust ... Edit ... to make the COGS bands match".** The plan ships a first implementation then tells the worker to rewrite it within the same step because the first arithmetic is wrong ($54k vs stated $36–43k). Not a TODO, but a known-wrong-then-patch in one step. -> Fix: write the corrected band-based `recompute_confidential_cogs` once; drop the superseded version.

- **[0g-confidential-kek / Task 8] same pattern:** provisional `_NON_GPU_LINE_ITEMS` summing to $4.5k, then "Re-read §16.1 ... Replace ... Delete the earlier provisional block." Known-wrong-then-replace within one task. -> Fix: ship only the reconciled line items.

- **[0h-ingestion / Task 13 Step 3] "no new code expected; if an import fails, correct the symbol name".** Conditional/vague. Minor. Acceptable as a verification task.

## (d) Phase-0 SCOPE-coverage GAPS

- **GAP: Guardrails partially covered.** SCOPE lists "Model Router (D-AI) ... guardrails." 0f Task 7 builds generation guardrails (egress re-check, injection filter, tier-pinned tools) — covered. No gap. ✓

- **GAP: "RAGAS-in-CI eval harness that MUST be PEP-gated (high finding about un-PEP-gated gold-set)."** 0i covers it. ✓

- **GAP: Keycloak + CILogon OIDC brokering.** 0d Task 4 covers Direct OIDC/CILogon verification. ✓ (SAML correctly deferred.)

- **GAP: SPECTER2 vectors ingestion.** 0h Task 3 reads SPECTER2 vectors. ✓

- **GAP: entity resolution / author disambiguation.** 0h Task 5. ✓

- **Real GAP — `IModelProvider` BYO + cloud-frontier production providers vs SCOPE "BYO provider/keys per tenant".** 0f Task 6 builds BYO registration. ✓ Covered.

- **Real GAP — pooled-plane object-authz (PLG: public + own-materials only, confidential/exchange hard-OFF).** 0d Task 6/8. ✓

- **Real GAP — Audit spine "per-stream hash-chain audit sink."** 0e. ✓

- **Real GAP — central-index read PEP with discoverability_scope.** Covered TWICE: 0c Task 10 (`filter_by_discoverability`) AND 0j (full `CentralIndexReadPEP`). -> **Overlap/conflict, not a gap:** two independent implementations of the central-index read PEP scope filter with different signatures (0c free function vs 0j class + owner-committed scope-epoch). 0j is the more complete (share-correctness) version. -> Fix: designate 0j as authoritative; 0c should drop or defer its `filter_by_discoverability` to avoid two divergent scope-filter implementations.

- **No uncovered SCOPE item found** otherwise; monorepo/RLS/contracts/PEP/classifier/router/ingestion/retrieval/audit/identity/mod-lit/mod-discovery/mod-funding all have an owning plan.

## (e) Plans straying into DEFERRED Phase-1+ scope

- **[0g-confidential-kek-stores] entire plan is largely DEFERRED scope.** DEFER explicitly lists "confidential cross-institution sharing grants, the revocation authority + tombstone log ... HYOK/per-tenant HSM." 0g builds per-tenant KEK/DEK envelope encryption + crypto-shred across confidential derivative stores. Phase-0 SCOPE does NOT list confidential-tier derivative-store crypto-shred as a deliverable — the kernel only stubs `IRevocationAuthority` Phase-1+. The COGS reconciliation (Table-B) is in-scope as a gate, but the KEK/crypto-shred machinery + per-subject erasure is Phase-1+ confidentiality build-out. -> Fix: confirm 0g is intended for Phase-0; if so, SCOPE must be amended to include it. As written it exceeds the strict Phase-0 anchor-MVP and overlaps the deferred revocation/HYOK line. **(High-severity scope question.)**

- **[0k-feature-modules] mod-lit-intelligence draft persistence depends on 0g KEK stores + per-subject erasure (§11.7) + crypto-shred contract.** Tasks 2,3,9 build tenant-KEK draft/buffer stores and a crypto-shred zero-hits contract. This inherits 0g's Phase-1+ confidentiality machinery into a Phase-0 feature module. -> Fix: if 0g is deferred, mod-lit-intelligence Phase-0 must persist drafts at private tier without the KEK/crypto-shred apparatus, leaving it as a seam.

- **[0e-audit-spine / Task 5,9] signed chain-head checkpoints + "external anchoring against a compelled operator" + transparency-log.** SCOPE says only "per-stream hash-chain audit sink." The signed Ed25519 checkpoint + control-plane transparency-log sink (§4.1 TXP) is arguably beyond the bare hash-chain sink. The plan itself notes TXP/fair-exchange-receipts are deferred but still ships the signer + checkpoint sink. -> Fix: confirm signed checkpointing is in Phase-0; if the bare sink is the deliverable, the checkpointer is Phase-1+ seam.

- **[0c-pep-broker / Task 5] revocation `DurableTombstoneReader` + `LeaseCache` + fenced-lease semantics.** DEFER lists "the revocation authority + tombstone log." 0c builds a cell-local durable tombstone reader + lease cache as the authoritative-deny store. The plan argues it's owner-local-only (not the cross-institution authority), but it implements tombstone-log reads + epochs that DEFER scope assigns to Phase-1+. -> Fix: confirm the owner-local tombstone read is Phase-0; the kernel stubs `IRevocationAuthority` for Phase-1+, so a live durable tombstone reader may stray. **(Scope question.)**

- **[0a-foundation / Task 8,9] `INTERFACE_LOCUS`, `InterfaceLocus`, `KERNEL_API_VERSION` added to the kernel `__init__.py` and `interfaces.py`.** These symbols are NOT in the canonical kernel surface (the authoritative `__init__.py` `__all__` does not include them). 0a is unilaterally extending the frozen kernel. -> Fix: either get these added to the canonical kernel first, or 0a must not export non-canonical symbols from `contracts` (kernel is near-frozen; additions need a kernel-version bump, not a sub-plan edit).

- **[0h-ingestion] `revocation_epoch` field on `OutboxEvent` + `CellRevocationEpoch`.** Carried "for the federation seam"; plan states Phase-0 emits only public projections and never uses it for cross-institution. Borderline but self-contained (the field is inert in Phase-0). Acceptable as a seam; flag only that it imports revocation-epoch semantics adjacent to the deferred revocation line.

---

## Summary of must-fix (highest leverage)

1. **`IAuditSink.append` arity** (0e) — kernel is one-arg; eliminate the two-arg confusion and the fabricated `TenantContext`.
2. **One PEP class + one `authorize` signature + one decision order** (0c vs 0d) — currently two class names, two bodies, an extra `requested_tier` kwarg, and divergent step ordering for the single chokepoint.
3. **`IModelProvider.satisfies_locality(tier: Tier)`** (0f) — concrete providers use `LocalityClass` and fail the kernel Protocol that 0i relies on.
4. **Central-index read-PEP duplication** (0c Task 10 vs 0j) — pick 0j as authoritative.
5. **`app/dependencies.py` + `app.main` + `modules/` ownership** (0k) — undefined module + path layout divergence from 0a.
6. **Classifier module name** standardized to `classification.classifier` across all import-linter contracts (0b/0c/0e/0k disagree: `classifier.engine`, `classification.engine`, `classification_engine`).
7. **Scope question:** 0g (KEK/crypto-shred), parts of 0c (durable tombstone/lease), and 0e (signed checkpoints) may stray into DEFERRED Phase-1+ confidentiality/revocation/transparency machinery — confirm against the intended Phase-0 line and amend SCOPE or descope.

Category (b)/(c)/(d)/(e) each have concrete issues above; **no category is fully clean**. The kernel-signature mismatches in (a) (items 1–3) and the scope strays in (e) (items 0g/0c/0e + the non-canonical kernel symbols in 0a) are the load-bearing fixes.