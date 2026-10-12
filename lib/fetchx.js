/* fetchx.js — bounded upstream fetch with AbortController timeout.
 * Identical across all 7 repos; do not fork.
 * All upstream calls go through fetchTimeout(). Never fetch raw.
 */
"use strict";

/**
 * @param {string} url
 * @param {object} [opts] { timeoutMs (default 4000), headers, userAgent, method }
 * @returns {Promise<{ok, status, text, ms, error}>}
 *   ok: true iff HTTP 2xx and no transport error. text is always a string.
 */
async function fetchTimeout(url, opts) {
  opts = opts || {};
  const timeoutMs = opts.timeoutMs || 4000;
  const t0 = Date.now();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  const headers = Object.assign({}, opts.headers || {});
  if (opts.userAgent && !headers["User-Agent"] && !headers["user-agent"]) {
    headers["User-Agent"] = opts.userAgent;
  }
  try {
    const r = await fetch(url, {
      method: opts.method || "GET",
      headers,
      signal: ctrl.signal,
      redirect: "follow",
    });
    const text = await r.text();
    return {
      ok: r.ok,
      status: r.status,
      text,
      ms: Date.now() - t0,
      error: r.ok ? null : "http " + r.status,
    };
  } catch (e) {
    const ms = Date.now() - t0;
    const name = e && e.name ? e.name : "Error";
    const aborted = name === "AbortError" || (e && e.code === 20);
    return {
      ok: false,
      status: 0,
      text: "",
      ms,
      error: aborted ? "timeout after " + timeoutMs + "ms" : String((e && e.message) || e),
    };
  } finally {
    clearTimeout(timer);
  }
}

module.exports = { fetchTimeout };
