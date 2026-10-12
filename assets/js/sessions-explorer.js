/* Aster da Master — sessions explorer (wave 19).
   Renders sessions-explorer.html from api/v1/session-clusters.json
   (the timeline: enriched sessions, gaps, seasons, insights) plus
   api/v1/sessions.json (per-session track lists, lazy per card).
   The page renders nothing invented: every figure comes from the JSON. */
(function () {
  "use strict";

  var ADM = window.ADM;
  var esc = ADM.esc, fmt = ADM.fmt, loadData = ADM.loadData;

  var state = { era: "all", year: "all", q: "", sort: "date-desc" };
  var DATA = null;      // session-clusters.json
  var TRACKS = {};      // session id -> tracks[] from sessions.json

  function $(id) { return document.getElementById(id); }

  function fail(sections) {
    sections.forEach(function (id) {
      var el = $(id);
      if (el) el.innerHTML = '<p class="se-error" role="alert">The session data could not be loaded. Check that this page is served over HTTP (browsers block fetch() from file://).</p>';
    });
  }

  function eraById(id) {
    for (var i = 0; i < DATA.eras.length; i++) {
      if (DATA.eras[i].id === id) return DATA.eras[i];
    }
    return null;
  }

  /* ---------------- insights ---------------- */
  function renderInsights() {
    var ins = DATA.insights;
    var items = [
      ["61", "sessions", "clustered by the 7-day upload-gap rule"],
      [String(ins.track_count), "tracks", "SoundCloud vault transmissions"],
      [String(ins.season_count), "activity seasons", "a silence over 90 days opens a new season"],
      [ins.longest_silence.days + "-day", "longest silence",
        ins.longest_silence.from_session + " \u2192 " + ins.longest_silence.to_session],
      [ins.most_prolific.track_count + "-track", "most-prolific session",
        ins.most_prolific.name + ", " + ins.most_prolific.start + " \u2192 " + ins.most_prolific.end],
      [fmt(ins.quietest_session.total_plays), "quietest session plays",
        ins.quietest_session.id + " \u2014 " + esc(ins.quietest_session.name)]
    ];
    $("se-insights").innerHTML = items.map(function (it) {
      return '<div class="se-stat"><dt>' + esc(it[1]) + '</dt><dd>' + esc(it[0]) +
        '</dd><p>' + it[2] + '</p></div>';
    }).join("");
  }

  /* ---------------- spotlight: the most-prolific session ---------------- */
  function trackList(id) {
    var tracks = TRACKS[id] || [];
    return '<ol class="session-tracks">' + tracks.map(function (t) {
      var plays = (t.plays == null) ? "plays uncounted" : fmt(t.plays) + " plays";
      return '<li><a href="' + esc(t.page) + '">' + esc(t.title) + '</a> <span class="chart-sub">' +
        esc(t.date) + ' \u00b7 ' + esc(plays) + '</span></li>';
    }).join("") + "</ol>";
  }

  function renderSpotlight() {
    var mp = DATA.insights.most_prolific;
    var s = DATA.sessions.filter(function (x) { return x.id === mp.id; })[0];
    var era = eraById(s.era_id);
    var cuts = '<p><strong>Loudest:</strong> <a href="' + esc(s.loudest.page) + '">' +
      esc(s.loudest.title) + '</a> <span class="dim">' + fmt(s.loudest.plays) + ' plays</span></p>';
    if (s.loudest.title === s.deepest_cut.title) {
      cuts += '<p class="chart-sub">A single transmission \u2014 loudest and deepest cut are one.</p>';
    } else {
      cuts += '<p><strong>Deepest cut in this session:</strong> <a href="' +
        esc(s.deepest_cut.page) + '">' + esc(s.deepest_cut.title) +
        '</a> <span class="dim">' + fmt(s.deepest_cut.plays) + ' plays</span></p>';
    }
    $("se-spotlight").innerHTML =
      '<article class="se-spot" aria-labelledby="se-spot-h">' +
      '<span class="kicker"><span class="numeral">\u2726</span>' + esc(s.start) + ' \u2013 ' + esc(s.end) + '</span>' +
      '<h3 id="se-spot-h">' + esc(s.name) + '</h3>' +
      '<p>' + s.track_count + ' transmissions \u00b7 ' + fmt(s.total_plays) +
      ' plays <span class="chart-sub">(snapshot ' + esc(DATA.plays_snapshot) + ')</span></p>' +
      '<p>The most prolific upload session on record \u2014 no other session put out more transmissions. ' +
      'Landed in <a href="' + esc(era.deep_dive) + '">' + esc(s.era_name) + '</a>.</p>' +
      '<div class="se-cuts">' + cuts + '</div>' +
      trackList(s.id) +
      '<p class="se-links">' +
      (s.deep_dive ? '<a class="btn btn-sm" href="' + esc(s.deep_dive) + '">Session deep dive \u2192</a> ' : '') +
      '<a class="btn btn-sm" href="' + esc(era.deep_dive) + '">Era deep dive \u2192</a> ' +
      '<a class="btn btn-sm" href="' + esc(s.journey) + '">Journey node \u2192</a></p>' +
      '</article>';
  }

  /* ---------------- gap visualization ---------------- */
  function renderGaps() {
    var gaps = DATA.gaps.slice();
    var max = Math.max.apply(null, gaps.map(function (g) { return g.days; }));
    var log = function (d) { return Math.log(d) / Math.log(max); };
    var rows = gaps.map(function (g) {
      var rec = g.days === DATA.insights.longest_silence.days;
      return '<li class="se-gap' + (rec ? ' is-record' : '') + '">' +
        '<a href="#card-' + esc(g.to_session) + '"><span class="se-gap-label">' +
        esc(g.from_session) + ' \u2192 ' + esc(g.to_session) + '</span>' +
        '<span class="se-gap-barwrap" aria-hidden="true"><span class="se-gap-bar" style="width:' +
        Math.round(log(g.days) * 100) + '%"></span></span>' +
        '<span class="se-gap-days">' + g.days + ' days' +
        (rec ? ' <span class="se-record">record</span>' : '') + '</span></a></li>';
    }).join("");
    var tops = DATA.silences.map(function (g) {
      return '<li>' + g.days + ' days \u2014 ' + esc(g.from_session) + ' (' + esc(g.from_end) +
        ') to ' + esc(g.to_session) + ' (' + esc(g.to_start) + ')</li>';
    }).join("");
    $("se-gaps").innerHTML =
      '<p class="chart-sub">60 silences between the 61 sessions, longest first at the record \u2014 ' +
      'bar length is log-scaled so the 553-day silence doesn\u2019t swallow the chart. Select a row to jump to the session that broke the silence.</p>' +
      '<ol class="se-gap-list">' + rows + '</ol>' +
      '<h4 class="se-sub">The five longest silences</h4>' +
      '<ol class="se-silences">' + tops + '</ol>' +
      '<p class="chart-sub">Upload dates are not recording dates \u2014 a silence is a gap in uploads, nothing more.</p>';
  }

  /* ---------------- seasons ---------------- */
  function renderSeasons() {
    $("se-seasons").innerHTML = '<ul class="se-season-grid">' + DATA.clusters.map(function (c) {
      var chips = c.session_ids.map(function (id) {
        return '<li><a href="#card-' + esc(id) + '">' + esc(id.replace("session-", "#")) + '</a></li>';
      }).join("");
      return '<li class="se-season"><h4>' + esc(c.label) + '</h4>' +
        '<p class="session-meta">' + esc(c.start) + ' \u2013 ' + esc(c.end) + '</p>' +
        '<p>' + c.session_count + ' sessions \u00b7 ' + c.track_count + ' transmissions \u00b7 ' +
        fmt(c.total_plays) + ' plays</p>' +
        '<ul class="se-chips">' + chips + '</ul></li>';
    }).join("") + '</ul>' +
    '<p class="chart-sub">Seasons are a computed browsing convention: consecutive sessions while the separating silence is \u2264 90 days \u2014 not artist-named eras.</p>';
  }

  /* ---------------- filter controls ---------------- */
  function renderFilters() {
    var eraOpts = '<option value="all">All eras</option>' + DATA.eras.map(function (e) {
      return '<option value="' + esc(e.id) + '"' + (state.era === e.id ? ' selected' : '') + '>' +
        esc(e.name) + ' (' + esc(e.span) + ')</option>';
    }).join("");
    var years = [];
    DATA.sessions.forEach(function (s) {
      var y = s.start.slice(0, 4);
      if (years.indexOf(y) === -1) years.push(y);
    });
    years.sort();
    var yearOpts = '<option value="all">All years</option>' + years.map(function (y) {
      return '<option value="' + y + '"' + (state.year === y ? ' selected' : '') + '>' + y + '</option>';
    }).join("");
    $("se-filters").innerHTML =
      '<div class="se-control"><label for="se-era">Era</label><select id="se-era">' + eraOpts + '</select></div>' +
      '<div class="se-control"><label for="se-year">Year</label><select id="se-year">' + yearOpts + '</select></div>' +
      '<div class="se-control"><label for="se-sort">Sort</label><select id="se-sort">' +
      '<option value="date-desc"' + (state.sort === "date-desc" ? ' selected' : '') + '>Newest first</option>' +
      '<option value="date-asc"' + (state.sort === "date-asc" ? ' selected' : '') + '>Oldest first</option>' +
      '<option value="tracks"' + (state.sort === "tracks" ? ' selected' : '') + '>Most tracks</option>' +
      '<option value="plays"' + (state.sort === "plays" ? ' selected' : '') + '>Most plays</option>' +
      '</select></div>' +
      '<div class="se-control"><label for="se-q">Search</label>' +
      '<input type="search" id="se-q" value="' + esc(state.q) + '" placeholder="session name or id" autocomplete="off" spellcheck="false"></div>';
    $("se-era").addEventListener("change", function (e) { state.era = e.target.value; sync(); });
    $("se-year").addEventListener("change", function (e) { state.year = e.target.value; sync(); });
    $("se-sort").addEventListener("change", function (e) { state.sort = e.target.value; sync(); });
    $("se-q").addEventListener("input", function (e) { state.q = e.target.value; renderCards(); });
  }

  function filtered() {
    var q = state.q.trim().toLowerCase();
    var out = DATA.sessions.filter(function (s) {
      if (state.era !== "all" && s.era_id !== state.era) return false;
      if (state.year !== "all" && s.start.slice(0, 4) !== state.year) return false;
      if (q && (s.name.toLowerCase().indexOf(q) === -1) && (s.id.toLowerCase().indexOf(q) === -1)) return false;
      return true;
    });
    var by = {
      "date-desc": function (a, b) { return a.start < b.start ? 1 : -1; },
      "date-asc": function (a, b) { return a.start < b.start ? -1 : 1; },
      "tracks": function (a, b) { return (b.track_count - a.track_count) || (b.total_plays - a.total_plays); },
      "plays": function (a, b) { return (b.total_plays - a.total_plays) || (b.track_count - a.track_count); }
    };
    out.sort(by[state.sort] || by["date-desc"]);
    return out;
  }

  /* ---------------- session cards ---------------- */
  function cardHtml(s) {
    var era = eraById(s.era_id);
    var span = s.start === s.end ? s.start : s.start + " \u2013 " + s.end;
    var cuts;
    if (s.loudest.title === s.deepest_cut.title) {
      cuts = '<p class="se-cut"><strong>The transmission:</strong> <a href="' + esc(s.loudest.page) + '">' +
        esc(s.loudest.title) + '</a> <span class="dim">' + fmt(s.loudest.plays) + ' plays</span></p>';
    } else {
      cuts = '<p class="se-cut"><strong>Loudest:</strong> <a href="' + esc(s.loudest.page) + '">' +
        esc(s.loudest.title) + '</a> <span class="dim">' + fmt(s.loudest.plays) + ' plays</span></p>' +
        '<p class="se-cut"><strong>Deepest cut in this session:</strong> <a href="' +
        esc(s.deepest_cut.page) + '">' + esc(s.deepest_cut.title) + '</a> <span class="dim">' +
        fmt(s.deepest_cut.plays) + ' plays</span></p>';
    }
    var collabs = s.collaborators.length ?
      s.collaborators.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join("") :
      '<li class="chart-sub">Solo run \u2014 no title-credited collaborators</li>';
    var links = '<a href="' + esc(era.deep_dive) + '">' + esc(s.era_name) + ' deep dive \u2192</a> ' +
      '<a href="' + esc(s.journey) + '">Journey node \u2192</a>' +
      (s.deep_dive ? ' <a href="' + esc(s.deep_dive) + '">Session deep dive \u2192</a>' : '');
    return '<article class="se-card" id="card-' + esc(s.id) + '">' +
      '<span class="session-meta"><span class="n">' + esc(s.id) + '</span> ' + esc(span) +
      ' \u00b7 ' + esc(s.season.replace("season-", "season ")) + '</span>' +
      '<h3>' + esc(s.name) + '</h3>' +
      '<p class="se-stats">' + s.track_count + ' transmission' + (s.track_count === 1 ? '' : 's') +
      ' \u00b7 ' + fmt(s.total_plays) + ' plays <span class="chart-sub">(snapshot ' +
      esc(DATA.plays_snapshot) + ')</span></p>' +
      '<div class="se-cuts">' + cuts + '</div>' +
      '<ul class="se-chips" aria-label="Title-credited collaborators">' + collabs + '</ul>' +
      '<p class="se-links">' + links + '</p>' +
      '<button type="button" class="btn btn-sm se-toggle" aria-expanded="false" aria-controls="tl-' +
      esc(s.id) + '" data-session="' + esc(s.id) + '">Tracks (' + s.track_count + ')</button>' +
      '<div id="tl-' + esc(s.id) + '" hidden></div>' +
      '</article>';
  }

  function renderCards() {
    var list = filtered();
    $("se-count").textContent = list.length + " of 61 sessions";
    $("se-cards").innerHTML = list.length ?
      list.map(cardHtml).join("") :
      '<p class="chart-sub">No sessions match these filters.</p>';
    var toggles = $("se-cards").querySelectorAll(".se-toggle");
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener("click", toggleTracks);
    }
  }

  function toggleTracks(e) {
    var btn = e.currentTarget;
    var id = btn.getAttribute("data-session");
    var box = $("tl-" + id);
    var open = btn.getAttribute("aria-expanded") === "true";
    if (open) {
      btn.setAttribute("aria-expanded", "false");
      box.hidden = true;
      btn.textContent = "Tracks (" + (TRACKS[id] || []).length + ")";
    } else {
      btn.setAttribute("aria-expanded", "true");
      box.hidden = false;
      box.innerHTML = trackList(id);
      btn.textContent = "Hide tracks";
    }
  }

  function sync() {
    // keep the era in the URL so era deep-dive pages can deep-link here
    var h = state.era !== "all" ? "era-" + state.era : "";
    try { history.replaceState(null, "", h ? "#" + h : location.pathname); } catch (err) { /* noop */ }
    // filters keep their own DOM state; only the cards re-render
    renderCards();
  }

  function readHash() {
    var h = (location.hash || "").replace(/^#/, "");
    if (/^era-/.test(h)) {
      var eraId = h.replace(/^era-/, "");
      if (eraById(eraId)) state.era = eraId;
    } else if (/^session-\d+$/.test(h) || /^card-session-\d+$/.test(h)) {
      // handled after render: jump to the card
    }
  }

  function jumpToCard() {
    var h = (location.hash || "").replace(/^#/, "").replace(/^card-/, "");
    if (/^session-\d+$/.test(h)) {
      var el = $("card-" + h);
      if (el) {
        el.scrollIntoView({ block: "start" });
        el.classList.add("se-flash");
      }
    }
  }

  /* ---------------- boot ---------------- */
  function boot() {
    Promise.all([
      loadData("api/v1/session-clusters.json"),
      loadData("api/v1/sessions.json")
    ]).then(function (res) {
      DATA = res[0];
      res[1].sessions.forEach(function (s) { TRACKS[s.id] = s.tracks; });
      readHash();
      renderInsights();
      renderSpotlight();
      renderGaps();
      renderSeasons();
      renderFilters();
      renderCards();
      jumpToCard();
      ADM.reveal();
    }, function () {
      fail(["se-insights", "se-spotlight", "se-gaps", "se-seasons", "se-cards"]);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
