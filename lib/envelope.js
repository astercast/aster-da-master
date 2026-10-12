/* envelope.js — shared §1.1 envelope helpers (identical across all 7 repos; do not fork).
 * Every function returns ONLY through ok() / err(). No raw res.json() shapes.
 */
"use strict";

const CACHE_GET = "public, s-maxage=600, stale-while-revalidate=86400"; // §1.6

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function newRequestId() {
  const b = require("crypto").randomBytes(3);
  return "req_" + b.toString("hex");
}

function sendJson(res, status, body, cacheControl) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", cacheControl);
  res.end(JSON.stringify(body));
}

/* Success envelope. opts: { source, degraded, stale_since, upstream[], note,
 * cache ('get'|'none'), version } */
function ok(res, service, version, data, opts) {
  opts = opts || {};
  const meta = {
    service,
    version,
    generated_at: nowIso(),
    request_id: newRequestId(),
  };
  if (opts.source !== undefined) meta.source = opts.source;
  if (opts.degraded !== undefined) meta.degraded = opts.degraded;
  if (opts.stale_since !== undefined) meta.stale_since = opts.stale_since;
  if (opts.upstream !== undefined) meta.upstream = opts.upstream;
  if (opts.note !== undefined) meta.note = opts.note;
  const cache = opts.cache === "none" ? "no-store" : CACHE_GET;
  sendJson(res, 200, { ok: true, data, meta }, cache);
  return meta.request_id;
}

/* Error envelope. Always 4xx/5xx with ok:false and an error object. */
function err(res, service, version, httpStatus, code, message, details) {
  const body = {
    ok: false,
    data: null,
    meta: {
      service,
      version,
      generated_at: nowIso(),
      request_id: newRequestId(),
    },
    error: { code, message },
  };
  if (details !== undefined) body.error.details = details;
  sendJson(res, httpStatus, body, "no-store");
  return body.meta.request_id;
}

/* 400 helper for query/body validation failures. fields: {param: reason} */
function badInput(res, service, version, fields) {
  const keys = Object.keys(fields).join(", ");
  return err(
    res, service, version, 400, "BAD_INPUT",
    "Invalid request parameters: " + keys + ".",
    { fields }
  );
}

module.exports = { nowIso, newRequestId, ok, err, badInput, CACHE_GET };
