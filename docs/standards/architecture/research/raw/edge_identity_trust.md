# Multi-edge identity, trust and credential distribution

```
Topic:          How is work authorised across trust boundaries when the worker is somebody
                else's machine — how do comparable systems distribute and scope credentials
                across those boundaries, what breaks when the edge is a laptop, and has anyone
                published a design where a federated layer dispatches work it cannot itself
                authenticate to perform?
Feeds:          standards/architecture/problem-statement.md § "Where we actually differ" #1
                (the three-tier trust model) and § "The edges";
                Phase: Temporal Integration — worker identity and credential locality.
Last validated: 2026-08-06
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE (first-party documented, raw-source verified): the SPIFFE trust-domain
                and federation model; the SPIRE node-attestor catalogue; RFC 8693 / 9449 / 9334 /
                8628 semantics; NIST SP 800-207 tenets; BeyondCorp's managed-device requirement;
                GitHub's and GitLab's self-hosted-runner security guidance; Temporal's self-hosted
                default authorizer, namespace semantics, multi-tenant patterns, data-converter
                placement, and the pull-based Worker/Task-Queue polling model.
                DERIVED (this paper's inference across those sources, flagged inline): the tier
                mapping table (§3), the verdict on differentiator #1 (§7), the "why nobody built
                it" analysis (§6.3), and the Temporal task-queue-binding gap (§2.8).
                DIRECTIONAL: arXiv 2504.14760 (single-author preprint, not peer-reviewed).
                REDUCED (rendered page, not raw): HashiCorp Vault response-wrapping; Anthropic
                Consumer Terms — the latter corroborated by an existing pool paper.
                UNVERIFIED / GAPS: whether any agent orchestrator ships subscription-at-edge with
                cross-machine dispatch (§6.2); Temporal Nexus cross-namespace authorization (§2.8);
                whether Temporal can bind a task queue to an attested worker identity (§2.8);
                Temporal's redelivery behaviour for a Task already dispatched to a worker that then
                sleeps or disconnects (§5 row 1, §9 item 11 — not researched, not assumed).
Critic:         PASS at round 2 (2026-08-06) and still standing: the round-3 correction was
                confirmed, and a round-4 repair to the §5 credential-expiry row's dangling
                search-method pointer was independently re-verified with no blocking findings —
                every round on the same date.
                Round 1 checked all 32 original citations, found every one existing and correctly
                cited with no fabricated source, judged the confidence marks correctly calibrated,
                and raised two defects. Both were repaired: a misquoted Codec Server definition
                span in §2.8 Finding 3 (the paper had "decode your encoded payloads remotely",
                a conflation of two adjacent sentences; the source reads "decode your data
                remotely"), and the pull-based Worker/Task-Queue polling premise (§2.7, §3, §4 #7,
                §5, §7), which had no source behind it and is now cited to first-party Temporal
                encyclopedia docs [S33][S34].
                Round 2 re-verified those repairs against its own fetches and returned PASS: both
                corrected [S24] spans character-exact, [S33] and [S34] resolving with every quoted
                span matching the raw source at each of the five sites claiming it, and the
                34-source list reconciled by enumeration with no orphans in either direction.
                Round 3 (this pass) fixed the one factual defect round 2 flagged as non-blocking:
                the §2.8 repair note left the impression that its four agreeing fetches had settled
                the quoted sentence's wording as unique in the source. A fresh four-fetch
                enumeration of that document found a near-identical sibling sentence two paragraphs
                below it. The quoted span itself is unchanged and re-confirmed exact; the note now
                records the sibling and the enumerate-before-quoting remedy. No other section of
                the paper was touched in round 3.
                Round 4 (2026-08-06) repaired a §3 conformance defect in the §5 table: the
                credential-expiry row — the table's only UNSOLVED verdict — sent readers to §8 for
                its search method, but §8 is the source list and describes no method for it, so the
                paper's strongest negative claim was effectively unmethodized and a reader could not
                tell "we looked and found nothing" from "we did not look". The pointer now carries
                an inline method, deliberately limited to what this artifact can actually evidence:
                the corpora are named from the row's own citations plus the synthesis's matching
                characterisation, and the cell says outright that the queries were not recorded and
                cannot be recovered. No method was reconstructed or inferred; the row's verdict and
                evidence column are unchanged, as is every other row and section.
```

**Mixed-volatility notice (per Research Standard §3).** This paper spans two decay rates. The
header takes the highest tier present. Sections marked **[LOW]** — §1, §2.1–2.7, §4, and §5
*except the rows cited below* — rest on RFCs, NIST publications, peer-reviewed and archival papers,
and versioned protocol specs; a refresh may skip re-verifying them absent a spec revision. Sections
marked **[HIGH]** — §2.8 (Temporal's auth surface), §2.6 (CI-runner vendor guidance), §6.2 (the
agent-category negative finding), the Anthropic-terms citation in §6.3, **and the three §5 rows
resting on [S26]/[S28] CI-runner guidance — including the table's only `UNSOLVED` verdict** — are
product/vendor surfaces and are the reason for the 6-week interval.

**Why §5 is split rather than tiered whole.** Its self-hosted-runner rows cite the same CI-vendor
guidance this notice already classes `[HIGH]`. Leaving them under `[LOW]` would tell a refresh to
skip re-verifying precisely the claims the paper says decay fastest — and differentiator #1's
costing rests on one of them. The fast-moving material is roughly a quarter of the paper, below the ~one-third threshold
at which §3 prefers a split; **if §2.8 grows past a page, split it into a `temporal_auth_surface.md`
paper and drop this one to medium.**

---

## §0 Bottom line up front

**Differentiator #1 survives as a correct design and does not survive as a novelty — and the claim
that replaces it is stronger.**

Three findings, in order of how much they change the architecture:

1. **The three-tier topology is a shipped, specified, named thing.** "Administratively isolated
   trust domains that exchange only public key material, so a foreign domain can *validate*
   identities it cannot *issue*" is the SPIFFE Federation specification, near-verbatim [S1][S2].
   The Edge/MDC/Federated table is workload-identity federation with different nouns. Stating it as
   an invention would not survive first contact with a reviewer who knows SPIFFE.

2. **What IS unusual is not the topology but the credential.** SPIFFE, OIDC federation, Vault,
   Kubernetes and every cloud workload-identity product assume the credential at the edge is
   **mintable by an authority inside one of the tiers** — that is the whole mechanism. Here the
   edge credential is a per-person consumer subscription minted by a fourth party (Anthropic),
   which the edge cannot attenuate, cannot delegate, cannot present a proof-of-possession for on
   the backbone's behalf, and is **contractually forbidden from sharing** [S30][S32]. The topology
   is therefore *forced*, not *chosen*. That is the defensible claim, and it explains §6.3's
   "why has nobody built this."

3. **The prior art's loudest verdict on this shape is a warning, not a blueprint.** The closest
   operational analogue to "a federated layer dispatches work onto a machine holding a credential
   the dispatcher does not have" is a self-hosted CI runner — and GitHub's own guidance is that a
   self-hosted runner "should almost never be used for public repositories" and "can be persistently
   compromised by untrusted code in a workflow" [S26], with GitLab corroborating that anyone with
   the Developer role "could compromise the security of the environment hosting the runner" [S28].
   Cross-operator dispatch onto a participant's laptop is structurally the configuration both
   vendors tell you not to run. **This does not refute the trust model; it prices it**, and the
   price is ephemeral, isolated execution at the edge — which a laptop is bad at.

---

## §1 Primer — the vocabulary this problem already has **[LOW]**

The question "how is work authorised when the worker is somebody else's machine" has four decades
of prior art under names that are not "agent orchestration." The load-bearing distinctions:

**Trust domain.** *"A SPIFFE trust domain is an identity namespace which is backed by an issuing
authority with a set of cryptographic keys"* [S2] (*definitive*). Each domain *"acts in its own
capacity, under its own authority, and is administratively isolated from systems residing in other
trust domains"* [S1] (*definitive*). This is the exact unit the problem statement calls a "tier."

