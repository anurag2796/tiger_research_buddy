# Build Runbook (Step-by-Step for the Local Model)

**What this document is for.** This is the single operational script you (a local code-generation model running on an Apple M4 Max via Ollama, with a limited context window) follow to build the TigerExchange Phase-0 MVP from an empty machine to a passing test suite. It assumes you know almost nothing about the toolchain: every prerequisite, exact command, file path, library version, environment variable, and acceptance gate is written out here so you never have to guess or re-derive a decision. TigerExchange is a hybrid RAG (Retrieval-Augmented Generation — retrieve documents, then generate grounded answers) research platform whose Phase-0 wedge is *grant intelligence*: helping research teams at different universities assemble grant-proposal teams and collaborate on confidential proposals. You build it as a Python monorepo rooted at `tigerexchange/`. Work strictly top-to-bottom; do not skip ahead. When a step says "acceptance gate", that gate MUST be green before you move to the next sub-plan.

---

## 0. Glossary (read once; every term used later is defined here)

We define every term inline the first time it appears, but this table is the fallback so you never stall on vocabulary.

| Term | One-line definition |
|---|---|
| **Monorepo** | One git repository holding multiple Python packages (libraries) and services side by side. |
| **uv** | A fast Python package/workspace manager (replaces `pip` + `virtualenv` + `poetry`). It reads `pyproject.toml`. |
| **Workspace** | A uv feature where several packages in one repo are installed together and can import each other locally. |
| **Kernel / `contracts`** | The frozen shared library of types + interfaces every other package imports. Near-frozen = changes are tightly controlled. |
| **PEP (Policy Enforcement Point)** | The single code chokepoint that decides allow/deny for every read/egress/derivation. Do NOT confuse with "PEP" as in Python Enhancement Proposal. |
| **Tier** | Sensitivity level of data: `public < private < confidential`. |
| **MAX-rule** | When combining data of two tiers, the result takes the MORE restrictive (higher) tier. |
| **Fail-closed** | On any error/ambiguity, deny access (never accidentally allow). The opposite of fail-open. |
| **Quarantine** | The fail-closed state for data the classifier is unsure about: treated as confidential, excluded from all retrieval. |
| **RLS (Row-Level Security)** | A Postgres feature where a row is only visible if it matches a per-session predicate (here: `tenant_id`). |
| **FORCE RLS** | A stronger RLS mode where even the table owner cannot bypass the row filter. |
| **Tenant** | One paying institution/customer. Their data must never leak to another tenant. |
| **BOLA / IDOR** | "Broken Object-Level Authorization" / "Insecure Direct Object Reference": reading another tenant's row by guessing its ID. The RLS test must block this. |
| **TDD (Test-Driven Development)** | Write a failing test first, then write the minimum code to make it pass. |
| **Pydantic v2** | A Python library for typed, validated data models. `frozen=True` makes an instance immutable. |
| **Protocol** | A Python `typing.Protocol` interface: structural typing, no inheritance required. |
| **import-linter** | A tool that fails CI if a package imports something it is forbidden to import. |
| **testcontainers** | A Python library that starts a real Postgres in Docker for an integration test, then tears it down. |
| **DUA** | Data Use Agreement: the legal contract that lets two institutions share confidential data. |

---

## 1. Prerequisites on the M4 Max

You are on macOS (Apple Silicon, M4 Max, 36 GB unified memory). Install the toolchain exactly as below. Run each command and confirm the version line printed matches (or exceeds) the stated minimum. **The project baseline is Python 3.11+** — the canonical kernel `pyproject.toml` (`00-kernel-contracts.md`) pins `requires-python = ">=3.11"`, and so do `0b`/`0c`/`0d`/`0e`/`0g`/`0h`. The kernel uses `enum.StrEnum`, which needs 3.11+. We install 3.12 as a concrete recent interpreter that satisfies the `>=3.11` floor — we considered 3.13 but rejected it because some dependencies (asyncpg wheels, testcontainers) lag the newest interpreter on release day. A specific service MAY target 3.12 if it documents the reason, but the baseline stated everywhere is 3.11+.

### 1.1 Homebrew (macOS package manager)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew --version   # expect: Homebrew 4.x
```

### 1.2 uv (Python + workspace manager) and Python 3.11+

We use **uv** (not bare pip) because the repo is a *workspace* of several packages that import each other; uv resolves and installs them together with one `uv sync`. We considered Poetry but rejected it because the plans' `pyproject.toml` files are written for `[tool.uv.workspace]`, and uv installs the interpreter itself so you do not need a separate pyenv.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart the shell or: source $HOME/.local/bin/env
uv --version            # expect: uv 0.4.x or newer
uv python install 3.12  # uv downloads and manages CPython 3.12 (any 3.11+ satisfies the >=3.11 floor)
uv python list          # confirm a 3.11+ entry appears
```

### 1.3 Docker Desktop (for local services + integration tests)

