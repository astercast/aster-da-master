/* ratelimit.js — per-instance in-memory token bucket (§1.7).
 * Identical across all 7 repos; do not fork.
 * Best-effort: resets on cold start. Keyed on x-forwarded-for (first entry).
 */
"use strict";

const BUCKETS = {
  public: { limit: 60, windowMs: 60 * 1000 },   // public GET functions
  compute: { limit: 20, windowMs: 60 * 1000 },  // POST compute endpoints
};

// ip -> { bucket -> [timestamps] }
const store = new Map();

function clientIp(req) {
  const fwd = req.headers && (req.headers["x-forwarded-for"] || req.headers["X-Forwarded-For"]);
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim();
  if (req.socket && req.socket.remoteAddress) return req.socket.remoteAddress;
  return "unknown";
}

function ipHash(ip) {
  return require("crypto").createHash("sha256").update(ip).digest("hex").slice(0, 12);
}

/**
 * @returns {{allowed:boolean, retryAfter:number}} retryAfter in seconds.
 */
function checkLimit(req, bucketName) {
  const cfg = BUCKETS[bucketName] || BUCKETS.public;
  const ip = clientIp(req);
  const now = Date.now();
  let rec = store.get(ip);
  if (!rec) { rec = {}; store.set(ip, rec); }
  let hits = rec[bucketName] || [];
  hits = hits.filter((t) => now - t < cfg.windowMs);
  if (hits.length >= cfg.limit) {
    const oldest = hits[0];
    const retryAfter = Math.max(1, Math.ceil((cfg.windowMs - (now - oldest)) / 1000));
    rec[bucketName] = hits;
    return { allowed: false, retryAfter, ipHash: ipHash(ip) };
  }
  hits.push(now);
  rec[bucketName] = hits;
  return { allowed: true, retryAfter: 0, ipHash: ipHash(ip) };
}

module.exports = { checkLimit, BUCKETS, clientIp, ipHash };
