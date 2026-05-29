# Plans — "TigerExchange": Federated Multi-University Grant-Intelligence & Research Platform

A from-scratch architecture + business plan, produced by two orchestrated research + adversarial-critique workflows (47 agents total, ~3.3M tokens). NOT bound by the existing TigerResearchBuddy code.

## Read this first
- **`final-plan-v2.md`** — the **canonical converged plan** (= `plan7`, 19 sections, ~143k chars). 0 critical findings across two bounded adversarial passes.
- **`00-decisions.md`** — the 7 locked founder/architecture decisions (D1–D7) everything is anchored on, with rationale.
- **`convergence-report.md`** — the before/after, plus the 11 remaining HIGH refinement items (no blockers).
- **`executive-summary.md`** — short auto-generated summary (the finalizer over-compressed; non-authoritative).

## How it was built
1. **Research** (5 parallel agents) → `00-research-brief.md` + `research/*.md` (market/competitors, federation/compliance, retrieval/RAG/KG, identity/authz, data/OSS stack).
2. **Loop 1** (plan1→plan5, 4 adversarial rounds): never converged — critics kept *re-litigating strategy* (~9 critical / ~21 high every round). Surfaced 5 structural tensions = founder decisions, not bugs. See `critique-log.md`, `decision-log.md`, `_findings.json`.
3. **Decisions locked** (`00-decisions.md`) — wedge = grant intelligence; narrow-to-land scope; anchor-consortium cold-start; + 3 architectural resolutions (single PEP chokepoint; owner-local authority / no global hot-path consensus; confidential content never in shared index).
4. **Loop 2 — decision-locked convergence** (`triage.md` → plan6 → verify → plan7 → verify): triaged 121 findings → 23 canonical issues (mostly resolved-by-decision), critics **bounded to implementation-correctness**. Result: **critical 9 → 0**, 0 relitigation.

## Convergence

| Version | size | critical | high | note |
|---|---|---|---|---|
| plan1–plan5 | 25k–153k | ~8–10 | ~20–22 | Loop-1; never converged; oscillated in length |
| final-plan.md | 79k | (unverified) | — | Loop-1 auto-finalizer (over-compressed) |
| **plan6** | 92k | 0 | 11 | decision-locked rebuild (verify-1) |
| **plan7 / final-plan-v2** | 143k | **0** | 11 | post-revision; **canonical** (verify-2) |

## Status
**Converged on blockers (0 critical).** 11 high-severity items remain — narrow internal-consistency refinements (e.g. epoch granularity overload, eval gold-set PEP-gating, COGS table line-item vs total, K=2 GPU-sharing vs isolation tension), listed in `convergence-report.md`. Not architectural blockers.
