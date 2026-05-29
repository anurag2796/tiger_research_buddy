# Decision & Evolution Log

This task is pure synthesis from the provided JSON and final plan. No tools needed.

# TigerExchange — Decision & Evolution Log

*Adversarial critique loop, v1 → v5. For founder records. Reconstructed from per-version critic findings (5 lenses: Distributed-systems & scalability; Security/privacy/confidentiality; Maintainability & modularity; Product/GTM/viability; Cost/ops/founder-feasibility) and the locked final plan (v5).*

---

## Macro arc

| Version | Critical | High | Net movement |
|---|---|---|---|
| v1 | 10 | 21 | Baseline. Plausible-sounding claims that contradict their own sections. |
| v2 | 8 | 22 | Mechanisms named (revocation set, HLC, PublishableProjection) but internally incoherent under CAP/skew. |
| v3 | 9 | 22 | Freshness-watermark architecture introduced; critics show it is fail-open and SPOF-bound. |
| v4 | 9 | 20 | Synchronous multi-region consensus on hot path — anti-scaling; econ contradiction sharpens ($30k ACV vs $36–60k COGS). |
| v5 | 0 | 0 | Hot path becomes a local lease read; chokepoint, privacy-gate, owner-side re-derivation, and unit economics all reconciled. |

The headline structural insight earned across the loop: **the same finding kept recurring under different masks** — "how does revocation stay correct without putting a global synchronous dependency on the hot path?" v1 hand-waved it, v2–v4 each proposed a global-consistency primitive that the critics killed on CAP/SPOF/latency grounds, and v5 finally inverted it (consensus on the low-rate *write*, local lease read on the hot path).

---

## v1 → v2: From asserted guarantees to named-but-incoherent mechanisms

### What the critics flagged (by lens)

