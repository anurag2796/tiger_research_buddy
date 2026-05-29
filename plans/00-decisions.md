# Locked Founder & Architecture Decisions

These decisions are the fixed anchor for the final plan. The first adversarial loop (4 rounds, plan1–plan5) never converged because each fresh critic panel **re-litigated strategy** instead of checking implementation. Locking the strategy below — and bounding critics to "is this *implemented* correctly / does it raise a *new* risk" — is what lets the plan converge.

---

## D1 — Beachhead wedge (LOCKED): Grant Intelligence as a cross-institution team-assembly + secure proposal-collaboration product

The user tilted toward the grant wedge and asked for the best long-run choice. They are the same choice. Among the four wedges, grant intelligence is the **only** one that is simultaneously:

1. **Validated buyer + validated willingness-to-pay** — research-development / sponsored-programs offices already buy here (Cayuse, Kuali Research, Pivot-RP are six-figure institutional contracts; Atom Grants validates the PLG floor at ~$179/mo across 50+ institutions).
2. **Intrinsically cross-institution** — large federal mechanisms (NIH U54/U01 centers, NSF AI Institutes, DOE, multi-PI R01s) *require* multi-institution teams. "Find me partners at other universities to assemble a competitive team for this RFP" is a real, recurring, high-value job. This means the wedge **needs** the federation layer rather than waiting for it — it does not have a cold-start problem the way pure discovery does.
3. **Confidential-data-using, but scoped** — proposals, budgets, preliminary data, and team negotiations are confidential and cross-institution. So the confidential tier + cross-institution sharing grants are exercised early, **but scoped to the proposal-collaboration use case** (not "all research data everywhere"), which is what makes the hard confidentiality machinery tractable for a small team.
4. **The demand-driver that pulls in the other three wedges as its natural decomposition** (see D2).

**Moat:** not the grant database (commodity: Grants.gov, NIH RePORTER, NSF, Pivot). The moat is the **cross-institution expertise graph + confidential team-assembly/proposal workspace + the federation network** — which compounds as institutions join. That is defensible in a way single-lab secure-RAG (which competes with Glean/Copilot/NotebookLM) is not.

**Buyers (in order):** (1) the anchor consortium's center-administrative core / RD office (institutional, mid-ACV); (2) individual PIs writing/renewing grants (PLG top-of-funnel). This naturally serves "sell to all buyers" over time without four products.

## D2 — Scope (LOCKED — my decision, per user's "pick it yourself and document why"): Narrow-to-land, full architecture

Build the **full modular architecture** so nothing is thrown away, but commit to the grant wedge + anchor consortium for the first **12–18 months**.

**Why I chose this over "keep maximalist":** the adversarial review proved (with numbers) that "all 4 wedges + sell to all 4 buyers + full confidential federation" turns Phase 1 into an 18–36-month pre-revenue program for a 3–4 person team, and inverts unit economics (per-cell COGS ≈ or exceeds wedge ACV). Maximalist-on-a-fast-timeline only works with significant funding *before* any validation — a bet-the-company move the evidence doesn't justify. Narrowing makes the team size and the numbers close while the constant architecture preserves the entire long-run vision.

**The elegant part:** the other three wedges are not "deferred features" — they are the **natural decomposition of the grant workflow**, so building the wedge legitimately builds slices of all four:
- *Team assembly* → **expert/collaborator discovery** (wedge 1)
- *Proposal grounding / prior-art / aims drafting* → **literature & research intelligence** (wedge 2)
- *Confidential proposal/budget/data co-editing across institutions* → **secure shared workspaces** (wedge 3)
- *The grant itself* → **grant & funding intelligence** (wedge 4)

So we ship one focused product that exercises the whole platform kernel.

## D3 — Cold-start (LOCKED, user choice): Anchor on one existing federally-funded multi-site center

Land **one** existing multi-institution unit that already shares confidential data under an existing legal vehicle (NIH U54/U01 center, NSF AI Institute, or an established research consortium) as the design partner. This gives, on day one: **N≥2 nodes**, a **pre-existing DUA** as the legal basis for confidential cross-institution sharing, and a **recurring, funded grant need** (renewals, supplements, new sub-projects) = a paying customer, not just a federation seed.

## D4 — Confidentiality enforcement = single Policy Enforcement Point (resolves the modularity-vs-confidentiality contradiction)

All retrieval / egress / derivation flows through **one Policy Enforcement Point (PEP) + data-access broker**. Feature modules stay "dumb" and pluggable behind it; they do **not** each re-implement the ~7 confidentiality mechanisms. This restores the locked "pluggable modules, minimal blast radius" requirement: adding wedge #4's funding module cannot become a leak vector because it physically cannot bypass the chokepoint.

## D5 — Owning node is the local authority (resolves the confidential hot-path latency/availability impossibility)

There is **no global multi-region consensus on the hot path.** The institution that owns a confidential artifact is the **sole authority** for access/revocation decisions on it; checks are **owner-local and fail-closed locally**. Discovery metadata is eventually-consistent and may be centrally indexed; **confidentiality decisions are strongly consistent at the owning node only.** This removes the multi-region-consensus-on-every-request anti-scaling serialization point and bounds the failure domain to a single node.

## D6 — Confidential content never enters the shared index (resolves the one-way-door leak)

The shared central index holds **only public-tier + explicitly-shared metadata + non-reversible derived signals** — never confidential-derived content or embeddings. The membership-inference / embedding-inversion / cross-tenant-linkage **red-team is a hard GATE on synthetic/de-identified corpora *before* any shared-index write** (not a GA gate after data is already published). Classifier abstention/ambiguity → **quarantine to default-deny (unclassified = treated as confidential, excluded from all retrieval) + human adjudication** before the record is usable.

## D7 — Unit economics floor

Revenue anchor is the **institutional / center sale** priced so **ACV ≥ 2–3× per-tenant COGS**; the $179/mo individual is top-of-funnel, not the model. Non-confidential workloads run **multi-tenant pooled**; **dedicated isolation is reserved for the confidential tier** to keep COGS bounded.
