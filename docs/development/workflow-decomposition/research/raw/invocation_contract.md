# invocation_contract

```
Topic:          The INVOCATION CONTRACT for this fleet's workflow children — "a workflow derives
                what it needs from how it was called." Three coupled facets, one paper:
                (1) DUAL-MODE — a child must run standalone (operator at a terminal) and under a
                    parent, equally well; what the field does about one unit with two callers.
                (2) SCOPE FROM THE TARGET — deriving feature scope from the path a workflow was
                    pointed at rather than restating it in a flag; when derivation is safe to
                    trust and when it becomes too clever to debug.
                (3) MANAGED CONFIG + A USER TIER — agents/skills/rules/hooks are read from
                    `~/.claude/`, so an interactive edit silently changes every dispatch on that
                    machine and no two machines can be shown to match; how managed-plus-user
                    layering, precedence, provenance, drift detection and cross-machine proof are
                    done elsewhere.
Feeds:          docs/development/workflow-decomposition/roadmap.md § Phase 3 — "The invocation
                contract". No phase doc exists yet; this paper is the evidence a planner
                decomposes Phase 3 from. It validates all four Phase 3 checkboxes.
Last validated: 2026-08-18
Revalidate:     high — 4 weeks   (mixed volatility, header takes the HIGHEST tier present per
                Research Standard §3. The fast-decaying material is §4.3 and §5.3 — the Claude
                Code CLI configuration surface, pinned at 2.1.234, which the upstream pool already
                rates `high — 4 weeks`. The slow-decaying material is §2.1–§2.3 and §3: git,
                systemd, npm, Bazel, pytest, chezmoi and Twelve-Factor precedence semantics have
                been stable for years and a refresh may skip re-verifying them. Marked in place.)
Confidence:     DEFINITIVE for every span quoted from a raw first-party artifact — each was
                verified by `curl -s <raw-url> | grep -c -F "<exact span>"` returning 1, or read
                directly out of a `curl`/`sed` byte stream, before being written here. DEFINITIVE
                for the Claude Code flag semantics in §4.3, which come from `claude --help` on the
                locally installed CLI at version 2.1.234 — a versioned first-party artifact,
                observed rather than summarized. DEFINITIVE for every count in §5, each produced by
                an enumerating command whose text and output are quoted at commit `128091c`.
                REDUCED for the Claude Code settings-precedence and `managed-settings.d/` facts in
                §4.3: those came from a summarizing fetch of a RENDERED page
                (code.claude.com/docs/en/settings), so nothing from it is quoted verbatim; the
                `/etc/claude-code/managed-settings.json` half is corroborated by a critic-PASS pool
                paper and rises to definitive, the `.d/` drop-in half is single-source and is
                marked DIRECTIONAL.
                REDUCED-BUT-VERIFIED for The Rails Doctrine (§3.2): only a rendered HTML page
                exists, so the three spans quoted from it were each confirmed with `grep -F`
                against the raw HTML bytes; no paraphrase of it is presented as a quotation.
                DERIVED — and each names its inputs — for: the three-way pattern ranking in §2.1;
                the "anchor, don't guess" rule in §2.2; the CENTRAL claim of §2.3, that the field
                runs TWO OPPOSITE precedence directions and the choice is a policy decision rather
                than a technical one; the §4.3 finding that moving the safety hook to the managed
                tier would make it immune to `--setting-sources`; and the recommendation set in §4.
                NEGATIVE FINDINGS, each stating its search method: (a) no first-party source was
                found that recommends TTY-sniffing as the primary way a unit distinguishes a
                machine caller from a human one — every first-party source found pairs detection
                with an explicit caller-supplied override (§2.1, §6.1); (b) no source was found
                measuring the defect rate of derived-vs-declared configuration (§6.2); (c) Terraform
                was checked as a dual-mode exemplar and its docs are no longer in the
                `hashicorp/terraform` repository, so no raw source was available and it is NOT
                cited (§8, "searched, not cited").
                UNVERIFIED: nothing load-bearing in this paper rests on uncorroborated commentary.
Critic:         PASS-WITH-FIXES — 2026-08-18, one `research-critic` round under `research-verify`.
                Every one of the seventeen external sources resolves, and every span re-checked
                against a byte-exact raw GET matched; the path-scoped commit SHAs each source was
                re-fetched at are recorded in §8 so a later re-check hits the same bytes. FOUR
                defects were found and all four are repaired in place: P14 pointed the reader at
                test T7 where §7's P14 test is T2; the docstring span attributed to
                `test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in` blended wording
                from two different docstrings in that file; the M2 pytest span had lost the source's
                RST double-backticks; and the Terraform negative finding described a `website/`
                directory as absent when it exists, holding only a redirect README. Three packaging
                counts were corrected in the same round — §2.3's count of systems read, §8's
                per-facet source distribution, and a §1.3 row for a paper nothing in the body rests
                on. NO fabricated source and NO confidence inflation was found; the two speculative
                facet-3 findings (P14, P18) were already correctly held below definitive.
```

> **Read this first — one framing correction, because it changes what Phase 3's second checkbox is
> asking for.** The dispatch that commissioned this paper describes `plan-project` as *"a
> not-yet-built workflow."* **It is built and it runs.** `scripts/workflows/temporal/scripts/run_plan_project.py`
> exists, `plan_project.sh` shims it, and `plan_project_workflow._plan_one` already invokes
> `plan-feature` and `plan-verify` per component. `plan-feature` already takes its component as a
> **positional path**, declared `p.add_repo_path("component", kind="dir", …)` — i.e. **scope is
> already derived from the target, not from a flag.** Enumeration and commands in §5.2.
>
> So Phase 3's second checkbox is not "build derivation." It is **"finish and harden the derivation
> that shipped"** — specifically: the chain-tail rule is not yet expressed anywhere in code, and
> what was derived is not yet reported back to the operator. That is a smaller, better-defined job
> than the roadmap line implies, and a planner sizing it from the roadmap wording alone would
> over-scope it. Everything else in the dispatch's framing held up.

---

## 1. Primer — what an invocation contract is, and what is NOT re-derived here

### 1.1 The concept

A workflow's **invocation contract** is everything the workflow learns from *the act of being
called*, as opposed to what it is told in prose. It has three inputs, and the three facets of this
paper are exactly those three inputs:

| Input | The question | Facet |
|---|---|---|
| **Who called me** | a human at a terminal, or another workflow | 1 — dual-mode |
| **What was I pointed at** | the target: a path, a PR number, a resource id | 2 — scope derivation |
| **What environment am I standing in** | the config the process absorbs before it starts | 3 — managed config |

The three are coupled and that is why they are one paper. A child that behaves differently under a
parent (facet 1) usually does so because it read something ambient (facet 3); a scope derived from
a target (facet 2) is only trustworthy if the *derivation itself* is observable, which is the same
provenance machinery facet 3 needs. Splitting them produces three papers that each recommend half a
mechanism.

### 1.2 What is already settled and is NOT re-derived

- **Parents, children, activities.** [`workflow-scripts.md` § Composition](../../../../standards/workflow-scripts.md)
  already binds this: a parent *"calls other workflows and calls no model itself"* and holds *"no
  process code"*; the test is *"does this touch the outside world?"*; activities own all external
  I/O. **Every recommendation below fits inside that shape and none replaces it.**
- **What a child returns.** The same standard already rules that `COMPLETION_PATTERN` plus a stable
  final-line identifier *"is the entire interface, and it is why composition needs no framework"*,
  and that routing contracts use a closed vocabulary and *"Fail safe, never guess."* This paper does
  not reopen the *return* contract; it addresses the *call* contract.
- **Fork vs parameterize.** [`fork_vs_parameterize_drift_signal.md`](./fork_vs_parameterize_drift_signal.md)
  (`Last validated: 2026-08-17`, `Revalidate: high — 6 weeks`, due 2026-09-28, **current**,
  `Critic: PASS-WITH-FIXES`) settles the Phase 2 question of telling a deliberate variant from a
  neglected copy. It is cited here only where a Phase 3 recommendation would create a second copy.
- **The parameterize-vs-fork general question** is [`workflow_reuse_boundary.md`](../../../../standards/architecture/research/raw/workflow_reuse_boundary.md)
  (upstream pool, `Last validated: 2026-08-03`, `high — 6 weeks`, due 2026-09-14, current).
- **Agents are not independently retryable**, and **retry/resumption inside children belongs to the
  Temporal port.** Both are operator rulings recorded in [`roadmap.md`](../../roadmap.md) § *What is
  deliberately not built*. Nothing below proposes otherwise.

### 1.3 Currency of the internal evidence this paper leans on

Checked at authoring time; all inside their windows.

