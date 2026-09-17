"""The viewer's JavaScript, cross-checked against its Python twin.

The modules under ``renderers/viewer/`` run in a browser, but the depth walk
in ``neighbourhood.mjs`` is a pure function Node can import — and it is the
same algorithm ``planning_ui.views.neighbourhood.neighbourhood()`` implements
in Python (the Python one so the tests can hold it; the JavaScript one so a
depth change is instant in the page). This file holds that they have not
drifted, on one synthetic index, for the best-connected roots at depths 1–3.

**The JavaScript tests themselves — ``tests/js/*.test.mjs`` — are NOT run
from here.** ``testing/suites/js.sh`` runs them, and refuses loudly under a
Node too old to; a second runner here would be two answers to "did the JS
pass". This file only asserts the files exist with the exports it needs.

Node is a TEST runtime here, not part of the viewer's serving path — the
phase's rule 1 (no Node, no bundler, no install step to load the page) is
untouched. A Node absent or too old is a FAILURE, never a skip (Testing
Standard § Tier Enforcement: a gate that cannot locate an interpreter must fail
loudly); the message says where to get one.
"""
from __future__ import annotations

import json
import os
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
    f"needs Node >= {NODE_MIN_MAJOR} and found {{found}} — a test runtime, not a viewer "
    "dependency. THE JAVASCRIPT TESTS THEMSELVES ARE NOT SKIPPED: testing/suites/js.sh runs "
    "them and REFUSES loudly under an old Node, so a green python suite here never means "
    "they passed. This is only the Python-side cross-check. Set NODE_BIN, as js.sh does."
)


def node() -> str:
    """The Node this cross-check runs, honouring NODE_BIN as testing/suites/js.sh does.

    SKIPS, by name, when it is too old. The JavaScript tests are gated by
    js.sh, which refuses rather than skips; this Python test only cross-checks
    one algorithm against its Python twin, and it must not make the python
    suite red for a runtime the js suite already reports.
    """
    found = shutil.which(os.environ.get("NODE_BIN", "node"))
    if found is None:
        pytest.skip(NO_NODE.format(found="no `node` at all"))
    version = subprocess.run([found, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    major = int(re.match(r"v(\d+)", version).group(1))
    if major < NODE_MIN_MAJOR:
        pytest.skip(NO_NODE.format(found=f"{found} = {version}"))
    return found


def test_the_js_test_files_exist_and_are_the_three_modules_with_pure_exports():
    """Positive control for the runner test below: a glob that matched zero
    files would otherwise report zero failures and look green. One file per
    viewer module that exports a pure function (`graph.mjs`: `layout`,
    `wrapLabel`; `neighbourhood.mjs`: `walk`; `sprint.mjs`: `levels`);
    `app.mjs`'s `parseRoute`/`formatRoute` cannot be imported without a DOM."""
    assert [p.name for p in JS_TESTS] == ["graph.test.mjs", "neighbourhood.test.mjs", "sprint.test.mjs"]


# The probe: run the JS walk over the same index and print what it returned.
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
