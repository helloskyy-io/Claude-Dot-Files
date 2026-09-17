// ForceGraph — the one drawing component both pages use.
//
// Layout is computed HERE, in the browser, from the graph handed in: the
// phase doc's design turns on never storing a drawing. d3-force runs to rest
// synchronously (a few hundred ticks over at most a few dozen nodes is
// milliseconds), so the picture is stable rather than animating into place,
// and a refresh draws the same corpus the same way.
//
// Pan and zoom are ~60 lines of pointer-event handling below rather than
// d3-zoom. The reason is the byte budget: d3-zoom's ES closure (d3-selection,
// d3-drag, d3-transition — 29 files — d3-interpolate, d3-color, d3-ease)
// put the vendored set 11,365 bytes over the 256 KiB budget, and this is the
// verbosity the phase doc chose to pay in view code, where it is visible.
//
// Colour is derived, never authored: every colour comes from the `state` or
// `declares` value the extractor put on the edge or the node, through
// tokens.mjs. Nothing here decides whether a dependency is satisfied.

import React from "../vendor/react@19.0.0/react.mjs";
import {
  forceSimulation, forceLink, forceManyBody, forceCollide, forceRadial, forceY, forceX,
} from "../vendor/d3-force@3.0.0/d3-force.mjs";
import { EDGE_STYLE, NODE_RING, STATUS, surfaces, UI } from "./tokens.mjs";

const h = React.createElement;
const { useEffect, useMemo, useRef, useState } = React;

export const NODE_RADIUS = 14;

// The sprint tag: a rectangle with a point on one end, carrying its label
// INSIDE it. A dot with the text floating beside it reads as a scatter plot;
// a tag reads as a step in a sequence, which is what a sprint item is.
export const TAG = { w: 360, h: 44, point: 14, pitch: 62, gutter: 120 };

// Run the simulation to rest and return {id → {x, y}}. `shape` picks the
// structure that makes the page readable:
//   radial — the root at the centre, each depth on its own ring (Page 2)
//   layered — a directed graph laid out by level, top to bottom
//   flow    — no simulation: the given order, one per row (Page 3)
export function layout(nodes, edges, { shape, level, width, height }) {
  if (nodes.length === 0) return {};
  if (shape === "flow") {
    // NOT a simulation. A sprint states an order and that order is the
    // meaning; physics does not know about it, so running a force here
    // produces a picture that is stable, arbitrary, and unrelated to the
    // document it claims to draw. Row i is item i, as written.
    const x = Math.max(TAG.w / 2 + 20, width / 2 - TAG.gutter / 2);
    const positions = {};
    nodes.forEach((n, i) => {
      positions[n.id] = { x, y: 40 + TAG.h / 2 + i * TAG.pitch };
    });
    return positions;
  }
  const simNodes = nodes.map((n) => ({ id: n.id }));
  const byId = new Map(simNodes.map((n) => [n.id, n]));
  const simLinks = edges
    .filter((e) => byId.has(e.source) && byId.has(e.target))
    .map((e) => ({ source: e.source, target: e.target }));
  const cx = width / 2;
  const cy = height / 2;
  const sim = forceSimulation(simNodes)
    .force("link", forceLink(simLinks).id((d) => d.id).distance(90).strength(0.4))
    .force("charge", forceManyBody().strength(-320))
    .force("collide", forceCollide(NODE_RADIUS * 3))
    .stop();
  if (shape === "radial") {
    // Ring spacing grows with the count on the ring, so a crowded ring is
    // pushed out rather than overlapping.
    const perRing = new Map();
    for (const n of nodes) perRing.set(level(n), (perRing.get(level(n)) || 0) + 1);
    const radius = (n) => {
      const l = level(n);
      if (l === 0) return 0;
      return 110 * l + Math.max(0, (perRing.get(l) || 0) - 6) * 12;
    };
    sim.force("radial", forceRadial((d) => radius(nodes[d.index]), cx, cy).strength(0.9));
  } else {
    // Rows by level; within a row, nodes are spread at a fixed pitch in
    // their given order so labels do not sit on top of one another. The
    // link force then nudges them toward what they connect to.
    const levels = nodes.map(level);
    const rows = Math.max(...levels) + 1;
    const rowGap = Math.min(150, Math.max(90, (height - 80) / Math.max(rows, 1)));
    const top = cy - ((rows - 1) * rowGap) / 2;
    const perRow = new Map();
    const slot = nodes.map((n, i) => {
      const l = levels[i];
      const k = perRow.get(l) || 0;
      perRow.set(l, k + 1);
      return k;
    });
    const pitch = 200;
    sim.force("y", forceY((d) => top + levels[d.index] * rowGap).strength(1.2));
    sim.force("x", forceX((d) => cx + (slot[d.index] - ((perRow.get(levels[d.index]) || 1) - 1) / 2) * pitch).strength(0.5));
  }
  // d3's default alpha schedule: ~300 ticks to alphaMin. Bounded.
  for (let i = 0; i < 300; i += 1) sim.tick();
  const positions = {};
  for (const n of simNodes) positions[n.id] = { x: n.x, y: n.y };
  return positions;
}

