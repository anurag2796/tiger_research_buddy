# TigerExchange Phase-0 — CONVENTIONS (Canonical)

> **AUTHORITATIVE REFERENCE.** This is the single canonical conventions document for the
> TigerExchange Phase-0 builder guide. Every other guide doc, every code-generation prompt,
> and the local model defer to this file. It is grounded in what the sub-plans `0a`–`0k`
> and `00-kernel-contracts.md` **actually build** (file-path / package-layout sections),
> not in prose aspirations.
>
> **If a guide doc disagrees with this file, THIS file wins.** Conflicts in any other
> guide document, plan prose, or generated code are to be resolved in favor of the rules
> stated here. When you find such a conflict, fix the other doc to match this file.

---

## 1. Project-root layout (SPEC vs CODE)

The repository has two top-level trees that are **siblings**:

```
<repo>/
├── plans/                      # THE SPEC — this guide + all sub-plans live here.
│   ├── 00-decisions.md
│   └── phase0/
│       ├── 00-kernel-contracts.md
│       ├── 0a-foundation.md … 0k-feature-modules.md
│       └── guide/CONVENTIONS.md   # ← this file
└── tigerexchange/              # THE CODE — everything that gets built lives here.
    ├── packages/<pkg>/src/<import_root>/…
    └── services/<svc>/…
```

**Rules (authoritative):**

- The code to be built lives at `<repo>/tigerexchange/`.
- The spec (this guide + the plans) lives at `<repo>/plans/` as a **sibling of**
  `tigerexchange/`, **NOT inside it**.
- **Spec paths** are written `plans/phase0/...` and `plans/...`.
- **Code paths** are written `tigerexchange/packages/...` and `tigerexchange/services/...`.
- Any reference of the form `tigerexchange/plans/...` is **WRONG** — fix it to `plans/...`.
- Any staging command of the form `git add tigerexchange/ plans/` is correct (two sibling
  trees); a command that nests them (e.g. `git add tigerexchange/plans`) is **WRONG**.

---

## 2. Canonical package + import-root map

Every Phase-0 package. **Directories use hyphens** (`mod-pep`); **Python import roots use
underscores** (`mod_pep`) — except the kernel and a few packages whose directory name is
already underscore-free. The "Python import root" column is the exact top-level module name
you `import` / install as (the dir under `src/`). Use these EXACT names.

