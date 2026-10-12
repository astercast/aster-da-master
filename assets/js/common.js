/* Aster da Master — shared helpers for standalone pages (timeline, network).
   site.js keeps its own copies; this file is loaded by pages that don't use site.js. */
(function () {
  "use strict";

  /* Web-craft failure-mode rule: the finished (revealed) state is the CSS
     default; the hidden pre-reveal state only applies when this script
     actually runs. If this file fails to load, content stays visible. */
  document.documentElement.classList.add("js");

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Parse "w/ X" / "ft. X" / "feat. X" collaborator credits from a title, verbatim.
     Producers (prod.) are excluded; self-references are excluded. */
  function parseCollabs(title) {
    var names = [];
    var re = /(?:\bw\/\s*|\bft\.?\s+|\bfeat\.?\s+)/gi;
    var m;
    while ((m = re.exec(title)) !== null) {
      var rest = title.slice(m.index + m[0].length);
      rest = rest.split(/[([]/)[0].split(/prod\.?/i)[0];
      rest.split(/\s+[xX]\s+|\s*&\s*|\s*\+\s*|,|\s*\/\s*|\s+and\s+/).forEach(function (p) {
        p = p.replace(/^[ .!~)"']+|[ .!~)"']+$/g, "");
        if (p && p.length < 30 && !/aster\s*da\s*master/i.test(p) && !/prod/i.test(p)) {
          names.push(p);
        }
      });
    }
    return names;
  }

  function loadData(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("data failed: " + url);
      return r.json();
    });
  }

  /* "2017 – 2019" / "2020" -> {start: 2017, end: 2019} */
  function spanYears(span) {
    var m = /(\d{4})(?:\s*[–—-]\s*(\d{4}))?/.exec(String(span || ""));
    if (!m) return null;
    return { start: parseInt(m[1], 10), end: parseInt(m[2] || m[1], 10) };
  }

  function fmt(n) { return Number(n).toLocaleString("en-US"); }

  /* Slugify, identical to scripts/build_releases.py slugify: lowercase,
     "&" -> " and ", every run of non [a-z0-9] -> "-", trim dashes.
     Single source of truth for JS deep links to generated pages. */
  function slugify(s) {
    return String(s == null ? "" : s).toLowerCase()
      .replace(/&/g, " and ")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "page";
  }

  /* Reveal on scroll (same pattern as site.js) */
  function reveal() {
    var els = document.querySelectorAll(".reveal");
    if ("IntersectionObserver" in window) {
      var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { e.target.classList.add("in"); obs.unobserve(e.target); }
        });
      }, { threshold: 0.12 });
      els.forEach(function (el) { obs.observe(el); });
    } else {
      els.forEach(function (el) { el.classList.add("in"); });
    }
  }

  window.ADM = { esc: esc, parseCollabs: parseCollabs, loadData: loadData, spanYears: spanYears, fmt: fmt, reveal: reveal, slugify: slugify };
})();