**Attestation vs. authentication.** Authentication proves possession of a credential. Attestation
proves something about the *machine* before a credential is issued to it. RFC 9334 names the roles:
an **Attester** is *"A role performed by an entity (typically a device) whose Evidence must be
appraised in order to infer the extent to which the Attester is considered trustworthy"*; a
**Verifier** *"appraises the validity of Evidence about an Attester and produces Attestation Results
to be used by a Relying Party"*; a **Relying Party** *"depends on the validity of information about
an Attester for purposes of reliably applying application-specific actions"* [S10] (*definitive*).
The split matters here: the federated tier is a Relying Party that must not become an issuing
authority.

**Bearer vs. sender-constrained credential.** A bearer token authorises whoever holds it — so it
must never transit a party you do not trust. A sender-constrained token is bound to a key the holder
proves possession of; RFC 9449 states the consequence plainly: *"If the private key is
non-extractable (as is possible with [W3C.WebCryptoAPI]), DPoP renders exfiltrated tokens alone
unusable"* [S8] (*definitive*). This is the cryptographic form of "the credential never leaves the
machine."

**Impersonation vs. delegation.** RFC 8693: *"When principal A impersonates principal B, A is given
all the rights that B has within some defined rights context and is indistinguishable from B in that
context"*; whereas *"With delegation semantics, principal A still has its own identity separate from
B, and it is explicitly understood that while B may have delegated some of its rights to A, any
actions taken are being taken by A representing B"* [S7] (*definitive*). Differentiator #2's
surviving form — "no label grants one edge the ability to authenticate as another subscriber" — is
precisely a prohibition on *impersonation*; it says nothing about delegation, which is the open
design space.

**Zero trust.** NIST's operative definition: *"Zero trust (ZT) provides a collection of concepts and
ideas designed to minimize uncertainty in enforcing accurate, least privilege per-request access
decisions in information systems and services in the face of a network viewed as compromised"*
[S11] (*definitive*). Tenet 2 is the one this architecture leans on: *"All communication is secured
regardless of network location. Network location alone does not imply trust"* [S11].

---

## §2 The specific models the landscape actually offers **[LOW except §2.6, §2.8]**

For each: how identity is established, how it is scoped, what crosses the boundary, what does not.

### 2.1 SPIFFE / SPIRE — the closest published analogue to the three-tier model **[LOW]**

*Identity established by:* a two-stage attestation. Node attestation binds an agent to a machine;
workload attestation binds a process to an identity. The Workload API deliberately requires no
secret from the caller: *"The SPIFFE Workload API is typically exposed locally (eg. via a Unix domain
socket), and explicitly does not include an authentication handshake or authenticating token from
the workload. Implementors can verify the authenticity of the caller to the Workload API via an
out-of-band method, such as inspecting the properties of the process calling the Unix domain socket
that are provided by the operating system"* [S3] (*definitive*). **This is the single most
transferable design in this paper**: the edge worker should not carry a bootstrap secret; it should
be identified by properties of the process, out of band.

*Scoped by:* a SPIFFE ID URI (trust domain + path) carried in an SVID [S3].

*What crosses a trust boundary:* **only public key material.** *"SPIFFE Federation enables the
authentication of identity credentials (SVIDs) across trust domains. Specifically, it is the act of
obtaining the necessary SPIFFE bundle(s) to authenticate SVIDs issued by a different trust
domain"* [S1]; *"A SPIFFE bundle is an object containing a trust domain's cryptographic keys"* [S2];
and the relationship is directional — federation relationships are *"one-way"*, so *"Alice could
have a relationship with Bob but not vice versa"* [S1] (all *definitive*). SPIRE implements this as
a bundle endpoint plus a `federates_with` list: *"Configuring a federated trust domain allows a trust
domain to authenticate identities issued by other SPIFFE authorities, allowing workloads in one trust
domain to securely authenticate workloads in a foreign trust domain"* [S6] (*definitive*).

*What explicitly does not cross:* private keys, and issuance authority. A federated domain can
**verify** and cannot **mint**. **That is the "Federated tier holds no edge credential" property,
already specified, already implemented.**

*The laptop problem, in SPIRE's own catalogue.* Enumerating the agent-side node-attestor plugin
docs in the SPIRE repository [S4] gives exactly ten: `aws_iid`, `azure_imds`, `azure_msi`,
`gcp_iit`, `http_challenge`, `jointoken`, `k8s_psat`, `sshpop`, `tpm_devid`, `x509pop` — **10
documented plugins, counted by enumerating that list** (caveat: this counts *documented* plugins in
`doc/`, which may differ from what is compiled in; the population enumerated is the doc directory,
not the binary). Four require a cloud instance-identity document, one requires a Kubernetes
projected token, one requires a TPM, three require a pre-provisioned secret or certificate, and one
is an HTTP challenge. For a participant-owned laptop, the only options are the pre-provisioned or
one-time-secret ones — and SPIRE describes `join_token` as *"responsible for attesting the agent's
identity using a one-time-use pre-shared key"* [S5] (*definitive*). **Derived from [S4]+[S5]:
SPIRE's attestation story degrades, on an unmanaged laptop, to "someone typed a secret in once" —
the same trust-on-first-use it replaces everywhere else.**

### 2.2 Token exchange, OIDC federation and short-lived credentials **[LOW]**

RFC 8693 supplies the vocabulary for narrowing authority across a boundary: an `actor_token` is
*"A security token that represents the identity of the acting party. Typically, this will be the
party that is authorized to use the requested security token and act on behalf of the subject"*, and
the `may_act` claim *"makes a statement that one party is authorized to become the actor and act on
behalf of another party"* [S7] (*definitive*). This is the standards-track way to express "SkyyNet
may cause work to run as this edge" **without** SkyyNet holding the edge's credential.

The shipped mass-market instance is CI→cloud OIDC federation. GitHub's own framing: hardcoded
secrets *"requires you to create credentials in the cloud provider and then duplicate them in
[GitHub] as a secret"*; instead *"You establish an OIDC trust relationship in the cloud provider,
allowing specific [GitHub] workflows to request cloud access tokens on behalf of a defined cloud
role"*, after which *"your cloud provider issues a short-lived access token that is only valid for a
single job, and then automatically expires"* [S27] (*definitive*). **The dispatcher holds a signing
key, not the target credential.** Kubernetes does the same internally: *"The TokenRequest API
produces bound tokens for a ServiceAccount. This binding is linked to the lifetime of the client,
such as a Pod, that is acting as that ServiceAccount"* [S17], contrasted with the pre-1.22 model that
*"provides a long-lived, static token to the Pod as a Secret"* [S17] (*definitive*).

RFC 8628's device authorization grant is the acquisition-side analogue: it exists for devices that
*"lack a browser to perform a user-agent-based authorization or are input constrained"*, and works by
having *"the device client instruct[] the end user to use another computer or device and connect to
the authorization server to approve the access request"* [S9] (*definitive*). **This is the shape a
headless edge worker uses to get its own credential with a human present exactly once.**

### 2.3 Zero trust: NIST SP 800-207 and BeyondCorp **[LOW]**

NIST's tenets that bear on this design, verbatim [S11] (*definitive*):

- *"All communication is secured regardless of network location. Network location alone does not
  imply trust."* — the MDC tier being "the local trusted network" is, by this tenet, not a security
  property.
- *"Access to individual enterprise resources is granted on a per-session basis."*
- *"Devices on the network may not be owned or configurable by the enterprise."* (Assumption 2)
- *"Remote enterprise subjects and assets cannot fully trust their local network connection."*
  (Assumption 5)
- *"No resource is inherently trusted."* … *"Subject credentials alone are insufficient for device
  authentication to an enterprise resource."* (Assumption 3)

