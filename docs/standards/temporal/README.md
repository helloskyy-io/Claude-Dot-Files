# Temporal Standards — vendored, and what they bind here

The three documents in this folder are **verbatim copies** from `helloskyy-io/MDC-Master-Planning`, `standards/development/temporal/`. They are the canonical standards for the durable-execution framework this repo's workflow fleet is being ported onto.

**Do not edit them here.** Amendments go upstream, then re-vendor:

```bash
scripts/helpers/vendor-standards.sh          # re-copy from source
scripts/helpers/vendor-standards.sh --check  # fail if a copy has drifted
```

**MIRROR, not FORK** — these copies are meant to track the source; a general improvement made here is retrofitted upstream in the same work. That intent flag is required by [Documentation Standard § *Cross-ecosystem vendored standards (binding)*](../documentation/documentation_standard.md), which governs this folder.

Vendored rather than referenced because claude-dot-files deploys standalone to machines that may not have the planning repo checked out, and **a standard you cannot read is not binding** — and because a live cross-ecosystem link is an unversioned silent dependency.

---

## What binds NOW, before any Temporal code exists

Most of this folder describes a system we have not built yet. **Three parts bind today**, because the current bash fleet was deliberately shaped to conform to them and `docs/standards/workflow-scripts.md` restates them for the bash era:

| Binding now | Where | What it governs here |
|---|---|---|
| **§3 Three-Layer Architecture** | `temporal_standard.md` | Why `activities/` holds I/O, why a parent holds none, and why `children/` are child *workflows* and not activities |
| **§3.4 Composition** | `temporal_standard.md` | Compose where it benefits — and the explicit warning that decomposition is **situational, not a mandate** |
| **§7 Activity Design Patterns** | `temporal_standard.md` | Activities must be **idempotent** (§7.1) and self-validating (§7.2). This is the test that decides what may become an activity |

**§10 Directory Structure is the target we are moving toward**, not what we have. The mapping and the known divergence are in `docs/standards/workflow-scripts.md § Location`.

## What does NOT bind yet

- **`worker_deployment_standard.md`** — immutable images, task-queue naming, worker RBAC, cutover discipline. Applies once workers exist. **Read §2 (queue naming) before naming anything**, since names are expensive to change later.
- **`stateful_patterns.md`** — persistence boundaries, idempotent writes, cleanup-on-failure. §4 and §6 are worth reading *now* by anyone writing an activity, because the idempotency discipline is the same whether or not Temporal is running it.
- **§4 `ACTIVITY_MAP`, §5 Worker Configuration, §8 Configuration Management, §9 Workflow Design Patterns** — all port-time.

## Where these standards do NOT reach

They were written for infrastructure management — Proxmox, k3s, Ansible, ArgoCD, Ceph. Two things are genuinely ours and have no upstream equivalent:

1. **Long-running non-deterministic activities.** A `claude -p` run takes 10–60 minutes and returns prose. Upstream activities are seconds-to-minutes and return structured results. Heartbeating and payload handling for this shape is new work.
2. **A producer that can be confidently wrong.** Every activity upstream either succeeds, fails, or times out. Ours can return a plausible-looking but incorrect result, which is why our routing contracts fail *safe to a human* rather than defaulting to the permissive branch.

Both are recorded in `claude-dot-files-addendum.md` as they get decided. **The addendum is the only file in this folder that may be edited locally.**

## Related

- `docs/standards/workflow-scripts.md` — how these rules apply to the bash fleet today
- `docs/development/skyy-net-seed-handoff.md` — the topology and decision record
- `docs/development/roadmap.md` → *Phase: Temporal Integration* — the migration path
