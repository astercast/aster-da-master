/* api/stats.js — GET /api/stats (§7.4 "The Signal").
 * Fresh numbers dashboard payload, computed live from the latest committed
 * snapshot: {tracks_captured, total_plays, snapshot_at, top_tracks, source}.
 * top_tracks carry delta_7d vs the snapshot row closest to 7 days ago;
 * delta_7d is null when no comparable history exists yet (honest gap, never
 * interpolated — §6). No bio content, no track content beyond titles/counts.
 */
"use strict";

const { ok, err, nowIso } = require("../lib/envelope");
const { checkLimit } = require("../lib/ratelimit");
const path = require("path");

const SERVICE = "aster-signal";
const VERSION = "1.0.0";
const UA = SERVICE + "/" + VERSION;
const TOP_N = 10;
const SEVEN_D_MS = 7 * 86400 * 1000;

function readJson(rel) {
  const t0 = Date.now();
  try {
    const abs = path.join(__dirname, "..", rel);
    delete require.cache[require.resolve(abs)];
    return { ok: true, obj: require(abs), ms: Date.now() - t0, error: null };
  } catch (e) {
    return { ok: false, obj: null, ms: Date.now() - t0, error: e.message };
  }
}

function upstreamEntry(source, r, checkedAt) {
  const e = { source, ok: r.ok, checked_at: checkedAt, latency_ms: r.ms };
  if (!r.ok) e.error = r.error;
  return e;
}

/* Closest history row to (now - 7d); null when the window has no row. */
function rowClosestTo7d(rows, nowMs) {
  let best = null;
  let bestDist = Infinity;
  for (const r of rows || []) {
    const t = Date.parse(r.snapshot_at);
    if (!Number.isFinite(t)) continue;
    const dist = Math.abs(t - (nowMs - SEVEN_D_MS));
    if (dist < bestDist) { bestDist = dist; best = r; }
  }
  // Only a row roughly a week old counts as the 7-day baseline (5–9 day band).
  if (!best) return null;
  const ageDays = Math.abs(Date.parse(best.snapshot_at) - (nowMs - SEVEN_D_MS)) / 86400000;
  return ageDays <= 2 ? best : null;
}

module.exports = (req, res) => {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.setHeader("Allow", "GET");
    res.end("Method Not Allowed");
    return;
  }

  const rl = checkLimit(req, "public");
  if (!rl.allowed) {
    console.log("[ratelimit] ip=" + rl.ipHash + " bucket=public path=/api/stats");
    res.setHeader("Retry-After", String(rl.retryAfter));
    err(res, SERVICE, VERSION, 429, "RATE_LIMITED",
      "Too many requests. Please retry in " + rl.retryAfter + " seconds.",
      { retry_after_s: rl.retryAfter });
    return;
  }

  const checkedAt = nowIso();
  const upstream = [];

  const snap = readJson("data/playcounts.snapshot.json");
  upstream.push(upstreamEntry("repo:data/playcounts.snapshot.json", snap, checkedAt));
  const status = readJson("api/v1/refresh-status.json");
  upstream.push(upstreamEntry("repo:api/v1/refresh-status.json", status, checkedAt));
  const hist = readJson("api/v1/stats-snapshots.json");
  upstream.push(upstreamEntry("repo:api/v1/stats-snapshots.json", hist, checkedAt));

  if (!snap.ok || !Array.isArray(snap.obj.tracks) || snap.obj.tracks.length === 0) {
    // No usable snapshot at all: honest 502; the frontend falls back to its
    // static file per §3 (which carries its own generated_at).
    err(res, SERVICE, VERSION, 502, "UPSTREAM_UNAVAILABLE",
      "No usable play-count snapshot is available right now. The numbers dashboard " +
      "is showing its last published static data instead.",
      { sources: ["repo:data/playcounts.snapshot.json"] });
    return;
  }

  const tracks = snap.obj.tracks
    .filter((t) => t && typeof t.title === "string")
    .map((t) => ({ title: t.title, plays: Number(t.plays) || 0 }));

  const totalPlays = tracks.reduce((s, t) => s + t.plays, 0);
  const top = tracks
    .slice()
    .sort((a, b) => b.plays - a.plays || (a.title < b.title ? -1 : 1))
    .slice(0, TOP_N);

  const baseline = hist.ok ? rowClosestTo7d(hist.obj.snapshots || hist.obj.rows, Date.now()) : null;
  const baseMap = {};
  if (baseline && Array.isArray(baseline.top)) {
    for (const b of baseline.top) baseMap[b.title] = Number(b.plays) || 0;
  }

  const topTracks = top.map((t) => ({
    title: t.title,
    plays: t.plays,
    delta_7d: Object.prototype.hasOwnProperty.call(baseMap, t.title)
      ? t.plays - baseMap[t.title]
      : null,
  }));

  const snapshotAt = (status.ok && status.obj.snapshot_at) || snap.obj.snapshot_at || null;
  const tracksCaptured = (status.ok && Number(status.obj.tracks_captured)) || tracks.length;

  ok(
    res, SERVICE, VERSION,
    {
      tracks_captured: tracksCaptured,
      total_plays: totalPlays,
      snapshot_at: snapshotAt,
      top_tracks: topTracks,
      source: snap.obj.source || "soundcloud api-v2",
      delta_baseline_at: baseline ? baseline.snapshot_at : null,
    },
    {
      source: "live",
      degraded: false,
      upstream,
      note: baseline ? null : "delta_7d is not available yet — the Signal is still building its first week of history.",
    }
  );
};
