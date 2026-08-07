# Detecting an expired Claude Code session from a headless dispatch

```
Topic:          How does a headless dispatch detect an expired or invalid Claude Code
                subscription session — as a pre-dispatch preflight and mid-run — and what
                can it do about it on an unattended machine?
Feeds:          Sprint milestone "Three cheap guards — credential expiry, false completion,
                and a safety-hook wiring test" (docs/development/sprint.md:180), the
                credential-expiry guard → the fleet-reliability phase doc (not yet written).
Last validated: 2026-08-07
Revalidate:     high — 3 weeks
Confidence:     DEFINITIVE (first-party documented, raw-source verified): the existence and
                exit-code contract of `claude auth status`; the two distinct expiry states
                (`Login expired` vs `OAuth token revoked/expired`) and their exact message
                strings; the non-interactive message text and its structured error code
                `authentication_failed`; that an expired login stops locally before any API
                request; the `/status` `Login` row; the 3-day advance warning; credential
                file location and mode; the six-step authentication precedence; the
                `system/api_retry` event schema and its `error` enum; that a `-p` in-run
                failure such as missing authentication is printed as the result on stdout;
                that there is no non-interactive re-login path for a subscription login;
                the `ResultMessage` / `AssistantMessage` field sets in the Python Agent SDK.
                DERIVED (this paper's inference over those sources, flagged inline): the
                precise reason today's preflight passes an expired credential through (§2.1);
                the failure-class distinguishability table (§4.3); that `expiresAt` is the
                wrong field to gate a dispatch on and `refreshTokenExpiresAt` is the
                horizon-relevant one (§3.3); the guard design recommendation (§5).
                UNVERIFIED (community-sourced or locally observed, uncorroborated by
                first-party docs): the `.credentials.json` key set and the ~8h access-token /
                ~11.5d refresh-token horizons; mid-run 401 blast-radius behaviour across
                concurrent children; the claim that `claude auth status` costs no quota.
                GAPS (stated as findings with search method in §6): the `claude auth status`
                JSON schema; whether its exit 1 covers "logged in but expired" or only
                "no credential"; whether it performs a network validation; its introducing
                version; the CLI's exit code on an auth failure inside a `-p` run.
Critic:         not-yet-verified — 2026-08-07
```

**Altitude:** COMPONENT. This paper is about *how to build the guard*. Whether a
subscription credential at an unattended edge is the right model at all was settled
upstream and is out of scope — see §8 Escalation.

**Quotation convention (binding on this paper).** Every span presented as a quotation
was returned by a **raw-source fetch** (plain `.md`, `.py`, or a JSON API response) and
its characters were read directly. Three mechanical renderings are applied and are the
*only* alterations: inline documentation hyperlinks `[text](/path)` are rendered as
their link text; a leading list bullet (`* `) or source-comment prefix (`# `) is
dropped; and an ellipsis `…` marks an elision, always within a sentence. No wording is
changed. Where a fetch **summarized** rather than returned raw text, the source carries
that flag in §9 and **no span from it is quoted anywhere in this paper** — this applies
to [S16] and [S18].

---

## §1 Primer — what "expired session" actually names here

### 1.1 The credential this fleet runs on

Every dispatch in this repo runs `claude -p … --output-format stream-json --verbose
--max-turns N --dangerously-skip-permissions` against a **Claude Max consumer
subscription**, not an API key ([S19] `scripts/workflows/activities/run-claude.sh`,
lines 127–154; repo root `CLAUDE.md`). Anthropic documents that subscription
credentials live on Linux in `~/.claude/.credentials.json` with file mode `0600`, that
Claude Code manages that file through `/login` and `/logout`, and that this file is
relocated by `CLAUDE_CONFIG_DIR` (*definitive*, [S1]). The repo's own `CLAUDE.md`
records that `~/.claude/.credentials.json` is machine-local and explicitly **not**
synced, so each of the workstation, travel laptop and VMs holds its own independent
credential with its own independent expiry clock.

Claude Code chooses among available credentials by a documented six-step precedence:
cloud-provider vars, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `apiKeyHelper`,
`CLAUDE_CODE_OAUTH_TOKEN`, and last, "Subscription OAuth credentials from `/login`"
(*definitive*, [S1]). This matters for a guard: **a probe and the real run only agree
about which credential is in play if they run in the same environment**, and an
`ANTHROPIC_API_KEY` present in a VM's shell profile silently outranks the subscription.

### 1.2 Two tokens, two clocks

OAuth 2.0 defines refresh tokens as credentials used to obtain new access tokens when
the current access token expires, with issuance at the authorization server's
discretion (RFC 6749 §1.5, [S18]; *definitive* for the protocol, paraphrased — see the
sourcing note in §6). Claude Code implements exactly this shape: the saved login is
renewed automatically until renewal fails.

Anthropic documents the terminal state precisely: Claude Code "tried to renew your
saved claude.ai or Claude Console login and the OAuth service rejected the stored
refresh token, so Claude Code cleared the saved credentials" (*definitive*, [S2]
`errors.md` §Login expired). **The operational consequence is the useful part:** after
that point "each request stops locally before it reaches the API, because only `/login`
can create new credentials" (*definitive*, [S2]).

### 1.3 What is already settled upstream — cited, not re-derived

The product pool established that **re-authentication of an expired subscription
session at an unattended edge is unsolved industry-wide**: `edge_identity_trust.md` §5
marks "Credential/session expiry at an unattended edge" **UNSOLVED / not documented**,
noting RFC 8628 gives only the acquisition shape and Fulcio's answer is short-lived
certs ([S21], last validated 2026-08-06, Critic: PASS at round 2). The product
synthesis states the same gap as "nothing found across the RFC series, NIST, BeyondCorp
or either CI vendor" ([S23] line 239, synthesis dated 2026-08-06). **This paper takes
that as given and does not re-run the survey.** It asks the narrower question upstream
did not: *what does Claude Code itself emit, and what can a bash preflight check?*