And the boundary NIST draws around its own applicability, which is directly relevant to a
cross-operator federation: *"These tenets apply to work done within an organization or in
collaboration with one or more partner organizations and not to anonymous public or consumer-facing
business processes. An organization cannot impose internal policies on external actors"* [S11]
(*definitive*). **SkyyNet's federated tier is on the boundary of that carve-out**: participants are
neither one organization's employees nor anonymous public.

BeyondCorp is the deployed instance, and its premise is the same as this repo's — *"We are removing
the requirement for a privileged intranet and moving our corporate applications to the Internet"*,
so that *"access depends solely on device and user credentials, regardless of a user's network
location"* [S12] (*definitive*). **But its device story is the exact opposite of an edge laptop**:
*"BeyondCorp uses the concept of a 'managed device,' which is a device that is procured and actively
managed by the enterprise. Only managed devices can access corporate applications"*, with the device
certificate *"stored on a hardware or software Trusted Platform Module (TPM) or a qualified
certificate store"* — and even then, *"While the certificate uniquely identifies the device, it does
not single-handedly grant access privileges"* [S12] (*definitive*). See §5.

### 2.4 Delegation credentials: macaroons **[LOW]**

The macaroons paper introduces *"flexible authorization credentials for Cloud services that support
decentralized delegation between principals"* [S13]. The mechanism is caveats: *"Macaroons allow
authority to be delegated between protection domains with both attenuation and contextual
confinement"*, where *"such caveats may attenuate a macaroon by limiting what objects and what
actions it permits, or contextually confine it by requiring additional evidence, such as third-party
signatures, or by restricting when, from where, or in what observable context it may be used"* [S13]
(*definitive*, peer-reviewed NDSS'14).

**Why it matters here:** macaroons are the published answer to "hand a downstream party *less*
authority than you hold, offline, without contacting the issuer." The federated tier handing an MDC
a narrowed capability is exactly this shape. It is also the technique bernstein's
"delegation-narrowing receipts" item gestures at [S31]. It does **not** solve our core problem —
macaroons assume you hold a credential you may attenuate; the edge subscription is not attenuable.

### 2.5 Credentials that structurally cannot be moved: WebAuthn, DPoP, Sigstore **[LOW]**

WebAuthn is the mass-deployed case of a credential that the relying party structurally cannot
possess: *"The credential private key is bound to a particular authenticator - its managing
authenticator - and is expected to never be exposed to any other party, not even to the owner of the
authenticator"* [S16] (*definitive*; quoted from the specification's Bikeshed source, with inline
`[=term=]` markup elided). The relying party stores only the public key and can *request an
assertion* it cannot manufacture. **This is the cleanest existing statement of "the dispatcher can
cause an action it cannot itself perform."**

Sigstore's Fulcio inverts the durability axis instead: *"Fulcio is a free-to-use certificate
authority for issuing code signing certificates for an OpenID Connect (OIDC) identity, such as email
address"* and *"Fulcio only issues short-lived certificates that are valid for 10 minutes"* [S19]
(*definitive*). Where a key cannot be pinned to hardware, make it worthless quickly.

### 2.6 Distributed CI — the closest *operational* analogue, and a warning **[HIGH]**

A self-hosted CI runner is a machine, owned by someone, holding real credentials, executing job
definitions authored elsewhere. That is the SkyyNet edge, minus the federation. The published
guidance is unusually blunt.

GitHub [S26] (*definitive*):
- *"Self-hosted runners should almost never be used for public repositories on GitHub, because any
  user can open pull requests against the repository and compromise the environment."*
- *"Anyone who can fork the repository and open a pull request (generally those with read access to
  the repository) are able to compromise the self-hosted runner environment, including gaining
  access to secrets and the `GITHUB_TOKEN`."*
- *"Self-hosted runners for GitHub do not have guarantees around running in ephemeral clean virtual
  machines, and can be persistently compromised by untrusted code in a workflow."*
- *"Some jobs will use secrets as command-line arguments which can be seen by another job running on
  the same runner, such as `ps x -w`. This can lead to secret leaks."*

GitLab corroborates independently [S28] (*definitive*): *"Any user that has the Developer role for
the project's repository could compromise the security of the environment hosting the runner,
whether intentional or not"*; and on the executor an agent edge most resembles: *"High-security risks
exist to your runner host and network when running builds with the `shell` executor. The jobs are run
with the permissions of the GitLab Runner's user and can steal code from other projects that are run
on this server. Use it only for running trusted builds."*

**DERIVED, from [S26]+[S28]:** the entire mitigation both vendors converge on is *ephemerality and
isolation per job* — a clean VM per run, no persistent state, no shared host. A participant's laptop
running `claude -p` against a real repository under a real subscription is the **anti-pattern by
construction**: persistent, shared with the human's own work, and holding a credential that cannot
be re-minted per job. This is the highest-value finding in the paper for planning, and it is a cost,
not a refutation.

### 2.7 Brokers, pull models, mesh identity, and volunteer compute **[LOW]**

**Secret broker.** Vault's response wrapping is the canonical "hand a secret through an untrusted
intermediary" primitive: *"When requested, Vault can take the response it would have sent to an HTTP
client and insert it into the cubbyhole of a single-use token, returning that single-use token
instead"*, providing *"cover"*, *"malfeasance detection by ensuring that only a single party can ever
unwrap the token"*, and lifetime limitation because *"the response-wrapping token has a lifetime that
is separate from the wrapped secret"* [S29] (**reduced confidence — rendered page, not raw; the
Vault product docs are no longer in the `hashicorp/vault` git tree, see §8 gap note**).

**Pull instead of push.** The OpenGitOps principles state it as a first principle: *"Software agents
automatically pull the desired state declarations from the source"* and *"Software agents
continuously observe actual system state and attempt to apply the desired state"* [S18]
(*definitive*). **Derived:** the pull model is the cheapest structural way to keep a credential
inside a boundary — the agent inside the boundary reaches out; nothing outside needs an inbound path
or a credential.

Temporal's worker model is itself a pull model, and this is first-party documented rather than
folklore: *"A Worker Process is responsible for polling a Task Queue, dequeueing a Task, executing
your code in response to a Task, and responding to the Temporal Service with the results"* and
*"A Worker Entity listens and polls on a single Task Queue"* [S33]; *"A Task Queue is a lightweight,
dynamically allocated queue that one or more Worker Entities poll for Tasks"* and *"Workers poll for
Tasks in Task Queues via synchronous RPC"* [S34] (all *definitive*). Temporal draws the reachability
consequence itself: *"Worker Processes connect directly to the Temporal Service for secure
communication without needing to open exposed ports"* [S34] (*definitive*). **Derived from
[S18]+[S33]+[S34]: the pull property this design needs at the edge is obtained for free from the
substrate already chosen** — the dispatcher never initiates a connection to the edge, so no inbound
path, no stable address, and no dispatcher-held edge credential are required for dispatch to work.

**Mesh identity.** WireGuard reduces peer identity to a key: *"In WireGuard, peers are identified
strictly by their public key, a 32-byte Curve25519 point"*, with *"an association between a peer
public key and a tunnel source IP address"* and *"Short pre-shared static keys—Curve25519 points—are
used for mutual authentication in the style of OpenSSH"* [S14] (*definitive*, NDSS'17 / archival
paper). No PKI, no CA, no rotation story — the cost is that key distribution is your problem, which
is precisely the problem SPIFFE exists to solve.

**Volunteer computing — the only prior art that fully accepts an uncontrolled edge.** BOINC states
the position without hedging: *"Projects have no control over participants, and cannot prevent
malicious behavior"* [S15]; participants are *"individuals who own Windows, Macintosh and Linux PCs,
connected to the Internet by telephone or cable modems or DSL, and often behind network-address
translators (NATs) or firewalls. The computers are frequently turned off or disconnected from the
Internet"* [S15]; and *"public-resource computing involves an asymmetric relationship between
projects and participants"* [S15] (all *definitive*, archival paper). **BOINC's answer is to hold no
participant credential at all and to verify results by redundant computation** — which does not
transfer to work whose output is not deterministically comparable, i.e. to agent output.

