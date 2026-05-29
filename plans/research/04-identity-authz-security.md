# Research: identity-authz-security

I now have comprehensive, verified material across all six domains. Synthesizing the final report.

---

# Identity, Auth & Access Control Architecture for a Federated Multi-University Research SaaS

Security architecture brief. Scope: academic federated identity, authorization, policy engines, key management, audit/compliance, and a cross-institution threat model — mapped onto the locked deployment (federated hybrid: per-university private node + thin shared exchange/control plane) and the locked data tiers (public / private / confidential with revocable cross-institution grants).

Bottom line up front:
- **Identity:** Be a SAML2 + OIDC **Service Provider** in eduGAIN/InCommon, but do not integrate raw federation metadata yourself — broker through **Keycloak** (self-host, fits the federated-node model and BYO-key story) or **CILogon** (managed, research-native, handles 5000+ IdPs + ORCID/social). Layer **SCIM** for deprovisioning and adopt **REFEDS R&S + Sirtfi + CoCo v2** entity categories so IdPs release attributes without per-institution paperwork.
- **Authorization:** **ReBAC (Zanzibar-style: SpiceDB or OpenFGA)** is the correct core for "confidential / per-project / per-lab / cross-institution sharing grant + tenant isolation." Layer a thin **ABAC/policy-engine (Cedar or OPA)** for classification gates, export-control residency, and AI-routing decisions. Pure RBAC will not survive contact with this requirements set.
- **Confidential tier:** **per-tenant envelope encryption + BYOK mandatory, HYOK offered**, plus a hard data-plane boundary that confidential data and confidential-routed AI inference never cross. This is the same boundary export controls (ITAR/EAR) care about.
- **Selling bar:** SOC 2 Type II (or in-progress), tamper-evident cross-institution audit trail, MFA/SSO/SCIM, signed DPA, FERPA "school official" posture, and demonstrable tenant isolation. Without these a university security review stalls.

---

## 1. Academic Federated Identity

### 1.1 The landscape and why it's different from generic B2B SSO

Universities already run an **IdP** (overwhelmingly **Shibboleth**, implementing SAML 2.0) plugged into **InCommon** (500+ US institutions) which interfederates globally via **eduGAIN** (3,000+ orgs, 60+ countries). You don't onboard each university one-off the way generic B2B SaaS does — you join the federation once as a **Service Provider (SP)** and become reachable to every member IdP. ([UW IT Connect](https://it.uw.edu//security/iam/federation/), [AARC Federations 101](https://aarc-project.eu/training/federations-101/))