The upstream engineering reference `claude_code_integration_surface.md` ([S22], last
validated 2026-07-25, Critic: PASS) already recorded the two expiry message strings and
the absence of a first-party exit-code table. Every claim this paper reuses from it has
been **independently re-fetched from the first-party raw source** and is cited to that
source, not to the pool paper — with one exception noted in §6.

---

## §2 The specific model — what Claude Code emits, and where today's guard fails

### 2.1 The load-bearing finding: why the existing preflight passes an expired credential

`check_rate_limit()` ([S19], lines 75–97) is the only pre-dispatch check in the fleet:

```bash
probe_stderr=$(claude -p "ping" --max-turns 1 --output-format text 2>&1 >/dev/null) && return 0
if echo "$probe_stderr" | grep -qi "rate.limit\|throttl\|429\|overloaded"; then
    …backoff…
else
    # Non-rate-limit error — don't block, let the real run surface it
    return 0
fi
```

Two independent first-party facts explain why an expired credential reaches the real
run unflagged (*derived*, from [S4] + [S2] + [S19]):

1. **The redirection captures stderr only.** `2>&1 >/dev/null` sends stdout to
   `/dev/null` and stderr to the captured substitution. Anthropic documents that "When
   a failure happens inside the run, such as missing authentication, Claude Code prints
   the failure as the result on **stdout**" (*definitive*, [S4] `headless.md`, emphasis
   added). The auth failure text is therefore discarded by construction, whichever exit
   code accompanies it.
2. **Even if it were captured, the grep would not match.** The non-interactive message
   is `Failed to authenticate: OAuth session expired and could not be refreshed`
   (*definitive*, [S2]). It contains none of `rate.limit`, `throttl`, `429`,
   `overloaded` — so control reaches the `else` branch and returns 0.

The comment on that branch — "don't block, let the real run surface it" — is a correct
policy for a *task* error and the wrong one for a *credential* error, because the real
run cannot surface it to anyone: the fleet is unattended. **This branch is the guard's
insertion point.**

A third fact makes the probe worse than merely blind: the probe is a real model query.
It consumes a turn and produces a `result` event carrying `total_cost_usd` — the same
field `print_cycle_totals()` sums for the monthly burn banner ([S19], lines 106–125) —
and Anthropic documents that "Usage counts against the session and weekly allowances at
the same time" (*definitive*, [S2] §Usage limits). So the current preflight spends
subscription quota on every dispatch to detect one failure class while structurally
missing the one this milestone is about.

### 2.2 The zero-turn check that already exists

The CLI reference documents a subcommand the fleet does not use (*definitive*, [S3]
`cli-reference.md`, CLI-commands table):

> `claude auth status` — Show authentication status as JSON. Use `--text` for
> human-readable output. Exits with code 0 if logged in, 1 if not