function ringFor(node) {
  if (node.kind === "missing") return { colour: STATUS.offline, dash: "5 3", width: 3 };
  if (node.kind !== "component") return { colour: UI.secondary, dash: "", width: 1.5 };
  return NODE_RING[node.declares] || NODE_RING[""];
}

function fillFor(node, S) {
  if (node.kind === "missing") return "transparent";
  if (node.kind === "component") return node.declares === "nothing" ? STATUS.maintenance : UI.primary;
  if (node.kind === "sprint_item") {
    if (!node.linked) return "transparent";
    return node.checked ? STATUS.online : UI.primary;
  }
  return S.panel;
}

function glyphFor(node) {
  if (node.kind === "missing") return "?";
  if (node.kind === "standard") return "§";
  if (node.kind === "artifact") return "◇";
  if (node.kind === "phase") return "φ";
  if (node.kind === "sprint_item") return node.checked ? "✓" : "";
  return "";
}

// Up to three lines of ~24 characters, broken at spaces or slashes; what is
// left after that is elided. A label is a name, and the panel has the rest.
export function wrapLabel(label, width = 24, lines = 3) {
  const words = label.split(/(?<=[ /·])/);
  const out = [];
  let current = "";
  for (const w of words) {
    if ((current + w).trim().length > width && current) {
      out.push(current.trim());
      current = w;
    } else {
      current += w;
    }
  }
  if (current.trim()) out.push(current.trim());
  if (out.length > lines) return [...out.slice(0, lines - 1), `${out[lines - 1].slice(0, width - 1)}…`];
  return out;
}