Protocol reality:
- **SAML2** is the lingua franca of eduGAIN today; **Shibboleth** is the dominant IdP/SP software. ([LoginRadius Shibboleth](https://www.loginradius.com/protocol/shibboleth))
- **OIDC** is rising but not yet first-class in eduGAIN; Shibboleth added an OIDC OP plugin (handed to the Shibboleth Consortium in 2019). Plan SAML2 for federation login, OIDC for your own mobile/API surface. ([GÉANT CONNECT](https://connect.geant.org/2019/12/18/propelling-openid-connect-forward), [Duende: SAML + OIDC coexistence](https://duendesoftware.com/blog/20260528-saml-and-openid-connect))

### 1.2 Attributes you actually consume (the `eduPerson` schema)

You authorize on **scoped, federation-standard attributes**, not on emails:
- `eduPersonPrincipalName` (eppn) — scoped user id, e.g. `jsmith@example.edu`.
- `eduPersonScopedAffiliation` — e.g. `faculty@example.edu;member@example.edu`. **This is your primary tenant + role signal.**
- `subject_id` / `eduPersonUniqueId` — stable non-reassigned id (eppn can be recycled; don't key confidential ACLs on it alone).
- `eduPersonOrcid` — persistent researcher id that survives institution changes. ([eduPerson 2020-01, REFEDS](https://wiki.refeds.org/display/STAN/eduPerson+2020-01), [Internet2 eduPerson spec](https://software.internet2.edu/eduperson/internet2-mace-dir-eduperson-201602.html))

**ORCID** is the cross-institution identity anchor: it persists across affiliation changes, which is exactly what your collaborator-discovery and grant-team-assembly features need. Don't make ORCID the *authentication* root of trust (it's self-asserted), but use it as a stable *correlation* key linking a person's profiles across tenants. ([ORCID via CILogon](https://www.cilogon.org/oidc))

### 1.3 How you onboard a university (the SP-side flow)

1. **Deploy/operate a SAML SP** (or broker — see 1.4) and publish SP metadata.
2. **Declare required attributes** — minimal set: a stable id, scoped affiliation, display name, email. IdPs decide what they release; you don't get to demand. ([UW IT Connect](https://it.uw.edu//security/iam/federation/))
3. **Register metadata with the federation** (InCommon/eduGAIN); validation + publication takes hours to days, after which every member IdP can reach you. ([uni-foundation eduGAIN guidelines](https://uni-foundation.eu/uploads/2020_MyAID_Guidelines_eduGAIN.pdf))
4. **Adopt entity categories to unlock attribute release without per-institution negotiation:**
   - **REFEDS Research & Scholarship (R&S)** — IdPs release the minimal R&S attribute bundle to R&S SPs automatically (or with user consent), no admin involvement. This is the single biggest onboarding-friction reducer for a research SP. ([REFEDS R&S](https://refeds.org/category/research-and-scholarship), [R&S FAQ](https://wiki.refeds.org/display/ENT/Research+and+Scholarship+FAQ))
   - **Sirtfi** — Security Incident Response Trust Framework; many IdPs require it before releasing attributes. Self-assert it, and mean it. ([Sirtfi](https://refeds.org/sirtfi))
   - **GÉANT/REFEDS Data Protection Code of Conduct (CoCo v2)** — your GDPR posture toward EU IdPs. ([CoCo v2](https://refeds.org/category/code-of-conduct/v2), [REFEDS DP CoCo](https://refeds.org/a/2805))

> Onboarding insight: R&S + Sirtfi + CoCo turns "negotiate attribute release with 200 universities" into "publish three entity-category tags." Budget for this early; it is a GTM accelerant, not just compliance.

### 1.4 Multi-IdP brokering — the build/buy decision

You will face hundreds of IdPs, mixed SAML/OIDC, plus researchers with no institutional IdP (industry collaborators, emeritus, citizen scientists). Don't hand-roll this. Options:

| Broker | Fit for this platform | Notes |
|---|---|---|
| **Keycloak** (self-host) | **Strong** | Free OSS; native **IdP brokering** for SAML2 + OIDC, account linking, per-realm isolation. A **realm-per-tenant** maps cleanly onto the per-university node. Self-host aligns with the confidential boundary + no-vendor-lock-in story. Operational cost is yours. ([PhaseTwo Keycloak IdP broker](https://phasetwo.io/docs/keycloak/idp/), [Keycloak](https://www.keycloak.org/)) |
| **CILogon** (managed, research-native) | **Strong / complementary** | Purpose-built for science: brokers **5000+ InCommon/eduGAIN IdPs** plus **ORCID, GitHub, Google, Microsoft** social login for unaffiliated researchers; exposes `eppn`, scoped `affiliation`, ORCID via OIDC/SAML/LDAP. Offloads federation membership pain. ([CILogon OIDC](https://www.cilogon.org/oidc), [CILogon paper](https://www.researchgate.net/publication/337427194_CILogon_Enabling_Federated_Identity_and_Access_Management_for_Scientific_Collaborations)) |
| **WorkOS / Auth0** | Moderate | Excellent enterprise SSO/SCIM DX, but cloud-only and not eduGAIN-native; weaker fit for the per-tenant-node + self-host-confidential constraint. WorkOS needs a separate primary auth system. ([Auth0 vs Keycloak, Frontegg](https://frontegg.com/guides/auth0-vs-keycloak)) |
| **Ory** | Moderate | Modular, cloud-native, K8s-friendly — composable services rather than a monolith; good if you want fine-grained control, more assembly required. ([Keycloak alternatives, Oso](https://www.osohq.com/learn/best-keycloak-alternatives-2025)) |

**Recommendation:** **CILogon as the federation front-door** (it already solved eduGAIN + ORCID + social at research scale) feeding **Keycloak as your per-tenant brokering/session layer and token issuer**. This is a pragmatic, fundable combination: you don't reimplement federation, you keep self-host control where the confidential boundary demands it.

### 1.5 Provisioning lifecycle — JIT + SCIM (both, not either)

- **JIT provisioning**: create the user record on first federated login from assertion attributes — cheap, good UX for PLG/bottom-up adoption.
- **SCIM (RFC 7644)**: the IdP *pushes* lifecycle changes, critically **deprovisioning**. JIT cannot revoke; SCIM can. For top-down institutional sales, **SCIM deprovisioning is table stakes** — a researcher who leaves must lose access to confidential workspaces automatically. ([SCIM provisioning guide, Descope](https://www.descope.com/blog/post/scim-providers-b2b-saas), [Scalekit SCIM](https://www.scalekit.com/blog/the-scim-imperative-transforming-b2b-user-identity-management))

> Design rule: every confidential-tier grant must be tied to an active affiliation. When SCIM signals deprovision (or affiliation drops in a re-assertion), cascade revocation through the authz store (Section 2). This closes the "departed researcher retains confidential access" gap that security reviews probe hard.

---

## 2. Authorization Model

### 2.1 Why not RBAC, why not pure ABAC

- **RBAC** is fine while roles are stable and context-free; it collapses under resource sharing, hierarchies, and per-object grants. Your requirements (per-project, per-lab, revocable cross-institution shares) are exactly where RBAC "becomes difficult to reason about." ([Oso RBAC vs ABAC vs ReBAC](https://www.osohq.com/learn/rbac-vs-abac-vs-rebac-what-is-the-best-access-policy-paradigm), [Permit.io](https://www.permit.io/blog/rbac-vs-abac-and-rebac-choosing-the-right-authorization-model))
- **ABAC** is maximally flexible but the hardest to maintain and audit, and answering "who can see this dataset?" (reverse lookup) is awkward.
- **ReBAC** (Google Zanzibar lineage) models ownership/membership/hierarchy/sharing **concisely and auditably** — and answers both "can user X read resource Y?" and "who can read Y?" / "what can X read?" natively. ([Pangea](https://pangea.cloud/blog/rbac-vs-rebac-vs-abac/), [Aserto](https://www.aserto.com/blog/rbac-abac-and-rebac-differences-and-scenarios))

**Consensus pattern:** start RBAC, add ABAC as roles multiply, pull in ReBAC for resource sharing/hierarchies — most real systems blend all three. ([Permit.io](https://www.permit.io/blog/rbac-vs-abac-and-rebac-choosing-the-right-authorization-model)) For this platform the blend is: **ReBAC core (relationships, sharing, isolation) + ABAC overlay (classification, residency, export-control, AI-routing) + RBAC sugar (roles expressed as relations).**

### 2.2 Engine choice: SpiceDB vs OpenFGA

Both implement Zanzibar; both support a schema of **definitions / relations / permissions** and the **Check / Expand / Watch / LookupResources** API surface. ([SpiceDB GitHub](https://github.com/authzed/spicedb), [WorkOS Zanzibar implementations](https://workos.com/blog/top-5-google-zanzibar-open-source-implementations-in-2024))

- **SpiceDB** — most Zanzibar-faithful. **ZedTokens** give per-request consistency and solve the **New Enemy Problem** (a revoked user still reading a resource due to cache staleness). **Caveats** add ABAC-style conditions inline. For a *confidentiality-first, revocation-is-correctness* product, the strong-consistency guarantee is the deciding factor — a stale "still allowed" after a revoked cross-institution share is a security incident, not a UX glitch. ([SpiceDB GitHub](https://github.com/authzed/spicedb), [SpiceDB vs Auth0 FGA, sph.sh](https://sph.sh/en/posts/spicedb-vs-auth0-fga/))
- **OpenFGA** — CNCF, Auth0/Okta origin, sub-10ms checks, great DX and community; defaults to relaxed consistency with opt-in `HIGHER_CONSISTENCY`. Excellent and cheaper to start; you must consciously opt into stronger consistency on confidential checks. ([OpenFGA vs SpiceDB, PkgPulse](https://www.pkgpulse.com/guides/openfga-vs-permify-vs-spicedb-zanzibar-authorization-2026))

**Recommendation:** **SpiceDB** for the confidential/cross-institution core because revocation correctness (ZedToken consistency) is a first-class product requirement here. OpenFGA is a defensible lower-friction alternative if you commit to `HIGHER_CONSISTENCY` on confidential-tier checks.

### 2.3 Proposed authorization data model

Two layers: **(A)** ReBAC relationship schema (the graph), **(B)** the ABAC attributes evaluated alongside it.

#### (A) ReBAC schema (SpiceDB-style pseudocode)

```
// ---- Tenancy ----
definition platform {}                       // root, for global/system roles only

definition tenant {                           // = a university
  relation platform: platform
  relation admin: user                        // institutional IT/research-office admin
  relation member: user                       // anyone with active affiliation here
  permission administer = admin + platform->...
}

definition org_unit {                         // department or lab (nestable)
  relation tenant: tenant
  relation parent: org_unit                   // hierarchy: lab -> dept
  relation lead: user                         // PI / chair
  relation member: user
  permission manage = lead + parent->manage + tenant->administer
  permission belong = member + lead + parent->belong
}

definition user {
  relation self: user
  // identity attrs (eppn, subject_id, orcid, scoped_affiliation, home_tenant)
  // live as ABAC context, not relations (see layer B)
}

// ---- Resources (all carry a classification attribute, layer B) ----
definition profile  { relation tenant: tenant; relation owner: user;  ... }
definition paper    { relation tenant: tenant; relation owner: user;  relation org_unit: org_unit; ... }
definition dataset  { relation tenant: tenant; relation org_unit: org_unit;
                      relation owner: user; relation steward: user; ... }

definition workspace {                         // cross-institution confidential collab
  relation tenant: tenant                       // owning/home tenant
  relation owner: user
  relation collaborator: user                   // may be from ANOTHER tenant via a grant
  relation viewer: user
  relation parent_grant: sharing_grant          // the grant that admitted external members
  permission edit  = owner + collaborator + tenant->administer
  permission view  = viewer + edit + parent_grant->is_active   // revocation cascades
}

// ---- The cross-institution sharing primitive (first-class, revocable) ----
definition sharing_grant {
  relation grantor_tenant: tenant               // who shares
  relation grantee_tenant: tenant               // who receives
  relation grantor: user                        // person who authorized (accountability)
  relation grantee_subject: user                // specific external user, or...
  relation grantee_group: org_unit              // ...an external lab
  relation resource_ref: workspace | dataset | paper | profile
  relation revoked_marker: platform             // present => revoked (kills permission)
  // scope/expiry/classification-ceiling live as caveat/ABAC context
  permission is_active = grantor - revoked_marker->...   // active unless revoked
  permission can_access = grantee_subject + grantee_group->belong
}
```

Key properties this buys you:
- **Tenant isolation** is structural: every resource has a `tenant` relation; cross-tenant access is *only* reachable through a `sharing_grant`. No grant ⇒ no path ⇒ deny. This is the "if tokens cross tenants, authorization never gets a chance" principle, enforced in the graph. ([Tenant isolation, Security Boulevard](https://securityboulevard.com/2025/12/tenant-isolation-in-multi-tenant-systems-architecture-identity-and-security/))
- **Revocation is O(1) and consistent**: set `revoked_marker` → `is_active` flips → `workspace.view` denies on the next ZedToken-consistent check. No orphaned access.
- **Accountability**: every grant records `grantor` (a person) and both tenants — feeds the immutable cross-institution audit trail (Section 5).
- **Hierarchy & delegation**: `org_unit.parent` lets a dept admin reason over labs; PIs manage their lab's resources without platform admins.

#### (B) ABAC attributes evaluated alongside the graph (caveats / policy engine)

| Attribute | Source | Used to gate |
|---|---|---|
| `resource.classification` ∈ {public, private, confidential} | resource metadata | the core tier gate |
| `user.home_tenant`, `user.scoped_affiliation` | federation assertion | cross-tenant + role checks |
| `grant.classification_ceiling` | grant | a grant can share *private* but never auto-promote *confidential* |
| `grant.expiry`, `grant.scope` | grant | time-boxed shares |
| `resource.export_control` ∈ {none, EAR, ITAR} | data steward | residency + nationality gate (Section 4) |
| `user.citizenship / country` (where lawfully collected) | institutional attribute | ITAR "deemed export" gate |
| `request.purpose`, `ai.route` | request context | AI router classification decision |

> Modeling rule: **relationships answer "is there a path?"; attributes answer "is this path *currently permitted* given classification/residency/expiry?"** Both must pass. Confidential is deny-by-default: absence of an explicit relation *and* a satisfied caveat = deny.

---

## 3. Policy Engine & PDP Placement

### 3.1 Engine comparison

| | **OPA/Rego** | **Cedar** | **OpenFGA** |
|---|---|---|---|
| Paradigm | General-purpose Datalog-ish policy | Purpose-built ABAC/RBAC, stateless | ReBAC graph traversal |
| Best at | Heterogeneous policy (K8s, CI/CD, app, compliance) | Readable, **deterministic**, validated access policies | Relationship/sharing/hierarchy at scale |
| Perf | ~26–44 ms typical RBAC; depends on data loading | Fast, stateless, predictable | <10 ms typical |
| Risk | Expressive but **error-prone**, non-determinism, ~30–40h learning curve | Less flexible for non-access logic | Not for complex conditional logic |

Sources: [Permit.io policy engine showdown](https://www.permit.io/blog/policy-engine-showdown-opa-vs-openfga-vs-cedar), [Teleport benchmark](https://goteleport.com/blog/benchmarking-policy-languages/), [sph.sh Cedar vs Rego vs OpenFGA](https://sph.sh/en/posts/policy-language-comparison-cedar-rego-openfga/).

These are **not mutually exclusive** — they answer different questions. ReBAC (OpenFGA/SpiceDB) answers *relationship* questions; Cedar/OPA answer *attribute/condition* questions. The mature pattern is to layer them (Topaz = OPA + Zanzibar-style data). ([Permit.io](https://www.permit.io/blog/policy-engine-showdown-opa-vs-openfga-vs-cedar))

### 3.2 Recommended composition

- **Relationship/isolation/sharing core → SpiceDB** (Section 2).
- **Classification + export-control + residency + AI-routing decisions → Cedar.** Cedar's **determinism and validation** matter because these are the highest-stakes, audit-scrutinized decisions; Rego's expressiveness is overkill and its non-determinism/runtime-exception risk is a liability for a confidentiality gate. ([Teleport benchmark](https://goteleport.com/blog/benchmarking-policy-languages/)) Use OPA/Rego only if you also need broad infra-policy (admission control, CI/CD) and want one engine — accept the learning curve.

### 3.3 PDP placement in the multi-tenant API

- **Pattern:** "**authorize locally, manage centrally**." Control plane (policies + schema) is centralized; the PDP runs as a **sidecar/local library** next to each service to keep evaluation latency sub-millisecond and survive control-plane blips. Centralized PDPs add network milliseconds; sidecars add only microseconds. ([Permit.io showdown](https://www.permit.io/blog/policy-engine-showdown-opa-vs-openfga-vs-cedar))
- **Hybrid for the federated topology:** SpiceDB relationship data is centralized in the **exchange/control layer** (cross-tenant grants must be globally consistent); Cedar PDP is **embedded per-tenant-node** so confidential-tier classification checks execute *inside the boundary* and never depend on the shared plane being reachable. Use **OPAL or SpiceDB Watch** to propagate policy/relationship updates to edges. ([CNCF policy languages](https://www.cncf.io/blog/2024/05/21/love-hate-and-policy-languages-an-introduction-to-decision-making-engines/))
- **Two-stage check on every request:** (1) tenant/path check (SpiceDB), (2) classification/residency caveat (Cedar). A request to confidential data from outside the boundary fails stage 2 even if a relationship path exists.

---

## 4. Secrets, Encryption & Key Management

### 4.1 Baseline (all tiers)

- TLS 1.2+/mTLS in transit for service-to-service across the exchange layer; AES-256 at rest.
- **Envelope encryption**: data encrypted with a per-record/per-tenant **DEK**; the DEK is wrapped by a **KEK** in a KMS/HSM, producing an EDEK. Disabling/revoking the KEK renders data undecryptable — instant cryptographic lockout / crypto-shred. ([IBM BYOK](https://www.ibm.com/think/topics/byok), [Thales cloud encryption](https://cpl.thalesgroup.com/blog/encryption/cloud-encryption-key-management-byok-hyok))
- Secrets (DB creds, broker client secrets, AI provider keys) in **Vault** or cloud KMS/Secrets Manager — never in env files or the federation config. Per-tenant BYO AI keys are tenant-scoped secrets.

### 4.2 What the confidential tier MUST mandate

| Control | Requirement | Rationale |
|---|---|---|
| **Per-tenant keys** | Distinct KEK per university; DEKs never shared across tenants | Crypto-enforced tenant isolation; one tenant's key compromise ≠ cross-tenant exposure. AWS KMS supports 100k keys/account/region — key-per-tenant is feasible. ([Awssome multi-tenant encryption](https://www.awssome.io/blog/multi-tenant-saas-security-encryption-faqs)) |
| **BYOK (mandatory for confidential)** | University creates/owns the KEK, grants the platform usage via its KMS | Revoke the KEK → platform can no longer decrypt that tenant's confidential DEKs. Hands the customer the kill switch — a recurring ask in research-IT reviews. ([IBM BYOK](https://www.ibm.com/think/topics/byok), [Replicon/AWS BYOK](https://www.awssome.io/blog/multi-tenant-saas-security-encryption-faqs)) |
| **HYOK (offered for highest-sensitivity)** | Keys never leave the university's environment; platform sees only ciphertext | True key sovereignty — survives legal order, provider insider misuse, provider error. Offer as a premium/edition for export-controlled or top-secret labs. ([Fortanix BYOK vs HYOK](https://www.fortanix.com/blog/differences-between-byok-and-hyok), [archTIS](https://www.archtis.com/byok-vs-hyok-whats-the-difference-and-which-is-right-for-you/)) |
| **AI boundary** | Confidential-routed inference (vLLM/Ollama) runs inside the tenant node; prompts/embeddings/outputs encrypted with the tenant key; no cloud egress | The model router's "local models for confidential" rule must be *cryptographically and network* enforced, not just configured. |
| **Key rotation + crypto-shred** | Scheduled KEK rotation; deletion = destroy key, not chase copies | Satisfies GDPR erasure for confidential data without hunting every replica. |

> Tie-in to export controls: HYOK + in-boundary inference + US-only data residency is the same control surface ITAR/EAR demand (Section 6.5). Build it once.

---

## 5. Audit & Compliance Logging

### 5.1 What to log (and how)

- **Immutable / tamper-evident cross-institution access trail.** Every cross-tenant access, grant creation, grant revocation, classification change, and confidential-data read/AI-inference event → append-only, hash-chained (or WORM-stored) log with: actor (eppn + ORCID + home_tenant), resource, classification, tenant pair, grant id, decision, policy/ZedToken version, timestamp. ([SOC 2 immutable evidence, soc2auditors](https://soc2auditors.org/insights/soc-2-compliance-checklist/), [Splunk SOC 2 checklist](https://www.splunk.com/en_us/blog/learn/soc-2-compliance-checklist.html))
- **Tenant-scoped audit export.** Each university can pull *its own* audit trail (incl. who at other institutions touched its shared resources). This is a sales feature and a FERPA/GDPR accountability requirement. ([FERPA safeguards: access controls + audit logs](https://www.reform.app/blog/ferpa-compliance-for-saas-tools-in-education))
- **Federation-grade auth logs.** SSO, MFA, SCIM provisioning/deprovisioning events — the "technical backbone for compliance across SOC 2 / ISO 27001 / HIPAA / GDPR." ([Security Boulevard: SSO compliance](https://securityboulevard.com/2026/04/11-sso-compliance-requirements-compared-soc-2-iso-27001-hipaa-pci-dss-and-gdpr/))

### 5.2 SOC 2 / ISO 27001 readiness

- **SOC 2 Type II is the de facto minimum for B2B SaaS handling customer data**; Type II readiness takes ~3–6 months. Universities will request your **SOC 2 Type II report or ISO 27001 certificate** during vendor review and reassess annually. ([Hyperproof SOC 2](https://hyperproof.io/soc2/), [SOC 2 checklist](https://soc2auditors.org/insights/soc-2-compliance-checklist/))
- ISO 27001 (ISMS certification) vs SOC 2 (attestation of controls) — for US R1s SOC 2 Type II usually opens the door; add ISO 27001 for international/EU institutions. ([Mimecast ISO 27001 vs SOC 2](https://www.mimecast.com/content/iso-27001-vs-soc-2/))
- Use a compliance-automation platform (Vanta/Drata/etc.) for continuous evidence + auditor portal + immutable evidence export from day one rather than retrofitting. ([Bright Defense SOC 2 software](https://www.brightdefense.com/resources/best-soc-2-compliance-software/))

---

## 6. Cross-Institution Threat Model & Mitigations

| Threat | Scenario | Mitigation |
|---|---|---|
| **Tenant data leakage** | Multi-tenant ≠ isolated; a shared table with a `tenant_id` column that a query forgets to filter. "You can be multi-tenant without being isolated." ([Security Boulevard](https://securityboulevard.com/2025/12/tenant-isolation-in-multi-tenant-systems-architecture-identity-and-security/)) | Structural isolation: per-tenant nodes for confidential data; every resource has a `tenant` relation; **deny-by-default** authz where no relationship path exists; per-tenant encryption keys so even a leaked row is ciphertext. |
| **BOLA / IDOR** | Attacker swaps an object id (`/papers/123` → `/papers/124`) to read another tenant's resource. **#1 in OWASP API Top 10.** ([Authgear IDOR](https://www.authgear.com/post/idor-insecure-direct-object-reference/), [arXiv BOLA](https://arxiv.org/pdf/2507.02309)) | **Object-level authz on every request** via SpiceDB `Check(user, view, resource)` — never trust the URL/id. Use unguessable ids as defense-in-depth, but the authz check is the control. |
| **Confused deputy in federation** | Compromised/fake IdP, or transitive trust (you trust Tenant A's IdP, A trusts a downstream AD) → adversary asserts identities into your platform. "Most federation issues are variations of the confused deputy." ([SlashID federation](https://www.slashid.dev/blog/identity-security-federation-issues/)) | Validate `issuer`/`audience` strictly; **scope every assertion to the asserting tenant** — an IdP for Tenant A can only mint Tenant-A identities. Require **Sirtfi** from IdPs. Pin/verify federation metadata + signing certs; alert on cert/metadata changes. |
| **IdP-initiated SSO bypass** | IdP-initiated flow lands a user in the wrong tenant context; isolation "collapses silently." ([SlashID](https://www.slashid.dev/blog/identity-security-federation-issues/)) | Prefer **SP-initiated** flows; if IdP-initiated is allowed, re-validate tenant binding server-side before establishing session. |
| **Token / session risk** | Stolen/replayed assertions or bearer tokens; over-broad scopes; long-lived tokens outliving revoked grants. | Short-lived access tokens + audience restriction; **DPoP/sender-constrained tokens** for confidential APIs; bind sessions to tenant + classification; re-check authz per request (don't cache "allowed"). |
| **Stale-grant / New Enemy Problem** | A revoked cross-institution share still reads a resource because a cache hasn't caught up. | **SpiceDB ZedToken** consistency on confidential checks; revocation flips `sharing_grant.is_active` and the next consistent Check denies. ([SpiceDB](https://github.com/authzed/spicedb)) |
| **Privilege creep via departed researcher** | Person leaves Tenant A but retains a collaborator relation in a confidential workspace. | **SCIM deprovisioning** + affiliation re-check cascade revocation through the authz graph (Section 1.5). |
| **AI exfiltration / shadow AI** | Faculty point a confidential workspace at a cloud frontier model; data leaves the boundary with no DPA. ([FERPA/GDPR shadow AI](https://secureprivacy.ai/blog/student-data-privacy-governance)) | Model router enforces classification→route binding; confidential ⇒ in-boundary local model only, network-egress-blocked; per-tenant BYO keys scoped so cloud routing is impossible for confidential-tagged data. |
| **Export-control violation (ITAR/EAR)** | Confidential dataset is export-controlled; a foreign-national collaborator's read = a "deemed export"; or data stored outside the US. ([UC Davis ITAR/EAR](https://cloud.ucdavis.edu/datatype/export-controlled-research-itar-ear), [Berkeley export control](https://spo.berkeley.edu/policy/exportcontrol.html)) | ABAC gate: `export_control` attribute + user citizenship/country + US-only residency; deny cross-border/foreign-national access on controlled resources. Note: imposing access controls can itself remove the Fundamental Research Exclusion, so this gate must be *opt-in per controlled project*, not blanket. ([Berkeley FRE exemptions](https://rac.berkeley.edu/ec/exemption.html), [WashU exclusions](https://research.washu.edu/exclusions-export-controls/)) |

---

## 7. Compliance Mapping (FERPA / GDPR / Export)

- **FERPA:** Position the platform as a **"school official"** under the institution's direct control; contractually limit data use to educational purposes; provide encryption, RBAC/ReBAC, audit logs. The school remains liable; you are its agent. ([Reform FERPA SaaS](https://www.reform.app/blog/ferpa-compliance-for-saas-tools-in-education), [getMonetizely FERPA](https://www.getmonetizely.com/articles/what-are-ferpa-and-student-privacy-regulations-in-edtech-saas))
- **GDPR:** University = controller, you = **processor**; mandatory **DPA**; honor **right-to-erasure** within 30 days — balanced against FERPA/accreditation retention (crypto-shred helps reconcile). Adopt **REFEDS CoCo v2** for EU IdP attribute release. ([SecurePrivacy student data](https://secureprivacy.ai/blog/student-data-privacy-governance), [REFEDS CoCo v2](https://refeds.org/category/code-of-conduct/v2))
- **Export (ITAR/EAR):** Fundamental Research Exclusion covers ordinarily-published research; controls bite on (a) accepting publication/access restrictions and (b) deemed exports to foreign nationals; controlled technical data must be **US-stored, US-person-access-only**. Provide the controls as an opt-in confidential-project mode (HYOK + US residency + nationality gate). ([UCCS FRE](https://osp.uccs.edu/export-controls/fundamental-research-exclusion-and-other-exemptions-from-export-controls), [Cornell export controls](https://researchservices.cornell.edu/resources/export-controls-research-and-education))

---

## 8. MVP Wedge vs Full Architecture (architecture constant, build order varies)

The locked NFR is "architecture stays constant; only build order changes." The security primitives that **cannot** be deferred without rework are tenancy, the authz graph, and the classification gate — build their *interfaces* in the MVP even if implementations are thin.

**MVP wedge (beachhead: a single research office / library at one R1, or one consortium):**
- SSO via **CILogon** (instant eduGAIN + ORCID reach, no federation-membership lift) → Keycloak session. JIT provisioning.
- SpiceDB with the tenant + org_unit + resource + sharing_grant schema, but only **public + private** tiers active; confidential tier *defined* but gated off.
- Per-tenant envelope encryption with platform-managed keys; **BYOK interface stubbed** (mandatory before first confidential customer).
- Audit log append-only from day one (cheap to add early, expensive to retrofit).
- SOC 2 Type II readiness process *started* (it gates the first institutional contract).

**Deferred to full platform:** HYOK, in-boundary AI router enforcement, export-control gate, full SCIM matrix, ISO 27001, multi-region residency, secure cross-institution workspaces (the confidential tier).

> Sequencing insight: lead with **cross-institution collaborator/expert discovery over public + private data** (feature 1) — lowest data-sensitivity, fastest to a defensible security review, and it exercises the federation + ReBAC + audit spine you'll reuse for the confidential features. Confidential workspaces (feature 3) come after BYOK + AI boundary + SOC 2 land.

---

## 9. Minimum Security Bar to Sell to a University (checklist)

**Identity & access**
- [ ] SAML2 + OIDC SSO; **InCommon/eduGAIN reachable** (directly or via CILogon broker)
- [ ] REFEDS **R&S + Sirtfi + CoCo v2** entity categories asserted
- [ ] **MFA** supported/enforceable; honors IdP-asserted assurance (REFEDS Assurance/MFA)
- [ ] **SCIM** provisioning + **deprovisioning** (auto-revoke on affiliation loss)
- [ ] SP-initiated flows default; strict `issuer`/`audience`/tenant-binding validation
- [ ] Object-level authorization on **every** request (no IDOR/BOLA surface)

**Data protection**
- [ ] AES-256 at rest, TLS 1.2+/mTLS in transit
- [ ] **Per-tenant envelope encryption**; **BYOK mandatory for confidential**, **HYOK offered**
- [ ] Confidential data + confidential AI inference **never leave the tenant boundary**; cloud egress blocked for confidential-tagged data
- [ ] Key rotation + crypto-shred for GDPR erasure

**Governance & audit**
- [ ] **Immutable/tamper-evident cross-institution access + grant + revocation audit trail**
- [ ] Per-tenant audit export (including external access to its shared resources)
- [ ] **Revocable, time-boxable, accountable** cross-institution sharing grants (grantor recorded)
- [ ] Demonstrable **tenant isolation** (deny-by-default; structural, not just a column)

**Compliance**
- [ ] **SOC 2 Type II** report (or in-progress with a date); ISO 27001 for international
- [ ] **FERPA "school official"** contractual posture; **GDPR DPA** with processor terms
- [ ] **Export-control mode** (ITAR/EAR): US residency + US-person-access gate, opt-in per controlled project
- [ ] Annual third-party/pen-test + documented incident response (Sirtfi-aligned)
- [ ] Subprocessor list + breach-notification SLA in contract

---

## Sources

- [UW IT Connect — Authenticate users from other academic institutions](https://it.uw.edu//security/iam/federation/)
- [AARC — Federations 101](https://aarc-project.eu/training/federations-101/)
- [LoginRadius — Shibboleth](https://www.loginradius.com/protocol/shibboleth)
- [uni-foundation — Guidelines: participating in eduGAIN (PDF)](https://uni-foundation.eu/uploads/2020_MyAID_Guidelines_eduGAIN.pdf)
- [GÉANT CONNECT — OIDC extension to Shibboleth Consortium](https://connect.geant.org/2019/12/18/propelling-openid-connect-forward)
- [Duende — SAML and OIDC: Coexistence, Not Competition](https://duendesoftware.com/blog/20260528-saml-and-openid-connect)
- [CILogon — OIDC scopes/claims and RP registration](https://www.cilogon.org/oidc)
- [CILogon — Enabling Federated Identity for Scientific Collaborations (paper)](https://www.researchgate.net/publication/337427194_CILogon_Enabling_Federated_Identity_and_Access_Management_for_Scientific_Collaborations)
- [REFEDS — eduPerson 2020-01](https://wiki.refeds.org/display/STAN/eduPerson+2020-01)
- [Internet2 — eduPerson Object Class Specification](https://software.internet2.edu/eduperson/internet2-mace-dir-eduperson-201602.html)
- [REFEDS — Research & Scholarship Entity Category](https://refeds.org/category/research-and-scholarship) | [R&S FAQ](https://wiki.refeds.org/display/ENT/Research+and+Scholarship+FAQ)
- [REFEDS — Sirtfi](https://refeds.org/sirtfi) | [Data Protection CoCo](https://refeds.org/a/2805) | [CoCo v2](https://refeds.org/category/code-of-conduct/v2)
- [PhaseTwo — Keycloak as IdP Broker](https://phasetwo.io/docs/keycloak/idp/) | [Keycloak](https://www.keycloak.org/)
- [Frontegg — Auth0 vs Keycloak](https://frontegg.com/guides/auth0-vs-keycloak) | [Oso — Keycloak alternatives](https://www.osohq.com/learn/best-keycloak-alternatives-2025)
- [Descope — SCIM providers for B2B SaaS](https://www.descope.com/blog/post/scim-providers-b2b-saas) | [Scalekit — SCIM imperative](https://www.scalekit.com/blog/the-scim-imperative-transforming-b2b-user-identity-management)
- [Oso — RBAC vs ABAC vs ReBAC](https://www.osohq.com/learn/rbac-vs-abac-vs-rebac-what-is-the-best-access-policy-paradigm) | [Permit.io — choosing the model](https://www.permit.io/blog/rbac-vs-abac-and-rebac-choosing-the-right-authorization-model) | [Pangea](https://pangea.cloud/blog/rbac-vs-rebac-vs-abac/) | [Aserto](https://www.aserto.com/blog/rbac-abac-and-rebac-differences-and-scenarios)
- [SpiceDB (GitHub)](https://github.com/authzed/spicedb) | [SpiceDB vs Auth0 FGA (sph.sh)](https://sph.sh/en/posts/spicedb-vs-auth0-fga/) | [OpenFGA vs Permify vs SpiceDB (PkgPulse)](https://www.pkgpulse.com/guides/openfga-vs-permify-vs-spicedb-zanzibar-authorization-2026) | [WorkOS — Zanzibar implementations](https://workos.com/blog/top-5-google-zanzibar-open-source-implementations-in-2024)
- [Permit.io — Policy Engine Showdown: OPA vs OpenFGA vs Cedar](https://www.permit.io/blog/policy-engine-showdown-opa-vs-openfga-vs-cedar) | [Teleport — Benchmarking policy languages](https://goteleport.com/blog/benchmarking-policy-languages/) | [sph.sh — Cedar vs Rego vs OpenFGA](https://sph.sh/en/posts/policy-language-comparison-cedar-rego-openfga/) | [CNCF — policy languages](https://www.cncf.io/blog/2024/05/21/love-hate-and-policy-languages-an-introduction-to-decision-making-engines/)
- [IBM — BYOK](https://www.ibm.com/think/topics/byok) | [Fortanix — BYOK vs HYOK](https://www.fortanix.com/blog/differences-between-byok-and-hyok) | [archTIS — BYOK vs HYOK](https://www.archtis.com/byok-vs-hyok-whats-the-difference-and-which-is-right-for-you/) | [Thales — cloud encryption / BYOK / HYOK](https://cpl.thalesgroup.com/blog/encryption/cloud-encryption-key-management-byok-hyok) | [Awssome — multi-tenant encryption FAQs](https://www.awssome.io/blog/multi-tenant-saas-security-encryption-faqs)
- [soc2auditors — SOC 2 checklist](https://soc2auditors.org/insights/soc-2-compliance-checklist/) | [Splunk — SOC 2 checklist](https://www.splunk.com/en_us/blog/learn/soc-2-compliance-checklist.html) | [Hyperproof — SOC 2 guide](https://hyperproof.io/soc2/) | [Mimecast — ISO 27001 vs SOC 2](https://www.mimecast.com/content/iso-27001-vs-soc-2/) | [Bright Defense — SOC 2 software](https://www.brightdefense.com/resources/best-soc-2-compliance-software/) | [Security Boulevard — SSO compliance comparison](https://securityboulevard.com/2026/04/11-sso-compliance-requirements-compared-soc-2-iso-27001-hipaa-pci-dss-and-gdpr/)
- [Authgear — IDOR](https://www.authgear.com/post/idor-insecure-direct-object-reference/) | [arXiv — Rethinking BOLA under Zero Trust](https://arxiv.org/pdf/2507.02309) | [SlashID — federation security issues](https://www.slashid.dev/blog/identity-security-federation-issues/) | [Security Boulevard — Tenant isolation](https://securityboulevard.com/2025/12/tenant-isolation-in-multi-tenant-systems-architecture-identity-and-security/)
- [UC Davis — Export Controlled Research (ITAR/EAR)](https://cloud.ucdavis.edu/datatype/export-controlled-research-itar-ear) | [Berkeley — export control policy](https://spo.berkeley.edu/policy/exportcontrol.html) | [Berkeley — exemptions/exclusions](https://rac.berkeley.edu/ec/exemption.html) | [UCCS — Fundamental Research Exclusion](https://osp.uccs.edu/export-controls/fundamental-research-exclusion-and-other-exemptions-from-export-controls) | [WashU — exclusions](https://research.washu.edu/exclusions-export-controls/) | [Cornell — export controls in research](https://researchservices.cornell.edu/resources/export-controls-research-and-education)
- [Reform — FERPA compliance for SaaS](https://www.reform.app/blog/ferpa-compliance-for-saas-tools-in-education) | [getMonetizely — FERPA in EdTech SaaS](https://www.getmonetizely.com/articles/what-are-ferpa-and-student-privacy-regulations-in-edtech-saas) | [SecurePrivacy — student data privacy governance](https://secureprivacy.ai/blog/student-data-privacy-governance)