The integration tests start a real Postgres in a container via `testcontainers`, and the local dev stack (Section 3) runs in `docker compose`. **Install Docker Desktop for Apple Silicon** (the arm64 build).

```bash
brew install --cask docker
open -a Docker          # launch it once; wait until the whale icon says "Running"
docker --version        # expect: Docker version 27.x
docker compose version  # expect: Docker Compose version v2.x
```

In Docker Desktop → Settings → Resources, set **Memory ≥ 12 GB** (the local stack in Section 3 fits in ~8–10 GB; the remaining ~24 GB of the 36 GB stays for macOS + your editor + Ollama). We do NOT give Docker more than ~12 GB because Ollama's models also use unified memory and you must not over-commit the 36 GB ceiling.

### 1.4 Ollama (local LLM inference) and the model to pull

Phase-0 *code* does not call an LLM (it is types, the PEP chokepoint, RLS, retrieval plumbing). Ollama is only needed so YOU (the local code-gen model) run, and later so the Model Router (sub-plan `0f`) has an in-boundary provider to route confidential traffic to. **Pull a coding-capable model that fits 36 GB unified memory.** A 32B-class model quantized to 4-bit (~Q4) uses roughly 18–20 GB and leaves headroom; we recommend `qwen2.5-coder:32b` for code generation. We reject unquantized 70B+ models because they exceed the 36 GB ceiling once macOS + Docker are also resident.

```bash
brew install ollama
ollama serve &                 # starts the local inference server on :11434
ollama pull qwen2.5-coder:32b  # ~18-20 GB at Q4; fits 36 GB with headroom
ollama list                    # confirm the model is present
```

### 1.5 Node.js — NOT required for Phase-0

Phase-0 ships **no frontend**. The deliverable is a FastAPI backend service plus libraries (see `0a`–`0k` deliverables). **Do not install Node**; it would be unused scope. (A web frontend is a later phase, out of scope here.)

### 1.6 Git

```bash
git --version   # macOS ships git; expect 2.39+
```

---

## 2. Repository bootstrap

You are creating the project root **`tigerexchange/`** with this exact monorepo layout (libraries under `packages/`, the API service under `services/`). The layout below is mandated by the decomposition (`_decomposition.json` → `"project_root": "tigerexchange"`) and the kernel doc.

```
tigerexchange/
├── .python-version                 # a concrete 3.11+ interpreter (e.g. "3.12")
├── pyproject.toml                  # uv workspace root + dev tools (ruff/mypy/pytest)
├── README.md
├── .pre-commit-config.yaml         # ruff + mypy on every commit
├── .env.example                    # env var template (Section 4)
├── .github/workflows/ci.yml        # CI gates
├── docker-compose.yml              # local dev stack (Section 3)
├── tests/                          # repo-level tests (layout, CI config, gate docs)
├── packages/
│   └── contracts/                  # the frozen kernel library (built by 0a)
│       ├── pyproject.toml
│       ├── api/contracts_api.txt   # frozen public-API baseline for compat check
│       ├── src/contracts/          # lattice.py, tenancy.py, classification.py, ...
│       └── tests/
│   # later sub-plans add: packages/mod-pep/, packages/mod-lit-intelligence/, etc.
└── services/
    └── api/                        # the FastAPI app (built by 0a)
        ├── pyproject.toml
        ├── src/api/                # app.py, db.py, config.py, tenant_context.py, dependencies.py
        ├── src/api_scripts/        # check_rls_bypass.py (RLS-bypass lint)
        ├── migrations/             # 001_tenant_rls.sql
        └── tests/
```

**Why `packages/` + `services/` split.** Libraries (the kernel and the `mod-*` feature modules) are reusable, import-only units; the FastAPI app is a deployable service that wires them together. Keeping them separate lets `import-linter` forbid the kernel from ever importing a service or a persistence engine (the "kernel fitness function"). We considered a flat single-package layout but rejected it because nothing would then stop a feature module from importing a raw database client and bypassing the PEP chokepoint (decision D4).

### 2.1 Create the repo and the first scaffold

Do this manually for the very first files, because sub-plan `0a` Task 1 writes them with TDD. The exact content of `pyproject.toml`, `.python-version`, and `README.md` is given verbatim in `0a-foundation.md` Task 1 — you will reproduce them there. For now, just create the directory and git:

```bash
mkdir -p tigerexchange && cd tigerexchange
git init
git branch -m main
```

> Note: every later command in this runbook is written `cd tigerexchange && ...`. Because this shell resets its working directory between steps in some environments, always prefix with `cd tigerexchange` (or use the absolute path to your checkout).

### 2.2 Root `pyproject.toml` (workspace + dev tools)

`0a` Task 1 creates this verbatim. It declares the two workspace members and the dev tool config. The key lines (reproduce exactly from `0a` Task 1):

