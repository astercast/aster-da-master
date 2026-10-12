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
  var TOOLS = null;     // session-tools.json (wave 25: compare / deepest / scrubber)

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

  /* ---------------- wave 25: session tools ---------------- */
  /* All compare math mirrors the server-side pure functions in
     scripts/build_session_tools.py (tested by test_session_tools.py). */

  function profById(id) {
    for (var i = 0; i < TOOLS.sessions.length; i++) {
      if (TOOLS.sessions[i].id === id) return TOOLS.sessions[i];
    }
    return null;
  }

  function deltaStr(n, places) {
    var v = places ? Number(n).toFixed(places) : String(Math.round(n));
    return (n > 0 ? "+" : n < 0 ? "\u2212" : "") + String(v).replace("-", "");
  }

  /* play profile: each transmission's lifetime plays in upload order.
     Honest labeling: a single snapshot cannot show a trajectory. */
  function stripHtml(s) {
    var prof = s.play_profile;
    var max = 1;
    for (var i = 0; i < prof.length; i++) max = Math.max(max, prof[i].plays);
    var bars = prof.map(function (t) {
      var w = Math.max(3, Math.round(t.plays / max * 100));
      return '<li aria-hidden="true"><span class="se-strip-barwrap">' +
        '<span class="se-strip-bar" style="width:' + w + '%" title="' +
        esc(t.title) + ' \u2014 ' + fmt(t.plays) + ' plays"></span></span></li>';
    }).join("");
    var min = prof[0].plays, mx = prof[0].plays;
    prof.forEach(function (t) { min = Math.min(min, t.plays); mx = Math.max(mx, t.plays); });
    var sr = prof.map(function (t) {
      return '<li>' + esc(t.title) + ' \u2014 ' + fmt(t.plays) + ' plays, ' + esc(t.date) + '</li>';
    }).join("");
    return '<div class="se-strip" role="img" aria-label="Play profile for ' + esc(s.name) +
      ': ' + prof.length + ' transmissions in upload order, lifetime plays ' + fmt(min) +
      ' to ' + fmt(mx) + ' (single 2026-10-11 snapshot, not a trajectory)">' +
      '<ol class="se-strip-bars">' + bars + '</ol></div>' +
      '<ul class="visually-hidden">' + sr + '</ul>' +
      '<p class="chart-sub">Play profile \u2014 lifetime plays per transmission in upload order ' +
      '(single snapshot, not a trajectory).</p>';
  }

  function sessionNameLink(s) {
    var href = s.deep_dive ? s.deep_dive : '#card-' + s.id;
    return '<a href="' + esc(href) + '">' + esc(s.name) + '</a>';
  }

  function crossLinks(s) {
    var out = (s.deep_dive ? '<a href="' + esc(s.deep_dive) + '">Session deep dive \u2192</a> ' : '') +
      '<a href="' + esc(s.era_deep_dive) + '">' + esc(s.era_name) + ' deep dive \u2192</a> ' +
      '<a href="' + esc(s.journey) + '">Journey node \u2192</a>';
    if (s.families.length) {
      out += ' <span class="chart-sub">Codex:</span> ' + s.families.map(function (f) {
        return '<a href="' + esc(f.page) + '">' + esc(f.name) + '</a>';
      }).join(' ');
    }
    return out;
  }

  /* ---------------- compare ---------------- */
  var cmp = { a: "session-02", b: "session-43" };

  function cmpOptions(sel) {
    return TOOLS.sessions.map(function (s) {
      var n = s.id.replace("session-", "#");
      return '<option value="' + esc(s.id) + '"' + (s.id === sel ? ' selected' : '') +
        '>' + esc(n) + ' \u2014 ' + esc(s.name) + '</option>';
    }).join("");
  }

  function overlapHtml(ov) {
    var part = function (label, ids) {
      return '<p class="se-cut"><strong>' + label + ':</strong> ' +
        (ids.length ? ids.map(function (c) {
          return '<span class="se-chip">' + esc(c) + '</span>';
        }).join(' ') : '<span class="chart-sub">none</span>') + '</p>';
    };
    return part("Only in A", ov.only_a) + part("In both", ov.both) + part("Only in B", ov.only_b);
  }

  function renderCompare() {
    var a = profById(cmp.a), b = profById(cmp.b);
    var box = $("se-compare-out");
    if (!a || !b || a.id === b.id) {
      box.innerHTML = '<p class="chart-sub">Pick two different sessions to compare.</p>';
      return;
    }
    var ca = new Set(a.collaborators), cb = new Set(b.collaborators);
    var ov = {
      only_a: a.collaborators.filter(function (c) { return !cb.has(c); }),
      only_b: b.collaborators.filter(function (c) { return !ca.has(c); }),
      both: a.collaborators.filter(function (c) { return cb.has(c); })
    };
    var span = function (s) { return s.start === s.end ? s.start : s.start + " \u2013 " + s.end; };
    var row = function (label, va, vb, delta) {
      return '<tr><th scope="row">' + label + '</th><td>' + va + '</td><td>' + vb +
        (delta ? ' <span class="chart-sub">' + delta + '</span>' : '') + '</td></tr>';
    };
    var dTracks = b.track_count - a.track_count;
    var dPlays = b.total_plays - a.total_plays;
    var dAvg = b.avg_plays_per_track - a.avg_plays_per_track;
    var sumBits = [];
    sumBits.push((dTracks >= 0 ? "+" : "\u2212") + Math.abs(dTracks) + " transmissions");
    sumBits.push((dPlays >= 0 ? "+" : "\u2212") + fmt(Math.abs(dPlays)) + " plays");
    sumBits.push((dAvg >= 0 ? "+" : "\u2212") + Math.abs(dAvg).toFixed(1) + " avg plays");
    box.innerHTML =
      '<p class="se-cmp-sum"><strong>B vs A:</strong> ' + sumBits.join(" \u00b7 ") +
      ' <span class="chart-sub">(B ' + (dAvg < 0 ? "runs deeper" : dAvg > 0 ? "runs louder" : "matches A") +
      ' on average plays)</span></p>' +
      '<div class="table-wrap"><table>' +
      '<caption class="visually-hidden">Head-to-head session comparison</caption>' +
      '<thead><tr><th scope="col">Metric</th><th scope="col">' + esc(a.id.replace("session-", "#")) +
      ' \u2014 ' + sessionNameLink(a) + '</th><th scope="col">' + esc(b.id.replace("session-", "#")) +
      ' \u2014 ' + sessionNameLink(b) + '</th></tr></thead><tbody>' +
      row("Span", esc(span(a)), esc(span(b)), null) +
      row("Era", '<a href="' + esc(a.era_deep_dive) + '">' + esc(a.era_name) + '</a>',
          '<a href="' + esc(b.era_deep_dive) + '">' + esc(b.era_name) + '</a>', null) +
      row("Transmissions", String(a.track_count), String(b.track_count), "B vs A " + deltaStr(dTracks)) +
      row("Total plays", fmt(a.total_plays), fmt(b.total_plays), "B vs A " + deltaStr(dPlays)) +
      row("Avg plays / transmission", a.avg_plays_per_track.toFixed(1), b.avg_plays_per_track.toFixed(1),
          "B vs A " + deltaStr(dAvg, 1)) +
      row("Loudest", '<a href="' + esc(a.loudest.page) + '">' + esc(a.loudest.title) + '</a> <span class="dim">' +
          fmt(a.loudest.plays) + '</span>',
          '<a href="' + esc(b.loudest.page) + '">' + esc(b.loudest.title) + '</a> <span class="dim">' +
          fmt(b.loudest.plays) + '</span>', null) +
      row("Deepest cut", '<a href="' + esc(a.deepest_cut.page) + '">' + esc(a.deepest_cut.title) + '</a> <span class="dim">' +
          fmt(a.deepest_cut.plays) + '</span>',
          '<a href="' + esc(b.deepest_cut.page) + '">' + esc(b.deepest_cut.title) + '</a> <span class="dim">' +
          fmt(b.deepest_cut.plays) + '</span>', null) +
      '</tbody></table></div>' +
      '<h4 class="se-sub">Who was in the room</h4>' + overlapHtml(ov) +
      '<h4 class="se-sub">Play profiles</h4>' +
      '<div class="se-cmp-profiles"><div><h5>' + esc(a.id.replace("session-", "#")) + '</h5>' + stripHtml(a) +
      '</div><div><h5>' + esc(b.id.replace("session-", "#")) + '</h5>' + stripHtml(b) + '</div></div>' +
      '<h4 class="se-sub">Keep digging</h4>' +
      '<p class="se-links"><strong>A:</strong> ' + crossLinks(a) + '</p>' +
      '<p class="se-links"><strong>B:</strong> ' + crossLinks(b) + '</p>';
    $("se-cmp-note").textContent = "Trajectory honesty: " + TOOLS.snapshot_history.note;
    try {
      history.replaceState(null, "", "#compare=" + a.id + "," + b.id);
    } catch (err) { /* noop */ }
  }

  function renderCompareControls() {
    $("se-cmp-a").innerHTML = cmpOptions(cmp.a);
    $("se-cmp-b").innerHTML = cmpOptions(cmp.b);
    $("se-cmp-a").addEventListener("change", function (e) { cmp.a = e.target.value; renderCompare(); });
    $("se-cmp-b").addEventListener("change", function (e) { cmp.b = e.target.value; renderCompare(); });
    $("se-cmp-copy").addEventListener("click", function () {
      var link = location.origin + location.pathname + "#compare=" + cmp.a + "," + cmp.b;
      var done = function (btn) {
        btn.textContent = "Copied \u2713";
        setTimeout(function () { btn.textContent = "Copy comparison link"; }, 1600);
      };
      var btn = $("se-cmp-copy");
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(link).then(function () { done(btn); }, function () { done(btn); });
      } else { done(btn); }
    });
    renderCompare();
  }

  /* ---------------- deepest cuts ---------------- */
  var deepShown = 10;

  function renderDeep() {
    var dc = TOOLS.deepest_cuts;
    $("se-formula").innerHTML = '<strong>The formula, stated:</strong> ' + esc(dc.formula) +
      ' <span class="chart-sub">' + dc.excluded_single_track_sessions +
      ' single-transmission sessions sit outside the ranking by that rule.</span>';
    var rows = dc.ranking.slice(0, deepShown);
    $("se-deep-list").innerHTML = rows.map(function (r) {
      var p = profById(r.session_id);
      var href = r.deep_dive ? r.deep_dive : '#card-' + r.session_id;
      return '<li class="se-deep-row"><span class="se-deep-rank" aria-label="rank ' + r.rank + '">#' +
        r.rank + '</span><div class="se-deep-body">' +
        '<h4><a href="' + esc(href) + '">' + esc(r.name) + '</a></h4>' +
        '<p class="session-meta">' + esc(r.start) + ' \u2013 ' + esc(r.end) + ' \u00b7 ' +
        esc(r.era_name) + '</p>' +
        '<p>' + r.track_count + ' transmissions \u00b7 ' + fmt(r.total_plays) + ' plays \u00b7 ' +
        '<strong>' + r.avg_plays_per_track.toFixed(1) + ' avg</strong></p>' +
        (p ? stripHtml(p) : '') +
        '</div></li>';
    }).join("");
    var btn = $("se-deep-toggle");
    var total = dc.ranking.length;
    if (deepShown >= total) {
      btn.textContent = "Show top 10";
      btn.setAttribute("aria-expanded", "true");
    } else {
      btn.textContent = "Show all " + total + " ranked sessions";
      btn.setAttribute("aria-expanded", "false");
    }
  }

  /* ---------------- quietest transmissions (track-level deep cuts) ---------------- */
  var trackDeepShown = 10;

  function renderTrackDeep() {
    var tdc = TOOLS.track_deep_cuts;
    if (!tdc) { return; }
    $("se-trackdeep-formula").innerHTML = '<strong>The formula, stated:</strong> ' +
      esc(tdc.formula);
    var rows = tdc.bottom_25.slice(0, trackDeepShown);
    $("se-trackdeep-list").innerHTML = rows.map(function (r) {
      var voices = r.voices.length ?
        ' <span class=\"dim\">w/ ' + esc(r.voices.join(", ")) + "</span>" : "";
      return '<li class=\"se-deep-row\"><span class=\"se-deep-rank\" aria-label=\"rank ' +
        r.rank + '\">#' + r.rank + '</span><div class=\"se-deep-body\">' +
        '<h4><a href=\"' + esc(r.page) + '\">' + esc(r.title) + "</a>" + voices + "</h4>" +
        '<p class=\"session-meta\">' + esc(r.date) + " \u00b7 " + esc(r.era_name) +
        " \u00b7 " + esc(r.session_name) + "</p>" +
        "<p><strong>" + fmt(r.plays) + " plays</strong> \u00b7 median is " +
        fmt(tdc.insights.median_plays) + "</p>" +
        "</div></li>";
    }).join("");
    var btn = $("se-trackdeep-toggle");
    var total = tdc.bottom_25.length;
    if (trackDeepShown >= total) {
      btn.textContent = "Show top 10";
      btn.setAttribute("aria-expanded", "true");
    } else {
      btn.textContent = "Show all " + total + " quietest transmissions";
      btn.setAttribute("aria-expanded", "false");
    }
  }

  /* ---------------- timeline scrubber ---------------- */
  var scrubIdx = 60;

  function stopHtml(s) {
    var span = s.start === s.end ? s.start : s.start + " \u2013 " + s.end;
    return '<article class="se-card se-scrub-card">' +
      '<span class="session-meta"><span class="n">' + esc(s.id) + '</span> ' + esc(span) + '</span>' +
      '<h3>' + sessionNameLink(s) + '</h3>' +
      '<p class="se-stats">' + s.track_count + ' transmission' + (s.track_count === 1 ? '' : 's') +
      ' \u00b7 ' + fmt(s.total_plays) + ' plays \u00b7 ' + s.avg_plays_per_track.toFixed(1) +
      ' avg <span class="chart-sub">(snapshot ' + esc(TOOLS.plays_snapshot) + ')</span></p>' +
      '<p class="se-cut"><strong>Era:</strong> <a href="' + esc(s.era_deep_dive) + '">' +
      esc(s.era_name) + '</a></p>' +
      '<p class="se-cut"><strong>Loudest:</strong> <a href="' + esc(s.loudest.page) + '">' +
      esc(s.loudest.title) + '</a> <span class="dim">' + fmt(s.loudest.plays) + ' plays</span></p>' +
      '<p class="se-cut"><strong>Deepest cut:</strong> <a href="' + esc(s.deepest_cut.page) + '">' +
      esc(s.deepest_cut.title) + '</a> <span class="dim">' + fmt(s.deepest_cut.plays) + ' plays</span></p>' +
      '<p class="se-links">' + crossLinks(s) + '</p>' +
      '</article>';
  }

  function renderScrub(i) {
    scrubIdx = Math.max(0, Math.min(TOOLS.sessions.length - 1, i));
    var s = TOOLS.sessions[scrubIdx];
    var range = $("se-scrub");
    range.value = String(scrubIdx);
    range.setAttribute("aria-valuetext",
      "Session " + (scrubIdx + 1) + " of " + TOOLS.sessions.length + ": " +
      s.name + ", " + s.start);
    $("se-scrub-pos").textContent = "Session " + (scrubIdx + 1) + " of " +
      TOOLS.sessions.length + " \u2014 " + s.id + ", " + s.start + " \u2013 " + s.end;
    $("se-scrub-card").innerHTML = stopHtml(s);
  }

  function renderScrubControls() {
    var range = $("se-scrub");
    range.max = String(TOOLS.sessions.length - 1);
    range.addEventListener("input", function (e) { renderScrub(Number(e.target.value)); });
    $("se-scrub-prev").addEventListener("click", function () { renderScrub(scrubIdx - 1); });
    $("se-scrub-next").addEventListener("click", function () { renderScrub(scrubIdx + 1); });
    renderScrub(TOOLS.sessions.length - 1);
  }
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
    var m = h.match(/^compare=(session-\d+),(session-\d+)$/);
    if (m && profById(m[1]) && profById(m[2])) {
      cmp.a = m[1]; cmp.b = m[2];
    } else if (/^era-/.test(h)) {
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
      loadData("api/v1/sessions.json"),
      loadData("api/v1/session-tools.json")
    ]).then(function (res) {
      DATA = res[0];
      res[1].sessions.forEach(function (s) { TRACKS[s.id] = s.tracks; });
      TOOLS = res[2];
      readHash();
      renderInsights();
      renderSpotlight();
      renderGaps();
      renderSeasons();
      renderFilters();
      renderCards();
      renderCompareControls();
      renderDeep();
      renderTrackDeep();
      renderScrubControls();
      $("se-deep-toggle").addEventListener("click", function () {
        var total = TOOLS.deepest_cuts.ranking.length;
        deepShown = deepShown >= total ? 10 : total;
        renderDeep();
      });
      $("se-trackdeep-toggle").addEventListener("click", function () {
        var total = TOOLS.track_deep_cuts.bottom_25.length;
        trackDeepShown = trackDeepShown >= total ? 10 : total;
        renderTrackDeep();
      });
      jumpToCard();
      ADM.reveal();
    }, function () {
      fail(["se-insights", "se-spotlight", "se-gaps", "se-seasons", "se-cards",
            "se-compare", "se-deep-list", "se-trackdeep-list", "se-scrub-card"]);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
