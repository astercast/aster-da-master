/* api/health.js — GET /api/health (§1.4). No auth. Edge-cacheable.
 * Never returns 5xx: a failing check flips status to "degraded", not the
 * HTTP code. uptime_s is per-instance (cold-start reset is expected).
 */
"use strict";

const { ok, nowIso } = require("../lib/envelope");

const SERVICE = "aster-signal";
const VERSION = "1.0.0";
const SLA_S = 86400; // 24h freshness SLA for Signal data (§7.4)

// function files in this deployment (§7.4 roster); the wave-A test asserts
// this list matches the spec roster exactly.
const FUNCTIONS = ["health", "stats", "uploads", "cron/signal"];

// static JSON the Signal's functions depend on, with the timestamp field
// each one carries and the SLA each is judged against.
const FRESHNESS_FILES = [
  { file: "api/v1/refresh-status.json", tsField: "snapshot_at", sla_s: SLA_S },
  { file: "api/v1/uploads.json", tsField: "generated_at", sla_s: SLA_S },
  { file: "api/v1/stats-snapshots.json", tsField: "generated_at", sla_s: SLA_S },
  { file: "api/v1/artist.json", tsField: "observed", sla_s: SLA_S * 7 },
];

const startedAt = nowIso();
const bootTime = Date.now();

function readBundleJson(relPath) {
  try {
    // require() is statically analyzable: Vercel's bundler ships these files.
    const abs = require("path").join(__dirname, "..", relPath);
    delete require.cache[require.resolve(abs)];
    return { ok: true, obj: require(abs) };
  } catch (e) {
    return { ok: false, obj: null, error: e.message };
  }
}

module.exports = (req, res) => {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.setHeader("Allow", "GET");
    res.end("Method Not Allowed");
    return;
  }

  const nowMs = Date.now();
  const dataFreshness = {};
  let allWithinSla = true;
  let staticPresent = true;

  for (const f of FRESHNESS_FILES) {
    const r = readBundleJson(f.file);
    if (!r.ok) {
      staticPresent = false;
      allWithinSla = false;
      dataFreshness[f.file.split("/").pop()] = {
        generated_at: null,
        age_s: null,
        sla_s: f.sla_s,
        within_sla: false,
        error: "file unreadable: " + r.error,
      };
      continue;
    }
    let gen = r.obj && r.obj[f.tsField] ? r.obj[f.tsField] : null;
    // artist.json carries "observed" as a YYYY-MM-DD date, not RFC3339.
    if (gen && !gen.endsWith("Z") && /^\d{4}-\d{2}-\d{2}$/.test(gen)) gen = gen + "T00:00:00Z";
    const genMs = gen ? Date.parse(gen) : NaN;
    const ageS = Number.isFinite(genMs) ? Math.max(0, Math.round((nowMs - genMs) / 1000)) : null;
    const within = ageS !== null && ageS <= f.sla_s;
    if (!within) allWithinSla = false;
    dataFreshness[f.file.split("/").pop()] = {
      generated_at: Number.isFinite(genMs) ? new Date(genMs).toISOString().replace(/\.\d{3}Z$/, "Z") : null,
      age_s: ageS,
      sla_s: f.sla_s,
      within_sla: within,
    };
  }

  const cronSecret = !!process.env.CRON_SECRET;
  const githubToken = !!process.env.GITHUB_REPO_TOKEN;
  const status = allWithinSla && staticPresent ? "ok" : "degraded";

  ok(
    res,
    SERVICE,
    VERSION,
    {
      status,
      service: SERVICE,
      version: VERSION,
      started_at: startedAt,
      uptime_s: Math.round((nowMs - bootTime) / 1000),
      node: process.version,
      functions: FUNCTIONS,
      data_freshness: dataFreshness,
      checks: {
        static_fallback_present: staticPresent,
        cron_secret_configured: cronSecret,
        github_token_configured: githubToken,
      },
    },
    {
      source: "live",
      degraded: status !== "ok",
      note: status === "ok"
        ? null
        : "One or more Signal data files are missing or past their freshness SLA; " +
          "see data_freshness. The static fallback contract (§3) keeps the site honest meanwhile.",
    }
  );
};