```toml
[project]
name = "tigerexchange"
version = "0.0.0"
requires-python = ">=3.11"

[tool.uv.workspace]
members = ["packages/contracts", "services/api"]

[dependency-groups]
dev = [
  "pytest>=8", "pytest-asyncio>=0.24", "testcontainers[postgres]>=4.8",
  "ruff>=0.6", "mypy>=1.11", "import-linter>=2.1", "griffe>=1.3",
]

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["packages/contracts/src", "services/api/src"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
markers = ["unit: no external services", "integration: requires a Postgres container"]
asyncio_mode = "auto"
testpaths = ["tests", "packages/contracts/tests", "services/api/tests"]
```

**Why these tools.** `ruff` = lint + format (fast, replaces flake8+black+isort). `mypy --strict` = static type-checking (the kernel is fully typed; strict catches contract drift). `pytest` = test runner. `import-linter` = enforces the kernel-has-no-feature-deps rule. `griffe` = diffs the kernel's public API against a baseline so a frozen symbol can't be silently removed. `pytest-asyncio` + `testcontainers[postgres]` = run async DB tests against a real ephemeral Postgres.

### 2.3 Install the workspace

```bash
cd tigerexchange && uv sync --all-extras
```

This creates `.venv/`, installs the dev group, and installs `packages/contracts` and `services/api` in editable mode so `import contracts` and `import api` resolve. Run `uv run python -c "import sys; print(sys.version)"` and confirm a `3.11+` interpreter (e.g. `3.12.x`).

### 2.4 pre-commit (ruff + mypy on every commit)

We add pre-commit so a broken commit can't land locally. Create `tigerexchange/.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff           # lint
        args: [--fix]
      - id: ruff-format    # format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: ["pydantic>=2.6"]
        args: ["--strict"]
```

Install the hook:

```bash
cd tigerexchange && uv run pre-commit install
```

**Why pre-commit AND CI.** Pre-commit catches issues before you waste a CI run; CI is the authoritative gate (a contributor could skip the hook). We considered only-CI but rejected it because the local feedback loop matters when you (the local model) are iterating quickly with limited context.

### 2.5 The CI workflow

`0a` Task 14 creates `tigerexchange/.github/workflows/ci.yml` verbatim with two jobs:

- **`quality`** — installs uv + Python 3.11+, `uv sync --all-extras`, then runs in order: `ruff check .`, `ruff format --check .`, `mypy .`, `lint-imports --config packages/contracts/pyproject.toml` (kernel fitness), `python -m api_scripts.check_rls_bypass services/api/migrations` (RLS-bypass lint), `pytest -m unit -q`, and the kernel contracts suite `pytest packages/contracts/tests -q`.
- **`integration`** — installs the same, then runs `pytest -m integration -q` (the FORCE-RLS cross-tenant tests need Docker on the runner).

You do not hand-author this; `0a` Task 14 has the exact YAML and a test (`tests/test_ci_config.py`) that asserts the required gate strings are present.

---

## 3. Local dev stack — `docker-compose.yml`

Phase-0 sub-plan `0a` only needs Postgres (for FORCE-RLS). But sub-plans `0c` (PEP), `0d` (identity), `0i` (retrieval), and `0j` (central-index) need the wider stack: Postgres+pgvector, Qdrant (vector DB), OpenSearch (BM25 lexical search), Keycloak (OIDC identity), SpiceDB (ReBAC relationship authz), and OPA (ABAC attribute policy). We bring them ALL up once so you do not fight infra mid-build. **Create `tigerexchange/docker-compose.yml`:**

```yaml
# TigerExchange local dev stack. Fits comfortably in ~8-10 GB; keep Docker Desktop
# memory >= 12 GB so the 36 GB unified memory still has room for Ollama + macOS.
services:
  postgres:
    image: pgvector/pgvector:pg16          # Postgres 16 WITH pgvector extension preinstalled
    environment:
      POSTGRES_USER: tigerexchange
      POSTGRES_PASSWORD: tigerexchange
      POSTGRES_DB: tigerexchange
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tigerexchange"]
      interval: 5s
      timeout: 5s
      retries: 10
    deploy: { resources: { limits: { memory: 1g } } }

  qdrant:
    image: qdrant/qdrant:v1.12.1            # vector search engine (0i)
    ports: ["6333:6333", "6334:6334"]
    healthcheck:
      test: ["CMD", "bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/6333"]
      interval: 5s
      timeout: 5s
      retries: 10
    deploy: { resources: { limits: { memory: 2g } } }

  opensearch:
    image: opensearchproject/opensearch:2.17.1   # BM25 lexical search (0i)
    environment:
      - discovery.type=single-node
      - DISABLE_SECURITY_PLUGIN=true        # local dev ONLY; never in prod
      - OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g  # cap heap so it fits the memory budget
    ports: ["9200:9200"]
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 12
    deploy: { resources: { limits: { memory: 3g } } }

  keycloak:
    image: quay.io/keycloak/keycloak:25.0   # OIDC identity provider (0d)
    command: ["start-dev"]
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    ports: ["8080:8080"]
    healthcheck:
      test: ["CMD-SHELL", "exec 3<>/dev/tcp/127.0.0.1/8080"]
      interval: 10s
      timeout: 5s
      retries: 12
    deploy: { resources: { limits: { memory: 1g } } }

  spicedb:
    image: authzed/spicedb:v1.37.0          # ReBAC relationship authz (0c)
    command: ["serve", "--grpc-preshared-key", "tigerexchange-dev-key", "--datastore-engine", "memory"]
    ports: ["50051:50051", "8443:8443"]
    healthcheck:
      test: ["CMD", "grpc_health_probe", "-addr=127.0.0.1:50051"]
      interval: 5s
      timeout: 5s
      retries: 10
    deploy: { resources: { limits: { memory: 512m } } }

  opa:
    image: openpolicyagent/opa:0.68.0        # ABAC attribute policy engine (0c)
    command: ["run", "--server", "--addr", "0.0.0.0:8181"]
    ports: ["8181:8181"]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1:8181/health"]
      interval: 5s
      timeout: 5s
      retries: 10
    deploy: { resources: { limits: { memory: 256m } } }
