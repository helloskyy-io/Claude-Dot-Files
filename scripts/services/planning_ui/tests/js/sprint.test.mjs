// The sprint board's layout — held to the property the operator asked for:
// the board draws the sprint's OWN order, one item per row.
//
// This file tested `levels()` — a longest-path-to-a-sink layering — until
// 2026-09-14. The board no longer lays out by dependency depth, so the
// function it tested is gone and these assert the layout that replaced it.
// A position test is admissible here precisely because `flow` computes
// positions arithmetically rather than by simulation: there is an exact
// answer, so the test can state it.

import { test } from "node:test";
import assert from "node:assert/strict";
import { layout, TAG } from "../../renderers/viewer/graph.mjs";

const box = { width: 1000, height: 700 };
const items = (...ids) => ids.map((id) => ({ id, label: id, kind: "sprint_item" }));
const edge = (source, target) => ({ source, target, state: "satisfied" });

test("every item is on its own row, in the order given", () => {
  const nodes = items("a", "b", "c");
  const pos = layout(nodes, [], { shape: "flow", ...box });
  assert.ok(pos.a.y < pos.b.y && pos.b.y < pos.c.y, "row order follows the item order");
  assert.equal(pos.b.y - pos.a.y, TAG.pitch, "rows are one pitch apart");
  assert.equal(pos.c.y - pos.b.y, TAG.pitch);
});

test("the column is one x for every item — a sprint is a sequence, not a scatter", () => {
  const pos = layout(items("a", "b", "c"), [], { shape: "flow", ...box });
  assert.equal(pos.a.x, pos.b.x);
  assert.equal(pos.b.x, pos.c.x);
});

test("edges do not move anything: the order drawn is the order stated", () => {
  const nodes = items("a", "b", "c");
  const bare = layout(nodes, [], { shape: "flow", ...box });
  // `c` depends on `a`, which under a dependency layout would reorder them.
  const linked = layout(nodes, [edge("c", "a"), edge("b", "a")], { shape: "flow", ...box });
  assert.deepEqual(linked, bare, "a dependency changes the arrows, never the rows");
});

test("no nodes → no positions", () => {
  assert.deepEqual(layout([], [], { shape: "flow", ...box }), {});
});

test("the tag is wide enough to carry its label and leaves room for the point", () => {
  assert.ok(TAG.w > 200, "a tag holds text inside it; a dot does not");
  assert.ok(TAG.point > 0 && TAG.point < TAG.w / 2, "the point is an end, not the shape");
});