Adjacent commands in the same table carry explicit version gates ("Requires Claude Code
v2.1.208 or later", "Available in Claude Code v2.1.195 and later"); the `claude auth
status` row carries none. Sibling `claude auth login` and `claude auth logout` rows are
documented alongside it, and `claude auth login` appears in the changelog at v2.1.200
[S12]. `claude auth status` itself does **not** appear anywhere in the changelog — see
the gap in §6.

This is the single most useful surface for the guard, and three properties of it are
**not documented** — see §6 G1–G3. In particular, the docs do not say whether the
"1 if not [logged in]" branch fires for a *saved-but-expired* login, which is exactly
the state the guard must catch.

### 2.3 The credential-state messages relevant to a subscription dispatch

All *definitive*, all from [S2] `errors.md` (fetched as raw markdown). **Not an
exhaustive list of that page's auth entries** — it omits states this fleet cannot
reach (`apiKeyHelper` failures, AWS/Bedrock credential errors, claude.ai connector
token rejection), which were read and excluded deliberately:

| State | Exact message | Where produced | Version gate |
|---|---|---|---|
| **Refresh failed, credential cleared** | `Login expired · Please run /login` (interactive) / `Failed to authenticate: OAuth session expired and could not be refreshed` (`-p` and Agent SDK) | **Locally, before any request is sent** — "it sends no request" | Non-interactive wording and structured code from v2.1.206; before that it surfaced as a model error |
| **Token revoked or expired at the API** | `OAuth token revoked · Please run /login` / `OAuth token has expired · Please run /login` / `API Error: 401 … authentication_error` | A 401 the API returned for a request Claude Code sent | — |
| **Credential valid in shape, account rejected** | `Please run /login · API Error: 401 Invalid authentication credentials` | API; documented as revocation / disabled org / deactivated account, explicitly **not** expiry | — |
| **Scope drift** | `OAuth token does not meet scope requirement: user:profile` | API | — |

The first two are the ones a fleet guard must separate, because they differ in whether
a request was made at all, and therefore in whether quota was spent.

The **structured** handle for the first state is documented: in non-interactive mode
and the Agent SDK, "the structured error code is `authentication_failed`" (*definitive*,
[S2]).

### 2.4 The advance-warning surface

Anthropic documents a proactive signal (*definitive*, [S1] `authentication.md`
§"Renew an expiring login"):

- Within three days of expiry, an **interactive startup warning**: `Your login expires
  in 3 days · run /login to renew`. Requires v2.1.203+; before v2.1.217 it appeared
  five days out.
- The warning "is informational and never blocks a request".
- `/status` shows a `Login` row reading `Expired — log in again` once expired, "plus
  the organization and email it has saved for the expired login". Requires v2.1.210+.
- The warning and the row appear **only** when a claude.ai or Claude Console login is
  the active credential — not for `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
  `apiKeyHelper` or a cloud provider.

And the sentence that makes this milestone Anthropic-acknowledged rather than
speculative (*definitive*, [S1]):

> Renewing early matters most for sessions that run unattended. A background session in
> agent view or a Remote Control session that outlives the login stops making progress
> once the credential expires and can't recover until you sign in again.

**Note the shape of this surface: it is a startup warning in an interactive TUI and a
row in an interactive slash command.** Neither is reachable from `claude -p`; headless
docs state that built-in commands that only run in the terminal interface, such as
`/login`, are not available in `-p` mode ([S4]). So the documented proactive signal
exists but is not, by itself, machine-readable from a dispatch script.

---

## §3 Comparative landscape — the guard designs, fairly stated

### 3.1 The seven options

| # | Design | Detects | Turn/quota cost | Status |
|---|---|---|---|---|
| A | **Status quo** — `claude -p "ping"` probe, grep stderr | rate limit only, and only when it reaches stderr | one turn per dispatch | Ships today; misses the target class entirely (§2.1) |
| B | **`claude auth status` exit-code gate** before dispatch | "logged in" per the CLI's own definition | none (*derived*, unconfirmed — G3) | Documented command [S3]; three undocumented properties (§6 G1–G3) |
| C | **Credentials-file horizon check** — read `refreshTokenExpiresAt`, refuse to dispatch inside a margin | *impending* expiry, before it bites | none | File shape is undocumented first-party (§3.3); *unverified* |
| D | **Mid-run stream classification** — classify `stream-json` events, park on `authentication_failed` | expiry that begins mid-run | none (reads the log already written) | Event fields documented [S4][S10][S11]; see §4 |
| E | **Change the credential**: `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` (one-year) | — (avoids the class) | none | First-party recommendation for automation [S1][S2][S6] |
| F | **Change the credential**: `apiKeyHelper` script | — (avoids the class) | none | Re-invoked after 5 min or on HTTP 401 [S1] |
| G | **Do nothing** — let the false-completion guard catch the empty run | after the fact | none | The honest baseline; see §7 |

B, C and D are complementary, not alternatives: B catches *already dead*, C catches
*about to die*, D catches *died mid-flight*. E and F are a different kind of answer —
they remove the failure mode instead of detecting it — and are the option Anthropic
itself points automation at.

### 3.2 The first-party answer to "what should automation do", stated fairly

`errors.md` §Login expired gives two remedies for the non-interactive case
(*definitive*, [S2]):

> In non-interactive mode, run `claude` in the same environment, complete `/login`, then
> rerun your command. For automation that can't sign in interactively, authenticate with
> `ANTHROPIC_API_KEY` or generate a long-lived token with `claude setup-token`.

Read literally, this is a **first-party confirmation of the upstream negative**: the
documented recovery for a headless run is *a human at a browser in that same
environment*. There is no documented non-interactive re-login path for a subscription
credential. The vendor's own escape hatch is to stop using the subscription credential.

Option E's terms are documented (*definitive*, [S1]): `claude setup-token` opens the
same browser flow as `/login`, prints a one-year token to the terminal, "does not save
the token anywhere", requires a Pro/Max/Team/Enterprise plan, and "can only make model
requests" — no Remote Control, no claude.ai connectors. The same page notes bare mode
does **not** read `CLAUDE_CODE_OAUTH_TOKEN`. Anthropic's GitHub Actions integration is
built on exactly this: the documented CI secrets are `ANTHROPIC_API_KEY` or
`CLAUDE_CODE_OAUTH_TOKEN`, the latter "generated with `claude setup-token`", and for
organization-wide use the docs recommend an API key instead "since an OAuth token is
tied to the subscription of the person who ran `claude setup-token`" (*definitive*,
[S6]). **Anthropic's own unattended-runner product does not carry a `/login` session.**

Option E's honest cost: it moves the expiry horizon from hours to a year but does not
remove it, and it forfeits nothing this fleet uses. Its real cost is that it is a
credential-model change — which is §8 Escalation territory, not this paper's call.

### 3.3 The credentials file as a signal — and the field trap

**First-party documentation covers the file's location and mode and nothing else.**
`authentication.md` documents the path, `0600`, the Windows/macOS variants, the
`CLAUDE_CONFIG_DIR` relocation, and that Claude Code manages it via `/login`/`/logout`
([S1]). **It does not document a single field name.** (Search method in §6, G4.)

Two non-first-party lines of evidence agree on the shape (*unverified*):

- **Local observation on this workstation** (key names and non-secret scalars extracted
  by pattern; token values never read, [S20]): a `claudeAiOauth` object containing
  `accessToken`, `refreshToken`, `expiresAt`, `refreshTokenExpiresAt`, `scopes`,
  `subscriptionType`, `rateLimitTier`. Observed values included
  `"expiresAt":1786124278104`, `"refreshTokenExpiresAt":1787106136104`,
  `"subscriptionType":"max"`.
- **Community reports.** Issue #83834 reports that "the `claudeAiOauth.expiresAt` field
  is written as `0`" after a v2.1.221 login and describes the expected value as "a real
  future timestamp (ms since epoch)" ([S14]). Issue #72017 reports the access token
  expiring roughly every 8 hours with `refreshToken` present under `claudeAiOauth`
  ([S17]).

