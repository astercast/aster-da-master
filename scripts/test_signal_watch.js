/* scripts/test_signal_watch.js — pinned checks for lib/signal-watch.js.
 * Fixtures prove the rules; the real-capture block proves them against the
 * archive's own two 2026-10-11 captures (artist.json vs the Signal stand-up
 * snapshot), where the known truth is: 185 tracks both sides, zero new
 * uploads (three titles differ only by apostrophe/space style), exactly two
 * +1 movers, zero crossings.
 * Run: node scripts/test_signal_watch.js  (exit 1 on any failure)
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { diffCaptures, normTitle } = require("../lib/signal-watch");

const ROOT = path.join(__dirname, "..");
let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name); }
}

console.log("== signal-watch: fixtures");
check("apostrophe styles normalize together",
  normTitle("life’s made") === normTitle("life's made"));
check("whitespace collapses",
  normTitle("prod.  okthxbb") === normTitle("prod. okthxbb"));

const prev = {
  captured_at: "2026-10-01T00:00:00Z",
  tracks: [
    { title: "life’s made prod wellfed", upload_date: "2026-03-17", plays: 150 },
    { title: "Climber", upload_date: "2025-01-01", plays: 990 },
    { title: "Flat", upload_date: "2025-01-01", plays: 42 },
    { title: "Gone", upload_date: "2024-01-01", plays: 7 },
  ],
};
const curr = {
  captured_at: "2026-10-03T00:00:00Z",
  tracks: [
    { title: "life's made prod wellfed", upload_date: "2026-03-17", plays: 158 },
    { title: "Climber", upload_date: "2025-01-01", plays: 1005 },
    { title: "Flat", upload_date: "2025-01-01", plays: 42 },
    { title: "Brand New", upload_date: "2026-10-02", plays: 12 },
  ],
};
const d = diffCaptures(prev, curr);
check("apostrophe variant is not a new upload", d.new_uploads.length === 1 && d.new_uploads[0].title === "Brand New");
check("removal detected", d.removed.length === 1 && d.removed[0].title === "Gone");
check("movers exclude flat tracks", d.movers.length === 2);
check("per_day over a 2-day gap", d.movers.find((m) => m.title === "Climber").per_day === 7.5);
check("crossing at 1000 recorded", d.crossings.length === 1 && d.crossings[0].threshold === 1000);
check("total_delta sums movers", d.total_delta === 23);

const sameDay = diffCaptures(
  { captured_at: "2026-10-03T00:00:00Z", tracks: curr.tracks },
  { captured_at: "2026-10-03T06:00:00Z", tracks: curr.tracks.map((t) => ({ ...t, plays: t.plays + 3 })) }
);
check("same-day gap yields per_day null, never an invented rate",
  sameDay.movers.length === 4 && sameDay.movers.every((m) => m.per_day === null));

console.log("== signal-watch: the real 2026-10-11 capture pair");
const artist = JSON.parse(fs.readFileSync(path.join(ROOT, "data/v1/artist.json"), "utf8"));
const snap = JSON.parse(fs.readFileSync(path.join(ROOT, "data/playcounts.snapshot.json"), "utf8"));
const prevReal = {
  captured_at: "2026-10-11",
  tracks: artist.discography
    .filter((e) => e.type === "SoundCloud-only" && Number.isInteger(e.plays))
    .map((e) => ({ title: e.title, upload_date: e.date, plays: e.plays })),
};
const currReal = { captured_at: snap.snapshot_at, tracks: snap.tracks };
const r = diffCaptures(prevReal, currReal);
check("185 tracks watched", r.tracks_watched === 185);
check("vault titles unique after normalization",
  new Set(prevReal.tracks.map((t) => normTitle(t.title))).size === 185);
check("zero false new uploads from title-style drift", r.new_uploads.length === 0);
check("zero removals", r.removed.length === 0);
check("exactly the two known +1 movers", r.movers.length === 2 && r.movers.every((m) => m.delta === 1));
check("movers are candy + Take Me",
  r.movers.map((m) => m.title).sort().join("|") ===
  ["Take Me (prod. Em Klebold)", "candy w/ capoxxo(prod. razorwrist)"].sort().join("|"));
check("no crossings between the captures", r.crossings.length === 0);
check("total plays match the snapshot file", r.total_plays === 257396);

console.log("\npass=" + pass + " fail=" + fail);
process.exit(fail ? 1 : 0);
