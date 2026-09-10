# `scripts/helpers/`

Standalone tools. Each one is invoked by something — a CI step, a command file, a
workflow, a test — and this file names that something for every tool on disk.

**Why the table is here and not implied.** A tool nobody invokes still costs the
run that wrote it, still reads as coverage, and goes wrong silently because
nothing was ever checking. That is the failure
[`phase6_every_producer_names_its_consumer.md`](/opt/skyy-net/skyynet-master-planning/development/edge-assistant/workflow-decomposition/phase6_every_producer_names_its_consumer.md)
exists to catch, and this directory is its first extension target beyond
`measure/`. The gate is
`tests/unit/test_every_producer_NAMES_ITS_CONSUMER.py`; it reads the population
off disk, so a tool that is never added to this table fails rather than hides.

**The `Invoked by` cell names a PATH, and the gate opens it.** A cell naming a
file that does not mention the tool fails — which is the whole point:
`harvest-intake.py` is a stated *condition of an exemption* invoked only by one
line of prose in `config/commands/standup.md`, and if that line is ever dropped
the intake keeps accepting, nothing empties it, and no suite goes red. Now one
does. **`docs/file_structure.txt` is rejected as an invoker by name** — a map
mentions every file in the repo, so accepting it would make every row pass
trivially.

| Tool | Does | Invoked by |
|---|---|---|
| `check_settings.py` | Parses `config/settings.json` and asserts every hook command resolves to an executable file | `scripts/helpers/check-settings.sh`, the merge-path wrapper |
| `check-settings.sh` | Merge-path wrapper over the above — the one control that operates during an autonomous run | `.github/workflows/tests.yml`, step *Validate settings.json* |
| `file_structure_check.py` | Holds `docs/file_structure.txt` to one line per entry and to the paths that actually exist | `scripts/helpers/tests/unit/test_file_structure_check.py`, run by the master runner on every CI run |
| `harvest-intake.py` | Drains the tracked-item intake into the four stores — **the named harvest cadence** Tracked Items §5.0 makes the exemption conditional on | `config/commands/standup.md`, Stage 2 action 2 |
| `init-project.sh` | Scaffolds a new repo: git, remote, folder structure, the four stores, CI | `scripts/workflows/plan-new.sh` |
| `lint-prompts.sh` | Catches prompt-construction landmines `bash -n` cannot see | `.github/workflows/tests.yml`, step *Prompt-construction lint* |
| `merge-pr.py` | Lands a reviewed PR set and drains the intake — the operator entry point | **NOBODY — baselined below.** No command file, CI step, workflow or test in this repo invokes it |
| `sibling_checkouts.py` | Reports work a dispatch left in a repo it was not pointed at | **NOBODY — baselined below.** Nothing outside its own test names it |
| `similar-candidates.py` | Ranks which existing tracked items to read before filing a new one | `scripts/workflows/temporal/modules/assistant/assistant_activities.py` |
| `standards_index.py` | Audits the standards corpus against the header contract and reports what is unreachable | `scripts/helpers/tests/unit/test_the_standards_index_is_ACTUALLY_CLEAN.py`, run against the live corpus |
| `vendor-standards.sh` | Re-copies vendored standards from their canonical home; `--check` fails on local drift | `scripts/workflows/temporal/modules/assistant/plan/plan_activities.py` |

**`README.md` — this file — is not a row either, and the reason is sharper than
tidiness.** It is the surface's declaration, not a member of it: a check whose
population includes the text making the claim can be satisfied by its own row,
which is a claim about nothing. Same treatment as `measure/run_log.py`, for the
same reason, and asserted by name in the gate.

**`measure/` and `tests/` are not rows.** `measure/` is its own producer surface
with its own table and its own `Read by` column; `tests/` holds the tools' tests,
which the runner reads rather than the system. Both are excluded **by name** in
the gate — an exclusion that is not named is a hole — and the gate fails if a
third subdirectory appears that is neither ruled in nor excluded.

## The two tools nothing invokes — a baseline that can only shrink

Two rows above name no invoker, and that is a **finding this phase produced
rather than a hole it left**. They are frozen below and the ratchet runs both
ways: a *new* uninvoked tool fails, and a baselined tool that gains a real
invoker fails until its line is deleted. Freezing rather than fixing is
deliberate — the phase's own boundary is that *finding* an unread producer is
the output and *ruling what happens to it* is a separate decision, and inventing
an invoker to make a check green is how a gate gets routed around.

- **`merge-pr.py`** — the fleet's only enforced gate on `main`, and its only
  mention outside its own docstring is a box in a workflow-tree diagram in
  `skyynet-master-planning/guide/puma-temp-workflows.md`. A diagram is not an
  invocation, and the doc's own name says it is temporary. Rename or delete that
  file and the merge path has no documented way in at all.
- **`sibling_checkouts.py`** — landed 2026-09-08 and has never been wired to
  anything. Nothing in this repo, no command file and no workflow names it; the
  only reference on disk is its own test. It reports a class of lost work
  (*a dispatch that committed into a repo it was not pointed at*) that by
  construction nobody is watching — so a report nobody runs is the same defect
  one level up.

## What this table does NOT claim

It claims a named invoker exists and that the named file mentions the tool. It
does **not** claim the invocation is correct, that its arguments are right, that
the path is ever actually taken at runtime, or that the tool's output is read by
a human once produced. Naming a reader is a much weaker claim than the reader
being any good, and this table makes only the weaker one. Do not over-read a
green suite.
