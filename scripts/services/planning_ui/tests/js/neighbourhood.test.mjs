// The browser's depth walk, held to the same answers `test_views_neighbourhood.py`
// holds `planning_ui.views.neighbourhood.neighbourhood()` to.
//
// Run by `node --test` (Node >= 18's built-in runner — no npm, no package.json,
// no node_modules). Reached from the one test runner by
// `tests/unit/test_viewer_js.py`, which also holds `walk()` to the Python
// copy on the live corpus; run directly with
//   node --test planning_ui/tests/js/neighbourhood.test.mjs
//
// `app.mjs` is NOT under test here: it calls `createRoot(document…)` at module
// level, so it cannot be imported without a DOM. `parseRoute`/`formatRoute`
// are covered only by the browser session the phase doc records.

import { test } from "node:test";
import assert from "node:assert/strict";
import { walk, DEFAULT_DEPTH, DEFAULT_NODE_CAP } from "../../renderers/viewer/neighbourhood.mjs";

// The Python unit fixture AFTER `component_index()` — three components, one
// missing target, one standard: a→b satisfied, a→(missing p9) broken,
// b→c underivable, a→x satisfied. Only ids and edge endpoints matter to the
// walk, so the nodes carry nothing else.
const A = "component:development/common/a";
const B = "component:development/common/b";
const C = "component:development/common/c";
const P9 = "phase:development/common/nowhere/p9.md";
const X = "standard:standards/x.md";

function index() {
  const nodes = {};
  for (const id of [A, B, C, P9, X]) nodes[id] = { id };
  return {
    nodes,
    edges: [
      { source: A, target: B, state: "satisfied" },
      { source: A, target: P9, state: "broken" },
      { source: B, target: C, state: "underivable" },
      { source: A, target: X, state: "satisfied" },
    ],
  };
}

test("depth 0 is the root alone", () => {
  const r = walk(index(), A, 0);
  assert.deepEqual(r.order, [A]);
  assert.deepEqual(r.edges, []);
});

test("depth 1 is exactly the direct neighbours, nearest-first and sorted within a ring", () => {
  const r = walk(index(), A, 1);
  assert.deepEqual(r.order, [A, B, P9, X]);
  for (const id of [B, P9, X]) assert.equal(r.distance.get(id), 1);
  assert.equal(r.distance.get(C), undefined, "c is two steps away and must not appear");
  // only edges among the returned nodes
  assert.deepEqual(r.edges.map((e) => [e.source, e.target]), [[A, B], [A, P9], [A, X]]);
});

test("depth 2 reaches c through b, after b", () => {
  const r = walk(index(), A, 2);
  assert.equal(r.distance.get(C), 2);
  assert.equal(r.order[0], A);
  assert.ok(r.order.indexOf(C) > r.order.indexOf(B));
  assert.equal(r.edges.length, 4, "every index edge is among the returned nodes at depth 2");
});

test("the walk runs against the edge direction too", () => {
  const r = walk(index(), C, 1);
  assert.deepEqual(r.order, [C, B]);
});

test("the defaults are the measured legibility figure", () => {
  assert.equal(DEFAULT_DEPTH, 2);
  assert.equal(DEFAULT_NODE_CAP, 25);
});