**The derived finding a guard must not get wrong.** At the moment of observation
[S20], `expiresAt` sat roughly 3.4 hours in the future while the session was entirely
healthy, and `refreshTokenExpiresAt` roughly 11.5 days out. (*Derived*, from the two
observed millisecond timestamps against this dispatch's own wall-clock; single sample,
one machine, one day.) That is consistent with the ~8h access-token lifetime reported
in [S17] and with the RFC 6749 access/refresh split.

The consequence for the guard is sharp: **`expiresAt` is the wrong field.** A dispatch
gate of the form *"refuse if `expiresAt` is inside the next 45 minutes"* would fire on a
perfectly healthy credential several times a day and would be silent on the state that
actually kills runs — because a near-future `expiresAt` is the *normal* condition of a
working session, and Claude Code renews it. The field that tracks the horizon after
which no renewal is possible is `refreshTokenExpiresAt`. Note that the community
workaround in [S15] — "check `expiresAt` before any Workflow launch" — is, on this
reading, the wrong check, and a guard copying it would inherit the defect.

**Weight this accordingly.** The field set is undocumented, the semantics are inferred
from two community reports plus one local sample, and #83834 is direct evidence the
field can be written with a garbage value by a shipped release. A guard that treats the
file as authoritative inherits that class of bug. A guard that treats it as an
*advisory* signal — "warn the operator that this machine's credential looks close to its
horizon" — does not.

---

## §4 What this provides — enumerated properties a plan can rely on

### 4.1 Pre-dispatch (preflight)

1. **A documented, non-model auth check exists and returns a machine-readable exit
   code:** `claude auth status`, "Exits with code 0 if logged in, 1 if not"
   (*definitive*, [S3]). Emitting JSON by default with a `--text` alternative is
   documented; the JSON's contents are not (G1).
2. **The preflight must run in the dispatch's own environment.** Authentication
   precedence is documented and environment-sensitive ([S1]); a check run under a
   different shell profile can validate a different credential than the run uses. The
   repo's own `-p` invocation inherits the dispatching shell, so co-locating the check
   inside `run_claude()` satisfies this for free.
3. **Proactive horizon data exists but only as an interactive surface** (`/status`
   `Login` row, v2.1.210+; 3-day startup warning, v2.1.203+ — *definitive*, [S1]),
   and neither is reachable from `-p` ([S4]).
4. **Version gating is real and recent.** v2.1.203, .206, .210, .211, .212, .217 each
   changed auth-adjacent behaviour ([S1][S2][S5]). A guard written against today's
   strings needs a version assertion, not a version assumption.

### 4.2 Mid-run

5. **An expired-mid-run session is machine-detectable in `stream-json`.** Claude Code
   emits a `system` / `api_retry` event before retrying a retryable failure, whose
   `error` field is an enum whose first documented value is `authentication_failed`,
   alongside `error_status` (an HTTP status "or `null` for connection errors with no
   HTTP response"), `attempt`, `max_retries`, `retry_delay_ms`, `uuid`, `session_id`
   (*definitive*, [S4]).
6. **The same discriminator appears on assistant messages.** The Python Agent SDK
   defines `AssistantMessageError = Literal["authentication_failed", "billing_error",
   "rate_limit", "invalid_request", "server_error", "unknown"]` and `AssistantMessage`
   carries `error: AssistantMessageError | None` (*definitive* for the SDK surface,
   [S10]); the parser reads it from the raw CLI JSON as `error=data.get("error")`
   (*definitive*, [S11]). **Derived:** the CLI's `stream-json` assistant events
   therefore carry a top-level `error` key with those exact string values, so a `jq`
   filter over the existing `$LOG_FILE` can classify without any new instrumentation.
   **Caveat — the two enums are not the same set.** The `api_retry` enum documented in
   [S4] is `authentication_failed`, `oauth_org_not_allowed`, `billing_error`,
   `rate_limit`, `overloaded`, `invalid_request`, `model_not_found`, `server_error`,
   `max_output_tokens`, `unknown`; the SDK's `AssistantMessageError` [S10] omits
   `oauth_org_not_allowed`, `overloaded`, `model_not_found` and `max_output_tokens`.
   A guard written against the SDK list alone would **miss `oauth_org_not_allowed`**,
   which is an auth-class failure. Match against the union, and treat unrecognised
   values as "unknown auth-adjacent" rather than as a pass. Whether the divergence is a
   real surface difference or documentation drift is **not established** — neither
   source states which is authoritative for the CLI's own stream. → T6.
7. **The `result` event carries an HTTP status for API-level failures.** `ResultMessage`
   defines `api_error_status: int | None` with the in-source comment that it is the
   "HTTP status code (e.g. 429, 500, 529) of the failing API call when ``is_error`` is
   True and ``subtype`` is "success"; None otherwise. Emitted by the CLI since
   v2.1.110." (*definitive*, [S10]), read as `api_error_status=data.get(
   "api_error_status")` ([S11]). It also carries `is_error: bool`, `subtype: str`,
   `errors: list[str] | None`, `num_turns`, `session_id` and `terminal_reason`.
8. **A refresh-failure mid-run costs no further quota.** Once the credential is cleared,
   "each request stops locally before it reaches the API" ([S2]) — so a 45-minute run
   whose refresh fails at minute 20 does not burn allowance for the remaining 25.

### 4.3 Failure-class separation — what is and is not distinguishable

*Derived* from [S2][S4][S10][S11]. This table is the answer to the milestone's real
question, and the **NOT distinguishable** rows are the finding.

| Class | Pre-dispatch signal | Mid-run signal | Separable? |
|---|---|---|---|
| **Expired / cleared login** | `claude auth status` exit code (G2: coverage undocumented); `refreshTokenExpiresAt` horizon (*unverified*) | `error == "authentication_failed"`; result text `Failed to authenticate: OAuth session expired and could not be refreshed` | **Yes** mid-run (documented string + structured code). Pre-dispatch: *probably*, pending G2 |
| **Revoked token / disabled account** | same exit code as expiry — no documented discriminator | `API Error: 401 … authentication_error`; `api_error_status == 401`; message text differs (`Invalid authentication credentials` vs `OAuth session expired`) | **Mid-run yes** by message text; **pre-dispatch NO** — both are "not logged in" |
| **Plan quota exhausted** | *none without a model call* — `rate_limits` appears in status-line JSON "only … after the first API response in the session" ([S8]) | `error == "rate_limit"`; `You've hit your session limit` / `weekly limit` / `Opus limit` with a reset time ([S2]) | **Mid-run yes**; **pre-dispatch NO without spending a turn** |
| **Server-side throttle (not your quota)** | none | `API Error: Server is temporarily limiting requests (not your usage limit)`; distinguished server-side "by the absence of the unified quota headers a real limit response carries" ([S2]); auto-retried since v2.1.199 | **Yes mid-run, by message.** Today's grep for `429\|throttl` conflates it with a real quota limit |
| **Network / TLS failure** | none | `error_status: null` on `api_retry` "for connection errors with no HTTP response" ([S4]); `Unable to connect to API`, `Socket is closed`, `SSL certificate verification failed` ([S2]) | **Yes**, via `error_status == null` |
| **Genuine task error** | n/a | `subtype`/`is_error` on the result with no `authentication_failed` or `rate_limit` upstream | **Yes**, by exclusion |
| **Turn-cap termination** | n/a | `"subtype":"error_max_turns"` — already handled ([S19] lines 167–192) | Yes (already shipped) |