export function ForceGraph({ nodes, edges, shape, level, selected, onSelect, onActivate, root }) {
  const svgRef = useRef(null);
  const [size, setSize] = useState({ width: 900, height: 600 });
  const [view, setView] = useState({ k: 1, tx: 0, ty: 0 });
  const [dragged, setDragged] = useState({});
  const [panning, setPanning] = useState(false);
  const gesture = useRef(null);

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return undefined;
    const measure = () => setSize({ width: el.clientWidth || 900, height: el.clientHeight || 600 });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const key = useMemo(
    () => `${shape}|${nodes.map((n) => n.id).join(",")}|${edges.map((e) => `${e.source}>${e.target}`).join(",")}`,
    [nodes, edges, shape],
  );
  const positions = useMemo(
    () => layout(nodes, edges, { shape, level, width: size.width, height: size.height }),
    // eslint-disable-next-line react-hooks/exhaustive-deps — `key` stands for nodes+edges
    [key, size.width, size.height],
  );
  useEffect(() => { setDragged({}); setView({ k: 1, tx: 0, ty: 0 }); }, [key]);

  const at = (id) => dragged[id] || positions[id] || { x: 0, y: 0 };
  const toGraph = (clientX, clientY) => {
    const rect = svgRef.current.getBoundingClientRect();
    return { x: (clientX - rect.left - view.tx) / view.k, y: (clientY - rect.top - view.ty) / view.k };
  };

  // Zoom about the cursor: the point under the pointer stays under it.
  // A native listener, because React registers `wheel` as passive and a
  // passive listener cannot preventDefault the page scroll.
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return undefined;
    const onWheel = (event) => {
      event.preventDefault();
      const rect = el.getBoundingClientRect();
      const px = event.clientX - rect.left;
      const py = event.clientY - rect.top;
      const factor = Math.exp(-event.deltaY * 0.0015);
      setView((v) => {
        const k = Math.min(6, Math.max(0.15, v.k * factor));
        const scale = k / v.k;
        return { k, tx: px - (px - v.tx) * scale, ty: py - (py - v.ty) * scale };
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const onPointerDown = (event) => {
    const target = event.target.closest("[data-node]");
    event.currentTarget.setPointerCapture(event.pointerId);
    if (target) {
      const id = target.getAttribute("data-node");
      gesture.current = { kind: "node", id, moved: false, start: toGraph(event.clientX, event.clientY), origin: at(id) };
    } else {
      gesture.current = { kind: "pan", moved: false, startX: event.clientX, startY: event.clientY, origin: view };
      setPanning(true);
    }
  };
  const onPointerMove = (event) => {
    const g = gesture.current;
    if (!g) return;
    if (g.kind === "pan") {
      const dx = event.clientX - g.startX;
      const dy = event.clientY - g.startY;
      if (Math.abs(dx) + Math.abs(dy) > 2) g.moved = true;
      setView({ k: g.origin.k, tx: g.origin.tx + dx, ty: g.origin.ty + dy });
    } else {
      const p = toGraph(event.clientX, event.clientY);
      const dx = p.x - g.start.x;
      const dy = p.y - g.start.y;
      if (Math.abs(dx) + Math.abs(dy) > 1) g.moved = true;
      setDragged((d) => ({ ...d, [g.id]: { x: g.origin.x + dx, y: g.origin.y + dy } }));
    }
  };
  // A double-click is detected here rather than with onDoubleClick: the
  // pointer capture taken on pointerdown retargets the browser's dblclick
  // at the svg, so the node it landed on is only known from the pointer
  // events themselves.
  const lastClick = useRef({ id: null, at: 0 });
  const onPointerUp = (event) => {
    const g = gesture.current;
    gesture.current = null;
    setPanning(false);
    if (!g || g.kind !== "node" || g.moved) return;
    const now = performance.now();
    const twice = lastClick.current.id === g.id && now - lastClick.current.at < 400;
    lastClick.current = { id: g.id, at: twice ? 0 : now };
    if (twice && onActivate) onActivate(g.id, event);
    else if (onSelect) onSelect(g.id, event);
  };

  const nodeById = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  // Read once per render: the themed surfaces come from the stylesheet, so
  // a theme change repaints the SVG on the re-render it already causes.
  const S = surfaces();

  // In flow mode every node is a tag in one column, so a straight line from
  // centre to centre would run THROUGH the labels between them. Each edge
  // leaves the source's point and re-enters the target's point through a
  // gutter to the right, bulging by its own span so two edges over different
  // distances do not trace the same curve.
  const flowEdges = edges
    .filter((e) => nodeById.has(e.source) && nodeById.has(e.target))
    .map((e) => {
      const s = at(e.source);
      const t = at(e.target);
      const sx = s.x + TAG.w / 2;
      const tx = t.x + TAG.w / 2;
      const bulge = 34 + Math.min(120, Math.abs(t.y - s.y) * 0.28);
      const style = EDGE_STYLE[e.state] || EDGE_STYLE.underivable;
      return h("path", {
        key: `${e.source}>${e.target}`,
        d: `M ${sx} ${s.y} C ${sx + bulge} ${s.y}, ${tx + bulge} ${t.y}, ${tx + 5} ${t.y}`,
        // Thinner than the neighbourhood's edges: there the line IS the
        // subject, here it is an annotation over a list the reader is already
        // following. The arrowheads scale with it — SVG sizes a marker in
        // stroke-widths by default — so the head thins with the line.
        fill: "none", stroke: style.colour, strokeWidth: 1.25,
        strokeDasharray: style.dash || undefined,
        markerEnd: `url(#arrow-${e.state || "underivable"})`,
        "data-edge-state": e.state,
      });
    });

  const drawnEdges = shape === "flow" ? flowEdges : edges
    .filter((e) => nodeById.has(e.source) && nodeById.has(e.target))
    .map((e) => {
      const s = at(e.source);
      const t = at(e.target);
      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const len = Math.hypot(dx, dy) || 1;
      // Stop the line at the target's rim so the arrowhead is visible.
      const ex = t.x - (dx / len) * (NODE_RADIUS + 4);
      const ey = t.y - (dy / len) * (NODE_RADIUS + 4);
      const style = EDGE_STYLE[e.state] || EDGE_STYLE.underivable;
      return h("line", {
        key: `${e.source}>${e.target}`,
        x1: s.x, y1: s.y, x2: ex, y2: ey,
        stroke: style.colour, strokeWidth: 2, strokeDasharray: style.dash || undefined,
        markerEnd: `url(#arrow-${e.state || "underivable"})`,
        "data-edge-state": e.state,
      });
    });

  const tagPath = (w, ht) =>
    `M ${-w / 2} ${-ht / 2} H ${w / 2 - TAG.point} L ${w / 2} 0 L ${w / 2 - TAG.point} ${ht / 2} H ${-w / 2} Z`;

  // A tag's OUTLINE carries its state and its fill stays the panel colour, so
  // the label is read against one background everywhere. A solid status fill
  // with text on top has to fight the text for contrast at four different
  // hues, and loses at two of them.
  // A tag's OUTLINE carries its state and its fill stays the panel colour, so
  // the label is read against one background everywhere. A solid status fill
  // with text on top has to fight the text for contrast at four different
  // hues, and loses at two of them.
  //
  // The outline means the same thing as the ring does in the circle drawing —
  // `ringFor` is the one carrier, so a tag and a sphere cannot disagree about
  // a node. Only a sprint item differs, because `checked` is a fact a
  // component does not have.
  const tagStroke = (n) => {
    if (n.kind === "sprint_item") {
      if (!n.linked) return STATUS.offline;
      return n.checked ? STATUS.online : UI.primary;
    }
    return ringFor(n).colour;
  };

  // The right-hand slot says the one thing this drawing would otherwise lose.
  // A sprint board loses nothing by ordering items — the rows ARE the order.
  // A neighbourhood laid out as a list loses its rings, so the distance from
  // the root goes here, and the root says so.
  const tagBadge = (n) => {
    if (n.kind === "sprint_item") return n.checked ? "✓ closed" : "";
    if (n.id === root) return "root";
    if (!level) return "";
    const d = level(n);
    return d ? `${d} away` : "";
  };

  const drawnTags = nodes.map((n) => {
    const p = at(n.id);
    const isSelected = selected === n.id;
    const stroke = tagStroke(n);
    const dashed = n.kind === "missing" || n.linked === false;
    const lines = wrapLabel(n.label, 40, 2);
    const badge = tagBadge(n);
    return h("g", {
      key: n.id, transform: `translate(${p.x},${p.y})`, "data-node": n.id,
      "data-kind": n.kind, "data-checked": n.checked ? "1" : "0", style: { cursor: "pointer" },
    },
      isSelected ? h("path", {
        d: tagPath(TAG.w + 10, TAG.h + 10), fill: "none", stroke: UI.white,
        strokeWidth: 2, opacity: 0.9, style: { pointerEvents: "none" },
      }) : null,
      h("path", {
        d: tagPath(TAG.w, TAG.h), fill: S.panel, stroke,
        strokeWidth: n.id === root ? 3 : 2, strokeDasharray: dashed ? "5 3" : undefined,
      }),
      h("rect", {
        x: -TAG.w / 2 + 1, y: -TAG.h / 2 + 1, width: 5, height: TAG.h - 2,
        fill: stroke, style: { pointerEvents: "none" },
      }),
      h("text", {
        x: -TAG.w / 2 + 16, fill: S.text, fontSize: 12,
        dy: lines.length === 1 ? 4 : -2, style: { pointerEvents: "none" },
      }, lines.map((line, i) => h("tspan", { key: i, x: -TAG.w / 2 + 16, dy: i === 0 ? 0 : 13 }, line))),
      badge ? h("text", {
        x: TAG.w / 2 - TAG.point - 8, dy: 4, textAnchor: "end", fontSize: 11,
        fill: n.checked ? STATUS.online : S.muted, style: { pointerEvents: "none" },
      }, badge) : null,
    );
  });

  const drawnNodes = shape === "flow" ? drawnTags : nodes.map((n) => {
    const p = at(n.id);
    const ring = ringFor(n);
    const isSelected = selected === n.id;
    const isRoot = root === n.id;
    return h("g", {
      key: n.id, transform: `translate(${p.x},${p.y})`, "data-node": n.id,
      "data-kind": n.kind, "data-declares": n.declares || undefined, style: { cursor: "pointer" },
    },
      isSelected ? h("circle", { r: NODE_RADIUS + 7, fill: "none", stroke: UI.white, strokeWidth: 2, opacity: 0.9, style: { pointerEvents: "none" } }) : null,
      h("circle", {
        r: isRoot ? NODE_RADIUS + 3 : NODE_RADIUS, fill: fillFor(n, S),
        stroke: ring.colour, strokeWidth: ring.width, strokeDasharray: ring.dash || undefined,
      }),
      glyphFor(n) ? h("text", { textAnchor: "middle", dy: 5, fill: UI.white, fontSize: 13, style: { pointerEvents: "none" } }, glyphFor(n)) : null,
      h("text", {
        y: NODE_RADIUS + 14, textAnchor: "middle", fill: S.text, fontSize: 11,
        style: { pointerEvents: "none", paintOrder: "stroke", stroke: S.dark, strokeWidth: 3 },
      }, wrapLabel(n.label).map((line, i) => h("tspan", { key: i, x: 0, dy: i === 0 ? 0 : 12 }, line))),
    );
  });

  const markers = Object.entries(EDGE_STYLE).map(([state, style]) =>
    h("marker", {
      key: state, id: `arrow-${state}`, viewBox: "0 0 10 10", refX: 9, refY: 5,
      markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse",
    }, h("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: style.colour })));

  return h("svg", {
    ref: svgRef, className: panning ? "panning" : "", onPointerDown, onPointerMove, onPointerUp,
    onPointerCancel: onPointerUp, "data-node-count": nodes.length, "data-edge-count": drawnEdges.length,
  },
    h("defs", null, markers),
    h("g", { transform: `translate(${view.tx},${view.ty}) scale(${view.k})` }, drawnEdges, drawnNodes),
  );
}
