# Multi-edge identity, trust and credential distribution

```
Topic:          How do comparable systems distribute and scope credentials across trust
                boundaries; what breaks when an edge is a laptop rather than a datacentre
                host; and what prior art exists for a three-tier edge / local-network /
                federated model?
Feeds:          docs/standards/architecture/problem-statement.md § "Where we actually differ" #1
                (the trust boundary — the strongest claim); and `Phase: Temporal Integration`
                in docs/development/roadmap.md — worker placement, queue naming, and what a
                worker may hold.
Last validated: 2026-08-06
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE (first-party documented, raw sources only) for: the SPIFFE trust-domain
                and federation model; the SPIRE node-attestor inventory; SPIRE TTL defaults;
                RFC 8693 / 9449 / 9334 / 7030 mechanics; the WebAuthn non-extractability property;
                Matrix's per-request signing and key-publication mechanism; Kubernetes KEP-1645's
                mutual-trust precondition; Vault Enterprise namespaces' single-organization framing;
                Temporal's default `noopAuthorizer` posture; BOINC's stated participant threat model;
                WireGuard's out-of-band key-distribution posture.
                DIRECTIONAL for: the SPIFFE Broker API (self-declared "Incubating").
                DERIVED (this paper's own inference, inputs named per claim) for: the three-tier
                model's decomposition into three DIFFERENT prior arts; the "everyone punts the
                bootstrap out-of-band" convergence; the BOINC polarity inversion; the cost table;
                the classification of the 10 SPIRE node attestors.
                GAP / NOT VERIFIED: whether the Claude Code edge credential is a plain bearer token
                and whether its issuer supports any sender-constraining; certificate revocation in
                the SPIFFE X.509 spec (searched, absent); hardware-root-of-trust availability on
                this fleet's actual laptops. Search methods stated at each gap.
Critic:         not-yet-verified — 2026-08-06
```

> **Mixed volatility, per Research Standard §3.** The header takes the highest tier present. Only
> **§3.6** (competitive positioning) and **§6.2** (the Temporal security surface) are genuinely
> high-volatility. **§§1, 2, 4, 5.1–5.4, 7 are LOW** — they rest on ratified specs (SPIFFE, RFC 7030 /
> 8693 / 9334 / 9449, W3C WebAuthn), a 2004 peer-reviewed paper, and a stable protocol spec. **A
> refresh may skip them** unless a named spec issues a new version.

> **What "quoted" means in this paper.** Every span in quotation marks was obtained from a **raw
> first-party artifact**: `raw.githubusercontent.com`, `api.github.com` JSON, an IETF `.txt` RFC, or a
> PDF I read directly. **No rendered HTML page was fetched anywhere in this cycle**, so no claim here
> inherits that fabrication surface. The two PDF sources ([S23] WireGuard, [S24] BOINC) were rendered
> to me page-by-page and I read the characters myself. Where a fetch returned a fragment without its
> enclosing sentence, that is flagged inline.

---

## 0. Verdict up front

**The three-tier claim survives, but not in the form the problem statement states it, and its
strongest part is currently unenforced.**

Three findings drive everything below.

**0.1 The *shape* is not novel, and that is good news.** Two of the three tiers have a mature,
ratified specification: SPIFFE's **trust domain** is the MDC tier ("A SPIFFE trust domain is an
identity namespace which is backed by an issuing authority with a set of cryptographic keys" [S3]),
and SPIFFE **federation** is the federated tier ("the act of obtaining the necessary SPIFFE bundle(s)
to authenticate SVIDs issued by a different trust domain, and providing said bundles to the workloads
performing the authentication" [S1]). Per §0 of `problem-statement.md`, mining beats inventing — this
is a win, not a loss. What SPIFFE federation moves across the boundary is **public trust material
only**: "A SPIFFE bundle is an object containing a trust domain's cryptographic keys. The keys within
the bundle are considered authoritative for the trust domain that the bundle represents" [S3]. **That
is exactly the problem statement's "holds no edge credential", already specified, already shipped, by
someone else.** §4.1.

**0.2 The edge tier is where the prior art runs out — and the reason is a polarity inversion.** The
best-documented "edge is a laptop" system in the sweep is BOINC, whose threat model is stated
outright: "Projects have no control over participants, and cannot prevent malicious behavior" [S24].
Its answer is not attestation; it is redundancy plus validation. **But BOINC protects the *project*
from the *volunteer*. This design has to protect the *volunteer's credential* from the *federation*.**
No system located in this sweep does that at the compute-placement layer. The closest primitive is
WebAuthn's, and it is a *credential* property rather than a *placement* property: the credential
private key "is bound to a particular [=authenticator=] - its [=managing authenticator=] - and is
expected to never be exposed to any other party, not even to the owner of the [=authenticator=]"
[S16]. §4.3, §5.

**0.3 The strongest claim is, today, a topology statement and not a security mechanism — and the
paper says so.** "Holds its own credential, which never leaves it" is currently enforced by *where the
worker runs*, not by anything cryptographic. The edge credential is a file on disk
(`~/.claude/.credentials.json` — named as machine-local state in this repo's own `CLAUDE.md`, and used
as a diagnostic surface in [I5]). If it is a bearer token, it is copyable by anyone with read access,
and the tier boundary holds only because nothing tries to cross it. **This is the single most
important open question in the paper and it is a one-hour experiment, not more research** (T1/T2 in
§8). Until it is answered, differentiator #1 should be stated as *"the design places the credential at
the edge and nothing in the federated tier is given a path to it"* rather than as a property the
credential itself has.

**Strongest located analogue:** the **SPIFFE Federation bundle endpoint** [S1][S3], corroborated by an
independent convergent design in **Matrix's published server signing keys plus per-request `X-Matrix`
signatures** [S17]. Two unrelated multi-operator fabrics arrived at the same answer for the
MDC↔federated boundary: *publish your public trust material at a well-known URL under web PKI, and
sign every request with a key the other side never holds.* §4.1.

**Biggest gap not closed:** nothing in this sweep addresses **an edge whose credential is issued by a
third party to a human, and is therefore neither mintable nor revocable by the trust domain the edge
belongs to.** Every identity system surveyed assumes the trust domain *issues* the identity it
consumes. §7.4.

---

## 1. Primer — the three questions any multi-edge identity system must answer

Grounding, so the rest of the paper is readable without a PKI background. Every system in §3 answers
these three questions and they are independent:

| # | Question | Name of art | Failure if unanswered |
|---|---|---|---|
| **Q1** | How does a machine prove it is the machine it claims to be, the *first* time? | **node attestation** / enrollment / bootstrap | anyone who can reach the endpoint can join the fleet |
| **Q2** | Once trusted, what credential does it get, how long does it live, and how is it withdrawn? | **issuance, rotation, revocation** | a stolen credential is valid forever |
| **Q3** | How does a *second, separately-administered* system come to accept credentials from the first? | **federation** / trust-bundle exchange | every cross-operator link is a bilateral hand-built secret |

RFC 9334, the IETF's remote-attestation architecture, gives Q1 its vocabulary: an **Attester**
"whose Evidence must be appraised in order to infer the extent to which the Attester is considered
trustworthy", a **Verifier** that "appraises the validity of Evidence about an Attester and produces
Attestation Results", and a **Relying Party** that "depends on the validity of information about an
Attester for purposes of reliably applying application-specific actions" [S14]. RFC 9334 also states
the assumption that makes hardware attestation work at all — and, read carefully, the assumption a
laptop cannot supply for free: "It is assumed that an Attesting Environment is sufficiently isolated
from the Target Environment it collects Claims about and that it signs the resulting Claims set with
an attestation key so that the Target Environment cannot forge Evidence" [S14]. *(definitive; raw RFC
text)*

