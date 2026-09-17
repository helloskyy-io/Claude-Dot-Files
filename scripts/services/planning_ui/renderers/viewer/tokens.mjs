// Design System Standard §1 tokens, as the viewer uses them.
//
// Requirement 4: the three states a reader must not confuse use the
// platform's EXISTING status colours, so a colour means the same thing here
// as on the Admin UI. Values are copied from
// standards/django/design_system_standard.md §1.2 and §1.3, never invented;
// the standard says the shades are to be tuned once there is a page to look
// at, and that page is this one.

export const STATUS = {
  online: "#10b981",       // status-online — healthy, running
  offline: "#ef4444",      // status-offline — down, broken
  warning: "#f59e0b",      // status-warning — degraded, needs attention
  maintenance: "#8b5cf6",  // status-maintenance — planned, not yet there
};

export const UI = {
  primary: "#0ea5e9",
  secondary: "#64748b",
  dark: "#0f172a",
  white: "#ffffff",
};

// The dark-theme shades the standard does not codify — its stated exception.
//
// STYLES.CSS IS THE CARRIER AND THIS READS IT. These four were written out
// twice — once as custom properties, once as constants here — and kept in
// step by hand, which is the same two-carriers-for-one-fact defect the
// consistency report exists to name. `surfaces()` reads the computed
// properties off the document, so a theme that changes them changes the SVG
// and the chrome together and cannot half-apply.
//
// The values below are the FALLBACK, for `node --test`, where there is no
// document to read. They are the light-on-slate theme's values.
const FALLBACK = {
  panel: "#1e293b",   // local — slate-800
  line: "#334155",    // local — slate-700
  text: "#e2e8f0",    // local — slate-200
  muted: "#94a3b8",   // local — slate-400
  dark: "#0f172a",    // ui-dark, themed with the rest
};

export function surfaces() {
  if (typeof document === "undefined") return FALLBACK;
  const css = getComputedStyle(document.documentElement);
  const read = (name, fallback) => css.getPropertyValue(name).trim() || fallback;
  return {
    panel: read("--panel", FALLBACK.panel),
    line: read("--line", FALLBACK.line),
    text: read("--text", FALLBACK.text),
    muted: read("--muted", FALLBACK.muted),
    dark: read("--ui-dark", FALLBACK.dark),
  };
}

// An edge's state → colour and dash. Colour and dash are BOTH varied so the
// four states stay apart for a reader who cannot tell red from green.
//   satisfied    the target is finished                 status-online
//   unsatisfied  the target is work not yet done        status-warning
//   broken       the target names nothing (a defect)    status-offline
//   underivable  the extractor refused to guess         ui-secondary
export const EDGE_STYLE = {
  satisfied:   { colour: STATUS.online,    dash: "" },
  unsatisfied: { colour: STATUS.warning,   dash: "8 4" },
  broken:      { colour: STATUS.offline,   dash: "3 3" },
  underivable: { colour: UI.secondary,     dash: "2 5" },
};

// A component node's declaration state → how its ring is drawn.
//   nothing     no `**Depends on:**` line a parser can read — a worklist
//               entry, neither a defect nor undone work   status-maintenance
//   prose-only  declares, but in prose the parser cannot bind
export const NODE_RING = {
  nothing:      { colour: STATUS.maintenance, dash: "6 3", width: 4 },
  "prose-only": { colour: STATUS.maintenance, dash: "", width: 3 },
  resolves:     { colour: UI.primary, dash: "", width: 1.5 },
  excepted:     { colour: UI.secondary, dash: "", width: 1.5 },
  "":           { colour: UI.secondary, dash: "", width: 1.5 },
};

export const STATE_LABEL = {
  satisfied: "satisfied — the target is finished",
  unsatisfied: "unsatisfied — the target is work not yet done",
  broken: "broken — the target resolves to no node (a defect in the corpus)",
  underivable: "underivable — the target's satisfaction is not defined by rule 9",
};
