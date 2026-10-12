/* Wave 17 proof: executes the 3 AGENT.md example workflows against the real
   local api/v1 JSON files and asserts each step returns real data.
   Run: node scripts/verify_agent_workflows.js (from the repo root). */
"use strict";
const fs = require("fs");
const path = require("path");

const API = path.join(__dirname, "..", "api", "v1");
const J = (p) => JSON.parse(fs.readFileSync(path.join(API, p), "utf8"));

let failures = 0;
function check(name, cond, detail) {
  if (cond) { console.log(`  ok: ${name}${detail ? " — " + detail : ""}`); }
  else { console.log(`  FAIL: ${name}${detail ? " — " + detail : ""}`); failures++; }
}

// --- Workflow 1: brief me on the SomeLowLifes era ---
console.log("[workflow 1] SomeLowLifes era brief");
{
  const tr = J("transmission.json");
  const era = tr.eras.find((e) => e.name === "The SomeLowLifes Era");
  check("era found", !!era);
  check("era span 2023-2024", era && era.span === "2023 – 2024", era && era.span);
  check("58 transmissions", era && era.transmissions === 58, String(era && era.transmissions));
  check("14,982 plays", era && era.plays === 14982, String(era && era.plays));
  check("signal mentions 553-day silence", era && /553-day silence/.test(era.signal));
  const ms = J("milestones.json");
  const silence = ms.milestones.find((m) => m.id === "longest-silence");
  check("longest-silence 553d 2022-02-22→2023-08-29",
    silence && silence.days === 553 && silence.from === "2022-02-22" && silence.to === "2023-08-29");
  check("era collaborators present", era && era.collaborators.length === 3,
    (era && era.collaborators.map((c) => c.name).join(", ")) || "");
  const yrs = J("years.json");
  check("2023+2024 vault = 26+20", yrs["2023"].vault === 26 && yrs["2024"].vault === 20);
}

// --- Workflow 2: 10 quietest deep cuts ---
console.log("[workflow 2] 10 quietest deep cuts");
{
  const artist = J("artist.json");
  const vault = artist.discography
    .filter((e) => e.type === "SoundCloud-only" && Number.isInteger(e.plays))
    .sort((a, b) => a.plays - b.plays);
  check("185 vault tracks with play counts", vault.length === 185, String(vault.length));
  const bottom10 = vault.slice(0, 10);
  check("quietest is nitemode2019 @ 17 plays",
    bottom10[0].plays === 17 && /nitemode2019/.test(bottom10[0].title),
    `${bottom10[0].plays} — ${bottom10[0].title}`);
  check("10th is 104 plays", bottom10[9].plays === 104, String(bottom10[9].plays));
  check("all 10 have dates and are non-increasing",
    bottom10.every((e) => e.date) && bottom10.every((e, i) => i === 0 || e.plays >= bottom10[i - 1].plays));
  const codex = J("codex.json");
  check("codex has 16 families", codex.families.length === 16, String(codex.families.length));
}

// --- Workflow 3: trace every Max Ferrari collaboration ---
console.log("[workflow 3] Max Ferrari collab trace");
{
  const circle = J("circle.json");
  const mf = circle["max-ferrari"];
  check("circle entry found", !!mf);
  check("8 shared transmissions", mf && mf.shared_transmissions === 8, String(mf && mf.shared_transmissions));
  check("13,618 shared plays", mf && mf.shared_plays === 13618, String(mf && mf.shared_plays));
  check("years_active 2018–2025", mf && mf.years_active === "2018–2025", mf && mf.years_active);
  check("8 tracks listed", mf && mf.tracks.length === 8, String(mf && mf.tracks.length));
  const nw = J("network.json");
  check("insight: most frequent = Max Ferrari x8",
    nw.insights.most_frequent_collaborator.name === "Max Ferrari" &&
    nw.insights.most_frequent_collaborator.track_count === 8);
  const cc = nw.edges.filter((e) => e.kind === "co-credit" &&
    (e.a === "max-ferrari" || e.b === "max-ferrari"));
  check("2 co-credit edges", cc.length === 2, cc.map((e) => `${e.a}<->${e.b} w${e.weight}`).join("; "));
  const jax = cc.find((e) => e.a === "jax" || e.b === "jax");
  check("jax edge weight 2 with shared_tracks", jax && jax.weight === 2 &&
    jax.shared_tracks.length === 2, jax && jax.shared_tracks.join(" | "));
  check("max/vetty are separate slugs; Max+Vetty track is NOT in max-ferrari",
    !!circle["max"] && !!circle["vetty"] &&
    !mf.tracks.some((t) => /Max\+Vetty/.test(t.title)));
}

// --- Workflow 4: deep-dive one era (eras.json) ---
console.log("[workflow 4] SomeLowLifes era deep dive");
{
  const er = J("eras.json");
  check("6 eras", er.eras.length === 6, String(er.eras.length));
  const e = er.eras.find((x) => x.id === "the-somelowlifes-era");
  check("era found", !!e);
  check("58 transmissions / 14,982 plays", e && e.transmissions === 58 && e.plays === 14982,
    e && `${e.transmissions} tx / ${e.plays} plays`);
  check("rank #2 by tx and by plays", e && e.summary.rank_by_transmissions === 2 &&
    e.summary.rank_by_plays === 2, e && JSON.stringify({ t: e.summary.rank_by_transmissions, p: e.summary.rank_by_plays }));
  check("archive share 5.82%", e && e.summary.archive_plays_share === 0.0582,
    e && String(e.summary.archive_plays_share));
  check("busiest year 2023 (31 tx / 10,179 plays)",
    e && e.summary.busiest_year.year === "2023" &&
    e.summary.busiest_year.transmissions === 31 && e.summary.busiest_year.plays === 10179);
  check("loudest = Clock In The Benz (725 plays)",
    e && e.summary.loudest_transmission.plays === 725 &&
    /Clock In The Benz/.test(e.summary.loudest_transmission.title));
  check("deepest cut = nitemode2019 (17 plays)",
    e && e.summary.deepest_cut.plays === 17 && /nitemode2019/.test(e.summary.deepest_cut.title));
  check("top family = The Rites (7 tx / 2,243 plays)",
    e && e.summary.top_family.name === "The Rites" &&
    e.summary.top_family.transmissions === 7 && e.summary.top_family.plays === 2243);
  check("5 collaborators / 8.5% collab share", e && e.summary.collaborators_count === 5 &&
    e.summary.collab_plays_share === 0.085);
  check("3 milestones", e && e.summary.milestones_count === 3);
  check("full track list = 58 entries", e && e.tracks.length === 58, e && String(e.tracks.length));
  check("more collaborators than transmission.json top-3",
    e && e.collaborators.length === 5,
    e && e.collaborators.map((c) => c.name).join(", "));
  check("deep_dive + journey links", e && e.deep_dive === "eras/the-somelowlifes-era.html" &&
    e.journey === "transmission.html#era-the-somelowlifes-era");
}

console.log(failures === 0 ? "\nALL 4 WORKFLOWS PROVE OUT" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
