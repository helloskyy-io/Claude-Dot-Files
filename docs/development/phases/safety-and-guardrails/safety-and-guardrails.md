# Phase: Safety & Guardrails

**Status:** ✅ COMPLETE
**Roadmap entry:** [`../roadmap.md`](../../roadmap.md)
**Depends on:** [`cross-device-sync.md`](../cross-device-sync/cross-device-sync.md) — hooks are only a guarantee if they are on every machine automatically

## Goal

Make it safe to say yes quickly in interactive mode, and safe to walk away in autonomous mode. Those are different problems: interactive needs a fast confirmation you can trust, autonomous needs a control that operates with nobody watching.

## Completion criteria

- [x] A destructive command is refused **even when permissions are bypassed**
- [x] A hook failure is loud, never silent-allow
- [x] Hooks arrive on a new machine with no extra step beyond `install.sh`
- [x] The operator is told when a long run finishes

## Work

- [x] **`PreToolUse` → `block-dangerous.sh`** — reads JSON on stdin, extracts the bash command, denies on destructive patterns (`rm -rf`, force push, `git reset --hard`, `DROP TABLE`, `dd`, fork bombs). Wired with matcher `"Bash"`
- [x] **`Stop` → `notify-done.sh`** — `notify-send` on completion; skips gracefully on headless machines
- [x] **Permissions reviewed in `settings.json`** — the allow/deny lists that prompt in interactive mode
- [x] **Both hooks tested** — permission layer prompts; notification fires

## Decisions

**Two layers, and they cover different failure modes.** Permissions catch *unlisted* commands and ask. The hook catches *known-dangerous* commands regardless of what the allow list says. A broad allow rule that accidentally matches `rm -rf` is caught by the second layer, which is the entire reason both exist.

**Hooks read JSON on stdin, never environment variables.** Codified in [`../../standards/hook-scripts.md`](../../../standards/hook-scripts.md). The contract is explicit and testable; env-var passing is neither.

**No `PostToolUse` auto-format.** Deliberately rejected — an automatic edit after every tool call fights the model's own file state and produces "file has been modified since read" errors, trading a formatting nicety for a class of run failure.

## What this phase turned out to be worth, discovered later

At the time this was defence-in-depth. It is not.

**Autonomous workflows pass `--dangerously-skip-permissions`**, which disables the entire permissions layer. Of the three things usually cited as making that safe — worktree isolation, the hook, PR review — isolation only bounds blast radius and PR review happens after the fact. **`block-dangerous.sh` is the only control that can stop a command before it runs**, on every autonomous run, on every machine.

Two consequences now binding, recorded in [`../../standards/hook-scripts.md`](../../../standards/hook-scripts.md):

- **A hook must fail CLOSED.** One that errors into "allow" is worse than no hook, because the safety story still claims it is there.
- **Any change to which setting sources load must prove the hook survives first.** Hook configuration lives in user-level `settings.json`; narrowing setting sources on a dispatch would drop it. That turned a two-line convenience into a two-line safety regression, and it is why the Managed Configuration phase carries a blocker rather than a task.

## Where this landed

- [`../../standards/hook-scripts.md`](../../../standards/hook-scripts.md) — the standard, including the headless safety invariant
- [`../../architecture/system-overview.md`](../../../architecture/system-overview.md) — hook architecture and the stdin JSON contract
- `config/hooks/` — the implementations