### 2.8 Temporal's actual authorisation surface, self-hosted **[HIGH — direct build consequence]**

This section assesses **self-hosted only**; Temporal Cloud is out of scope per
`system-overview.md` § *Deployment target*.

**Finding 1 — the default is open.** *"If you do **not** explicitly configure an `Authorizer`,
Temporal uses the default `noopAuthorizer`."* and *"This default allows **every** API request, with
no authentication or access control."* [S21] (*definitive*; re-verified by a second targeted fetch
against the raw `.mdx`, which returned both sentences with markdown emphasis intact). Two pluggable
interfaces exist: *"The Claim Mapper component is a pluggable component that extracts Claims from
JSON Web Tokens (JWTs)"* and *"The `Authorizer` plugin contains a single Authorize method, which is
invoked for each incoming API call"* [S21]. **Build consequence: authorisation on a self-hosted
Temporal is something we write, not something we configure.**

**Finding 2 — a namespace is an isolation unit whose security depends on you.** The self-hosted docs
define it minimally: *"A Namespace is a unit of isolation within the Temporal Platform"* [S23]
(*definitive*), with **no statement in that file about it being a security boundary** (negative
finding; search method: fetched the raw `namespaces.mdx` and asked explicitly for any isolation,
security-boundary or limitation statement, and for an explicit "not present" answer).
`multi-tenant-patterns.mdx` is where the security semantics actually live and it is precise: the
namespace-per-tenant pattern *"is usually chosen when tenant boundaries also need to be credential
boundaries"*, whereas *"Shared Namespace with per-tenant Task Queues: Best for scale and operational
simplicity, but tenant isolation is mostly enforced by your application and worker routing logic
rather than by Temporal credentials"* [S22] (*definitive*; both spans re-verified by a second
targeted fetch that searched for the exact phrases). **Answer to the dispatch's precise question: a
namespace is the only place Temporal offers to put a credential boundary, but it is administrative
by default and becomes a trust boundary only when a ClaimMapper + Authorizer make it one.**

**Finding 3 — payload confidentiality across the trunk is already solved.** *"With encryption
enabled, data exists unencrypted only on the Client and the Worker process, on hosts that you
control"*, and *"Payloads on the Temporal Service (whether on Temporal Cloud or self-hosted) remain
encrypted"*; a Codec Server is *"an HTTP server that uses your custom Codec logic to decode your data
remotely"* whose output is *"decoded and returned on the client side only"*, and *"You create,
operate, and manage access to your Codec Server in your own environment"* [S24] (*definitive*).
**This is a direct win for the federated tier**: the trunk can carry work whose inputs and outputs it
cannot read, using a shipped, documented mechanism. It is the strongest single piece of substrate
support for differentiator #1 found in this cycle.