| Package directory | Python import root | Owning sub-plan | One-line purpose |
|---|---|---|---|
| `tigerexchange/packages/contracts` | `contracts` | `0a` (extended by `0j`) | The near-frozen kernel: `Tier` lattice (K1), `PublishableProjection` (K2), all `I*` Protocol interfaces (K3), PEP/audit/tenancy/classification types. Zero feature deps, no persistence. `0j` adds `contracts/discovery.py`. |
| `tigerexchange/packages/mod-pep` | `mod_pep` | `0c` | **The single Policy Enforcement Point** (`PolicyEnforcementPoint` implementing `IPolicyEnforcement.authorize`) + data-access broker — the sole confidentiality chokepoint (D4). Wraps OPA (ABAC) and SpiceDB (ReBAC). |
| `tigerexchange/services/classification` | `classification` | `0b` | The single fail-closed classifier + adjudication queue + ingest hard-gate (`FailClosedClassifier`, abstention → QUARANTINE → default-deny, D6). |
| `tigerexchange/packages/mod-identity` | `mod_identity` | `0d` | OIDC token → frozen `TenantContext` + `Entitlement`; the injected `EntitlementEvaluator` step inside the one PEP; pooled-plane object-authz `Check`. |
| `tigerexchange/packages/mod-pooled-plane` | `mod_pooled_plane` | `0d` | Pooled multi-tenant data-plane helpers (FORCE-RLS-hardened Postgres path behind the SpiceDB object-authz boundary). |
| `tigerexchange/packages/mod-audit` | `mod_audit` | `0e` | Per-stream hash-chained audit spine (`IAuditSink` impl, `prev_hash`→`entry_hash`, transparency-log checkpoints). |
| `tigerexchange/packages/mod_ai` | `mod_ai` | `0f` | Provider-agnostic, classification-routed **model router** (`ModelRouter`/`IModelRouter`), provider registry, transport egress guard, BYO provider, guardrails. Directory name is `mod_ai` (underscore), matching its import root. |
| `tigerexchange/packages/mod-confidential-crypto` | `confidential_crypto` | `0g` (referenced by `0k`) | Confidential KEK/DEK envelope crypto + per-cell key stores for the confidential tier. |
| `tigerexchange/packages/mod-confidential-cogs` | `confidential_cogs` | `0g` | Confidential-tier COGS / dedicated-isolation cost accounting (D7 unit-economics floor). |
| `tigerexchange/packages/mod-ingestion` | `mod_ingestion` | `0h` | Dagster code location: source-snapshot → distill → classify (hard gate) → embed → index → graph DAGs + transactional-outbox sensor. |
| `tigerexchange/packages/identity-resolution` | `identity_resolution` | `0h` | Entity resolution (deterministic ORCID/DOI/ROR anchors → probabilistic blocking) feeding ingestion. |
| `tigerexchange/packages/retrieval` | `retrieval` | `0i` | Shared **retrieval infrastructure** (NOT a feature module): `HybridRetriever`/`IRetrievalStrategy` (Qdrant vector + OpenSearch BM25 + RRF), `IReranker`. Also ships an `eval` import root for the eval harness. |
| `tigerexchange/services/central_index` | `central_index` | `0j` | Central-index read-PEP service: `CentralIndexReadPEP` (`IPolicyEnforcement`), owner-authoritative scope registry, encrypted index store, scope-epoch enforcement. Directory is `central_index` (underscore). |
| `tigerexchange/packages/mod-lit-intelligence` | `mod_lit_intelligence` | `0k` | **Feature module 1 — literature & research intelligence.** Proposal grounding / prior-art / aims drafting over retrieval. |
| `tigerexchange/packages/mod-discovery` | `mod_discovery` | `0k` | **Feature module 2 — expert/collaborator discovery.** PUBLIC-tier only (see §6.6). |
| `tigerexchange/packages/mod-funding-lite` | `mod_funding_lite` | `0k` | **Feature module 3 — grant & funding intelligence (lite).** The beachhead wedge slice (D1). |
| `tigerexchange/services/api` | `api` | `0a` (wired by `0d`, `0k`) | The single FastAPI app. Derives `TenantContext` per request, pins it to a transaction-scoped Postgres connection via `SET LOCAL app.tenant_id`. |

**Disagreement notes (recorded for traceability):**

- The model-router package is named **`mod_ai`** (directory and import root both underscore)
  per `0f`'s file table, *not* `mod-ai`. Where any doc writes `mod-ai`, prefer `mod_ai`.
- `0f`'s "AI / Model-Router layer" docstring in the kernel cites a phantom label
  `D-AI`; see §5 — that label does not exist. The package itself (`mod_ai`) is correct.
- `mod-confidential-crypto` (directory, hyphen) imports as **`confidential_crypto`**
  (no `mod_` prefix on the import root) per `0g`. Same pattern for `mod-confidential-cogs`
  → `confidential_cogs`. This asymmetry is intentional; do not "fix" it.
- `identity-resolution` (`0h`) has **no `mod-` prefix** (it is an evicted helper service,
  not a feature module). Import root `identity_resolution`.
- The kernel package `contracts` is owned by `0a`; `0j` legitimately **extends** it with
  `contracts/discovery.py` (`DiscoveryQuery`, `ScopeCommit`, `ScopeEpochTooOld`) on the
  single import surface. This is the only package two plans write to; `0a` is the owner.

**`mod-workspace` is intentionally absent** from this table — it is **not built in Phase-0**
(see §7).

---

## 3. ABAC = OPA, ReBAC = SpiceDB (authoritative)