Three separations are **not reliably makeable**, and they define the guard's ceiling:

- **Expired vs revoked, pre-dispatch.** Both are "not logged in". They differ only in
  remedy urgency, and both remedies are the same action (`/login` by a human), so the
  practical cost of conflating them is low.
- **Quota exhaustion, pre-dispatch, without spending a turn.** Quota state is documented
  as appearing only after the first API response of a session ([S8]). This is why
  option B **cannot replace** the existing probe outright: dropping `check_rate_limit()`
  in favour of `claude auth status` would trade one blind spot for another.
- **`claude auth status` exit 1 semantics.** Until G2 is settled by experiment, exit 1
  means "the CLI declined to call this logged in", which is a superset of the target
  state and possibly a proper superset. As a *blocking* signal that is fine (it is
  never wrong to refuse); as a *diagnostic* it is imprecise.

### 4.4 Mid-run expiry — the concrete picture

A 45-minute run whose session expires at minute 20 produces, in order (*derived* from
[S4][S2][S10][S11]): one or more `system`/`api_retry` events with
`error: "authentication_failed"` (and `error_status: 401` if the API rejected it, or
absent/`null` in the local-stop case); then either recovery, or a terminal result whose
`.result` text carries `Failed to authenticate: OAuth session expired and could not be
refreshed`. Because `$LOG_FILE` already captures every stream line ([S19] lines
144–154), **detection needs no new plumbing — only a `jq` pass**, structurally identical
to the existing `error_max_turns` check.

Two caveats, both *unverified* and both consequential for a fleet:

- **Sub-agent fan-out may die silently.** Issue #84273 reports background/workflow
  children all failing 401 at a token rollover while the parent kept working, with "Each
  dead child left a zero-byte `.output` file and no notification; the run produced
  nothing" ([S15], community-authored, one reporter, Windows). If that behaviour is
  real on Linux, a parent-level stream check would see a *successful-looking* run —
  which is precisely the false-completion guard's territory, and an argument for
  designing the two guards together as the sprint already requires.
- **Blast radius is machine-wide.** The same report describes two unrelated interactive
  sessions taking the same 401 inside the same window ([S15]). Anthropic documents the
  underlying coordination: "Parallel sessions on one machine share a saved login and
  coordinate its renewal so that only one process refreshes the token at a time"
  (*definitive*, [S5]), with a v2.1.211 fix for double-renewal after wake-from-sleep.
  **Derived:** credential failure is a per-machine event, not a per-dispatch one, so the
  guard's park/notify state belongs at machine scope, not run scope.

### 4.5 What a guard can DO on an unattended machine

Given §3.2's first-party confirmation that no non-interactive re-login exists, the
option space is exactly three, and they compose:

1. **Detect and park.** Refuse to start (preflight) or stop cleanly and leave the
   worktree intact (mid-run), with a machine-scoped marker so sibling dispatches on the
   same host do not each rediscover it. Cost: near zero. This is the only option fully
   inside this component's control.
2. **Detect and notify.** Emit into the blocked-work channel the sprint already plans
   (milestone "A blocked-work notifier"). This guard is a *producer* for that channel,
   not a re-implementation of it — the channel's design is topic 5 of this same pool.
3. **Proactive horizon check.** Refuse to *start* a long dispatch inside the
   `refreshTokenExpiresAt` margin. Cheap, but rests entirely on an undocumented field
   and on the *unverified* claim that Claude Code will not silently extend it.

**What is NOT possible** (*definitive*, [S1][S2], corroborated by upstream [S21][S23]):
re-authenticating a subscription login without a human at a browser in the same
environment; determining quota headroom without spending a turn; distinguishing expiry
from revocation before dispatch.

### 4.6 Cost of a preflight

Today's probe costs one model turn per dispatch against the subscription's session and
weekly allowances ([S2][S19]). `claude auth status` is a distinct CLI subcommand, not a
`-p` query, and nothing in its documentation describes a model request ([S3]) —
**derived: it consumes no turn and no quota.** Whether it makes any *network* call
(and therefore whether it can fail on a flaky VM link, or detect a server-side
revocation that the local file cannot) is **not documented** (G3) and is the single
highest-value item in the test plan.

