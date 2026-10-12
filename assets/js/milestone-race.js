/* Aster da Master — milestone race (wave 22).
   Renders milestone-race.html from api/v1/milestone-races.json.
   Every figure comes from the JSON; nothing is computed client-side
   beyond display formatting. Pace figures are stated as estimates,
   never predictions. */
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

  /* ---------------- closest races ---------------- */
  function raceCard(r, rank) {
    var bar = '<div class="mr-bar" role="progressbar" aria-valuenow="' +
      esc(r.progress_pct) + '" aria-valuemin="0" aria-valuemax="100" ' +
      'aria-label="' + esc(r.title) + ': ' + esc(r.progress_pct) +
      ' percent of the way to ' + esc(r.milestone) + '">' +
      '<span style="width:' + esc(r.progress_pct) + '%"></span></div>';
    return '<article class="mr-race">' +
      '<p class="mr-rank" aria-label="Race ' + rank + ' of 4">#' + rank + '</p>' +
      '<h3><a href="' + esc(r.page) + '">' + esc(r.title) + '</a></h3>' +
      '<p class="mr-line"><strong>' + fmt(r.plays) + '</strong> of ' +
      fmt(r.target) + ' plays — <strong>' + fmt(r.needed) + ' needed</strong></p>' +
      bar +
      '<p class="mr-pace">Pace: ~' + esc(r.pace_per_day) + ' plays/day ' +
      '(lifetime average to the 2026-10-11 snapshot). At this pace, the gap ' +
      'closes in <strong>~' + fmt(r.days_at_pace) + ' days</strong> — ' +
      'an estimate, not a prediction.</p>' +
      '</article>';
  }

  function renderClosest(data) {
    var byId = {};
    data.play_races.forEach(function (r) { byId[r.id] = r; });
    var html = data.closest_races.map(function (rid, i) {
      return raceCard(byId[rid], i + 1);
    }).join("");
    $("mr-closest").innerHTML = html;
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

  /* ---------------- just crossed ---------------- */
  function renderCrossed(data) {
    var html = data.just_crossed.map(function (m) {
      return '<li><strong>' + esc(m.name) + '</strong> — ' + esc(m.date) +
        (m.title ? ' <span class="chart-sub">' + esc(m.title) + '</span>' : '') +
        '</li>';
    }).join("");
    $("mr-crossed").innerHTML = '<ul class="story-list">' + html + '</ul>';
  }

  /* ---------------- methodology ---------------- */
  function renderMethod(data) {
    $("mr-method").textContent = data.pace_definition;
  }

  /* ---------------- boot ---------------- */
  loadData("api/v1/milestone-races.json").then(function (data) {
    renderClosest(data);
    renderSummit(data);
    renderRecords(data);
    renderCrossed(data);
    renderMethod(data);
    if (ADM.reveal) ADM.reveal();
  }, function () {
    fail(["mr-closest", "mr-summit", "mr-records", "mr-crossed"]);
  });
})();