**The load-bearing observation of this whole paper is that Q1 is where every mature system stops and
hands the problem to a human.** §5.1.

---

## 2. The specific model — the three tiers, mapped onto named prior art

The problem statement's tiers [I1], with the closest specified primitive for each:

| Tier | Problem statement says | Closest specified prior art | Transfer quality |
|---|---|---|---|
| **Edge** — a participant's own machine, possibly a laptop | "holds its own credential, which never leaves it" | **WebAuthn platform authenticator** [S16]; **DPoP** sender-constrained tokens [S13]; **TPM DevID** [S10] | **Partial.** The *property* is specified and standard. The *mechanism* requires the credential issuer to cooperate, and ours does not obviously do so (§7.4, T1). |
| **MDC** — the local trusted network, one operator's domain | "runs local services and workloads — secure, but one operator's domain" | **SPIFFE trust domain** [S3]; **Vault Enterprise namespace** [S22]; **Istio mesh trust domain** [S19] | **Strong.** This is a solved, specified concept with three independent shipped implementations. |
| **Federated** — across MDCs and operators | "deliberately limited: sends work over the trunk, holds no edge credential" | **SPIFFE Federation bundle endpoint** [S1]; **Matrix `/_matrix/key/v2/server` + `X-Matrix`** [S17] | **Strong, and convergently corroborated.** Both designs move public keys only. |

**DERIVED, from [S1] + [S3] + [S13] + [S16] + [S17] + [S19] + [S22]:** *the three-tier model is not one
invention; it is a composition of three separately-mature prior arts that nobody has previously had a
reason to compose.* The composition is where the work is, not the tiers. This is a materially
different — and much cheaper — statement than "we are building a novel trust model."

**Why nobody composed them.** *(DERIVED, from [S20] + [S22] + [S24] + [I3])* Datacentre systems never
needed the edge tier because their edges are hosts the operator owns and can re-provision at will;
volunteer-compute systems never needed the MDC tier because there is no trusted local network between
a volunteer and a project. **Our shape exists because the credential is a per-person subscription
owned by a human — an economics fact, not a security fact** [I1 § *Affordability is the enabler*].
That is the honest answer to "what has nobody attempted and why not."

---

## 3. Comparative landscape — the discriminating question, answered

The dispatch's discriminating question was: *which of these assume a single operator, and which
genuinely span operators?* Answered from first-party text only.

| System | Spans distinct operators? | The sentence that settles it | Conf. |
|---|---|---|---|
| **Kubernetes Multi-Cluster Services (KEP-1645)** | **No** | A ClusterSet is "A placeholder name for a group of clusters with a high degree of mutual trust and shared ownership that share services amongst themselves"; and "This requires that within a clusterset, a given namespace is governed by a single authority across all clusters" [S20] | definitive |
| **HashiCorp Vault Enterprise namespaces** | **No** | Namespaces support "secure multi-tenancy (SMT) within a single Vault Enterprise instance"; the framing is "the different teams in an organization" [S22] | definitive |
| **Slurm federation** | **No — and it does not even raise the question** | The federation doc is silent on administrative domains (search method in §3.5); what it does state is a *shared* namespace: "Job ids in the federation are unique across all clusters in the federation" [S18] | definitive (for the silence; method stated) |
| **Istio multi-mesh** | **Yes, at the mesh boundary** | "When federating two meshes that do not share the same trust domain, you must federate identity and trust bundles between them"; "To enable communication between two meshes with different CAs, you must exchange the trust bundles of the meshes" [S19] | definitive |
| **SPIFFE Federation** | **Yes, by design** | "SPIFFE is decentralized by nature...a core SPIFFE use case is enabling communication across these same boundaries where needed. Therefore, it is necessary to define a mechanism by which an entity may be introduced to a foreign trust domain" [S1] | definitive |
| **Matrix server-server API** | **Yes, by design** | Each homeserver "publishes its public keys under `/_matrix/key/v2/server`" and every request is signed: "The resulting signatures are added as an `Authorization` header with an auth scheme of `X-Matrix`" [S17] | definitive for the mechanism; **derived** for "by design" (inferred from per-server key publication + per-request signing + hostname-scoped delegation rules, not from a quoted design statement) |
| **BOINC** | **Yes, radically — and with zero host trust** | "BOINC-based projects are autonomous. Projects are not centrally authorized or registered. Each project operates its own servers and stands completely on its own" [S24] | definitive |
| **bernstein (nearest neighbour)** | **No, by its own documentation** | "Fleet mode is multi-project, **not** multi-tenant in the security sense. Every task server it queries is assumed to be run by the same operator, on a network the operator trusts"; v1 limitations list "Cross-tenant federation across organisations" [I3 §0.2] | definitive |

**3.1 The count.** Of eight systems enumerated above, **four** genuinely span distinct operators
(Istio multi-mesh, SPIFFE Federation, Matrix, BOINC) and **four** do not (Kubernetes MCS, Vault
namespaces, Slurm federation, bernstein fleet). *(This count is over the enumerated population in the
table above — it is a count of this paper's own list, not a claim about the field's totals.)*

