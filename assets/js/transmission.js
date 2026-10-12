/* TRANSMISSION 3.0 — the flagship guided journey: six eras + seven data chapters.
   Era stops come from api/v1/transmission.json (incl. the 2026 extras block on
   The Return). Era enrichment ("the archive's reading") loads LIVE from
   api/v1/eras.json + api/v1/years.json — ranks, archive-play shares, per-year
   strips, deepest cuts, top word families; all computed, never authored.
   Data chapters pull LIVE from the real api/v1 JSON (no figures hardcoded, so
   future waves update the journey automatically):
     chapter-race    <- milestone-races.json (closest races + summit)
     chapter-record  <- milestone-races.json (records + just crossed)
     chapter-codex   <- codex-families.json  (word families)
     chapter-architects <- producer-deepdives.json (as-credited producers)
     chapter-seasons <- session-clusters.json (activity seasons + silences)
     chapter-deepcuts <- session-tools.json (deepest-sessions + deepest-transmissions rankings)
     chapter-horizon <- verified 2026-10-11 research pass, sourced inline
   If any optional file fails to load, its chapter degrades away gracefully.
   Titles/metadata only — never lyrics.
   Keyboard: in the journey, ←/→ step stops (Home/End jump), Esc in the map
   returns to the journey. Tab order follows rail → panel → controls.
   Motion: era changes ride the View Transitions API (crossfade on the panel)
   when available and allowed; otherwise the tuning flicker. Scroll-driven
   card/glow motion is CSS-only (animation-timeline) with @supports guards.
   Auto-play (~12s) is fully disabled under prefers-reduced-motion: manual
   stepping only. Progress (stop + visited map) persists via localStorage
   (resume from last stop; clearable) — the journey never auto-jumps. */
