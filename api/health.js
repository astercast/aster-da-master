/* api/health.js — GET /api/health (§1.4). No auth. Edge-cacheable.
 * Never returns 5xx: a failing check flips status to "degraded", not the
 * HTTP code. uptime_s is per-instance (cold-start reset is expected).
 *
 * Fleet Commons alignment (Rotation 13, patterns/health-endpoint
 * canonical v1.0.0, FULL variant): non-GET/HEAD requests get the 400
 * BAD_INPUT envelope (was a plain-text 405); the public rate-limit
 * bucket applies with hashed-IP logging; status is "ok" only when the
 * files are present and within SLA *and* CRON_SECRET is configured
 * (github_token_configured is reported, never gating — token-pending
 * read-only mode is legitimate); the response is edge-cached at
 * s-maxage=60; a handler error reports as a degraded 200 envelope,
 * never a 500. The per-file freshness extractors stay site-specific
 * (each file's own timestamp field, per the canonical's plug-in rule).
 */
"use strict";

const { ok, err, nowIso } = require("../lib/envelope");
const { checkLimit } = require("../lib/ratelimit");

const SERVICE = "aster-signal";
const VERSION = "1.0.0";
const SLA_S = 86400; // 24h freshness SLA for Signal data (§7.4)

// function files in this deployment (§7.4 roster, Signal 2.0 wave added
// "watch"); tests/api.test.sh asserts this list matches exactly.
const FUNCTIONS = ["health", "stats", "uploads", "watch", "cron/signal"];

// static JSON the Signal's functions depend on, with the timestamp field
// each one carries and the SLA each is judged against.
const FRESHNESS_FILES = [
  { file: "data/v1/refresh-status.json", tsField: "snapshot_at", sla_s: SLA_S },
  { file: "data/v1/uploads.json", tsField: "generated_at", sla_s: SLA_S },
  { file: "data/v1/stats-snapshots.json", tsField: "generated_at", sla_s: SLA_S },
  { file: "data/v1/signal-watch.json", tsField: "generated_at", sla_s: SLA_S },
  { file: "data/v1/artist.json", tsField: "observed", sla_s: SLA_S * 7 },
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
  try {
    if (req.method !== "GET" && req.method !== "HEAD") {
      return err(res, SERVICE, VERSION, 400, "BAD_INPUT",
        "Only GET is supported on /api/health.", { fields: ["method"] });
    }

    const limit = checkLimit(req, "public");
    if (!limit.allowed) {
      console.log("[ratelimit] ip=" + limit.ipHash +
        " bucket=public path=/api/health");
      res.setHeader("Retry-After", String(limit.retryAfter));
      return err(res, SERVICE, VERSION, 429, "RATE_LIMITED",
        "Rate limit exceeded. Try again shortly.",
        { retry_after_s: limit.retryAfter });
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
    const githubToken = !!(process.env.GITHUB_REPO_TOKEN && process.env.GITHUB_REPO);
    // Canonical gating: files present + within SLA + cron secret.
    const status = allWithinSla && staticPresent && cronSecret ? "ok" : "degraded";

    return ok(
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
        stale_since: status !== "ok" ? startedAt : null,
        upstream: [],
        note: status === "ok"
          ? null
          : "One or more health checks failed; see data.checks and " +
            "data.data_freshness. The static fallback contract (§3) " +
            "keeps the site honest meanwhile.",
        cacheMaxAge: 60,
      }
    );
  } catch (e) {
    // Never 5xx (§1.4): even an internal failure reports as degraded.
    try {
      return ok(
        res,
        SERVICE,
        VERSION,
        {
          status: "degraded",
          service: SERVICE,
          version: VERSION,
          started_at: startedAt,
          uptime_s: Math.round((Date.now() - bootTime) / 1000),
          node: process.version,
          functions: FUNCTIONS,
          data_freshness: {},
          checks: { handler_error: false },
          error: String((e && e.message) || e),
        },
        { source: "live", degraded: true, stale_since: startedAt,
          upstream: [], note: null, cacheMaxAge: 60 }
      );
    } catch (e2) {
      res.statusCode = 200;
      res.setHeader("Content-Type", "application/json; charset=utf-8");
      res.end(JSON.stringify({ ok: true, data: { status: "degraded", service: SERVICE }, meta: {} }));
    }
  }
};
