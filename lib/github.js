/* github.js — the repo is the database (§5).
 * Identical across all 7 repos; do not fork.
 *
 * READ-ONLY DEGRADATION (pending user decision, 2026-10-11):
 * The cron commit-back path needs a fine-grained PAT (contents:write on this
 * repo only) stored as GITHUB_REPO_TOKEN. That token is still pending the
 * user's decision. Until it exists:
 *   - readJson() still works: it reads via the unauthenticated raw file
 *     endpoint (the repo is public), so jobs can always see current state.
 *   - writeJsonIfChanged() returns {committed:false, reason:'no-token-readonly'}
 *     and NEVER attempts a write. Cron jobs degrade to read-only: they
 *     compute fresh data, return it in their response envelope, and leave
 *     persistence to the wave engine's pushes. Nothing is faked, nothing is
 *     half-written. See spec §14 open decision 1.
 */
"use strict";

const { fetchTimeout } = require("./fetchx");

const API = process.env.GITHUB_API || "https://api.github.com";
const REPO = process.env.GITHUB_REPO || "astercast/aster-da-master";
const PREFIX = process.env.REPO_STATIC_PREFIX || ""; // '' for root-served repos, 'site/' otherwise
const TIMEOUT = 8000;

function token() {
  return (process.env.GITHUB_REPO_TOKEN || "").trim();
}

function contentsUrl(repoPath) {
  const p = PREFIX + repoPath;
  return API + "/repos/" + REPO + "/contents/" + encodeURIComponent(p).replace(/%2F/g, "/");
}

function rawUrl(repoPath) {
  const p = PREFIX + repoPath;
  return "https://raw.githubusercontent.com/" + REPO + "/main/" + p;
}

function canonical(obj) {
  return JSON.stringify(sortKeys(obj), null, 2) + "\n";
}

function sortKeys(v) {
  if (Array.isArray(v)) return v.map(sortKeys);
  if (v && typeof v === "object") {
    const out = {};
    for (const k of Object.keys(v).sort()) out[k] = sortKeys(v[k]);
    return out;
  }
  return v;
}

function sha256(s) {
  return require("crypto").createHash("sha256").update(s, "utf8").digest("hex");
}

/* Read a JSON file from the repo. Authenticated when the token exists
 * (higher rate limit); falls back to the unauthenticated raw endpoint.
 * @returns {Promise<{ok, obj, sha, error}>} */
async function readJson(repoPath, userAgent) {
  const t = token();
  if (t) {
    const r = await fetchTimeout(contentsUrl(repoPath), {
      timeoutMs: TIMEOUT,
      userAgent,
      headers: {
        Authorization: "Bearer " + t,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
    });
    if (!r.ok) return { ok: false, obj: null, sha: null, error: "contents api: " + r.error };
    try {
      const body = JSON.parse(r.text);
      return {
        ok: true,
        obj: JSON.parse(Buffer.from(body.content || "", "base64").toString("utf8")),
        sha: body.sha || null,
        error: null,
      };
    } catch (e) {
      return { ok: false, obj: null, sha: null, error: "contents decode: " + e.message };
    }
  }
  const r = await fetchTimeout(rawUrl(repoPath), { timeoutMs: TIMEOUT, userAgent });
  if (!r.ok) return { ok: false, obj: null, sha: null, error: "raw: " + r.error };
  try {
    return { ok: true, obj: JSON.parse(r.text), sha: null, error: null };
  } catch (e) {
    return { ok: false, obj: null, sha: null, error: "raw parse: " + e.message };
  }
}

/* Write JSON only when the canonical bytes differ. On SHA conflict, re-read
 * once and retry once, then report conflict. Never force-push, never delete.
 * knownCurrent (optional): the already-read current file content — skips the
 * pre-write re-read for the change comparison (the cron already read state).
 * @returns {Promise<{committed, sha, changed, reason?}>} */
async function writeJsonIfChanged(repoPath, obj, message, userAgent, knownCurrent) {
  const canon = canonical(obj);
  const digest = sha256(canon);
  const sameAs = (cur) => {
    try { return sha256(canonical(cur)) === digest; } catch (e) { return false; }
  };
  const READONLY_NOTE =
    "GITHUB_REPO_TOKEN (fine-grained PAT, contents:write) is pending the user's " +
    "decision — running read-only; static JSON updates via wave-engine pushes only.";

  const readWithToken = async () => {
    const t = token();
    const r = await fetchTimeout(contentsUrl(repoPath), {
      timeoutMs: TIMEOUT,
      userAgent,
      headers: {
        Authorization: "Bearer " + t,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
    });
    if (r.status === 404) return { exists: false, sha: null, same: false };
    if (!r.ok) throw new Error("contents read: " + r.error);
    const body = JSON.parse(r.text);
    const current = Buffer.from(body.content || "", "base64").toString("utf8");
    return { exists: true, sha: body.sha, same: sha256(canonical(JSON.parse(current))) === digest };
  };

  if (!token()) {
    // PENDING-TOKEN path: compute change-ness without writing and without
    // any extra network when the caller already read the current file.
    let changed;
    if (knownCurrent !== undefined) {
      changed = !sameAs(knownCurrent);
    } else {
      const cur = await readJson(repoPath, userAgent);
      changed = !cur.ok || !sameAs(cur.obj);
    }
    return { committed: false, sha: null, changed, reason: "no-token-readonly", note: READONLY_NOTE };
  }

  const put = async (sha) => {
    const t = token();
    const payload = { message, content: Buffer.from(canon, "utf8").toString("base64") };
    if (sha) payload.sha = sha;
    // DATAOPS-003 fix (2026-10-15): the payload MUST ride as the request
    // body. It was previously built and then dropped — the PUT went out
    // empty, GitHub answered 422 ("content" wasn't supplied), and every
    // cron commit-back failed silently behind an HTTP 200 envelope.
    return fetchTimeout(contentsUrl(repoPath), {
      timeoutMs: TIMEOUT,
      userAgent,
      method: "PUT",
      body: JSON.stringify(payload),
      headers: {
        Authorization: "Bearer " + t,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
      },
    });
  };

  try {
    const cur = await readWithToken();
    if (cur.same) return { committed: false, sha: cur.sha, changed: false };
    let r = await put(cur.sha);
    if (r.status === 409 || (r.text || "").includes("does not match")) {
      // One re-read + one retry, then give up honestly.
      const again = await readWithToken();
      if (again.same) return { committed: false, sha: again.sha, changed: false };
      r = await put(again.sha);
      if (r.status === 409 || !r.ok) {
        return { committed: false, sha: null, changed: true, reason: "conflict" };
      }
    }
    if (!r.ok) return { committed: false, sha: null, changed: true, reason: "write-failed", error: r.error };
    const body = JSON.parse(r.text);
    return { committed: true, sha: (body.content && body.content.sha) || null, changed: true };
  } catch (e) {
    return { committed: false, sha: null, changed: true, reason: "write-error", error: e.message };
  }
}

module.exports = { readJson, writeJsonIfChanged, canonical, REPO, PREFIX };
