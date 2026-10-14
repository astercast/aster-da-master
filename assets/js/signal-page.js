/* assets/js/signal-page.js — The Signal 2.0 page wiring.
 *
 * Progressive enhancement over the pre-rendered watch log and date board:
 * the HTML ships with the full static content. On load the live /api/watch
 * payload is tried first (static watch file as fallback); live answers
 * repaint the summary, movers and date board, anything else leaves the
 * pre-rendered page standing and the badge says which happened.
 *
 * Countdown chips ("in 3 days") are computed from each event's own date
 * against the reader's calendar — presentation only, never stored.
 * Titles, dates, counts and venues only.
 */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Display normalization (rotation 22): third-party strings carried
     in the data files (listing titles, source labels, sweep notes)
     are shown with commas where the stored record uses an em dash.
     The stored records are never rewritten; this is display only. */
  function disp(s) {
    return String(s == null ? "" : s).replace(/ \u2014 /g, ", ");
  }

  function fmt(n) {
    var v = Number(n);
    return Number.isFinite(v) ? v.toLocaleString("en-US") : "n/a";
  }

  function fmtDay(iso) {
    var m = /^(\d{4}-\d{2}-\d{2})/.exec(String(iso || ""));
    return m ? m[1] : "";
  }

  /* ---- countdown chips ---- */
  function paintWhen(root) {
    var now = new Date();
    var today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    Array.prototype.forEach.call(root.querySelectorAll("[data-when]"), function (el) {
      var parts = String(el.getAttribute("data-when") || "").split("-");
      if (parts.length !== 3) return;
      var t = Date.UTC(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
      var days = Math.round((t - today) / 86400000);
      el.textContent =
        days === 0 ? "today" :
        days === 1 ? "tomorrow" :
        days > 1 ? "in " + days + " days" :
        days === -1 ? "yesterday" :
        Math.abs(days) + " days ago";
    });
  }

  /* ---- watch log repaint (live data only) ---- */
  function paintWatch(d) {
    if (!d || !d.summary) return;
    var s = d.summary;
    function set(key, val) {
      Array.prototype.forEach.call(document.querySelectorAll('[data-watch="' + key + '"]'),
        function (el) { el.textContent = val; });
    }
    set("tracks", fmt(s.tracks_watched));
    set("plays", fmt(s.total_plays));
    set("new", fmt(s.new_uploads));
    if (s.newest_upload) set("newest", fmtDay(s.newest_upload.uploaded_at) || "n/a");

    if (Array.isArray(d.new_uploads)) {
      var box = document.getElementById("watch-new");
      if (box && d.new_uploads.length) {
        box.innerHTML = '<ul class="fact-list">' + d.new_uploads.map(function (u) {
          var inner = esc(u.title) + ", uploaded " + esc(fmtDay(u.uploaded_at) || "date unrecorded");
          if (u.url) inner = '<a href="' + esc(u.url) + '" target="_blank" rel="noopener">' + inner + "</a>";
          return "<li>" + inner + "</li>";
        }).join("") + "</ul>";
      }
    }

    if (Array.isArray(d.movers)) {
      /* Rotation 22 (§8.4): movers are log lines now, not table rows.
         The line carries the same facts in the log's order: the
         title, the before and after counts, the change as the line's
         appended fact, the per-day rate. */
      var list = document.getElementById("watch-movers");
      if (list) {
        list.innerHTML = d.movers.map(function (m) {
          return "<li>" + esc(m.title) + " · " + fmt(m.before) + " to " + fmt(m.after) +
            ' · <span class="watch-delta">' + (m.delta > 0 ? "+" : "") + fmt(m.delta) + " plays</span>" +
            (m.per_day === null || m.per_day === undefined ? "" : " · " + fmt(m.per_day) + " per day") + "</li>";
        }).join("");
      }
    }

    var fresh = document.getElementById("watch-fresh");
    if (fresh) {
      var f = d.freshness || {};
      var gen = fmtDay(f.generated_at || d.generated_at);
      fresh.textContent = f.status === "stale"
        ? "Watch file from " + (gen || "an unknown date") + ", past its 24-hour window; the latest verified captures stand below, not a live feed."
        : "Watch file generated " + (gen || "at an unknown time") + " · live dates last swept " +
          (fmtDay(f.live_dates_checked_at) || "2026-10-12") + ".";
    }
  }

  /* ---- date-board repaint (rotation 22, §8.4) ----
     The board is a broadcast schedule grouped by day: a day heading,
     then the day's entries. An entry's title line carries its state
     as a brace word inside the line; the countdown stays a plain
     word; the bill, the note, the open conflicts and the sources
     print under the line in prose. No cards. */
  function entryHtml(ev) {
    var state = ev.status === "verified" ? "{VERIFIED}" : "{SINGLE-SOURCE}";
    var meta = [ev.weekday + ", " + ev.date, ev.time, ev.venue, ev.address || ev.city, ev.price]
      .filter(Boolean).map(function (x) { return esc(disp(x)); }).join(" · ");
    var bill = ev.bill && ev.bill.length > 2 ? '<p class="date-meta">Bill: ' + ev.bill.map(function (x) { return esc(disp(x)); }).join(", ") + "</p>" : "";
    var disc = (ev.discrepancies || []).map(function (x) {
      return '<p class="date-disc">Open conflict: ' + esc(disp(x)) + "</p>";
    }).join("");
    var srcs = (ev.sources || []).map(function (s) {
      return '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(disp(s.label)) + "</a>";
    }).join(" · ");
    return '<article class="sched-entry"><h2>' + esc(disp(ev.artist)) + ", " + esc(disp(ev.title)) +
      ' <span class="line-state">' + state + '</span>' +
      ' <span class="when-word" data-when="' + esc(ev.date) + '"></span></h2>' +
      '<p class="date-meta">' + meta + "</p>" + bill +
      '<p class="date-note">' + esc(disp(ev.note)) + "</p>" + disc +
      '<p class="date-meta">Sources: ' + srcs + "</p></article>";
  }

  function dayHeading(ev) {
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var p = String(ev.date || "").split("-");
    var pretty = p.length === 3 ? months[Number(p[1]) - 1] + " " + Number(p[2]) + ", " + p[0] : ev.date;
    return esc(ev.weekday) + ", " + esc(pretty);
  }

  function paintDates(doc) {
    var board = document.getElementById("date-board");
    if (!board || !doc || !Array.isArray(doc.events)) return;
    var html = "", lastDay = null;
    doc.events.forEach(function (ev) {
      if (ev.date !== lastDay) {
        if (lastDay !== null) html += "</section>";
        html += '<section class="sched-day"><h3 class="sched-day-h">' + dayHeading(ev) + "</h3>";
        lastDay = ev.date;
      }
      html += entryHtml(ev);
    });
    if (lastDay !== null) html += "</section>";
    board.innerHTML = html;
    paintWhen(board);
  }

  /* ---- wire-up ---- */
  paintWhen(document);

  var badge = document.getElementById("watch-badge");
  if (badge && window.ApiClient) {
    window.ApiClient.fetchWithFallback("/api/watch", "data/v1/signal-watch.json", { badgeEl: badge })
      .then(function (r) {
        if (!r) return;
        if (r.source === "none") {
          badge.textContent = "signal lost";
          badge.title = "The live server and the static watch file both failed: the pre-rendered page stands.";
          return;
        }
        if (r.source === "live") paintWatch(r.data);
      });
  }

  if (window.fetch) {
    fetch("data/v1/live-dates.json", { cache: "force-cache" })
      .then(function (r) { if (!r.ok) throw new Error("dates " + r.status); return r.json(); })
      .then(paintDates)
      .catch(function () { /* pre-rendered board stands */ });
  }
})();
