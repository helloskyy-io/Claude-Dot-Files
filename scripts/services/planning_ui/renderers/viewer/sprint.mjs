// Page 3 — one sprint's board, beside the rendered sprint.
//
// Both halves read `views.sprints[name]` — ONE item list. The board draws the
// items as nodes with the directed edges the extractor's dependencies give
// them; the list beside it is the same array in file order, each item with
// the line it was read from. Selecting on either side highlights both.
//
// The board draws items in the order the sprint STATES, one per row, because
// that order is the document's meaning. It was laid out by dependency depth
// until 2026-09-14; the operator's reading was that the result was chaotic to
// read against the file it draws, and the file's own order is what a reader
// is holding in their head.

import React from "../vendor/react@19.0.0/react.mjs";
import { ForceGraph } from "./graph.mjs";
import { Legend, StateBadge, Counts } from "./panel.mjs";

const h = React.createElement;
const { useState } = React;

function ItemPanel({ item, board, onNavigate }) {
  const out = board.edges.filter((e) => e.source === item.id);
  const inc = board.edges.filter((e) => e.target === item.id);
  const name = (id) => { const it = board.items.find((i) => i.id === id); return it ? it.label : id; };
  const hours = item.hours_low == null ? "—" : item.hours_high ? `~${item.hours_low}–${item.hours_high}h` : `~${item.hours_low}h`;
  return h("div", null,
    h("h2", null, item.label),
    h("dl", null,
      h("dt", null, "read from"), h("dd", { className: "mono" }, `development/sprints.md:${item.line}`),
      h("dt", null, "state"), h("dd", null, item.checked ? "checked — closed" : "unchecked — open"),
      h("dt", null, "layer · hours"), h("dd", null, `${item.layer == null ? "no L<n>" : `L${item.layer}`} · ${hours}`),
      h("dt", null, "schedules"), h("dd", null, item.schedules.length ? h("ul", null, item.schedules.map((s) => h("li", { key: s, className: "mono" }, s))) : h("span", { className: "muted" }, "nothing this graph knows")),
      item.unresolved.length ? [h("dt", { key: "u" }, "links that resolve to no node"), h("dd", { key: "uv" }, h("ul", null, item.unresolved.map((s) => h("li", { key: s, className: "mono" }, s))))] : null,
      !item.linked ? [h("dt", { key: "l" }, "note"), h("dd", { key: "lv" }, "this item links no phase and no roadmap — nothing can be derived about it, which is a different fact from having no dependencies")] : null,
    ),
    h("h3", null, `depends on (${out.length})`),
    out.length ? h("ul", null, out.map((e) => h("li", { key: e.target }, h("button", { className: "link", onClick: () => onNavigate(e.target) }, name(e.target)), h(StateBadge, { state: e.state }),
      h("ul", null, e.via.map((v, i) => h("li", { key: i, className: "mono muted" }, `${v.source.split(":").slice(1)} → ${v.target.split(":").slice(1)} (${v.file}:${v.line})`)))))) : h("p", { className: "muted" }, "no item in this sprint"),
    h("h3", null, `depended on by (${inc.length})`),
    inc.length ? h("ul", null, inc.map((e) => h("li", { key: e.source }, h("button", { className: "link", onClick: () => onNavigate(e.source) }, name(e.source)), h(StateBadge, { state: e.state })))) : h("p", { className: "muted" }, "no item in this sprint"),
  );
}

export function SprintPage({ views, route, navigate }) {
  const names = Object.keys(views.sprints);
  const name = route.id && views.sprints[route.id] ? route.id : names[0];
  const board = views.sprints[name];
  const [selected, setSelected] = useState(null);
  const nodes = board.items.map((i) => ({ ...i, kind: "sprint_item" }));
  const counts = {
    "items": board.items.length,
    "closed": board.items.filter((i) => i.checked).length,
    "edges among items": board.edges.length,
    "items linking no phase or roadmap": board.items.filter((i) => !i.linked).length,
    "items with a link that resolves to no node": board.items.filter((i) => i.unresolved.length).length,
    "broken edges": board.edges.filter((e) => e.state === "broken").length,
    "unsatisfied edges": board.edges.filter((e) => e.state === "unsatisfied").length,
  };
  const selectedItem = board.items.find((i) => i.id === selected) || null;

  return h(React.Fragment, null,
    h("div", { className: "controls" },
      h("button", {
        className: "back", onClick: () => navigate({ page: "sprint", id: "" }),
        title: "back to every sprint",
      }, "← all sprints"),
      h("label", null, "sprint",
        h("select", { value: name, onChange: (e) => { setSelected(null); navigate({ page: "sprint", id: e.target.value }); } },
          names.map((n) => h("option", { key: n, value: n }, `${n} ${views.sprints[n].marker ? `· ${views.sprints[n].marker}` : ""}`)))),
      h("span", { className: "note mono" }, `development/sprints.md:${board.line}`),
      h("span", { className: "note" }, "an edge A → B: something A schedules depends on something B schedules · click an item on either side"),
    ),
    h("div", { className: "page" },
      h("div", { className: "canvas" },
        board.items.length
          ? h(ForceGraph, { nodes, edges: board.edges, shape: "flow", selected, onSelect: (id) => setSelected(id) })
          : h("p", { className: "loading" }, "this sprint has no items")),
      h("aside", null,
        selectedItem ? h(ItemPanel, { item: selectedItem, board, onNavigate: setSelected }) : h("p", { className: "muted" }, "select an item"),
        h("h3", null, "this sprint"), h(Counts, { rows: counts, prefix: "sprint" }),
        h("h3", null, `the sprint as written (${board.items.length} items)`),
        h("ol", { className: "sprint-list", "data-rendered-items": board.items.length }, board.items.map((i) => h("li", {
          key: i.id, className: `${i.id === selected ? "selected" : ""} ${i.linked ? "" : "unlinked"}`, onClick: () => setSelected(i.id), "data-item": i.id,
        },
          h("span", { className: "line" }, `L${i.line} `), i.checked ? "☑ " : "☐ ", i.label,
          !i.linked ? h("span", { className: "badge state-broken" }, "no link") : null,
          i.unresolved.length ? h("span", { className: "badge state-broken" }, "link → nothing") : null,
          h("span", { className: "raw" }, i.raw),
        ))),
        h(Legend, null),
      ),
    ),
  );
}