```

### 3.1 Memory budget on 36 GB

| Service | Purpose | Used by sub-plan | Memory cap |
|---|---|---|---|
| postgres (pgvector) | tenant data + FORCE-RLS | 0a, 0d | 1 GB |
| qdrant | vector retrieval | 0i, 0k | 2 GB |
| opensearch | BM25 lexical retrieval | 0i, 0k | 3 GB |
| keycloak | OIDC identity | 0d | 1 GB |
| spicedb | ReBAC authz | 0c | 0.5 GB |
| opa | ABAC authz | 0c | 0.25 GB |
| **Total stack** | | | **~7.75 GB** |
| + Ollama (qwen2.5-coder:32b, Q4) | local code-gen | — | ~18–20 GB |
| + macOS + editor | | | ~4–6 GB |
| **Grand total** | | | **~30–34 GB** (fits 36 GB) |

**Reasoning:** OpenSearch (JVM) is the biggest single consumer, so its heap is explicitly capped at 1 GB via `OPENSEARCH_JAVA_OPTS`. We considered running OpenSearch and Keycloak (both JVM) without caps but rejected it because two uncapped JVMs plus a 20 GB model would blow the 36 GB ceiling and trigger macOS memory pressure/swapping. If you hit memory pressure, **stop the model you are not actively using** (`ollama stop`) or bring up only the subset of services the current sub-plan needs (e.g. for `0a` you only need `postgres`).

### 3.2 Bring it up / health-check / down

```bash
cd tigerexchange && docker compose up -d
cd tigerexchange && docker compose ps          # STATUS column should read "healthy"
# For 0a only, you can start just Postgres:
cd tigerexchange && docker compose up -d postgres
cd tigerexchange && docker compose down         # stop everything when done
```

Note: `testcontainers` (used by `0a`'s integration tests) starts its OWN throwaway Postgres independent of this compose stack, so `0a`'s tests pass even if compose is down — they only need Docker running.

---

## 4. Environment variables — `.env.example`

Create `tigerexchange/.env.example`. Copy it to `.env` (which is git-ignored) and fill secrets. **The service reads settings via `pydantic-settings` with prefix `TIGEREXCHANGE_`** (see `0a` Task 10 `config.py`), so DB settings must use that prefix. The connection string uses the `postgresql+asyncpg://` scheme because the service uses the async SQLAlchemy engine.

```dotenv
# ---- Core (0a) ----
TIGEREXCHANGE_ENV=dev
# asyncpg DSN. Matches docker-compose postgres credentials above.
TIGEREXCHANGE_DATABASE_DSN=postgresql+asyncpg://tigerexchange:tigerexchange@localhost:5432/tigerexchange

# ---- Retrieval engines (0i) ----
QDRANT_URL=http://localhost:6333
OPENSEARCH_URL=http://localhost:9200

# ---- Identity / authz (0c, 0d) ----
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=tigerexchange
OIDC_CLIENT_ID=tigerexchange-api
OIDC_CLIENT_SECRET=change-me
SPICEDB_ENDPOINT=localhost:50051
SPICEDB_PRESHARED_KEY=tigerexchange-dev-key
OPA_URL=http://localhost:8181

# ---- Model Router (0f) ----
# Local in-boundary provider (confidential/private traffic routes here).
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:32b
# Cloud frontier provider (PUBLIC tier only; never confidential — decision D6).
# Leave blank in Phase-0 unless a public-tier route is exercised.
OPENAI_API_KEY=
```

Then:

```bash
cd tigerexchange && cp .env.example .env
# Add the live ignore rule:
cd tigerexchange && printf "\n.env\n.venv/\n__pycache__/\n" >> .gitignore
```

