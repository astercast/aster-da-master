/* The Scene Atlas — scene-atlas.html.
 * A cartographer's chart of the scene around the music, plotted ONLY
 * from data/v1/circle.json (21 title-credited collaborators) and
 * data/v1/scene-figures.json (the producer-credit scene figure).
 * Figures are charted deepest first (shared plays, as recorded).
 * Crossings are computed by literal track-title match across two
 * figures' own track lists — no other connection is drawn, because
 * the data states no other. Figures with no verified notes render
 * honestly thin. A failed fetch leaves the printed chart standing
 * and says so. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(n) { return Number(n).toLocaleString("en-US"); }
  function pad(n, w) { var s = String(n); while (s.length < w) s = "0" + s; return s; }
  function normTitle(t) {
    return String(t || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  var els = {
    route: document.getElementById("atlas-route"),
    card: document.getElementById("atlas-card"),
    status: document.getElementById("atlas-status"),
    filters: document.getElementById("atlas-filters"),
    routes: document.getElementById("atlas-routes"),
    logBody: document.getElementById("chart-log-body"),
    logCount: document.getElementById("chart-log-count")
  };
  if (!els.route || !els.card) return;

  var ALL = [];
  var filter = "all";
  var activeId = null;

  function normalize(circle, scene) {
    var out = [];
    Object.keys(circle || {}).forEach(function (k) {
      var v = circle[k], vn = v.verified_notes || {};
      out.push({
        id: k, name: v.name, kind: "Title-credited collaborator", role: "collaborator",
        page: v.page, n: v.shared_transmissions, plays: v.shared_plays,
        years: v.years_active, tracks: v.tracks || [],
        facts: vn.facts || [], sources: vn.sources || [], standing: "", watch: null
      });
    });
    Object.keys(scene || {}).forEach(function (k) {
      var v = scene[k];
      var yrs = v.tracks.map(function (t) { return t.date.slice(0, 4); }).sort();
      out.push({
        id: k, name: v.name, kind: v.kind, role: "scene",
        page: v.page, n: v.tracks.length,
        plays: v.tracks.reduce(function (a, t) { return a + (t.plays || 0); }, 0),
        years: yrs[0] + "\u2013" + yrs[yrs.length - 1], tracks: v.tracks,
        facts: v.facts || [], sources: v.sources || [],
        standing: v.standing || "", watch: v.watch || null
      });
    });
    out.sort(function (a, b) { return b.plays - a.plays; });
    out.forEach(function (f, i) { f.rank = i + 1; });
    return out;
  }

  function crossings(figs) {
    var byTitle = {};
    figs.forEach(function (f) {
      f.tracks.forEach(function (t) {
        var key = normTitle(t.title);
        (byTitle[key] = byTitle[key] || []).push({ fig: f, track: t });
      });
    });
    var out = [];
    Object.keys(byTitle).forEach(function (key) {
      var hits = byTitle[key];
      var ids = {};
      hits.forEach(function (h) { ids[h.fig.id] = true; });
      if (Object.keys(ids).length > 1) out.push({ key: key, hits: hits });
    });
    out.sort(function (a, b) { return (b.hits[0].track.plays || 0) - (a.hits[0].track.plays || 0); });
    return out;
  }

  function matches(f) {
    if (filter === "all") return true;
    if (filter === "collaborator") return f.role === "collaborator";
    if (filter === "scene") return f.role === "scene";
    if (filter === "verified") return f.facts.length > 0;
    if (filter === "thin") return f.facts.length === 0;
    return true;
  }

  function renderRoute() {
    var max = ALL.length ? ALL[0].plays : 1;
    els.route.innerHTML = ALL.map(function (f) {
      var pct = Math.max(3, Math.round((f.plays / max) * 100));
      return '<li class="atlas-stop' + (f.facts.length ? "" : " is-thin") +
        (f.id === activeId ? " is-active" : "") + '"' + (matches(f) ? "" : " hidden") + ">" +
        '<button type="button" class="atlas-stop-btn" data-fig="' + esc(f.id) + '" aria-pressed="' +
        (f.id === activeId) + '">' +
        '<span class="atlas-dot" aria-hidden="true">' + pad(f.rank, 2) + "</span>" +
        '<span class="atlas-stop-main"><span class="atlas-stop-name">' + esc(f.name) + "</span>" +
        '<span class="atlas-stop-sub">' + esc(f.kind) + " \u00b7 " + f.n + " tracks \u00b7 " + esc(f.years) + "</span></span>" +
        '<span class="atlas-stop-depth"><b>' + fmt(f.plays) + '</b>' +
        '<span class="atlas-stop-bar" aria-hidden="true"><i style="width:' + pct + '%"></i></span></span>' +
        "</button></li>";
    }).join("");
  }

  function renderCard(f) {
    var tracks = f.tracks.slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    var trackHtml = tracks.map(function (t) {
      var label = esc(t.title) + ' <span class="dim">' + esc(t.date) + " \u00b7 " +
        (t.plays == null ? "plays not carried" : fmt(t.plays) + " plays") + " \u00b7 " + esc(t.type) + "</span>";
      if (t.page) return '<li><a href="releases/' + esc(t.page) + '">' + esc(t.title) + '</a> <span class="dim">' +
        esc(t.date) + " \u00b7 " + fmt(t.plays) + " plays \u00b7 " + esc(t.type) + "</span></li>";
      return "<li>" + label + "</li>";
    }).join("");
    var note = f.standing
      ? '<p class="atlas-card-note">' + esc(f.standing) + "</p>"
      : (f.facts.length
        ? '<p class="atlas-card-note">Charted from the shared record below, with ' + f.facts.length +
          " verified notes the archive has recorded beyond the titles.</p>"
        : '<p class="atlas-card-note">The archive carries no verified notes for ' + esc(f.name) +
          " yet \u2014 only the shared record below. Plotted honestly thin: the sounding is real, the coastline beyond it is not drawn.</p>");
    var factsHtml = f.facts.length
      ? '<h4 class="atlas-sub">Verified notes the archive carries</h4><ul class="fact-list">' +
        f.facts.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>"
      : "";
    var sourcesHtml = f.sources.length
      ? '<h4 class="atlas-sub">Sources on record</h4><p class="atlas-sources">' +
        f.sources.map(function (s) {
          return '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.label) + "</a>";
        }).join(" \u00b7 ") + "</p>"
      : "";
    var watchHtml = f.watch
      ? '<div class="atlas-watch"><b>The watch \u2014 ' + esc(f.watch.label) + ":</b> " +
        esc(f.watch.status) + ", expected " + esc(f.watch.expected) +
        " (as of " + esc(f.watch.as_of) + "). The archive records a release as released only after a pass confirms it.</div>"
      : "";
    els.card.innerHTML =
      '<div class="atlas-card-head"><span class="atlas-rank">SOUNDING ' + pad(f.rank, 2) + " / " + ALL.length +
      '</span><span class="atlas-kind">' + esc(f.kind) + "</span></div>" +
      '<h3 class="atlas-card-name">' + esc(f.name) + "</h3>" +
      '<div class="atlas-card-facts">' +
      "<div><b>" + f.n + "</b><span>shared transmissions</span></div>" +
      "<div><b>" + fmt(f.plays) + "</b><span>shared plays</span></div>" +
      "<div><b>" + esc(f.years) + "</b><span>years on the chart</span></div>" +
      "<div><b>" + f.facts.length + "</b><span>verified notes recorded</span></div></div>" +
      note + factsHtml +
      '<h4 class="atlas-sub">The shared record, in order</h4>' +
      '<ol class="year-list">' + trackHtml + "</ol>" +
      sourcesHtml + watchHtml +
      '<div class="atlas-card-actions"><a class="btn btn-neon" href="' + esc(f.page) + '">Full circle page &rarr;</a></div>';
    els.status.textContent = "Sounding " + pad(f.rank, 2) + " of " + ALL.length + " \u2014 " + f.name +
      ". Charted only from data/v1/circle.json and data/v1/scene-figures.json.";
  }

  function renderRoutes() {
    var xs = crossings(ALL);
    if (!xs.length) return;
    els.routes.innerHTML = xs.map(function (x) {
      var title = x.hits[0].track.title;
      var names = [];
      x.hits.forEach(function (h) { if (names.indexOf(h.fig.name) < 0) names.push(h.fig.name); });
      var versions = x.hits.length > names.length
        ? " \u2014 carried in " + x.hits.length + " entries across the two records"
        : "";
      var plays = x.hits[0].track.plays;
      return "<li><strong>" + esc(title) + '</strong> <span class="dim">\u2014 ' +
        names.map(esc).join(" \u00d7 ") + " (" + esc(x.hits[0].track.date) + " \u00b7 " +
        (plays == null ? "plays not carried" : fmt(plays) + " plays") + ")" + versions + "</span></li>";
    }).join("");
  }

  function select(id, push) {
    var f = ALL.filter(function (x) { return x.id === id; })[0];
    if (!f) return;
    activeId = id;
    renderRoute();
    renderCard(f);
    if (els.logBody) {
      Array.prototype.forEach.call(els.logBody.querySelectorAll("tr"), function (tr) {
        tr.classList.toggle("is-active", tr.getAttribute("data-fig") === id);
      });
    }
    if (push) {
      try { history.replaceState(null, "", "#fig=" + encodeURIComponent(id)); } catch (e) { /* static file */ }
    }
  }

  function bind() {
    els.route.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-fig]");
      if (b) select(b.getAttribute("data-fig"), true);
    });
    if (els.logBody) {
      els.logBody.addEventListener("click", function (ev) {
        var tr = ev.target.closest("tr[data-fig]");
        if (tr) {
          select(tr.getAttribute("data-fig"), true);
          document.getElementById("chart").scrollIntoView({ block: "start" });
        }
      });
    }
    if (els.filters) {
      els.filters.addEventListener("click", function (ev) {
        var b = ev.target.closest("[data-filter]");
        if (!b) return;
        filter = b.getAttribute("data-filter");
        Array.prototype.forEach.call(els.filters.querySelectorAll("[data-filter]"), function (x) {
          x.setAttribute("aria-pressed", x === b ? "true" : "false");
        });
        renderRoute();
        var visible = ALL.filter(matches);
        els.status.textContent = visible.length + " of " + ALL.length + " figures on this view of the chart.";
      });
    }
  }

  Promise.all([
    fetch("data/v1/circle.json", { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error("circle " + r.status); return r.json();
    }),
    fetch("data/v1/scene-figures.json", { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error("scene " + r.status); return r.json();
    })
  ]).then(function (pair) {
    ALL = normalize(pair[0], pair[1]);
    bind();
    renderRoutes();
    var fromHash = (location.hash.match(/fig=([^&]+)/) || [])[1];
    var start = fromHash ? decodeURIComponent(fromHash) : ALL[0].id;
    select(start, false);
    if (els.logCount) els.logCount.textContent = ALL.length + " soundings";
  }).catch(function () {
    els.status.textContent = "The live chart could not load its two source files \u2014 the printed chart log below stands as recorded.";
    els.status.classList.add("is-lost");
  });
})();