**RULE:** The ABAC (attribute-based, tier × subject-attrs × edition) engine is **OPA
(Open Policy Agent, Rego)**, deployed as an **HTTP sidecar**. The ReBAC (relationship-based,
grants/entitlements/`tenant#member`) engine is **SpiceDB**. This is what `0c` and `0d`
actually build (grep-confirmed: `0c`/`0d` reference OPA + Rego + SpiceDB throughout; the
runbook docker-compose stands up the OPA sidecar; there is no Cedar anywhere in the plans).

- The single canonical decision order inside `PolicyEnforcementPoint.authorize` is fixed:
  **(1) entitlement/edition gate → (2) capability gate → (3) ReBAC Check (SpiceDB, narrow-only
  cache) → (4) ABAC tier check (OPA, narrows-only) → (5) owner-local durable tombstone read
  (AUTHORITATIVE deny) → (6) lease read (narrow-only positive-grant cache).**
- **Any doc that LOCKS Cedar as the ABAC engine is WRONG.** Change it to OPA and rewrite the
  rationale to justify OPA: mature, **CNCF-graduated**, matches the built plans, and gives a
  **single decision point for tier ABAC** (one owned Rego policy table behind the one PEP).
- Cedar may be mentioned **only** as a considered-but-not-used alternative.

---

## 4. Python baseline = 3.11+ (authoritative)

**RULE:** Python **3.11+** is the project baseline stated everywhere. The canonical kernel
`pyproject.toml` (`00-kernel-contracts.md`) pins `requires-python = ">=3.11"`, and so do
`0b`/`0c`/`0d`/`0e`/`0g`/`0h`.

- **DELETE any claim that the kernel pins 3.12** — it is false. The kernel pins `>=3.11`.
- A specific **service MAY target 3.12** if it documents the reason, but the **baseline
  stated everywhere is 3.11+**. Do not state 3.12 as the project/kernel baseline.

---

## 5. Decision labels: only D1–D7 exist (authoritative)

**RULE:** The locked decisions are exactly **D1 through D7** (see `plans/00-decisions.md`).
**Never cite a numbered decision outside D1–D7.** Replace phantom labels:

- **`D-AI`** → write it out as **"the AI/model-router requirement (provider-agnostic,
  classification-routed; confidential-routing rule per D6)."** Do not coin a `D-AI` label.
- **`D9`** → write it out as **"the single-tenant Phase-0 scope rule (consequence of
  D2 + D6; cross-institution sharing / revocation-authority is Phase-1+)."** There is no `D9`.

For reference, the canonical D-labels: D1 grant-intelligence wedge; D2 narrow-to-land /
full architecture; D3 anchor consortium; **D4 single PEP + data-access broker**; D5 owning
node is local authority; **D6 confidential content never enters the shared index** +
abstention→quarantine→default-deny; D7 unit-economics floor.

---

## 6. The three feature modules (authoritative)

**RULE:** There are exactly **three** Phase-0 feature modules:

1. literature module = **`mod-lit-intelligence`** (import `mod_lit_intelligence`)
2. discovery module = **`mod-discovery`** (import `mod_discovery`)
3. funding module = **`mod-funding-lite`** (import `mod_funding_lite`)

Additional binding rules:

- **6.5 — Do NOT introduce `mod-retrieval` as a FEATURE module.** Retrieval is **shared
  infrastructure** (the `retrieval` package, `0i`), not one of the three Phase-0 feature
  modules. Wherever doc `05` (or any doc) says `mod-retrieval` as a feature module, **fix it
  to `mod-lit-intelligence`** (the literature feature module that consumes retrieval).
- **6.6 — `mod-discovery` operates on PUBLIC-tier data ONLY.** It consumes
  `IRetrievalStrategy` / `ICollaborationGraph` / `IExpertiseFingerprint` (and `IExchangeFeed`
  **only** as a Phase-1+ type-referenced stub — never wired in Phase-0). It **is** still
  subject to the central-index read PEP (`0j`) for discoverability **scope**, but it does
  **NOT** touch the confidential enforcement path. Wherever a doc states "all modules go
  through the PEP," **add this public-tier clarification**: `mod-discovery` goes through the
  central-index read PEP for scope filtering only and never reaches confidential data.

