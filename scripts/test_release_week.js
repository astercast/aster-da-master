/* scripts/test_release_week.js — pinned checks for the Release Week package.
 *
 * Data checks: data/release-week-uncle.json must agree with the two sources
 * it mirrors — data/v1/live-dates.json (event ids, statuses, the two
 * unconfirmed leads) and data/v1/scene-figures.json (the watch it flips) —
 * and the post-release flip must still be armed with an honestly empty
 * first-capture slot. When the post-Oct 16 pass flips release.status to
 * "released", the announced-state checks below are expected to invert in
 * that same commit.
 *
 * Behavior checks: assets/js/release-week.js runs in a DOM shim — the
 * countdown chips paint from their own dates, an "announced" release file
 * never flips the page, and a "released" file flips the state line, the
 * release chip and the capture slot.
 *
 * Run: node scripts/test_release_week.js  (exit 1 on any failure)
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..");
const J = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name); }
}

console.log("== release-week: data file vs its sources");
const rw = J("data/release-week-uncle.json");
const dates = J("data/v1/live-dates.json");
const figures = J("data/v1/scene-figures.json");

check("version matches the archive (0.19.0)", rw.version === "0.19.0" && dates.version === "0.19.0");
check("subject is the K Records LP", rw.subject.artist === "Fish Narc" && rw.subject.catalog === "KLP313" && rw.subject.tracks === 11);
check("release still announced, nothing confirmed early",
  rw.release.status === "announced" && rw.release.expected === "2026-10-16" &&
  rw.release.confirmed_at === null && rw.release.confirmed_by === null);
check("scene-figures watch agrees (announced, same date)",
  figures["fish-narc"].watch.status === rw.release.status && figures["fish-narc"].watch.expected === rw.release.expected);

const rwEvents = Object.fromEntries(rw.events.map((e) => [e.id, e]));
const ldEvents = Object.fromEntries(dates.events.map((e) => [e.id, e]));
for (const id of ["fish-narc-uncle-listening-party", "fish-narc-uncle-release"]) {
  check("event carried + verified: " + id,
    !!rwEvents[id] && !!ldEvents[id] && rwEvents[id].status === "verified" &&
    rwEvents[id].date === ldEvents[id].date && rwEvents[id].venue === ldEvents[id].venue);
}
check("party facts match the sweep (Thu Oct 15, 7:00 PM PDT, free/RSVP)",
  rwEvents["fish-narc-uncle-listening-party"].weekday === "Thursday" &&
  rwEvents["fish-narc-uncle-listening-party"].time === "7:00 PM PDT" &&
  rwEvents["fish-narc-uncle-listening-party"].price === "Free, RSVP");

const rwUnc = rw.unconfirmed.map((u) => u.id).sort();
const ldUnc = dates.unconfirmed.map((u) => u.id).sort();
check("unconfirmed leads are exactly the sweep's two",
  JSON.stringify(rwUnc) === JSON.stringify(ldUnc) &&
  rw.unconfirmed.every((u) => u.status === "unconfirmed"));
check("JamBase conflict kept as an open conflict, not smoothed over",
  Array.isArray(rw.open_conflicts) && rw.open_conflicts.length === 1 && /JamBase/.test(rw.open_conflicts[0]));

const flip = rw.post_release_flip;
check("flip is armed with named steps",
  flip.state === "armed" && Array.isArray(flip.steps) && flip.steps.length === 5 &&
  flip.steps.some((s) => s.includes("scene-figures")) && flip.steps.some((s) => s.includes("signal_watch_capture")));
const cap = flip.signal_watch_capture;
check("first-capture slot pending and honestly null",
  cap.status === "pending" && cap.captured_at === null && cap.source === null &&
  cap.vault_tracks_watched === null && cap.new_uploads === null);
check("all three page states documented",
  ["pre_release", "release_day_unconfirmed", "released"].every((k) => typeof rw.page_states[k] === "string"));

console.log("== release-week: page behavior (DOM shim)");
const SRC = fs.readFileSync(path.join(ROOT, "assets/js/release-week.js"), "utf8");

function makeEl(attrs) {
  return {
    attrs: Object.assign({}, attrs),
    textContent: "",
    innerHTML: "",
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    removeAttribute(k) { delete this.attrs[k]; },
  };
}

function runPage(fetchData) {
  const chips = [makeEl({ "data-when": "2026-10-15" }), makeEl({ "data-when": "2026-10-16", id: "rw-release-chip" })];
  const byId = {
    "rw-state": makeEl({ "data-status": "announced", "data-expected": "2026-10-16" }),
    "rw-release-chip": chips[1],
    "rw-capture": makeEl({}),
  };
  byId["rw-state"].textContent = "Announced — expected 2026-10-16.";
  byId["rw-capture"].innerHTML = "First Signal capture after the release: not logged yet.";
  const document = {
    baseURI: "http://localhost/scene/uncle-release-week.html",
    getElementById: (id) => byId[id] || null,
    querySelectorAll: (sel) => (sel === "[data-when]" ? chips : []),
  };
  const fetchedUrls = [];
  const window = {
    fetch: (u) => { fetchedUrls.push(String(u)); return Promise.resolve({ ok: true, json: () => Promise.resolve(fetchData) }); },
  };
  vm.runInNewContext(SRC, { document, window, fetch: window.fetch, URL, console });
  return new Promise((res) => setImmediate(() => res({ chips, byId, fetchedUrls })));
}

(async () => {
  const rel = (over) => Object.assign(JSON.parse(JSON.stringify(rw)), over);

  const a = await runPage(rel({}));
  check("data fetch resolves from the scene/ directory to the repo data file",
    a.fetchedUrls.length === 1 && a.fetchedUrls[0] === "http://localhost/data/release-week-uncle.json");
  check("party chip paints a countdown (Oct 15)", /today|tomorrow|in \d+ days|yesterday|\d+ days ago/.test(a.chips[0].textContent));
  check("release chip paints a countdown (Oct 16)", /today|tomorrow|in \d+ days|yesterday|\d+ days ago/.test(a.chips[1].textContent));
  check("announced file never flips the state line", a.byId["rw-state"].getAttribute("data-status") === "announced");
  check("pending capture slot text stands", /not logged yet/.test(a.byId["rw-capture"].innerHTML));

  const flipped = rel({});
  flipped.release.status = "released";
  flipped.release.confirmed_at = "2026-10-17";
  flipped.release.confirmed_by = "K Records listing";
  flipped.post_release_flip.signal_watch_capture = {
    status: "logged", captured_at: "2026-10-17T16:00:00Z", source: "Signal cron capture",
    vault_tracks_watched: 185, new_uploads: 0,
  };
  const b = await runPage(flipped);
  check("released file flips the state line",
    b.byId["rw-state"].getAttribute("data-status") === "released" && /Released — confirmed 2026-10-17/.test(b.byId["rw-state"].textContent));
  check("released file turns the chip to 'out now'",
    b.chips[1].textContent === "out now" && b.chips[1].getAttribute("data-when") === null);
  check("logged capture fills the slot", /First Signal capture after the release: logged 2026-10-17/.test(b.byId["rw-capture"].innerHTML));

  console.log("\nrelease-week: " + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})();
