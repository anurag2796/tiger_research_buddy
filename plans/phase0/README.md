# TigerExchange — Phase-0 Implementation Plan Set

Bite-sized, TDD, no-placeholder implementation plans for the Phase-0 MVP, authored by an orchestrated workflow (15 agents) against the approved design (`../final-plan-v2.md`) and locked decisions (`../00-decisions.md`). Build target: a greenfield project root **`tigerexchange/`**.

## Files
- **`00-kernel-contracts.md`** — the canonical shared `contracts/kernel` package (TierLattice, TenantContext, PEP/classifier/router/retrieval interfaces). **Authoritative**: every sub-plan imports these verbatim. Implemented by `0a`.
- **`0a`–`0k`** — the 11 sub-plans (below), each a working/testable deliverable.
- **`_decomposition.json`** — structured sub-plan graph.
- **`_consistency-check.md`** — cross-plan consistency punch-list (read before executing — see "Known issues").

## Sub-plans (build order: `0a → 0b → 0c → 0d → 0e → 0f → 0g → 0h → 0i → 0j → 0k`)

```mermaid
graph TD
  0a[0a Foundation: monorepo + kernel + FORCE-RLS + FastAPI + CI]
  0b[0b Classification engine + quarantine]
  0c[0c PEP + data-access broker chokepoint]
  0d[0d Identity + Entitlement/Edition @ PEP]
  0e[0e Audit spine: per-stream hash-chain]
  0f[0f Model Router: classification-routed + BYO]
  0g[0g Confidential KEK/DEK stores + crypto-shred]
  0h[0h Ingestion: OpenAlex/Crossref/ROR/ORCID/SPECTER2 + grants]
  0i[0i Hybrid retrieval + PEP-gated RAGAS eval]
  0j[0j Central-index read PEP + discoverability_scope]
  0k[0k Feature modules: lit-intelligence, discovery, funding-lite]
  0a-->0b-->0c
  0a-->0c
  0c-->0d & 0e & 0f
  0a-->0d
  0c-->0g-->0i
  0f-->0g & 0i & 0k
  0a-->0h-->0i
  0b-->0h
  0a-->0j
  0c-->0j & 0i & 0k
  0d-->0j
  0h-->0i & 0k
  0i-->0k
```

| id | name | deliverable |
|---|---|---|
| 0a | Foundation | monorepo + frozen `contracts/kernel` + Postgres FORCE-RLS tenant isolation + FastAPI skeleton + CI walking skeleton |
| 0b | Classification engine | fail-closed classifier; abstention → quarantine default-deny + adjudication queue |
| 0c | PEP + broker | single chokepoint: ABAC (OPA) + ReBAC (SpiceDB) + owner-local revocation decision-order |
| 0d | Identity + Entitlement | Keycloak+CILogon OIDC; Edition/Entitlement evaluated at the PEP; pooled-plane object-authz |
| 0e | Audit spine | per-stream hash-chain audit sink |
| 0f | Model Router | provider-agnostic, classification-routed (local vs cloud) + BYO keys + guardrails |
| 0g | Confidential KEK stores | per-tenant KEK/DEK derivative-store encryption + crypto-shred + Table-B COGS reconciliation |
| 0h | Ingestion pipelines | Dagster: scholarly + grant corpora; classify-gate-index outbox; entity resolution |
| 0i | Retrieval + eval | Qdrant + OpenSearch + RRF + reranker; PEP-gated RAGAS-in-CI |
| 0j | Central-index read PEP | per-query authz + `discoverability_scope` (owner-committed, strongly consistent) |
| 0k | Feature modules | mod-lit-intelligence (grounded drafting), mod-discovery (public OpenAlex), mod-funding-lite (grant match) |

All 11 high-severity refinement items from `../convergence-report.md` are assigned to owning sub-plans (see `highs_addressed` in `_decomposition.json`).

## Cross-plan consistency — status after fix-up (wf `w0j0cd0j8`)
A reconciliation pass (12 in-place fix agents + re-check) resolved **8 of 10** issues: object-classification (0c), `IAuditSink.append` one-arg (0e), `satisfies_locality(tier: Tier)` (0f), single central-index PEP = **0j** (0c dup dropped), `packages/`+`services/` layout & `api.dependencies` DI factories (0a defines, 0k consumes), `classification.classifier` naming everywhere, the kernel interface-versioning amendment (`KERNEL_API_VERSION`/`InterfaceLocus`/`INTERFACE_LOCUS`), and single-tenant scope notes (0g/0c/0e). Full verdict + per-file changelogs: **`_recheck-after-fixup.md`**.

**3 residual items — fix before executing the affected plans:**
1. **🔴 PEP module-path + constructor mismatch (0c ↔ 0d).** The class name (`PolicyEnforcementPoint`), `authorize` signature, and decision order are now unified, but 0c builds it at `services/pep/src/pep/pep.py` with ctor `(entitlement, classifier, rebac, abac, tombstone, lease, broker)` while 0d imports `mod_pep.policy_enforcement_point` with a thinner ctor. **Pick one module path + one constructor parameter set across 0c and 0d.** (Blocking only when executing 0c/0d.)
2. **0f Task 8 / 0g Task 8 COGS** — confirm each ships only the reconciled band-based computation (no superseded-then-rewritten block within one step).
3. **Kernel-doc walrus artifact** — scrub the `IRerankerLike := IReranker` line in `00-kernel-contracts.md`'s `__init__.py` block (0a is already instructed to skip it, so it cannot ship, but the authoritative doc still carries the wrong line).

## Scope — resolved
0g (confidential-at-rest KEK/crypto-shred), 0c (owner-local revocation), and 0e (signed checkpoints) are **kept in Phase-0, scoped single-tenant own-data only** — the MVP stores the center's own confidential proposal drafts, so HYOK-at-rest + GDPR crypto-shred are genuinely required. Each now carries an explicit note that the **cross-institution** sharing/exchange + revocation-*authority* are Phase-1+ (kernel interfaces stubbed, not active). `0k`'s confidential draft persistence stays single-tenant via `0g`.

## Execution
Each sub-plan is executed task-by-task via `superpowers:subagent-driven-development` (fresh agent per task, review between) in the dependency order above. `0d`/`0e`/`0f` can run in parallel after `0c`; `0j` can run alongside the `0g`→`0h`→`0i` track. **Apply the known-issue fixes + resolve the scope question first.**
