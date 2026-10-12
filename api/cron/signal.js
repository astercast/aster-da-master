/* api/cron/signal.js — GET /api/cron/signal (§7.4 "The Signal").
 * Daily 0 16 * * * UTC. Cron-only: CRON_SECRET bearer required, fail closed.
 *
 * Bounded incremental refresh (fits the 10s function budget):
 *  1. read current state (github.js readJson — GitHub is the source of truth)
 *  2. fetch SoundCloud api-v2 in parallel-ish (4s per-source timeouts)
 *  3. merge: diff track titles vs known set -> new_uploads[]
 *  4. writeJsonIfChanged per file (no change -> no commit -> no redeploy)
 *  5. envelope with per-source results (doubles as the run report, §4.5)
 *
 * READ-ONLY DEGRADATION: without GITHUB_REPO_TOKEN the job computes fresh
 * data and returns it in the envelope but persists nothing (see lib/github.js
 * header — the fine-grained PAT is pending the user's decision). Nothing is
 * faked: read_only:true is in the payload and the note says so plainly.
 *
 * Idempotent (§4.3): content-hash commits, title-set dedupe, 60s duplicate
 * cooldown, SHA-conflict retry in github.js.
 */
"use strict";

const { ok, err, nowIso } = require("../../lib/envelope");
const { fetchTimeout } = require("../../lib/fetchx");
const { assertCron } = require("../../lib/cronauth");
const { readJson, writeJsonIfChanged, REPO } = require("../../lib/github");

const SERVICE = "aster-signal";
const VERSION = "1.0.0";
const UA = SERVICE + "/" + VERSION;
const PROFILE_URL = "https://soundcloud.com/asterdamaster";
const API_V2 = "https://api-v2.soundcloud.com";
const FETCH_MS = 4000;
const SNAPSHOT_DAYS = 30; // §5.1 retention: aster stats snapshots, last 30 daily
const UPLOADS_DAYS = 90;  // upload entries pruned after 90 days
const COOLDOWN_MS = 60000;

const lastRunAt = new Map(); // job name -> timestamp (double-fire protection)