---

## §5 The design this evidence supports (derived)

Not binding — research is evidence (Research Standard §1). Stated so the phase doc has
something concrete to accept or reject.

Replace the `else` branch of `check_rate_limit()` — not the function — with a
classification, and keep the model probe only for what only it can see:

1. **Preflight, before the probe:** `claude auth status` (discard stdout). Exit 1 →
   **park + notify, do not dispatch.** Exit 0 → continue. Cost: no turn.
2. **Preflight, advisory:** if `~/.claude/.credentials.json` parses and
   `refreshTokenExpiresAt` is inside a margin exceeding this workflow's expected
   duration, **warn** (never block — the field is undocumented and #83834 shows it can
   be garbage).
3. **Keep the model probe** for quota, since §4.3 shows quota is not observable without
   it — but **rewrite its capture** to `2>&1` combined (stdout carries the auth failure,
   per [S4]) and **split its `else` branch** into: `authentication_failed` /
   `OAuth session expired` → park; `Invalid authentication credentials` → park;
   `Unable to connect` / `Socket is closed` / `SSL certificate` → retry with backoff,
   distinct from the rate-limit backoff; anything else → today's pass-through.
4. **Post-run:** one `jq` pass over `$LOG_FILE` for `error` in
   `{authentication_failed, oauth_org_not_allowed}` (the union of §4.2's two enums) or
   `api_error_status == 401`, alongside the existing `error_max_turns` and
   `COMPLETION_PATTERN` checks — same shape, same place, no new plumbing.
5. **Park state is machine-scoped**, per §4.4's blast-radius finding.
6. **Assert the CLI version** where a documented behaviour is version-gated, rather than
   assuming the fleet is current.

Everything above is component-altitude and reversible. Option E (`setup-token`) is a
credential-model change and belongs in §8.

---

## §6 Honest boundary analysis — and the gaps, with their search method

### 6.1 When this guard is NOT worth building

- **If option E lands first, this guard is mostly dead weight.** A one-year
  `CLAUDE_CODE_OAUTH_TOKEN` moves the horizon out by ~365× ([S1]); the expiry class
  stops being an overnight event and becomes an annual calendar item. Building an
  elaborate detector for a failure that a credential swap nearly eliminates is
  the classic mis-sequencing. **The guard is still worth its cheap form** — a preflight
  exit-code check is a handful of lines and catches revocation, org changes and a
  fat-fingered `/logout` regardless of credential type — but the *proactive horizon*
  machinery (option C) should not be built until the credential model is settled.
- **If the false-completion guard is built first and is good, it catches this too.** A
  run that dies on auth produces no PR; a guard that verifies observable artifacts
  detects that without knowing why. The credential guard's marginal value is
  **attribution and pre-emption** — telling the operator *what* to fix, and not burning
  a worktree and a dispatch to find out.
- **If runs are attended, the value collapses.** Anthropic already ships an interactive
  3-day warning and a `/status` row ([S1]). A human at the terminal is already covered.
- **The base rate is unmeasured.** Nothing in this repo records how often a dispatch has
  actually died on credential expiry. §7 T7 proposes measuring it before sizing the
  work; the honest position today is that this is a *plausible* failure mode with
  vendor acknowledgement ([S1] "sessions that run unattended") and community reports
  ([S16][S15][S17]), not an observed rate in this fleet.

### 6.2 What the guard fails to catch even when built

- **A credential that is valid at preflight and revoked one minute later.** Only the
  mid-run leg sees it, and only if the stream is classified.
- **Silent sub-agent death** while the parent survives ([S15]) — a *false completion*,
  not a detectable auth failure at parent scope.
- **The wrong credential being valid.** If `ANTHROPIC_API_KEY` is set on a VM, both the
  check and the run use it, both pass, and the subscription's state is irrelevant —
  correct behaviour, but the operator's mental model ("the fleet runs on Max") is now
  wrong and nothing says so. Community issue #84245 reports a related gap: no way to
  confirm which account a session is authenticated as under a per-project token
  override ([S13], unverified).
- **A credential file written with a garbage `expiresAt`** ([S14]) — the horizon check
  would either fire constantly or never.
- **Everything upstream declared unsolved:** the guard detects and reports; it cannot
  re-authenticate ([S21] §5, [S23]).

### 6.3 Gaps — stated as findings, with search method

Search method for all of the below, unless stated otherwise: enumerated the
first-party documentation index at `code.claude.com/docs/llms.txt` [S9] for pages whose
title or URL relates to authentication, credentials, login, headless/SDK, monitoring or
error handling; fetched **as raw markdown** each of `authentication.md` [S1],
`errors.md` [S2], `cli-reference.md` [S3], `headless.md` [S4], `troubleshoot-install.md`
[S5], `github-actions.md` [S6], `agent-sdk/troubleshooting.md` [S7], `statusline.md`
[S8]; grep'd the retrieved raw text for `credentials.json`, `auth status`, `expiresAt`,
`refresh token`, `exit code`, `Login expired`, `authentication_failed`; fetched
`CHANGELOG.md` from `raw.githubusercontent.com` [S12] for the substrings `auth status`,
`auth login`, `auth logout`, `claude auth`; and queried the GitHub issues search API on
`anthropics/claude-code` for `"auth status"` and `".credentials.json"`.

- **G1 — the `claude auth status` JSON schema is not documented.** `cli-reference.md`
  states it outputs JSON [S3]; no page in the index defines a field. Consequence: a
  guard can rely on the exit code but must not parse the JSON without pinning a version
  and testing it. → T1.
- **G2 — whether exit 1 covers "saved login, expired" or only "no credential" is not
  documented.** `errors.md` documents that `/status` (interactive) shows an
  `Expired — log in again` row from v2.1.210 [S2], which makes parity plausible, but
  plausible is not documented and this paper does not assert it. **This is the guard's
  single load-bearing unknown.** → T1.
- **G3 — whether `claude auth status` performs a network validation is not documented.**
  Determines whether it detects server-side revocation, and whether it can fail on a
  flaky link. → T2.
- **G4 — the `.credentials.json` schema is not documented first-party.** [S1] documents
  location and mode only. The key set in §3.3 is local observation plus community
  reports and is marked *unverified* throughout; no first-party schema exists to
  corroborate it. → T3.
- **G5 — the CLI exit code for an auth failure inside a `-p` run is not documented.**
  `headless.md` documents 0 on success, non-zero on failure, and 143 on SIGTERM [S4];
  no page maps auth failure to a specific code. The upstream pool independently
  recorded the absence of any first-party exit-code table ([S22] §5) — **this is the one
  claim reused from the pool paper rather than re-derived**, because it is a negative
  about the whole corpus. → T4.
- **G6 — the introducing version of `claude auth status` is unrecorded.** Its
  `cli-reference.md` row carries no version gate while neighbouring rows do [S3], and
  the substring `auth status` returned no match in the changelog [S12]. **Caveat on
  that negative:** the same changelog fetch returned one bullet attributed to `claude
  auth` whose quoted text does not contain the substring, so the retrieval layer is not
  reliable for exhaustive search and this negative is weaker than a grep over a local
  copy. Treat as "not established", not "confirmed absent". → T5.
- **G7 — the subscription access-token and refresh-token lifetimes are not documented.**
  The ~8h / ~11.5d figures in §3.3 are one local sample plus community reports. Anthropic
  documents only the *warning* interval (3 days), never the lifetime [S1]. → T3.
- **G8 — which error enum the CLI's own `stream-json` emits is not established.** The
  `api_retry` enum [S4] and the SDK's `AssistantMessageError` [S10] differ by four
  values (§4.2 property 6); neither source states which governs the CLI stream a bash
  guard reads. Consequence: a filter written against the wrong list silently passes
  `oauth_org_not_allowed`, an auth-class failure. → T6.

---

## §7 Test plan — what research cannot settle

Each item names the experiment and what its result decides. Run on a pinned CLI version,
recorded in the result.

- **T1 — `claude auth status` truth table (settles G1, G2; unblocks the whole guard).**
  On a machine with a valid login, capture exit code, stdout, stderr. Then: (a) `claude
  auth logout`, repeat; (b) restore a login and hand-edit `expiresAt` and
  `refreshTokenExpiresAt` into the past in a *copy* of the config dir selected via
  `CLAUDE_CONFIG_DIR`, repeat; (c) with `ANTHROPIC_API_KEY` set, repeat. Record the JSON
  body verbatim in each case. **Decides:** whether option B alone is a sufficient
  preflight, or must be paired with option C.
- **T2 — network dependence (settles G3).** Run `claude auth status` with outbound
  traffic to `api.anthropic.com` and `claude.ai` blocked. If it still exits 0 on a valid
  login, it is a local check and cannot see revocation; if it fails, the preflight
  inherits a network dependency and needs its own timeout. **Decides:** whether a
  network failure can masquerade as an auth failure in the preflight.
- **T3 — expiry horizon (settles G4, G7).** Log `expiresAt` and `refreshTokenExpiresAt`
  (values only, no tokens) on each fleet machine every hour for two weeks. **Decides:**
  the real refresh cadence, whether `refreshTokenExpiresAt` slides forward on renewal
  (if it does, option C is unbuildable as specified), and the correct safety margin.
- **T4 — exit-code map for auth failure (settles G5).** Run `claude -p "ping"
  --output-format text` against a deliberately expired credential; record exit code,
  full stdout, full stderr separately (no `2>&1`). **Decides:** whether the preflight
  can branch on exit code alone or must match message text, and confirms §2.1's derived
  claim that the failure text lands on stdout.
- **T5 — version floor (settles G6).** Run `claude auth status --text` on each fleet
  machine and record `claude --version`. **Decides:** whether the guard needs a fallback
  path for older installs.
- **T6 — mid-run capture.** Force an expiry mid-run (start a long dispatch, then
  `/logout` from another shell on the same machine, or expire the copied config dir) and
  capture the full `stream-json` log. **Decides:** the exact `jq` filter for §5 step 4,
  and confirms whether `api_retry`/`error` appear at all in the local-stop case where no
  request is sent. Also record which enum the live stream actually emits, settling the
  `api_retry` vs `AssistantMessageError` divergence in §4.2 property 6.
- **T7 — base rate.** Grep the existing `.claude/logs/*.jsonl` corpus for
  `authentication_failed`, `Login expired`, `OAuth session expired`, `401`. **Decides**
  whether this guard is cheap-insurance-sized or a real observed failure mode — and
  therefore how much of §5 to build now.
- **T8 — sub-agent fan-out ([S15] on Linux).** During T6, run a dispatch that spawns
  sub-agents and check whether children fail while the parent's result still reports
  success. **Decides:** whether this guard and the false-completion guard must share a
  detection path.

---

## §8 Escalation — out of scope, recorded not acted on

Two items sit above COMPONENT altitude. **Named here; not acted on in this paper.**

1. **Whether the fleet should keep a `/login` subscription session as its dispatch
   credential at all.** Anthropic's own unattended product (GitHub Actions) does not
   ([S6]); its documented automation advice is `ANTHROPIC_API_KEY` or `claude
   setup-token` ([S2]). That is a credential-model decision with cost, ToS and
   multi-machine implications — the product pool's territory
   (`subscription_economics.md`, `anthropic_tos_and_enterprise.md`,
   `edge_identity_trust.md`), not this milestone's.
2. **Whether `--bare` should become the fleet's invocation mode.** Anthropic states
   bare mode "is the recommended mode for scripted and SDK calls, and will become the
   default for `-p` in a future release" ([S4]) — but bare mode "never reads OAuth
   credentials or the system keychain" ([S4]), so adopting it *forces* item 1. A
   roadmap statement plus a hard dependency on a credential change is an architecture
   decision, not a guard.

---

## §9 Citations

**First-party documented — fetched as raw markdown / raw source (highest confidence):**

- **[S1]** Anthropic, *Authentication* — https://code.claude.com/docs/en/authentication.md (raw markdown)
- **[S2]** Anthropic, *Error reference* — https://code.claude.com/docs/en/errors.md (raw markdown)
- **[S3]** Anthropic, *CLI reference* — https://code.claude.com/docs/en/cli-reference.md (raw markdown)
- **[S4]** Anthropic, *Run Claude Code programmatically* (headless) — https://code.claude.com/docs/en/headless.md (raw markdown)
- **[S5]** Anthropic, *Troubleshoot installation and login* — https://code.claude.com/docs/en/troubleshoot-install.md (raw markdown)
- **[S6]** Anthropic, *Claude Code GitHub Actions* — https://code.claude.com/docs/en/github-actions.md (raw markdown)
- **[S7]** Anthropic, *Agent SDK Troubleshooting* — https://code.claude.com/docs/en/agent-sdk/troubleshooting.md (raw markdown). Consulted and **negative**: covers CLI-startup, Windows batch-script and structured-output errors; contains no authentication, credential or exit-code entry.
- **[S8]** Anthropic, *Customize your status line* — https://code.claude.com/docs/en/statusline.md (raw markdown; `rate_limits` fields)
- **[S9]** Anthropic, documentation index — https://code.claude.com/docs/llms.txt (used to enumerate the pages above)
- **[S10]** Anthropic, `claude-agent-sdk-python`, `src/claude_agent_sdk/types.py` — https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/src/claude_agent_sdk/types.py (`ResultMessage`, `AssistantMessage`, `AssistantMessageError`)
- **[S11]** Anthropic, `claude-agent-sdk-python`, `src/claude_agent_sdk/_internal/message_parser.py` — https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/src/claude_agent_sdk/_internal/message_parser.py (raw-JSON key names)
- **[S12]** Anthropic, `claude-code` `CHANGELOG.md` — https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md (targeted substring search; see G6 caveat)
- **[S24]** GitHub REST API, `anthropics/claude-code` repository metadata — https://api.github.com/repos/anthropics/claude-code (`default_branch: "main"`, confirmed before any raw fetch against that branch; `archived: false`)

**Community-sourced — GitHub issue bodies fetched via the REST API (*unverified*; one reporter each unless noted):**

- **[S13]** Issue #84245, *No way to confirm which account a session is authenticated as when using a per-project CLAUDE_CODE_OAUTH_TOKEN override*, open, 2026-08-05 — https://github.com/anthropics/claude-code/issues/84245
- **[S14]** Issue #83834, *v2.1.221: OAuth login always fails with 'Login expired' - credentials.json expiresAt written as 0*, open, 2026-08-04 — https://github.com/anthropics/claude-code/issues/83834
- **[S15]** Issue #84273, *[BUG] Background/Workflow subagents all 401 at OAuth token rollover while the parent session refreshes successfully (spawn-time token capture)*, open, 2026-08-05 — https://github.com/anthropics/claude-code/issues/84273
- **[S16]** Issue #12447, *[BUG] OAuth token expiration disrupts autonomous workflows – refresh token handling needed*, open, 2025-11-26, 25 comments — https://github.com/anthropics/claude-code/issues/12447. **Body was returned by a summarizing fetch; no span from it is quoted in this paper.**
- **[S17]** Issue #72017, *OAuth session expires every ~8 hours, requires daily /login*, closed, 2026-06-28 — https://github.com/anthropics/claude-code/issues/72017

**Standards:**

- **[S18]** IETF RFC 6749, *The OAuth 2.0 Authorization Framework*, §1.5 — https://www.rfc-editor.org/rfc/rfc6749.txt. **Sourcing note:** fetched from the raw `.txt`, but the retrieval layer reflowed the text, so §1.2 **paraphrases** rather than quotes it.

**This repo and its own research pool:**

- **[S19]** `scripts/workflows/activities/run-claude.sh` (this repo) — `check_rate_limit()` lines 75–97; `print_cycle_totals()` 106–125; `run_claude()` 127–223
- **[S20]** Local observation, `~/.claude/.credentials.json` on this workstation, 2026-08-07. Key names and non-secret scalars extracted by regex; **token values were never read into context**. Single machine, single sample. *Unverified* — no first-party schema exists to corroborate it.
- **[S21]** `docs/standards/architecture/research/raw/edge_identity_trust.md` §5 — last validated 2026-08-06, Critic: PASS at round 2. Cited for the settled upstream negative only.
- **[S22]** `docs/standards/architecture/research/raw/claude_code_integration_surface.md` §3, §5 — last validated 2026-07-25, Critic: PASS. Cited once, for the corpus-level negative in G5.
- **[S23]** `docs/standards/architecture/research/synthesis.md` (2026-08-06), candidate 21 and the gap list line 239.
