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

  /* "2026-10-11T22:11:31Z" → "4h ago" / "2d ago" / "just now".
     Computed from the response's own timestamps, never the wall clock. */
  function relTime(iso) {
    var t = Date.parse(iso);
    if (!Number.isFinite(t)) return "";
    var s = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (s < 90) return "just now";
    var m = Math.floor(s / 60);
    if (m < 90) return m + "m ago";
    var h = Math.floor(m / 60);
    if (h < 48) return h + "h ago";
    return Math.floor(h / 24) + "d ago";
  }

  /* Freshness readout for [data-signal-fresh="stats"|"uploads"] hooks: an
     honest "last checked" line next to the badge. Every timestamp comes from
     the API response or the static fallback file — never invented. */
  function paintFreshness(kind, r) {
    var nodes = document.querySelectorAll('[data-signal-fresh="' + kind + '"]');
    if (!nodes.length) return;
    var text;
    if (!r || r.source === "none") {
      text = "Signal lost — the archive stands on its static numbers.";
    } else {
      var d = r.data || {};
      var f = d.freshness || {};
      var checked = relTime(f.checked_at || r.generatedAt);
      var checkedTxt = checked ? "Checked " + checked : "Checked at an unknown time";
      if (kind === "stats") {
        var snap = fmtDay(f.snapshot_at) || fmtDay(r.generatedAt);
        text = checkedTxt + " · play counts from " + (snap || "the last snapshot") +
          (f.status === "stale" ? " (stale — latest verified capture)" : "");
      } else {
        var newest = fmtDay(d.newest_upload_at);
        text = checkedTxt + (newest ? " · newest upload on record " + newest : "");
      }
    }
    Array.prototype.forEach.call(nodes, function (el) { el.textContent = text; });
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

  /* Wire a stats badge + live number refresh for the numbers surfaces.
     On total failure (live AND static unreachable) the badge says "signal
     lost" instead of hiding — the page keeps its pre-rendered numbers and
     says so, per the honesty contract. */
  function wireStats(badgeId) {
    var badge = badgeId && document.getElementById(badgeId);
    if (!badge || !window.ApiClient) return;
    window.ApiClient.fetchWithFallback("/api/stats", "data/v1/stats-snapshots.json", { badgeEl: badge })
      .then(function (r) {
        if (!r) { paintFreshness("stats", null); return; }
        if (r.source === "none") {
          badge.textContent = "signal lost";
          badge.title = "The live server and the static file both failed — the page keeps its pre-rendered numbers.";
        } else if (r.source === "live") {
          var d = statsPayload(r);
          if (d) paintStats(d);
        }
        paintFreshness("stats", r);
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
      if (!r) { paintFreshness("uploads", null); return; }
      if (r.source === "none") {
        badge.textContent = "signal lost";
        badge.title = "The live server and the static file both failed — the pre-rendered list stands.";
      } else if (r.source === "live" && list) {
        var ups = uploadsPayload(r).slice(0, 5);
        if (ups.length) {
          list.innerHTML = ups.map(function (u) {
            var date = u.uploaded_at || fmtDay(u.first_seen_at);
            var inner = '<span class="dim">' + esc(date) + '</span> ' + esc(u.title);
            if (u.url) inner = '<a href="' + esc(u.url) + '" target="_blank" rel="noopener">' + inner + "</a>";
            return "<li>" + inner + "</li>";
          }).join("");
        }
        /* nothing new — the featured release stands */
      }
      paintFreshness("uploads", r);
    });
  }

  window.Signal = { wireStats: wireStats, wireUploads: wireUploads };
})();