---

## 7. `mod-workspace` is NOT built in Phase-0 (authoritative)

**RULE:** The secure-shared-workspace module **`mod-workspace` is Phase-1+** and is **not
built, not scaffolded** in Phase-0. Only the **kernel seams** it would later use exist
(e.g. `IGrantStore` is present as a Protocol; in Phase-0 only the owner-local own-tenant
read path is exercised, and `IExchangeFeed`/`IRevocationAuthority` are unimplemented Phase-1+
stubs). Do not create a `mod-workspace` package, directory, or import root.

---

## 8. Low-severity canonical settings (authoritative)

These are pinned to keep generated code internally consistent:

| Item | Canonical rule |
|---|---|
| **Funding-source enum value** | Use **`grants_gov`** (underscore) **everywhere** — the enum value, snapshot directory, reader name, and `SourceRecord.source` (matches `0h`). Never `grants.gov` / `grantsgov` / `grants-gov` as the enum value. |
| **Dagster version pin** | Pin **`dagster>=1.8,<2`**. (`0h` currently shows `dagster>=1.7,<2`; the canonical pin is `>=1.8,<2` — update `0h` and any guide doc to match.) |
| **Qdrant collection setup** | Use **`create_collection` guarded by `collection_exists`** (create-if-absent). Do **NOT** use the deprecated/destructive **`recreate_collection`** (`0i` line ~2129 currently uses `recreate_collection` — fix it: check `client.collection_exists(name)` and only `create_collection` when absent). |
| **`class_codes` classification column** | Keep it consistent between DDL and prose. **Prefer keeping `class_codes TEXT[]` in the DDL** (tiers/flags ride every content row, so the classification columns belong on the row). If a doc mentions `class_codes` in prose, ensure the column also appears in the DDL; otherwise remove the prose mention. Do not have it in prose-only with no DDL backing. |
| **`abstract` field alignment** | The **Qdrant payload schema** and the **OpenSearch mapping** must agree on the `abstract` field (same name, same presence). `0h` uses `abstract: str = ""` on the research card and writes `"abstract"` into the payload; the lexical index mapping must carry the same `abstract` field. Align both schemas — do not let one have `abstract` and the other omit/rename it. |

---

## 9. Naming-convention quick rules

- **Package directories**: lowercase, hyphenated, feature modules prefixed `mod-`
  (`mod-pep`, `mod-discovery`). Exceptions that are underscore-named directories: `mod_ai`
  (`0f`) and the `central_index` **service** (`0j`).
- **Python import roots**: lowercase, underscored (`mod_pep`, `mod_discovery`,
  `mod_funding_lite`, `mod_lit_intelligence`, `mod_ai`, `mod_ingestion`, `identity_resolution`,
  `confidential_crypto`, `confidential_cogs`, `mod_audit`, `mod_pooled_plane`, `mod_identity`,
  `retrieval`, `eval`, `contracts`, `api`, `classification`, `central_index`).
- **Services vs packages**: `tigerexchange/services/` holds runnable services
  (`api`, `classification`, `central_index`); `tigerexchange/packages/` holds importable
  libraries/modules. Use the EXACT tree (`packages` vs `services`) from §2.
- **Kernel imports**: everything is imported from `contracts` verbatim
  (`from contracts import Tier, PepRequest, ...`). Feature modules import the kernel; the
  kernel imports nothing feature-side (import-linter forbidden-import contract).

---

## 10. Precedence

This file is the authoritative reference. Order of precedence for any conflict:

1. **This `CONVENTIONS.md`** (canonical reconciliations above).
2. The owning **sub-plan** file-path / package-layout sections (`0a`–`0k`,
   `00-kernel-contracts.md`) for anything not covered here.
3. `plans/00-decisions.md` for decision semantics (D1–D7 only).

Any other guide doc, prose, or generated artifact that disagrees with (1) is wrong and must
be corrected to match this file.