- **Distributed-systems (2 critical, 4 high):** Revocation correctness depended on an unbounded CDC fast-path; the "read-time re-check makes correctness independent of propagation latency" claim was only half-true — it protected drill-down but not the *central index's* surfacing of fact-of-existence/metadata after a REVOKE or reclassification (CDC is append-only; tombstone/delete propagation unspecified). SpiceDB was drawn as a single globally-consistent cross-tenant store on the hot path, contradicting the plan's own "confidential check never depends on the shared plane." The central index was mislabeled "thin/stateless" while actually being the write-amplified union of all tenants' corpora. Brokered drill-down availability was treated as independent when it is the *product* of A-PEP × control-plane × B-cell. Hot-tenant and per-cell KG/vector growth were essentially unmodeled.
- **Security (4 critical, 6 high):** The entire confidentiality guarantee was single-point-of-failure on the classifier with no defined fail-mode, no default tier, no derived-data tiering. The "publishable metadata only" Outbox invariant was *trusted, not checked* — CDC ships whatever is in the outbox table. The central index was an unencrypted cross-institution honeypot with no per-query authz. Revocation was correct only for future reads (cached/derived/in-flight data unaddressed). ABAC+ABAC composition order and fail-mode were under-specified (fail-open risk on missing `export_controlled`). Deemed-export collected nationality with no trustworthy source. BYOK had DEK-at-use exposure and crypto-shred that didn't reach embeddings/BM25/graph derivatives.
- **Maintainability (1 critical, 5 high):** The module DAG contradicted the "a module never imports another module" rule (mod-funding semantically consumes mod-discovery's expertise/graph). The 8 kernel contracts were entangled and versioned as one unit. The "swappable" router actually carried four responsibilities (routing + compliance egress + guardrails + eval coupling). `IRetrieval` was a leaky catch-all across single-shot/multi-hop/corrective/multi-agent. The federation seam — the existential boundary — had no testable contract for "publishable."
- **Product/GTM (2 critical, 4 high):** The MVP delivered *none* of the moat and landed in the most commoditized arena the plan itself said to avoid. Beachhead unit economics were likely inverted (confidential GPU cell cannot be served at ~$300/mo). PLG "below-committee-threshold" contradicted the day-one governance burden. Cold-start was asserted, not solved. Pricing benchmarks were borrowed from non-analogous products.
- **Cost/ops (2 critical, 5 high):** Phase-0 "MVP" mandated the entire kernel + 6 infra systems + SOC2 before first revenue. Unit economics inverted (buried as Open Question #4). Self-hosted node burden dumped on Research IT. SOC2 Type II treated as free/fast. Two orchestrators + Kafka + Debezium + schema registry over-engineered for a few labs. TEE under-priced.

### What changed in response (v2)
- Introduced a **"strongly-consistent revocation set"** as the explicit metadata-leak gate.
- Introduced **per-record HLC monotonicity** for revoke-ordering / idempotent CDC.
- Reclassified the central index as **first-class stateful**, sized in GB, sharded by topic.
- Introduced **PublishableProjection** (total projection function, every field non-published by default) and an **independent egress PEP** to make "publishable" a checked rather than trusted boundary.
- Added **`IExpertiseGraph`** as a kernel-owned decoupling seam so mod-funding need not import mod-discovery.
- Introduced **`ClassificationCapabilityDescriptor`** to data-drive tier consumption.
- Retired the commodity public-tier wedge; moved first revenue onto the confidential/federation capability; framed a **pre-bonded 2-node consortium** as the bootstrap.

### Decisions locked
- Confidential bytes never centralize; only projections + grant references leave a cell.
- Classifier fail-closed (direction stated) and projection-by-default-deny become the intended leak defenses.
- Central index is stateful and must be sized/sharded.

---

## v2 → v3: The consistency primitive collapses under CAP and clock-trust

### What the critics flagged (by lens)

- **Distributed-systems (2 critical, 4 high):** The "strongly-consistent revocation set" was simultaneously required to be strongly consistent, replicated to every geo-distributed cell + index, and checked inline <5s — **direct CAP tension never reconciled** (a replicated copy is not strongly consistent at the consumer). Per-record HLC monotonicity assumed a single logical clock domain, but the nodes are mutually-distrusting, possibly air-gapped sovereign cells with skewable clocks — a 10-min-fast node can stamp a publish that dominates a legitimate later tombstone, **resurrecting revoked metadata**. The discovery path never composed the cost of inline per-hit revocation gate + per-query PEP + discoverability filter inside 800ms. Ordered grant replication's *liveness* (how a cell knows its replica is stale) was undefined. The re-lease firehose (TTL'd records) was an unmodeled write-amplification floor.
- **Security (2 critical, 5 high):** The revocation set is an **eventually-replicated artifact masquerading as strongly consistent**; a stale replica surfaces the exact leak. **MRL truncation was mislabeled a privacy mechanism** (it is a quality knob — membership inference / embedding inversion / co-occurrence survive). Operator-trust boundary was internally contradictory (operator runs Vault + egress PEP; "never leaves" overclaimed for managed cells). GDPR erasure via crypto-shred doesn't reach control-plane-keyed central-index data or federated grantee copies. The classifier is a prompt-injection target whose fail-closed-on-abstention does **not** defend against a confident *downgrade*. PSI/DP differencing across *multiple* pairs + index was unmodeled. Grantee-side propagation of grantor caveats (sticky policy) was absent.
- **Maintainability (1 high noted but the descriptor critique was central):** `ClassificationCapabilityDescriptor` was **false decoupling** — tier is pervasive policy (fail-closed default, MAX-derivation, output clamp, BYO eligibility, local-only routing), not a lookup value; a 4th tier still forces edits across classifier/router/egress/Cedar/edition. `IExpertiseGraph` was an unspecified write-once/read-many **god-contract** relocating the DAG cycle into a shared schema. PublishableProjection created a parallel data model with no versioning story across independently-upgrading nodes. import-linter cannot catch coupling through the **shared Postgres** the MVP consolidates into.
- **Product/GTM (2 critical, 5 high):** Entire revenue plan rested on a **four-way-AND buyer** (legal + technical + joint-scheduling + budget) filed under Open Question #1. Differentiated value vs fast revenue in unacknowledged tension. The fallback export/defense lab is a *harder* first sale (CMMC/DCSA/air-gap) than the primary. WTP anchored to COGS, not external evidence (free VIVO, $179 Atom). Cold-start "restated, not solved" (a dyad is N=2 with one edge). PLG scoped down to undifferentiated. Sales-cycle-vs-runway never quantified.
- **Cost/ops (2 critical, 5 high):** Phase-0 ~12 hard subsystems, each a multi-week hardening effort because one bug is the existential leak. Vault namespaces are Enterprise-only (the OQ#6 answer was already knowable). Cloud-GPU COGS understated (~$735–1,454/mo for one A10G/L4 alone; no HA budget vs 99.9% SLO). Central OpenSearch sized in GB but never in dollars/owner. The four-edition surface must be designed up front even if sold one motion at a time.

### What changed in response (v3)
- Replaced the bare revocation set with a **freshness watermark**: consumers fail-closed if their watermark is older than `(now − leak-window)`; per-shard revocation **bitmaps**; "incomplete" flag on stale/absent shards.
- Introduced a **single-region linearizable Revocation Authority** (etcd/Spanner-class) as the monotonic version source.
- Phase-staged the sync stack: outbox-polling Phase 0/1, Debezium+Kafka CDC at Phase 2 (when the central index first exists).
- Added **counter-signed audit receipts** + two-sided reconciliation.
- Two-tier **topical-cluster sharding** for the central index.
- Began honest qualification of managed-cell trust (operator in TCB; "provably" reserved for sovereign+TEE).

### Decisions locked
- A monotonic authority *version* — not wall-clock timestamps — orders security decisions (kills the HLC-skew attack in principle).
- The leak-window becomes an explicit, first-class SLO target.
- Central index is sharded by topic.

---

## v3 → v4: Freshness watermark proves fail-open; SPOF and synchronous-consensus surface

### What the critics flagged (by lens)

- **Distributed-systems (2 critical, 4 high):** The watermark had **no propagation mechanism, no monotonicity-under-failover, no end-to-end budget** (punted to OQ#4) and compared against the consumer's **local skewed `now`**. The single-region linearizable authority was a **global synchronous SPOF** — its *outage* (not partition) ages every cell's watermark past the window and **fails-closed the entire confidential feature platform-wide**, contradicting "cell-isolated failure domains" and 99.95%. Topical sharding recreated **hot shards** (power-law topics), incurred **re-clustering/re-embedding drift** never costed, and **fanned the revocation bitmap across many shards**. The phase-inconsistent sync stack meant Phase-1 federation had *no Kafka and no central index* yet still claimed a CDC tombstone/watermark feed. Brokered drill-down's ~98.5% availability *stacked* with freshness-deny + authority-deny into a near-total correlated outage during any control-plane blip.
- **Security (2 critical, 5 high):** **The watermark gate is fail-OPEN inside the leak-window for the wrong event** — watermark freshness proves the channel is alive, not that *this grant* isn't revoked; a revoke committed 1s ago is served as ALLOW for the full propagation latency. LSH-code non-invertibility was **asserted, not established**; existence/count/topical-cluster/churn metadata *is* the leak regardless. Subject deprovisioning was enforced only on confidential drill-down, leaving private/own-materials on bearer-token-expiry. Audit divergence was *detected* but had **no defined response** and no before-vs-after counter-sign protocol (repudiation gap). The **MAX-rule conflicts with the index design**: an LSH/fingerprint derived from confidential data should be confidential by MAX, yet the index is designed to receive it — an unreconciled carve-out. Managed-cell operator is in TCB + holds key-unwrap + runs egress PEP, yet is the Phase-0 product sold to "security-sensitive" buyers. BYO-confidential trusted an **unverified institutional attestation** (config-time bypass of the strongest router invariant).
- **Maintainability (1 critical, 5 high):** The TierLattice "compiler-enforced exhaustiveness across five consumers" **cannot exist** — consumers are independently-deployed services/appliances with no shared compilation unit, and Python has no compile-fail exhaustive match. The kernel was a **god-object by accumulation** (11+ contracts) with no kernel-wide version or change-frequency bound. "Additive-only forever" with no exercised removal path is an unmaintainability *guarantee*. **Distributed monolith**: independently-deployed services sharing one Postgres via cross-schema grants. The router/transport "disagreement = hard fail" makes the router *not* low-blast-radius-swappable (a disagreeing replacement is a hard outage).
- **Product/GTM (2 critical, 5 high):** Phase-0 is a **single-tenant confidential RAG tool with none of the federation value**, competing with NotebookLM/Glean/ChatGPT-Enterprise. Cold-start hand-waved (LOIs ≠ deployed nodes). $30k floor ASP **below loaded COGS+CAC**; BYO-compute escape *escalates* friction. Four sequential enterprise motions run by one GTM hire across ~3 years. The race-window thesis defeated by its own timeline (defensibility milestone lands *after* the threat window). Beachhead internally contradictory (strip export/defense/CMMC and the remaining segment is narrow). Procurement time under-budgeted vs runway; pilot sold before any SOC2 exists.
- **Cost/ops (2 critical, 5 high):** Phase-0 "3-engineer-buildable" materially larger than admitted (platform/abstraction work delivering zero customer value before first dollar). **Burn/runway model omitted salaries** entirely. Vault Community per-cell, SpiceDB cell-local replica, freshness feed, per-shard bitmaps, egress PEP = a dense bespoke distributed-systems cluster for 3 people in one phase. **$30k ACV vs $36–60k/yr dedicated-cell COGS = structural loss.** OpenSearch Serverless idle-OCU floor from node 1. Per-cell Vault ops toil uncounted.

### What changed in response (v4)
- Made the revocation authority **multi-region consensus** and put a **synchronous authoritative check on the confidential hot path** with a 6.5s composite SLO.
- Generalized **owner-side re-derivation from export-only to all cross-tenant access**; grantee/broker assertions = untrusted hints; HSM-DPoP, confused-deputy-safe tokens.
- Replaced the all-attest exhaustiveness with **signed conformance attestation per consumer + control-plane refuses activation until all attest** (and runtime fail-closed deny).
- Strengthened audit (hash-chain + fair-exchange receipts + external timestamp + divergence auto-suspend).
- Honest labeling of **bounded ALLOW windows** by tier; quarantine-on-abstention direction; BYO-endpoint verification claim (in-boundary proof + mTLS + no-retention).

### Decisions locked
- **Owner-side authoritative re-derivation** is the universal cross-tenant invariant (confused-deputy/IDOR closed in principle).
- Consensus ordering for revocation writes.
- Cross-tenant linkage / membership inference must be in the threat model.

---

## v4 → v5: Invert the hot path; reconcile economics; decompose the impossible phase

### What the critics flagged (by lens)
v4's two unresolved critical fault-lines drove the final rewrite:
1. **Distributed-systems / Security:** A synchronous multi-region-consensus check on the un-sheddable confidential hot path is **anti-scaling** (a per-request global serialization point) and **fails closed platform-wide during any leader election/partition** — total outage of the flagship feature exactly when the network is stressed, with an unsourced "~80–150ms" never derived from Raft RTT + HSM latency. CDC ordering/idempotency/exactly-once semantics still undefined; un-sharing is an *eventual* CDC event (unbounded discoverability window). The all-attest activation gate was a **global liveness barrier** across autonomous nodes (deadlock or silent degrade) **and** a correctness hazard (nodes comparing on different lattices mid-rollout).
2. **Maintainability / Product / Cost:** Confidentiality smeared across 7 mechanisms made "minimal blast radius" structurally unachievable. The shared-contracts package had no scaling evolution mechanism. import-linter alone (no DB-role isolation in Phase 0) cannot stop shared-table coupling. **Self-contradictory unit economics: $30k kill-gate floor vs $80–130k/mo burn and $36–60k/yr COGS.** Phase 1 was a multi-year platform program listed as one milestone. Salaries + compliance cash absent from burn. Cold-start still on non-binding LOIs.

### What changed in response (v5) — the resolutions

| v4 problem | v5 resolution |
|---|---|
| Synchronous consensus on hot path (anti-scale + global outage) | **Lease-based local read.** Raft consensus only on the low-rate revocation *write*; hot path is a local fenced-lease read (~15ms p99). Authority partition = **TTL-bounded graceful degradation then deny**, not instant total outage, with a **published deny-minutes/year release gate**. |
| Revocation fail-open inside leak-window | Lease-TTL is the explicit, first-class allow-window (2s default); **security-reason/consent-withdrawal/compromise revocations take a synchronous zero-window path regardless of tier** (§4.5). |
| Confidentiality smeared across modules | **Single mediated PEP + data-access broker chokepoint**; modules receive already-projected, already-tier-checked objects and structurally cannot touch raw store/classifier — so adding mod-funding **inherits enforcement for free** (reconciles the two coupled locked requirements). |
| All-attest barrier (liveness + correctness) | **Additive, two-phase recognize-before-emit, fail-closed-by-construction** lattice; unknown tier treated as most-restrictive; min-common version at the Exchange. No global barrier. Governance machinery deferred to N≥5. |
| Privacy bound proven too late (one-way door) | **Membership/inversion/linkage red-team is a Phase-1 DESIGN gate on synthetic/de-identified corpora before any real embedding ships.** Bound pinned to `IIndexProfile`; embedding swap re-validates through a gate. |
| Operator audit rewrite | **External chain-head anchoring** (TSA/transparency log) makes internal-only access tamper-evident even against the node operator; **per-stream parallel chains** remove the serial throughput ceiling. |
| $30k vs COGS contradiction | **Floor ASP raised to $75–150k** (HYOK+GPU+SOC2 enterprise deal) AND **Phase-0 COGS collapsed to ~$1.5–2.5k/mo via shared/burstable GPU + shared index** → ≥60% margin gate. Burn now itemizes salaries + compliance cash (~$94k/mo; $3.0M → ~32-month runway). |
| Phase 1 = multi-year monolith | **Decomposed into 1.0 / 1.1 / 1.2** with independent gates; single-region authority first (accept SPOF for the dyad), multi-region lease authority only if N>2/SLO demands. |
| Cold-start on LOIs | **Sell first dyad into a pre-existing legal sharing vehicle** (NIH U01/U54, NSF AI institute, master DUA) as a hard Phase-1 entry gate. Two independent kill-gates (A appliance demand / B federation-thesis demand). |
| Export deemed-export via operations | **Export-conformant cells only** (US-person ops + US-region + TEE); router refuses placement otherwise; data not accepted until conformant. |
| Distributed-monolith coupling | Per-module schemas + **DB-role REVOKE from day one** + "no cross-schema query" check + versioned domain events (CDC only for a module's own read store). |

v5 returned **zero blocking findings**.

---

## Resolved Tradeoffs (locked decisions)

1. **Revocation consistency vs scalability/availability** — Resolved by *splitting the path*: Raft consensus on the low-rate write, local fenced-lease read on the hot path (~15ms p99). Lease-TTL is the honest, first-class allow-window; security-reason revocations get a synchronous zero-window path. Authority partition degrades TTL-boundedly then fail-closed-denies, with a *measured* published deny-minutes/year as a release gate rather than an asserted number.
2. **Modularity vs cross-cutting confidentiality** — Resolved by a *single mediated PEP/broker chokepoint*. The two locked requirements (pluggable modules with minimal blast radius; end-to-end confidentiality enforcement) were proven coupled by the critics and then decoupled by routing all enforcement through one boundary modules cannot bypass; new modules inherit enforcement.
3. **Tier-model extensibility vs distributed safety** — Resolved by an additive, formally-specified, near-frozen 3-tier lattice with two-phase recognize-before-emit and unknown-tier-as-most-restrictive; no global attestation barrier. Heavy governance machinery deferred to N≥5.
4. **Central-index discovery value vs irreversible privacy leak** — Resolved by making the privacy bound a Phase-1 design gate proven on synthetic data *before* the one-way door opens, with cross-tenant linkage explicitly in the threat model, the bound pinned to `IIndexProfile`, and gated embedding swaps.
5. **Confused-deputy / cross-tenant IDOR** — Resolved by owner-side authoritative re-derivation as the *universal* invariant (broker/grantee scope claims are untrusted hints), plus grant-ID lookup and audience-bound single-use HSM-DPoP tokens.
6. **Operator trust** — Resolved honestly: managed cell = bounded processor (not zero-trust); "provably/never-leaves" reserved for sovereign+TEE; audit externally anchored against the operator; plaintext-at-use residual stated, TEE as the upgrade path.
7. **Unit economics** — Resolved by raising floor ASP to $75–150k *and* collapsing Phase-0 COGS via shared/burstable GPU + shared index → ≥60% margin gate; burn itemized including salaries and compliance cash.
8. **MVP scope vs runway** — Resolved by decomposing Phase 1 into three independently-gated sub-phases, deferring HYOK to the first real-confidential-data customer, deferring multi-region authority/Temporal/Cedar/fair-exchange/governance machinery to demand-or-N triggers, and managed-cell-only through Phase 1.
9. **Cold-start** — Resolved by refusing to bootstrap a relationship from zero: the first dyad must digitize a pre-existing legal sharing vehicle, gated before Phase-1 commit.
10. **Self-host / export buyers** — Resolved by deferral: managed-only Phase 0–1; self-host is a separately-funded Phase-2+ edition; export-controlled data not accepted until export-conformant cells exist.

---

## Remaining Open Questions to validate with customers/spikes

These are explicitly *not* closed by the architecture — they are demand/legal/measurement facts the plan gates real spend on:

**Demand & GTM (kill-gates):**
- **Gate A (Week 1, hard):** ≥2 of 3 named labs give written ≥$75k/yr price indication vs a budget line; ≥1 funds a paid sandbox. Fail → pivot the wedge before engineering.
- **Gate B (Week 1, hard):** the *same* buyers (or a named peer pair) confirm in writing a concrete, funded cross-institution confidential-sharing pain. Fail → federation thesis is unvalidated; Phase 1 becomes an independent kill-gate, not an automatic continuation.
- **Cold-start (before Phase 1, hard):** one pre-existing confidential-sharing relationship + its legal vehicle confirmed.
- **Procurement (Week-1 sub-condition, hard):** a named buyer confirms in writing a paid sandbox can sign *without* full vendor security review / BAA. Fail → re-baseline runway against the full-review cycle.
- **Pilot→recurring conversion** (target 50% within 4 months) and the founder-led 6–9 month first-close date — validate against real runway.
- **PLG locked-requirement sign-off** — confirm "sellable to PLG" is satisfied by a loss-leader brand-surface tier rather than standalone PLG revenue.

**Distributed-systems / cost spikes (release gates):**
- **Revocation lease latency + partition deny-minutes** — measure local-lease read p99, leader-election stall bound, publish a *measured* confidential deny-minutes/year (not a target).
- **SpiceDB ZedToken→local-revision replication go/no-go (Week 1)** — if monotonic reads under lag cannot be guaranteed, fall back to cell-local cached authz + sync re-check on the confidential subset only.
- **AGE multi-hop/PPR at R1 scale** (synthetic) — benchmark; Neo4j/Memgraph swap via `IGraphStore` conformance suite if it fails.
- **Index skew/drift/bitmap locality** (synthetic OpenAlex) — topical concentration of corpus *and* queries; bounded shard set; re-cluster/re-embed cost.
- **Central graph cost + team-assembly quality at N=10/50/200** — validate sharding triggers (shard at ~N≈50) and bounded-candidate assembly.

**Privacy / security spikes (design gates):**
- **Central-index privacy red-team (Phase-1 design gate, synthetic)** — membership inference + embedding inversion + cross-tenant linkage; quantified ε/k/churn bound in `shared/contracts/`; rollback procedure. *Must pass before any real embedding is written.*
- **BYO endpoint verification + sovereign-tier definition** — in-boundary proof + mTLS + TEE-attestation matrix per pre-certified cloud; "no-retention" remains a contractual control until TEE-attested.
- **TEE deployment surface** — Nitro vs SEV-SNP/TDX abstraction + attestation; spike when the first export-class buyer's threat model demands it.

**Compliance / legal (officer sign-offs):**
- **Export-control operational surface** (officer) — confirm US-person ops + US-region + TEE conformance covers *operational* access, not just end-users.
- **GDPR controllership / transfers / lawful basis** (DPO) — EU-region pinning; **is opt-out-default defensible for EU subjects, or is opt-in / legitimate-interest balancing required?**; per-tier/per-reason max-staleness acceptability for withdrawn consent.
- **FERPA gating + flow-down** (registrar) — owner-side + role re-check + sticky flag + audit authz sufficiency; per-tier/per-reason allow-window acceptability.
- **CILogon cost & eduGAIN/SAML brokering effort** — hard quote + engineer-weeks (gates university/consortium buyers).
- **SOC2 timing** (real CISO) — confirm the sandbox/de-identified pilot avoids full prod review and that Type I can land at the Phase-0/1 boundary.
- **PMC/Europe PMC OA-subset** — confirm the commercial-OK filter yields a usefully large corpus; size the ingestion/embedding cost line.
- **PSI usability + scaling** (Phase-1 spike) — pairwise O(N²) vs multiparty; bounded set sizes; confirm the k-anon-bucketed-overlap fallback returns useful answers (so the feature is not architecturally dependent on cryptographic PSI).
- **Eval gold-set bootstrapping per tenant** — built inside the cell; who labels; GPU-staging judge cost.

**Defensibility (the standing market bet):** reaching **N≥2-with-gravity** inside the incumbent replicate window (4–6 quarters), targeting **N≥5 + ≥1 multi-year consortium by month 24**; if unreachable on the modeled ramp, the **regulated-niche down-scope is the primary plan-B**, triggered explicitly rather than discovered late.