**Why `.env` is git-ignored and `.env.example` is committed.** Secrets (OIDC client secret, cloud API key) must never enter git history. The `.example` file is the committed contract documenting every variable; `.env` holds real values locally. This is also a decision-D6-relevant discipline: the cloud `OPENAI_API_KEY` exists ONLY for public-tier routing — confidential content never leaves the boundary, so leaking that key cannot leak confidential data, but we still keep it out of git.

---

## 5. The build order: `0a → 0b → 0c → 0d → 0e → 0f → 0g → 0h → 0i → 0j → 0k`

This is the dependency-respecting order from `README.md`. **Build them in exactly this sequence.** Some can run in parallel after their deps land (`0d`/`0e`/`0f` after `0c`; `0j` alongside the `0g→0h→0i` track), but the local model should build them serially in the listed order to keep context small and avoid half-finished cross-dependencies.

### 5.1 Dependency graph

```mermaid
graph TD
  0a[0a Foundation: monorepo + kernel + FORCE-RLS + FastAPI + CI]
  0b[0b Classification engine + quarantine]
  0c[0c PEP + data-access broker chokepoint]
  0d[0d Identity + Entitlement/Edition at PEP]
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

### 5.2 Per-sub-plan table: deliverable, test command, acceptance gate

For each sub-plan, the plan file is `plans/phase0/<id>.md` (e.g. `0a-foundation.md`) — the spec tree `plans/` is a **sibling of** the code tree `tigerexchange/`, not inside it. The "test command" is run from inside `tigerexchange/`. The "acceptance gate" is what MUST be green before you start the next sub-plan.

| id | Delivers (one line) | Test command | Acceptance gate (must pass before moving on) |
|---|---|---|---|
| **0a** | Monorepo + frozen `contracts` kernel + Postgres FORCE-RLS tenant isolation + FastAPI `/health` + CI. | `uv run pytest -q` then `uv run ruff check . && uv run mypy . && uv run lint-imports --config packages/contracts/pyproject.toml` | Full suite green (unit + integration). Cross-tenant-read-denied (BOLA) RLS test passes. import-linter reports `1 kept, 0 broken`. Kernel fitness + compat tests pass. Week-1 gate docs present. |
| **0b** | Single fail-closed classifier; low-confidence/abstention → quarantine (= confidential, excluded from retrieval) + adjudication queue. | `uv run pytest services/classification/tests -q` (path per `0b`'s File Structure) | Inject low-confidence + adversarial records (confidential content with public-looking metadata); assert ZERO leak into any retrievable surface. MAX-rule + sticky-flag-UNION property tests pass. |
| **0c** | The single PEP + data-access broker chokepoint: ReBAC (SpiceDB) then ABAC (OPA) then revocation read, in one fixed order. | `uv run pytest packages/mod-pep/tests -q` | Broker DB-role can read ONLY confidential-artifact/classification tables, no feature schema. ABAC narrows-only; missing-attr → deny; PIP-unavailable-on-confidential → deny. Feature modules cannot import the raw store / classifier / construct a `PublishableProjection` (import-linter). |
| **0d** | Federated identity (Keycloak + CILogon OIDC) + Entitlement/Edition evaluated at the PEP + pooled-plane object-authz. | `uv run pytest -m integration -q` (needs Postgres + Keycloak) | A PLG-edition tenant cannot construct a confidential-tier or exchange request. Pooled-plane cross-tenant read denied by-ID, via SECURITY DEFINER path, AND via a borrowed PgBouncer connection after the prior tenant's transaction. |
| **0e** | Per-stream hash-chained, tamper-evident audit sink + periodic signed chain-head checkpoints. | `uv run pytest packages/mod-audit/tests -q` | Chain-tamper-detection test passes. Append-rate ceiling stated and shown to exceed peak per-cell operation rate. PEP decisions + data-access events recorded. |
| **0f** | Provider-agnostic, classification-routed Model Router + BYO keys + one owned tier→locality policy table. | `uv run pytest packages/mod_ai/tests -q` | A confidential request can NEVER select a cloud provider. A router/transport policy disagreement HARD-fails. BYO registration with attested locality fails closed to in-boundary when attestation is absent. |
| **0g** | All confidential derivative stores (Qdrant/OpenSearch/graph/object/cache) encrypted under tenant KEK/DEK + crypto-shred. | `uv run pytest -m integration -q` (needs Qdrant + OpenSearch) | After KEK crypto-shred, a search across vector + BM25 + graph returns NO decryptable hits. Table-B COGS line items sum to the stated total. |
| **0h** | Dagster ingestion DAGs (OpenAlex/Crossref/ROR/ORCID/SPECTER2 + grants) with classify-gate-index outbox + entity resolution. | `uv run pytest packages/mod-ingestion/tests -q` | Quarantined/unclassified records NEVER reach any index. Outbox carries per-record `projection_version` (lower-version-reject) and per-cell `revocation_epoch` distinctly. |
| **0i** | Hybrid retrieval (Qdrant + OpenSearch + RRF + reranker) + PEP-gated RAGAS eval harness in CI. | `uv run pytest packages/retrieval/tests -q` | A confidential eval cannot route to a cloud judge. Confidential eval traces are KEK-encrypted and shred on crypto-shred. RAGAS-in-CI gate fails the build on regression. |
| **0j** | Central-index read PEP: per-query authz + `discoverability_scope`, evaluated against owner-committed scope. | `uv run pytest services/central_index/tests -q` | Scope denied to a non-member; named-tenants allowlist enforced. Property test: no projection is ever queryable at a scope WIDER than the owner's currently-committed scope across version-skew/replay. |
| **0k** | Three feature modules: mod-lit-intelligence (grounded drafting), mod-discovery (public OpenAlex), mod-funding-lite (grant match). | `uv run pytest packages/mod-lit-intelligence/tests packages/mod-discovery/tests packages/mod-funding-lite/tests -q` | Modules import ONLY kernel interfaces + the broker (no raw-store/classifier/projection imports — import-linter). Generated draft + history KEK-bound and included in the post-crypto-shred zero-decryptable-hits test. |

> The exact sub-package paths for `0b`–`0k` come from each plan's own "File Structure" section, reconciled in `guide/CONVENTIONS.md` §2 (the canonical package/import-root map). Most feature modules are `tigerexchange/packages/mod-<name>/`, but note the deliberate exceptions: `0b` classification and `0j` central-index are **services** (`tigerexchange/services/classification`, `tigerexchange/services/central_index`); `0f`'s model router is `tigerexchange/packages/mod_ai` (underscore dir); `0i` retrieval is shared infra `tigerexchange/packages/retrieval` (no `mod-` prefix). Read `CONVENTIONS.md` §2 + the plan file for the canonical path before running its test command; if a guide doc disagrees with `CONVENTIONS.md`, `CONVENTIONS.md` wins.

### 5.3 How to execute ONE sub-plan, task-by-task (the inner loop)

Every sub-plan file (`0a`–`0k`) is a list of numbered Tasks. Each Task has 5 steps. Follow them literally, in order, one Task at a time. **This is strict TDD: you write the failing test first, watch it fail, write the minimum code, watch it pass, then commit.** We do this because (a) it proves the test actually tests something — a test that passes before you write code tests nothing; and (b) it keeps each change tiny enough to fit your limited context window.

```mermaid
graph LR
  A[Read plans/phase0/&lt;id&gt;.md Task N] --> B[Step 1: write the failing test file VERBATIM]
  B --> C[Step 2: run it, CONFIRM it fails with the stated error]
  C --> D[Step 3: write the minimal implementation VERBATIM]
  D --> E[Step 4: run it, CONFIRM it passes with the stated count]
  E --> F[Step 5: git add + commit with the stated message]
  F --> G{More tasks?}
  G -- yes --> A
  G -- no --> H[Run the sub-plan acceptance gate from 5.2]
