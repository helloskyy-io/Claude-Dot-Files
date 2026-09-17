// Page 2 — a component's dependency neighbourhood, at a depth chosen here.
//
// Backstage's Catalog Graph convention, adopted unchanged: the depth-limited
// neighbourhood of ONE entity, never the whole graph. The walk below is the
// same breadth-first walk as `planning_ui/views/neighbourhood.py::neighbourhood`
// — that copy is the one the tests hold to a hand-known answer; this one
// runs in the browser so a depth change is instant rather than a re-derive.
// Nearest-first order is what the node cap truncates by.

import React from "../vendor/react@19.0.0/react.mjs";
import { ForceGraph } from "./graph.mjs";
import { Legend, StateBadge, Counts } from "./panel.mjs";

const h = React.createElement;
const { useEffect, useMemo, useState } = React;

// The default depth and the node cap, set from the measured legibility
// figure — see the phase doc's runtime verification: the radial layout was
// read clearly at 25 nodes and became a ring of overlapping labels past
// ~30. The cap is a default the reader raises, not a hard split.
export const DEFAULT_DEPTH = 2;
export const DEFAULT_NODE_CAP = 25;

export function walk(index, rootId, depth) {
  const adjacency = new Map();
  const add = (a, b) => { if (!adjacency.has(a)) adjacency.set(a, new Set()); adjacency.get(a).add(b); };
  for (const e of index.edges) { add(e.source, e.target); add(e.target, e.source); }
  const distance = new Map([[rootId, 0]]);
  const order = [rootId];
  const queue = [rootId];
  while (queue.length) {
    const current = queue.shift();
    if (distance.get(current) >= depth) continue;
    const next = [...(adjacency.get(current) || [])].sort();
    for (const n of next) {
      if (distance.has(n)) continue;
      distance.set(n, distance.get(current) + 1);
      order.push(n);
      queue.push(n);
    }
  }
  const edges = index.edges.filter((e) => distance.has(e.source) && distance.has(e.target));
  return { order, distance, edges };
}

function Via({ via, phases }) {
  return h("ul", null, via.map((v, i) => h("li", { key: i, className: "mono" },
    `${v.source.split(":").slice(1).join(":")} → ${v.target.split(":").slice(1).join(":")}`,
    h(StateBadge, { state: v.state }),
    h("div", { className: "muted" }, `${v.file}:${v.line}`),
  )));
}

function NodePanel({ node, index, onNavigate }) {
  const out = index.edges.filter((e) => e.source === node.id);
  const inc = index.edges.filter((e) => e.target === node.id);
  const link = (id) => h("button", { className: "link", onClick: () => onNavigate(id) }, id.split(":").slice(1).join(":"));
  return h("div", null,
    h("h2", null, node.label),
    h("dl", null,
      h("dt", null, "kind"), h("dd", null, node.kind === "missing" ? "missing — the edge resolves to no node" : node.kind),
      node.file ? [h("dt", { key: "f" }, "read from"), h("dd", { key: "fv", className: "mono" }, `${node.file}:${node.line}`)] : null,
      node.kind === "component" ? [
        h("dt", { key: "d" }, "declares"),
        h("dd", { key: "dv" }, node.declares === "nothing" ? "nothing a parser can read — a worklist entry"
          : node.declares === "prose-only" ? "in prose only — a worklist entry"
          : node.declares === "excepted" ? `excepted (${node.disposition})` : node.declares || "—"),
        h("dt", { key: "s" }, "status line"), h("dd", { key: "sv" }, node.status || "—"),
      ] : null,
    ),
    node.kind === "component" && node.owned_phases.length ? [
      h("h3", { key: "oh" }, `own phases (${node.owned_phases.length})`),
      h("ul", { key: "ol" }, node.owned_phases.map((id) => {
        const ph = index.phases[id];
        return h("li", { key: id, className: "mono" }, ph ? ph.label : id, h("span", { className: "badge" }, ph && ph.status ? ph.status : "no status"));
      }),
      ),
    ] : null,
    h("h3", null, `depends on (${out.length})`),
    out.length ? h("ul", null, out.map((e) => h("li", { key: e.target }, link(e.target), h(StateBadge, { state: e.state }), h(Via, { via: e.via, phases: index.phases })))) : h("p", { className: "muted" }, "nothing across a component boundary"),
    h("h3", null, `depended on by (${inc.length})`),
    inc.length ? h("ul", null, inc.map((e) => h("li", { key: e.source }, link(e.source), h(StateBadge, { state: e.state }), h(Via, { via: e.via, phases: index.phases })))) : h("p", { className: "muted" }, "nothing"),
    node.internal && node.internal.length ? [
      h("h3", { key: "ih" }, `within this component (${node.internal.length})`),
      h("p", { key: "ip", className: "muted" }, "one of its phases depending on another — not drawn, because it crosses no boundary"),
      h(Via, { key: "iv", via: node.internal, phases: index.phases }),
    ] : null,
  );
}

