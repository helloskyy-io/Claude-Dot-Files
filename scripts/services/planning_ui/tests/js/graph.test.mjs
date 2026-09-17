// graph.mjs's two pure exports: the label wrapper and the layout.
//
// `layout()` runs d3-force to rest; positions are not asserted to the pixel
// (a force layout is a reading of the graph, not a canonical picture — phase
// doc § What is committed) but the STRUCTURE each shape promises is: rings by
// level for the radial page, rows by level for the layered one.
//
// Run by `node --test`; reached from the one runner by
// `tests/unit/test_viewer_js.py`. See neighbourhood.test.mjs for why
// `app.mjs` is not imported here.

import { test } from "node:test";
import assert from "node:assert/strict";
import { layout, wrapLabel } from "../../renderers/viewer/graph.mjs";

test("a short label is one line, untouched", () => {
  assert.deepEqual(wrapLabel("common/planning_ui"), ["common/planning_ui"]);
});

test("a long label breaks after a slash, space or middle dot, never mid-word", () => {
  const lines = wrapLabel("service/home-auto/phase6_elk_m1_alarm_panel", 24, 3);
  assert.deepEqual(lines, ["service/home-auto/", "phase6_elk_m1_alarm_panel"]);
  for (const l of lines) assert.ok(l.length <= 25, l);
});

test("past the line limit the last line is elided with an ellipsis", () => {
  const lines = wrapLabel("one two three four five six seven eight nine ten eleven twelve thirteen fourteen", 12, 3);
  assert.equal(lines.length, 3);
  assert.ok(lines[2].endsWith("…"), lines[2]);
  assert.ok(lines[2].length <= 12, lines[2]);
});

const box = { width: 1400, height: 900 };
const nodes = ["r", "a", "b", "c", "d"].map((id) => ({ id }));
const edges = [["r", "a"], ["r", "b"], ["a", "c"], ["b", "d"]].map(([source, target]) => ({ source, target }));
const lvl = { r: 0, a: 1, b: 1, c: 2, d: 2 };
const level = (n) => lvl[n.id];

test("no nodes → no positions; every node gets finite coordinates", () => {
  assert.deepEqual(layout([], [], { shape: "radial", level, ...box }), {});
  const pos = layout(nodes, edges, { shape: "radial", level, ...box });
  assert.deepEqual(Object.keys(pos).sort(), ["a", "b", "c", "d", "r"]);
  for (const p of Object.values(pos)) assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y));
});

test("radial: each level sits on a ring farther from the centre than the one before", () => {
  const pos = layout(nodes, edges, { shape: "radial", level, ...box });
  const dist = (id) => Math.hypot(pos[id].x - box.width / 2, pos[id].y - box.height / 2);
  const ring = (l) => nodes.filter((n) => lvl[n.id] === l).map((n) => dist(n.id));
  assert.ok(Math.max(...ring(0)) < Math.min(...ring(1)), "root inside ring 1");
  assert.ok(Math.max(...ring(1)) < Math.min(...ring(2)), "ring 1 inside ring 2");
});

test("layered: a higher level is a lower row, and rows do not interleave", () => {
  const pos = layout(nodes, edges, { shape: "layered", level, ...box });
  const row = (l) => nodes.filter((n) => lvl[n.id] === l).map((n) => pos[n.id].y);
  assert.ok(Math.max(...row(0)) < Math.min(...row(1)), "level 0 above level 1");
  assert.ok(Math.max(...row(1)) < Math.min(...row(2)), "level 1 above level 2");
});

// The Component page's tag drawing reuses the sprint board's `flow` layout,
// so the same node order guarantee has to hold for a neighbourhood walk —
// which arrives root-first, nearest-first, and must stay that way.
test("flow keeps a neighbourhood's nearest-first order", () => {
  const walked = [
    { id: "root", label: "root" },
    { id: "ring1a", label: "a" },
    { id: "ring1b", label: "b" },
    { id: "ring2", label: "c" },
  ];
  const pos = layout(walked, [{ source: "ring2", target: "root" }], { shape: "flow", ...box });
  const ys = walked.map((n) => pos[n.id].y);
  assert.deepEqual([...ys].sort((a, b) => a - b), ys, "row order is the walk's order");
  assert.equal(pos.root.x, pos.ring2.x, "one column, whatever the distance");
});
