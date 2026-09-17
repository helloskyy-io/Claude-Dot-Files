// Page — the four tracked stores and the Unplaced list: what owes a ruling.
//
// FETCHED ONLY WHEN THIS PAGE IS OPENED. The store rows are ~400 and no other
// page draws them, so the viewer's first paint must not wait on a derivation
// it will not use. That is why they are a second artifact and a second route
// rather than a key in the views payload.
//
// Every row carries the file and line it was read from, because a row a
// reader cannot act on without going looking is a number rather than a
// worklist — the bar every other finding in this component is held to.
//
// NOTHING HERE RULES ANYTHING. The page reports what owes a ruling;
// `triage-candidates` and the operator rule, and the generator holds no write
// path to any store — `tracked/operations/` is human-only.

import React from "../vendor/react@19.0.0/react.mjs";

const h = React.createElement;
const { useEffect, useState, useMemo } = React;

const API = "/api/stores.json";

function Table({ table, filter }) {
  // Sorting is local state, not route state: the filter says WHAT you are
  // looking at and is worth sending someone; the column order says how you
  // happened to arrange it.
  const [sort, setSort] = useState({ key: "", desc: false });

  const rows = useMemo(() => {
    const needle = filter.toLowerCase();
    const matched = !filter ? table.rows : table.rows.filter((r) =>
      Object.values(r.cells).some((v) => String(v).toLowerCase().includes(needle))
      || r.file.toLowerCase().includes(needle));
    if (!sort.key) return matched;
    // Numeric where both sides are numbers — `count` and the age columns sort
    // as quantities, not as strings, or 10 lands between 1 and 2.
    const value = (r) => (r.cells[sort.key] ?? "");
    const sorted = [...matched].sort((a, b) => {
      const x = value(a);
      const y = value(b);
      const nx = Number(String(x).replace(/[^0-9.-]/g, ""));
      const ny = Number(String(y).replace(/[^0-9.-]/g, ""));
      const both = String(x).trim() !== "" && String(y).trim() !== ""
        && Number.isFinite(nx) && Number.isFinite(ny);
      const cmp = both ? nx - ny : String(x).localeCompare(String(y));
      return sort.desc ? -cmp : cmp;
    });
    return sorted;
  }, [table, filter, sort]);

  const pick = (key) => setSort((s) => ({ key, desc: s.key === key ? !s.desc : true }));

  return h("section", { className: "store", "data-store": table.key },
    h("h2", null, table.title),
    h("p", { className: "store-meta" },
      h("span", { className: "mono" }, table.source),
      h("span", null, `${rows.length} of ${table.rows.length} row${table.rows.length === 1 ? "" : "s"}`),
      // `scanned` and `suppressed` ride beside the count: a table that shows
      // fewer rows than it read must say so, or the shorter table reads as a
      // smaller problem.
      table.scanned ? h("span", null, `${table.scanned} read`) : null,
      table.suppressed ? h("span", { className: "sr-warn" }, `${table.suppressed} owing nothing, not listed`) : null),
    table.owes_definition ? h("p", { className: "store-owes" }, table.owes_definition) : null,
    rows.length
      ? h("div", { className: "store-scroll" },
        h("table", null,
          h("thead", null, h("tr", null,
            table.columns.map((c) => h("th", {
              key: c.key,
              className: `${c.derived ? "derived" : ""} sortable ${sort.key === c.key ? "sorted" : ""}`,
              onClick: () => pick(c.key),
              title: "sort by this column",
            }, c.label, sort.key === c.key ? h("span", { className: "arrow" }, sort.desc ? " ▾" : " ▴") : null)),
            h("th", null, "read from"))),
          h("tbody", null, rows.map((r, i) => h("tr", { key: `${r.file}:${r.line}:${i}` },
            table.columns.map((c) => h("td", { key: c.key }, r.cells[c.key] || "")),
            h("td", { className: "mono muted" }, `${r.file}:${r.line}`))))))
      : h("p", { className: "muted" }, filter ? "nothing matches that filter" : "nothing owes a ruling here"),
    (table.notes || []).map((n, i) => h("p", { key: i, className: "store-note muted" }, n)),
  );
}

// The readings are not a sixth store — they are what the stores say when read
// ACROSS each other: what is queued for triage, what is due to be pruned,
// whether the exit test is met, whether the stores conform. They earn their
// own tab rather than a run-on at the bottom of the last table.
const READINGS = "readings";

function SubTabs({ tables, active, onPick }) {
  return h("div", { className: "subtabs", role: "tablist" },
    tables.map((t) => h("button", {
      key: t.key, role: "tab", "aria-selected": t.key === active,
      className: `subtab ${t.key === active ? "active" : ""}`,
      onClick: () => onPick(t.key),
    },
      h("span", null, t.short),
      // The count rides ON the tab: tabbing costs the at-a-glance view the
      // one-page version had, and the count is what that view was for.
      h("span", { className: `subtab-count ${t.rows.length ? "" : "zero"}` }, t.rows.length))),
  );
}

export function StoresPage({ route, navigate }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const filter = route.q || "";

  useEffect(() => {
    let live = true;
    fetch(API, { cache: "no-store" })
      .then((r) => r.json())
      .then((payload) => {
        if (!live) return;
        if (!payload.ok) { setError(payload); return; }
        setData(payload);
      })
      .catch((exc) => live && setError({ error: `could not fetch ${API}: ${exc}` }));
    return () => { live = false; };
  }, []);

  if (error) {
    return h("div", { className: "error", role: "alert" },
      h("h2", null, "the stores could not be derived"),
      h("pre", null, error.traceback || error.error));
  }
  if (!data) return h("p", { className: "loading" }, "reading the four stores…");

  const stores = data.stores;
  const tabs = stores.tables.map((t) => ({ ...t, short: t.key }));
  const readings = {
    key: READINGS, short: "readings",
    rows: stores.crossings.reduce((n, t) => n.concat(t.rows), []),
  };
  const all = [...tabs, readings];
  const active = all.some((t) => t.key === route.store) ? route.store : all[0].key;
  const pick = (store) => navigate({ page: "issues", store, q: filter });
  const owing = stores.tables.reduce((n, t) => n + t.rows.length, 0);
  const showing = active === READINGS ? stores.crossings : [stores.tables.find((t) => t.key === active)];

  return h(React.Fragment, null,
    h("div", { className: "controls" },
      h("label", null, "filter",
        h("input", {
          type: "search", value: filter, placeholder: "id, title, component, file…",
          // Filter and tab both ride in the route, so a view of one store
          // filtered to one component is a link.
          onChange: (e) => navigate({ page: "issues", store: active, q: e.target.value }),
        })),
      h("span", { className: "note" }, `${owing} item${owing === 1 ? "" : "s"} owe a ruling across the stores`),
      h("span", { className: "note mono" }, `derived in ${data.derive_ms} ms`),
      h("span", { className: "note" }, "this page reports; it rules nothing and writes nothing"),
    ),
    h(SubTabs, { tables: all, active, onPick: pick }),
    h("div", { className: "stores" }, showing.map((t) => h(Table, { key: t.key, table: t, filter }))),
  );
}