export function NeighbourhoodPage({ views, route, navigate }) {
  const index = views.neighbourhood;
  const components = Object.values(index.nodes).filter((n) => n.kind === "component");
  const rootId = route.id && index.nodes[route.id] ? route.id : (components[0] && components[0].id);
  const depth = Number.isFinite(route.depth) ? route.depth : DEFAULT_DEPTH;
  const cap = Number.isFinite(route.cap) ? route.cap : DEFAULT_NODE_CAP;
  const [selected, setSelected] = useState(rootId);
  // The route is the source of truth for the root (back/forward, a pasted
  // URL); the selection follows it rather than pointing at a node that may
  // no longer be drawn.
  useEffect(() => { setSelected(rootId); }, [rootId]);

  const result = useMemo(() => (rootId ? walk(index, rootId, depth) : { order: [], distance: new Map(), edges: [] }), [index, rootId, depth]);
  const shown = result.order.slice(0, cap);
  const shownSet = new Set(shown);
  const nodes = shown.map((id) => index.nodes[id]);
  const edges = result.edges.filter((e) => shownSet.has(e.source) && shownSet.has(e.target));
  const truncated = result.order.length - shown.length;

  const inView = {
    "components declaring nothing": nodes.filter((n) => n.kind === "component" && n.declares === "nothing").length,
    "broken edges": edges.filter((e) => e.state === "broken").length,
    "unsatisfied edges": edges.filter((e) => e.state === "unsatisfied").length,
    "underivable edges": edges.filter((e) => e.state === "underivable").length,
    "satisfied edges": edges.filter((e) => e.state === "satisfied").length,
  };
  const c = views.state_counts;
  const corpus = {
    "components declaring nothing": `${c.components_declaring_nothing} of ${c.components}`,
    "broken edges": c.edges_broken,
    "unsatisfied edges": c.edges_unsatisfied,
    "underivable edges": c.edges_underivable,
    "satisfied edges": c.edges_satisfied,
    "components declaring in prose only": c.components_prose_only,
  };

  // Tags are the default: a reader identifying something reads a label, and
  // a label beside a dot is a scatter plot. The sphere drawing stays one
  // control away because it shows SHAPE — clusters, isolates, how far a
  // neighbourhood reaches — which a list flattens away.
  const view = route.view === "graph" ? "graph" : "tags";
  const go = (patch) => navigate({ page: "component", id: rootId, depth, cap, view, ...patch });
  const selectedNode = index.nodes[selected] || index.nodes[rootId];

  return h(React.Fragment, null,
    h("div", { className: "controls" },
      h("label", null, "component",
        h("select", { value: rootId || "", onChange: (e) => { setSelected(e.target.value); go({ id: e.target.value }); } },
          components.map((n) => h("option", { key: n.id, value: n.id }, n.label)))),
      h("label", null, "depth",
        h("input", { type: "number", min: 0, max: 8, value: depth, onChange: (e) => go({ depth: Math.max(0, Number(e.target.value) || 0) }) })),
      h("label", null, "view",
        h("select", { value: view, onChange: (e) => go({ view: e.target.value }) },
          h("option", { value: "tags" }, "diagram"),
          h("option", { value: "graph" }, "graph"))),
      h("label", null, "node cap",
        h("input", { type: "number", min: 1, max: 200, value: cap, onChange: (e) => go({ cap: Math.max(1, Number(e.target.value) || 1) }) })),
      h("span", { className: "note", "data-query-count": result.order.length, "data-shown-count": shown.length },
        `${shown.length} node${shown.length === 1 ? "" : "s"}, ${edges.length} edge${edges.length === 1 ? "" : "s"} at depth ${depth}`),
      truncated > 0 ? h("span", { className: "warn", "data-truncated": truncated },
        `showing ${shown.length} of the ${result.order.length} the query returned — nearest first; raise the node cap to see the rest`) : null,
      h("span", { className: "note" }, "click a node to select it · double-click to make it the root · drag to pan · wheel to zoom"),
      view === "tags" ? h("span", { className: "note" }, "nearest first; the badge is how many steps from the root") : null,
    ),
    h("div", { className: "page" },
      h("div", { className: "canvas" },
        h(ForceGraph, {
          nodes, edges, shape: view === "graph" ? "radial" : "flow", root: rootId, selected,
          level: (n) => result.distance.get(n.id) || 0,
          onSelect: (id) => setSelected(id),
          // Click-through: a component becomes the root of its own
          // neighbourhood. Anything else (a standard, a missing target) has
          // no neighbourhood to go to and stays selected.
          onActivate: (id) => { setSelected(id); if (index.nodes[id] && index.nodes[id].kind === "component") go({ id }); },
        })),
      h("aside", null,
        selectedNode ? h(NodePanel, { node: selectedNode, index, onNavigate: (id) => { setSelected(id); if (index.nodes[id] && index.nodes[id].kind === "component") go({ id }); } }) : null,
        h("h3", null, "in this view"), h(Counts, { rows: inView, prefix: "view" }),
        h("h3", null, "whole corpus"), h(Counts, { rows: corpus, prefix: "corpus" }),
        h(Legend, null),
      ),
    ),
  );
}
