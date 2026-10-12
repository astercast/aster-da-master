/* Aster da Master — milestone race (wave 22; wave 28: race 2.0).
   Renders milestone-race.html from api/v1/milestone-races.json.
   Every figure comes from the JSON; nothing is computed client-side
   beyond display formatting and pair lookup. Pace figures are stated as
   estimates, never predictions. */
(function () {
  "use strict";

  var ADM = window.ADM;
  var esc = ADM.esc, fmt = ADM.fmt, loadData = ADM.loadData;

  function $(id) { return document.getElementById(id); }

  function fail(sections) {
    sections.forEach(function (id) {
      var el = $(id);
      if (el) el.innerHTML = '<p class="se-error" role="alert">The race data could not be loaded. Check that this page is served over HTTP (browsers block fetch() from file://).</p>';
    });
  }

  function producerLinks(prods) {
    if (!prods || !prods.length) return "";
    return '<p class="chart-sub">Produced by ' + prods.map(function (p) {
      return '<a href="' + esc(p.page) + '">' + esc(p.name) + "</a>";
    }).join(", ") + "</p>";
  }

  /* ---------------- closest races ---------------- */
  function raceCard(r, rank, total) {
    var bar = '<div class="mr-bar" role="progressbar" aria-valuenow="' +
      esc(r.progress_pct) + '" aria-valuemin="0" aria-valuemax="100" ' +
      'aria-label="' + esc(r.title) + ': ' + esc(r.progress_pct) +
      ' percent of the way to ' + esc(r.milestone) + '">' +
      '<span style="width:' + esc(r.progress_pct) + '%"></span></div>';
    return '<article class="mr-race">' +
      '<p class="mr-rank" aria-label="Race ' + rank + " of " + total + '">#' + rank + '</p>' +
      '<h3><a href="' + esc(r.page) + '">' + esc(r.title) + '</a></h3>' +
      '<p class="mr-line"><strong>' + fmt(r.plays) + '</strong> of ' +
      fmt(r.target) + ' plays — <strong>' + fmt(r.needed) + ' needed</strong></p>' +
      bar +
      '<p class="mr-pace">Pace: ~' + esc(r.pace_per_day) + ' plays/day ' +
      '(lifetime average to the 2026-10-11 snapshot). At this pace, the gap ' +
      'closes in <strong>~' + fmt(r.days_at_pace) + ' days</strong> — ' +
      'an estimate, not a prediction.</p>' +
      producerLinks(r.producers) +
      '</article>';
  }

  function renderClosest(data) {
    var byId = {};
    data.play_races.forEach(function (r) { byId[r.id] = r; });
    var html = data.closest_races.map(function (rid, i) {
      return raceCard(byId[rid], i + 1, data.play_races.length);
    }).join("");
    $("mr-closest").innerHTML = html;
  }

  /* ---------------- race to watch (computed spotlight + share card) ---------------- */
  function renderWatch(data) {
    var w = data.race_of_the_week;
    $("mr-watch-basis").textContent = w.basis;
    var byId = {};
    data.play_races.forEach(function (r) { byId[r.id] = r; });
    var r = byId[w.race_id];
    $("mr-watch").innerHTML =
      '<article class="mr-watch-card" aria-labelledby="mr-watch-title">' +
      '<p class="kicker"><span class="numeral">✦</span>Spotlight</p>' +
      raceCard(r, 1, 1).replace('aria-label="Race 1 of 1"', 'aria-label="Race to watch"') +
      '<p class="chart-sub">' + esc(w.caveat) + '</p>' +
      '<div class="btn-row">' +
      '<button class="btn btn-sm btn-neon" id="mr-share" type="button">Copy share link</button>' +
      '</div>' +
      '<p class="chart-sub" id="mr-share-note" aria-live="polite"></p>' +
      '</article>';
    $("mr-share").addEventListener("click", function () {
      var text = w.share_text + " " + location.href.split("#")[0] + "#watch";
      var note = $("mr-share-note");
      function done(ok) {
        note.textContent = ok ? "Copied — paste it anywhere."
          : "Copy this: " + text;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { done(true); },
          function () { done(false); });
      } else {
        done(false);
      }
    });
  }

  /* ---------------- head-to-head: race any two vault tracks ----------------
     Client-side mirror of the generator's project_pair: needed = target -
     plays; days at pace = needed / lifetime pace; already past the line
     means no race to run. bankers1 matches Python's round(x, 1) exactly
     (half-even), so the tool reproduces the asserted JSON figures. */
  var VAULT = null;

  function bankers1(x) {
    var n = x * 10, f = Math.floor(n), d = n - f;
    if (Math.abs(d - 0.5) < 1e-9) return (f % 2 === 0 ? f : f + 1) / 10;
    return Math.round(n) / 10;
  }

  var UNCERTAIN = "Pace is a lifetime average from a single snapshot, not a " +
    "current rate - this is arithmetic, not a forecast.";

  function trackById(id) {
    for (var i = 0; i < VAULT.length; i++) {
      if (VAULT[i].id === id) return VAULT[i];
    }
    return null;
  }

  function projectPair(a, b, ta, tb) {
    var na = ta - a.plays, nb = tb - b.plays;
    var crossed = [];
    if (na <= 0) crossed.push(a.id);
    if (nb <= 0) crossed.push(b.id);
    var da = na > 0 ? bankers1(na / a.pace_per_day) : 0;
    var db = nb > 0 ? bankers1(nb / b.pace_per_day) : 0;
    var sameTarget = ta === tb;
    var first, note;
    if (crossed.length === 2) {
      first = null;
      note = "Both tracks are already past their lines - no race to run. " + UNCERTAIN;
    } else if (crossed.length === 1) {
      var w = crossed[0] === a.id ? a : b;
      var wt = crossed[0] === a.id ? ta : tb;
      first = crossed[0];
      note = '"' + w.title + '" already crossed the ' + fmt(wt) +
        ' plays line - the race is over. ' + UNCERTAIN;
    } else {
      if (da < db) first = a.id;
      else if (db < da) first = b.id;
      else first = null;
      var lineNote = sameTarget
        ? "the same finish line - the race is purely who closes the gap first"
        : "different finish lines - the race is who gets there first, not who runs fastest";
      var firstTitle = first === a.id ? a.title : (first === b.id ? b.title : null);
      note = "At lifetime pace from the 2026-10-11 snapshot, " +
        (first ? '"' + firstTitle + '" crosses first - ' + lineNote + "."
               : "the pair is tied at lifetime pace - no projected finisher.") +
        " " + UNCERTAIN;
    }
    return {
      a: a, b: b, ta: ta, tb: tb, na: na, nb: nb, da: da, db: db,
      sameTarget: sameTarget, crossed: crossed, first: first, note: note,
      gap: bankers1(Math.abs(da - db))
    };
  }

  function pairHash(a, b, t) {
    return "#h2h=" + encodeURIComponent(a) + "," + encodeURIComponent(b) + "," + t;
  }

  function renderH2H() {
    var selA = $("mr-h2h-a"), selB = $("mr-h2h-b"), selT = $("mr-h2h-t");
    var idA = selA.value, idB = selB.value;
    if (idA === idB) {
      // same-track guard: bump B to the next vault track
      idB = VAULT[(VAULT.indexOf(trackById(idA)) + 1) % VAULT.length].id;
      selB.value = idB;
    }
    var a = trackById(idA), b = trackById(idB), t = parseInt(selT.value, 10);
    if (!a || !b) { $("mr-h2h").innerHTML = '<p class="se-error">That track is not in the race data.</p>'; return; }
    var p = projectPair(a, b, t, t);
    function col(tr) { return '<th scope="col">' + esc(tr.title) + '</th>'; }
    function row(label, fa, fb) {
      return '<tr><th scope="row">' + label + '</th><td>' + fa + '</td><td>' + fb + '</td></tr>';
    }
    function statusCell(tr, n) {
      return n <= 0 ? '<strong>Already past the line</strong>' : fmt(n) + " needed";
    }
    function daysCell(d, crossed) {
      return crossed ? "—" : "~" + fmt(d) + " days";
    }
    var verdict = p.first
      ? '<p class="mr-verdict">At lifetime pace from the 2026-10-11 snapshot, <strong>' +
        esc(p.first === a.id ? a.title : b.title) +
        '</strong> crosses first — ' + esc(p.note) + '</p>'
      : '<p class="mr-verdict">' + esc(p.note) + '</p>';
    $("mr-h2h").innerHTML =
      '<div class="table-wrap"><table class="data-table">' +
      '<caption class="visually-hidden">Head-to-head: ' + esc(a.title) + ' vs ' + esc(b.title) +
      ' at ' + fmt(t) + ' plays</caption>' +
      '<thead><tr><th scope="col"><span class="visually-hidden">Measure</span></th>' + col(a) + col(b) + '</tr></thead>' +
      '<tbody>' +
      row("Plays", fmt(a.plays), fmt(b.plays)) +
      row("Target", fmt(t) + " plays", fmt(t) + " plays") +
      row("Status", statusCell(a, p.na), statusCell(b, p.nb)) +
      row("Pace (lifetime avg)", "~" + esc(a.pace_per_day) + "/day", "~" + esc(b.pace_per_day) + "/day") +
      row("Days at pace", daysCell(p.da, p.na <= 0), daysCell(p.db, p.nb <= 0)) +
      '<tr><th scope="row">Projected finish gap</th><td colspan="2">' +
        (p.crossed.length ? "No race to run" : "~" + fmt(p.gap) + " days") + '</td></tr>' +
      '</tbody></table></div>' +
      verdict +
      '<p class="chart-sub">Keep digging: ' +
      '<a href="' + esc(a.page) + '">' + esc(a.title) + '</a> · ' +
      '<a href="' + esc(b.page) + '">' + esc(b.title) + '</a> · ' +
      a.producers.concat(b.producers).map(function (pr) {
        return '<a href="' + esc(pr.page) + '">' + esc(pr.name) + '</a>';
      }).join(" · ") + ' <span class="chart-sub">(producers)</span></p>';
    var h = pairHash(idA, idB, t);
    if (location.hash !== h) history.replaceState(null, "", h);
  }

  function bootH2H(data) {
    VAULT = data.vault_pace.tracks;
    var selA = $("mr-h2h-a"), selB = $("mr-h2h-b"), selT = $("mr-h2h-t");
    // the 4 active races first ("in a race now"), then the full vault
    var activeIds = {};
    data.closest_races.forEach(function (rid) {
      var r = null;
      data.play_races.forEach(function (x) { if (x.id === rid) r = x; });
      if (r) activeIds[r.title] = true;
    });
    function group(label, tracks) {
      var g = document.createElement("optgroup");
      g.label = label;
      tracks.forEach(function (v) {
        var o = document.createElement("option");
        o.value = v.id; o.textContent = v.title;
        g.appendChild(o);
      });
      return g;
    }
    var active = VAULT.filter(function (v) { return activeIds[v.title]; });
    var rest = VAULT.filter(function (v) { return !activeIds[v.title]; });
    [selA, selB].forEach(function (sel) {
      sel.appendChild(group("In a race now", active));
      sel.appendChild(group("All vault tracks", rest));
    });
    // deep link: #h2h=<idA>,<idB>,<target>; default = the featured closest pair
    var feat = data.head_to_head.pairs[0];
    var idA = null, idB = null, t = feat.a_target;
    var m = /^#h2h=([^,]+),([^,]+),(\d+)$/.exec(location.hash);
    if (m) {
      var a = trackById(decodeURIComponent(m[1]));
      var b = trackById(decodeURIComponent(m[2]));
      var tt = parseInt(m[3], 10);
      if (a && b && [1000, 10000, 20000, 30000].indexOf(tt) !== -1) {
        idA = a.id; idB = b.id; t = tt;
      }
    }
    if (!idA) {
      // featured pair: map the race ids back to vault tracks by title
      var fa = trackById(VAULT.filter(function (v) { return v.title === feat.a_title; })[0].id);
      var fb = trackById(VAULT.filter(function (v) { return v.title === feat.b_title; })[0].id);
      idA = fa.id; idB = fb.id;
    }
    selA.value = idA; selB.value = idB; selT.value = String(t);
    selA.addEventListener("change", renderH2H);
    selB.addEventListener("change", renderH2H);
    selT.addEventListener("change", renderH2H);
    renderH2H();
    if (m) {
      // shared deep link: land on the matchup (instant scroll — motion-safe)
      var sec = $("h2h");
      if (sec && sec.scrollIntoView) sec.scrollIntoView();
    }
  }

  /* ---------------- the climb: the full summit leaderboard ---------------- */
  var CLIMB = null, CLIMB_SHOW_ALL = false;

  function renderClimb() {
    var q = $("mr-climb-q").value.trim().toLowerCase();
    var rows = CLIMB.filter(function (c) {
      return !q || c.title.toLowerCase().indexOf(q) !== -1;
    });
    var shown = CLIMB_SHOW_ALL || q ? rows : rows.slice(0, 25);
    var html = shown.map(function (c) {
      return '<tr><td class="num">' + c.rank + '</td>' +
        '<td><a href="' + esc(c.page) + '">' + esc(c.title) + '</a></td>' +
        '<td class="num">' + fmt(c.plays) + '</td>' +
        '<td class="num">' + fmt(c.gap) + '</td>' +
        '<td class="num">~' + esc(c.pace_per_day) + '</td>' +
        '<td class="num">~' + fmt(c.catch_days_at_pace) + '</td></tr>';
    }).join("");
    var more = (!CLIMB_SHOW_ALL && !q && rows.length > 25)
      ? '<div class="btn-row"><button class="btn btn-sm btn-ghost" id="mr-climb-all" type="button">Show all ' +
        rows.length + ' climbers</button></div>'
      : "";
    var empty = rows.length === 0
      ? '<p class="se-error">No climbers match that filter.</p>' : "";
    $("mr-climb").innerHTML =
      '<div class="table-wrap"><table class="data-table">' +
      '<caption class="visually-hidden">The Climb: every summit-eligible vault track ranked by catch time at lifetime pace</caption>' +
      '<thead><tr><th scope="col">Rank</th><th scope="col">Track</th><th scope="col">Plays</th>' +
      '<th scope="col">Behind summit</th><th scope="col">Pace/day</th><th scope="col">Catch time (days)</th></tr></thead>' +
      '<tbody>' + html + '</tbody></table></div>' + more + empty +
      '<p class="chart-sub">Catch time is plain division on the 2026-10-11 snapshot — an estimate, never a prediction. ' +
      'Showing ' + shown.length + ' of ' + rows.length + ' climbers' +
      (q ? ' matching "' + esc($("mr-climb-q").value.trim()) + '"' : "") + '.</p>';
    var btn = $("mr-climb-all");
    if (btn) btn.addEventListener("click", function () {
      CLIMB_SHOW_ALL = true; renderClimb();
    });
  }

  function bootClimb(data) {
    CLIMB = data.the_climb.entries;
    $("mr-climb-method").textContent = data.the_climb.method;
    $("mr-climb-q").addEventListener("input", function () { renderClimb(); });
    renderClimb();
  }

  /* ---------------- the summit race ---------------- */
  function renderSummit(data) {
    var s = data.summit_race;
    $("mr-summit-elig").textContent = s.eligibility;
    var rows = s.contenders.map(function (c, i) {
      var title = c.page ? '<a href="' + esc(c.page) + '">' + esc(c.title) + '</a>'
        : esc(c.title);
      return '<li><span class="mr-rank" aria-hidden="true">#' + (i + 1) + '</span> ' +
        title + ' — ' + fmt(c.plays) + ' plays, <strong>' + fmt(c.gap) +
        ' behind</strong>. Catch time at lifetime pace: ~' +
        fmt(c.catch_days_at_pace) + ' days (estimate, not a prediction).</li>';
    }).join("");
    $("mr-summit").innerHTML =
      '<div class="mr-holder"><p class="mr-summit-title"><a href="' +
      esc(s.holder.page) + '">' + esc(s.holder.title) + '</a></p>' +
      '<p class="mr-summit-num">' + fmt(s.holder.plays) + ' <span>plays</span></p>' +
      '<p class="chart-sub">The summit record — the highest-play transmission in the vault, ' +
      esc(s.holder.date) + '.</p></div>' +
      '<ol class="mr-contenders">' + rows + '</ol>';
  }

  /* ---------------- the record book ---------------- */
  function renderRecords(data) {
    function items(recs) {
      return recs.map(function (r) {
        var head = r.page ? '<a href="' + esc(r.page) + '">' + esc(r.record) + '</a>'
          : esc(r.record);
        return '<div class="mr-rec"><dt>' + head + '</dt><dd><strong>' +
          esc(r.value) + '</strong> — ' + esc(r.holder) +
          ' <span class="chart-sub">' + esc(r.detail) + '</span></dd></div>';
      }).join("");
    }
    $("mr-records").innerHTML =
      '<div><h3>Session records</h3><dl>' + items(data.session_records) + '</dl></div>' +
      '<div><h3>Era records</h3><dl>' + items(data.era_records) + '</dl></div>';
  }

  /* ---------------- race history ---------------- */
  function renderHistory(data) {
    var h = data.race_history;
    $("mr-history-method").textContent = h.method;
    var html = h.completed_crossings.map(function (m) {
      return '<li><strong>' + esc(m.name) + '</strong> — ' + esc(m.date) +
        (m.title ? ' <span class="chart-sub">' + esc(m.title) + '</span>' : '') +
        '</li>';
    }).join("");
    $("mr-crossed").innerHTML = '<ul class="story-list">' + html + '</ul>';
    var rows = h.threshold_winners.map(function (t) {
      return '<tr><th scope="row">' + esc(t.label) + '</th>' +
        '<td class="num">' + fmt(t.crossed_count) + '</td>' +
        '<td><a href="' + esc(t.leader.page) + '">' + esc(t.leader.title) + '</a></td>' +
        '<td class="num">' + fmt(t.leader.plays) + '</td></tr>';
    }).join("");
    $("mr-winners").innerHTML =
      '<div class="table-wrap"><table class="data-table">' +
      '<caption class="visually-hidden">Threshold winners: vault tracks past each round-number play count</caption>' +
      '<thead><tr><th scope="col">Threshold</th><th scope="col">Tracks past it</th><th scope="col">Leader</th><th scope="col">Leader plays</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>';
    var pf = h.photo_finish;
    $("mr-photo").innerHTML =
      '<article class="mr-photo-card">' +
      '<p><strong>' + esc(pf.a.name) + '</strong> <span class="chart-sub">' + esc(pf.a.date) + '</span> ' +
      'vs <strong>' + esc(pf.b.name) + '</strong> <span class="chart-sub">' + esc(pf.b.date) + '</span></p>' +
      '<p class="mr-summit-num">' + fmt(pf.gap_days) + ' <span>days apart</span></p>' +
      '<p class="chart-sub">' + esc(pf.note) + '</p>' +
      '</article>';
  }

  /* ---------------- methodology ---------------- */
  function renderMethod(data) {
    $("mr-method").textContent = data.pace_definition + " " + data.snapshot_provenance;
  }

  /* ---------------- boot ---------------- */
  loadData("api/v1/milestone-races.json").then(function (data) {
    renderClosest(data);
    renderWatch(data);
    bootH2H(data);
    renderSummit(data);
    bootClimb(data);
    renderRecords(data);
    renderHistory(data);
    renderMethod(data);
    if (ADM.reveal) ADM.reveal();
  }, function () {
    fail(["mr-closest", "mr-watch", "mr-h2h", "mr-summit", "mr-climb",
      "mr-records", "mr-crossed", "mr-winners", "mr-photo"]);
  });
})();
