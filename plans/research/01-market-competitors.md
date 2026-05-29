# Research: market-competitors

I now have everything needed for a rigorous, well-cited landscape. The CTSAsearch/Direct2Experts finding is important — it proves cross-institution federation has been attempted in academia but only for *public* linked-open-data, never for confidential tiers. That sharpens the white space. Let me synthesize the full report.

---

# Competitive & Market Landscape: Federated Multi-University Research Collaboration & Discovery Platform

*Research date: May 2026. All claims cited inline. Where pricing is "custom/contact sales," that itself is a market signal (enterprise procurement, not PLG).*

---

## Executive read

The market is **fragmented into six silos that each solve one of your four pillars partially, none of which is federated-with-confidentiality or AI-native end-to-end.** Incumbents (Elsevier, Clarivate, Digital Science) own the *data and profile* layer; a fast wave of VC-style startups (Elicit, Consensus, SciSpace, Undermind, Atom Grants) own the *AI workflow* layer but are single-tenant SaaS over **public** literature only; research-admin incumbents (Cayuse, Kuali) own the *compliance/grants* layer. **Cross-institution federation exists in academia only for public linked-open-data (VIVO/CTSAsearch), and confidential data-sharing exists only in commercial clean rooms (Decentriq, Snowflake, Databricks) that have no research-domain features.** Nobody fuses all three. That intersection is your white space.

---

## Segment 1 — Research Information Management Systems (RIMS) / faculty-profile & expertise systems

These are the incumbent "system of record" for institutional research output. **This is the buyer you must coexist with or displace, and where the highest GTM friction lives.**

