"""Requirement 6: the generator is structurally incapable of writing `tracked/`.

**Intent does not satisfy this requirement and the phase doc says so.** §1.2 of
the Tracked Items Standard reserves ``tracked/operations/`` to humans — *"no
workflow, dispatch or agent writes into it, ever"* — and records that moving
``tracked/`` to the repo root took the store OUT of every path-prefix write
guard silently, so the only protection standing today is prose.

**Every assertion here has a verified negative control.** A structural check
that cannot fail is worse than no check: it manufactures confidence. So each
test drives the same scanner at a scratch module that deliberately writes, and
requires it to go red.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from planning_ui.decisions import readonly_scan

DECISIONS = Path(readonly_scan.__file__).resolve().parent
PLAN_EXTRACTOR = DECISIONS.parent / "plan_extractor"


# ---------------------------------------------------------------------------
# The proof
# ---------------------------------------------------------------------------
def test_the_decisions_package_holds_no_write_path():
    """The package that renders `tracked/operations/` cannot mutate anything."""
    violations = readonly_scan.scan_tree(DECISIONS)
    assert violations == [], "\n".join(str(v) for v in violations)


def test_the_reader_it_consumes_holds_no_write_path():
    """The proof has to cover the WHOLE read path, not this package alone.

    `services/decisions/` opens no file itself — it delegates every read to
    `plan_extractor`. A proof scoped to the consumer would be satisfied by a
    package that simply calls a writer, which is the shape the requirement is
    guarding against.
    """
    violations = readonly_scan.scan_tree(PLAN_EXTRACTOR)
    assert violations == [], "\n".join(str(v) for v in violations)


def test_every_mention_of_the_human_only_store_is_a_read():
    """The §1.2 grep the implementation step asks for, produced rather than argued.

    The AST scan above subsumes it — no mutation exists anywhere in the tree —
    but the grep is what a human can check by eye, so it is emitted. Each line is
    asserted free of any mutating verb.
    """
    mentions = readonly_scan.human_only_store_mentions(DECISIONS)
    assert mentions, "the store is rendered, so the source must mention it"
    verbs = (
        readonly_scan.MUTATING_METHODS
        | readonly_scan.MUTATING_BUILTINS
        | readonly_scan.AMBIGUOUS_MUTATING_METHODS
    )
    for rel, line_no, text in mentions:
        for verb in verbs:
            assert f"{verb}(" not in text, f"{rel}:{line_no} — {text}"


def test_the_self_exclusion_removes_exactly_one_file():
    """The scanner excludes itself, and the exclusion is one file wide.

    It names every forbidden construct in order to detect them, so it cannot
    scan itself without reporting its own vocabulary. A stated exclusion is only
    legitimate while it is this narrow — an exclusion that quietly grew to cover
    a second file would be a suppression list.
    """
    scanned = {
        p.relative_to(DECISIONS).as_posix()
        for p in DECISIONS.rglob("*.py")
        if p.relative_to(DECISIONS).as_posix() != readonly_scan.SELF
    }
    everything = {p.relative_to(DECISIONS).as_posix() for p in DECISIONS.rglob("*.py")}
    assert everything - scanned == {readonly_scan.SELF}


# ---------------------------------------------------------------------------
# The negative controls — the scanner must go red when the property is violated
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "source,kind",
    [
        (
            "from pathlib import Path\n"
            "def render(root):\n"
            "    (root / 'tracked/operations/O-x.md').write_text('ruled')\n",
            "mutating-call",
        ),
        (
            "def render(root):\n"
            "    with open(root / 'tracked/operations/O-x.md', 'w') as fh:\n"
            "        fh.write('ruled')\n",
            "mutating-call",
        ),
        (
            "import subprocess\n"
            "def render(root):\n"
            "    subprocess.run(['git', '-C', root, 'commit', '-m', 'ruled'])\n",
            "mutating-git",
        ),
        (
            "import shutil\n"
            "def render(root):\n"
            "    return root\n",
            "forbidden-import",
        ),
        (
            "import requests\n"
            "def render(root):\n"
            "    return requests.get('https://api.github.com/issues')\n",
            "forbidden-import",
        ),
        (
            "from pathlib import Path\n"
            "def render(root):\n"
            "    Path(root, 'tracked', 'operations').mkdir(parents=True)\n",
            "mutating-call",
        ),
        # --- the shapes the first draft of the scanner missed entirely -------
        # Each of these was found by a reviewer reading the scanner rather than
        # by a test, which is why every one of them now HAS a test.
        (
            "from pathlib import Path\n"
            "def render(root):\n"
            "    fh = Path(root, 'tracked/operations/O-x.md').open('w')\n"
            "    fh.write('ruled')\n",
            "mutating-call",
        ),
        (
            "import os\n"
            "def render(root):\n"
            "    fd = os.open(root + '/tracked/operations/O-x.md', os.O_WRONLY)\n"
            "    os.write(fd, b'ruled')\n",
            "mutating-call",
        ),
        (
            "import os\n"
            "def render(src, dst):\n"
            "    os.replace(src, dst)\n",
            "mutating-call",
        ),
        (
            "import os\n"
            "def render(root):\n"
            "    os.system('echo ruled > tracked/operations/O-x.md')\n",
            "mutating-call",
        ),
        (
            "from pathlib import Path\n"
            "def render(root):\n"
            "    getattr(Path(root), 'write_text')('ruled')\n",
            "mutating-call",
        ),
        (
            "def render(root, payload):\n"
            "    exec(payload)\n",
            "mutating-call",
        ),
        (
            "import subprocess\n"
            "def render(root, argv):\n"
            "    subprocess.run(argv)\n",
            "opaque-argv",
        ),
        (
            "import subprocess\n"
            "def render(root):\n"
            "    cmd = ['git', '-C', root, 'commit', '-m', 'x']\n"
            "    subprocess.run(cmd)\n",
            "opaque-argv",
        ),
        (
            "import subprocess\n"
            "def render(root):\n"
            "    subprocess.run(['sh', '-c', 'rm -rf tracked/operations'])\n",
            "mutating-call",
        ),
    ],
)
def test_the_scanner_fires_on_a_deliberate_write(tmp_path: Path, source: str, kind: str):
    """The verified negative control: break the property, watch the check go red."""
    (tmp_path / "writer.py").write_text(source, encoding="utf-8")
    violations = readonly_scan.scan_tree(tmp_path)
    assert violations, f"the scanner missed a deliberate {kind}"
    assert any(v.kind == kind for v in violations), [str(v) for v in violations]


def test_the_scanner_passes_a_read_only_module(tmp_path: Path):
    """The other half of the control — it is not simply always red.

    A scanner that fails on everything proves nothing about the packages above.
    This module reads a file, resolves a path and runs a read-only `git`
    subcommand, which is precisely the shape the real package has.
    """
    (tmp_path / "reader.py").write_text(
        "import subprocess\n"
        "from pathlib import Path\n"
        "def render(root):\n"
        "    text = (Path(root) / 'tracked/operations/O-x.md').read_text()\n"
        "    subprocess.run(['git', '-C', str(root), 'log', '--name-status'])\n"
        "    return text\n",
        encoding="utf-8",
    )
    assert readonly_scan.scan_tree(tmp_path) == []


def test_the_module_does_not_claim_to_be_a_proof_of_impossibility(tmp_path: Path):
    """The guard states its own ceiling, and this test is what keeps it stating it.

    Two reviewers independently had to correct a docstring that called this
    scan "structurally incapable" of writing. It is not, and it cannot be: a
    name-and-arity scan over one package's own source is walkable-around by
    construction. The enforced control is the `readOnly: true` corpus mount in
    the pod; this is a regression guard against careless additions everywhere
    else.

    Asserted rather than commented, because the overclaim is the thing that
    actually costs a reviewer their time — a guard people believe is a proof
    gets trusted for decisions it cannot support.
    """
    header = readonly_scan.__doc__ or ""
    assert "regression guard" in header
    assert "NOT a proof" in header
    assert "readOnly: true" in header, "the enforced control must be named, not implied"


def test_the_argv_check_reaches_a_wrapper_call_site(tmp_path: Path):
    """A mutating subcommand is caught where the LITERAL is, not where git runs.

    The page's git wrapper takes the subcommand as a parameter, so a check
    pinned to the `subprocess.run` call site would see only `*args` and pass a
    module whose caller passes `['commit', ...]`.
    """
    (tmp_path / "wrapper.py").write_text(
        "import subprocess\n"
        "def _run_git(root, args):\n"
        "    return subprocess.run(['git', '-C', str(root), *args])\n"
        "def render(root):\n"
        "    return _run_git(root, ['commit', '-m', 'ruled'])\n",
        encoding="utf-8",
    )
    violations = readonly_scan.scan_tree(tmp_path)
    assert [v.kind for v in violations] == ["mutating-git"]
