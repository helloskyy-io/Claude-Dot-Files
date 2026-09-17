"""The viewer's JavaScript, reached from the one test runner.

The six modules under ``renderers/viewer/`` run in a browser, but two of them
carry pure functions — the depth walk in ``neighbourhood.mjs``, the layering
in ``sprint.mjs``, the label wrapper and the layout's ring/row structure in
``graph.mjs`` — that Node can import and hold to a known answer.
Two things are held here:

1. ``tests/js/*.test.mjs`` — Node's built-in runner over hand-drawn inputs;
   this file runs it by explicit path and asserts a non-zero pass count.
2. ``walk()`` against ``planning_ui.views.neighbourhood.neighbourhood()`` on the
   same synthetic index, for the three best-connected components at depths
   1–3. The two walks are the same algorithm written twice (the Python one so
   the tests can hold it; the JavaScript one so a depth change is instant in
   the page); this is the check that they have not drifted.

Node is a TEST runtime here, not part of the viewer's serving path — the
phase's rule 1 (no Node, no bundler, no install step to load the page) is
untouched. A Node absent or too old is a FAILURE, never a skip (Testing
Standard § Tier Enforcement: a gate that cannot locate an interpreter must fail
loudly); the message says where to get one.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import planning_ui.views.neighbourhood as nb

DEV_UI = Path(__file__).resolve().parents[2]
JS_TESTS = sorted((DEV_UI / "tests" / "js").glob("*.test.mjs"))
VIEWER = DEV_UI / "renderers" / "viewer"

#: A SYNTHETIC index with real structure — a hub of degree 3, a chain to depth
#: 3, one isolate — in the exact shape `views.neighbourhood.component_index`
#: emits. Hand-drawn rather than derived from a corpus: the property under
#: test is that the browser's walk equals Python's on the same input, and a
#: graph whose shape is known tests that better than one that happens to be
#: lying around. The tooling's suite tests what the tooling owns.
def synthetic_index() -> dict:
    def comp(name):
        return {"id": f"component:{name}", "kind": "component", "label": name,
                "declares": "links", "owned": [], "referenced": [], "internal": []}
    nodes = {c["id"]: c for c in (comp("hub"), comp("a"), comp("b"), comp("c"), comp("d"), comp("alone"))}
    nodes["standard:s"] = {"id": "standard:s", "kind": "standard", "label": "s", "internal": []}
    edge = lambda s, t, st="satisfied": {"source": f"component:{s}", "target": t, "state": st, "via": []}
    edges = [
        edge("hub", "component:a"), edge("hub", "component:b"), edge("hub", "component:c"),
        edge("a", "component:d"), edge("d", "standard:s", "unsatisfied"),
    ]
    return {"nodes": nodes, "edges": edges}

#: `node --test` arrived in 18; `node:test`'s `assert` module and ES-module
#: imports of the vendored React need nothing newer.
NODE_MIN_MAJOR = 18

NO_NODE = (
    f"the viewer's JavaScript tests need `node` >= {NODE_MIN_MAJOR} on PATH and found {{found}}. "
    "This is a test runtime, not a viewer dependency. On the dev VM, without sudo: "
    '`conda create -p /tmp/node -c conda-forge "nodejs>=20"` then `PATH=/tmp/node/bin:$PATH python -m pytest`. '
    "The pull-request runner installs it with actions/setup-node (see .github/workflows/dev-ui-tier.yml)."
)


def node() -> str:
    """The `node` on PATH, or a failure naming what was found and how to fix it."""
    found = shutil.which("node")
    if found is None:
        pytest.fail(NO_NODE.format(found="no `node` at all"))
    version = subprocess.run([found, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    major = int(re.match(r"v(\d+)", version).group(1))
    if major < NODE_MIN_MAJOR:
        pytest.fail(NO_NODE.format(found=f"{found} = {version}"))
    return found


def test_the_js_test_files_exist_and_are_the_three_modules_with_pure_exports():
    """Positive control for the runner test below: a glob that matched zero
    files would otherwise report zero failures and look green. One file per
    viewer module that exports a pure function (`graph.mjs`: `layout`,
    `wrapLabel`; `neighbourhood.mjs`: `walk`; `sprint.mjs`: `levels`);
    `app.mjs`'s `parseRoute`/`formatRoute` cannot be imported without a DOM."""
    assert [p.name for p in JS_TESTS] == ["graph.test.mjs", "neighbourhood.test.mjs", "sprint.test.mjs"]


def test_node_runs_the_js_tests_and_every_one_passes():
    proc = subprocess.run(
        [node(), "--test", "--test-reporter=tap", *map(str, JS_TESTS)],
        capture_output=True, text=True, cwd=DEV_UI,
    )
    tap = proc.stdout
    summary = re.search(r"^# pass (\d+)$", tap, re.M), re.search(r"^# fail (\d+)$", tap, re.M)
    if not all(summary):
        # No TAP summary at all: node crashed before the runner reported, or
        # a test file failed to parse. Show what it said rather than a bare
        # AttributeError on the missing match.
        pytest.fail(f"node --test produced no TAP summary (exit {proc.returncode}):\n{tap}\n{proc.stderr}")
    passed, failed = (int(m.group(1)) for m in summary)
    assert proc.returncode == 0 and failed == 0, f"node --test failed:\n{tap}\n{proc.stderr}"
    assert passed >= 14, f"positive control: the three files carry fourteen tests, TAP reports {passed}"


# ---- the browser's walk against the Python walk, on one synthetic index -------

_PROBE = """
import fs from "node:fs";
import { walk } from "{viewer}/neighbourhood.mjs";
const index = JSON.parse(fs.readFileSync("{view_inputs}", "utf8")).neighbourhood;
const out = [];
for (const [root, depth] of JSON.parse(process.argv[1])) {
  const r = walk(index, root, depth);
  out.push({ root, depth, order: r.order, distance: Object.fromEntries(r.distance),
             edges: r.edges.map((e) => [e.source, e.target]) });
}
process.stdout.write(JSON.stringify(out));
"""


def test_the_browser_walk_agrees_with_the_python_walk(tmp_path):
    index = synthetic_index()
    view_inputs = tmp_path / "view-inputs.json"
    view_inputs.write_text(json.dumps({"neighbourhood": index}))
    degree: dict[str, int] = {}
    for e in index["edges"]:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1
    roots = sorted(
        (n for n in index["nodes"] if index["nodes"][n]["kind"] == "component"),
        key=lambda n: (-degree.get(n, 0), n),
    )[:3]
    assert degree.get(roots[0], 0) >= 2, "positive control: the best-connected component has neighbours"
    queries = [(root, depth) for root in roots for depth in (1, 2, 3)]

    probe = _PROBE.replace("{viewer}", VIEWER.as_uri()).replace("{view_inputs}", str(view_inputs))
    proc = subprocess.run(
        [node(), "--input-type=module", "-e", probe, "--", json.dumps(queries)],
        capture_output=True, text=True, check=True,
    )
    js = json.loads(proc.stdout)
    assert len(js) == len(queries) == 9

    for got in js:
        py = nb.neighbourhood(index, got["root"], got["depth"])
        assert got["order"] == py["order"], (got["root"], got["depth"])
        assert got["distance"] == py["distance"], (got["root"], got["depth"])
        assert got["edges"] == [[e["source"], e["target"]] for e in py["edges"]], (got["root"], got["depth"])
    assert any(len(g["order"]) > 1 for g in js), "positive control: at least one query returned neighbours"
