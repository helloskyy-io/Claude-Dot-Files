# Direction decisions — the operator's inbox

**This file is not a standard.** It lives beside the research pool because that is where its rows come from, but nothing here binds anything. It is the queue of rulings only the operator can make.

## Why it exists

`plan-sprint` triages research candidates into `ship`, `requires review` and `reject`. `requires review` is the release valve: a finding that is real but not schedulable, because the answer is a preference, a priority or a commitment rather than a fact that more work would uncover. Shipping one puts a question mark in the sprint plan; rejecting one throws away a real finding. Both are wrong, so it comes here instead.

## The rule

> **Automation appends and leaves `status` at `open`. The operator sets `status`.**

- **IDs are `D-001`, `D-002`, …**, independent of the `C-` series in [`candidates.md`](candidates.md). Never reused, never renumbered.
- **Nobody deletes a row.** A `rejected` row stays visible so the same recommendation is not re-proposed.
- **`Source` carries the `C-NNN` it came from**, so this file and `candidates.md` stay linked.
- **Recommendation and *Why it matters* are one sentence each.** These are read at standup.

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
| `D-002` | Close the cross-machine-failover ruling and amend `problem-statement.md`, which still states it open | The third option — pin the credential and proxy the model call — is documented not to work for `claude-cli` runtimes, so the evidence now argues for the pinned design rather than leaving the cost unresolved | `C-019`, `C-037` | `open` |
| `D-003` | Rule the laptop trust boundary — the resolution available is that the credential is the operator's own, so the operator is inside the boundary | Both major CI vendors publish guidance against a self-hosted runner holding a credential its dispatcher lacks, and leaving that unwritten leaves differentiator #1 uncosted | `C-021` | `open` |
| `D-004` | Amend `workflow-scripts.md § Composition` and `architectural_standard.md § 3`'s `author ≠ judge` seam, which justify two mechanisms with an argument supporting only the first | Fresh context is directionally evidenced and no-authoring-authority has no isolating study, so both documents currently imply measured backing that does not exist | `C-032` | `open` |
| `D-005` | Rule whether a cross-family judge for `review-pr` is in scope at all | Every genuinely cross-family option requires a second provider credential, which cuts against the subscription-economics thesis and the unmintable-credential differentiator | `C-034` | `open` |
| `D-006` | Rule whether multi-participant support belongs to this repo or to SkyyNet | The four team-scaling items cannot be sized until that boundary is set, and the problem statement's *nothing may assume a single operator* constraint depends on the answer | `C-041` | `open` |
| `D-007` | Rule whether the VERDICT-token-on-stdout completion contract keeps standing unchanged in `workflow-scripts.md § Composition` and `architectural_standard.md § 2`, gains a write-time gate, or is replaced | Every located instance of parsing a machine value out of a human artifact pairs it with enforcement at authoring time and ours has none, but the same pool found no evidence the incumbent has ever produced a wrong route — so this is a cost to weigh, not a defect to fix | `memory-management-framework/research/synthesis.md` #14 | `open` |

## Related

- [`candidates.md`](candidates.md) — research action candidates and their dispositions
- [`synthesis.md`](synthesis.md) — what the evidence currently says
- [`../problem-statement.md`](../problem-statement.md) — the thesis these rulings bear on