| Paper | Last validated | Revalidate | Due | Critic |
|---|---|---|---|---|
| `fork_vs_parameterize_drift_signal.md` (this pool) | 2026-08-17 | high — 6 weeks | 2026-09-28 | PASS-WITH-FIXES |
| `claude_code_integration_surface.md` (upstream) | 2026-07-25 | high — 4 weeks | 2026-08-22 | PASS |
| `paperclip_assessment.md` (upstream) | 2026-08-04 | high — 4 weeks | 2026-09-01 | PASS-WITH-FIXES |
| `openclaw_assessment.md` (upstream) | 2026-08-06 | high — 3 weeks | 2026-08-27 | PASS |
| `hermes_assessment.md` (upstream) | 2026-08-06 | high — 3 weeks | 2026-08-27 | PASS-WITH-FIXES |
| `workflow_reuse_boundary.md` (upstream) | 2026-08-03 | high — 6 weeks | 2026-09-14 | PASS-WITH-FIXES |

`claude_code_integration_surface.md` is **four days from its window** at the time of writing. A
consumer reading this paper after 2026-08-22 should treat §4.3's corroborating citation to it as
unverified until that paper is refreshed — the `claude --help` observation in §4.3 is independent of
it and does not decay on the same clock.

---

## 2. The specific model / options — what the landscape actually offers

### 2.1 Facet 1 — one unit, two callers *(slow-decaying section)*

The field offers four shapes. They are not mutually exclusive; the strongest systems use two or
three together.

#### Option A — one entrypoint, runtime mode detection

The unit sniffs its environment and adapts. The canonical sniff is the terminal check. The Command
Line Interface Guidelines state it plainly [S1]:

> The most simple and straightforward heuristic for whether a particular output stream (`stdout` or `stderr`) is being read by a human is _whether or not it’s a TTY_.

and applies it to interactivity [S1]:

> **Only use prompts or interactive elements if `stdin` is an interactive terminal (a TTY).**

*(definitive — raw markdown, both spans `grep -F`-verified.)*

**What it buys:** one entrypoint, one contract, zero duplication. **What it costs:** the behaviour
changes under a pipe, which is precisely the condition under which a parent calls a child — so the
mode the child runs in under a parent is the mode a human almost never sees.

#### Option B — the caller DECLARES the context

The caller passes the answer instead of letting the callee guess. The same guide pairs every sniff
with an explicit flag [S1]:

> **If `--no-input` is passed, don’t prompt or do anything interactive.**

Git goes further and lets the caller override the sniff *for the sniff's own subject*: `git config`
exposes [S2]

> `--get-colorbool <name> [<stdout-is-tty>]::`

— i.e. a wrapper that knows better than `isatty()` can supply the tty-ness as an argument.
*(definitive — raw `git-config.adoc`, span `grep -F`-verified.)*

