# Direction decisions — the operator's inbox

**This file is not a standard.** It lives beside the research pool because that is where its rows come from, but nothing here binds anything. It is the queue of rulings only the operator can make.

## Why it exists

`triage-candidates` triages research candidates into `ship`, `requires review` and `reject`. `requires review` is the release valve: a finding that is real but not schedulable, because the answer is a preference, a priority or a commitment rather than a fact that more work would uncover. Shipping one puts a question mark in the sprint plan; rejecting one throws away a real finding. Both are wrong, so it comes here instead.

## The rule

> **Automation appends and leaves `status` at `open`. The operator sets `status`.**

- **IDs are `D-001`, `D-002`, …**, independent of the `C-` series in [`candidates.md`](candidates.md). Never reused, never renumbered.
- **A row is a RECEIPT once ruled, not a record.** The durable home of a ruling is elsewhere — see *Resolving a row* below — and a ruled row rotates out on the schedule at the bottom of this file.
- **`Source` carries the `C-NNN` it came from**, so this file and `candidates.md` stay linked.
- **Recommendation and *Why it matters* are one sentence each.** These are read at standup.

## Resolving a row — four steps, and step 3 is the one that matters

**This file is the human's. `candidates.md` is the machine's.** A question goes up; an answer must come back down, in a form `triage-candidates` can act on. A ruling that lives only here is a decision the automation cannot see.

**1 · Rule it.** Define the resolution properly, or reject it. A ruling that restates the question is not a ruling.

**2 · If REJECTED** — set `status: rejected`, and **write the reasoning into the source candidate's Note** in `candidates.md`. That file never deletes a row, so the reasoning is what stops the same recommendation being re-proposed by a later research cycle. Then abandon it in place; a rejection is a design decision, not unfinished work.

**3 · If ACCEPTED** — set `status: applied`, and:

- **Set the source candidate's `decision` back to BLANK**, with the ruling written into its Note. **Blank is deliberate and it is not a downgrade.** Blank means *needs triage*, which is now true — the question that blocked it has an answer. `triage-candidates` re-triages it on the next run and reads the ruling as its input.
- **Do NOT set it to `ship` by hand.** Blank is what puts it back in the triage working set; a hand-set `ship` skips the run that would have read your ruling and recorded why the answer changed. **The reasoning is the point of this file, and a hand-set `ship` throws it away.**

  *(This warning used to carry a second reason — that `plan-sprint` placed only what it had shipped in that same run, so a hand-set `ship` would sit decided-and-unplaced forever. **The split fixed that**: `plan-sprint` now runs after triage and places from the `ship` rows in the file, whoever set them and whenever. The remaining reason is enough on its own.)*
- **Amend the document the ruling governs** if it changes what the project believes. `D-002`'s ruling lives in `problem-statement.md`, not here.

**4 · Next run picks it up.** `triage-candidates` re-triages and ships it; `plan-sprint`, running after, places it — or reports it *for placement* if it is too small for the sprint file.

## Rotation — a ruled row is deleted once its reasoning lives somewhere permanent

**A ruled row rotates out at the first standup ≥90 days after it was ruled.** This file is the operator's inbox, and an inbox that only grows stops being read.

**Rotation is safe ONLY because the reasoning is durable elsewhere by then**, which is the whole point of steps 2 and 3:

| Ruled | Durable home | Rotates when |
|---|---|---|
| `rejected` | the source candidate's Note in `candidates.md`, which never deletes | reasoning is recorded there |
| `applied` | the amended document, plus the source candidate's Note | the amendment has landed |

**No durable record, no rotation.** Same discipline as the standup tracker's pruning stamp: the record is what makes deletion safe, and a row whose reasoning was never written down stays here until it is. **Deleting an unrecorded ruling loses the one thing that stops it being re-proposed.**

## Statuses

| `status` | Meaning | Who sets it |
|---|---|---|
| `open` | Outstanding — awaiting the operator's ruling | automation, always |
| `applied` | Ruled, and the resulting change has landed | the operator |
| `rejected` | Ruled against — the reasoning goes in the row | the operator |

---

## Open decisions

| ID | Recommendation | Why it matters | Source | `status` |
|---|---|---|---|---|
| `D-001` | Rule the queue-axis conflict between the pinned-edge design and the vendored Worker Deployment Standard | It gates planning for Temporal Integration, and the polling-authorization spike (`C-022`) is the evidence the ruling needs before it can be made | `C-010` | `open` |
| `D-002` | Close the cross-machine-failover ruling and amend `problem-statement.md`, which still states it open | The third option — pin the credential and proxy the model call — is documented not to work for `claude-cli` runtimes, so the evidence now argues for the pinned design rather than leaving the cost unresolved | `C-019`, `C-037` | `applied` |
| `D-003` | Rule the laptop trust boundary — the resolution available is that the credential is the operator's own, so the operator is inside the boundary | Both major CI vendors publish guidance against a self-hosted runner holding a credential its dispatcher lacks, and leaving that unwritten leaves differentiator #1 uncosted | `C-021` | `open` |
| `D-004` | Amend `workflow-scripts.md § Composition` and `architectural_standard.md § 3`'s `author ≠ judge` seam, which justify two mechanisms with an argument supporting only the first | Fresh context is directionally evidenced and no-authoring-authority has no isolating study, so both documents currently imply measured backing that does not exist | `C-032` | `open` |
| `D-005` | Rule whether a cross-family judge for `review-pr` is in scope at all | Every genuinely cross-family option requires a second provider credential, which cuts against the subscription-economics thesis and the unmintable-credential differentiator | `C-034` | `open` |
| `D-006` | Rule whether multi-participant support belongs to this repo or to SkyyNet | The four team-scaling items cannot be sized until that boundary is set, and the problem statement's *nothing may assume a single operator* constraint depends on the answer | `C-041` | `open` |
| `D-007` | Rule whether the VERDICT-token-on-stdout completion contract keeps standing unchanged in `workflow-scripts.md § Composition` and `architectural_standard.md § 2`, gains a write-time gate, or is replaced | Every located instance of parsing a machine value out of a human artifact pairs it with enforcement at authoring time and ours has none, but the same pool found no evidence the incumbent has ever produced a wrong route — so this is a cost to weigh, not a defect to fix | `memory-management-framework/research/synthesis.md` #14 | `open` |

## Related

- [`candidates.md`](candidates.md) — research action candidates and their dispositions
- [`synthesis.md`](synthesis.md) — what the evidence currently says
- [`../problem-statement.md`](../problem-statement.md) — the thesis these rulings bear on