> **Repair note (2026-08-06, critic round 1 — a repaired span is a new claim, §3).** The Codec
> Server definition sentence above previously read *"…to decode your encoded payloads remotely"*.
> That was a conflation of two adjacent sentences in [S24]: the definition sentence
> (*"A Codec Server is an HTTP server that uses your custom Codec logic to decode your data
> remotely."*) and the sentence preceding it (*"Use a Codec Server to programmatically decode your
> encoded payloads."*, which carries an inline markdown link on *payloads*). The critic reported
> that its own fetches of this URL returned differing renderings of the passage and could neither
> confirm nor refute the wording. **Re-verification method:** four fetches of the raw `.mdx` — three
> against the `main` raw URL under three different prompt shapes (enumerate-all-Codec-Server-
> sentences; reproduce-these-two-sentences; reproduce-the-whole-defining-section) and one against
> the `HEAD` raw URL to obtain a cache-independent retrieval. All four returned the definition
> sentence and the *"in your own environment"* sentence identically, in the wording now quoted
> above — which establishes agreement on the *wording of those two sentences*, and **not** that either
> wording is unique in the document; see the round-3 addendum below. The two spans are treated as
> certifiably verbatim and retain the *definitive* mark. **Neither span is load-bearing for the finding itself**: Finding 3's claim — that the
> Temporal Service never holds decrypted payloads — rests on the two *"unencrypted only on the
> Client and the Worker process"* / *"remain encrypted"* spans, which reproduced identically across
> every fetch by both the analyst and the critic. The Codec Server spans establish only *where the
> decode capability lives*, which reinforces the finding rather than carrying it.

> **Round-3 addendum (2026-08-06) — the source contains a near-duplicate sibling sentence, and that
> is the actual failure class.** A round-3 enumeration of `data-encryption.mdx` — four fresh fetches,
> three prompt shapes against the `main` raw URL (every sentence containing "environment"; every
> sentence containing "Codec Server"; verbatim reproduction of the contiguous block spanning both)
> and one against the `HEAD` raw URL — found a **second sentence carrying a near-identical phrase**,
> a few lines below the one quoted in Finding 3: *"Because you create, operate, and manage access to
> your Codec Server in your controlled environment, ensure that you consider the following:"* Every
> round-3 fetch that was asked to enumerate returned this sentence with identical characters, and the
> contiguous-block fetch places it two paragraphs after *"You create, operate, and manage access to
> your Codec Server in your own environment."* **The span quoted in Finding 3 is the *own
> environment* sentence; it is unchanged, still character-exact, and still correctly attributed.**
> What was wrong was the round-1 note's implicature that four agreeing fetches had settled the
> passage — they settled a *wording*, not its *uniqueness*, and a reader was entitled to take the
> stronger reading. Correcting that is the whole of this round's change.
>
> **What this changes about the lesson.** This document contains **two** near-duplicate Codec Server
> sentence pairs, not one: the *own / controlled environment* pair above, and the
> *"Use a Codec Server to programmatically decode your encoded payloads."* /
> *"…uses your custom Codec logic to decode your data remotely."* pair named in the round-1 note.
> The round-1 defect — *"decode your encoded payloads remotely"* — is exactly a concatenation of the
> second pair's two halves, so for **that** pair, a summarizing fetch layer blending near-duplicate
> siblings is **demonstrated, not hypothesised**. For the *environment* pair the same mechanism is
> **plausible but not directly observed**: this paper cannot inspect what the round-1 critic's
> fetches returned, and does not claim to have reproduced that blend. **Stated as one instance, not
> a general law:** where a source contains near-duplicate siblings, re-fetching harder is the wrong
> remedy, because every retrieval can return the same stable blend and agreement then certifies
> nothing. The remedy that works is to **enumerate every occurrence of the distinctive phrase before
> quoting one of them** — which round 3 did and rounds 1 and 2 did not.
>
> **A second, smaller fetch-layer defect observed while doing this.** Two of the three filtered
> enumerations returned items that do **not** contain the string they were asked to filter on —
> seven spurious items in one, one in the other — and one of the two appended its own corrective
> note narrowing the list afterwards. Both true matches appeared in every enumeration that asked for
> them, so over-inclusion rather than omission was the failure direction *here*; four fetches of one
> document cannot establish that omission does not also occur. Operational consequence: check each
> enumerated item for the literal string yourself rather than trusting the layer's filter.

**Gap 1 — task-queue-to-worker binding is not documented as a Temporal mechanism.** Nothing in
[S21][S22][S23] states a way to restrict *which worker process may poll a given task queue* by
attested identity. `multi-tenant-patterns.mdx` positively implies the opposite for shared namespaces
(isolation is *"enforced by your application and worker routing logic"* [S22]). **Derived, and
flagged as derived:** because `Authorize` *"is invoked for each incoming API call"* [S21], a custom
Authorizer could in principle gate `PollWorkflowTaskQueue`/`PollActivityTaskQueue` on caller claims
plus target task queue — but **no first-party document was found describing this**, so it is a design
hypothesis for the test plan (§9), not a documented capability. Search method: fetched raw
`security.mdx`, `namespaces.mdx`, `multi-tenant-patterns.mdx`, and enumerated two directories via
the GitHub contents API [S25]. `docs/production-deployment/` returned `data-encryption.mdx`,
`index.mdx`, `multi-tenant-patterns.mdx`, `self-hosted-guide`, `temporal-proxy`,
`worker-deployments` — **6 names, counted from that enumeration**. Its `self-hosted-guide`
subdirectory returned `archival.mdx`, `checklist.mdx`, `defaults.mdx`, `deployment.mdx`,
`embedded-server.mdx`, `index.mdx`, `monitoring.mdx`, `multi-cluster-replication.mdx`,
`namespaces.mdx`, `security.mdx`, `server-frontend-api-reference.mdx`, `temporal-nexus.mdx`,
`upgrade-server.mdx`, `visibility.mdx` — **14 names, counted from that enumeration**. No entry in
either listing addresses worker-to-task-queue binding.

**Gap 2 — Nexus authorization across namespaces is not established.** `temporal-nexus.mdx` was
fetched raw and yielded operational statements (*"When using Nexus for cross namespace calls, the
URL's host is irrelevant as the address is resolved using membership"*) but **no** access-control or
trust statement; `docs/encyclopedia/nexus.mdx` returned HTTP 404. Nexus is the obvious candidate
mechanism for MDC↔MDC calls and its authorization model is **not established by this paper**.

---

## §3 Comparative landscape — what each model supplies per tier

**DERIVED table.** Every cell is this paper's mapping of the cited source onto the problem
statement's tiers; the sources make no claim about SkyyNet. Sources: [S1]–[S29], [S33]–[S34].

| Model | Edge tier (credential stays put) | MDC tier (one operator's domain) | Federated tier (holds no edge credential) |
|---|---|---|---|
| **SPIFFE / SPIRE** [S1][S3][S6] | Workload API issues SVIDs locally, no bootstrap secret from the workload | Trust domain = one issuing authority; exactly the MDC unit | **Yes — federation exchanges bundles (public keys) only, one-way** |
| **OIDC federation / RFC 8693** [S7][S27] | Cloud role assumed by a short-lived, per-job token | Trust policy configured once per relying party | **Yes — dispatcher holds a signing key, never the target credential** |
| **NIST ZTA** [S11] | Per-session, per-request decisions; network location grants nothing | PDP/PEP pair per resource | Partial — explicitly carves out non-organizational actors |
| **BeyondCorp** [S12] | Device certificate in TPM; **requires an enterprise-managed device** | Access proxy + inventory | No federation across operators described |
| **Self-hosted CI runner** [S26][S28] | Runner holds real credentials the dispatcher lacks | Runner group scoping | **Yes in mechanism, explicitly discouraged in this configuration** |
| **Vault response wrapping** [S29] | Single-use unwrap token; broker never re-exposes the secret | Broker is the MDC-tier service | Transits an untrusted intermediary by design |
| **WebAuthn** [S16] | **Private key never leaves the authenticator, ever** | — | **Relying party can request an assertion it cannot manufacture** |
| **DPoP** [S8] | Non-extractable key renders stolen tokens useless | — | Sender-constraining survives an untrusted hop |
| **Macaroons** [S13] | — | Attenuate before handing down | Offline delegation with contextual caveats |
| **RATS** [S10] | Attester = the edge | Verifier = MDC service | **Relying Party consumes attestation results without issuing them** |
| **GitOps pull** [S18] | Agent inside the boundary pulls | Reconciler owns the cluster credential | Control plane needs no inbound path or credential |
| **WireGuard** [S14] | Peer *is* its public key | Cryptokey routing table | No PKI — key distribution unsolved at federation scale |
| **BOINC** [S15] | **Holds no participant credential at all** | Project server | **Accepts uncontrolled participants; verifies by redundancy, not trust** |
| **Temporal (self-hosted)** [S21][S22][S24][S33][S34] | Worker polls (pull), no exposed ports [S33][S34]; payloads encrypted client-side [S24] | Namespace + ClaimMapper/Authorizer | **Trunk can carry payloads it cannot read [S24]**; task-queue binding undocumented |

**Reading of the table (derived):** for the *Federated* tier — the tier the problem statement calls
the strongest claim — **six independent models already supply the property**. The claim's novelty is
not there.

---

## §4 What this provides — enumerated, citable properties a plan may rely on **[LOW]**

1. **A specified topology for the three tiers.** SPIFFE trust domains + one-way federation via
   bundle endpoints, with `federates_with` per registration entry [S1][S2][S6]. If the design needs
   a name in a document a reviewer will accept, this is it. *(definitive)*
2. **A no-bootstrap-secret pattern for the edge worker.** Identify the local workload by OS-level
   properties of the calling process rather than a token it presents [S3]. *(definitive)*
3. **A standards-track way to express "SkyyNet may cause work to run as this edge" without holding
   the credential** — delegation semantics with `actor_token` / `may_act`, explicitly distinguished
   from impersonation [S7]. *(definitive)*
4. **A shipped, mass-scale reference for dispatcher-without-target-credential**: CI→cloud OIDC, with
   per-job tokens that expire automatically [S27], and bound, audience-scoped tokens in Kubernetes
   [S17]. *(definitive)*
5. **A mechanism for onboarding a headless edge with a human present exactly once** — the device
   authorization grant [S9]. *(definitive)*
6. **A substrate-native answer to trunk confidentiality**: Temporal's data converter leaves payloads
   unencrypted *only* on client and worker hosts you control [S24]. *(definitive)*
7. **A substrate-native pull model**, so no inbound path to the edge is required. Temporal's
   Workers poll Task Queues [S33][S34] and *"connect directly to the Temporal Service … without
   needing to open exposed ports"* [S34]; GitOps states the same principle generically [S18].
   *(the two polling/port facts are* definitive *and first-party [S33][S34]; the conclusion that
   this satisfies the edge's reachability requirement is* derived *from [S18]+[S33]+[S34])*
8. **A priced warning, with named failure modes, for exactly this configuration** — persistent
   compromise, cross-job secret visibility via process arguments, fork-initiated compromise
   [S26][S28]. *(definitive)*
9. **A vocabulary for attestation roles that keeps the federated tier a Relying Party** [S10].
   *(definitive)*
10. **An offline attenuation primitive** for narrowing authority as it descends tiers [S13].
    *(definitive)*
11. **The precise Temporal build consequence:** authorisation is code we write (default is
    `noopAuthorizer`, allowing every API request) and the namespace is the only offered credential
    boundary [S21][S22]. *(definitive)*

---

## §5 What breaks when the edge is a laptop **[LOW]**

Each item states whether the prior art *solves* it or *assumes it away*.

| Failure mode | Prior art's position | Verdict |
|---|---|---|
| **Intermittent connectivity, sleep/suspend** | BOINC states it as a premise: computers *"are frequently turned off or disconnected from the Internet"* [S15] and designs around it with work units and backoff | **Solved in principle** — by an architecture that assumes it. Temporal's task-queue polling model tolerates a disconnected worker; a task simply is not picked up. *(derived from [S15] + Temporal's documented polling model [S33][S34]. Note: research did not establish what happens to a Task already dispatched to a worker that then sleeps — that is a timeout/retry question, §9 item 11.)* |
| **NAT, no stable address** | BOINC: participants *"often behind network-address translators (NATs) or firewalls"* [S15]; GitOps pull makes inbound reachability unnecessary [S18]; WireGuard supports roaming endpoints [S14]; Temporal's Workers poll and *"connect directly to the Temporal Service … without needing to open exposed ports"* [S34] | **Solved** — by never dispatching inbound. Pull-only is not a preference, it is the requirement, and the chosen substrate documents it [S33][S34]. |
| **No HSM / no managed attestation root** | BeyondCorp *requires* a *"managed device… procured and actively managed by the enterprise"* with the cert in a TPM [S12]; SPIRE's ten documented node attestors reduce, on an unmanaged laptop, to pre-shared secrets [S4][S5] | **ASSUMED AWAY by the prior art.** This is the largest unsolved gap. Every mature model either owns the device or has a cloud instance-identity document. |
| **The operator does not physically control the machine** | NIST Assumption 2: *"Devices on the network may not be owned or configurable by the enterprise"* [S11] — but its remedy is CDM/posture monitoring, i.e. the operator still *measures* the device | **Partially addressed, at a cost we may not be able to pay** (posture agents on a participant's personal laptop). |
| **The user can read every secret on their own machine** | WebAuthn is the only cited model that addresses this head-on: the private key *"is expected to never be exposed to any other party, not even to the owner of the authenticator"* [S16] — and it achieves that with an authenticator, i.e. hardware | **ASSUMED AWAY**, unless hardware is in play. For an OAuth subscription token on disk, the user is inside the trust boundary. This may be acceptable (the credential is *theirs*), and stating that explicitly is the honest resolution. |
| **Credential/session expiry at an unattended edge** | RFC 8628 gives the *acquisition* shape — authorise on a second device [S9]; Fulcio's answer is 10-minute certs [S19]; nothing found addresses re-authentication when no human is present | **UNSOLVED / not documented.** Negative finding; **method stated at corpus level only, because that is all the record supports**: the bodies actually consulted are the ones cited on this row and around it — RFC 8628 [S9], Fulcio [S19], NIST SP 800-207 [S11], BeyondCorp [S12], and both CI vendors' runner guidance [S26][S28] — and `research/synthesis.md` characterises the same sweep as *"nothing found across the RFC series, NIST, BeyondCorp or either CI vendor"*. The **queries behind it were never recorded and are not reconstructible from this artifact**, so treat the sweep as unaudited below corpus granularity and re-run it as an explicit, recorded search at next revalidation. |
| **Revocation when a laptop is lost** | SPIFFE bundles rotate and *"This exchange should occur on a regular basis"* [S1]; short-lived credentials bound revocation latency [S19][S27]; BeyondCorp revokes at the inventory/certificate layer [S12] | **Solved for credentials the system mints; unsolved for the exogenous subscription**, which only its issuer can revoke. |
| **Untrusted work landing on a credential-holding machine** | GitHub: *"can be persistently compromised by untrusted code in a workflow"* [S26]; GitLab: shell executor jobs *"can steal code from other projects"* [S28] | **Solved only by ephemerality**, which a laptop resists. See §7. |
| **Cross-job secret leakage on a shared host** | GitHub: *"Some jobs will use secrets as command-line arguments which can be seen by another job running on the same runner, such as `ps x -w`"* [S26] | **Named and documented**; mitigation is process/user isolation per run. |

---

## §6 Prior art for the three-tier model specifically

### 6.1 The closest analogues, and precisely how they differ

**Closest overall: SPIFFE Federation** [S1][S6]. It matches the topology exactly — administratively
isolated domains, one-way trust, only public key material crossing. **How it differs:** SPIFFE
assumes each domain's *own* issuing authority mints the credentials its workloads use. The three-tier
model's edge credential is issued by a party outside all three tiers and cannot be minted, rotated,
or attenuated by any of them. SPIFFE would sit *alongside* the subscription credential, identifying
the worker to the backbone; it cannot *be* the subscription credential.

**Closest by mechanism: CI→cloud OIDC federation** [S27]. A dispatcher that provably cannot
impersonate its targets, at industry scale. **How it differs:** the target credential is minted on
demand by the relying party (the cloud), per job. Ours is long-lived, human-bound, and cannot be
re-minted per job.

**Closest operationally: the self-hosted CI runner** [S26][S28]. Same physics: a machine someone
owns, holding credentials the dispatcher lacks, executing definitions authored elsewhere. **How it
differs:** the trust direction. In CI, the *repository owner* also owns the runner; the untrusted
party is the pull-request author. In SkyyNet, the runner owner and the work author are different
*operators* by design, which is the configuration both vendors explicitly warn against.

**Closest in spirit: WebAuthn** [S16]. The only widely deployed system whose relying party *provably*
cannot perform the action it requests. **How it differs:** it authorises a single assertion, not an
arbitrary long-running workload, and its guarantee comes from an authenticator device.

**Closest for uncontrolled edges: BOINC** [S15]. The only system found that dispatches real work at
scale to machines the operator has no control over, and says so plainly. **How it differs:** it
carries *no participant credential*, so the hard problem is absent; and its integrity mechanism —
redundant computation — presumes deterministic, comparable results, which agent output is not.

**Academic near-miss:** arXiv 2504.14760 argues the CI-identity case this paper's §2.2 and §2.1
assemble — *"This paper describes the shift from static credentials to OpenID Connect (OIDC)
federation, and introduces SPIFFE … as a runtime-issued, platform-neutral identity model for
non-human actors"* [S20]. *(directional — single-author preprint, not peer-reviewed; useful as
corroboration of framing, not as authority.)*

### 6.2 Has anyone published the specific design? — negative finding, with method **[HIGH]**

**No published design was found in which a federated coordinator dispatches work across
organisational boundaries onto machines whose per-person credential the coordinator cannot obtain,
by design.** Every analogue above breaks in one of two ways: the coordinator *could* have held the
credential and chose not to (OIDC, GitOps, SPIFFE), or there is no credential to hold (BOINC).

**Search method.** (a) Three targeted web searches — federated agent dispatch across trust domains
with edge-held credentials; self-hosted-runner/worker orchestration over a user's own AI
subscription; SPIFFE federation on non-TPM developer laptops. Returns were vendor marketing blogs,
aggregator listicles, and arXiv preprints; **no shipped system's first-party documentation** matched.
(b) First-party raw-source sweep of the specification corpora most likely to contain it: the SPIFFE
standards directory (enumerated, 16 entries) [S1][S2][S3], SPIRE's `doc/` directory (enumerated)
[S4], the relevant RFC series [S7][S8][S9][S10], and NIST SP 800-207 [S11]. (c) The nearest
neighbour was already excluded first-party by an existing pool paper: bernstein's fleet mode is
*"multi-project, not multi-tenant in the security sense… assumed to be run by the same operator, on
a network the operator trusts"* and its federation v1 limitations list *"Cross-tenant federation
across organisations"* [S31].

**Named unverified lead (a gap, not a finding).** A web-search summary asserted that Block's `goose`
lets teams reuse existing Claude Code or Codex subscriptions inside its runtime. **A search-engine
summary is not a source and this was not verified against first-party documentation.** If true it
would be subscription-at-edge, which is already conceded as non-differentiating [problem-statement
§ *Not differentiators*]; it would only threaten differentiator #1 if goose also dispatched across
machines under distinct operators, which nothing observed suggests. **Verify at next revalidation.**

### 6.3 Why has nobody built it? — three distinguishable reasons **[HIGH]**

This is the dispatch's requested high-value output. The reasons are distinguishable, and only one
of them is "it's hard."

**Reason 1 — for everyone who had the choice, centralising was strictly cheaper (structural).**
*Derived from [S27][S17][S19][S1].* The dominant industry pattern is to make credentials *cheap to
mint and short to live* — per-job OIDC tokens [S27], bound service-account tokens [S17], 10-minute
signing certs [S19], rotating SVIDs [S1]. Once a credential is mintable on demand by an authority
you run, "the coordinator must not hold the worker's credential" stops being an architectural
constraint and becomes a one-line trust policy. **Nobody built the three-tier model because nobody
with a mintable credential needs it.** The design only becomes *necessary* when the credential is
exogenous and non-mintable — which is a property of the business model (per-person subscriptions),
not of the technology.

**Reason 2 — the easy version is contractually forbidden (licence/ToS).** Anthropic's Consumer
Terms: *"You may not share your Account login information, Anthropic API key, or Account credentials
with anyone else. You also may not make your Account available to anyone else."* [S30] (*reduced
confidence — rendered page*; **corroborated** by the pool's existing `anthropic_tos_and_enterprise.md`
which quotes the same span from §2 of the terms and records Anthropic's separate objection to
third-party developers routing requests through subscription plans on behalf of users [S32]). **A
centralised orchestrator that proxied users' subscriptions is the obvious product, and it is
prohibited.** So the market has no incumbent doing it the easy way, and the hard way (dispatch to
where the credential already is) has no incumbent either, because — see Reason 1 — the actors with
the engineering capacity to build federation all have mintable credentials.

**Reason 3 — the residual is genuinely hard, and the hard part is attestation, not topology.**
*Derived from [S4][S5][S12][S26].* The topology is a solved problem with a spec. What is unsolved is
establishing *what the edge machine is* when it is an unmanaged personal laptop: BeyondCorp requires
a managed device [S12]; SPIRE's laptop-viable attestors degrade to a pre-shared secret [S4][S5]; and
CI vendors' answer to untrusted execution — ephemeral clean VMs — is precisely what a laptop is not
[S26]. **This is the genuine research frontier in the topic, and it is narrower than the
differentiator claims.**

**Commercial uninterest is a contributing, weaker reason** and is stated as *unverified*: no source
was found asserting that the per-person-subscription federation market is too small to pursue. It is
an inference from the absence of products, and absence of products is weak evidence of absence of
interest.

---

## §7 Honest boundary analysis — does differentiator #1 survive?

**It survives as a design. It does not survive as stated.** Four specific problems, and the
reformulation that fixes them.

**(a) "Three distinct trust tiers" is not a differentiator; it is a specification.** SPIFFE
Federation defines administratively isolated trust domains exchanging only public key material, with
one-way relationships [S1][S2]. Six of the fourteen models in §3 already give the federated tier the
"holds no edge credential" property. **If the problem statement continues to present the tier table
as the distinguishing architecture, a reviewer who knows workload identity will correctly read it as
re-branded federation.** The pool has previously rewarded exactly this kind of narrowing
(differentiator #2 and #4 were both narrowed by commissioned counter-research); this is the same
correction applied to #1.

**(b) The comparison is against the wrong reference class.** It is true — first-party and
current — that cross-organisation federation is outside bernstein's shipped scope [S31]. But that
establishes only that *the nearest agent orchestrator* has not done it. Against the reference class
that actually contains this problem — workload identity, zero trust, distributed CI — the property is
ordinary and shipped at enormous scale. **Differentiator #1 is a differentiator within agent
orchestration, and the statement should say so.**

**(c) The claim is silent about the thing that is actually unusual.** No model in §3 assumes an
edge credential that (i) is minted by a party outside every tier, (ii) cannot be attenuated or
delegated [contrast S13], (iii) cannot be re-minted per job [contrast S27], and (iv) is
contractually non-transferable [S30][S32]. **That conjunction is the real differentiator, it is
narrower, and it is far harder to attack.** It also converts the differentiator from a design
preference into a forced consequence — a much stronger rhetorical position, since a competitor
cannot "just add" it without acquiring the same constraint.

**(d) The strongest evidence against the design is operational, not architectural.** GitHub and
GitLab, independently, document that dispatching work authored by a party you do not control onto a
persistent machine holding real credentials is compromise-by-construction, mitigable mainly by
ephemeral isolation [S26][S28]. The edge is a laptop; laptops are the opposite of ephemeral. **The
federated tier as described is not refuted, but it cannot be shipped without an isolation story, and
this paper found no prior art for ephemeral isolation on an unmanaged personal machine that also
retains a long-lived subscription session.** That is the honest bill.

**Where the design is genuinely well-served by the substrate already chosen.** Temporal's worker
model is pull-based — *"Workers poll for Tasks in Task Queues via synchronous RPC"* and
*"Worker Processes connect directly to the Temporal Service for secure communication without needing
to open exposed ports"* [S34], cf. [S33] and §2.7 — and its data converter leaves payloads readable
*"only on the Client and the Worker process, on hosts that you control"* [S24]. Those two properties
together mean the trunk can dispatch work it can neither perform nor read — a large part of
differentiator #1, obtained from documented features of a dependency already committed to. **Both
halves are first-party documented; only the conjunction is this paper's.**

**When this whole topic is NOT needed.** If every participant turns out to be inside one operator's
domain — one household, one company, one lab — then the MDC tier is the only tier, bernstein's
"same operator, network the operator trusts" assumption [S31] is *also true for us*, and every cost
in this paper is unpaid complexity. **The three-tier model earns its cost only when a second operator
actually exists.** Nothing observed in this repo's current deployment (two servers, one operator,
systemd workers per `system-overview.md`) requires it yet. That is not an argument against the
architecture; it is an argument about *sequencing*, and it belongs in planning.

---

## §8 Citations

**Negative-finding note on source availability.** HashiCorp Vault's product documentation is no
longer in the `hashicorp/vault` git tree: `website/content/docs/concepts/response-wrapping.mdx` and
the `website/content/docs` directory listing both returned HTTP 404 against the repository's
confirmed `default_branch` of `main` (checked via the GitHub repository API before recording the
absence). [S29] is therefore cited from the rendered site at reduced confidence.

**Raw / specification / archival sources (LOW volatility):**

- **[S1]** SPIFFE Federation specification (raw). https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE_Federation.md
- **[S2]** SPIFFE Trust Domain and Bundle specification (raw). https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE_Trust_Domain_and_Bundle.md
- **[S3]** SPIFFE overview specification (raw). https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE.md
- **[S4]** SPIRE `doc/` directory listing, GitHub contents API (enumerated; node-attestor plugins counted from the enumeration). https://api.github.com/repos/spiffe/spire/contents/doc
- **[S5]** SPIRE agent NodeAttestor `join_token` (raw). https://raw.githubusercontent.com/spiffe/spire/main/doc/plugin_agent_nodeattestor_jointoken.md
- **[S6]** SPIRE server configuration reference, federation sections (raw). https://raw.githubusercontent.com/spiffe/spire/main/doc/spire_server.md
- **[S7]** RFC 8693, OAuth 2.0 Token Exchange (plain text). https://www.rfc-editor.org/rfc/rfc8693.txt
- **[S8]** RFC 9449, OAuth 2.0 Demonstrating Proof of Possession (DPoP) (plain text). https://www.rfc-editor.org/rfc/rfc9449.txt
- **[S9]** RFC 8628, OAuth 2.0 Device Authorization Grant (plain text). https://www.rfc-editor.org/rfc/rfc8628.txt
- **[S10]** RFC 9334, Remote ATtestation procedureS (RATS) Architecture (plain text). https://www.rfc-editor.org/rfc/rfc9334.txt
- **[S11]** NIST SP 800-207, *Zero Trust Architecture* (PDF, read page-by-page). https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-207.pdf
- **[S12]** Ward & Beyer, *BeyondCorp: A New Approach to Enterprise Security*, ;login: Vol. 39 No. 6, Dec 2014 (PDF, read page-by-page). https://www.usenix.org/system/files/login/articles/login_dec14_02_ward.pdf
- **[S13]** Birgisson, Politz, Erlingsson, Taly, Vrable & Lentczner, *Macaroons: Cookies with Contextual Caveats for Decentralized Authorization in the Cloud*, NDSS 2014 (PDF, read page-by-page). https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/41892.pdf
- **[S14]** Donenfeld, *WireGuard: Next Generation Kernel Network Tunnel* (NDSS 2017; draft revision e2da747, dated June 1 2020) (PDF, read page-by-page). https://www.wireguard.com/papers/wireguard.pdf
- **[S15]** Anderson, *BOINC: A System for Public-Resource Computing and Storage* (PDF, read page-by-page). https://boinc.berkeley.edu/grid_paper_04.pdf
- **[S16]** W3C Web Authentication specification, Bikeshed source (raw). https://raw.githubusercontent.com/w3c/webauthn/main/index.bs
- **[S17]** Kubernetes documentation, *Service Accounts* concept (raw). https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/security/service-accounts.md
- **[S18]** OpenGitOps, `PRINCIPLES.md` (raw). https://raw.githubusercontent.com/open-gitops/documents/main/PRINCIPLES.md
- **[S19]** Sigstore Fulcio, `README.md` (raw). https://raw.githubusercontent.com/sigstore/fulcio/main/README.md
- **[S20]** Avirneni, *Establishing Workload Identity for Zero Trust CI/CD: From Secrets to SPIFFE-Based Authentication*, arXiv:2504.14760 (2025-04-20) — **preprint, single author, not peer-reviewed**. https://arxiv.org/abs/2504.14760

**Product / vendor surfaces (HIGH volatility):**

- **[S21]** Temporal documentation, self-hosted security guide (raw; load-bearing spans re-verified by a second targeted fetch). https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/security.mdx
- **[S22]** Temporal documentation, multi-tenant application patterns (raw; both load-bearing spans re-verified by a second targeted phrase search). https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/multi-tenant-patterns.mdx
- **[S23]** Temporal documentation, self-hosted namespaces (raw). https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/namespaces.mdx
- **[S24]** Temporal documentation, data encryption (raw). https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/data-encryption.mdx
- **[S25]** Temporal documentation directory listings, GitHub contents API (both enumerated; counts in §2.8 taken from the enumerations). https://api.github.com/repos/temporalio/documentation/contents/docs/production-deployment and https://api.github.com/repos/temporalio/documentation/contents/docs/production-deployment/self-hosted-guide
- **[S26]** GitHub Docs, *Secure use reference* for GitHub Actions (raw markdown source). https://raw.githubusercontent.com/github/docs/main/content/actions/reference/security/secure-use.md
- **[S27]** GitHub Docs, OpenID Connect concept for GitHub Actions (raw markdown source). https://raw.githubusercontent.com/github/docs/main/content/actions/concepts/security/openid-connect.md
- **[S28]** GitLab Runner documentation, *Security risks for runners* (raw markdown source). https://gitlab.com/gitlab-org/gitlab-runner/-/raw/main/docs/security/_index.md
- **[S29]** HashiCorp Vault, *Response Wrapping* — **rendered page, reduced confidence** (raw path unavailable, see note above). https://developer.hashicorp.com/vault/docs/concepts/response-wrapping
- **[S30]** Anthropic Consumer Terms of Service, §2 — **rendered page, reduced confidence; corroborated by [S32]**. https://www.anthropic.com/legal/consumer-terms
- **[S33]** Temporal documentation, *Workers* encyclopedia entry (raw; both load-bearing spans re-verified by a second fetch against the `HEAD` raw URL). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/workers.mdx
- **[S34]** Temporal documentation, *Task Queues* encyclopedia entry (raw; all three load-bearing spans re-verified by a second fetch against the `HEAD` raw URL). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/task-queues.mdx

**Volatility note on [S33]–[S34].** These are vendor product docs and sit in this section by source
type, but the facts drawn from them — that Workers poll Task Queues and require no inbound port —
are core architectural properties of Temporal, not a fast-moving product surface. A refresh may
treat them as **[LOW]** unless Temporal announces a dispatch-model change.

**Source-list provenance.** [S1]–[S32] are the paper's original citations, all of which the
2026-08-06 critic pass verified as existing and correctly cited. [S33]–[S34] were added in that same
pass to close an untraced premise (the pull-based worker model), not to support a new argument.

**Internal pool papers (evidence, non-binding):**

- **[S31]** `docs/standards/architecture/research/raw/bernstein_capability_mining.md` — first-party
  confirmation that cross-organisation federation is outside the nearest neighbour's scope.
- **[S32]** `docs/standards/architecture/research/raw/anthropic_tos_and_enterprise.md` — corroborating
  quotation of the Anthropic account-sharing prohibition and the third-party-proxying objection.

---

## §9 Test plan — what research cannot settle

Each item is framed as an experiment with an observable outcome.

1. **Can a Temporal Authorizer gate task-queue polling by worker identity?** §2.8 Gap 1 is a design
   hypothesis, not a documented capability. *Experiment:* implement a minimal custom `Authorizer` on
   a self-hosted server; attempt `PollActivityTaskQueue` from two workers with different claims
   against the same task queue; observe whether the call is reachable and deniable at that
   granularity. *Settles:* whether a task queue can be a trust boundary, or whether only a namespace
   can.

2. **Does mTLS client identity reach the Authorizer?** If worker identity must come from a
   certificate rather than a JWT, the ClaimMapper must see it. *Experiment:* configure frontend mTLS,
   log what the ClaimMapper receives. *Settles:* whether SPIFFE SVIDs can drive Temporal
   authorisation directly, or whether a JWT bridge is required.

3. **What is the actual re-authentication behaviour of a subscription session on an unattended
   edge?** §5 records this as unsolved in the literature. *Experiment:* run a long-lived headless
   worker and instrument every auth failure; measure time-to-expiry, whether refresh is automatic,
   and what human interaction is required. *Settles:* whether an unattended edge is viable at all,
   which is upstream of every other question here.

4. **Can the edge run work in a per-job ephemeral sandbox while retaining the subscription session?**
   This is the direct response to §2.6's warning. *Experiment:* a per-run container/VM with the
   credential mounted read-only and no persistence, versus a bare systemd worker; measure whether the
   agent still functions (repo access, session continuity) and what leaks between runs. *Settles:*
   whether the CI industry's mitigation transfers to a laptop edge.

5. **Is `ps`-visible secret exposure real for our worker invocation?** [S26] names it specifically.
   *Experiment:* inspect the process table during a run for credential material in argv/environ.
   *Settles:* a concrete, cheap hardening item.

6. **Does SPIRE run usefully on an unmanaged laptop?** *Experiment:* stand up a SPIRE server plus an
   agent on a laptop using `join_token`, then attempt federation to a second trust domain; measure
   what re-attestation costs after a reboot and after a network change. *Settles:* whether SPIFFE is
   adoptable at the edge tier now, or is an MDC-tier-only technology for us.

7. **Does the data converter actually keep the trunk blind end-to-end?** [S24] is a documented
   claim; verify it. *Experiment:* encrypt payloads client-side, then inspect workflow history via
   the Web UI and the API without a Codec Server. *Settles:* whether the federated tier can be
   operated by a party who must not read the work.

8. **Verify or dismiss the `goose` lead (§6.2).** *Method:* fetch Block goose's first-party
   documentation raw and establish (a) whether it authenticates with a user's Claude/Codex
   subscription, and (b) whether it dispatches across machines. *Settles:* whether a shipped system
   already occupies part of differentiator #1's ground.

9. **Establish Temporal Nexus's authorization model** (§2.8 Gap 2), which this paper leaves open.
   *Method:* first-party documentation sweep plus a two-namespace experiment; determine whether a
   Nexus Endpoint call can be denied on caller identity.

10. **The sequencing question research cannot answer:** does a second operator exist within the
    planning horizon? §7 shows the three-tier model is unpaid complexity until one does. *Settles:*
    by operator decision, not by evidence.

11. **What happens to a Task already dispatched to a worker that then sleeps or disconnects?**
    [S33][S34] establish that Workers *poll* — so an offline worker takes no new work, which is the
    §5 row-1 claim. They do **not** establish the behaviour of a Task already handed to a worker that
    goes away mid-execution; this paper did not research Temporal's timeout and retry semantics, and
    states that as a gap rather than assuming the pull model covers it. *Experiment:* start a
    long-running Activity on a laptop worker, suspend the machine, and observe when the Task is
    redelivered and to whom. *Settles:* whether laptop sleep is a non-event or a duplicate-execution
    hazard — which bears directly on idempotency requirements at the edge.
