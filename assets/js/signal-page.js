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

  function fmt(n) {
    var v = Number(n);
    return Number.isFinite(v) ? v.toLocaleString("en-US") : "—";
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
    if (s.newest_upload) set("newest", fmtDay(s.newest_upload.uploaded_at) || "—");

    if (Array.isArray(d.new_uploads)) {
      var box = document.getElementById("watch-new");
      if (box && d.new_uploads.length) {
        box.innerHTML = '<ul class="fact-list">' + d.new_uploads.map(function (u) {
          var inner = esc(u.title) + " — uploaded " + esc(fmtDay(u.uploaded_at) || "date unrecorded");
          if (u.url) inner = '<a href="' + esc(u.url) + '" target="_blank" rel="noopener">' + inner + "</a>";
          return "<li>" + inner + "</li>";
        }).join("") + "</ul>";
      }
    }

    if (Array.isArray(d.movers)) {
      var tbl = document.getElementById("watch-movers");
      var body = tbl && tbl.querySelector("tbody");
      if (body) {
        body.innerHTML = d.movers.map(function (m) {
          return "<tr><td>" + esc(m.title) + '</td><td class="num">' + fmt(m.before) +
            '</td><td class="num">' + fmt(m.after) + '</td><td class="num watch-delta">' +
            (m.delta > 0 ? "+" : "") + fmt(m.delta) + '</td><td class="num">' +
            (m.per_day === null || m.per_day === undefined ? "—" : fmt(m.per_day)) + "</td></tr>";
        }).join("");
      }
    }

    var fresh = document.getElementById("watch-fresh");
    if (fresh) {
      var f = d.freshness || {};
      var gen = fmtDay(f.generated_at || d.generated_at);
      fresh.textContent = f.status === "stale"
        ? "Watch file from " + (gen || "an unknown date") + " — past its 24-hour window; the latest verified captures stand below, not a live feed."
        : "Watch file generated " + (gen || "at an unknown time") + " · live dates last swept " +
          (fmtDay(f.live_dates_checked_at) || "2026-10-12") + ".";
    }
  }

  /* ---- date-board repaint (from the static research file) ---- */
  function cardHtml(ev) {
    var chip = ev.status === "verified"
      ? '<span class="watch-chip is-verified">Verified</span>'
      : '<span class="watch-chip is-single">Single-source</span>';
    var meta = [ev.weekday + ", " + ev.date, ev.time, ev.venue, ev.address || ev.city, ev.price]
      .filter(Boolean).map(esc).join(" · ");
    var bill = ev.bill && ev.bill.length > 2 ? '<p class="date-meta">Bill: ' + ev.bill.map(esc).join(", ") + "</p>" : "";
    var disc = (ev.discrepancies || []).map(function (x) {
      return '<p class="date-disc">Open conflict: ' + esc(x) + "</p>";
    }).join("");
    var srcs = (ev.sources || []).map(function (s) {
      return '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.label) + "</a>";
    }).join(" · ");
    return '<article class="date-card"><h4>' + esc(ev.artist) + " — " + esc(ev.title) + " " + chip +
      ' <span class="watch-chip is-when" data-when="' + esc(ev.date) + '"></span></h4>' +
      '<p class="date-meta">' + meta + "</p>" + bill +
      '<p class="date-note">' + esc(ev.note) + "</p>" + disc +
      '<p class="date-meta">Sources: ' + srcs + "</p></article>";
  }

  function paintDates(doc) {
    var board = document.getElementById("date-board");
    if (!board || !doc || !Array.isArray(doc.events)) return;
    board.innerHTML = doc.events.map(cardHtml).join("");
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
          badge.title = "The live server and the static watch file both failed — the pre-rendered page stands.";
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
