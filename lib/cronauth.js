/* cronauth.js — CRON_SECRET bearer check (§8.3, §1.11).
 * Identical across all 7 repos; do not fork.
 * Vercel auto-sends `Authorization: Bearer <CRON_SECRET>` on cron invocations
 * when CRON_SECRET is set. Fail closed: no secret configured -> deny.
 */
"use strict";

const MISSING = "cron-secret-missing";

/**
 * @returns {{ok:boolean, reason:string}} reason is "ok", "missing-secret",
 *   or "bad-secret". Logs the denial line per §4.5 (never logs the secret).
 */
function assertCron(req, jobName) {
  const configured = process.env.CRON_SECRET;
  if (!configured) {
    console.log("[cron] " + (jobName || "job") + " denied: CRON_SECRET not configured");
    return { ok: false, reason: "missing-secret" };
  }
  const got = req.headers && (req.headers.authorization || req.headers.Authorization);
  if (got === "Bearer " + configured) {
    return { ok: true, reason: "ok" };
  }
  console.log("[cron] " + (jobName || "job") + " denied: bad bearer token");
  return { ok: false, reason: "bad-secret" };
}

module.exports = { assertCron, MISSING };