**3.2 The pattern in that split.** *(DERIVED, from the table's own rows.)* **Every system that spans
operators is a communication or work-distribution fabric; every system that does not is a
resource-management plane.** Kubernetes MCS, Vault namespaces and Slurm federation are all
schedulers/stores that assume they can *see and control* the resource. SPIFFE federation, Matrix and
BOINC all assume they *cannot*. The three-tier model asks the federated tier to be the second kind
while the MDC tier is the first kind — which is precisely the layering `problem-statement.md`
describes, and it is a known-good split rather than an unusual one.

**3.3 Grid vs. volunteer computing — the cleanest statement of the axis, from 2004.** Anderson
contrasts Grid computing, where "There is a symmetric relationship between organizations: each one can
either provide or use resources. Malicious behavior such as intentional falsification of results would
be handled outside the system, e.g. by firing the perpetrator", with public-resource computing, which
"involves an asymmetric relationship between projects and participants" [S24]. **The MDC↔MDC link is
the symmetric case (contracts, operators, out-of-band recourse); the MDC↔edge link is the asymmetric
case.** That is a 22-year-old, peer-reviewed articulation of exactly the two-different-boundaries
insight the three-tier model encodes. *(definitive for the quotes; derived for the mapping.)*

**3.4 What the SPIFFE bundle endpoint does and does not transfer.** The dispatch asked specifically.

*Transfers:*
- **The direction of flow.** Only bundles cross; credentials never do [S1][S3]. Direct support for
  "the federated tier holds no edge credential."
- **Two authentication profiles, one of which needs no prior relationship.** "The `https_web` profile
  leverages publicly trusted certificate authorities to provide a low-friction path for configuring
  SPIFFE Federation"; "The `https_spiffe` profile uses an X509-SVID issued by a SPIFFE trust domain (as
  opposed to a certificate issued by public certificate authorities)" [S1]. Web PKI for the first
  contact, SPIFFE-native once established — a two-phase pattern SkyyNet can copy verbatim.
- **A polling/currency contract.** "Clients SHOULD poll at a frequency equal to the value of the
  bundle's `spiffe_refresh_hint`, in seconds. If not set, a reasonably low default value should apply -
  five minutes is recommended" [S1].
- **Rotation without revocation infrastructure.** "Keys are added and revoked by issuing a new bundle
  with new keys included and revoked keys omitted" [S3].

*Does NOT transfer:*
- **It does not solve first contact.** "If the endpoint is self-serving, clients need to be configured
  with a single up-to-date bundle in order to bootstrap the federation relationship" [S1]. The
  chicken-and-egg is acknowledged and handed back to the operator.
- **It says nothing about distribution mechanics inside a trust domain.** "The exact format and method
  by which these updates are delivered is out of scope for this specification"; "It is the
  responsibility of the SPIFFE implementation to distribute bundle content updates to workloads as
  needed" [S3].
- **It is about *authenticating* SVIDs, not about *authorizing* work.** Nothing in [S1] constrains what
  a federated peer may ask a trust domain to do. The authorization half is entirely ours to build
  (§6.2 — and see bernstein's channel/action split, [I3 §4.18]).

**3.5 Negative finding — Slurm federation and administrative domains. Search method:** fetched
`raw.githubusercontent.com/SchedMD/slurm/master/doc/html/federation.shtml` twice, the second time with
an explicit token search for `slurmdbd`, `database`, `unique`, `cluster name`, `munge`, `auth`, `same`.
The fetch reported **not found** for `slurmdbd`, `database`, `munge` and `auth`, and returned no
sentence about administrative domains. **Result: the Slurm federation document does not discuss trust,
authentication, or administrative boundaries at all** — the shared job-ID space [S18] is the only
cross-cluster coupling it names. This is a *finding*, not a gap: a scheduler federation spec that never
mentions authentication is strong evidence that the field treats intra-operator federation as an
authentication non-problem.

**3.6 Competitive positioning — HIGH volatility, and owned elsewhere.** The bernstein reading in the
table is transcribed from [I3], which is the paper that owns it. This paper does not re-derive it and a
refresh of *this* paper should not re-fetch it; refresh [I3] instead.

---

## 4. What comparable systems ACTUALLY do — including the negative results

Not what they could do. What ships.

### 4.1 The convergence: publish public keys at a well-known URL, sign every request

SPIFFE and Matrix are unrelated projects with unrelated goals and they built the same thing.

- SPIFFE: "A SPIFFE bundle endpoint is a resource (represented by a URL) that serves a copy of a
  SPIFFE bundle for a trust domain"; "Bundle endpoint URLs utilizing `https_web` MUST have the scheme
  set to `https` and MUST NOT include userinfo in the authority component" [S1].
- Matrix: "Each homeserver publishes its public keys under `/_matrix/key/v2/server`. Homeservers query
  for keys by either getting `/_matrix/key/v2/server` directly or by querying an intermediate notary
  server"; "The request method, target and body are signed by wrapping them in a JSON object and
  signing it using the JSON signing algorithm" [S17]. Key expiry is enforced at verification time:
  "only signatures from known unexpired keys from the originating server(s) are found to be valid",
  and "any keys that are known to have expired prior to the event's `origin_server_ts` are ignored"
  [S17].

**DERIVED, from [S1] + [S3] + [S17]:** two independent designs for cross-operator trust converged on
*(a)* a well-known HTTPS endpoint per operator, *(b)* public material only, *(c)* per-request or
per-event signatures verified against that material, and *(d)* expiry-at-verification rather than
revocation lists. **This is the design SkyyNet's trunk should adopt, and adopting it is a specification
read, not a research problem.** Matrix additionally supplies a primitive SPIFFE lacks: an
**intermediate notary server** [S17], which is directly useful when an MDC is behind NAT or
intermittently reachable.

### 4.2 The negative result that matters most: **everybody punts the bootstrap out-of-band**

Four independent, first-party, raw sources say the same thing, and none of them apologises for it.

1. **SPIRE join token** — "The `join_token` is responsible for attesting the agent's identity using a
   one-time-use pre-shared key" [S9]. A secret a human carries to the machine.
2. **SPIRE TPM DevID** — "The `tpm_devid` plugin provides attestation data for a node that owns a TPM
   and that has been provisioned with a LDevID certificate through an out-of-band mechanism", and
   "Only local device identities (LDevIDs) are supported. Attestation using IDevIDs is not supported"
   [S10]. Even the hardware-root-of-trust path requires out-of-band provisioning first.
3. **WireGuard** — "Through a diverse set of out-of-band mechanisms, two peers generally exchange their
   static public keys", and explicitly: "WireGuard's attitude toward key distribution is that this is
   the wrong layer to address that particular problem, and so the interface is simple enough that any
   key distribution solution can be used with it" [S23].
4. **RFC 7030 (EST)** — the IETF's own enrollment protocol requires a *human*: the client "MUST extract
   the HTTP content data from the response...and engage a human user to authorize the CA certificate
   using out-of-band data such as a CA certificate 'fingerprint'", and "It is incumbent on the user to
   properly verify the TA information, or to provide the 'fingerprint' data during configuration that
   is necessary to verify the TA information" [S15].

**DERIVED, from [S9] + [S10] + [S15] + [S23]:** *there is no shipped, specified mechanism for enrolling
a machine into a trust domain without either (a) a platform-issued instance identity document the
trust domain already trusts, or (b) an out-of-band secret carried by a human.* **A laptop has neither
(a) available. Therefore the three-tier model's edge-enrollment step is (b), a human, and that is not a
shortcut — it is what the entire field does.** This should be written into the standard as a deliberate
choice with these four citations, not left as an embarrassment to be engineered away later.

### 4.3 The device-bound-credential art, and its precondition

WebAuthn is the cleanest statement of the edge tier's desired property: the credential private key "is
bound to a particular [=authenticator=] - its [=managing authenticator=] - and is expected to never be
exposed to any other party, not even to the owner of the [=authenticator=]" [S16]. It also gives the
scoping primitive: "The [=RP ID=] of a [=public key credential=] determines its scope" [S16], and it
distinguishes the two form factors — "[=Authenticators=] being implemented on device are called
[=platform authenticators=]. Authenticators being implemented off device ([=roaming authenticators=])
can be accessed over a transport such as Universal Serial Bus (USB), Bluetooth Low Energy (BLE), or
Near Field Communications (NFC)" [S16]. Attestation is separately defined: it "is employed to provide
verifiable evidence as to the origin of an [=authenticator=] and the data it emits" [S16].

For OAuth-shaped credentials the equivalent is DPoP: "an application-level mechanism for
sender-constraining OAuth access and refresh tokens. It enables a client to prove the possession of a
public/private key pair by including a DPoP header in an HTTP request" [S13]. Its key sentence for
this design: "If the private key is non-extractable (as is possible with W3C.WebCryptoAPI), DPoP
renders exfiltrated tokens alone unusable" [S13].

**The precondition, stated plainly: all three of these require the *issuer* to participate.** WebAuthn
needs a relying party that speaks WebAuthn; DPoP needs an authorization server that issues
DPoP-bound tokens; TPM DevID needs someone to provision an LDevID. **The edge credential here is issued
by a model vendor to a human on a subscription.** Whether that issuer offers any sender-constraining is
**NOT VERIFIED in this cycle** — search method: not attempted; this cycle's fetches were confined to
identity specifications and comparable-system documentation, and vendor OAuth surfaces were out of the
dispatched scope. It is T1 in §8 and it is cheap to settle.

### 4.4 Short-lived credentials replace revocation — with concrete numbers

The shipped answer to "how do you revoke a credential on a machine that is off" is: *don't; expire it.*

- SPIRE server defaults, from the raw configuration reference: `default_x509_svid_ttl` = "1h",
  `default_jwt_svid_ttl` = "5m", `ca_ttl` = "24h" [S11]. *(definitive)*
- The administrative controls exist and are coarse: `spire-server agent ban` — "Ban attested node given
  its spiffeID. A banned attested node is not able to re-attest" — and `spire-server agent evict` —
  "De-attesting an already attested node given its spiffeID" [S11]. **Both act at the next
  re-attestation, not on the running node.**
- SPIFFE trust-bundle rotation is by *replacement*: "Keys are added and revoked by issuing a new bundle
  with new keys included and revoked keys omitted" [S3].
- GitHub Actions states the same doctrine for cloud access: "you can configure your workflow to request
  a short-lived access token directly from the cloud provider", with the benefit "Rotating credentials:
  With OIDC, your cloud provider issues a short-lived access token that is only valid for a single job"
  [S21].

**Negative finding — revocation in the SPIFFE X.509 spec. Search method:** fetched
`raw.githubusercontent.com/spiffe/spiffe/main/standards/X509-SVID.md` and searched for lifetime,
revocation, CRL and OCSP terms. **Result: the X509-SVID specification does not address certificate
revocation, and does not state a lifetime requirement either.** What it does mandate is that leaf SVIDs
"MUST NOT set `keyCertSign` or `cRLSign`" [S4] — i.e. the spec removes the *ability* to sign CRLs from
leaves and then never defines a revocation mechanism. **DERIVED, from [S3] + [S4] + [S11]:** SPIFFE's
revocation story is *entirely* short-TTL-plus-bundle-replacement; there is no online revocation check
anywhere in the model. For an intermittently-connected edge this is the right architecture and the
wrong ergonomics — a laptop that is asleep for six hours wakes with an expired SVID and must
re-attest, which is the same class of failure [I5] already ranks first for this fleet.

### 4.5 Scoping: what the field uses to say "this credential may do only this"

- **SPIFFE:** the identity itself carries the scope. "A SPIFFE Identity (or SPIFFE ID) is defined as an
  RFC 3986 compliant URI comprising a 'trust domain name' and an associated path" [S2]; in X.509 form,
  "An X.509 SVID MUST contain exactly one URI SAN, and by extension, exactly one SPIFFE ID" [S4].
- **OIDC workload identity federation:** the scope is a *claim match* configured at the resource side —
  "the OIDC token's subject and other claims are a match for the conditions that were preconfigured on
  the cloud role's OIDC trust definition", with subjects shaped like
  "repo:octo-org/octo-repo:environment:prod" [S21]. **This is the closest existing analogue to
  "queue naming that expresses what a worker may hold"** and it is worth copying its shape:
  a hierarchical, machine-parseable subject string that the *relying* side pattern-matches.
- **OAuth Token Exchange (RFC 8693):** gives the vocabulary for a *federated tier that acts on behalf
  of an edge without holding its credential*. The distinction is exactly the one the three-tier model
  needs: "When principal A impersonates principal B, A is given all the rights that B has within some
  defined rights context and is indistinguishable from B in that context", versus "With delegation
  semantics, principal A still has its own identity separate from B, and it is explicitly understood
  that while B may have delegated some of its rights to A, any actions taken are being taken by A
  representing B" [S12]. **SkyyNet dispatching work to an MDC is delegation, never impersonation** —
  and RFC 8693 is the ratified way to say so. Its `grant_type` is
  "urn:ietf:params:oauth:grant-type:token-exchange" [S12]. *(definitive for the quotes; derived for the
  mapping onto our tiers.)*
- **Vault Enterprise namespaces:** hierarchical delegated administration — "Vault system administrators
  can assign administration rights to delegate admins to allow teams to self-manage their namespace. In
  addition to basic management, delegate admins can create child namespaces and assign admin rights to
  subordinate delegate admins" [S22]. A useful model for SkyyNet→MDC→edge *administration* even though
  its tenancy assumption is single-organization.

### 4.6 The systems that punt entirely — and why they got away with it

The dispatch asked for these specifically, because "what the field considers sufficient" is evidence.

- **Temporal, self-hosted, out of the box, holds nothing back:** "If you do not explicitly configure an
  Authorizer, Temporal uses the default noopAuthorizer. This default allows every API request, with no
  authentication or access control", and "Without this, your deployment is effectively open to anyone
  with network access" [S25]. It also documents the escape hatch operators actually take: "users may
  also choose to design their own security architecture with reverse proxies or run unsecured instances
  inside of a VPC environment" [S25]. **They get away with it because the network is the boundary.**
- **bernstein's mTLS**, per [I3 §4.18]: opt-in, "existing plain-HTTP deployments keep working", and
  **"Rotation is manual"**. They get away with it because the fleet is "run by the same operator, on a
  network the operator trusts" [I3 §0.2].
- **Slurm federation** never mentions authentication at all (§3.5). It gets away with it because a
  cluster federation is one site's HPC estate.
- **WireGuard** declines the key-distribution problem on principle [S23]. It gets away with it because
  it is a transport, and its layering argument is correct.

**DERIVED, from [S25] + [S23] + [S18] + [I3]:** *the field's actual sufficiency bar for
compute-orchestration identity is "the network is the trust boundary", and it is met by an
operator-controlled LAN or VPC.* **The three-tier model is a claim that this bar is wrong for a fleet
whose edges are people's laptops.** That claim is defensible — but it must be argued from the *laptop*,
not from an abstract preference for zero trust, because the field's default is well-reasoned for the
datacentre case and the paper should concede that (§7.1).

---

## 5. What breaks when an edge is a LAPTOP — the sharpest half

Nine failure modes, each marked **solved** (named mechanism exists), **priced** (mechanism exists, cost
is the issue), or **open** (no located mechanism).

| # | Failure mode | Status | Mechanism / evidence |
|---|---|---|---|
| **L1** | Intermittent connectivity; sleep/resume | **Priced** | BOINC names it as a design premise: participants' "computers are frequently turned off or disconnected from the Internet" [S24], and answers with exponential backoff plus soft deadlines on workunits. Temporal's durable execution answers the orchestration half [I3 §3]. The residual cost is credential expiry across the sleep — see L4. |
| **L2** | No stable network identity; NAT; roaming | **Solved** | WireGuard: "In WireGuard, peers are identified strictly by their public key, a 32-byte Curve25519 point"; and "Since a public key uniquely identifies a peer, the outer external source IP of an encrypted WireGuard packet is used to identify the remote endpoint of a peer, enabling peers to roam freely between different external IPs, between mobile networks for example" [S23]. Matrix's **notary server** [S17] solves the unreachable-peer variant for trust material. BOINC names NAT explicitly [S24]. **Identity must not be an address. This is settled art.** |
| **L3** | No guaranteed hardware root of trust | **Open in practice** | See §5.1 — the enumerated SPIRE attestor population. A laptop has no instance identity document, no Kubernetes projected token, and `tpm_devid` needs an LDevID "provisioned...through an out-of-band mechanism" [S10]. Whether *this fleet's* laptops even have a usable TPM/Secure Enclave path is **NOT VERIFIED** (T6). |
| **L4** | Credential expiry at an unattended edge | **Priced — and live today** | [I5] ranks this the #1 exposure for this fleet, at ~2 operator-hours to mitigate, citing an upstream report that "OAuth access tokens expire and are not refreshed when Claude Code is invoked non-interactively" and a second that the credential can be "replaced with an empty value" on a failed refresh [I5 §2.7.1]. The field's answer (short TTL + re-attest, §4.4) *makes this worse*, not better, on a machine that sleeps. |
| **L5** | Revocation reaching a machine that is off | **Solved by redefinition** | Nobody delivers revocation to an offline machine. SPIFFE replaces the bundle [S3]; SPIRE `agent ban` acts at next re-attestation [S11]; Matrix ignores expired keys at verification time [S17]. **The correct design posture: make credentials short-lived enough that revocation is unnecessary, and accept that a stolen laptop is authorised until its current credential expires.** |
| **L6** | Physical loss or theft | **Priced** | Reduces to L5 plus the device-bound-key question (§4.3). If the credential is a file, theft of the disk is theft of the credential; if it is non-extractable, "DPoP renders exfiltrated tokens alone unusable" [S13]. **The entire delta between these two outcomes is T1/T2.** |
| **L7** | The machine's owner is an adversary, or merely careless | **Solved, but for the opposite polarity** | BOINC is the definitive treatment: "Projects have no control over participants, and cannot prevent malicious behavior", answered by redundant computing — "A project can specify that N results should be created for each workunit. Once M ≤ N of these have been distributed and completed, an application-specific function is called to compare the results and possibly select a canonical result" — plus an anti-collusion rule, "a work-distribution policy that sends only at most one result of a given workunit to a given user" [S24]. **This is a validation strategy, not an identity strategy, and it works because BOINC's asset is the result.** Our asset is the credential; the strategy does not transfer. §7.4. |
| **L8** | Attestation when you cannot trust the host | **Open, and RFC 9334 says why** | "It is assumed that an Attesting Environment is sufficiently isolated from the Target Environment it collects Claims about and that it signs the resulting Claims set with an attestation key so that the Target Environment cannot forge Evidence" [S14]. **On a laptop with no hardware attesting environment, that assumption fails and the whole RATS model degrades to trusting software on a machine you don't control.** There is no shipped fix; there is a choice between hardware and giving up. |
| **L9** | The edge's credential is not the trust domain's to issue | **Open — no located prior art** | §7.4. |

### 5.1 The enumerated evidence for L3: SPIRE's node attestors

**Population and method:** enumerated via the GitHub contents API on `spiffe/spire/contents/doc`
([S8], default branch confirmed as `main` for `spiffe/spiffe` [S7]; the SPIRE listing resolved without
a redirect on the same default). I listed the entries and counted the list myself; I did not ask any
layer for a total.

Agent-side node attestor plugin docs, enumerated: `aws_iid`, `azure_imds`, `azure_msi`, `gcp_iit`,
`http_challenge`, `jointoken`, `k8s_psat`, `sshpop`, `tpm_devid`, `x509pop` — **10**. The server-side
set carries the same 10 names. Workload attestors, enumerated: `docker`, `k8s`, `systemd`, `unix`,
`windows` — **5**.

**DERIVED classification of the 10** (the grouping is this paper's; the names are from [S8]):

| Class | Members | Count | Available to a laptop? |
|---|---|---|---|
| Cloud instance identity document | `aws_iid`, `azure_imds`, `azure_msi`, `gcp_iit` | 4 | **No** |
| Orchestrator-issued token | `k8s_psat` | 1 | **No** |
| Pre-shared secret or pre-provisioned key, delivered out-of-band | `jointoken`, `sshpop`, `x509pop`, `tpm_devid` | 4 | **Yes — via a human** |
| Network-reachability challenge | `http_challenge` | 1 | **No** (a roaming laptop is not reachable) |

**Six of ten attestation methods in the reference SPIFFE implementation are unavailable to a laptop,
and the four that remain all reduce to "a human carried a secret to the machine."** This is the
strongest single piece of evidence in the paper for why the edge tier has no cheap technical answer,
and it is an enumeration rather than an assertion.

---

## 6. What this provides — enumerated, citable properties a plan can rely on

Each item is something a planner may treat as established by this paper.

1. **The federated tier's boundary contract is already specified.** Bundles only, never credentials
   [S1][S3]; two auth profiles, web-PKI for first contact [S1]; polling with `spiffe_refresh_hint`
   [S1]; rotation by bundle replacement [S3]. *(definitive)*
2. **An independent corroborating implementation of the same contract exists** in Matrix, including a
   primitive SPIFFE lacks — the notary server for unreachable peers [S17]. *(definitive for mechanism)*
3. **The MDC tier is a SPIFFE trust domain**, a concept with a ratified definition [S3] and three
   independent shipped realisations [S3][S19][S22]. *(definitive)*
4. **Delegation, not impersonation, is the correct and ratified vocabulary** for SkyyNet→MDC work
   dispatch, with a standard grant type [S12]. *(definitive for the RFC; derived for the mapping)*
5. **Scope belongs in a hierarchical, machine-parseable subject that the relying side pattern-matches**
   — SPIFFE ID paths [S2][S4] and OIDC subject claims like `repo:org/repo:environment:prod` [S21]
   are the two shipped shapes. *(definitive)* **This directly answers the roadmap's queue-naming
   question: name the queue the way SPIFFE names an ID.**
6. **Revocation should be designed out, not built.** Short TTLs (SPIRE: 1h X.509, 5m JWT, 24h CA
   [S11]), bundle replacement [S3], expiry-checked-at-verification [S17]. *(definitive)*
7. **Out-of-band, human-mediated enrollment is the field standard, not a shortcut** — four independent
   first-party confirmations [S9][S10][S15][S23]. *(derived from four definitive inputs)*
8. **Temporal self-hosted is open by default and this must be closed in the Temporal Integration
   phase** — "the default noopAuthorizer...allows every API request, with no authentication or access
   control" [S25]. The plugin points are named: `ClaimMapper` and `Authorizer`, with per-namespace
   permissions from the set "read, write, worker, admin" [S25]. *(definitive)* **This is the one item
   in the paper that is urgent independent of the three-tier thesis.**
9. **Identity must not be an address** — WireGuard's cryptokey routing is the settled answer for
   roaming edges [S23]. *(definitive)*
10. **A no-trust-in-the-host strategy exists and is proven at million-host scale, but its polarity is
    wrong for us** [S24]. *(definitive for BOINC's mechanism; derived for the non-transfer)*

### 6.1 Cost table — S/M/L, dependencies, sequenceable

**Cost basis (derived):** this repo is bash workflow scripts, markdown config, and GitHub as memory,
with no server and no daemon today [I2]; Temporal is self-hosted on k3s with systemd workers, decided
2026-07-12 [I2 § *Deployment target*]. S ≈ under a day; M ≈ a few days; L ≈ a sprint or more.

| # | Component | Cost | Depends on | Do it when |
|---|---|---|---|---|
| 1 | **Write the trust model down as a standard**: the three tiers, and for each boundary, exactly what may cross it. Cite [S1][S3][S12] for the vocabulary. | **S** | nothing | **Now.** Highest value per hour in the table; also the artifact that stops the claim being re-derived wrongly, the failure [I2] already documents once. |
| 2 | **Replace `noopAuthorizer` with a namespace-scoped `Authorizer` + `ClaimMapper`; enable frontend TLS** [S25] | **M** | Temporal port exists | **Phase: Temporal Integration**, non-negotiable. The default is open [S25]. |
| 3 | **Queue / namespace naming that encodes what a worker may hold**, shaped like a SPIFFE ID path [S2] or an OIDC subject [S21] | **S** | #1 | With #2. Naming is free before workers exist and expensive after. |
| 4 | **Edge enrollment: a one-time-use join token, human-in-the-loop**, explicitly modelled on [S9] and justified by [S10][S15][S23] | **S–M** | #1 | When a second machine joins. |
| 5 | **Short-lived worker credentials + rotation**, targets anchored on SPIRE's defaults [S11] | **M** | #2, #4 | After #2. Note this *worsens* L4 on sleeping laptops — pair it with the [I5] mitigation. |
| 6 | **Federated bundle endpoint** (publish MDC trust material at a well-known HTTPS URL, `https_web` profile) [S1] | **M** | #2, and a second MDC existing | **Not until a second MDC exists.** Building a federation interface with one implementer is how the interface comes out wrong. |
| 7 | **Device-bound edge credential** (WebAuthn/DPoP/TPM) [S13][S16] | **L** | **Blocked on the credential issuer** (T1) | Cannot be sequenced until T1 answers. |
| 8 | **Hardware attestation of a laptop edge** | **L** | hardware survey (T6) | **Recommend: do not build.** Six of ten SPIRE attestors are unavailable to a laptop and the remaining four are out-of-band anyway (§5.1). Accept #4 instead. |

**The sequencing insight (derived, from the table):** items 1–4 total **S+M+S+S** and cover the
boundary that actually exists today. Items 6–8 are the ones that make the three-tier model *sound*
expensive, and all three are correctly deferred — one on a missing peer, two on missing hardware or a
missing vendor capability. **The three-tier model is cheap to *commit to* and expensive to *complete*,
and the cheap part is the part that matters this year.**

---

## 7. Honest boundary analysis — the case against this paper's own thesis

### 7.1 For the next year, tiers 2 and 3 are the same tier, and the model is over-built

There is one operator, one or two machines, one trusted LAN [I2]. The federated tier has no second
participant. **Every mechanism in §6.1 items 5–8 protects against a threat that cannot occur until a
second MDC run by a different person exists.** The nearest neighbour looked at the same problem and
chose single-operator deliberately — "assumed to be run by the same operator, on a network the
operator trusts" [I3 §0.2] — and shipped a product that is ahead of this repo on every axis but three
[I1]. **The field's sufficiency bar (§4.6) is met by a VPC, and Temporal's own documentation offers
"run unsecured instances inside of a VPC environment" as a legitimate architecture** [S25]. A reviewer
who says "you are building a federation for a fleet of two laptops" is not wrong today.

**The honest response is not to defend the mechanisms — it is to concede them and defend only item 1.**
Writing the trust model down costs S and prevents the shortcut `problem-statement.md` § *What this
means* forbids ("Nothing may assume a single operator"). Everything else waits.

### 7.2 The claim is currently a topology statement, not a security property

Nothing today prevents a federated-tier component from being handed an edge credential; the tier
boundary holds because no code crosses it. **A differentiator enforced only by the absence of code is
an intention.** Until T1/T2 answer, differentiator #1 should be worded to say what is true — the
credential is *placed* at the edge and nothing is *given* a path to it — rather than implying a
cryptographic guarantee the credential may not have.

### 7.3 The strongest analogues both weaken the differentiator, and that must be said

SPIFFE federation is a mature, adopted, CNCF-hosted specification (the `spiffe/spiffe` repository
carries 1820 stars [S7]) that already specifies the MDC↔federated boundary. Matrix has shipped a
convergent design for a decade. **"Distinct operators in distinct trust domains" is not outside the
industry's shipped scope — it is outside *bernstein's* shipped scope** [I3 §0.2]. The problem
statement's #1 is precise about naming bernstein, and it should stay precise: the differentiator is
*relative to the nearest neighbour in agent orchestration*, not relative to distributed systems. That
is a narrower claim than a casual reader takes from the current wording, and it is the true one.

### 7.4 The gap that is genuinely ours — and it may not be a good gap

**Every identity system in this sweep assumes the trust domain issues the identity it consumes.**
SPIFFE: the server mints every SVID [S3][S11]. OIDC federation: the cloud provider mints the token
after matching claims it configured [S21]. WebAuthn: the RP registers the credential [S16]. Matrix: the
homeserver holds its own signing key [S17]. **Here, the edge credential is issued by a third party to a
human, and the MDC can neither mint it, scope it, nor revoke it.** No prior art located in this sweep
addresses that asymmetry.

**But an unoccupied space is not automatically a valuable one.** The plainest reading is that nobody
built this because *federating around a per-seat consumer subscription is a business-model artifact,
not an engineering primitive* — and business-model artifacts are exactly the kind of foundation that a
vendor terms-of-service change can remove. `problem-statement.md` grounds the whole affordability
thesis on it [I1], and this paper's finding is that **the trust architecture inherits that dependency
wholesale.** That is a real, stateable risk against the thesis, not a decoration. (The ToS question
itself is owned by `raw/anthropic_tos_and_enterprise.md`, not by this paper.)

### 7.5 Where BOINC says we may be wrong about the whole framing

BOINC handles a million untrusted hosts without attesting any of them, by making the *work* verifiable
instead of the *worker* [S24]. If the results of an edge's work can be verified independently — and
[I3 §4.6] already recommends adopting evidence-hash verification of claims — **then a large part of the
edge-trust problem dissolves without any identity machinery at all.** The three-tier model may be
solving trust at the wrong layer. This paper does not resolve that; it flags it as the most interesting
counter-thesis it found, and notes that BOINC's own answer was reached after the identity-first
approach (Grid computing) had been tried and found "unlikely" to suit the case [S24].

---

## 8. Test plan — what research cannot settle

Ordered by how much downstream decision they unblock.

**T1 — Is the edge credential sender-constrained, or is it a bearer token?** *(unblocks §6.1 item 7,
§7.2, and the wording of differentiator #1)*
Inspect the credential artifact's structure and check the issuer's authorization-server metadata for
any DPoP or mTLS-bound token support [S13]. **Reads out:** whether "never leaves the machine" can ever
be a cryptographic property or is permanently a topological one.

**T2 — Does a copied credential authenticate from a second machine?** *(the decisive experiment)*
Copy the credential file to a second machine under the operator's control and attempt a run. **Reads
out:** if it works, the tier boundary is policy-only and §6.1 item 1 must say so explicitly; if it
fails, identify the binding mechanism, because that mechanism *is* the edge tier.

**T3 — What does a worker actually see with, and without, a namespace-scoped `Authorizer`?**
Stand up self-hosted Temporal with `noopAuthorizer`, enumerate what a worker on one queue can read
across namespaces, then repeat with a `ClaimMapper` + `Authorizer` and the four permission values
[S25]. **Reads out:** the concrete blast radius that §6.1 item 2 buys down, in observed API calls
rather than in principle.

**T4 — Real edge availability.** Instrument 30 days of laptop uptime/sleep against dispatch attempts.
**Reads out:** whether short-TTL credentials (§4.4) are viable here at all, or whether L4 [I5] forces a
longer-lived credential and therefore a different revocation posture.

**T5 — Operator cost of human-mediated enrollment.** Enroll one machine via a join-token-shaped flow
[S9] and measure operator-minutes end to end. **Reads out:** whether §6.1 item 4 scales past ~5
machines, which is the number at which item 8's cost starts looking justified.

**T6 — Hardware survey.** Determine, per machine in the fleet, whether a TPM 2.0 or platform secure
element is present and whether an LDevID provisioning path exists at all [S10][S16]. **Reads out:**
whether L3/L8 are "expensive" or "impossible" for this fleet. Research cannot answer this; only the
hardware can.

**T7 — Bundle-endpoint round trip between two trust domains.** Cannot be run until a second MDC exists.
**Explicitly deferred, with the reason recorded** so a future cycle does not mistake it for an untried
idea.

**T8 — Does work-verification substitute for worker-trust?** Take one workflow, apply the
evidence-hash verification pattern [I3 §4.6], and assess whether the edge's identity still needed to be
trusted for that workflow's result to be usable. **Reads out:** whether §7.5's counter-thesis is
actionable or merely interesting.

---

## 9. Citations

**External — all raw sources. Every fetch in this cycle was `raw.githubusercontent.com`,
`api.github.com` JSON, an IETF `.txt` RFC, or a PDF read directly. No rendered HTML page was fetched.**

- **[S1]** SPIFFE Federation specification. `https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE_Federation.md`
- **[S2]** SPIFFE ID specification. `https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE-ID.md`
- **[S3]** SPIFFE Trust Domain and Bundle specification. `https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE_Trust_Domain_and_Bundle.md` — *note: the phrase "administrative and/or security boundaries" was returned attributed to the abstract; its full enclosing sentence was not returned, and it is quoted here as a fragment only.*
- **[S4]** SPIFFE X.509-SVID specification. `https://raw.githubusercontent.com/spiffe/spiffe/main/standards/X509-SVID.md`
- **[S5]** SPIFFE Broker API specification (self-declared "Stability: Incubating"). `https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE_Broker_API.md` — *directional only; cited for the existence of a brokered-issuance direction, not relied on for any claim.*
- **[S6]** `spiffe/spiffe` `standards/` directory listing (GitHub contents API). `https://api.github.com/repos/spiffe/spiffe/contents/standards`
- **[S7]** `spiffe/spiffe` repository metadata; `default_branch` = `main`, `stargazers_count` = 1820. `https://api.github.com/repos/spiffe/spiffe`
- **[S8]** `spiffe/spire` `doc/` directory listing (GitHub contents API) — the enumerated population for §5.1. `https://api.github.com/repos/spiffe/spire/contents/doc`
- **[S9]** SPIRE `join_token` agent node attestor. `https://raw.githubusercontent.com/spiffe/spire/main/doc/plugin_agent_nodeattestor_jointoken.md`
- **[S10]** SPIRE `tpm_devid` agent node attestor. `https://raw.githubusercontent.com/spiffe/spire/main/doc/plugin_agent_nodeattestor_tpm_devid.md`
- **[S11]** SPIRE server configuration reference (TTL defaults, `agent ban` / `agent evict`). `https://raw.githubusercontent.com/spiffe/spire/main/doc/spire_server.md`
- **[S12]** RFC 8693, *OAuth 2.0 Token Exchange*. `https://www.rfc-editor.org/rfc/rfc8693.txt`
- **[S13]** RFC 9449, *OAuth 2.0 Demonstrating Proof of Possession (DPoP)*. `https://www.rfc-editor.org/rfc/rfc9449.txt`
- **[S14]** RFC 9334, *Remote ATtestation procedureS (RATS) Architecture*. `https://www.rfc-editor.org/rfc/rfc9334.txt`
- **[S15]** RFC 7030, *Enrollment over Secure Transport (EST)*. `https://www.rfc-editor.org/rfc/rfc7030.txt`
- **[S16]** W3C Web Authentication (WebAuthn), specification source (`index.bs`, Bikeshed markup — the `[=...=]` term syntax in the quoted spans is the raw source's own). `https://raw.githubusercontent.com/w3c/webauthn/main/index.bs`
- **[S17]** Matrix Specification, Server-Server API. `https://raw.githubusercontent.com/matrix-org/matrix-spec/main/content/server-server-api.md`
- **[S18]** Slurm federated scheduling documentation. `https://raw.githubusercontent.com/SchedMD/slurm/master/doc/html/federation.shtml` — *default branch `master`; the raw fetch resolved, so the negative finding in §3.5 rests on a successful fetch, not on a 404.*
- **[S19]** Istio deployment models documentation source. `https://raw.githubusercontent.com/istio/istio.io/master/content/en/docs/ops/deployment/deployment-models/index.md`
- **[S20]** Kubernetes KEP-1645, *Multi-Cluster Services API*. `https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/sig-multicluster/1645-multi-cluster-services-api/README.md`
- **[S21]** GitHub Actions — OpenID Connect concept documentation source. `https://raw.githubusercontent.com/github/docs/main/content/actions/concepts/security/openid-connect.md`
- **[S22]** HashiCorp Vault Enterprise namespaces documentation source (v1.20.x). `https://raw.githubusercontent.com/hashicorp/web-unified-docs/main/content/vault/v1.20.x/content/docs/enterprise/namespaces/index.mdx`
- **[S23]** Donenfeld, J. A., *WireGuard: Next Generation Kernel Network Tunnel* (draft revision e2da747, dated June 1 2020; a version appears in *Proceedings of NDSS 2017*). `https://www.wireguard.com/papers/wireguard.pdf` — **PDF read directly, pages 1–5.**
- **[S24]** Anderson, D. P., *BOINC: A System for Public-Resource Computing and Storage*, Space Sciences Laboratory, UC Berkeley (published at IEEE/ACM GRID 2004). `https://boinc.berkeley.edu/grid_paper_04.pdf` — **PDF read directly, pages 1–8.**
- **[S25]** Temporal self-hosted security documentation source. `https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/security.mdx`

**Internal (this repo — evidence, non-binding):**

- **[I1]** `docs/standards/architecture/problem-statement.md`
- **[I2]** `docs/standards/architecture/system-overview.md`, incl. § *Deployment target*
- **[I3]** `docs/standards/architecture/research/raw/bernstein_capability_mining.md`
- **[I4]** `docs/standards/architecture/research/raw/dedicated_edge_routing.md`
- **[I5]** `docs/standards/architecture/research/raw/fleet_failure_modes.md`

**Source count: 25 external (all raw/first-party) + 5 internal.** Above the §3 band of 10–20,
deliberately: the topic spans four distinct literatures (workload identity, federated protocols,
volunteer computing, device-bound credentials) and narrowing to 20 would have meant dropping one of
them.

**Sources sought and NOT obtained, with method:** Apple's *Platform Security* guide was fetched as a
PDF (`help.apple.com/pdf/security/en_US/apple-platform-security-guide.pdf`, 2.9 MB) but not paged
through in this cycle; no Secure Enclave claim is made anywhere in this paper as a result. The
WebAuthn non-extractability property [S16] carries that argument instead. TCG TPM specifications were
not fetched.