**Derived (inputs: [S1] `--no-input`; [S2] `--get-colorbool`; [S1]'s stdout/stderr split): every
first-party source found here treats detection as a DEFAULT and the caller's declaration as the
AUTHORITY.** No source found recommends detection alone. That asymmetry is the whole finding for
Option A vs B, and it is carried in the header as a negative finding; **its search method and its
narrowness are stated in §6.1**, which is where a reader should decide how much weight it bears.

#### Option C — two entrypoints over one shared core

The unit is a library function; each caller gets a thin adapter. This is Temporal's model at the
architectural altitude, and it is where this fleet is going [S12]:

> A Child Workflow Execution is a [Workflow Execution](/workflow-execution) that is spawned from within another Workflow in the same Namespace.

> A Workflow Execution can be both a Parent and a Child Workflow Execution because any Workflow can spawn another Workflow.

*(definitive — raw `.mdx`, read directly out of the fetched byte stream.)*

**The load-bearing property: child-ness is a RELATIONSHIP, not a TYPE.** The same Workflow Definition
is started by a Client or by another Workflow, and nothing about the definition changes. This is the
same rule [`workflow-scripts.md`](../../../../standards/workflow-scripts.md) already states for this
fleet — *"a child workflow is not a kind of file in a place, it is **a workflow that another workflow
starts**"* — and it is why the standard says not to build conventions that depend on `children/`
surviving the port.

#### Option D — an injected context object

Instead of a boolean mode, the caller hands in the capabilities: where to log, how loud, whether it
may prompt. Twelve-Factor's §III is the general statement of why this beats ambient discovery [S4]:

> Apps sometimes store config as constants in the code.  This is a violation of twelve-factor, which requires **strict separation of config from code**.  Config varies substantially across deploys, code does not.

*(definitive — raw markdown.)*

**Derived ranking (inputs: [S1], [S2], [S12], [S4], and the local shape measured in §5.1): C is the
structural answer and B is the behavioural one, applied together; A is a default of last resort; D
is what B degenerates into when the number of context values passes about three.** C alone does not
help — two adapters can still print different things — which is why B is needed on top of it.

#### What actually breaks — the enumerated failure surface

Every item here has a first-party citation; none is speculative.

| # | Breakage | Evidence |
|---|---|---|
| F1 | **Output verbosity inverts by caller.** A default tuned for scripts is wrong for humans and vice versa | [S1]: *"Traditionally, when nothing is wrong, UNIX commands display no output to the user."* / *"This makes sense when they’re being used in scripts, but can make commands appear to be hanging or broken when used by humans."* and *"**Make the default the right thing for most users.**"* |
| F2 | **Exit-code semantics** — the parent's only cheap signal | [S1]: *"Return zero exit code on success, non-zero on failure."* |
| F3 | **Interactive prompts block a non-interactive caller** | [S1]: *"**Only use prompts or interactive elements if `stdin` is an interactive terminal (a TTY).**"* |
| F4 | **Stream discipline** — machine output and log messages must not share a channel | [S1]: *"Anything that is machine readable should also go to `stdout`—this is where piping sends things by default."* |
| F5 | **Working-directory assumptions.** cwd is the caller's, not the unit's | §5.2 below: `preflight.resolve_repo_root`'s docstring — *"The repository ROOT, never the directory the operator happened to be in."* Six of seven V2 entrypoints had dropped this |
| F6 | **Environment leakage** — the unit absorbs config from the ambient environment | Facet 3, §2.3 and §4.3 |
| F7 | **The contract itself is an interface and cannot be changed casually** | [S1]: *"Subcommands, arguments, flags, configuration files, environment variables: these are all interfaces, and you’re committing to keeping them working."* |

*(F1–F4, F7 definitive from raw markdown, each span `grep -F`-verified. F5 definitive from a local
file read. F6 is a pointer, not a claim.)*

#### How the difference is kept OUT of the core

The measured answer in this repo is a one-line shim over a runner over a workflow function; see
§5.1. The general statement is Temporal's warning against using the composition mechanism for
organisation [S12]:

> There is no reason to use Child Workflows just for code organization.

and the reason the boundary is real when it *is* used [S12]:

> However, this also means that a Parent Workflow Execution and a Child Workflow Execution do not share any local state.

*(definitive — raw `.mdx`.)* That second sentence is the same fresh-context argument
[`workflow-scripts.md`](../../../../standards/workflow-scripts.md) § *Why compose at all* makes for
`author ≠ judge`, arrived at from durability rather than from bias.

### 2.2 Facet 2 — scope from the target, not from a flag *(slow-decaying section)*

#### The two positions, both first-party

**For derivation.** The Rails Doctrine is the canonical statement [S5]:

> Not only does the transfer of configuration to convention free us from deliberation, it also provides a lush field to grow deeper abstractions.

> The power of good conventions is that they pay dividends across a wide spectrum of use.

> Part of the Rails’ mission is to swing its machete at the thick, and ever growing, jungle of recurring decisions that face developers creating information systems for the web.

*(reduced-but-verified — only a rendered page exists; all three spans confirmed with `grep -F`
against the raw HTML bytes.)*

**Against derivation.** PEP 20, line 24 [S6]:

> Explicit is better than implicit.

and line 30, which is the clause people forget:

> Special cases aren't special enough to break the rules.

*(definitive — raw `.rst`.)*

#### What makes a derived value safe — the four shipped mechanisms

The field has converged, and the convergence is more specific than "validate it."

**M1 — Anchor on a MARKER, never on a heuristic.** Bazel [S7]:

> A repo is a directory tree with a boundary marker file at
> its root; such a boundary marker file could be `MODULE.bazel`, `REPO.bazel`, or
> in legacy contexts, `WORKSPACE` or `WORKSPACE.bazel`.

> A package is defined as a directory containing a
> [`BUILD` file](/concepts/build-files) named either `BUILD` or `BUILD.bazel`.

and the invariant that falls out of it:

> From this definition, no
> file or directory may be a part of two different packages.

*(definitive — raw markdown, read out of the byte stream.)*

**M2 — Publish a DETERMINISTIC, WRITTEN-DOWN algorithm.** pytest documents rootdir derivation as a
numbered procedure, and states its own fallback [S8]:

> Determine the common ancestor directory for the specified ``args`` that are recognised as paths that exist in the file system. If no such paths are found, the common ancestor directory is set to the current working directory.

**M3 — REPORT what was derived, unprompted.** pytest again [S8]:

> pytest determines a ``rootdir`` for each test run which depends on
> the command line arguments (specified test files, paths) and on
> the existence of configuration files.  The determined ``rootdir`` and ``configfile`` are
> printed as part of the pytest header during startup.

**M4 — Provide an explicit OVERRIDE, and state its limits honestly** [S8]:

> The :option:`--rootdir=path` command-line option can be used to force a specific directory.
> Note that contrary to other command-line options, ``--rootdir`` cannot be used with
> :confval:`addopts` inside a configuration file because the ``rootdir`` is used to *find* the configuration file
> already.

**M5 — Bound the blast radius by saying what the derived value is NOT used for** [S8]:

> ``rootdir`` is **NOT** used to modify ``sys.path``/``PYTHONPATH`` or
> influence how modules are imported.

*(M2–M5 definitive — raw `.rst`, read out of the byte stream; the header-printing span was
`grep -F`-verified after a summarizing fetch had silently stripped its double-backtick markup, which
is why it is quoted from the raw form.)*

**Derived (inputs: M1–M5 plus git's own marker-file derivation, §5.2): the rule is ANCHOR, DON'T
GUESS.** A derived value is safe when (a) it terminates on a marker whose presence is a fact rather
than a similarity judgement, (b) the algorithm is published, (c) the result is echoed back, (d) an
override exists, and (e) the scope of what it controls is stated. M4's parenthetical is the honest
part: an override on a derived value can be *unrepresentable* in the very config the derivation
finds. That circularity is intrinsic and is the strongest single argument in §6.2.

### 2.3 Facet 3 — managed config with a user tier beside it *(slow-decaying section, except §4.3)*

Seven systems were read for this facet. **Five ship a documented precedence model — git, npm,
systemd, VS Code and Claude Code — and four of those five also ship provenance. Two of the seven
ship drift classification (systemd, chezmoi); one ships a machine-checkable agreement proof
(chezmoi); and one supplies the digest primitive that proof implies (Nix).** That distribution is
the finding. The precedence table immediately below covers the five that have precedence; chezmoi
and Nix enter two subsections later, where the question narrows to drift and agreement — which is
why §3.3's comparative table has seven rows and this sentence used to say five.

#### Precedence — and the direction is NOT universal

| System | Order (winner last) | Who wins |
|---|---|---|
| **git** [S2] | system `$(prefix)/etc/gitconfig` → user `~/.gitconfig` → repo `$GIT_DIR/config` → `config.worktree` → `-c` | **the local/user side** |
| **npm** [S3] | built-in → global `$PREFIX/etc/npmrc` → per-user `$HOME/.npmrc` → per-project `.npmrc` → env `npm_config_*` → flags | **the local/user side** |
| **systemd** [S10] | `/usr/lib/systemd/system` (vendor) → `/run/systemd/system` → `/etc/systemd/system` (admin) | **the local ADMIN side, over the vendor** |
| **VS Code** [S11] | default → user → remote → workspace → folder → language-specific variants → **Policy** | **the ORG POLICY side, over everything** |
| **Claude Code** [S13][S14] | user → project → local → CLI args → **Managed** | **the ORG POLICY side, over everything** |

git states the rule [S2]:

> The files are read in the order given above, with last value found taking
> precedence over values read earlier.

systemd states it for drop-ins [S10]:

> Drop-in files in <filename>/etc/</filename>
> take precedence over those in <filename>/run/</filename> which in turn take precedence over those
> in <filename>/usr/lib/</filename>. Drop-in files under any of these directories take precedence
> over unit files wherever located. Multiple drop-in files with different names are applied in
> lexicographic order, regardless of which of the directories they reside in.

VS Code states the top of its stack [S11]:

> Policy settings - Set by the system administrator, these values always override other setting values.

*(all three definitive — raw sources, each `grep -F`-verified.)*

> **This is the central derived claim of facet 3, and it is a policy question wearing a technical
> costume.** *(derived — inputs: the five rows above.)* The field runs **two opposite precedence
> directions**, and which one a system uses depends entirely on **who the "managed" party is**:
>
> - When managed means **the vendor's packaged defaults**, the local tier WINS (systemd: `/etc` beats
>   `/usr/lib`; git: `~/.gitconfig` beats `/etc/gitconfig`; npm: `.npmrc` beats `$PREFIX/etc/npmrc`).
> - When managed means **organizational policy**, the managed tier wins and cannot be overridden
>   (VS Code Policy; Claude Code Managed).
>
> **Phase 3's roadmap line — *"the user keeps a tier they own and can extend"* — is the FIRST shape,
> not the second.** claude-dot-files is a vendor-package, not a policy. A design that reaches for
> Claude Code's Managed tier because it is called "managed" would silently adopt the second shape and
> take away the very tier the checkbox promises the user. §4.3 gives the one narrow exception where
> the policy tier is the right answer.

#### Provenance — four of five ship it

- **git** [S2] — `--show-origin`: *"Augment the output of all queried config options with the"* / *"origin type (file, standard input, blob, command line) and"* the actual origin; and `--show-scope`, which augments *"all queried config options with the scope of that value"* / *"(worktree, local, global, system, command)."*
- **systemd** [S15] — `systemd-analyze cat-config` *"will copy the contents of a config file and any drop-ins to standard output, using the usual systemd set of directories and rules for precedence"*, emitting each source file's path as a comment above its contribution.
- **npm** [S3] — *"Run `npm config ls -l` to see a set of configuration parameters that are internal to npm, and are defaults if nothing else is specified."* Weakest of the four: it shows the effective set, not the origin of each value.
- **VS Code** [S11] — the `@modified` filter: *"A setting shows up under this filter if its value differs from the default value, or if its value is explicitly set in the respective settings JSON file."*
- **Claude Code** — **no equivalent found.** There is no documented flag that prints the effective merged settings with per-key origin. Stated as a gap; search method in §6.4.

*(git, npm, VS Code spans `grep -F`-verified; systemd span read out of the raw XML byte stream. All definitive.)*

#### Drift classification — two ship it, and one of them classifies

`systemd-delta` exists for exactly this job [S16]:

> <command>systemd-delta</command> may be used to identify and
> compare configuration files that override other configuration
> files.

and it does not merely diff — it **types** the drift, with `--type=` taking `masked`, `equivalent`,
`redirected`, `overridden`, `extended`, `unchanged`. The distinction that matters most here is
`equivalent`, documented as *"Show overridden files that while overridden, do not differ in
content."* **An override that changes nothing is a different finding from an override that changes
something**, and a drift detector that cannot say which produces noise.

chezmoi's `status` runs a **three-way** comparison rather than two-way: *"The first column of output
indicates the difference between the last state written by chezmoi and the actual state. The second
column indicates the difference between the actual state and the target state, and what effect
running [`chezmoi apply`][apply] will have."* [S17]

*(both definitive — raw sources read out of the byte stream.)*

#### Proving two machines agree — one system ships an answer, one ships the primitive

**chezmoi `verify` is a machine-checkable agreement proof** [S17]:

> Verify that all *target*s match their target state. chezmoi exits with code 0
> (success) if all targets match their target state, or 1 (failure) otherwise. If
> no targets are specified then all targets are checked.

It also separates the two tiers by enumeration rather than by convention: `managed` *"List all
managed entries in the destination directory"*, `unmanaged` *"List all unmanaged files in *path*s."*
And it states the desired-state model directly: *"You declare the desired state of files,
directories, and symbolic links in your source of truth and chezmoi updates your home directory to
match that state."*

**Nix supplies the primitive chezmoi's exit code implies** — a single opaque value that stands for
the whole content [S18]:

> Think of a store path base name as an [opaque], [unique identifier]:
> The only way to obtain a store path base name is by adding or building store objects.
> A store path base name will always reference exactly one store object.

*(both definitive — raw markdown read out of the byte stream.)*

**Derived (inputs: chezmoi `verify`/`managed`/`unmanaged`; Nix store-path digest; systemd-delta's
type taxonomy; git `--show-origin`): "prove two machines agree" decomposes into three separable
capabilities, and they can be built in any order.** (i) a **digest** of the managed set, so
agreement is one comparison rather than N; (ii) an **enumeration** of what is managed vs not, so the
unmanaged tier is visible rather than invisible; (iii) a **typed diff** for the cases that disagree,
so `equivalent` does not read the same as `overridden`. Only (i) needs to exist before a run can
record what it used.

---

## 3. Comparative landscape — the alternatives, fairly stated

### 3.1 Facet 1

| Pattern | Where it ships | Strength | Honest weakness |
|---|---|---|---|
| **A — mode detection** | `ls`, `git color.ui`, most CLIs [S1][S2] | zero caller burden; correct for the common case | the behaviour under a pipe is the one nobody tests, and that is the parent's path |
| **B — caller declares** | `--no-input` [S1], `--get-colorbool <stdout-is-tty>` [S2] | deterministic; testable; the parent gets what it asked for | every context value is a new flag; the flag set grows |
| **C — two entrypoints, one core** | Temporal Client-vs-Parent start [S12]; this fleet's shim→runner→workflow [§5.1] | child-ness becomes a relationship, not a type; the core cannot diverge | two adapters can still print differently — C does not solve F1–F4 on its own |
| **D — injected context object** | Twelve-Factor config-as-environment [S4] | one parameter, arbitrarily rich; testable by construction | over-general early; a `Context` with three booleans is three flags with extra ceremony |

**A fair statement of the case for A, which this paper does not adopt:** detection is the only option
that requires nothing of existing callers. Every caller of a unit that switches from A to B must be
updated, and [S1] itself notes that flags are an interface you commit to keeping working. For a unit
with many external callers, A is the right answer. **This fleet has few callers and controls all of
them**, which is what tips it.

### 3.2 Facet 2

| Position | Where it ships | Strength | Honest weakness |
|---|---|---|---|
| **Derive from the target** | Rails CoC [S5]; Bazel packages [S7]; pytest rootdir [S8]; git repo-root discovery [S2] | one source of truth; a path cannot disagree with itself | the derivation is invisible until it is wrong, and then it is wrong somewhere the user did not look |
| **Declare explicitly** | PEP 20 [S6]; Bazel's explicit deps [S7]; this fleet's `--repo` [§5.2] | debuggable; greppable; no hidden coupling | two statements of one fact can disagree — the exact hazard Phase 3's checkbox names |
| **Derive, then ECHO** | pytest header [S8]; chezmoi `managed` [S17] | keeps the single source of truth AND makes it inspectable | costs output the machine caller must be able to suppress — which is facet 1's F1 |

**The strongest counter-case, stated fully:** this repo has already ruled derivation OUT for one
value and was right to. `run_review_pr.py` declares `--repo` with the help string *"target repo —
explicit identity, never derived from cwd"*, and `run_plan_feature.py` / `run_plan_project.py` /
`run_research.py` each declare it as *"target repo — a FILESYSTEM PATH, never a gh slug"* (§5.2).
**Repo identity is declared; component scope is derived.** Any Phase 3 rule that says "derive
everything" contradicts a shipped, deliberate decision.

### 3.3 Facet 3

| Approach | Precedence | Provenance | Drift typing | Agreement proof |
|---|---|---|---|---|
| **git** [S2] | yes, local-wins | yes (`--show-origin`, `--show-scope`) | no | no |
| **npm** [S3] | yes, local-wins | partial (`npm config ls -l`) | no | no |
| **systemd** [S10][S15][S16] | yes, admin-wins-over-vendor | yes (`cat-config`) | **yes, six types** | no |
| **VS Code** [S11] | yes, policy-wins | partial (`@modified`) | no | Settings Sync moves the files; it does not prove they match |
| **chezmoi** [S17] | source-of-truth + templates | yes (`managed`/`unmanaged`) | yes (three-way `status`) | **yes (`verify`, exit 0/1)** |
| **Nix** [S18] | n/a (whole-system) | digest | n/a | **digest equality** |
| **Claude Code** [S13][S14] | yes, policy-wins | **not found** | no | no |

**The fair case against building any of this**, which §6.3 develops: **the entire divergence-detection
half may be unnecessary if the run bag records what a run used.** Phase 3's own roadmap line states
that gate. §5.3 measures exactly how far the bag is from that today, and the answer is: five tag
lines, none of which names the config.

---

## 4. What this provides — enumerated, citable properties

These are the claims a Phase 3 plan may cite. Each carries its confidence class and its inputs.

### 4.1 Facet 1 — dual-mode

- **P1 *(derived — inputs [S1], [S2], [S12], §5.1)*.** The dual-mode answer is **C + B**: one core
  function, thin adapters per caller, and every context difference passed as an **explicit
  parameter** rather than detected. Mode detection (A) is acceptable only as the *default value* of
  a parameter that a caller can always override.
- **P2 *(definitive — [S12])*.** Child-ness is a relationship, not a type. Nothing in a child's
  definition may branch on "am I a child." This is already the destination architecture's rule and
  already this fleet's stated rule.
- **P3 *(definitive — [S1])*.** The enumerated dual-mode failure surface is F1–F7 (§2.1). A Phase 3
  acceptance test that does not exercise F1, F2, F3 and F5 for a given child has not tested
  dual-mode; it has tested one mode twice.
- **P4 *(derived — inputs [S1] F1/F2/F4, §5.1)*.** The minimum context parameter set for this fleet
  is three values, and all three already exist somewhere in the tree: `verbose` (F1), the log
  destination (F4), and the working root (F5). Exit codes (F2) need no parameter — they need a test.
- **P5 *(definitive — §5.1)*.** The shim→runner→core shape already implemented for all eleven
  runners is pattern C, correctly. **The gap is not the structure; it is that nine of twenty workflow
  modules have no runner at all**, so pattern C is unavailable to them. Enumeration in §5.1.

### 4.2 Facet 2 — scope from the target

- **P6 *(derived — inputs M1–M5, §2.2)*.** A derived value is safe to trust when all five hold:
  **anchor on a marker** (M1), **published algorithm** (M2), **echo the result** (M3), **explicit
  override** (M4), **stated scope of effect** (M5). Fewer than five is a partial answer, and the one
  most often skipped is M3.
- **P7 *(definitive — §5.2)*.** `plan-feature` already derives component scope from a positional
  path, and `plan-project` already passes a re-anchored component path to it. M1 and M4 are
  satisfied today (`RepoPathParser` anchors on the git root; `--repo` is the override). **M2, M3 and
  M5 are not.** That is the actual Phase 3 work item.
- **P8 *(definitive — §5.2)*.** The derivation is already containment-checked, and the check is
  structural rather than remembered: `add_repo_path` writes the dest into a registry and
  `parse_with_preflight` resolves every dest in it, so *"A runner cannot accept a repo path through
  this parser and skip the check, because there is no step between the two to forget."* A Phase 3
  design that adds a new derived path must declare it through that parser or it inherits none of
  this.
- **P9 *(derived — inputs §3.2, `run_review_pr.py`, `run_plan_feature.py`)*.** **Derivation is
  per-value, never a policy.** This fleet already derives component scope and explicitly refuses to
  derive repo identity. A Phase 3 rule must be written per-value with its reason, not as "prefer
  derivation."
- **P10 *(definitive — [S8] M4)*.** An override on a derived value can be unrepresentable in the
  configuration the derivation locates. pytest documents exactly this for `--rootdir` in `addopts`.
  Any override this fleet adds must be reachable **before** the derived value is used.

### 4.3 Facet 3 — managed config plus a user tier *(FAST-DECAYING — re-verify this subsection first)*

- **P11 *(derived — inputs: the five-row precedence table, §2.3)*.** The precedence direction is a
  policy choice. Phase 3's stated intent — a managed set plus *"a tier they own and can extend"* —
  is the **vendor-package** shape (systemd/git/npm), where the local tier wins, **not** the
  **policy** shape (VS Code Policy, Claude Code Managed), where it cannot.
- **P12 *(definitive — [S13], `claude --help`, v2.1.234 observed locally 2026-08-18)*.** Claude Code
  already ships three levers over what a run absorbs from `~/.claude/`, and their exact help text is:
  - `--setting-sources <sources>` — *"Comma-separated list of setting sources to load (user, project, local)."*
  - `--bare` — *"Minimal mode: skip hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, and CLAUDE.md auto-discovery. … Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings (OAuth and keychain are never read)."*
  - `--safe-mode` — *"Start with all customizations (CLAUDE.md, skills, plugins, hooks, MCP servers, custom commands and agents, output styles, workflows, custom themes, keybindings, and more) disabled — useful for troubleshooting a broken configuration. **Admin-managed (policy) settings still apply.** Auth, model selection, built-in tools, and permissions work normally."*

  > **One normalization applies to all three spans above, named so they are not over-read.**
  > `claude --help` wraps its right-hand column to the terminal width, so each of these appears in the
  > raw output broken across several lines with leading padding. **The character sequences are quoted
  > with those wraps collapsed to single spaces and the padding removed; no word was changed, added or
  > dropped.** Anyone re-verifying should compare against `claude --help` token-by-token rather than
  > with `grep -F` on the whole span, which will not match for this reason alone.
- **P13 *(definitive — [S13] plus [`workflow-scripts.md` § The safety-layer invariant](../../../../standards/workflow-scripts.md), corroborated by §5.3)*.** `--bare` is **unusable for this
  fleet as it stands**: it skips hooks — which the safety-layer invariant makes the sole live control
  in a headless run — and it refuses OAuth and keychain reads, which is the subscription credential
  this whole edge runs on ([`problem-statement.md`](../../../../standards/architecture/problem-statement.md)
  § *Affordability is the enabler*). The upstream integration paper's recommendation to *"Use `--bare`
  … so a run is reproducible independent of whatever is in `~/.claude`"*
  ([`claude_code_integration_surface.md`](../../../../standards/architecture/research/raw/claude_code_integration_surface.md)
  §8) is correct for an API-keyed worker and **does not transfer to a subscription-backed edge**.
  Stated here so a planner does not adopt it by citation.
- **P14 — the highest-value finding in this facet *(DERIVED, and flagged for measurement — inputs:
  [S13]'s `--setting-sources` enumerating only `user, project, local`; [S13]'s `--safe-mode` text
  *"Admin-managed (policy) settings still apply"*; [S14]'s precedence placing Managed above CLI
  args)*.** **Declaring the safety hook in the MANAGED tier would make it immune both to
  `--setting-sources` and to `--safe-mode`.** That is a direct route out of the blocker recorded in
  `test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in`, whose own docstring says
  *"The Managed Configuration sprint carries that flag as a candidate mechanism, and its own
  checkbox says the safety blocker must be resolved BEFORE the flag is touched."* **This is an inference across three sources, one of which
  is a rendered page — it MUST be measured before it is relied on.** Test T2 in §7. The safety-layer
  invariant already demands demonstration before landing, and this is exactly the demonstration it
  means.
- **P15 *(definitive — §5.3)*.** The current managed tier is **seven symlinks and no version
  identity**. `install.sh` verifies that each symlink resolves to the expected source path and
  nothing else: a grep of `install.sh` for `rev-parse|sha|commit|version|hash` returns **0**. Two
  machines can both pass `install.sh`'s verification while running different content.
- **P16 *(definitive — §5.3)*.** The run bag records five `Journal-` info tags —
  `Journal-Workflow`, `Journal-Origin-Repo`, `Journal-Origin-Remote`, `Journal-Origin-Commit`,
  `Journal-Worktree` — and **none of them names the configuration the run used.**
  `Journal-Origin-Commit` is the *target repo's* commit. For a dispatch against any repo other than
  claude-dot-files itself, the config commit is unrecorded. **The PMP Part 1 gate is therefore NOT
  satisfied today**, and closing it is one additional info tag, not a subsystem.
- **P17 *(derived — inputs: chezmoi `verify`/`managed`/`unmanaged` [S17]; Nix digest [S18];
  systemd-delta types [S16]; git `--show-origin` [S2])*.** The mechanism set decomposes into three
  independently shippable pieces — digest, enumeration, typed diff — and **only the digest is needed
  before a run can record what it used.** This is the cheapest possible first increment and it
  discharges P16.
- **P18 *(directional — single rendered source [S14], no verbatim span)*.** Claude Code's managed
  tier reportedly supports a drop-in directory (`managed-settings.d/`) alongside the single file, on
  all three platforms. If true this is systemd's exact shape and would let a managed base and a
  local extension coexist without a merge step. **Not verified; do not design on it.** Test T8.

### 4.4 Cross-facet

- **P19 *(derived — inputs: [S1] F7; [`workflow-scripts.md`](../../../../standards/workflow-scripts.md)
  § Naming; [`fork_vs_parameterize_drift_signal.md`](./fork_vs_parameterize_drift_signal.md))*.** Any
  Phase 3 change that adds a per-child adapter risks creating the near-duplicate class Phase 2 is
  still closing. The shim test (`test_shim_usage_names_itself.py`) exists because exactly that
  happened: *"Three V2 entry scripts — `research.sh`, `build_minor.sh` and `plan_sprint.sh` —
  carried usage blocks reading `./build.sh`, nine wrong lines copied from the file they were cloned
  from and never renamed."* **Adding nine new adapters (P5) without a corresponding guard would
  reintroduce it at three times the scale.**

---

## 5. Local grounding — measured in this repo, by this analyst

All commands run at commit `128091c` from the repository root. Each count is the output of the
command quoted beside it; nothing here is a remembered figure.

### 5.1 Facet 1 — the dual-mode gap is nine missing adapters, not a wrong structure

```
$ find scripts/workflows/temporal/modules -name '*_workflow.py' | wc -l
20
$ ls -1 scripts/workflows/temporal/scripts/run_*.py | wc -l
11
$ ls -1 scripts/workflows/temporal/scripts/*.sh | wc -l
11
$ comm -13 <(ls -1 scripts/workflows/temporal/scripts/run_*.py | sed 's#.*/run_##;s#\.py##' | sort) \
           <(find scripts/workflows/temporal/modules -name '*_workflow.py' | sed 's#.*/##;s#_workflow\.py##' | sort)
build_draft
build_draft_minor
build_refine
build_refine_minor
research_refresh
research_refresh_parent
research_verify
research_write
research_write_minor
```

**Twenty workflow modules; eleven runners; eleven shims, 1:1 with the runners; nine modules with no
same-named runner.** The nine are, without exception, the children. The shim is deliberately thin —
`plan_feature.sh` in full:

```
# Thin by design: it resolves the interpreter and hands every argument through
# untouched. Argument parsing lives in run_plan_feature.py so there is exactly
# one place that defines the CLI contract.
…
exec python3 "${SCRIPT_DIR}/run_plan_feature.py" "$@"
```

and the parent calls the core function directly, never the runner —
`plan_project_workflow._plan_one`:

```python
    repo_component = repo_root / component_root.relative_to(worktree)
    feature.run_plan_feature(
        repo_root=repo_root, worktree=worktree, component=repo_component,
        candidates_path=candidates_path, pr_number=pr, verbose=verbose,
    )
```

**That is pattern C, correctly, with `verbose` (F1) passed as an explicit parameter (pattern B) rather
than detected.** The gap is that only the eleven parents/monoliths have the standalone half.
*(definitive — enumerated above; file contents read locally.)*

**One roadmap wording correction, offered as a finding rather than an edit.** Roadmap Phase 3 says
*"`research_refresh_parent` has no entrypoint — a parent nothing can invoke."* At `128091c` it **is**
invocable: `run_research.py` imports it and dispatches to it on `--refresh` —

```python
        result = rr.run_research_refresh(research_dir=research_dir, repo_root=repo_root,
                                         worktree_name=wt, verbose=a.verbose) if a.refresh \
            else rw.run_research(…)
```

The accurate statement is narrower and still a real defect: **it has no entrypoint of its own** —
there is no `research_refresh.sh` and no `run_research_refresh.py`, so it is reachable only as a
*mode of another workflow's* CLI, and its name does not appear at the shell. A planner should fix the
wording before decomposing the item, or the fix will be scoped to the wrong thing.
*(definitive — the shim enumeration above shows no `research_refresh.sh`; the dispatch line is read
from the file.)*

### 5.2 Facet 2 — derivation shipped; the reporting half did not

`run_plan_feature.py` declares the component as a positional **path**:

```python
    p.add_repo_path("component", kind="dir",
                    help="the component directory, e.g. docs/development/fleet-reliability")
```

and repo identity as an explicit, never-derived flag — the same string appears in
`run_plan_feature.py`, `run_plan_project.py` and `run_research.py`:

```python
    p.add_argument("--repo", dest="repo_target", help="target repo — a FILESYSTEM PATH, never a gh slug")
```

while `run_review_pr.py` says it with the reason attached:

```python
    parser.add_argument("--repo", dest="repo_target",
                        help="target repo — explicit identity, never derived from cwd")
```

**M1 (anchor on a marker) is satisfied by `preflight.resolve_repo_root`,** which is git's own
marker-file derivation and which documents the failure it prevents:

> The repository ROOT, never the directory the operator happened to be in.
>
> V1 did `REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT"` and
> USED the answer rather than just its exit code. Six of seven V2 entrypoints
> dropped that and kept `Path.cwd()`.

**M4 (explicit override) is satisfied by `--repo`.** **M2, M3 and M5 are not**: there is no published
statement of how feature scope relates to the project chain, no banner line echoing what was derived
(the `--dry-run` path prints the component, but the live path does not), and no statement of what the
derived component controls. `plan-feature`'s `--dry-run` does prove the *rendering* is shared —

```python
            # THE SAME ASSEMBLY THE LIVE RUN USES, called rather than copied. A
            # dry run that builds its own values dict previews a prompt that is
            # not the one dispatched — the family has shipped that bug once
            # already (see `plan_sprint`'s `correction_note`)
```

— which is M3 applied to the prompt but not to the derivation.
*(definitive — all spans read locally from the named files.)*

### 5.3 Facet 3 — seven links, no identity, and a bag that does not record it

```
$ find ~/.claude -maxdepth 1 -type l -printf '%f -> %l\n' | sort
CLAUDE.md -> /home/puma/Repos/claude-dot-files/config/CLAUDE.md
agents -> /home/puma/Repos/claude-dot-files/config/agents
commands -> /home/puma/Repos/claude-dot-files/config/commands
hooks -> /home/puma/Repos/claude-dot-files/config/hooks
rules -> /home/puma/Repos/claude-dot-files/config/rules
settings.json -> /home/puma/Repos/claude-dot-files/config/settings.json
skills -> /home/puma/Repos/claude-dot-files/config/skills
$ find ~/.claude -maxdepth 1 -type l | wc -l
7
$ grep -c -i -E 'rev-parse|sha|commit|version|hash' install.sh
0
$ grep -rn -- '--setting-sources' scripts/ | grep -v '^\s*#' | wc -l
0
$ grep -c '"Journal-' scripts/workflows/temporal/modules/journal/journal_activities.py
5
```

**Seven symlinks, matching the seven `SYMLINK_TARGETS` declared in `install.sh`.** The verification
loop checks link identity only:

```bash
    if [ -L "$target_path" ] && [ "$(readlink -f "$target_path")" = "$(readlink -f "$source_path")" ]; then
        info "$item ✓"
```

Every link points into the **main working tree** of `claude-dot-files`, not into a pinned checkout —
so the effective config of every dispatch on this machine is whatever is on disk in that repo at that
moment, including uncommitted edits. Both of the safety hook's halves ride this: the declaration
lives in `config/settings.json` (user scope, symlinked), and the command it names is
`$HOME/.claude/hooks/block-dangerous.sh`, which is itself a path through a symlink into the same
unpinned tree. **Two independent unversioned dependencies for the one live safety control.**

The run bag's info tags, in full:

```python
    return open_bag(root, run_id, info={
        "Journal-Workflow": workflow_key,
        "Journal-Origin-Repo": str(repo_root),
        "Journal-Origin-Remote": remote or "-",
        "Journal-Origin-Commit": commit or "-",
        "Journal-Worktree": worktree_name or "-",
    })
```

**No tag names the config.** The gate in Phase 3's roadmap line — *"if the run bag records the config
a run used, the divergence half shrinks to a reader"* — is open, and the increment that closes it is
one tag carrying the digest from P17(i).
*(all definitive — commands and outputs above; file contents read locally.)*

---

## 6. Honest boundary analysis — the case against this paper

### 6.1 The dual-mode recommendation may be solving a problem this fleet does not have

**P1 says "explicit parameters, not detection." But the fleet already does that**, and §5.1 shows
the structure is already pattern C with `verbose` threaded as a parameter. The measured gap is nine
missing *adapters* — a mechanical job — not a wrong pattern. **A planner who reads §2.1 and
decomposes a "dual-mode design" is decomposing a design that already exists.**

And the nine missing adapters may be **correct as they stand.**
[`workflow-scripts.md`](../../../../standards/workflow-scripts.md) already rules: *"Running one by
hand is recovery — a failed review half, or a PR whose producer is not yet a parent — never the
interface."* If standalone invocation of a child is *recovery only*, then nine children without
shells is a deliberate narrowing of the operator's foot-gun surface, not a defect — and Phase 3's
checkbox *"Every child runs standalone and under a parent, equally well"* is in tension with a rule
the same repo already ratified. **This paper cannot resolve that tension; it is a ruling, not a
finding.** It is stated here so the planner rules on it explicitly rather than inheriting one side
by accident.

**Also stated against the paper's own framing:** the negative finding in the header — that no
first-party source was found recommending TTY-sniffing *without* an explicit caller-supplied override
— rests on **two** sources, not a survey. Search method: [S1] read in full and grepped for `TTY`,
`--no-input`, `interactive`, `script`, `robot`; [S2] grepped for `tty`, `colorbool`, `color.ui`. Both
pair detection with an override. **Two is a thin base for a negative.** It means "not found in these
two," not "the field agrees," and a reader who needs that claim to hold should widen the sweep before
leaning on it.

### 6.2 Derivation's failure mode is exactly the one this fleet is worst placed to catch

pytest's `--rootdir` caveat [S8] is the general form: **a derived value can make its own override
unrepresentable.** The local form is worse. A derived scope that is wrong produces a *plausible*
run — the workflow plans the wrong component competently — and this fleet's producer is an LLM,
which [`workflow-scripts.md`](../../../../standards/workflow-scripts.md) already warns *"can emit a
plausible-looking but wrong result."* A wrong flag fails loudly at parse time; a wrong derivation
fails at review time, after the spend.

**M3 (echo what was derived) is the mitigation, and it collides head-on with F1.** Echoing costs
output, and the caller that most needs the echo — the parent — is the caller that most wants
silence. This paper does not resolve that; it names it. The honest statement is that M3 buys
debuggability at the price of a second output-verbosity decision.

**No source was found measuring how often derived configuration is wrong versus declared
configuration.** Searched: the CLI-design guide [S1], the Rails doctrine [S5], PEP 20 [S6], Bazel's
concepts docs [S7], pytest's customization docs [S8]. All five argue the position; **none measures
it.** The entire industry position on facet 2 is, as far as this sweep found, argued rather than
evidenced. A Phase 3 decision that leans on §2.2 is leaning on well-reasoned convention, not data.

### 6.3 Facet 3 may not need building at all, and the paper says so

Phase 3's own roadmap line carries the gate: *"if the run bag records the config a run used, the
divergence half shrinks to a reader."* §5.3 measures the bag at five tags, none of them config —
so the gate is open. **But P17 is the honest reading of the whole facet: if you ship only the
digest, and put it in the bag, you get divergence detection for free as a post-hoc reader over run
bags, and you never build a drift detector at all.**

That makes most of §2.3 — provenance commands, typed diffs, agreement proofs — **material for a
later increment that may never be justified.** A planner who decomposes §2.3 into a full
managed-config subsystem is building ahead of the evidence. The measured, minimal Phase 3 item is:
one digest, one info tag, one reader.

**And there is a case for doing nothing at all here.** Facet 3's problem statement is *"no two
machines can be shown to match."* This fleet has one operator, and
[`problem-statement.md`](../../../../standards/architecture/problem-statement.md) explicitly says
*"Nothing may assume a single operator"* — which is a rule about not taking single-operator
**shortcuts**, not a claim that the multi-machine problem is live today. If the multi-machine case
is not yet real, the honest disposition of facet 3 is a digest (cheap, needed anyway for run
provenance) and nothing else.

### 6.4 What was searched and NOT found

- **No documented Claude Code command prints the effective merged settings with per-key origin.**
  Method: `claude --help` on v2.1.234 scanned for `setting`, `config`, `origin`, `scope`; the
  settings documentation page fetched and asked directly; `claude_code_integration_surface.md` §4
  read in full. Three checks, none found one. This is *"not found by those three"*, not *"does not
  exist"*.
- **Terraform was pursued as the best first-party statement of human-vs-automation invocation and
  abandoned.** Method: `hashicorp/terraform` default branch confirmed as `main`; `website/docs/cli`
  and `website/docs/cli/config` both returned `Not Found` from the contents API; the `website/`
  directory that does remain at repo root holds exactly one file, a `README.md` redirecting all
  documentation contributions to `hashicorp/web-unified-docs`. The docs have moved out of the
  repository and only a rendered site remains. **Terraform is therefore not cited anywhere in this paper**, rather than
  cited from a rendered page — its would-be contribution (`-input=false`, `TF_IN_AUTOMATION`) is
  already covered by [S1]'s `--no-input`.
- **`rust-lang/cargo`'s workspace reference was sought as a second path-derivation exemplar** and its
  `src/doc/src/reference` path returned `Not Found` on the `master` branch. Not cited. Bazel [S7] and
  pytest [S8] carry that argument.

### 6.5 Confirmation risk, named

This paper was commissioned by a dispatch that already stated the desired shape of all three answers
(dual-mode parity, derive-don't-flag, managed-plus-user). **It agrees with all three**, which is
exactly what a confirmation-biased paper looks like from outside. The three places it pushes back are
the honest signal, and they are: the framing correction at the top (`plan-project` is built), §6.1
(the standard already says standalone-is-recovery, contradicting the checkbox), and §6.3 (facet 3's
minimal increment is one tag, not a subsystem). A reader who finds those three too weak should treat
§4's recommendations as directional.

### 6.6 Where this paper's authority stops

Everything in §2 and §3 is drawn from systems with **no LLM in the loop.** git, systemd, npm, pytest,
Bazel, chezmoi and VS Code all have deterministic callees. This fleet's callee is a model. The one
place that difference is load-bearing is §6.2's asymmetry — a wrong derivation produces a competent
wrong run rather than an error — and no cited source addresses it. **Every mechanism transferred here
carries that untested hop.**

---

## 7. Test plan — what research cannot settle

Ordered by how much a wrong answer would cost.

- **T1 — Does the safety hook survive a narrowed `--setting-sources`?** Run a headless dispatch with
  `--setting-sources project,local` against a worktree, attempt a command `block-dangerous.sh`
  blocks, and record whether it fires. **This is the precondition the safety-layer invariant demands
  and it has never been measured** (`grep -rn -- '--setting-sources' scripts/` returns 0 today).
- **T2 — P14: does a hook declared in the MANAGED tier survive both `--setting-sources` and
  `--safe-mode`?** Place a trivially-observable `PreToolUse` hook in
  `/etc/claude-code/managed-settings.json`, then run `-p` four ways: default; `--setting-sources
  project,local`; `--safe-mode`; both. Record which invocations fire it. **A YES converts P14 from a
  derived inference into the mechanism that unblocks the whole facet-3 flag question.**
- **T3 — Exit-code parity for a child under both callers.** For one child, run it standalone with a
  deliberately-failing input and again under its parent with the same input; assert the parent
  observes a non-zero result and routes to the human branch. F2 is the only dual-mode property whose
  breakage is silent.
- **T4 — Verbosity parity (F1).** Run one child standalone with and without `--verbose`, and under a
  parent with and without, and diff the four output streams. Confirm the parent-invoked path emits
  nothing to stdout that a parent would have to parse around.
- **T5 — Working-directory independence (F5).** Invoke every shim from three cwds — repo root, a deep
  subdirectory, and outside the repo with `--repo` — and confirm worktrees and logs land in the same
  place all three times. `resolve_repo_root`'s docstring says six of seven runners once got this
  wrong; a test is what stops the seventh.
- **T6 — Give the nine children adapters, or rule that they should not have them.** Not a test —
  the operator ruling §6.1 names. It must precede T3/T4 for those nine, since there is nothing to
  invoke standalone.
- **T7 — Digest stability.** Compute a digest over the seven managed paths on two machines with the
  same `git rev-parse HEAD` in `claude-dot-files` and confirm equality; then dirty one file and
  confirm inequality. This is P17(i) and P16's fix in one experiment.
- **T8 — P18: does `managed-settings.d/` exist and does it merge?** Place two drop-ins with
  conflicting keys and observe which wins, and whether lexicographic order governs as it does in
  systemd. **Do not design on P18 before this runs** — it rests on a single rendered-page fetch.
- **T9 — The chain-tail rule.** Give `plan-feature` a component path that is NOT the tail of a
  project chain and record what it does. M2 cannot be written until the current behaviour is known.
- **T10 — Does echoing the derived scope (M3) cost anything a parent cares about?** Add the echo to
  one runner behind the existing `verbose` parameter and measure whether any parent's parsing changes.
  This is the F1-vs-M3 collision from §6.2, resolved empirically rather than argued.

---

## 8. Citations

Seventeen external sources plus seven internal documents and thirteen locally-read code artifacts.

*(Numbering note: there is no **S9**. An early draft listed npm twice — once for its precedence order
and once for `npm config ls -l` — and the duplicate row was removed rather than renumbered, so the
gap is a deletion and not a missing citation. The seventeen S-numbers in use and the seventeen defined
below are the same set.)*
**Why this count is right for this topic:** the Research Standard's floor is 10–20 for medium+
topics. This is genuinely three coupled facets, so it was worked at the top of that range. The
seventeen break down as: **fourteen raw first-party artifacts** fetched from `raw.githubusercontent.com`
as `.adoc` / `.rst` / `.md` / `.xml` / `.mdx` plain text (S1, S2, S3, S4, S6, S7, S8, S10, S11, S12,
S15, S16, S17, S18); **one first-party artifact observed locally** — the installed CLI's own `--help`
at a pinned version (S13); **one rendered page whose three quoted spans were each `grep -F`-verified
against the raw HTML bytes** (S5); and **one rendered page read through a summarizing fetch, from
which nothing is quoted** (S14).

**Distribution across the facets, counting each source once per facet it is used in** — re-enumerated
during verification, because the figures first published here were estimated rather than counted:
facet 3 draws on ten (S2, S3, S10, S11, S13, S14, S15, S16, S17, S18), being the facet where the
field has actually shipped mechanisms; facet 2 on six (S2, S5, S6, S7, S8, S17); facet 1 on four
(S1, S2, S4, S12). Two sources carry across facets — S2 in all three, S17 in facets 2 and 3 — so the
three counts sum to twenty over seventeen sources, which is the arithmetic check that they were
enumerated and not guessed. **Facet 2's evidence is still the thinnest where it counts:** only four
of its six (S5, S6, S7, S8) address the derivation question directly, S2 and S17 entering solely as
comparative rows in §3.2 — and as §6.2 records, all four *argue* that position rather than measuring
it, so additional sources would have added restatements and not evidence.

### External — raw first-party (definitive)

| # | Source | URL | Verification |
|---|---|---|---|
| S1 | *Command Line Interface Guidelines* — `content/_index.md` | https://raw.githubusercontent.com/cli-guidelines/cli-guidelines/main/content/_index.md | 10 spans, each `grep -c -F` = 1. Two spans initially failed because a summarizing fetch had normalized `’` to `'`; both re-verified in their exact form |
| S2 | git — `Documentation/git-config.adoc` (default branch `master`, confirmed via the repos API) | https://raw.githubusercontent.com/git/git/master/Documentation/git-config.adoc | 7 spans, each `grep -c -F` = 1 |
| S3 | npm CLI — `using-npm/config.md` (default branch `latest`, confirmed via the repos API) | https://raw.githubusercontent.com/npm/cli/latest/docs/lib/content/using-npm/config.md | source list and `npm config ls -l` read out of the raw byte stream |
| S4 | *The Twelve-Factor App* §III Config | https://raw.githubusercontent.com/heroku/12factor/main/content/en/config.md | span read out of the raw byte stream (`content/config.md` 404s; `content/en/config.md` located by enumerating `content/`) |
| S6 | PEP 20, *The Zen of Python* | https://raw.githubusercontent.com/python/peps/main/peps/pep-0020.rst | lines 24 and 30 read out of the raw byte stream |
| S7 | Bazel — *Repositories, workspaces, packages, and targets* (default branch `master`) | https://raw.githubusercontent.com/bazelbuild/bazel/master/site/en/concepts/build-ref.md | spans read out of the raw byte stream |
| S8 | pytest — `reference/customize.rst` | https://raw.githubusercontent.com/pytest-dev/pytest/main/doc/en/reference/customize.rst | 4 spans `grep -F`-verified; the header-printing sentence was quoted from raw after a summarizing fetch stripped its RST markup |
| S10 | systemd — `man/systemd.unit.xml` | https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.unit.xml | drop-in precedence paragraph read out of the raw byte stream |
| S11 | VS Code — `docs/configure/settings.md` | https://raw.githubusercontent.com/microsoft/vscode-docs/main/docs/configure/settings.md | 2 spans, each `grep -c -F` = 1 |
| S12 | Temporal — `encyclopedia/child-workflows/child-workflows.mdx` | https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/child-workflows/child-workflows.mdx | spans read out of the raw byte stream |
| S15 | systemd — `man/systemd-analyze.xml` (`cat-config`) | https://raw.githubusercontent.com/systemd/systemd/main/man/systemd-analyze.xml | span read out of the raw byte stream |
| S16 | systemd — `man/systemd-delta.xml` | https://raw.githubusercontent.com/systemd/systemd/main/man/systemd-delta.xml | description and the six `--type=` values read out of the raw byte stream |
| S17 | chezmoi (default branch `master`, confirmed via the repos API) — five files under `assets/chezmoi.io/docs/`: `what-does-chezmoi-do.md`, and `reference/commands/` `verify.md`, `status.md`, `managed.md`, `unmanaged.md` | https://raw.githubusercontent.com/twpayne/chezmoi/master/assets/chezmoi.io/docs/what-does-chezmoi-do.md · https://raw.githubusercontent.com/twpayne/chezmoi/master/assets/chezmoi.io/docs/reference/commands/verify.md · https://raw.githubusercontent.com/twpayne/chezmoi/master/assets/chezmoi.io/docs/reference/commands/status.md · https://raw.githubusercontent.com/twpayne/chezmoi/master/assets/chezmoi.io/docs/reference/commands/managed.md · https://raw.githubusercontent.com/twpayne/chezmoi/master/assets/chezmoi.io/docs/reference/commands/unmanaged.md | spans read out of the raw byte streams |
| S18 | Nix — `doc/manual/source/store/store-path.md` (default branch `master`) | https://raw.githubusercontent.com/NixOS/nix/master/doc/manual/source/store/store-path.md | span read out of the raw byte stream |

**Pinned at verification — the SHAs a re-check should use.** The URLs above address a branch tip,
which moves. During the `research-verify` round on 2026-08-18 each source was re-fetched at the
path-scoped commit below and returned HTTP 200; quoting these rather than the tip is what makes a
later re-check hit the same bytes this paper was written against, instead of whatever the branch has
moved to since.

| # | Path-scoped commit at verification |
|---|---|
| S1 | `2bd6023eae2aa60a374c4e7275f935d0917c6c86` |
| S2 | `4fa2c6e0457c5d00742f0cebded4f122f1dcd81a` |
| S3 | `cf56a1e4df9c8ae7b7e9752437d827a183e4040e` |
| S4 | `6a686a58cb187b68ea8c53288ab0972e057dd034` |
| S6 | `b990d0599141b030e68d1a1bb91aac9981d1fd56` |
| S7 | `13ecdf583301a94484a1ae0eb27c56fcf3248dc5` |
| S8 | `1027dee0156aa4928a1d09d3eac91d20c6a1b306` |
| S10 | `6f9bfb0e06f9ddea4a1a6182b230a8d5e9e90323` |
| S11 | `5b62e4a3430c5190e1b59a36ebd41f717f1c2625` |
| S12 | `26e515f28f8fdb27628b2fc968ef8f74a1d48d0f` |
| S15 | `3a79aaea83ead6bd743fab9355a480c4c1a554c1` |
| S16 | `af29d0b1796bd165bec4ddee65531333bd2e6aba` |
| S17 | one per file: `what-does-chezmoi-do.md` `788eb3bb5e9cff42197ebfd908836ee3540401dd` · `verify.md` `6c4431e430d4ad45b10bd44e711bd5d5c64ed5a5` · `status.md` `30a2391dfb3a2e30903d5e1360ab9e359aef790e` · `managed.md` `7df7c5805d43a6428ce113f79a49543fe77e30aa` · `unmanaged.md` `557cd16eee281d267e868aa100a461ef2889c75f` |
| S18 | `22d1e6eef7eaaac25b322ac141bad07d25239357` |

**S5, S13 and S14 have no commit to pin, and that is a real limit rather than an omission.** S5 and
S14 are rendered pages served from no public repository — a re-check of S5's three spans re-fetches
the live HTML and may legitimately fail if the page is re-rendered. S13 is the locally installed CLI,
pinned instead by its version string (2.1.234), which is the only identifier it exposes.

### External — first-party, observed locally (definitive)

| # | Source | Verification |
|---|---|---|
| S13 | Claude Code CLI, **version 2.1.234**, `claude --help`, observed 2026-08-18 on the authoring host | `--bare`, `--safe-mode`, `--setting-sources`, `--settings`, `--strict-mcp-config` help text read directly from the command's own output. A versioned, vendor-shipped artifact |

### External — rendered pages (reduced confidence; no verbatim spans presented as quotations)

| # | Source | URL | Status |
|---|---|---|---|
| S5 | *The Rails Doctrine* — § Convention over Configuration | https://rubyonrails.org/doctrine | Rendered HTML only. The three spans quoted in §2.2 were each confirmed with `curl -s … \| grep -c -F` = 1 against the raw HTML bytes. Nothing else from the page is quoted |
| S14 | Claude Code — Settings | https://code.claude.com/docs/en/settings | Rendered page read through a **summarizing** fetch, so **nothing from it is quoted verbatim**. Used for two facts: the managed-tier precedence position and the Linux managed-settings path — the latter corroborated by `claude_code_integration_surface.md` §4 (critic PASS) and therefore definitive; the `managed-settings.d/` drop-in claim is single-source and is marked **directional** (P18) |

### Searched and NOT cited (stated so the absence is not read as an oversight)

- **Terraform** — the natural first-party source for human-versus-automation invocation. Its docs are
  no longer in `hashicorp/terraform`; `website/docs/cli` and `website/docs/cli/config` both return
  `Not Found`, and the `website/` directory still present at repo root holds only a `README.md`
  redirecting contributions to `hashicorp/web-unified-docs`. Not cited from a rendered page.
- **Cargo** — `src/doc/src/reference` returns `Not Found` on `master`. Not cited.
- **Open Policy Agent** — `docs/content` returns `Not Found` on `main`. Not pursued further; the
  policy-as-code angle is covered by VS Code Policy settings [S11] and Claude Code's managed tier
  [S13][S14].

### Internal — this repo's standards and research pools

| # | Document | State |
|---|---|---|
| L1 | [`docs/standards/workflow-scripts.md`](../../../../standards/workflow-scripts.md) — § Composition, § Naming, § The safety-layer invariant, § A prompt block with two consumers is promoted | Binding standard |
| L2 | [`docs/development/workflow-decomposition/roadmap.md`](../../roadmap.md) — Phase 3 and § What is deliberately not built | Planning artifact |
| L3 | [`raw/fork_vs_parameterize_drift_signal.md`](./fork_vs_parameterize_drift_signal.md) | This pool. 2026-08-17, high — 6 weeks, due 2026-09-28, **current**, PASS-WITH-FIXES |
| L4 | [`standards/architecture/research/raw/claude_code_integration_surface.md`](../../../../standards/architecture/research/raw/claude_code_integration_surface.md) — §4 configuration surface, §8 integration implications | Upstream pool, read-only. 2026-07-25, high — 4 weeks, due 2026-08-22, current |
| L5 | [`standards/architecture/research/raw/workflow_reuse_boundary.md`](../../../../standards/architecture/research/raw/workflow_reuse_boundary.md) | Upstream pool, read-only. 2026-08-03, due 2026-09-14, current |
| L6 | [`standards/architecture/research/raw/paperclip_assessment.md`](../../../../standards/architecture/research/raw/paperclip_assessment.md) — §4.5 skills-injection (*"Never copy or symlink skills into the agent's `cwd`"*, the `--add-dir` temp-symlink farm), which names this repo's global `config/` → `~/.claude/` symlinking as the thing that *"works for one operator on one machine"* | Upstream pool, read-only. 2026-08-04, due 2026-09-01, current |
| L7 | [`standards/architecture/problem-statement.md`](../../../../standards/architecture/problem-statement.md) — § Affordability is the enabler; § What this means for anything built here | Read-only |

`openclaw_assessment.md` and `hermes_assessment.md` were read for facet-3 material (per-agent
credential stores with a stated precedence; `/etc/hermes` managed scope) and are **not cited as
evidence** — neither adds a mechanism the systems in §2.3 do not already document, and citing them
would inflate the source list without adding an argument. `hook_sourcing_supplement.md` belongs in
the same category and is recorded here for the same reason: it was read at authoring time and an
earlier revision listed it in §1.3 as evidence this paper leans on, but **no claim anywhere in the
body rests on it**, so the verification round moved it out of that table rather than leaving a row
that overstated what was drawn on.

### Internal — local artifacts read at commit `128091c`

`install.sh`; `config/settings.json`; `scripts/workflows/activities/run-claude.sh`;
`scripts/workflows/temporal/scripts/preflight.py`; `.../scripts/run_plan_feature.py`;
`.../scripts/run_plan_project.py`; `.../scripts/run_research.py`; `.../scripts/run_review_pr.py`;
`.../scripts/plan_feature.sh`; `.../modules/assistant/plan/plan_project/plan_project_workflow.py`;
`.../modules/journal/journal_activities.py`;
`testing/config-hooks/tests/unit/test_the_safety_hook_is_wired.py`;
`.../tests/unit/test_shim_usage_names_itself.py`.

Every count reported in §5 is the output of the enumerating command quoted beside it. No count in
this paper was taken from a retrieval layer's total.
