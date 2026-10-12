/* api/watch.js — GET /api/watch (The Signal 2.0).
 * The watch board payload: new-upload detection, play-count movers,
 * milestone crossings, and the live-date verification board, read from
 * the committed watch files (data/v1/signal-watch.json, written by the
 * daily cron's diff and seeded by scripts/build_signal_watch.py;
 * data/v1/live-dates.json, hand-verified research).
 *
 * ?kind= narrows the payload: all (default) | new | movers | crossings |
 * dates. Anything else is a 400 BAD_INPUT. Freshness is reported against
 * the watch file's own generated_at — a stale watch degrades honestly,
 * never silently.
 */
"use strict";

const { ok, err, badInput, nowIso } = require("../lib/envelope");
const { checkLimit } = require("../lib/ratelimit");
const path = require("path");

const SERVICE = "aster-signal";
const VERSION = "2.0.0";
const KINDS = ["all", "new", "movers", "crossings", "dates"];
const FRESH_SLA_MS = 24 * 3600 * 1000;

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

module.exports = (req, res) => {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.setHeader("Allow", "GET");
    res.end("Method Not Allowed");
    return;
  }

  const rl = checkLimit(req, "public");
  if (!rl.allowed) {
    console.log("[ratelimit] ip=" + rl.ipHash + " bucket=public path=/api/watch");
    res.setHeader("Retry-After", String(rl.retryAfter));
    err(res, SERVICE, VERSION, 429, "RATE_LIMITED",
      "Too many requests. Please retry in " + rl.retryAfter + " seconds.",
      { retry_after_s: rl.retryAfter });
    return;
  }

  const query = req.query || {};
  const kind = query.kind === undefined || query.kind === "" ? "all" : String(query.kind);
  if (!KINDS.includes(kind)) {
    badInput(res, SERVICE, VERSION, { kind: "must be one of " + KINDS.join(", ") });
    return;
  }

  const checkedAt = nowIso();
  const watch = readJson("data/v1/signal-watch.json");
  const dates = readJson("data/v1/live-dates.json");
  const upstream = [
    { source: "repo:data/v1/signal-watch.json", ok: watch.ok, checked_at: checkedAt, latency_ms: watch.ms },
    { source: "repo:data/v1/live-dates.json", ok: dates.ok, checked_at: checkedAt, latency_ms: dates.ms },
  ];
  if (!watch.ok) upstream[0].error = watch.error;
  if (!dates.ok) upstream[1].error = dates.error;

  if (!watch.ok || !watch.obj.summary) {
    err(res, SERVICE, VERSION, 502, "UPSTREAM_UNAVAILABLE",
      "The watch file is unavailable right now. The Signal page keeps its last published static data instead.",
      { sources: ["repo:data/v1/signal-watch.json"] });
    return;
  }

  const w = watch.obj;
  const genMs = Date.parse(w.generated_at || "");
  const ageMs = Number.isFinite(genMs) ? Math.max(0, Date.now() - genMs) : NaN;
  const stale = !Number.isFinite(ageMs) || ageMs > FRESH_SLA_MS;
  const freshness = {
    checked_at: checkedAt,
    generated_at: w.generated_at || null,
    age_hours: Number.isFinite(ageMs) ? Math.round(ageMs / 3600000) : null,
    status: !Number.isFinite(ageMs) ? "unknown" : stale ? "stale" : "fresh",
    sla_hours: FRESH_SLA_MS / 3600000,
    live_dates_checked_at: dates.ok ? dates.obj.checked_at || null : null,
  };

  const data = { kind, freshness };
  if (kind === "all" || kind === "new") {
    data.summary = w.summary;
    data.new_uploads = w.new_uploads || [];
    data.removed = w.removed || [];
  }
  if (kind === "all" || kind === "movers") {
    data.movers = w.movers || [];
    data.next_up = w.next_up || [];
  }
  if (kind === "all" || kind === "crossings") data.crossings = w.crossings || [];
  if (kind === "all" || kind === "dates") {
    data.live_dates = dates.ok
      ? { checked_at: dates.obj.checked_at, events: dates.obj.events || [], unconfirmed: dates.obj.unconfirmed || [] }
      : null;
  }
  if (kind === "all") data.baseline = w.baseline || null;

  ok(
    res, SERVICE, VERSION, data,
    {
      source: "live",
      degraded: stale,
      upstream,
      note: stale
        ? "The watch file is past its 24-hour freshness window — these are the latest verified captures, not a live feed."
        : null,
    }
  );
};
