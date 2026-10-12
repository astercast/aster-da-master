/* api/uploads.js — GET /api/uploads (§7.4 "The Signal").
 * New-upload detection payload: ?since= (ISO date, default 30d ago).
 * A track counts as new when its uploaded_at is on/after `since`
 * (uploaded_at missing -> falls back to first_seen_at). Invalid dates get a
 * 400 BAD_INPUT envelope with details.fields (§1.2, §8.5). Sorted newest
 * first. Titles + dates + permalinks only — never track content.
 */
"use strict";

const { ok, err, badInput, nowIso } = require("../lib/envelope");
const { checkLimit } = require("../lib/ratelimit");
const path = require("path");

const SERVICE = "aster-signal";
const VERSION = "1.0.0";
const DEFAULT_WINDOW_DAYS = 30;
const MAX_LIMIT = 200;

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

function parseSince(raw, nowMs) {
  if (raw === undefined || raw === null || raw === "") {
    return { ok: true, iso: new Date(nowMs - DEFAULT_WINDOW_DAYS * 86400000).toISOString().replace(/\.\d{3}Z$/, "Z") };
  }
  let s = String(raw).trim();
  // Accept YYYY-MM-DD as midnight UTC.
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) s = s + "T00:00:00Z";
  const ms = Date.parse(s);
  if (!Number.isFinite(ms)) {
    return { ok: false, error: "must be a valid ISO date (YYYY-MM-DD or full RFC 3339)" };
  }
  return { ok: true, iso: new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z") };
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
    console.log("[ratelimit] ip=" + rl.ipHash + " bucket=public path=/api/uploads");
    res.setHeader("Retry-After", String(rl.retryAfter));
    err(res, SERVICE, VERSION, 429, "RATE_LIMITED",
      "Too many requests. Please retry in " + rl.retryAfter + " seconds.",
      { retry_after_s: rl.retryAfter });
    return;
  }

  const nowMs = Date.now();
  const checkedAt = nowIso();

  // ---- input validation (§8.5): coerce with bounds, 400 on bad input ----
  const query = req.query || {};
  const sinceP = parseSince(query.since, nowMs);
  if (!sinceP.ok) {
    badInput(res, SERVICE, VERSION, { since: sinceP.error });
    return;
  }
  let limit = 50;
  if (query.limit !== undefined && query.limit !== "") {
    const n = Number(query.limit);
    if (!Number.isInteger(n) || n < 1) {
      badInput(res, SERVICE, VERSION, { limit: "must be an integer between 1 and " + MAX_LIMIT });
      return;
    }
    limit = Math.min(n, MAX_LIMIT);
  }

  const up = readJson("data/v1/uploads.json");
  const upstream = [{
    source: "repo:data/v1/uploads.json",
    ok: up.ok,
    checked_at: checkedAt,
    latency_ms: up.ms,
  }];
  if (!up.ok) upstream[0].error = up.error;

  if (!up.ok || !Array.isArray(up.obj.uploads)) {
    err(res, SERVICE, VERSION, 502, "UPSTREAM_UNAVAILABLE",
      "The upload log is unavailable right now. The page keeps its last published static data instead.",
      { sources: ["repo:data/v1/uploads.json"] });
    return;
  }

  const sinceMs = Date.parse(sinceP.iso);
  /* newest-first over the FULL log first: "newest upload on record" must not
     depend on the caller's ?since window. */
  const all = up.obj.uploads
    .filter((u) => u && typeof u.title === "string")
    .map((u) => ({
      title: u.title,
      uploaded_at: u.uploaded_at || null,
      url: u.url || null,
      first_seen_at: u.first_seen_at || null,
    }))
    .sort((a, b) => {
      const ta = Date.parse(a.uploaded_at || a.first_seen_at || 0);
      const tb = Date.parse(b.uploaded_at || b.first_seen_at || 0);
      return tb - ta || (a.title < b.title ? -1 : 1);
    });
  const newestOnRecord = all.length ? all[0].uploaded_at || all[0].first_seen_at : null;
  const uploads = all
    .filter((u) => {
      const ref = u.uploaded_at || u.first_seen_at;
      const t = ref ? Date.parse(ref) : NaN;
      return Number.isFinite(t) && t >= sinceMs;
    })
    .slice(0, limit);

  ok(
    res, SERVICE, VERSION,
    {
      since: sinceP.iso,
      count: uploads.length,
      uploads,
      /* Freshness: the dashboard states when it last checked and what the
         newest upload on record is — both from real data, never "now". */
      checked_at: checkedAt,
      newest_upload_at: newestOnRecord,
      freshness: {
        checked_at: checkedAt,
        newest_upload_at: newestOnRecord,
        status: "ok",
        source: "repo:data/v1/uploads.json",
      },
    },
    { source: "live", degraded: false, upstream }
  );
};
