#!/usr/bin/env node
/* Scene Atlas tests — scripts/test_scene_atlas.js
 * Recomputes the Atlas from its ONLY two allowed sources
 * (data/v1/circle.json + data/v1/scene-figures.json) and pins the
 * figures the page prints: 22 charted, deepest-first order, totals,
 * the honestly-thin split, and the literal-title crossings. Also
 * asserts the shipped page / CSS / JS carry the wiring the Atlas
 * needs. No invented connections pass here: a crossing is an
 * identical track title in two figures' own track lists. */
"use strict";
const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..");

let pass = 0, fail = 0;
function ok(cond, label) {
  if (cond) { pass++; console.log("  ok:", label); }
  else { fail++; console.log("  FAIL:", label); }
}

const circle = JSON.parse(fs.readFileSync(path.join(ROOT, "data/v1/circle.json"), "utf8"));
const scene = JSON.parse(fs.readFileSync(path.join(ROOT, "data/v1/scene-figures.json"), "utf8"));

function normalize() {
  const out = [];
  for (const [k, v] of Object.entries(circle)) {
    const vn = v.verified_notes || {};
    out.push({ id: k, name: v.name, kind: "Title-credited collaborator", role: "collaborator",
      page: v.page, n: v.shared_transmissions, plays: v.shared_plays, years: v.years_active,
      tracks: v.tracks, facts: vn.facts || [], sources: vn.sources || [] });
  }
  for (const [k, v] of Object.entries(scene)) {
    const yrs = v.tracks.map(t => t.date.slice(0, 4)).sort();
    out.push({ id: k, name: v.name, kind: v.kind, role: "scene", page: v.page,
      n: v.tracks.length, plays: v.tracks.reduce((a, t) => a + (t.plays || 0), 0),
      years: yrs[0] + "\u2013" + yrs[yrs.length - 1], tracks: v.tracks,
      facts: v.facts || [], sources: v.sources || [], standing: v.standing || "", watch: v.watch });
  }
  out.sort((a, b) => b.plays - a.plays);
  out.forEach((f, i) => { f.rank = i + 1; });
  return out;
}
const figs = normalize();

ok(Object.keys(circle).length === 21, "circle.json carries exactly 21 collaborators");
ok(Object.keys(scene).length === 1 && scene["fish-narc"], "scene-figures.json carries exactly 1 figure (fish-narc)");
ok(figs.length === 22, "atlas charts exactly 22 figures");
ok(figs[0].id === "yung-vetta" && figs[0].plays === 17893, "deepest sounding is Yung Vetta at 17,893 shared plays");
ok(figs[1].id === "capoxxo" && figs[1].plays === 16174, "second sounding is capoxxo at 16,174");
ok(figs[2].id === "fish-narc" && figs[2].plays === 13677, "scene figure charts third at 13,677 (733 + 12,944 from its two tracks)");
ok(figs.every((f, i) => i === 0 || figs[i - 1].plays >= f.plays), "soundings are in non-increasing shared-plays order");
ok(figs.reduce((a, f) => a + f.plays, 0) === 124690, "charted shared plays total 124,690 across figures");
ok(figs.reduce((a, f) => a + f.n, 0) === 46, "46 shared track entries plotted (44 circle + 2 scene-figure)");
ok(figs.filter(f => f.facts.length > 0).length === 8, "exactly 8 figures carry verified notes");
ok(figs.filter(f => f.facts.length === 0).length === 14, "exactly 14 figures are honestly thin (no verified notes)");
ok(figs.filter(f => f.role === "scene").length === 1, "exactly 1 producer-credit scene figure");
const fish = figs.find(f => f.id === "fish-narc");
ok(fish.watch && fish.watch.status === "announced" && fish.watch.expected === "2026-10-16",
   "fish-narc watch still reads announced / 2026-10-16 (no early flip)");
ok(fish.standing.includes("outside the circle count"), "fish-narc standing keeps him outside the 21 count");
ok(figs.every(f => {
  // rotation 22: figure pages are folds (circle/index.html#c-<slug>);
  // the file must exist and carry the anchor id.
  const [file, frag] = f.page.split("#");
  const p = path.join(ROOT, file);
  if (!fs.existsSync(p)) return false;
  return !frag || fs.readFileSync(p, "utf8").includes(`id="${frag}"`);
}), "every figure's circle page exists on disk");
ok(figs.every(f => f.tracks.every(t => t.title && t.date && t.type)), "every plotted track carries title, date and type");

// crossings: literal normalized-title match across figures
const byTitle = {};
for (const f of figs) for (const t of f.tracks) {
  const key = t.title.toLowerCase().replace(/\s+/g, " ").trim();
  (byTitle[key] = byTitle[key] || new Set()).add(f.id);
}
const crossings = Object.entries(byTitle).filter(([, s]) => s.size > 1).map(([k]) => k);
ok(crossings.length === 5, "exactly 5 literal titles cross between figures");
ok(crossings.some(k => k.includes("night mode")), "NIGHT MODE crossing present (3 figures)");
ok(crossings.filter(k => k.includes("master key")).length === 2, "Master Key crosses in both its carried versions");
ok(crossings.some(k => k.includes("destiny")), "DESTINY crossing present");
ok(crossings.some(k => k.includes("nitemode2019")), "nitemode2019 crossing present");
const nightFigs = byTitle[crossings.find(k => k.includes("night mode"))];
ok(nightFigs.size === 3 && nightFigs.has("max-ferrari") && nightFigs.has("yung-vetta") && nightFigs.has("jax"),
   "NIGHT MODE connects exactly Max Ferrari, Yung Vetta and JAX");

// shipped page wiring
const html = fs.readFileSync(path.join(ROOT, "scene-atlas.html"), "utf8");
const js = fs.readFileSync(path.join(ROOT, "assets/js/scene-atlas.js"), "utf8");
const css = fs.readFileSync(path.join(ROOT, "assets/css/scene-atlas.css"), "utf8");
ok(html.includes('id="atlas-route"') && html.includes('id="atlas-card"'), "page carries the route and the chart card");
ok(html.includes('id="atlas-filters"') && html.includes('data-filter="thin"'), "page carries the record filters incl. honestly-thin");
ok((html.match(/<tr data-fig=/g) || []).length === 22, "static chart log prints all 22 figures with no JS");
ok(html.includes("Yung Vetta") && html.includes("17,893"), "static first sounding is the real figure #1");
ok(html.includes("data/v1/circle.json") && html.includes("data/v1/scene-figures.json"),
   "page states its two-source provenance in print");
ok(html.includes('href="scene-atlas.html" aria-current="page"'), "page's own nav marks Atlas current");
ok(js.includes('fetch("data/v1/circle.json"') && js.includes('fetch("data/v1/scene-figures.json"'),
   "JS fetches exactly the two allowed source files");
ok(!/fetch\("data\/v1\/(?!circle\.json|scene-figures\.json)/.test(js), "JS fetches no other data file");
ok(css.includes(".atlas-route::before") && css.includes("dashed"), "CSS draws the dashed route line");
ok(html.includes("Start charting"), "hero carries its one primary action");

console.log(`\nscene-atlas: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
