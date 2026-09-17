// Page 1 — every sprint in `sprints.md`, in the order the file states them.
//
// The front door. A reader arrives asking "where is everything?", and
// descends from a row here into that sprint's board.
//
// ORDER IS FILE ORDER, not alphabetical. `views.sprints` is a mapping and
// arrives sorted by name; a page whose subject is a document must present the
// document's own sequence, so every row is placed by the line it was read
// from. This is the same rule the sprint board follows.
//
// HOURS ARE REPORTED AS KNOWN-AND-UNKNOWN, never as one number. An item with
// no `~Nh` figure contributes nothing to a sum, so a sprint whose open items
// carry no figures reads "0h to go" and looks finished. `Foundations 3` is
// exactly that case today: one item open, no hours on it. The count of
// figureless items rides beside every total so the total cannot mislead.

import React from "../vendor/react@19.0.0/react.mjs";

const h = React.createElement;

// The close-out item is a standing per-sprint gate, not sprint content — the
// sprint file says so and does not size it. Counting it would put a
// permanently-open item in every sprint's denominator.
const isWork = (item) => !item.close_out;

export function summarise(board) {
  const items = board.items.filter(isWork);
  const done = items.filter((i) => i.checked);
  const open = items.filter((i) => !i.checked);
  const hours = (list) => list.reduce((total, i) => total + (i.hours_low || 0), 0);
  return {
    name: board.name,
    line: board.line,
    marker: board.marker || "",
    items: items.length,
    done: done.length,
    openCount: open.length,
    hoursTotal: hours(items),
    hoursLeft: hours(open),
    openWithoutHours: open.filter((i) => i.hours_low == null).length,
    itemsWithoutHours: items.filter((i) => i.hours_low == null).length,
    unlinked: items.filter((i) => !i.linked).length,
    closeOut: board.items.some((i) => i.close_out),
  };
}

const MARKER_CLASS = {
  "COMPLETE": "done",
  "IN PROGRESS": "active",
  "PLANNED": "planned",
  "NOT SCHEDULED": "unscheduled",
};

function SprintRow({ s, onOpen }) {
  const pct = s.items ? Math.round((s.done / s.items) * 100) : 0;
  const cls = MARKER_CLASS[s.marker] || "planned";
  // A sprint every item of which is checked, still marked otherwise, is the
  // disagreement the consistency report names; the row shows both rather than
  // choosing one.
  const disagrees = s.items > 0 && s.done === s.items && s.marker && s.marker !== "COMPLETE";
  return h("li", { className: `sprint-row ${cls}`, onClick: () => onOpen(s.name), "data-sprint": s.name },
    h("div", { className: "sr-head" },
      h("span", { className: `sr-marker ${cls}` }, s.marker || "no marker"),
      h("span", { className: "sr-name" }, s.name),
      h("span", { className: "sr-line mono" }, `sprints.md:${s.line}`),
    ),
    h("div", { className: "sr-bar", title: `${s.done} of ${s.items} items checked` },
      h("div", { className: `sr-fill ${cls}`, style: { width: `${pct}%` } })),
    h("div", { className: "sr-facts" },
      h("span", null, h("b", null, `${s.done}/${s.items}`), " items"),
      h("span", null, h("b", null, `~${s.hoursLeft}h`), " to go",
        s.openWithoutHours
          ? h("span", { className: "sr-warn" }, ` + ${s.openWithoutHours} open with no figure`)
          : null),
      h("span", { className: "muted" }, `~${s.hoursTotal}h sized`),
      s.unlinked ? h("span", { className: "sr-warn" }, `${s.unlinked} linking nothing`) : null,
      disagrees ? h("span", { className: "sr-warn" }, `every item checked, marked ${s.marker}`) : null,
    ),
  );
}

export function SprintOverview({ views, navigate }) {
  const boards = Object.values(views.sprints)
    .map(summarise)
    .sort((a, b) => a.line - b.line);
  const open = (name) => navigate({ page: "sprint", id: name });

  const totals = boards.reduce((acc, s) => ({
    items: acc.items + s.items,
    done: acc.done + s.done,
    hoursLeft: acc.hoursLeft + s.hoursLeft,
    noFigure: acc.noFigure + s.openWithoutHours,
  }), { items: 0, done: 0, hoursLeft: 0, noFigure: 0 });

  return h(React.Fragment, null,
    h("div", { className: "controls" },
      h("span", { className: "note mono" }, `development/sprints.md · ${boards.length} sprints`),
      h("span", { className: "note" },
        `${totals.done} of ${totals.items} work items closed · ~${totals.hoursLeft}h remaining across ${totals.noFigure ? `${totals.items - totals.done - totals.noFigure} sized open items` : "all open items"}`),
      totals.noFigure
        ? h("span", { className: "warn" }, `${totals.noFigure} open items carry no hour figure and are in no total`)
        : null,
      h("span", { className: "note" }, "click a sprint to open its board"),
    ),
    h("div", { className: "overview" },
      h("ol", { className: "sprint-rows", "data-sprint-count": boards.length },
        boards.map((s) => h(SprintRow, { key: s.name, s, onOpen: open }))),
    ),
  );
}
