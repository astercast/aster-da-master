/* lib/signal-watch.js — The Signal 2.0 watch logic (pure, no I/O).
 *
 * Shared by api/cron/signal.js (live refresh) and scripts/test_signal_watch.js
 * (fixtures + the real archive captures). The Python mirror that seeds the
 * committed watch file is scripts/build_signal_watch.py — keep the keying
 * and threshold rules in step with it.
 *
 * Keying lessons (paid for in the 2026-10-11 captures):
 *  - The same track can appear with a curly apostrophe in one capture and
 *    a straight one in the next, or with a doubled space. Naive title
 *    matching flags those as new uploads. Keys therefore normalize case,
 *    apostrophes, quotes and whitespace before anything is compared.
 *  - Upload dates are display data, never identity: the research capture
 *    behind artist.json runs one day behind the api-v2 created_at for
 *    most tracks, and a handful differ by months (session-derived dates
 *    vs raw created_at). Keying on title+date flagged 121 of 185 tracks
 *    as simultaneously new and removed. Vault titles are unique after
 *    normalization (asserted in the test), so the normalized title alone
 *    is the key; a same-capture collision falls back to title+date.
 *
 * Honesty rules:
 *  - per_day is a plain division over the real elapsed time between two
 *    captures, and only when that gap is at least 24 hours. Anything
 *    shorter reports null — a rate is never invented from same-day noise.
 *  - a milestone crossing requires the track to be strictly below the
 *    threshold in the earlier capture and at/above it in the later one.
 */
"use strict";

const THRESHOLDS = [100, 500, 1000, 5000, 10000, 20000, 30000];
const DAY_MS = 86400000;

/* The watch file's method statement. scripts/build_signal_watch.py carries
 * the same text — one method, two writers (seed + cron). */
const METHOD =
  "Each capture of the SoundCloud vault is diffed against the previous one. " +
  "Tracks are keyed by normalized title (case, apostrophe style and whitespace " +
  "unified) or permalink when a live refresh captured one — upload dates drift " +
  "between capture methods and are never used as identity. A track in the new " +
  "capture with no key in the old is a new upload. per_day is plain division over " +
  "the real gap between captures and is only reported when that gap is at least " +
  "24 hours; below that it is null rather than invented.";

function normTitle(t) {
  return String(t || "")
    .replace(/[‘’ʼ]/g, "'")
    .replace(/[“”]/g, '"')
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/* Stable identity for a track across captures: the permalink when a live
 * refresh captured one, else the normalized title alone (see the keying
 * lessons above — dates drift between capture methods). */
function trackKey(t) {
  if (t && typeof t.url === "string" && t.url) return "url:" + t.url.replace(/\/+$/, "");
  return "title:" + normTitle(t && t.title);
}

function playsOf(t) {
  const n = Number(t && t.plays);
  return Number.isFinite(n) && n >= 0 ? Math.round(n) : null;
}

function indexTracks(tracks) {
  const map = new Map();
  for (const t of tracks || []) {
    if (!t || typeof t.title !== "string") continue;
    const p = playsOf(t);
    if (p === null) continue;
    let key = trackKey(t);
    /* Same normalized title twice inside ONE capture (a genuine duplicate
     * title, not style drift): fall back to title+date so both survive. */
    if (map.has(key)) key = key + "|" + String(t.upload_date || t.uploaded_at || "");
    map.set(key, {
      title: t.title,
      upload_date: t.upload_date || t.uploaded_at || null,
      plays: p,
      url: typeof t.url === "string" ? t.url : null,
    });
  }
  return map;
}

/* Diff two captures. prev/curr: { captured_at, tracks: [{title, plays,
 * upload_date|uploaded_at, url}] }. Returns new uploads, removals, movers
 * (non-zero play deltas, biggest first) and round-number crossings. */
function diffCaptures(prev, curr) {
  const prevMap = indexTracks(prev && prev.tracks);
  const currMap = indexTracks(curr && curr.tracks);
  const prevAt = Date.parse((prev && prev.captured_at) || "");
  const currAt = Date.parse((curr && curr.captured_at) || "");
  const elapsedDays = Number.isFinite(prevAt) && Number.isFinite(currAt) && currAt > prevAt
    ? (currAt - prevAt) / DAY_MS
    : null;
  const rateOk = elapsedDays !== null && elapsedDays >= 1;

  const newUploads = [];
  const removed = [];
  const movers = [];
  const crossings = [];

  for (const [key, c] of currMap) {
    const p = prevMap.get(key);
    if (!p) {
      newUploads.push({ title: c.title, uploaded_at: c.upload_date, plays: c.plays, url: c.url });
      continue;
    }
    if (c.plays !== p.plays) {
      movers.push({
        title: c.title,
        before: p.plays,
        after: c.plays,
        delta: c.plays - p.plays,
        per_day: rateOk ? Math.round(((c.plays - p.plays) / elapsedDays) * 100) / 100 : null,
        url: c.url || p.url,
      });
    }
    for (const th of THRESHOLDS) {
      if (p.plays < th && c.plays >= th) {
        crossings.push({ title: c.title, threshold: th, before: p.plays, after: c.plays, url: c.url || p.url });
      }
    }
  }
  for (const [key, p] of prevMap) {
    if (!currMap.has(key)) {
      removed.push({ title: p.title, uploaded_at: p.upload_date, plays: p.plays, url: p.url });
    }
  }

  movers.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta) || (a.title < b.title ? -1 : 1));
  newUploads.sort((a, b) => String(b.uploaded_at || "") < String(a.uploaded_at || "") ? -1 : 1);
  crossings.sort((a, b) => b.threshold - a.threshold || (a.title < b.title ? -1 : 1));

  return {
    previous_capture_at: (prev && prev.captured_at) || null,
    latest_capture_at: (curr && curr.captured_at) || null,
    elapsed_days: elapsedDays === null ? null : Math.round(elapsedDays * 100) / 100,
    tracks_watched: currMap.size,
    total_plays: Array.from(currMap.values()).reduce((s, t) => s + t.plays, 0),
    total_delta: movers.reduce((s, m) => s + m.delta, 0),
    new_uploads: newUploads,
    removed: removed,
    movers: movers,
    crossings: crossings,
  };
}

module.exports = { THRESHOLDS, METHOD, normTitle, trackKey, diffCaptures };
