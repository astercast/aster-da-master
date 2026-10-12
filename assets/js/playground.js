/* API playground — interactive explorer for the versioned JSON API.
   Endpoint picker, live fetch, pretty-printed response, copy button. */
(function () {
  "use strict";

  var ENDPOINTS = [
    { id: "index", path: "api/v1/index.json",
      blurb: "Start here. Endpoint map, version, provenance, agent guidance." },
    { id: "artist", path: "api/v1/artist.json",
      blurb: "The source of truth: artist record, discography (219 entries), platforms, eras, vault, upcoming." },
    { id: "milestones", path: "api/v1/milestones.json",
      blurb: "Career firsts computed from the verified discography: firsts, records, silences." },
    { id: "codex", path: "api/v1/codex.json",
      blurb: "The vocabulary codex: 16 word families with per-family track lists." },
    { id: "circle", path: "api/v1/circle.json",
      blurb: "The collaborators: 21 voices parsed from title credits." },
    { id: "scene-figures", path: "api/v1/scene-figures.json",
      blurb: "Scene figures: producer credits and scene research outside the 21 (e.g. Fish Narc)." },
    { id: "years", path: "api/v1/years.json",
      blurb: "Year-in-review archive: per-year stats and highlights, 2018–2026." },
    { id: "on-this-day", path: "api/v1/on-this-day.json",
      blurb: "Calendar index: transmissions keyed by MM-DD upload date." },
    { id: "release-slugs", path: "api/v1/release-slugs.json",
      blurb: "Slug index for the 219+ generated release pages." },
    { id: "sessions", path: "api/v1/sessions.json",
      blurb: "Upload sessions: 61 studio sessions clustered from vault upload dates (7-day gap rule)." },
    { id: "changelog", path: "api/v1/changelog.json",
      blurb: "Site construction history, generated from the git log." },
    { id: "first-last", path: "api/v1/first-last.json",
      blurb: "Per year 2018–2026: the opening and closing transmissions." },
    { id: "milestone-watch", path: "api/v1/milestone-watch.json",
      blurb: "Milestone watch: vault tracks near round-number play counts (2026-10-11 snapshot)." },
    { id: "transmission", path: "api/v1/transmission.json",
      blurb: "The guided journey: six eras with stats, top tracks, key sessions, collaborators, milestones, computed signal lines." },
    { id: "network", path: "api/v1/network.json",
      blurb: "Collaboration network: artist-centered nodes (21 title-credited collaborators + producer scene figures), track-weighted edges, co-credit links, computed insights." },
    { id: "eras", path: "api/v1/eras.json",
      blurb: "Era deep-dives: six eras with full transmission lists (every track + plays), all in-era collaborators, active codex families, computed signal summaries. Drives the eras/<id>.html pages." },
    { id: "session-clusters", path: "api/v1/session-clusters.json",
      blurb: "Session archaeology, interactive: the 61 upload sessions as an explorable timeline — per-session enrichment (era, loudest + deepest-cut tracks, cross-links), the 60 inter-session gaps, 9 activity seasons, asserted insights. Drives sessions-explorer.html." },
    { id: "codex-families", path: "api/v1/codex-families.json",
      blurb: "Codex family deep-dives: 16 vocabulary families with decoded readings, era-by-era evolution, key sessions, and title-credited collaborators. Drives the codex/<slug>.html deep-dive pages." }
  ];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function highlight(json) {
    return esc(json).replace(
      /(&quot;(?:[^&]|&(?!quot;))*?&quot;)(\s*:)?/g,
      function (m, str, colon) {
        if (colon) return '<span class="jk">' + str + "</span>" + colon;
        return '<span class="js">' + str + "</span>";
      }).replace(/\b(true|false|null)\b/g, '<span class="jb">$1</span>')
      .replace(/(^|[\s\[,:])(-?\d[\d.]*)/g, '$1<span class="jn">$2</span>');
  }

  function initTabs() {
    var tabs = document.querySelectorAll('[role="tab"]');
    if (!tabs.length) return;
    var panels = {};
    for (var i = 0; i < tabs.length; i++) {
      panels[tabs[i].id] = document.getElementById(tabs[i].getAttribute("aria-controls"));
    }
    function activate(tab) {
      for (var j = 0; j < tabs.length; j++) {
        var on = tabs[j] === tab;
        tabs[j].setAttribute("aria-selected", on ? "true" : "false");
        tabs[j].tabIndex = on ? 0 : -1;
        var p = panels[tabs[j].id];
        if (p) p.hidden = !on;
      }
    }
    for (var k = 0; k < tabs.length; k++) {
      (function (tab, idx) {
        tab.addEventListener("click", function () { activate(tab); });
        tab.addEventListener("keydown", function (e) {
          var dir = e.key === "ArrowRight" ? 1 : (e.key === "ArrowLeft" ? -1 : 0);
          if (!dir) return;
          e.preventDefault();
          var next = tabs[(idx + dir + tabs.length) % tabs.length];
          activate(next);
          next.focus();
        });
      })(tabs[k], k);
    }
  }

  function init() {
    var list = document.getElementById("pg-list");
    var url = document.getElementById("pg-url");
    var meta = document.getElementById("pg-meta");
    var pre = document.getElementById("pg-pre");
    var copyBtn = document.getElementById("pg-copy");
    if (!list || !pre) return;

    var current = null;

    function select(ep, btn) {
      var btns = list.querySelectorAll("[role=option]");
      for (var i = 0; i < btns.length; i++) btns[i].setAttribute("aria-selected", "false");
      btn.setAttribute("aria-selected", "true");
      current = null;
      copyBtn.disabled = true;
      url.textContent = ep.path;
      meta.textContent = "loading…";
      pre.innerHTML = "<code>Fetching " + esc(ep.path) + "…</code>";
      fetch(ep.path)
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.text();
        })
        .then(function (text) {
          var parsed;
          try { parsed = JSON.parse(text); } catch (e) { throw new Error("not JSON"); }
          current = JSON.stringify(parsed, null, 2);
          var kb = (new Blob([current]).size / 1024).toFixed(1);
          var keys = parsed && typeof parsed === "object"
            ? Object.keys(parsed).length : 0;
          meta.textContent = kb + " KB · " + keys + " top-level keys";
          pre.innerHTML = "<code>" + highlight(current) + "</code>";
          copyBtn.disabled = false;
        })
        .catch(function (err) {
          meta.textContent = "failed";
          pre.innerHTML = "<code>Could not read " + esc(ep.path) + " (" +
            esc(err.message) + "). Serve the site over HTTP — browsers block " +
            "fetch() from file:// pages.</code>";
        });
    }

    ENDPOINTS.forEach(function (ep) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "pg-ep";
      b.setAttribute("role", "option");
      b.setAttribute("aria-selected", "false");
      b.innerHTML = '<span class="pg-ep-id">' + esc(ep.id) + "</span>" +
        '<span class="pg-ep-path">' + esc(ep.path) + "</span>" +
        '<span class="pg-ep-blurb">' + esc(ep.blurb) + "</span>";
      b.addEventListener("click", function () { select(ep, b); });
      list.appendChild(b);
    });

    copyBtn.addEventListener("click", function () {
      if (!current) return;
      var done = function () {
        copyBtn.textContent = "Copied ✓";
        setTimeout(function () { copyBtn.textContent = "Copy JSON"; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(current).then(done, function () {
          fallbackCopy(done);
        });
      } else {
        fallbackCopy(done);
      }
    });

    function fallbackCopy(done) {
      var ta = document.createElement("textarea");
      ta.value = current;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { /* noop */ }
      document.body.removeChild(ta);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(); initTabs(); });
  } else {
    init();
    initTabs();
  }
})();
