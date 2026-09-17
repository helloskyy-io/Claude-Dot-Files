// The viewer — fetches one fresh derivation, routes by URL hash, and renders
// the two diagram pages. Written with React.createElement: JSX needs a
// compiler and this repository has none (phase doc § The decision).
//
// Start it:   python3 -m planning_ui serve          (from a checkout of this repo)
// Reach it:   http://127.0.0.1:8765/
// Refresh:    re-derives from the checkout — there is nothing to regenerate.

import React from "../vendor/react@19.0.0/react.mjs";
import { createRoot } from "../vendor/react-dom@19.0.0/client.mjs";
import { NeighbourhoodPage } from "./neighbourhood.mjs";
import { SprintPage } from "./sprint.mjs";
import { SprintOverview } from "./overview.mjs";
import { StoresPage } from "./stores.mjs";

const h = React.createElement;
const { useEffect, useState, useCallback } = React;

const API = "/api/views.json";
const MANIFEST = "/renderers/vendor/manifest.json";

// #/sprint/<sprint name>   ·   #/component/<component id>?depth=2&cap=25
//
// `sprint` is the default page: the front door is where everything stands,
// and a reader descends from there into one component or one sprint.
export function parseRoute(hash) {
  const [path, query = ""] = (hash || "").replace(/^#\/?/, "").split("?");
  const [page, ...rest] = path.split("/");
  const id = rest.length ? decodeURIComponent(rest.join("/")) : "";
  const params = new URLSearchParams(query);
  const num = (k) => (params.has(k) ? Number(params.get(k)) : NaN);
  return {
    page: page || "sprint", id,
    depth: num("depth"), cap: num("cap"),
    view: params.get("view") || "", q: params.get("q") || "",
    store: params.get("store") || "",
  };
}

export function formatRoute(route) {
  const params = new URLSearchParams();
  if (Number.isFinite(route.depth)) params.set("depth", String(route.depth));
  if (Number.isFinite(route.cap)) params.set("cap", String(route.cap));
  // The view is in the ROUTE rather than in storage: which drawing you are
  // looking at is part of what you would send someone, unlike the theme.
  if (route.view) params.set("view", route.view);
  if (route.q) params.set("q", route.q);
  if (route.store) params.set("store", route.store);
  const q = params.toString();
  return `#/${route.page}${route.id ? `/${encodeURIComponent(route.id)}` : ""}${q ? `?${q}` : ""}`;
}

function ErrorBlock({ error }) {
  return h("div", { className: "error", role: "alert" },
    h("h2", null, "the derivation raised — this is the corpus defect, surfaced here rather than in a terminal"),
    h("pre", null, error.traceback || error.error || String(error)),
  );
}

function Footer({ manifest }) {
  if (!manifest) return h("footer", null, "vendored modules: manifest not loaded");
  const over = manifest.total_bytes > manifest.budget_bytes;
  return h("footer", null,
    h("span", { "data-vendored-bytes": manifest.total_bytes },
      `committed third-party bytes: ${manifest.total_bytes.toLocaleString()} of a ${manifest.budget_bytes.toLocaleString()} budget (${over ? "OVER" : "under"} by ${Math.abs(manifest.budget_bytes - manifest.total_bytes).toLocaleString()})`),
    h("details", null, h("summary", null, `${manifest.files.length} files — package, version, integrity`),
      h("table", null, h("tbody", null, manifest.files.map((f) => h("tr", { key: f.file },
        h("td", null, f.package), h("td", null, f.version), h("td", null, f.bytes.toLocaleString()), h("td", null, f.committed_integrity)))))),
    h("span", null, "React 19 via React.createElement · d3-force for layout · pan and zoom in view code · no build step"),
  );
}

function HowTo() {
  return h("div", { className: "howto" },
    h("h2", null, "how this viewer is started and reached"),
    h("pre", null, "cd <a checkout of a planning repo>\npython3 -m planning_ui serve            # http://127.0.0.1:8765/  — ^C stops it\npython3 -m planning_ui serve --repo-root <path>   # from anywhere; refused by name if the path is not a planning repo\npython3 -m planning_ui serve --port 9000 --bind 0.0.0.0   # reachable from another machine — read the caution below"),
    h("p", null, "There is no authentication: bound to 0.0.0.0, anyone who can reach the port reads this checkout's planning corpus and, when a derivation raises, its full traceback. Keep the loopback default unless the network is one you trust."),
    h("p", null, "Every refresh re-runs the extractor over the checkout it sits in. Nothing is regenerated, cached or written; edit a roadmap, refresh, and the change is in the picture. The committed artifacts under development/derived/ are unaffected — regenerate those with python3 -m planning_ui as before."),
    h("p", null, "The graph is the artifact; the drawing is a reading of it. No picture is committed."),
  );
}

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [manifest, setManifest] = useState(null);
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));

  // The theme is a READER's preference about this browser, not a fact about
  // the corpus, so it lives in localStorage and never in the URL or an
  // artifact. Setting the attribute on <html> is what both the stylesheet and
  // tokens.surfaces() read, so the chrome and the SVG change together.
  const [theme, setTheme] = useState(() => {
    try { return window.localStorage.getItem("planning_ui.theme") || "slate"; } catch { return "slate"; }
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { window.localStorage.setItem("planning_ui.theme", theme); } catch { /* private mode: the theme is simply not remembered */ }
  }, [theme]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch(API, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok || !payload.ok) { setError(payload); setData(null); return; }
      setData(payload);
    } catch (exc) {
      setError({ error: `the viewer could not fetch ${API}: ${exc}` });
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    fetch(MANIFEST, { cache: "no-store" }).then((r) => r.json()).then(setManifest).catch(() => setManifest(null));
  }, []);
  useEffect(() => {
    const onHash = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = (next) => { window.location.hash = formatRoute(next); };
  const nav = (page, label) => h("a", { href: formatRoute({ page }), className: route.page === page ? "active" : "" }, label);

  let body;
  if (error) body = h(ErrorBlock, { error });
  else if (!data) body = h("p", { className: "loading" }, "deriving from the checkout…");
  else if (route.page === "component") body = h(NeighbourhoodPage, { views: data.views, route, navigate });
  else if (route.page === "issues") body = h(StoresPage, { route, navigate });
  else if (route.page === "howto") body = h(HowTo, null);
  else if (route.id) body = h(SprintPage, { views: data.views, route, navigate });
  else body = h(SprintOverview, { views: data.views, navigate });

  const prov = data ? data.views.provenance : null;
  return h(React.Fragment, null,
    h("header", { className: "top" },
      h("h1", null, data ? `planning-ui · ${data.repo}` : "planning-ui"),
      h("nav", null, nav("sprint", "Sprint"), nav("component", "Component"), nav("issues", "Issues"), nav("howto", "How to start")),
      h("label", { className: "theme" }, "theme",
        h("select", {
          value: theme, onChange: (e) => setTheme(e.target.value),
          title: "surfaces only — the status colours are Design System §1.2 and do not change",
        },
          h("option", { value: "slate" }, "slate"),
          h("option", { value: "contrast" }, "high contrast"))),
      h("button", { onClick: load, title: "re-derive now (a browser refresh does the same)" }, "re-derive"),
      data ? h("span", { className: "stamp", "data-derived-at": data.derived_at },
        `derived ${data.derived_at} in ${data.derive_ms} ms · commit ${prov.commit.slice(0, 10)} · ${prov.input_count} inputs · ${data.counts.findings} findings`) : null,
    ),
    body,
    h(Footer, { manifest }),
  );
}

createRoot(document.getElementById("root")).render(h(App));
