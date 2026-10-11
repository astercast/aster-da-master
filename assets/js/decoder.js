/* Transmission decoder — codex-powered word search across all titles.
   Mirrors scripts/build_codex.py: lowercase + leet-normalize, word-boundary
   matching, multi-word phrases. Reports matching tracks and codex family. */
(function () {
  "use strict";

  var LEET = { "1": "l", "0": "o", "3": "e", "4": "a", "5": "s", "7": "t" };

  function norm(s) {
    return String(s == null ? "" : s).toLowerCase().replace(/[103457]/g, function (c) {
      return LEET[c] || c;
    });
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function escRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function fmt(n) {
    return Number(n).toLocaleString("en-US");
  }

  var DATA = null;
  var CODEX = null;

  function load() {
    return Promise.all([
      fetch("data/artist.json").then(function (r) {
        if (!r.ok) throw new Error("artist");
        return r.json();
      }),
      fetch("data/codex.json").then(function (r) {
        if (!r.ok) throw new Error("codex");
        return r.json();
      })
    ]).then(function (pair) {
      DATA = pair[0];
      CODEX = pair[1];
    });
  }

  function decode(word) {
    var q = norm(word.trim());
    if (!q) return null;
    var re = new RegExp("\\b" + escRe(q) + "\\b");
    var hits = (DATA.discography || []).filter(function (r) {
      return re.test(norm(r.title));
    }).sort(function (a, b) {
      return (b.plays || 0) - (a.plays || 0);
    });
    var families = (CODEX.families || []).filter(function (f) {
      return (f.words || []).some(function (w) { return norm(w) === q; });
    });
    return { q: q, raw: word.trim(), hits: hits, families: families };
  }

  function render(res, out) {
    if (!res) {
      out.innerHTML = '<p class="dec-empty">Speak a word first.</p>';
      return;
    }
    var html = '<p class="kicker"><span class="numeral">✦</span>Decoded: <strong>' +
      esc(res.raw) + "</strong>" + (res.q !== res.raw.toLowerCase()
        ? ' <span class="chart-sub">(heard as "' + esc(res.q) + '")</span>' : "") + "</p>";

    if (res.families.length) {
      html += '<div class="dec-fams">' + res.families.map(function (f) {
        return '<article class="dec-fam"><h3>' + esc(f.name) + "</h3>" +
          '<p class="chart-sub">' + esc(f.epithet) + "</p>" +
          '<p><a href="codex/' + esc(famSlug(f.name)) + '.html">Open the family &rarr;</a></p></article>';
      }).join("") + "</div>";
    } else {
      html += '<p class="chart-sub">No codex family claims this word — it stands alone in the vocabulary.</p>';
    }

    if (res.hits.length) {
      html += '<h3 class="stat-h">' + res.hits.length + " transmission" +
        (res.hits.length === 1 ? "" : "s") + " carry it</h3>" +
        '<ol class="top-list">' + res.hits.map(function (r) {
          var plays = (r.plays != null) ? fmt(r.plays) + " plays" : "plays uncounted";
          return "<li><span>" + esc(r.title) +
            '<br><small class="chart-sub">' + esc(r.date || "date unknown") +
            " · " + esc(r.type) + "</small></span>" +
            '<span class="top-n">' + esc(plays) + "</span></li>";
        }).join("") + "</ol>";
    } else {
      html += '<p class="dec-empty">No transmission carries this word. The archive is silent — try another.</p>';
    }
    out.innerHTML = html;
  }

  /* Mirror of scripts/build_releases.py slugify: lowercase, "&" -> " and",
     non-alphanumerics -> hyphens. Family names carry no leet digits. */
  function famSlug(name) {
    return String(name).toLowerCase().replace(/&/g, " and ")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "family";
  }

  function init() {
    var form = document.getElementById("dec-form");
    var input = document.getElementById("dec-input");
    var out = document.getElementById("dec-out");
    if (!form || !input || !out) return;

    out.innerHTML = '<p class="dec-empty">Loading the archive…</p>';
    load().then(function () {
      out.innerHTML = '<p class="dec-empty">The archive is listening.</p>';
      var params = new URLSearchParams(window.location.search);
      var preset = params.get("w");
      if (preset) {
        input.value = preset;
        render(decode(preset), out);
      }
    }).catch(function () {
      out.innerHTML = '<p class="dec-empty">Could not load the archive. Serve the site over HTTP — browsers block fetch() from file:// pages.</p>';
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!DATA) return;
      render(decode(input.value), out);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