function normTitle(t) {
  return String(t || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function log() {
  console.log.apply(console, arguments);
}

/* ---- SoundCloud api-v2 client_id ----
 * Tiered read-only extraction (self-healing across key rotations):
 *  1. profile HTML: SoundCloud embeds the webapp client_id as a bare
 *     32-char alphanumeric token in the page (verified 2026-10-12).
 *  2. webapp JS bundles: the older client_id:"<key>" literal pattern
 *     (worked 2026-10-11; kept as fallback).
 * Every candidate is VERIFIED with one resolve call before use (parallel,
 * first success wins). Nothing unverified is ever used. */

async function extractClientId(upstream) {
  const checkedAt = nowIso();
  const entry = { source: "sc-webapp-client-id", ok: false, checked_at: checkedAt, latency_ms: 0 };
  const t0 = Date.now();
  const XT = 3000; // extraction steps get a tighter timeout (10s job budget)
  try {
    const html = await fetchTimeout("https://soundcloud.com", { timeoutMs: XT, userAgent: UA });
    if (!html.ok) throw new Error("profile html: " + html.error);

    const candidates = [];
    const push = (c) => { if (c && !candidates.includes(c)) candidates.push(c); };

    // 1. bare 32-char tokens in the HTML (the current webapp pattern)
    const tok = /"([A-Za-z0-9]{32})"/g;
    let m;
    while ((m = tok.exec(html.text)) !== null && candidates.length < 8) push(m[1]);

    // 2. bundle literals (older pattern, kept as fallback)
    if (candidates.length === 0) {
      const bundles = [];
      const re = /https:\/\/a-v2\.sndcdn\.com\/assets\/[\w.\-]+\.js/g;
      while ((m = re.exec(html.text)) !== null && bundles.length < 2) {
        if (!bundles.includes(m[0])) bundles.push(m[0]);
      }
      if (!bundles.length) throw new Error("no client_id token in html and no webapp bundles found");
      const fetched = await Promise.allSettled(
        bundles.map((u) => fetchTimeout(u, { timeoutMs: XT, userAgent: UA }))
      );
      for (const f of fetched) {
        if (f.status !== "fulfilled" || !f.value.ok) continue;
        const rx = /client_id\s*:\s*"([A-Za-z0-9]{20,40})"/g;
        let c;
        while ((c = rx.exec(f.value.text)) !== null) push(c[1]);
      }
    }

    if (!candidates.length) throw new Error("no client_id candidates found");

    // verify in parallel; first resolve-with-id wins
    const verified = await Promise.allSettled(
      candidates.slice(0, 8).map((cand) =>
        fetchTimeout(
          API_V2 + "/resolve?url=" + encodeURIComponent(PROFILE_URL) + "&client_id=" + encodeURIComponent(cand),
          { timeoutMs: XT, userAgent: UA }
        ).then((v) => ({ cand, v }))
      )
    );
    for (const r of verified) {
      if (r.status !== "fulfilled" || !r.value.v.ok) continue;
      try {
        const j = JSON.parse(r.value.v.text);
        if (j && j.id) {
          entry.ok = true;
          entry.latency_ms = Date.now() - t0;
          upstream.push(entry);
          return { clientId: r.value.cand, userId: j.id, via: "webapp-extraction" };
        }
      } catch (e) { /* next */ }
    }
    throw new Error("no extracted client_id verified (" + candidates.length + " candidate(s))");
  } catch (e) {
    entry.latency_ms = Date.now() - t0;
    entry.error = e.message;
    upstream.push(entry);
    log("[upstream] sc-webapp-client-id fail error=" + e.message);
    return null;
  }
}

/* ---- track pull ---- */

async function fetchTracks(clientId, userId, upstream) {
  const checkedAt = nowIso();
  const entry = { source: "sc-tracks", ok: false, checked_at: checkedAt, latency_ms: 0 };
  const t0 = Date.now();
  const tracks = [];
  try {
    let url = API_V2 + "/users/" + userId + "/tracks?client_id=" + encodeURIComponent(clientId) + "&limit=200";
    for (let page = 0; page < 3 && url; page++) {
      const r = await fetchTimeout(url, { timeoutMs: FETCH_MS, userAgent: UA });
      if (!r.ok) throw new Error("tracks page " + (page + 1) + ": " + r.error);
      const j = JSON.parse(r.text);
      const coll = j.collection || [];
      for (const t of coll) {
        if (!t || typeof t.title !== "string") continue;
        const plays = Number(t.playback_count);
        tracks.push({
          title: t.title,
          upload_date: typeof t.created_at === "string" ? t.created_at.slice(0, 10) : null,
          plays: Number.isFinite(plays) && plays >= 0 ? Math.round(plays) : null,
          url: typeof t.permalink_url === "string" ? t.permalink_url : null,
        });
      }
      url = j.next_href || null;
      if (url && !url.includes("client_id")) {
        url += (url.includes("?") ? "&" : "?") + "client_id=" + encodeURIComponent(clientId);
      }
    }
    entry.ok = true;
    entry.latency_ms = Date.now() - t0;
    upstream.push(entry);
    return tracks;
  } catch (e) {
    entry.latency_ms = Date.now() - t0;
    entry.error = e.message;
    upstream.push(entry);
    log("[upstream] sc-tracks fail error=" + e.message);
    return null;
  }
}

/* Read current state: GitHub is the source of truth (§4.2). When the GitHub
 * read fails (e.g. the file isn't committed yet, or no token for a private
 * mirror), fall back to the deployment bundle — the committed files the
 * function shipped with. The fallback used is recorded in meta.upstream. */
async function readState(repoPath, upstream) {
  const r = await readJson(repoPath, UA);
  if (r.ok) return r;
  try {
    const abs = require("path").join(__dirname, "..", "..", repoPath);
    delete require.cache[require.resolve(abs)];
    const obj = require(abs);
    upstream.push({
      source: "bundle-fallback:" + repoPath, ok: true, checked_at: nowIso(),
      error: "github read failed (" + r.error + "); used deployment bundle",
    });
    return { ok: true, obj, sha: null, error: null, fromBundle: true };
  } catch (e) {
    return r;
  }
}

function buildUploads(current, known /* Map norm->entry */, nowIsoStr, prevUploads) {
  const out = prevUploads.slice();
  const seen = new Set(prevUploads.map((u) => normTitle(u.title)));
  const fresh = [];
  for (const t of current) {
    const n = normTitle(t.title);
    if (seen.has(n)) continue;
    const entry = {
      title: t.title,
      uploaded_at: t.upload_date || null,
      url: t.url || null,
      first_seen_at: nowIsoStr,
    };
    out.push(entry);
    fresh.push(entry);
    seen.add(n);
  }
  // prune entries older than the retention window (git history keeps all)
  const cutoff = Date.parse(nowIsoStr) - UPLOADS_DAYS * 86400000;
  const pruned = out.filter((u) => {
    const t = Date.parse(u.first_seen_at || "");
    return !Number.isFinite(t) || t >= cutoff;
  });
  return { uploads: pruned, newUploads: fresh };
}

function buildSnapshotRow(tracks, nowIsoStr) {
  const valid = tracks.filter((t) => Number.isFinite(t.plays));
  const top = valid
    .slice()
    .sort((a, b) => b.plays - a.plays || (a.title < b.title ? -1 : 1))
    .slice(0, 20)
    .map((t) => ({ title: t.title, plays: t.plays }));
  return {
    snapshot_at: nowIsoStr,
    total_plays: valid.reduce((s, t) => s + t.plays, 0),
    tracks_captured: valid.length,
    top,
  };
}

/* ---- handler ---- */

/* SoundCloud pull (independent of the state reads, so the handler runs it
 * concurrently with them to stay inside the 10s budget). */
async function pullSoundCloud(upstream) {
  let clientId = (process.env.SOUNDCLOUD_CLIENT_ID || "").trim();
  let userId = null;
  let via = null;
  if (clientId) {
    upstream.push({ source: "sc-client-id", ok: true, checked_at: nowIso(), latency_ms: 0 });
    const v = await fetchTimeout(
      API_V2 + "/resolve?url=" + encodeURIComponent(PROFILE_URL) + "&client_id=" + encodeURIComponent(clientId),
      { timeoutMs: FETCH_MS, userAgent: UA }
    );
    const e = { source: "sc-resolve", ok: v.ok, checked_at: nowIso(), latency_ms: v.ms };
    if (!v.ok) { e.error = v.error; log("[upstream] sc-resolve fail error=" + v.error); }
    else {
      try { userId = JSON.parse(v.text).id || null; }
      catch (ex) { e.ok = false; e.error = "resolve unparseable"; }
    }
    upstream.push(e);
    via = "env";
  } else {
    const got = await extractClientId(upstream);
    if (got) { clientId = got.clientId; userId = got.userId; via = got.via; }
  }
  let tracks = null;
  if (clientId && userId) tracks = await fetchTracks(clientId, userId, upstream);
  return { clientId, userId, via, tracks };
}

module.exports = async (req, res) => {
  const requestId = require("../../lib/envelope").newRequestId();
  log("[cron] signal start request_id=" + requestId);

  if (req.method !== "GET") {
    res.statusCode = 405;
    res.setHeader("Allow", "GET");
    res.end("Method Not Allowed");
    return;
  }

  // 60s duplicate-delivery cooldown (§4.3)
  const prev = lastRunAt.get("signal") || 0;
  if (Date.now() - prev < COOLDOWN_MS) {
    log("[cron] signal duplicate suppressed request_id=" + requestId);
    ok(res, SERVICE, VERSION,
      { checked: 0, changed: false, committed: false, duplicate: true, tracks_captured: null, new_uploads: [] },
      { source: "live", degraded: false, cache: "none", note: "Duplicate cron delivery suppressed (60s cooldown)." });
    return;
  }
  lastRunAt.set("signal", Date.now());

  const auth = assertCron(req, "signal");
  if (!auth.ok) {
    err(res, SERVICE, VERSION, 401, "UNAUTHORIZED",
      auth.reason === "missing-secret"
        ? "CRON_SECRET is not configured, so the refresh cannot run. Set it in the Vercel dashboard (Production scope)."
        : "The Authorization bearer token did not match CRON_SECRET.",
      { job: "signal" });
    return;
  }

  const upstream = [];
  const now = nowIso();
  let changed = false;
  let degraded = false;
  let note = null;
  let readOnlyFlag = false;
  const commitShas = {};

  try {
    // 1+2. state reads and SoundCloud pull run CONCURRENTLY (10s budget).
    // GitHub is the source of truth (§4.2); deployment-bundle fallback covers
    // the bootstrap window (files committed locally but not yet pushed).
    // data/playcounts.snapshot.json is bundle-only: the wave engine owns it;
    // the cron only rewrites it on a real change.
    const [reads, sc] = await Promise.all([
      Promise.all([
        readState("api/v1/uploads.json", upstream),
        readState("api/v1/stats-snapshots.json", upstream),
        readState("api/v1/refresh-status.json", upstream),
        readState("data/playcounts.snapshot.json", upstream),
      ]),
      pullSoundCloud(upstream),
    ]);
    const [uploadsR, snapsR, statusR, snapFileR] = reads;
    const { clientId, userId, via, tracks } = sc;
    upstream.push({
      source: "github-contents-read", ok: uploadsR.ok && snapsR.ok && statusR.ok,
      checked_at: nowIso(),
      ...(uploadsR.ok && snapsR.ok && statusR.ok ? {} : { error: [uploadsR.error, snapsR.error, statusR.error].filter(Boolean).join("; ") || "read failed" }),
    });
    const prevUploads = uploadsR.ok && Array.isArray(uploadsR.obj.uploads) ? uploadsR.obj.uploads : [];
    const prevSnaps = snapsR.ok && Array.isArray(snapsR.obj.snapshots) ? snapsR.obj.snapshots : [];

    // (SoundCloud pull ran concurrently above as pullSoundCloud().)
    if (!clientId) {
      degraded = true;
      note = "No SoundCloud client_id available (no SOUNDCLOUD_CLIENT_ID and webapp extraction failed); no fresh counts this run.";
    }

    let tracksCaptured = null;
    let newUploads = [];

    if (tracks && tracks.length) {
      const valid = tracks.filter((t) => Number.isFinite(t.plays));
      tracksCaptured = valid.length;
      const skipped = tracks.length - valid.length;

      // 3. merge
      const merged = buildUploads(tracks, null, now, prevUploads);
      newUploads = merged.newUploads;
      const uploadsDoc = { generated_at: now, uploads: merged.uploads };

      const row = buildSnapshotRow(tracks, now);
      const cutoff = Date.parse(now) - SNAPSHOT_DAYS * 86400000;
      const snaps = prevSnaps
        .filter((r) => Number.isFinite(Date.parse(r.snapshot_at || "")) && Date.parse(r.snapshot_at) >= cutoff)
        .concat([row]);
      const snapsDoc = { generated_at: now, retention_days: SNAPSHOT_DAYS, snapshots: snaps };

      const statusDoc = {
        last_attempt: now,
        status: "ok",
        source: "soundcloud api-v2",
        client_id_source: via,
        snapshot_at: now,
        tracks_captured: tracksCaptured,
        tracks_skipped_no_count: skipped,
      };
      const snapshotDoc = {
        snapshot_at: now,
        source: "soundcloud api-v2",
        profile: PROFILE_URL,
        tracks: valid.map((t) => ({ title: t.title, upload_date: t.upload_date, plays: t.plays })),
        tracks_captured: tracksCaptured,
        tracks_skipped_no_count: skipped,
        client_id_source: via,
      };

      // 4. commit-back (read-only degrade without the PAT — see lib/github.js).
      // knownCurrent skips the pre-write re-read: step 1 already read state.
      const msg = "Signal: play-count refresh " + now.slice(0, 10) +
        " (" + tracksCaptured + " tracks" + (newUploads.length ? ", " + newUploads.length + " new upload(s)" : "") + ")";
      const writes = await Promise.all([
        writeJsonIfChanged("api/v1/uploads.json", uploadsDoc, msg, UA, uploadsR.ok ? uploadsR.obj : undefined),
        writeJsonIfChanged("api/v1/stats-snapshots.json", snapsDoc, msg, UA, snapsR.ok ? snapsR.obj : undefined),
        writeJsonIfChanged("api/v1/refresh-status.json", statusDoc, msg, UA, statusR.ok ? statusR.obj : undefined),
        writeJsonIfChanged("data/playcounts.snapshot.json", snapshotDoc, msg, UA, snapFileR.ok ? snapFileR.obj : undefined),
      ]);
      const files = ["uploads.json", "stats-snapshots.json", "refresh-status.json", "playcounts.snapshot.json"];
      writes.forEach((w, i) => {
        if (w.changed) changed = true;
        if (w.committed) commitShas[files[i]] = w.sha;
        if (w.reason === "no-token-readonly") readOnlyFlag = true;
      });

      if (readOnlyFlag) {
        degraded = true;
        note = (note ? note + " " : "") +
          "GITHUB_REPO_TOKEN is pending the user's decision, so this run was read-only: " +
          tracksCaptured + " tracks were read fresh from SoundCloud and are reported here, " +
          "but nothing was persisted. Static JSON still updates via the wave engine's pushes.";
      }
    } else {
      degraded = true;
      tracksCaptured = (statusR.ok && Number(statusR.obj.tracks_captured)) || null;
      note = (note ? note + " " : "") +
        "SoundCloud was unreachable this run; nothing changed. Last good data stands.";
    }

    const sourcesOk = upstream.filter((u) => u.ok).length;
    log("[cron] signal done changed=" + changed +
      " committed=" + (Object.keys(commitShas).length ? JSON.stringify(commitShas) : "false") +
      " sources_ok=" + sourcesOk + "/" + upstream.length +
      " tracks=" + tracksCaptured + " new_uploads=" + newUploads.length +
      " request_id=" + requestId);

    ok(res, SERVICE, VERSION,
      {
        checked: upstream.length,
        changed,
        committed: Object.keys(commitShas).length > 0,
        commit_shas: commitShas,
        tracks_captured: tracksCaptured,
        new_uploads: newUploads.map((u) => ({ title: u.title, uploaded_at: u.uploaded_at, url: u.url, first_seen_at: u.first_seen_at })),
        read_only: !!readOnlyFlag,
      },
      {
        source: "live",
        degraded,
        stale_since: degraded ? now : null,
        upstream,
        note,
        cache: "none",
      });
  } catch (e) {
    log("[cron] signal fail stage=" + (e.stage || "unknown") + " error=" + e.message + " request_id=" + requestId);
    err(res, SERVICE, VERSION, 500, "REFRESH_FAILED",
      "The Signal refresh failed partway through. Nothing was half-written; the next scheduled run picks it up.",
      { stage: e.stage || "unknown" });
  }
};