| Product | Who buys | Deployment | Pricing signal | Strength | Gap vs. your platform |
|---|---|---|---|---|---|
| **Elsevier Pure** | Research office + library; senior leadership | Vendor-hosted SaaS or institutionally hosted | Enterprise, custom; no free tier, free trial only ([Capterra](https://www.capterra.com/p/233902/Elsevier-Pure/), [SoftwareWorld](https://www.softwareworld.co/software/elsevier-pure-reviews/)) | System of record; **Pure Experts Portal** = turnkey expertise profiling + research-networking; feeds SciVal ([Elsevier](https://www.elsevier.com/solutions/pure/2021-backup/features-/pure-experts-portal)) | Single-institution; no confidential tier; no cross-institution sharing grants; AI bolt-on, not AI-native |
| **Clarivate Converis** | Research office | Vendor-hosted | Enterprise custom | Workflow/compliance-heavy RIMS | Same as above; Clarivate's strategic energy is shifting to Esploro post-ProQuest ([Scholarly Kitchen](https://scholarlykitchen.sspnet.org/2021/05/18/clarivate-to-acquire-proquest/)) |
| **Ex Libris / Clarivate Esploro** | **Library**-led (Ex Libris is a library-systems vendor) | SaaS | Enterprise custom | Configurable researcher profiles + portal; captures outputs/projects/activities; ProQuest acquisition strengthens it vs Pure/Symplectic ([Esploro](https://exlibrisgroup.com/products/esploro-research-services-platform/researcher-profiles/), [Scholarly Kitchen](https://scholarlykitchen.sspnet.org/2021/05/18/clarivate-to-acquire-proquest/)) | Library-centric; no confidential project workspaces; no federation |
| **Symplectic Elements** | Research office | SaaS/hosted | Enterprise custom | Strong publication harvesting; sibling to Springer Nature/Digital Science orbit; competes head-to-head with Pure/Converis/Esploro ([Sourceforge](https://sourceforge.net/software/product/Symplectic-Elements/alternatives)) | Same structural gaps |
| **Interfolio (Faculty Information System)** | **Faculty affairs / provost** (RPT, faculty lifecycle), not research office | SaaS | **FTE-based**; example institution paid ~$27,907/yr incl. $5,400 service pkg, +~$800/yr escalator; range "few thousand to six figures" ([Interfolio cost FAQ](https://www.interfolio.com/blog/faq/how-much-does-interfolio-cost/), [Oreate analysis](https://www.oreateai.com/blog/understanding-the-costs-of-interfolio-a-comprehensive-guide/5595d0b61c3ed83d4f456010a84f6ee4)) | Best public pricing benchmark for FTE model | Faculty-review focus, not discovery/AI; single-institution |
| **Academic Analytics** | **Provost/deans** — benchmarking & strategy | SaaS data product | Enterprise custom | Comparative faculty/research benchmarking; "visualize scholarship, enhance collaboration" ([academicanalytics.com](https://www.academicanalytics.com/)) | Top-down admin tool; not a researcher-facing PLG product; no AI Q&A; no confidentiality model |
| **Dimensions (Digital Science)** | Librarians, researchers, admins, **funders** | Cloud DB + API | Free web tier; paid Analytics; API licensed ([digital-science.com](https://www.digital-science.com/products/dimensions/), [dimensions.ai](https://www.dimensions.ai/products/all-products/dimensions-analytics/)) | Linked grants↔pubs↔patents↔clinical-trials graph; built with 100+ funders/universities | Public-data graph; not a collaboration platform; no confidential tier |
| **VIVO** (open source) | Library/IT (technical buyers) | **Self-hosted, open-source**, semantic-web/RDF | Free software (staffing cost) | Open ontology; semantic profiles; *the* precedent for cross-institution federation | See Segment 5 — federation only over **public LOD**, "not well supported in current interfaces" ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4376239/)) |

**Buyer reality:** RIMS purchases are split across **research office, library, faculty affairs, and IT** — exactly the four buyers your GTM must serve. Note the buyer *fragmentation* differs by product (Esploro=library, Interfolio=provost, Academic Analytics=deans). This fragmentation is both the friction and the opening: no incumbent sells one product to all four.

---

## Segment 2 — Researcher discovery networks

| Product | Model | Signal |
|---|---|---|
| **ResearchGate** | Ad/recruitment + publisher deals (e.g., MDPI); **no open API** ([C&EN](https://cen.acs.org/policy/publishing/academic-social-networking-site-ResearchGate/102/i2), [IntuitionLabs](https://intuitionlabs.ai/articles/research-paper-apis-scientific-literature)). Visited regularly by ~48% of S&E researchers ([THE](https://www.timeshighereducation.com/features/do-academic-social-networks-share-academics-interests)) | Consumer-grade reach, zero institutional confidentiality, closed data |
| **Academia.edu** | **Freemium "Premium" subscription**; explored paid OA (~$50/paper proposal); ~5× fewer regular visitors than ResearchGate ([THE](https://www.timeshighereducation.com/features/do-academic-social-networks-share-academics-interests)) | Individual-researcher PLG model proven, but content-monetization criticized |
| **ORCID** | Non-profit; **open REST API** (read public, write authenticated); 20M+ researchers (2025) ([ORCID](https://info.orcid.org/orcid-celebrates-oaweek-2025-with-continued-support-of-open-research-information-exploration/), [IntuitionLabs](https://intuitionlabs.ai/articles/research-paper-apis-scientific-literature)) | **Use as identity/disambiguation primitive — don't rebuild it** |
| **Google Scholar** | Free, no API, ToS-restricted scraping | Ubiquitous but un-integrable; not a build target |
| **OpenAlex** | **Fully open, free API**; 240M+ works, ~2.5B citation links; aggregates MAG/Crossref/ORCID/Unpaywall ([OpenAlex](https://openalex.org/), [IntuitionLabs](https://intuitionlabs.ai/articles/research-paper-apis-scientific-literature)) | **This is your public-data substrate.** Free, legal, comprehensive — the foundation layer for the "public" data tier and the cross-institution discovery graph |

**Takeaway:** The *public* researcher/paper graph is a solved, commoditized, and in OpenAlex's case **free** layer. Do not differentiate here. Differentiate on the **private/confidential** graph that OpenAlex can never see.

---

## Segment 3 — AI research assistants (the fastest-moving, best-funded threat)

| Product | Pricing | Strength | Structural limit |
|---|---|---|---|
| **Elicit** | ~$12/mo ([paperguide](https://paperguide.ai/blog/elicit-vs-consensus/), [researcher.life](https://researcher.life/blog/article/best-ai-research-assistants/)) | Only tool with true **systematic-review screening pipeline**; semantic search over 138M Semantic Scholar papers | Public lit only; SaaS; no institutional/confidential data |
| **Consensus** | ~$11.99/mo | "Consensus meter" over peer-reviewed claims | Same |
| **Scite** | ~$20/mo; acquired by Research Solutions 2023 | **Citation intelligence** — 1.2B citation statements classified supporting/contrasting/mentioning | Same |
| **SciSpace** | $20–$160/mo tiered | Breadth: 280M+ papers, multi-source, AI Writer, agents, Deep Review | Same |
| **Undermind** | Subscription | **Most thorough** deep multi-agent iterative search (librarian favorite for niche topics) | Same |
| **Semantic Scholar / Scholar-QA** (Allen AI) | Free / open | Open AI-native QA over scientific corpus | Public only; not institutional |
| **ResearchRabbit** | **Freemium as of Nov 2025; acquired by Litmaps** ([aarontay](https://aarontay.substack.com/p/researchrabbits-2025-revamp-iterative)) | Visual citation-chaining | Consolidating; public only |
| **Connected Papers** | Freemium | Visual paper-relationship graphs | Public only |
| **Perplexity** | $20/mo consumer | General grounded answers | Not research-domain; not institutional |

**Critical pattern:** Every AI research assistant is (a) **single-tenant consumer/prosumer SaaS**, (b) grounded **only on public literature**, (c) priced **$12–$20/seat PLG**, and (d) sends queries to cloud frontier models. **None can touch institution-private or lab-confidential documents** because none has a data-residency/confidential-tier architecture. PapersFlow's own marketing flags this as the unmet need: "SSO, FERPA, and compliance — what universities need from research SaaS" ([papersflow](https://papersflow.ai/blog/sso-compliance-academic-saas)). This is your sharpest AI-layer differentiator: **grounded Q&A over confidential internal docs with a model router that keeps confidential data on local/self-hosted models.**

---

## Segment 4 — Grant/funding intelligence + research admin

| Product | Who buys | Pricing | Notes |
|---|---|---|---|
| **Pivot-RP** (Clarivate/ProQuest) | Research dev professionals, admins, faculty | Institutional subscription | Curated global funding DB; integrates to Cayuse; deep RD market penetration ([Clarivate](https://clarivate.com/academia-government/scientific-and-academic-research/research-funding-analytics/pivot-rp-funding/)) |
| **GrantForward** | Higher-ed institutions | Institutional | Funding search engine; **exclusive integration partner of Kuali Research** ([Kuali](https://www.kuali.co/products/research/resources/grantforward)) |
| **Instrumentl** | Nonprofits + consultants + universities | **Published tiers**: Discover ~$299/mo, Pre-Award ~$499/mo, Full Lifecycle, Enterprise ([Instrumentl pricing](https://www.instrumentl.com/pricing), [grantsights](https://grantsights.com/blog/instrumentl-review-2026)) | Strongest published SMB/PLG pricing benchmark in funding |
| **Cayuse** | Research office (sponsored programs) | Enterprise custom | **"Tops grants-management ranking among higher-ed year after year"**; full cloud eRA lifecycle suite ([Cayuse](https://www.cayuse.com/higher-education/)) |
| **Kuali Research** | Research universities | Enterprise custom | Modular cloud eRA; compliance modules in one DB ([Kuali](https://www.kuali.co/products/research)) — *modularity is explicitly their pitch, mirror this* |
| **Atom Grants** ⚠️ | **Research development offices** | **~$179/mo entry** ([Atom](https://atomgrants.com/)) | **CLOSEST ADJACENT THREAT.** AI matches researchers↔grants, builds live researcher profiles from public outputs, **"AI-matched researcher database for finding the right co-PIs across institutions,"** RFP→section-by-section drafting. Trusted by NYU Langone, Memphis, Auburn, 50+ institutions; Memphis saw 1,000% engagement jump ([ALPSP](https://blog.alpsp.org/2025/08/spotlight-on-atom-grants.html)) |
| **GrantsAI / GROW** | RD offices | Varies; GROW open-sourcing on AWS Samples early 2026 ([AWS](https://aws.amazon.com/blogs/publicsector/aws-and-unc-researcher-build-a-prototype-agentic-ai-tool-to-streamline-grant-funding/)) | "Identifies what's missing in a proposed team, recommends collaborators who complete the picture" — **directly your Pillar 4** |

**Watch Atom Grants and GrantsAI closely.** They are already shipping AI-native *cross-institution co-PI matching* (your Pillar 4 + Pillar 1) and earning revenue with PLG-ish pricing (~$179/mo) into research-development offices. **They are single-tenant and public-data-only** — no confidential workspaces, no federation, no private-data tier. That is the gap you exploit, but they validate the wedge and the buyer.

---

## Segment 5 — Secure cross-institution collaboration / clean rooms / consortium sharing

This is where **confidentiality + federation** lives today — but **entirely outside the research-discovery domain.**

| Product/standard | What it does | Why it matters |
|---|---|---|
| **Globus + InCommon/CILogon** | Secure cross-institution data transfer/sharing via **federated identity**; ~1,900 IdPs, ~95% via InCommon ([Globus](https://www.globus.org/news/incommon-20-year-milestone), [Wisconsin CALS](https://admin.cals.wisc.edu/2022/02/18/globas-platform-available-for-research-data-sharing-and-big-data-transfers/)) | **This is the academic federation primitive — adopt it. Use InCommon/CILogon for cross-institution auth; do NOT roll your own identity federation.** |
| **VIVO CTSAsearch / Direct2Experts** | Federated multi-institution expertise search over **VIVO-compliant Linked Open Data**; 64 institutions, 150–300K researchers, 10M pubs across 3 continents ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4376239/)) | **Proof cross-institution discovery is wanted and feasible — but only for PUBLIC data, and "not well supported in current interfaces."** No confidentiality tiers, no AI, stagnant tooling |
| **Decentriq** | SaaS **data clean rooms** on confidential computing; collaborate without sharing raw data; GDPR-aligned ([Decentriq](https://www.decentriq.com/article/what-is-a-data-clean-room)) | Confidentiality-first federation exists — but **commercial/healthcare, zero research-discovery features** |
| **BeeKeeperAI** | Privacy-preserving analytics on multi-institutional protected health data in confidential-compute enclaves ([Decentriq](https://www.decentriq.com/article/what-is-a-data-clean-room)) | Same: confidential multi-party compute, but narrow vertical |
| **Snowflake / Databricks / Salesforce / Azure clean rooms** | Federated querying without data movement; TEEs ([Databricks](https://www.databricks.com/blog/top-10-questions-you-asked-about-databricks-clean-rooms-answered), [Azure](https://learn.microsoft.com/en-us/azure/confidential-computing/multi-party-data)) | Infrastructure primitives you could build on; not products universities buy for research discovery |
| **Duality** | FHE + federated learning + TEEs; privacy-preserving RAG in TEEs ([Duality](https://dualitytech.com/blog/llm-data-privacy/)) | Confirms confidential RAG is technically real; enterprise/regulated, not academic |

**This is the single most important finding.** The *exact* combination your platform locks in — **federated cross-institution + first-class confidentiality tiers + explicit revocable sharing grants** — exists in commercial data clean rooms and in academic public-LOD federation, **but never together, and never with research-discovery + AI on top.** The "confidential RAG with local-model routing" pattern your AI layer specifies is documented as real and emerging (Secure Multifaceted-RAG: local open-source generator, external LLM only when a prompt passes security filtering — [arXiv 2504.13425](https://arxiv.org/pdf/2504.13425)), which de-risks your model-router design.

---

## Segment 6 — Enterprise expertise-location tools

| Product | Pricing | Lesson |
|---|---|---|
| **Starmind** | **Knowledge Engine (API) base $4,000/mo for ≤500 profiles; Expert Finder $0.60/active-user/mo; Knowledge Suite $1.80/active-user/mo; Combo $2.20** (Sept 2025 restructure) ([Starmind pricing](https://www.starmind.com/blog/introducing-starminds-new-pricing-structure), [Software Finder](https://softwarefinder.com/artificial-intelligence/starmind)) | **Best-in-class packaging model to copy:** a base "profile/mapping" platform fee + per-active-user feature modules + headless API tier. ISO 27001, GDPR, audit logging — table-stakes security ([research.com](https://research.com/software/reviews/starmind)) |

Starmind maps expertise from real work activity (conversations, collaboration, contributions) rather than static org charts, surfaced inside Teams/Slack. **Translate this directly:** your cross-institution expert discovery should infer expertise from actual outputs and (in private tiers) internal activity, not just self-reported profiles — and the **base-platform-fee + per-active-user-module + API-tier** structure is the cleanest mapping to your "configurable editions, one product" GTM requirement.

---

## WHITE SPACE — what nobody does well

Cross-referencing all six segments, the unoccupied intersection is precise:

1. **Federated cross-institution discovery over CONFIDENTIAL data.** VIVO/CTSAsearch federates public LOD; clean rooms federate confidential commercial data. **No one federates institution-private/lab-confidential research data across universities with explicit, revocable sharing grants.** This is your core moat.
2. **AI-native grounded Q&A that respects a data-classification boundary.** Every AI assistant (Elicit, SciSpace, Undermind, Scholar-QA) is public-lit-only single-tenant SaaS. **None routes by data classification to keep confidential data on local/self-hosted models.** Your model router *is* the differentiator, and the technique is now published-and-real, not speculative.
3. **All-four-pillars in one modular platform.** Discovery (RIMS/VIVO/Starmind), literature intelligence (Elicit et al.), secure workspaces (clean rooms/Globus), and funding+team-assembly (Atom/Pivot) **each exist separately.** No vendor unifies them — and the closest unifier, Atom Grants, covers only pillars 1+4 and only on public data.
4. **One product sellable to all four buyers via packaging.** Incumbents fracture by buyer (Esploro→library, Interfolio→provost, Cayuse→research office, Elicit→individual). **Configurable editions + deployment tiers that serve research-office/library/IT (top-down), individual researchers (PLG), consortia, and campus-wide from one codebase is unoccupied.**
5. **Confidentiality + compliance designed-in (FERPA/GDPR/ITAR-EAR).** Commercial clean rooms have the confidential-compute substrate but no academic compliance/export-control awareness; academic tools have FERPA awareness but no confidential federation. **Export-control-aware (ITAR/EAR) cross-institution sharing is genuinely novel** and a hard requirement for defense/engineering research — a wedge into well-funded labs.

---

## Most defensible wedge for a new entrant

**Do NOT lead with the full four-pillar platform or with public-literature AI search** — Elicit/SciSpace/Undermind/OpenAlex have commoditized that and you cannot out-fund them, and a horizontal "all-in-one" triggers the longest, most committee-bound procurement.

**Lead with the wedge that is (a) revenue-bearing fast, (b) PLG-able into a single department, and (c) sits on your locked architecture without rework:**

> **AI-native research/literature intelligence over the institution's OWN private+confidential corpus (internal docs, lab notes, unpublished work, profiles), with the model router keeping confidential data on self-hosted models — sold first to a single research-active department or lab, bottom-up.**

Why this wedge:
- **Unmet & defensible:** the one thing no AI assistant can do (confidential-tier grounding) and the one thing RIMS won't do (AI-native).
- **Architecture-constant:** it exercises the data-classification engine, the model router, and the private-node tenancy from day one — federation/exchange layer comes online in phase 2 with zero re-architecture.
- **Procurement-light:** a single lab/department buy on private data with local models is the *easiest* security review to pass (data never leaves the boundary → HECVAT/SOC2 friction collapses).
- **Natural expansion path:** private-corpus intelligence → institution-wide expert discovery → *then* flip on the cross-institution exchange layer (the federated moat) once 2+ institutions are live → *then* funding/team-assembly to monetize the consortium.

The **second wedge to keep warm: cross-institution co-PI/team assembly for grants** (Atom Grants' beachhead, proven to earn revenue at ~$179/mo into RD offices) — but enter it *with* confidentiality/federation that Atom lacks, once you have ≥2 nodes live.

---

## Pricing / packaging norms

| Model | Used by | Implication for you |
|---|---|---|
| **FTE-based site license** | Interfolio (~$28K/yr observed, +~$800/yr escalator), most RIMS | The institutional/top-down norm; "FTE" is the unit deans/research offices expect |
| **Enterprise custom (contact sales)** | Pure, Esploro, Symplectic, Converis, Cayuse, Kuali, Academic Analytics, Dimensions Analytics | Signals long sales cycles, committee buys; expect 6–18 month cycles |
| **Per-active-user module + base platform fee + API tier** | **Starmind** ($4K/mo base ≤500 profiles + $0.60–$2.20/active-user) | **Best fit for your "one product, configurable editions" mandate** — base node fee + per-pillar per-active-user modules + BYO-API/headless tier |
| **Freemium / prosumer per-seat $12–$20/mo** | Elicit, Consensus, Scite, SciSpace, Perplexity | The PLG bottom-up norm; this is your individual-researcher entry price band |
| **Published SMB tiers $179–$499/mo** | Instrumentl, Atom Grants | The lab/department PLG band — your wedge entry price |

**Recommended packaging:** per-institution **node/platform base fee** (data plane + isolation) + **per-active-user pillar modules** (discovery, lit-intelligence, workspaces, funding) + **consortium/exchange-layer add-on** (priced per connected institution) + **BYO-provider/key tier**. This single SKU structure serves PLG (one module, few seats), department, campus-wide (all modules, FTE-capped), and consortia (exchange add-on) — satisfying the locked GTM without four products. Mirror Starmind's "pay for profiles mapped + active users" base.

---

## Realistic GTM friction selling to universities

1. **HECVAT is mandatory and brutal.** Security review via HECVAT is required for *any* cloud/SaaS touching private data, **before** purchase/renewal/pilot/signing; the full toolkit is **321 questions** spanning security, privacy, accessibility, AI governance, operations ([SaltyCloud](https://www.saltycloud.com/blog/what-is-the-hecvat/), [Montclair State](https://www.montclair.edu/information-technology/security/hecvat/)). Without **SOC 2 Type II**, you face extended review: architecture docs, pen-test results, possibly on-site audit ([papersflow](https://papersflow.ai/blog/sso-compliance-academic-saas)). **Get SOC 2 Type II early; pre-fill HECVAT; lead with "confidential data never leaves your node."** Your federated-hybrid architecture is the single strongest HECVAT answer you can give — turn it into the sales weapon.
2. **Buyer fragmentation = multi-stakeholder sale.** Research office, library, faculty affairs, IT/security, and data-governance committee each have veto power; they map to different incumbents (Cayuse/Esploro/Interfolio/Academic Analytics). **The PLG private-corpus wedge bypasses most of them** by starting below the committee threshold.
3. **Data-governance & compliance committees** add months; FERPA + GDPR + (for engineering/defense) **ITAR/EAR export controls** must be answerable on day one. Most competitors have *none* of this — making it both friction *and* differentiator.
4. **Identity federation is solved — use it.** Adopt **InCommon/CILogon/Globus** for cross-institution auth (95% of academic IdPs already federate via InCommon). Rolling your own is a procurement and trust liability.
5. **Incumbent integration, not replacement, early.** Pure/Esploro/Cayuse/ORCID/OpenAlex are entrenched. Ship **connectors** (ingest from Pure/Esploro/ORCID, push to Cayuse) so you're an *additive* AI/federation layer in the first sale, not a rip-and-replace fight you'll lose to procurement inertia.

---

## Build implications

1. **Build the data-classification engine + model router as the kernel first.** Every differentiator (confidential RAG, federation grants, compliance) hangs off classification. The confidential-RAG-with-local-model-routing pattern is published and real ([arXiv 2504.13425](https://arxiv.org/pdf/2504.13425)) — implement security-filtered routing: local/self-hosted (vLLM prod, Ollama M4 Max dev) for confidential, frontier cloud for public.
2. **Phase-1 MVP = AInative literature/internal-doc intelligence over a single lab's private+confidential corpus, local-model-only.** Smallest procurement surface, exercises kernel, earns revenue. Price in the $179–$499/mo department band (Instrumentl/Atom benchmark).
3. **Foundation public-data layer = OpenAlex (free) + ORCID (identity).** Do not rebuild the public graph; spend zero differentiation budget here. Reserve hybrid retrieval (your existing vector+BM25+RRF+KG) for the *private/confidential* corpus where it's defensible.
4. **Federation/exchange layer = phase 2, on InCommon/CILogon.** Light up cross-institution discovery + revocable sharing grants only once ≥2 nodes exist. Federate *confidential* data with grants — the white space VIVO/CTSAsearch never reached. Do not build identity federation; ride InCommon.
5. **Packaging = Starmind model:** per-node base fee + per-active-user pillar modules + consortium/exchange add-on + BYO-provider tier. One SKU, four GTM motions. Make each pillar a true pluggable module (your non-functional mandate) so editions are config, not forks.
6. **Compliance is a feature, ship it as one.** SOC 2 Type II + pre-filled HECVAT + FERPA/GDPR + **ITAR/EAR export-control-aware sharing** (genuinely novel) — this both clears procurement and becomes the differentiator no AI-assistant competitor can match. Target export-controlled engineering/defense labs as a high-value, low-competition beachhead.
7. **Integrate, don't displace, the incumbents.** Connectors to Pure/Esploro/ORCID/OpenAlex (ingest) and Cayuse/Kuali (push) make you additive in the first sale and defuse rip-and-replace resistance.
8. **Watch Atom Grants / GrantsAI as the fast-follow threat on pillars 1+4.** They've validated AI-native cross-institution co-PI matching and the RD-office buyer at PLG pricing — but are single-tenant, public-data-only. Enter funding/team-assembly *with* the confidentiality + federation they structurally lack.