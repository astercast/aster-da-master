/* assets/js/signal.js — The Signal frontend wiring (Vercel Wave B).
 *
 * Progressive enhancement over pre-rendered static numbers (ARCHITECTURE.md §3):
 * every widget ships with its static data already in the HTML. On load, the
 * live function is tried first (7s timeout); on success the fresh numbers
 * swap in, otherwise the static data stands and the badge says so honestly.
 *
 * Requires window.ApiClient (assets/js/api-client.js) — no-ops without it,
 * so a blocked or missing script can never break the page.
 *
 * The Signal deals in numbers only: play counts, track counts, upload titles
 * and dates. No content, no lyrics, no bio facts.
 */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmt(n) {
    var v = Number(n);
    return Number.isFinite(v) ? v.toLocaleString("en-US") : "—";
  }

  /* "2026-10-11T22:11:31Z" → "2026-10-11". Honest data timestamp, never "now". */
  function fmtDay(iso) {
    if (!iso) return "";
    var m = /^(\d{4}-\d{2}-\d{2})/.exec(String(iso));
    return m ? m[1] : "";
  }

  /* Normalize the two shapes fetchWithFallback can return:
   *  - live:  envelope data {tracks_captured, total_plays, snapshot_at, top_tracks, ...}
   *  - static: data/v1/stats-snapshots.json {snapshots:[{snapshot_at,total_plays,tracks_captured,top}]}
   * Returns the latest row, or null when neither carries real numbers. */
  function statsPayload(r) {
    var d = (r && r.data) || {};
    if (Array.isArray(d.snapshots) && d.snapshots.length) {
      d = d.snapshots.slice().sort(function (a, b) {
        return (a.snapshot_at || "") < (b.snapshot_at || "") ? -1 : 1;
      })[d.snapshots.length - 1];
    }
    if (typeof d.total_plays !== "number") return null;
    return d;
  }

  /* Paint fresh numbers into [data-signal] hooks. Called ONLY with live data —
   * cached/static results keep the pre-rendered numbers (§3: the badge is the
   * honesty mechanism, not a repaint). */
  function paintStats(d) {
    var nodes = document.querySelectorAll('[data-signal="plays"]');
    Array.prototype.forEach.call(nodes, function (el) {
      el.textContent = fmt(d.total_plays);
      /* keep any count-up target honest: the live total replaces the static one */
      var cell = el.closest ? el.closest("[data-count]") : null;
      if (cell) cell.setAttribute("data-count", String(d.total_plays));
    });
    nodes = document.querySelectorAll('[data-signal="tracks"]');
    Array.prototype.forEach.call(nodes, function (el) { el.textContent = fmt(d.tracks_captured); });
    nodes = document.querySelectorAll('[data-signal="snapshot"]');
    var day = fmtDay(d.snapshot_at);
    Array.prototype.forEach.call(nodes, function (el) { if (day) el.textContent = day; });
    /* Per-track refresh for the glance top-5: exact title match only;
     * any title the live feed doesn't carry keeps its static count. */
    if (Array.isArray(d.top_tracks)) {
      var map = {};
      d.top_tracks.forEach(function (t) {
        if (t && typeof t.title === "string") map[t.title] = t.plays;
      });
      nodes = document.querySelectorAll("[data-signal-top]");
      Array.prototype.forEach.call(nodes, function (el) {
        var t = el.getAttribute("data-signal-top");
        if (Object.prototype.hasOwnProperty.call(map, t)) {
          el.textContent = fmt(map[t]) + " plays";
        }
      });
    }
  }

  /* Wire a stats badge + live number refresh for the numbers surfaces. */
  function wireStats(badgeId) {
    var badge = badgeId && document.getElementById(badgeId);
    if (!badge || !window.ApiClient) return;
    window.ApiClient.fetchWithFallback("/api/stats", "data/v1/stats-snapshots.json", { badgeEl: badge })
      .then(function (r) {
        if (!r || r.source !== "live") return; /* cached: static numbers stand */
        var d = statsPayload(r);
        if (d) paintStats(d);
      });
  }

  /* Normalize uploads payloads:
   *  - live:  envelope data {since, count, uploads:[{title,uploaded_at,url,first_seen_at}]}
   *  - static: data/v1/uploads.json {generated_at, note, uploads:[...]}
   * Returns the list newest-first (both shapes already carry newest-first
   * or get sorted), filtered to rows with real titles. */
  function uploadsPayload(r) {
    var d = (r && r.data) || {};
    var list = Array.isArray(d.uploads) ? d.uploads : [];
    return list
      .filter(function (u) { return u && typeof u.title === "string"; })
      .slice()
      .sort(function (a, b) {
        var ta = Date.parse(a.uploaded_at || a.first_seen_at || "") || 0;
        var tb = Date.parse(b.uploaded_at || b.first_seen_at || "") || 0;
        return tb - ta || (a.title < b.title ? -1 : 1);
      });
  }

  /* Wire the "fresh uploads" badge + list. On live data the list is repainted
   * with the newest uploads; on cached/static the pre-rendered list stands. */
  function wireUploads(badgeId, listId) {
    var badge = badgeId && document.getElementById(badgeId);
    var list = listId && document.getElementById(listId);
    if (!badge || !window.ApiClient) return;
    window.ApiClient.fetchWithFallback(
      "/api/uploads?since=2025-01-01&limit=5", "data/v1/uploads.json", { badgeEl: badge }
    ).then(function (r) {
      if (!r || r.source !== "live" || !list) return;
      var ups = uploadsPayload(r).slice(0, 5);
      if (!ups.length) return; /* nothing new — featured release stands */
      list.innerHTML = ups.map(function (u) {
        var date = u.uploaded_at || fmtDay(u.first_seen_at);
        var inner = '<span class="dim">' + esc(date) + '</span> ' + esc(u.title);
        if (u.url) inner = '<a href="' + esc(u.url) + '" target="_blank" rel="noopener">' + inner + "</a>";
        return "<li>" + inner + "</li>";
      }).join("");
    });
  }

  window.Signal = { wireStats: wireStats, wireUploads: wireUploads };
})();
