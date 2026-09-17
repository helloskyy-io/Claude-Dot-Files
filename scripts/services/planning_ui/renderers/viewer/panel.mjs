// Small pieces both pages share: the legend, a state badge, a counts grid.
import React from "../vendor/react@19.0.0/react.mjs";
import { EDGE_STYLE, NODE_RING, STATE_LABEL, STATUS } from "./tokens.mjs";

const h = React.createElement;

export function StateBadge({ state }) {
  return h("span", { className: `badge state-${state || "none"}`, title: STATE_LABEL[state] || "" }, state || "—");
}

export function Counts({ rows, prefix }) {
  return h("div", { className: "counts" }, Object.entries(rows).flatMap(([label, value]) => [
    h("b", { key: `${label}-v`, "data-count": `${prefix}:${label}` }, String(value)),
    h("span", { key: `${label}-l` }, label),
  ]));
}

export function Legend() {
  return h("div", null,
    h("h3", null, "legend — three states a reader must not confuse"),
    h("ul", null,
      h("li", null, h("span", { className: "ring nothing" }), "a component that declares nothing — a worklist entry (status-maintenance)"),
      h("li", null, h("span", { className: "swatch", style: { borderColor: EDGE_STYLE.broken.colour, borderTopStyle: "dotted" } }), "a broken edge — the target resolves to no node; a defect in the corpus (status-offline)"),
      h("li", null, h("span", { className: "swatch", style: { borderColor: EDGE_STYLE.unsatisfied.colour, borderTopStyle: "dashed" } }), "an unsatisfied edge — the target is work not yet done (status-warning)"),
    ),
    h("h3", null, "and the rest"),
    h("ul", null,
      h("li", null, h("span", { className: "swatch", style: { borderColor: EDGE_STYLE.satisfied.colour } }), "a satisfied edge — the target is finished (status-online)"),
      h("li", null, h("span", { className: "swatch", style: { borderColor: EDGE_STYLE.underivable.colour, borderTopStyle: "dotted" } }), "an underivable edge — the extractor refused to guess (ui-secondary)"),
      h("li", null, h("span", { className: "ring", style: { borderColor: NODE_RING["prose-only"].colour } }), "a component declaring in prose only — also a worklist entry"),
      h("li", null, h("span", { className: "ring missing" }), "a node that is not there — what a broken edge points at"),
      h("li", null, "§ a standard · ◇ an artifact · φ a phase no roadmap owns"),
    ),
  );
}

export { STATUS };
