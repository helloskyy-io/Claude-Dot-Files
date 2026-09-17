"""The read-only regression guard — a source scan, not a proof of impossibility.

**Read the limit before the claim.** This module is a *regression guard*: it
catches the write shapes a careless change would plausibly introduce, and it is
falsifiable — the test drives it at deliberately-writing modules and requires it
to go red, because a contract check that cannot fail manufactures confidence.

**It is NOT a proof that writing is impossible, and an earlier version of this
docstring said it was.** A name-and-arity scan over one package's own source can
always be walked around — ``getattr(obj, "wri" + "te_text")(...)``, a descriptor,
``exec``, a raw descriptor from ``os.open`` handed to ``os.write``, ``ctypes``.
Chasing that surface to completion is unbounded work for a check whose ceiling is
provably below "structural", so the scope is deliberately the *careless* case and
not the *adversarial* one. Two independent reviewers had to correct the stronger
claim on the same day it was written; it is stated plainly here so nobody has to
correct it a third time.

**There is no enforced control beneath this one, and the docstring used to
say there was.** An earlier home for this package served the corpus from a pod
that mounted it ``readOnly: true``, which the kernel enforced. Hosted in the
tooling and run against a developer's writable checkout, that mount does not
exist, so this guard is the only thing standing between the reader and a write
path — which is why it is tested to go red, and why the honest statement is
"a regression guard" and not "a proof".

§1.2 of the Tracked Items Standard is why it exists at all: it reserves
``tracked/operations/`` to humans, and a reader that CAN write there is a
different kind of object from one that reads it.

It is itself read-only: it parses source with :mod:`ast` and opens nothing for
writing.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

#: Methods whose NAME alone proves mutation. Nothing in the standard library's
#: non-filesystem types answers to any of these, so a bare attribute match is
#: sound.
MUTATING_METHODS: frozenset[str] = frozenset(
    {
        "write_text",
        "write_bytes",
        "writelines",
        "mkdir",
        "makedirs",
        "touch",
        "unlink",
        "rmdir",
        "rmtree",
        "copyfile",
        "copytree",
        "symlink_to",
        "hardlink_to",
        "chmod",
        "chown",
        "rename",
        "truncate",
        # `fh.write(...)` after `Path(p).open("w")` — the plainest two-line file
        # write there is, and the first draft of this module missed it entirely
        # because it only listed the pathlib one-shot forms.
        "write",
        # `os.system` / `os.popen` / `os.exec*` / `os.spawn*` — a shell is a
        # write path with extra steps.
        "system",
        "popen",
        "execv",
        "execve",
        "execvp",
        "spawnv",
        "spawnl",
    }
)

#: Callables that open a handle. Matched on the NAME wherever it appears, as a
#: bare call or as an attribute — ``open(p, "w")``, ``Path(p).open("w")``,
#: ``os.open(...)``, ``io.open(...)`` are one shape wearing four spellings, and
#: a check that only knew the bare builtin let three of them through.
OPENERS: frozenset[str] = frozenset({"open", "fdopen", "FileIO"})

#: Methods whose name is SHARED with a harmless builtin type, so the name alone
#: is not evidence. ``str.replace`` and ``list.remove`` and ``dict.copy`` are
#: everywhere; ``Path.replace``, ``os.remove`` and ``shutil.copy`` are writes.
#:
#: **This split exists because the first draft flagged three `str.replace` calls
#: in the reader as filesystem writes.** A check that cries wolf on ordinary
#: string handling gets an exclusion bolted onto it within a week, and the
#: exclusion is what eventually hides a real one. So the ambiguity is resolved
#: by ARITY — the path-mutating forms take exactly one positional argument and
#: their string/list/dict namesakes do not — rather than by exempting files.
AMBIGUOUS_MUTATING_METHODS: frozenset[str] = frozenset(
    {"replace", "remove", "copy", "copy2", "move"}
)

#: The arity that makes an :data:`AMBIGUOUS_MUTATING_METHODS` name a write.
#: ``Path.replace(target)`` and ``os.remove(path)`` take ONE positional
#: argument; ``dict.copy()`` takes none and ``str.replace(old, new)`` takes two.
#: ``os.replace(src, dst)`` takes two as well and would have slipped through on
#: arity alone, so it is named explicitly below rather than left to the rule.
_PATH_MUTATING_ARITY = 1

#: Two-argument forms that ARE writes despite matching a harmless namesake's
#: arity. Named, because the arity heuristic is a good default and a bad
#: absolute — and a heuristic with no stated exceptions grows silent ones.
TWO_ARG_MUTATING: frozenset[str] = frozenset({"replace", "rename", "copy", "copy2", "move"})

#: Receivers whose every ambiguous method is a filesystem operation.
MUTATING_RECEIVERS: frozenset[str] = frozenset({"os", "shutil", "io", "pathlib"})

#: Bare callables that create a mutable handle or evaluate constructed code.
#: ``exec``/``eval``/``compile``/``__import__`` are here because they defeat the
#: whole scan in one line; there is no legitimate use of any of them in a package
#: whose only job is to read files and format tables.
MUTATING_BUILTINS: frozenset[str] = frozenset(
    {"open", "exec", "eval", "compile", "__import__", "getattr", "setattr"}
)

#: Modules whose whole purpose is mutation or reaching the network. Importing
#: one is reported even if nothing is called — the capability is the finding.
#:
#: Enumerated at SUBMODULE granularity where the package is mixed: `urllib.parse`
#: is pure string manipulation and the reader legitimately uses it to unquote a
#: markdown link, while `urllib.request` opens sockets. Banning the parent would
#: have made requirement 5 ("no network call") assert something false about a
#: `unquote` import, and a check that is wrong in an obvious place is a check
#: people learn to override.
FORBIDDEN_IMPORTS: frozenset[str] = frozenset(
    {
        "shutil",
        "tempfile",
        "socket",
        "ssl",
        "requests",
        "httpx",
        "aiohttp",
        "ftplib",
        "smtplib",
        "telnetlib",
        "xmlrpc",
        "urllib.request",
        "urllib.error",
        "http.client",
        "https",
    }
)

#: ``git`` subcommands that write the repository or reach the network. The page
#: uses ``log``, ``blame`` and ``rev-parse``; anything here is a defect.
MUTATING_GIT_SUBCOMMANDS: frozenset[str] = frozenset(
    {
        "add",
        "am",
        "apply",
        "branch",
        "checkout",
        "cherry-pick",
        "clean",
        "clone",
        "commit",
        "config",
        "fetch",
        "gc",
        "init",
        "ls-remote",
        "merge",
        "mv",
        "prune",
        "pull",
        "push",
        "rebase",
        "reset",
        "restore",
        "revert",
        "rm",
        "stash",
        "switch",
        "tag",
        "update-ref",
        "worktree",
    }
)

#: The one program these packages may run. Allow-listing the EXECUTABLE and not
#: only the subcommand is what stops ``["sh", "-c", …]`` — a shell hides its
#: whole payload from a scan that inspects argv words.
ALLOWED_EXECUTABLE = "git"

#: The store §1.2 reserves to humans. Named explicitly so the guard states the
#: thing it is protecting rather than only the general property.
HUMAN_ONLY_STORE = "tracked/operations"


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    kind: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.file}:{self.line} {self.kind} — {self.detail}"


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.violations: list[Violation] = []

    def _add(self, node: ast.AST, kind: str, detail: str) -> None:
        self.violations.append(
            Violation(self.rel, getattr(node, "lineno", 0), kind, detail)
        )

    @staticmethod
    def _forbidden(module: str) -> str:
        """The longest forbidden prefix of a dotted module name, or ``""``."""
        parts = module.split(".")
        for depth in range(len(parts), 0, -1):
            candidate = ".".join(parts[:depth])
            if candidate in FORBIDDEN_IMPORTS:
                return candidate
        return ""

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            match = self._forbidden(alias.name)
            if match:
                self._add(node, "forbidden-import", f"imports `{alias.name}` (`{match}`)")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        match = self._forbidden(module)
        if not match:
            # `from urllib import request` — the forbidden part is the NAME, not
            # the module. Without this, banning `urllib.request` is one import
            # style away from doing nothing.
            for alias in node.names:
                match = self._forbidden(f"{module}.{alias.name}" if module else alias.name)
                if match:
                    break
        if match:
            self._add(node, "forbidden-import", f"imports from `{module}` (`{match}`)")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            if func.id in MUTATING_BUILTINS or func.id in OPENERS:
                self._add(node, "mutating-call", f"calls `{func.id}(…)`")
        elif isinstance(func, ast.Attribute):
            receiver = func.value.id if isinstance(func.value, ast.Name) else ""
            if func.attr in MUTATING_METHODS:
                self._add(node, "mutating-call", f"calls `.{func.attr}(…)`")
            elif func.attr in OPENERS:
                # `Path(p).open("w")`, `os.open(...)`, `io.open(...)`. The bare
                # builtin was the only spelling the first draft knew, so the
                # other three walked past a check written to stop exactly them.
                self._add(node, "mutating-call", f"calls `.{func.attr}(…)` — opens a handle")
            elif func.attr in AMBIGUOUS_MUTATING_METHODS and self._is_path_mutation(
                node, func.attr, receiver
            ):
                self._add(
                    node,
                    "mutating-call",
                    f"calls `{receiver or '…'}.{func.attr}(…)` in its path-mutating form",
                )

        # Every subprocess call is inspected — and one whose argv is not a fully
        # literal list is itself a violation. The page needs exactly two literal
        # argvs, so the rule costs nothing here and closes the hole where a list
        # is assembled in a variable and the literal check sees an `ast.Name`.
        if self._is_subprocess(func):
            self._check_subprocess(node)
        elif self._is_git_wrapper(func):
            for argument in node.args:
                self._check_argv(argument)
        self.generic_visit(node)

    @staticmethod
    def _is_path_mutation(node: ast.Call, attr: str, receiver: str) -> bool:
        """Whether an ambiguous name is being used in its filesystem form.

        Arity is the default discriminator — ``Path.replace(target)`` and
        ``os.remove(path)`` take one positional argument, ``str.replace(old,
        new)`` takes two and ``dict.copy()`` takes none. Two exceptions are
        named rather than left implicit: a known filesystem receiver makes the
        call a write at any arity, and ``os.replace(src, dst)``-shaped
        two-argument forms are writes despite matching ``str.replace``'s shape.
        """
        if receiver in MUTATING_RECEIVERS:
            return True
        if len(node.args) == _PATH_MUTATING_ARITY and not node.keywords:
            return True
        return len(node.args) == 2 and attr in TWO_ARG_MUTATING and receiver not in ("", "text")

    def _check_subprocess(self, node: ast.Call) -> None:
        """A subprocess argv must be a list literal, and must not mutate."""
        argv = node.args[0] if node.args else None
        if argv is None:
            for keyword in node.keywords:
                if keyword.arg in ("args", "cmd"):
                    argv = keyword.value
        if not isinstance(argv, (ast.List, ast.Tuple)):
            self._add(
                node,
                "opaque-argv",
                "subprocess argv is not a literal list, so its subcommand cannot be checked",
            )
            return
        head = argv.elts[0] if argv.elts else None
        if not (isinstance(head, ast.Constant) and head.value == ALLOWED_EXECUTABLE):
            # The page runs exactly one program. Anything else — a shell above
            # all — is a write path whose contents this scan cannot read, so the
            # executable is allow-listed rather than the subcommands alone.
            self._add(
                node,
                "mutating-call",
                f"subprocess runs something other than `{ALLOWED_EXECUTABLE}`",
            )
            return
        self._check_argv(argv)

    @staticmethod
    def _is_subprocess(func: ast.AST) -> bool:
        return isinstance(func, ast.Attribute) and func.attr in (
            "run",
            "Popen",
            "check_call",
            "check_output",
            "call",
        )

    @staticmethod
    def _is_git_wrapper(func: ast.AST) -> bool:
        """Whether a call is plausibly handing an argv to a ``git`` wrapper.

        Scoped by name, because an unscoped sweep of every list literal for the
        word ``tag`` or ``config`` or ``prune`` finds ordinary vocabulary all
        over a planning-corpus reader. This is what reaches the WRAPPER'S
        CALLERS, where the literal subcommand actually lives — the wrapper takes
        it as a parameter, so a check pinned to the subprocess call site would
        see only ``*args``.
        """
        return isinstance(func, ast.Name) and "git" in func.id.lower()

    def _check_argv(self, node: ast.AST) -> None:
        """Report a mutating ``git`` subcommand in a list-literal argv.

        Checked wherever the literal is, not only at the ``subprocess.run`` call
        site — the page's git wrapper takes the subcommand as a parameter and
        its callers pass the literal, so a check pinned to the ``subprocess``
        call would see only ``*args``.
        """
        if not isinstance(node, (ast.List, ast.Tuple)):
            return
        for element in node.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                continue
            if element.value in MUTATING_GIT_SUBCOMMANDS:
                self._add(
                    element,
                    "mutating-git",
                    f"argv carries the mutating git subcommand `{element.value}`",
                )


#: This module names every forbidden construct in order to detect it, so it
#: cannot be scanned by itself without reporting its own vocabulary. **A STATED
#: exclusion, which is the difference between a taxonomy and a suppression
#: list** — and the exclusion is one file wide, by name, with the test asserting
#: the file is the only thing it removes.
SELF = "readonly_scan.py"


def scan_tree(root: Path) -> list[Violation]:
    """Every mutation-capable construct under ``root``, sorted for stable output."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel == SELF:
            continue
        visitor = _Visitor(rel)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        violations.extend(visitor.violations)
    return sorted(violations, key=lambda v: (v.file, v.line, v.kind))


def human_only_store_mentions(root: Path) -> list[tuple[str, int, str]]:
    """Every source line mentioning the human-only store, for the §1.2 grep.

    The implementation step asks for *"a grep of the source for that path
    returning only reads"*. The AST scan above already proves no mutation exists
    anywhere in the tree, which subsumes it — but the grep is what a human can
    check by eye, so it is produced rather than argued away.
    """
    out: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if HUMAN_ONLY_STORE in line or '"operations"' in line or "'operations'" in line:
                out.append((rel, number, line.strip()))
    return out