```

Concrete procedure for Task N of sub-plan `<id>`:

1. **Read** `plans/phase0/<id>.md` (sibling of `tigerexchange/`), find "Task N". Read ONLY that task (to save context).
2. **Step 1 — write the failing test.** Copy the test code block from the task into the exact file path the task names. Do not paraphrase; the test encodes the contract.
3. **Step 2 — run it and confirm it fails.** Run the exact `python -m pytest ...` command the task gives. Confirm the error matches the task's "Expected:" line (usually `ModuleNotFoundError` or `FileNotFoundError`). If it does NOT fail, you copied the test wrong or the code already exists — stop and re-check.
4. **Step 3 — write the minimal implementation.** Copy the implementation block(s) into the named file path(s). For kernel files (`0a` Tasks 2–9), the code is reproduced verbatim and is authoritative — type it exactly, including docstrings.
5. **Step 4 — run it and confirm it passes** with the exact pass count the task states (e.g. `9 passed`). If the count differs, you have a typo; fix the implementation only (never weaken the test).
6. **Step 5 — commit** with the exact commit message from the task. Always end the commit message with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.
7. Repeat for Task N+1 until the sub-plan's tasks are exhausted, then run the **acceptance gate** for that sub-plan from the table in 5.2.

**Two known corrections in `0a` you must apply (the plan calls them out):**
- In `0a` Task 13 the test references `permits_tier_confidential_is_false()`, which is NOT a real kernel method. The plan instructs you to change that test line to `assert ctx.entitlement.permits_tier(Tier.confidential) is False` and add `from contracts.lattice import Tier` to the test imports. Do this — it preserves the kernel's frozen API.
- The kernel files in `0a` Tasks 2–9 must match `00-kernel-contracts.md` exactly. If `0a`'s reproduced code and `00-kernel-contracts.md` ever appear to differ, **`00-kernel-contracts.md` is authoritative** (it is the canonical kernel).

### 5.4 What `0a` builds (concrete reference, since you start here)

`0a-foundation.md` has 16 tasks. In order: (1) monorepo scaffold + py3.11+ + dev tooling; (2) kernel `lattice.py` (Tier MAX-rule, fail-closed parse, compliance flags); (3) `tenancy.py` (TenantContext, Edition, Entitlement, Capability); (4) `classification.py` (Decision ALLOW/DENY/QUARANTINE, DiscoverabilityScope, Caveats); (5) `projection.py` (PublishableProjection — rejects confidential tier, decision D6); (6) `pep.py` (PepRequest/PepResponse, non-ALLOW carries no payload); (7) `audit.py` (per-stream hash-chain AuditEvent); (8) `interfaces.py` (the ~13 K3 Protocols + InterfaceLocus/INTERFACE_LOCUS); (9) freeze kernel public API + fitness + compat baseline; (10) async DB engine with transaction-scoped `SET LOCAL`; (11) FORCE-RLS migration (RESTRICTIVE + WITH CHECK + tenant_id-leading index); (12) RLS-bypass lint (no SECURITY DEFINER / matview); (13) FastAPI app `/health` + tenant-context dependency + demo route; (13b) `api.dependencies` DI factory seam (fail-closed `get_*` stubs); (14) CI workflow; (15) full local green run; (16–18) Week-1 GTM/cost validation gate docs (non-code deliverables).

---

## 6. Running the whole test suite, ruff, and mypy

Run these from inside `tigerexchange/`. This is the same sequence CI runs (`0a` Task 15), so if all six are green locally, CI will be green.

```bash
cd tigerexchange && uv sync --all-extras                                   # 1. install/refresh deps
cd tigerexchange && uv run ruff check . && uv run ruff format --check .     # 2. lint + format check
cd tigerexchange && uv run mypy .                                          # 3. strict type-check
cd tigerexchange && uv run lint-imports --config packages/contracts/pyproject.toml  # 4. kernel fitness
cd tigerexchange && uv run python -m api_scripts.check_rls_bypass services/api/migrations  # 5. RLS-bypass lint
cd tigerexchange && uv run pytest -q                                        # 6. full test suite
```

Expected outputs: ruff prints nothing (clean); mypy prints `Success: no issues found`; `lint-imports` prints `Contracts: 1 kept, 0 broken`; the RLS lint prints nothing and exits 0; pytest is fully green.

**Marker-scoped runs** (faster inner loops):

```bash
cd tigerexchange && uv run pytest -m unit -q          # no Docker; fast
cd tigerexchange && uv run pytest -m integration -q   # needs Docker (testcontainers Postgres)
cd tigerexchange && uv run pytest packages/contracts/tests -q   # kernel only
cd tigerexchange && uv run pytest -k bola -q          # one test by name substring
```

---

## 7. Common errors and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'contracts'` | Workspace not installed, or kernel package not yet built (Task 2 not done). | `cd tigerexchange && uv sync`. If still failing, confirm `packages/contracts/pyproject.toml` exists (it is created in `0a` Task 2). |
| `ModuleNotFoundError: No module named 'api'` / `api.db` | `services/api` not installed. | `cd tigerexchange && uv sync`; confirm `services/api/pyproject.toml` lists `tigerexchange-contracts` and `[tool.hatch.build.targets.wheel] packages = ["src/api"]`. |
| Integration test hangs or errors `Could not connect to Docker` | Docker Desktop not running. | `open -a Docker`, wait for "Running", retry. testcontainers needs the Docker daemon. |
| `testcontainers` pulls `postgres:16-alpine` slowly / times out | First run pulls the image. | Pre-pull once: `docker pull postgres:16-alpine`. |
| `SET LOCAL` test shows tenant leaked across connections | Used `SET` instead of `SET LOCAL` / `set_config(..., true)`. | Use `SELECT set_config('app.tenant_id', :tid, true)` (the `true` = is_local, transaction-scoped) inside an explicit transaction — exactly as `0a` Task 10 `db.py` does. This is decision-relevant: transaction-scoping is what makes pooled PgBouncer connections safe. |
| BOLA test FAILS (tenant-A reads tenant-B's row) | Policy is PERMISSIVE not RESTRICTIVE, or `FORCE ROW LEVEL SECURITY` missing, or seeded rows inserted outside `tenant_session`. | Migration must have `FORCE ROW LEVEL SECURITY` and `AS RESTRICTIVE ... USING (...) WITH CHECK (...)`; seed rows THROUGH `tenant_session` so the tenant is bound. |
| mypy errors on a Pydantic model | Missing/loose types, or not on Pydantic v2. | Kernel is fully typed; copy the verbatim kernel code. Ensure `pydantic>=2.6,<3` is installed (`uv sync`). |
| `lint-imports` reports `1 broken` | The kernel imported a forbidden module (e.g. `sqlalchemy`, `fastapi`, `api`). | Remove the import — the kernel must be zero-dependency on persistence/feature packages (the fitness function). Move that logic into `services/api` or a `mod-*` package. |
| `griffe`/kernel compat test fails: "public API removed/renamed" | A symbol in `__all__` was deleted/renamed without updating the baseline. | If the change was intentional + additive, regenerate `packages/contracts/api/contracts_api.txt` (the command is in `0a` Task 9) IN THE SAME COMMIT. Never silently remove a frozen symbol. |
| ruff "import sorting" / format diffs | Code not formatted. | `cd tigerexchange && uv run ruff format . && uv run ruff check --fix .` |
| Docker memory pressure / macOS swapping during a build | Full stack + Ollama model + editor exceed RAM. | `ollama stop`, or `docker compose up -d postgres` only (for `0a`), or lower OpenSearch heap. |
| OpenSearch container unhealthy / OOM-killed | JVM heap not capped. | Confirm `OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g` is set in compose; restart it. |

---

## 8. Definition of Done — Phase-0

Phase-0 is DONE when ALL of the following hold simultaneously. Treat this as the final, auditable checklist.

1. **All 11 sub-plans `0a`–`0k` are complete**, each having passed its acceptance gate from the table in Section 5.2.
2. **The full local CI sequence (Section 6) is green** from a clean `uv sync`: ruff clean, `ruff format --check` clean, `mypy` `Success`, `lint-imports` `1 kept, 0 broken`, RLS-bypass lint exit 0, and `uv run pytest -q` fully green (unit + integration).
3. **The single PEP chokepoint holds (D4):** every retrieval/egress/derivation path is authorized through the one PEP; feature modules physically cannot import a raw store, the classifier, or construct a `PublishableProjection` (enforced by import-linter, verified in `0c`/`0k`).
4. **Fail-closed everywhere:** classifier abstention → quarantine (excluded from all retrieval, `0b`); unknown tier → confidential (`Tier.parse`, kernel); non-ALLOW PepResponse carries no payload (kernel); un-wired DI factory raises `NotWiredError`, never `None` (`0a` Task 13b).
5. **Confidential content never enters the shared index (D6):** `PublishableProjection` rejects confidential tier (kernel validator, verified in `0a` Task 5 + `0j`).
6. **Tenant isolation proven (D5/D7 pooled plane):** the FORCE-RLS cross-tenant-read-denied (BOLA) test passes, including the borrowed-PgBouncer-connection variant (`0a` Task 11, `0d`).
7. **Confidential-at-rest works (single-tenant own-data scope):** after KEK crypto-shred, a search across vector + BM25 + graph returns zero decryptable hits (`0g`, `0i`, `0k`).
8. **Owner-authoritative discovery scope (D5):** the central-index read PEP never serves a projection at a scope wider than the owner's currently-committed scope (`0j` property test).
9. **The Week-1 non-code gate docs exist and are structured** (`tigerexchange/docs/gates/week1-validation.md`: Gate A, Gate B, Q17, Line-(a) runway stress test, PLG-positioning), with the line-(a) ACV modeled at $20–60k (NOT $120k) and runway surviving on seed to the month-18 line-(b) landing (`0a` Tasks 16–18).
10. **The kernel public API is frozen and versioned:** `KERNEL_API_VERSION` present, the compat baseline `packages/contracts/api/contracts_api.txt` matches `contracts.__all__`, and the kernel fitness (size/fan-in, zero persistence deps) test passes (`0a` Task 9).

When 1–10 are all true, Phase-0 is complete and the walking skeleton is ready for Phase-1 (cross-institution federation: lighting up the deferred `IExchangeFeed`/`IRevocationAuthority` seams).

---

## 9. Quick command reference (copy/paste)

```bash
# --- one-time setup ---
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12   # any 3.11+ satisfies the >=3.11 baseline
brew install --cask docker && open -a Docker
brew install ollama && ollama serve & && ollama pull qwen2.5-coder:32b

# --- per checkout ---
cd tigerexchange && uv sync --all-extras
cd tigerexchange && uv run pre-commit install
cd tigerexchange && cp .env.example .env

# --- local stack ---
cd tigerexchange && docker compose up -d            # full stack
cd tigerexchange && docker compose up -d postgres   # 0a only
cd tigerexchange && docker compose ps               # health
cd tigerexchange && docker compose down

# --- the gate (run before every "done" claim) ---
cd tigerexchange && uv run ruff check . && uv run ruff format --check .
cd tigerexchange && uv run mypy .
cd tigerexchange && uv run lint-imports --config packages/contracts/pyproject.toml
cd tigerexchange && uv run python -m api_scripts.check_rls_bypass services/api/migrations
cd tigerexchange && uv run pytest -q
```