(function () {
  "use strict";

  var esc = window.ADM.esc;
  var fmt = window.ADM.fmt;
  var loadData = window.ADM.loadData;
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var VT = !REDUCED && typeof document.startViewTransition === "function";
  var AUTOPLAY_MS = 12000;
  var STORE_KEY = "adm.transmission.stop";
  var STORE_KEY_V = "adm.transmission.visited";

  var DATA = null, RACES = null, CODEX = null, ERASJ = null, YRS = null,
      CLUST = null, TOOLS = null, PD = null;
  var view = "entry";       // entry | journey | map | end
  var stops = [];           // [{kind,id,hash,label,name,span,era,deepDive,render,brief}]
  var stop = 0;
  var visited = {};         // stop index -> true
  var timer = null;

  var $ = function (id) { return document.getElementById(id); };
  var entryEl = $("tx-entry"), journeyEl = $("tx-journey"), mapEl = $("tx-map"), endEl = $("tx-end");
  var railEl = $("tx-rail"), innerEl = $("tx-era-inner"), eraEl = $("tx-era");
  var liveEl = $("tx-live");
  var autoplayBtn = $("tx-autoplay");

  /* ---------- views ---------- */
  function show(v) {
    view = v;
    entryEl.hidden = v !== "entry";
    journeyEl.hidden = v !== "journey";
    mapEl.hidden = v !== "map";
    endEl.hidden = v !== "end";
    if (v === "journey") focusStopHeading();
    if (v === "map") $("tx-map-heading").focus();
    if (v === "end") { renderEnd(); $("tx-end-heading").focus(); }
    if (v === "entry") { updateProgress(); $("tx-title").focus(); }
  }

  function announce(msg) { liveEl.textContent = ""; liveEl.textContent = msg; }

  function focusStopHeading() {
    var h = $("tx-era-heading");
    if (h) h.focus({ preventScroll: false });
  }

  /* ---------- progress persistence (stop + visited map) ---------- */
  function remember() {
    try {
      localStorage.setItem(STORE_KEY, String(stop));
      localStorage.setItem(STORE_KEY_V, JSON.stringify(Object.keys(visited).map(Number)));
    } catch (e) { /* private mode */ }
  }

  function savedStop() {
    try {
      var v = parseInt(localStorage.getItem(STORE_KEY), 10);
      return isNaN(v) ? null : v;
    } catch (e) { return null; }
  }

  function restoreVisited() {
    try {
      var arr = JSON.parse(localStorage.getItem(STORE_KEY_V) || "[]");
      if (arr && arr.length) {
        for (var i = 0; i < arr.length; i++) visited[arr[i]] = true;
      }
    } catch (e) { /* noop */ }
  }

  function clearProgress() {
    try {
      localStorage.removeItem(STORE_KEY);
      localStorage.removeItem(STORE_KEY_V);
    } catch (e) { /* noop */ }
    visited = {};
    stop = 0;
  }

  function visitedCount() { return Object.keys(visited).length; }

  function updateProgress() {
    var n = visitedCount();
    var pl = $("tx-progress");
    if (pl) pl.textContent = n + " of " + stops.length + " stops visited.";
    var cb = $("tx-clear");
    if (cb) cb.hidden = !(n > 0 || savedStop() != null);
  }

  /* ---------- shared row renderers ---------- */
  function trackRow(t) {
    return '<li class="tx-track"><span><a href="' + esc(t.page) + '">' + esc(t.title) + "</a>" +
      '<span class="tx-meta">' + esc(t.date) + "</span></span>" +
      '<span class="tx-plays">' + fmt(t.plays) + " plays</span></li>";
  }

  function sessionRow(s) {
    var name = s.deep_dive
      ? '<a href="' + esc(s.deep_dive) + '">' + esc(s.name) + '</a> <span class="tx-dd">deep dive</span>'
      : '<a href="sessions.html">' + esc(s.name) + "</a>";
    return '<li class="tx-sess">' + name +
      '<span class="tx-meta">' + s.track_count + " transmissions &middot; " + fmt(s.total_plays) +
      " plays &middot; " + s.days + " days</span></li>";
  }

  function collabRow(c) {
    return '<li class="tx-collab"><a href="' + esc(c.page) + '">' + esc(c.name) + "</a>" +
      '<span class="tx-meta">' + c.transmissions + " transmissions &middot; " + fmt(c.plays) + " plays</span></li>";
  }

  function mileRow(m) {
    var title = m.title ? " — \u201c" + esc(m.title) + "\u201d" : "";
    var date = m.date ? '<span class="tx-meta">' + esc(m.date) + "</span>" : "";
    return '<li class="tx-mile"><span class="m-name">' + esc(m.name) + "</span>" + title + date +
      '<p class="m-fact">' + esc(m.fact) + "</p></li>";
  }

  function statCell(v, l) {
    return '<div class="stat"><div class="stat-value">' + v + '</div><div class="stat-label">' + l + "</div></div>";
  }

  function deepDivePara(dd) {
    return '<p class="tx-era-dd"><a href="' + esc(dd.href) + '">' + esc(dd.text) + " &rarr;</a></p>";
  }

  /* ---------- the 2026 extras (only The Return carries them) ---------- */
  function renderExtras(x) {
    var singles = x.singles_2026.map(function (s) {
      return '<li class="tx-track"><span><a href="' + esc(s.page) + '">' + esc(s.title) + "</a>" +
        '<span class="tx-meta">' + esc(s.date) + "</span></span></li>";
    }).join("");
    var u = x.q4_watch.uncle;
    var uStatus = u.status === "announced"
      ? "Announced \u2014 expected " + esc(u.expected) + " (as of " + esc(u.as_of) + ")."
      : "Status: " + esc(u.status) + " (as of " + esc(u.as_of) + ").";
    var t = x.q4_watch.trilogy;
    return '<div class="tx-cols">' +
      '<div class="tx-block"><h3>The 2026 singles</h3><ol>' + singles + "</ol>" +
      '<p class="tx-note">' + esc(x.singles_note) + "</p></div>" +
      '<div class="tx-block"><h3>Q4 2026 watch</h3>' +
      '<div class="tx-mile"><span class="m-name">' + esc(u.label) + "</span>" +
      '<p class="m-fact">' + uStatus + " " + esc(u.note) + ' <a href="' + esc(u.figure_page) + '">The Uncle watch &rarr;</a></p></div>' +
      '<div class="tx-mile"><span class="m-name">' + esc(t.title) + "</span>" +
      '<p class="m-fact">' + esc(t.status) + ' <a href="' + esc(t.page) + '">The trilogy page &rarr;</a></p></div>' +
      "</div></div>" +
      '<p class="tx-note">' + esc(x.snapshot.note) + "</p>";
  }

  /* ---------- era enrichment: "the archive's reading" (live, computed) ---------- */
  function eraJSON(id) {
    if (!ERASJ) return null;
    for (var i = 0; i < ERASJ.eras.length; i++) {
      if (ERASJ.eras[i].id === id) return ERASJ.eras[i];
    }
    return null;
  }

  function renderReading(e) {
    var ej = eraJSON(e.id);
    if (!ej || !YRS || !ej.summary) return "";
    var s = ej.summary;
    var share = (s.archive_plays_share * 100);
    var shareTxt = share.toFixed(1);
    var yrs = e.years.map(function (y) {
      var r = YRS[y] || {};
      return { year: y, plays: r.plays || 0, tx: r.transmissions || 0 };
    });
    var maxP = Math.max.apply(null, yrs.map(function (y) { return y.plays; }).concat([1]));
    var strips = yrs.map(function (y) {
      var w = (y.plays / maxP * 100).toFixed(1);
      return '<div class="tx-yrow"><span class="y-lab">' + esc(y.year) + "</span>" +
        '<span class="y-bar" aria-hidden="true"><i style="width:' + w + '%"></i></span>' +
        '<span class="y-num">' + fmt(y.plays) + " plays &middot; " + y.tx + " tx</span></div>";
    }).join("");
    var dc = s.deepest_cut, tf = s.top_family, by = s.busiest_year;
    var stripLabel = yrs.map(function (y) { return y.year + ": " + fmt(y.plays) + " plays"; }).join(", ");
    return '<div class="tx-block tx-reading"><h3>The archive\u2019s reading</h3>' +
      '<p class="tx-readline">Rank <strong>#' + s.rank_by_plays + " of " + s.eras_total + "</strong> by plays &middot; " +
      "rank <strong>#" + s.rank_by_transmissions + " of " + s.eras_total + "</strong> by transmissions &middot; " +
      "<strong>" + shareTxt + "%</strong> of every play in the archive.</p>" +
      '<div class="tx-sharebar" role="img" aria-label="' + esc(e.name) + " holds " + shareTxt +
      ' percent of all archive plays"><div class="tx-sharebar-fill" style="width:' + shareTxt +
      '%"></div><span class="tx-sharebar-num">' + shareTxt + "%</span></div>" +
      '<div class="tx-yrows" role="img" aria-label="Plays per year in ' + esc(e.name) + ": " + esc(stripLabel) + '">' +
      strips + "</div>" +
      '<ul class="tx-readlist">' +
      '<li><span class="rl-lab">Deepest cut</span> <a href="' + esc(dc.page) + '">' + esc(dc.title) + "</a> &mdash; " + fmt(dc.plays) + " plays</li>" +
      '<li><span class="rl-lab">Busiest year</span> ' + esc(by.year) + " &mdash; " + by.transmissions + " transmissions, " + fmt(by.plays) + " plays</li>" +
      '<li><span class="rl-lab">Top word family</span> <a href="' + esc(tf.page) + '">' + esc(tf.name) + "</a> &mdash; " + fmt(tf.plays) + " plays</li>" +
      '<li><span class="rl-lab">Summoned voices</span> ' + s.collaborators_count + " voices &middot; " +
      (s.collab_plays_share * 100).toFixed(1) + "% of era plays carried a collaborator</li>" +
      '<li><span class="rl-lab">Milestones filed</span> ' + s.milestones_count + "</li>" +
      "</ul>" +
      '<p class="tx-note">Computed from the archive at load time \u2014 the archive assigns no meaning it doesn\u2019t state.</p>' +
      "</div>";
  }

  /* ---------- era stop rendering ---------- */
  function renderEraPanel(e) {
    var collabs = e.collaborators.length
      ? "<ul>" + e.collaborators.map(collabRow).join("") + "</ul>"
      : '<p class="tx-empty">No title-credited collaborators this era — every transmission stands alone.</p>';
    var miles = e.milestones.length
      ? "<ul>" + e.milestones.map(mileRow).join("") + "</ul>"
      : '<p class="tx-empty">No milestones filed for this era. The numbers speak.</p>';
    return '<div class="stat-grid">' +
      statCell(fmt(e.transmissions), "Transmissions") +
      statCell(fmt(e.plays), "Plays") +
      statCell(e.sessions, "Sessions") +
      statCell(e.distributor, "Distributor releases") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' + esc(e.signal) + "</blockquote>" +
      renderReading(e) +
      (e.extras ? renderExtras(e.extras) : "") +
      '<div class="tx-cols">' +
      '<div class="tx-block"><h3>Defining tracks</h3><ol>' + e.top_tracks.map(trackRow).join("") + "</ol></div>" +
      '<div class="tx-block"><h3>Key sessions</h3><ul>' + e.key_sessions.map(sessionRow).join("") + "</ul></div>" +
      '<div class="tx-block"><h3>Summoned voices</h3>' + collabs + "</div>" +
      '<div class="tx-block"><h3>Milestones</h3>' + miles + "</div>" +
      "</div>";
  }

  /* ---------- data chapter: THE RACE (from milestone-races.json) ---------- */
  function raceById(id) {
    for (var i = 0; i < RACES.play_races.length; i++) {
      if (RACES.play_races[i].id === id) return RACES.play_races[i];
    }
    return null;
  }

  function raceCard(r) {
    var pct = Math.max(0, Math.min(100, r.progress_pct));
    return '<li class="tx-race"><a href="' + esc(r.page) + '">' + esc(r.title) + "</a>" +
      '<div class="tx-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + pct.toFixed(1) + '" ' +
      'aria-label="' + esc(r.title) + ": " + fmt(r.plays) + " of " + fmt(r.target) + " plays, " + fmt(r.needed) + ' to go">' +
      '<div class="tx-bar-fill" style="width:' + pct.toFixed(1) + '%"></div></div>' +
      '<span class="tx-meta">' + fmt(r.plays) + " / " + fmt(r.target) + " plays &middot; " + fmt(r.needed) +
      " to go &middot; ~" + fmt(Math.round(r.days_at_pace)) + " days at lifetime pace</span></li>";
  }

  function renderRace() {
    var races = RACES.closest_races.map(raceById).filter(Boolean).slice(0, 3);
    var h = RACES.summit_race.holder;
    var nearest = Math.min.apply(null, races.map(function (r) { return r.needed; }));
    var contenders = RACES.summit_race.contenders.slice(0, 3).map(function (c) {
      var link = c.page ? '<a href="' + esc(c.page) + '">' + esc(c.title) + "</a>" : esc(c.title);
      return '<li class="tx-track"><span>' + link +
        '<span class="tx-meta">' + esc(c.date) + "</span></span>" +
        '<span class="tx-plays">' + fmt(c.plays) + " plays</span></li>";
    }).join("");
    return '<div class="stat-grid">' +
      statCell(RACES.play_races.length, "Play-count races") +
      statCell(fmt(nearest), "Nearest gap (plays)") +
      statCell(fmt(h.plays), "Summit plays") +
      statCell(RACES.plays_snapshot, "Snapshot") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' +
      "Four tracks are closing in on round numbers, ranked by how soon the lifetime pace closes the gap. " +
      "At the top of the mountain, \u201c" + esc(h.title) + "\u201d sits at " + fmt(h.plays) +
      " plays — and nobody is close. Pace arithmetic only: estimates, never predictions.</blockquote>" +
      '<div class="tx-cols">' +
      '<div class="tx-block"><h3>Closest races</h3><ol class="tx-races">' + races.map(raceCard).join("") + "</ol></div>" +
      '<div class="tx-block"><h3>The summit</h3>' +
      '<div class="tx-mile"><span class="m-name"><a href="' + esc(h.page) + '">' + esc(h.title) + "</a></span>" +
      '<p class="m-fact">' + fmt(h.plays) + " plays &middot; uploaded " + esc(h.date) + ". The most-played vault transmission on record." + "</p></div>" +
      '<h3 style="margin-top:var(--space-5)">Nearest contenders</h3><ol>' + contenders + "</ol>" +
      '<p class="tx-note">' + esc(RACES.summit_race.eligibility) + "</p></div>" +
      "</div>" +
      '<p class="tx-note">Keep racing: <a href="milestone-race.html#watch">race to watch</a> &middot; ' +
      '<a href="milestone-race.html#h2h">head-to-head</a> &middot; ' +
      '<a href="milestone-race.html#history">race history</a> — every pair raced, every decided race on the books.</p>';
  }

  function raceBrief() {
    var races = RACES.closest_races.map(raceById).filter(Boolean);
    var nearest = races.length ? fmt(Math.min.apply(null, races.map(function (r) { return r.needed; }))) : "?";
    return [
      "The signal: four tracks closing in on round numbers — nearest gap " + nearest + " plays.",
      "The summit: \u201c" + RACES.summit_race.holder.title + "\u201d at " + fmt(RACES.summit_race.holder.plays) + " plays."
    ];
  }

  /* ---------- data chapter: THE RECORD BOOK (from milestone-races.json) ---------- */
  function renderRecordBook() {
    var sess = RACES.session_records.map(function (r) {
      var holder = r.page ? '<a href="' + esc(r.page) + '">' + esc(r.holder) + "</a>" : esc(r.holder);
      return '<li class="tx-mile"><span class="m-name">' + esc(r.record) + "</span>" +
        '<p class="m-fact">' + holder + " — " + esc(r.value) + " &middot; " + esc(r.detail) + "</p></li>";
    }).join("");
    var eras = RACES.era_records.map(function (r) {
      return '<li class="tx-mile"><span class="m-name">' + esc(r.record) + "</span>" +
        '<p class="m-fact"><a href="' + esc(r.page) + '">' + esc(r.holder) + "</a> — " + esc(r.value) +
        " &middot; " + esc(r.detail) + "</p></li>";
    }).join("");
    var crossed = RACES.just_crossed.map(function (j) {
      var title = j.title ? " — \u201c" + esc(j.title) + "\u201d" : "";
      return '<li class="tx-mile"><span class="m-name">' + esc(j.name) + "</span>" +
        '<span class="tx-meta">' + esc(j.date) + "</span>" + title +
        '<p class="m-fact">' + esc(j.fact) + "</p></li>";
    }).join("");
    return '<div class="stat-grid">' +
      statCell(RACES.session_records.length, "Session records") +
      statCell(RACES.era_records.length, "Era records") +
      statCell(RACES.just_crossed.length, "Just crossed") +
      statCell(RACES.plays_snapshot, "Snapshot") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' +
      "The archive keeps its own scoreboard: the most prolific session, the longest silence, the loudest and quietest rooms — and the milestones that fell most recently.</blockquote>" +
      '<div class="tx-cols">' +
      '<div class="tx-block"><h3>Session records</h3><ul>' + sess + "</ul></div>" +
      '<div class="tx-block"><h3>Era records</h3><ul>' + eras + "</ul></div>" +
      "</div>" +
      '<div class="tx-block" style="margin-top:var(--space-6)"><h3>Just crossed</h3><ul>' + crossed + "</ul></div>";
  }

  function recordBrief() {
    return [
      "The signal: the archive's own scoreboard — " + RACES.session_records.length +
      " session records, " + RACES.era_records.length + " era records, " +
      RACES.just_crossed.length + " just crossed."
    ];
  }

  /* ---------- data chapter: THE CODEX (from codex-families.json) ---------- */
  function renderCodex() {
    var fams = CODEX.families.slice().sort(function (a, b) { return b.track_count - a.track_count; }).slice(0, 5);
    var totalLinks = CODEX.families.reduce(function (n, f) { return n + f.track_count; }, 0);
    var loudest = CODEX.families.slice().sort(function (a, b) { return b.total_plays - a.total_plays; })[0];
    var rows = fams.map(function (f) {
      return '<li class="tx-mile"><span class="m-name"><a href="' + esc(f.page) + '">' + esc(f.name) + "</a></span>" +
        '<span class="tx-meta">' + esc(f.epithet) + "</span>" +
        '<p class="m-fact">' + f.track_count + " transmissions &middot; " + fmt(f.total_plays) + " plays &middot; " +
        esc(f.first_appearance.date) + " \u2192 " + esc(f.latest.date) + "</p>" +
        '<p class="m-fact tx-reading">' + esc(f.decoded.reading) + "</p></li>";
    }).join("");
    return '<div class="stat-grid">' +
      statCell(CODEX.family_count, "Word families") +
      statCell(totalLinks, "Family-track links") +
      statCell(fmt(loudest.total_plays), "Loudest family plays") +
      statCell(esc(loudest.name), "Loudest family") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' +
      "Sixteen word families run through the vault like watermarks — the mode-words, the rites, the light. " +
      "Tallied, never translated: the archive assigns no meaning the index doesn't state.</blockquote>" +
      '<div class="tx-block"><h3>Loudest families by transmissions</h3><ul>' + rows + "</ul></div>" +
      '<p class="tx-meta"><a href="codex-network.html">Map the families →</a> ' +
      "the sixteen families as a network: shared voices as edges, degrees of separation from Aster, and a connect-the-dots pathfinder.</p>" +
      '<p class="tx-meta"><a href="producers/">Producer deep dives →</a> ' +
      "the architects behind the sound — every as-credited producer, their productions, fingerprints, and scene context.</p>";
  }

  function codexBrief() {
    var totalLinks = CODEX.families.reduce(function (n, f) { return n + f.track_count; }, 0);
    return [
      "The signal: " + CODEX.family_count + " word families, " + totalLinks +
      " family-track links — tallied, never translated."
    ];
  }

  /* ---------- data chapter: THE ARCHITECTS (from producer-deepdives.json) ---------- */
  function renderArchitects() {
    var ps = PD.producers.slice().sort(function (a, b) {
      return b.production_count - a.production_count || b.total_plays - a.total_plays;
    });
    var ins = PD.insights;
    var top5 = ps.slice(0, 5);
    var rows = top5.map(function (p) {
      return '<li class="tx-track"><span><a href="' + esc(p.page) + '">' + esc(p.name) + "</a>" +
        '<span class="tx-meta">' + p.production_count + " production" + (p.production_count > 1 ? "s" : "") +
        " &middot; " + esc(p.years_active) + "</span></span>" +
        '<span class="tx-plays">' + fmt(p.total_plays) + " plays</span></li>";
    }).join("");
    var researched = ps.filter(function (p) { return p.research; });
    var rRows = researched.map(function (p) {
      return '<li class="tx-collab"><a href="' + esc(p.page) + '">' + esc(p.name) + "</a>" +
        '<span class="tx-meta">' + p.production_count + " production" + (p.production_count > 1 ? "s" : "") + "</span></li>";
    }).join("");
    return '<div class="stat-grid">' +
      statCell(ins.producer_count, "As-credited producers") +
      statCell(ins.total_credits, "Title prod. credits") +
      statCell(ins.researched_count, "Researched profiles") +
      statCell(PD.research_pass || PD.plays_snapshot, "Research pass") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' +
      "Every producer in the vault, as credited in the titles' own prod./produced-by fragments — verbatim, never merged beyond spelling. " +
      ins.solo_only_producers + " of " + ins.producer_count + " produced exactly once; the busiest hand in the vault is " +
      esc(ins.most_prolific.name) + " (" + ins.most_prolific.productions + " productions). " +
      "The most-played single production is \u201cTake Me\u201d \u2014 " + fmt(ins.most_plays.plays) +
      " plays (" + esc(ins.most_plays.name) + ").</blockquote>" +
      '<div class="tx-cols">' +
      '<div class="tx-block"><h3>Most prolific hands</h3><ol>' + rows + "</ol></div>" +
      '<div class="tx-block"><h3>Researched profiles</h3><ul>' + rRows + "</ul>" +
      '<p class="tx-note">' + esc(ins.note) + "</p></div>" +
      "</div>" +
      '<p class="tx-note">Fingerprints are computed from the credits, never biographies. ' +
      'Aliases are recorded where spelling variants slug identically.</p>';
  }

  function architectsBrief() {
    var ins = PD.insights;
    return [
      "The signal: " + ins.producer_count + " as-credited producers, " + ins.total_credits +
      " title credits — busiest hand " + ins.most_prolific.name + " (" + ins.most_prolific.productions + ")."
    ];
  }

  /* ---------- data chapter: THE SEASONS (from session-clusters.json) ---------- */
  function renderSeasons() {
    var ins = CLUST.insights;
    var longS = ins.longest_silence;
    var mp = ins.most_prolific, ls = ins.loudest_session, qs = ins.quietest_session;
    var seasonRows = CLUST.clusters.map(function (c) {
      return '<li class="tx-sess"><span>' + esc(c.label) + "</span>" +
        '<span class="tx-meta">' + esc(c.start) + " \u2192 " + esc(c.end) + " &middot; " +
        c.session_count + " sessions &middot; " + c.track_count + " transmissions &middot; " +
        fmt(c.total_plays) + " plays</span></li>";
    }).join("");
    var silRows = CLUST.silences.slice(0, 3).map(function (g) {
      return '<li class="tx-mile"><span class="m-name">' + g.days + " days</span>" +
        '<p class="m-fact">' + esc(g.from_session) + " \u2192 " + esc(g.to_session) + " &middot; " +
        esc(g.from_end) + " \u2192 " + esc(g.to_start) + "</p></li>";
    }).join("");
    return '<div class="stat-grid">' +
      statCell(ins.session_count, "Upload sessions") +
      statCell(ins.season_count, "Activity seasons") +
      statCell(CLUST.gaps.length, "Session gaps") +
      statCell(longS.days + " days", "Longest silence") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' +
      ins.session_count + " upload sessions fall into " + ins.season_count +
      " activity seasons — consecutive sessions separated by no more than " + CLUST.season_gap_days +
      " days (a stated browsing convention, not an artist fact). The most prolific session on record is \u201c" +
      esc(mp.name) + "\u201d \u2014 " + mp.track_count + " transmissions across " + esc(mp.start) + " \u2192 " + esc(mp.end) +
      ". The loudest room ever uploaded is \u201c" + esc(ls.name) + "\u201d (" + fmt(ls.total_plays) +
      " plays); the quietest, \u201c" + esc(qs.name) + "\u201d (" + fmt(qs.total_plays) + " plays).</blockquote>" +
      '<div class="tx-cols">' +
      '<div class="tx-block"><h3>The nine seasons</h3><ul>' + seasonRows + "</ul>" +
      '<p class="tx-note">Season rule: a new season starts when the gap to the next session exceeds ' +
      CLUST.season_gap_days + " days.</p></div>" +
      '<div class="tx-block"><h3>Longest silences</h3><ul>' + silRows + "</ul>" +
      '<p class="tx-note">The longest silence on record: ' + longS.days + " days between " +
      esc(longS.from_end) + " and " + esc(longS.to_start) + ".</p></div>" +
      "</div>";
  }

  function seasonsBrief() {
    var ins = CLUST.insights;
    return [
      "The signal: " + ins.session_count + " sessions in " + ins.season_count +
      " activity seasons — longest silence " + ins.longest_silence.days + " days."
    ];
  }

  /* ---------- data chapter: THE DEEP CUTS (from session-tools.json) ---------- */
  function renderDeepCuts() {
    var dc = TOOLS.deepest_cuts;
    var ins = TOOLS.insights;
    var rows = dc.ranking.slice(0, 10).map(function (r) {
      var link = r.deep_dive ? '<a href=\"' + esc(r.deep_dive) + '\">' + esc(r.name) + "</a>" : esc(r.name);
      return '<li class=\"tx-track\"><span><span class=\"tx-rank\">#' + r.rank + "</span> " + link +
        '<span class=\"tx-meta\">' + r.track_count + " transmissions &middot; " + fmt(r.total_plays) +
        " plays &middot; " + esc(r.era_name) + "</span></span>" +
        '<span class=\"tx-plays\">' + r.avg_plays_per_track + " avg</span></li>";
    }).join("");
    var deep = ins.deepest_session, quiet = ins.quietest_session;
    var tdc = TOOLS.track_deep_cuts || null;
    var tRows = "", tStats = "", tNote = "";
    if (tdc) {
      tRows = tdc.bottom_25.slice(0, 10).map(function (r) {
        var voices = r.voices.length ? " &middot; w/ " + esc(r.voices.join(", ")) : "";
        return '<li class=\"tx-track\"><span><span class=\"tx-rank\">#' + r.rank + "</span> " +
          '<a href=\"' + esc(r.page) + '\">' + esc(r.title) + "</a>" +
          '<span class=\"tx-meta\">' + esc(r.date) + " &middot; " + esc(r.era_name) + voices +
          "</span></span>" +
          '<span class=\"tx-plays\">' + fmt(r.plays) + " plays</span></li>";
      }).join("");
      var ti = tdc.insights;
      tStats = statCell(fmt(ti.quietest.plays) + " plays", "Quietest transmission") +
        statCell(fmt(ti.median_plays), "Median plays / transmission") +
        statCell(ti.under_100_plays + " of 185", "Transmissions under 100 plays");
      tNote = '<div class=\"tx-block\"><h3>The quietest transmissions</h3><ol>' + tRows + "</ol>" +
        '<p class=\"tx-note\"><strong>The formula:</strong> ' + esc(tdc.formula) + "</p>" +
        '<p class=\"tx-note\">The full quietest-25 lives on the ' +
        '<a href=\"sessions-explorer.html#se-trackdeep\">sessions explorer</a>. ' +
        "Nine of the 185 vault transmissions sit under 100 plays; the median is " +
        fmt(ti.median_plays) + ".</p></div>";
    }
    return '<div class=\"stat-grid\">' +
      statCell(dc.ranking.length, "Ranked sessions") +
      statCell(dc.excluded_single_track_sessions, "Single-track sessions excluded") +
      statCell(deep.avg_plays_per_track, "Deepest avg (plays/tx)") +
      tStats +
      statCell(TOOLS.plays_snapshot, "Snapshot") +
      "</div>" +
      '<blockquote class=\"tx-signal\"><span class=\"sig-lab\">The signal</span>' +
      "The quietest rooms in the vault, ranked by average plays per transmission. The deepest session on record is \u201c" +
      esc(deep.name) + "\u201d \u2014 " + deep.avg_plays_per_track + " plays per transmission across " +
      "its two tracks." +
      (tdc ? " And the quietest single transmission ever uploaded is \u201c" +
        esc(tdc.insights.quietest.title) + "\u201d \u2014 " +
        fmt(tdc.insights.quietest.plays) + " plays." : "") +
      " An editorial ranking, not an artist fact.</blockquote>" +
      '<div class=\"tx-block\"><h3>The deepest sessions</h3><ol>' + rows + "</ol>" +
      '<p class=\"tx-note\"><strong>The formula:</strong> ' + esc(dc.formula) + "</p>" +
      '<p class=\"tx-note\">The quietest single session ever uploaded: \u201c' + esc(quiet.name) + "\u201d \u2014 " +
      fmt(quiet.total_plays) + " plays. Play counts are a single snapshot (" + esc(TOOLS.plays_snapshot) +
      ") \u2014 no trajectories are drawn from them.</p></div>" +
      tNote;
  }

  function deepCutsBrief() {
    var deep = TOOLS.insights.deepest_session;
    var tdc = TOOLS.track_deep_cuts;
    var extra = tdc ? " Quietest transmission: \u201c" + tdc.insights.quietest.title +
      "\u201d (" + tdc.insights.quietest.plays + " plays)." : "";
    return [
      "The signal: the vault's quietest sessions, ranked \u2014 deepest is \u201c" + deep.name +
      "\u201d at " + deep.avg_plays_per_track + " avg plays per transmission." + extra
    ];
  }


  /* ---------- data chapter: THE HORIZON (verified 2026-10-11 research pass)
     Hand-authored from the research report — every fact sourced, nothing from
     the archive's play counts. Status words only ("announced", "as of"),
     never released-claims. */
  function srcLink(href, text) {
    return '<a href="' + esc(href) + '" rel="noopener">' + esc(text) + "</a>";
  }

  function renderHorizon() {
    return '<div class="stat-grid">' +
      statCell("2026-10-16", "Uncle expected") +
      statCell("0", "New uploads past session-61") +
      statCell("0", "Trilogy confirmations") +
      statCell("2026-10-11", "Research pass") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' +
      "Beyond the vault: what the 2026-10-11 research pass found outside the archive. " +
      "The archive itself holds no uploads past session-61 (2026-10-02) and no distributor releases past the May 2026 singles — " +
      "so nothing here is an artist claim. Every item carries its source.</blockquote>" +
      '<div class="tx-cols">' +
      '<div class="tx-block"><h3>Fish Narc &mdash; \u201cUncle\u201d</h3>' +
      '<div class="tx-mile"><span class="m-name">Fifth solo LP, expected 2026-10-16</span>' +
      '<p class="m-fact">Via K Records (catalog KLP313), 11 tracks, co-produced with Alex Farrar (Wednesday, MJ Lenderman, Fiddlehead). ' +
      "Singles: \u201cMuch Less Me\u201d (Aug 18, 2026) and \u201cBig Dumb World\u201d (Sept 15, 2026). " +
      "Fall tour: Oct 29 Los Angeles @ Gold Diggers \u00b7 Nov 6 Kingston NY @ Tubby\u2019s \u00b7 Nov 7 Ridgewood NY @ Stone Circle Theatre.</p>" +
      '<p class="m-fact">Status as of 2026-10-11: announced, pre-release \u2014 never claimed released early. ' +
      "Sources: " + srcLink("https://stereogum.com/2508537/fish-narc-announces-new-album-uncle-hear-much-less-me/music", "Stereogum (announcement)") + ", " +
      srcLink("https://stereogum.com/2511545/fish-narc-big-dumb-world/music", "Stereogum (\u201cBig Dumb World\u201d)") + ", " +
      srcLink("https://consequence.net/music-albums-released-2026/", "Consequence") + ", " +
      srcLink("https://www.faygoluvers.net/v5/2026/09/fish-narc-announces-new-album-uncle-on-k-records/", "Faygoluvers") +
      ". " + srcLink("circle/fish-narc.html", "The Uncle watch \u2192") + "</p></div></div>" +
      '<div class="tx-block"><h3>capoxxo &mdash; active this fall</h3>' +
      '<div class="tx-mile"><span class="m-name">New activity off the vault\u2019s edge</span>' +
      '<p class="m-fact">\u201csmoke one right now\u201d ft. mayh3mp \u2014 official video ~Sept 13, 2026 (ASTARI EXCLUSIVE; video by mikester; prod. credited luvpurp &amp; nyli). ' +
      "\u201care we cool\u201d \u2014 May 2, 2026 (DistroKid). " +
      "<em>Persona</em> cassette with mayh3mp (Cult Love Sound Tapes, 100 hand-numbered, sold out).</p>" +
      '<p class="m-fact">Touring: off tour per Songkick; zero setlists on setlist.fm. Sources: ' +
      srcLink("https://www.youtube.com/watch?v=lf4WylI5-8o", "YouTube (\u201csmoke one right now\u201d)") + ", " +
      srcLink("https://www.youtube.com/watch?v=sE7jnjhIBpU", "YouTube (\u201care we cool\u201d)") + ", " +
      srcLink("https://cultlovesoundtapes.bandcamp.com/album/persona", "Cult Love Sound Tapes") + ", " +
      srcLink("https://www.songkick.com/artists/9749264-capoxxo", "Songkick") + ", " +
      srcLink("https://www.setlist.fm/setlists/capoxxo-53f3e735.html", "setlist.fm") +
      ". " + srcLink("circle/capoxxo.html", "capoxxo\u2019s circle page \u2192") + "</p></div></div>" +
      "</div>" +
      '<div class="tx-cols" style="margin-top:var(--space-6)">' +
      '<div class="tx-block"><h3>The Litemode Trilogy &mdash; still unconfirmed</h3>' +
      '<div class="tx-mile"><span class="m-name">No movement as of 2026-10-11</span>' +
      '<p class="m-fact">No titles, no dates, no tracklists, no announcements, no fan discussion found anywhere public. ' +
      "The only evidence on record is the artist\u2019s own SoundCloud bio line. " +
      "The archive marks it unconfirmed rather than inventing a meaning. " +
      srcLink("trilogy.html", "The trilogy page \u2192") + "</p></div></div>" +
      '<div class="tx-block"><h3>The vault\u2019s edge</h3>' +
      '<div class="tx-mile"><span class="m-name">Nothing new on record</span>' +
      '<p class="m-fact">Newest upload on record: session-61, \u201cturn up w me (prod_timmy)\u201d, 2026-10-02. ' +
      "Newest distributor releases: the May 2026 singles (\u201cLiving With The Big Shots\u201d, \u201c9 Trips\u201d, \u201cWriting Books\u201d; \u201cThe Night Ends Yeaaa\u201d March 2026) " +
      "per the iHeart catalog listing. No new uploads, no new releases \u2014 the archive reports what it has.</p></div></div>" +
      "</div>";
  }

  function horizonBrief() {
    return [
      "The signal: Fish Narc's \u201cUncle\u201d expected 2026-10-16 (announced, pre-release) — " +
      "no new Aster uploads past session-61 (2026-10-02), no trilogy confirmation."
    ];
  }

  /* ---------- stop assembly ---------- */
  function buildStops() {
    var list = DATA.eras.map(function (e) {
      var ej = eraJSON(e.id);
      var deepest = ej && ej.summary ? {
        title: ej.summary.deepest_cut.title,
        plays: ej.summary.deepest_cut.plays,
        page: ej.summary.deepest_cut.page
      } : null;
      return {
        kind: "era", era: e, id: "era-" + e.id, hash: "era-" + e.id,
        label: "Era", name: e.name, span: e.span, deepest: deepest,
        deepDive: { href: "eras/" + e.id + ".html", text: "Deep dive: " + e.name },
        render: function () { return renderEraPanel(e); }
      };
    });
    if (RACES) {
      list.push({
        kind: "chapter", id: "chapter-race", hash: "chapter-race",
        label: "Data chapter", name: "The Race", span: "four play-count races \u00b7 the summit chase",
        deepDive: { href: "milestone-race.html", text: "Deep dive: the milestone race" },
        render: renderRace, brief: raceBrief
      });
      list.push({
        kind: "chapter", id: "chapter-record", hash: "chapter-record",
        label: "Data chapter", name: "The Record Book", span: "session records \u00b7 era records \u00b7 just crossed",
        deepDive: { href: "milestone-race.html", text: "Deep dive: the milestone race" },
        render: renderRecordBook, brief: recordBrief
      });
    }
    if (CODEX) {
      list.push({
        kind: "chapter", id: "chapter-codex", hash: "chapter-codex",
        label: "Data chapter", name: "The Codex", span: "sixteen word families \u00b7 the vocabulary",
        deepDive: { href: "decoder.html", text: "Deep dive: the decoder" },
        render: renderCodex, brief: codexBrief
      });
    }
    if (PD) {
      list.push({
        kind: "chapter", id: "chapter-architects", hash: "chapter-architects",
        label: "Data chapter", name: "The Architects", span: "113 as-credited producers \u00b7 the hands",
        deepDive: { href: "producers/", text: "Deep dive: the producers" },
        render: renderArchitects, brief: architectsBrief
      });
    }
    if (CLUST) {
      list.push({
        kind: "chapter", id: "chapter-seasons", hash: "chapter-seasons",
        label: "Data chapter", name: "The Seasons", span: "61 sessions \u00b7 9 activity seasons",
        deepDive: { href: "sessions-explorer.html", text: "Deep dive: the sessions explorer" },
        render: renderSeasons, brief: seasonsBrief
      });
    }
    if (TOOLS) {
      list.push({
        kind: "chapter", id: "chapter-deepcuts", hash: "chapter-deepcuts",
        label: "Data chapter", name: "The Deep Cuts", span: "the quietest rooms + transmissions \u00b7 ranked",
        deepDive: { href: "sessions-explorer.html", text: "Deep dive: the sessions explorer" },
        render: renderDeepCuts, brief: deepCutsBrief
      });
    }
    list.push({
      kind: "chapter", id: "chapter-horizon", hash: "chapter-horizon",
      label: "Data chapter", name: "The Horizon", span: "beyond the vault \u00b7 2026-10-11 research pass",
      deepDive: { href: "circle/fish-narc.html", text: "Deep dive: the Uncle watch" },
      render: renderHorizon, brief: horizonBrief
    });
    return list;
  }

  function pad(n) { return ("0" + (n + 1)).slice(-2); }

  /* ---------- rendering ---------- */
  function renderRail() {
    railEl.innerHTML = stops.map(function (s, i) {
      var cur = i === stop ? ' aria-current="step"' : "";
      var seen = visited[i] ? ' <span class="tx-visited" aria-hidden="true">\u25cf</span>' : "";
      var al = "Stop " + (i + 1) + " of " + stops.length + ", " + s.label + ": " + s.name +
        (visited[i] ? ", visited" : "");
      return '<li><button type="button" class="tx-node" data-stop="' + i + '"' + cur + ' aria-label="' + esc(al) + '">' +
        '<span class="n-num">' + pad(i) + " / " + pad(stops.length - 1) + seen + "</span>" +
        '<span class="n-name">' + esc(s.name) + "</span>" +
        '<span class="tx-meta">' + esc(s.span || "") + "</span></button></li>";
    }).join("");
  }

  function renderCrumb() {
    var s = stops[stop];
    var crumb = $("tx-crumb");
    if (!crumb) return;
    crumb.innerHTML = '<ol><li><a href="transmission.html">Transmission</a></li>' +
      '<li><span class="crumb-stop">Stop ' + (stop + 1) + " of " + stops.length + "</span></li>" +
      '<li aria-current="page">' + esc(s.name) + "</li></ol>";
    var prev = stops[stop - 1], next = stops[stop + 1];
    $("tx-prev").setAttribute("aria-label", prev ? "Previous stop: " + prev.label + " — " + prev.name : "Previous stop");
    $("tx-next").setAttribute("aria-label", next ? "Next stop: " + next.label + " — " + next.name : "Next stop");
  }

  function renderStop() {
    var s = stops[stop];
    visited[stop] = true;
    var kick = s.kind === "era"
      ? '<span class="kicker"><span class="numeral">\u2726</span>Era ' + (eraIndex(stop) + 1) + " of " + DATA.eras.length + "</span>"
      : '<span class="kicker"><span class="numeral">\u2726</span>Data chapter</span>';
    innerEl.innerHTML =
      '<div class="tx-era-kicker">' + kick + '<span class="tx-span">' + esc(s.span || "") + "</span></div>" +
      '<h2 id="tx-era-heading" tabindex="-1">' + esc(s.name) + "</h2>" +
      (s.kind === "era" ? '<p class="tx-scene">' + esc(s.era.scene) + "</p>" : "") +
      s.render() +
      deepDivePara(s.deepDive);
    renderRail();
    renderCrumb();
    document.title = s.name + " \u00b7 Transmission \u2014 Aster da Master";
  }

  function eraIndex(i) {
    var n = 0;
    for (var k = 0; k < i; k++) { if (stops[k].kind === "era") n++; }
    return n;
  }

  function renderMap() {
    $("tx-map-grid").innerHTML = stops.map(function (s, i) {
      var seen = visited[i] ? ' <span class="tx-visited" aria-hidden="true">\u25cf</span>' : "";
      var stat = "";
      if (s.kind === "era") stat = fmt(s.era.transmissions) + " tx \u00b7 " + fmt(s.era.plays) + " plays";
      return '<div class="tx-map-item">' +
        '<button type="button" class="tx-map-card" data-stop="' + i + '">' +
        '<span class="c-num">' + esc(s.label.toUpperCase()) + " " + pad(i) + seen + "</span>" +
        '<span class="c-name">' + esc(s.name) + "</span>" +
        '<span class="c-stats">' + esc(stat || s.span || "") + "</span>" +
        "</button>" +
        '<a class="tx-map-dd" href="' + esc(s.deepDive.href) + '">' + esc(s.deepDive.text) + " &rarr;</a>" +
        "</div>";
    }).join("");
  }

  /* ---------- navigation ---------- */
  function afterNav(s, opts) {
    renderCrumb(); /* crumb holds prev/next names after the move */
    try {
      window.history.replaceState(null, "", "#" + s.hash);
    } catch (err) { /* file:// or sandboxed contexts: the link still works */ }
    announce("Stop " + (stop + 1) + " of " + stops.length + ": " + s.label + " — " + s.name +
      (s.span ? ", " + s.span : "") + ".");
    if (!VT && !REDUCED) {
      eraEl.classList.remove("tuning");
      void eraEl.offsetWidth; /* restart the tuning animation */
      eraEl.classList.add("tuning");
    }
    if (opts.focus !== false) focusStopHeading();
    if (view !== "journey") show("journey");
  }

  function goStop(i, opts) {
    opts = opts || {};
    stopAutoplay();
    if (i >= stops.length) { show("end"); return; }
    if (i < 0) i = 0;
    stop = i;
    if (VT) {
      /* view-transition crossfade on the panel; focus after it lands */
      var vt = document.startViewTransition(function () { renderStop(); remember(); });
      vt.finished.then(function () {
        if (opts.focus !== false) focusStopHeading();
      }, function () {
        if (opts.focus !== false) focusStopHeading();
      });
      afterNav(stops[stop], { focus: false });
    } else {
      renderStop();
      remember();
      afterNav(stops[stop], opts);
    }
  }

  function nextStop(manual) { goStop(stop + 1, { focus: manual !== false }); }
  function prevStop() { goStop(stop - 1); }

  /* ---------- auto-play ---------- */
  function startAutoplay() {
    if (REDUCED || timer) return;
    autoplayBtn.setAttribute("aria-pressed", "true");
    autoplayBtn.innerHTML = "&#10074;&#10074; Pause";
    timer = setInterval(function () {
      if (stop + 1 >= stops.length) { stopAutoplay(); show("end"); return; }
      stop += 1;
      renderStop();
      remember();
      var s = stops[stop];
      announce("Stop " + (stop + 1) + " of " + stops.length + ": " + s.label + " — " + s.name + ".");
    }, AUTOPLAY_MS);
    announce("Auto-play on: advancing every 12 seconds. Press pause to take over.");
  }

  function stopAutoplay() {
    if (timer) { clearInterval(timer); timer = null; }
    autoplayBtn.setAttribute("aria-pressed", "false");
    autoplayBtn.innerHTML = "&#9654; Press play";
  }

  /* ---------- share ---------- */
  function eraStops() { return stops.map(function (s, i) { return s.kind === "era" ? i : -1; }).filter(function (i) { return i >= 0; }); }

  function favoriteEra() {
    var idx = eraStops().filter(function (i) { return visited[i]; });
    if (!idx.length) idx = eraStops().slice(0, 1);
    return idx.reduce(function (a, b) { return stops[b].era.plays > stops[a].era.plays ? b : a; });
  }

  function shareText() {
    var fe = stops[favoriteEra()];
    var top = fe.era.top_tracks[0];
    var names = stops.map(function (s, i) { return visited[i] ? s.name : null; }).filter(Boolean);
    var n = visitedCount();
    var lines = [
      "MY TRANSMISSION \u2014 Aster da Master (2018 \u2192 2026)",
      "Stops visited: " + n + " of " + stops.length + (names.length ? " \u2014 " + names.join(" \u00b7 ") : ""),
      "Favorite era by plays: " + fe.name + " \u2014 " + fmt(fe.era.plays) + " plays across " + fe.era.transmissions + " transmissions",
      "Top track: \u201c" + top.title + "\u201d \u2014 " + fmt(top.plays) + " plays"
    ];
    if (fe.deepest) lines.push("Deepest cut in that era: \u201c" + fe.deepest.title + "\u201d \u2014 " + fmt(fe.deepest.plays) + " plays");
    lines.push("Signal: " + fe.era.signal);
    lines.push("Play counts: " + DATA.plays_snapshot + " snapshot. Titles only, never lyrics.");
    return lines.join("\n");
  }

  function stopBrief(s) {
    var base = window.location.href.split("#")[0];
    var L = [
      "TRANSMISSION BRIEF \u2014 Aster da Master",
      s.label.toUpperCase() + " \u2014 " + s.name,
      "Stop of the journey: " + base + "#" + s.hash
    ];
    if (s.span) L.push("(" + s.span + ")");
    if (s.kind === "era") {
      var e = s.era;
      L.push(fmt(e.transmissions) + " transmissions \u00b7 " + fmt(e.plays) + " plays \u00b7 " +
        e.sessions + " sessions \u00b7 " + e.distributor + " distributor releases");
      L.push("The signal: " + e.signal);
      var top = e.top_tracks[0];
      if (top) L.push("Top track: \u201c" + top.title + "\u201d \u2014 " + fmt(top.plays) + " plays");
      if (s.deepest) L.push("Deepest cut: \u201c" + s.deepest.title + "\u201d \u2014 " + fmt(s.deepest.plays) + " plays");
    } else if (typeof s.brief === "function") {
      L = L.concat(s.brief());
    }
    L.push("Deep dive: " + s.deepDive.href);
    return L.join("\n");
  }

  function copyText(text, btn, doneMsg) {
    var done = function () {
      var label = btn.getAttribute("data-label") || btn.textContent;
      btn.setAttribute("data-label", label);
      btn.textContent = "Copied \u2713";
      announce(doneMsg);
      setTimeout(function () { btn.textContent = label; }, 2000);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else {
      fallbackCopy(text, done);
    }
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* noop */ }
    document.body.removeChild(ta);
    done();
  }

  function copyTransmission(btn) {
    copyText(shareText(), btn,
      "Transmission copied: " + visitedCount() + " of " + stops.length +
      " stops visited. Favorite era by plays: " + stops[favoriteEra()].name + ".");
  }

  function copyStopLink(btn) {
    var s = stops[stop];
    var url = window.location.href.split("#")[0] + "#" + s.hash;
    copyText(url, btn, "Stop link copied: " + s.label + " — " + s.name + ".");
  }

  function copyBrief(btn) {
    var s = stops[stop];
    copyText(stopBrief(s), btn, "Stop brief copied: " + s.label + " — " + s.name + ".");
  }

  /* ---------- end card ---------- */
  function renderEnd() {
    var t = DATA.archive_totals;
    $("tx-end-stats").innerHTML =
      statCell(fmt(t.transmissions), "Transmissions, 2018\u20132026") +
      statCell(fmt(t.plays), "Plays (" + DATA.plays_snapshot + " snapshot)") +
      statCell(t.sessions, "Upload sessions") +
      statCell(stops.length, "Stops traversed");
    var box = $("tx-share-out");
    box.textContent = shareText();
    box.hidden = false;
    document.title = "Signal received \u00b7 Transmission \u2014 Aster da Master";
  }

  /* ---------- wiring ---------- */
  function wire() {
    $("tx-begin").addEventListener("click", function () { stop = 0; goStop(0); });
    var resumeBtn = $("tx-resume");
    if (resumeBtn) resumeBtn.addEventListener("click", function () {
      var v = savedStop();
      goStop(v == null ? 0 : Math.min(v, stops.length - 1));
    });
    var clearBtn = $("tx-clear");
    if (clearBtn) clearBtn.addEventListener("click", function () {
      clearProgress();
      updateProgress();
      var rb = $("tx-resume");
      if (rb) rb.hidden = true;
      announce("Progress cleared. The journey is back at the start.");
    });
    $("tx-open-map").addEventListener("click", function () { renderMap(); show("map"); });
    $("tx-map-btn").addEventListener("click", function () { renderMap(); show("map"); });
    $("tx-map-back").addEventListener("click", function () { show("journey"); });
    $("tx-prev").addEventListener("click", prevStop);
    $("tx-next").addEventListener("click", function () { nextStop(true); });
    $("tx-stop-link").addEventListener("click", function () { copyStopLink($("tx-stop-link")); });
    $("tx-brief").addEventListener("click", function () { copyBrief($("tx-brief")); });
    $("tx-replay").addEventListener("click", function () { stopAutoplay(); stop = 0; goStop(0); });
    $("tx-copy").addEventListener("click", function () { copyTransmission($("tx-copy")); });
    $("tx-copy-end").addEventListener("click", function () { copyTransmission($("tx-copy-end")); });

    var jump = function (ev) {
      var b = ev.target.closest("[data-stop]");
      if (b) goStop(parseInt(b.getAttribute("data-stop"), 10));
    };
    railEl.addEventListener("click", jump);
    $("tx-map-grid").addEventListener("click", jump);

    if (REDUCED) {
      autoplayBtn.hidden = true; /* manual stepping only */
    } else {
      autoplayBtn.addEventListener("click", function () {
        if (timer) stopAutoplay();
        else startAutoplay();
      });
    }

    document.addEventListener("keydown", function (ev) {
      var tag = (document.activeElement && document.activeElement.tagName) || "";
      if (/INPUT|TEXTAREA|SELECT/.test(tag)) return;
      if (view === "journey") {
        if (ev.key === "ArrowRight") { ev.preventDefault(); nextStop(true); }
        else if (ev.key === "ArrowLeft") { ev.preventDefault(); prevStop(); }
        else if (ev.key === "Home") { ev.preventDefault(); goStop(0); }
        else if (ev.key === "End") { ev.preventDefault(); goStop(stops.length - 1); }
      } else if (view === "map" && ev.key === "Escape") {
        ev.preventDefault(); show("journey");
      }
    });
  }

  /* ---------- boot ---------- */
  function boot(d) {
    DATA = d;
    restoreVisited();
    stops = buildStops();
    var t = d.archive_totals;
    document.querySelector('[data-tx-total="transmissions"]').textContent = fmt(t.transmissions);
    document.querySelector('[data-tx-total="plays"]').textContent = fmt(t.plays);
    document.querySelector('[data-tx-total="sessions"]').textContent = fmt(t.sessions);
    document.querySelector('[data-tx-total="stops"]').textContent = stops.length;
    wire();

    /* resume: offer the last stop, never auto-jump */
    var v = savedStop();
    var m = /^#((?:era|chapter)-[a-z0-9-]+)$/.exec(window.location.hash || "");
    if (m) {
      for (var k = 0; k < stops.length; k++) {
        if (stops[k].hash === m[1]) { goStop(k, { focus: false }); break; }
      }
      if (view !== "journey") show("entry");
    } else if (v != null && v >= 0 && v < stops.length) {
      var rb = $("tx-resume");
      if (rb) {
        rb.hidden = false;
        rb.innerHTML = "Resume \u2014 " + esc(stops[v].name) + " &rarr;";
      }
    }
    updateProgress();
    if (window.ADM.reveal) window.ADM.reveal();
  }

  Promise.all([
    loadData("api/v1/transmission.json"),
    loadData("api/v1/milestone-races.json").then(null, function () { return null; }),
    loadData("api/v1/codex-families.json").then(null, function () { return null; }),
    loadData("api/v1/eras.json").then(null, function () { return null; }),
    loadData("api/v1/years.json").then(null, function () { return null; }),
    loadData("api/v1/session-clusters.json").then(null, function () { return null; }),
    loadData("api/v1/session-tools.json").then(null, function () { return null; }),
    loadData("api/v1/producer-deepdives.json").then(null, function () { return null; })
  ]).then(function (res) {
    RACES = res[1];
    CODEX = res[2];
    ERASJ = res[3];
    YRS = res[4];
    CLUST = res[5];
    TOOLS = res[6];
    PD = res[7];
    boot(res[0]);
  }).catch(function () {
    $("tx-entry").insertAdjacentHTML("beforeend",
      '<p class="chart-sub" role="alert">The transmission data failed to load. The archive pages are all static and fine — this journey just needs its JSON.</p>');
  });
})();
