/* TRANSMISSION 4.0 — the full broadcast (wow wave 1).
   Scroll-driven pirate broadcast: six era segments (2018→2026) + seven data
   chapters rendered as broadcast segments on one long scroll. Traveling
   between segments plays a signal-static flash (pure CSS/SVG, opacity only);
   the station tuner jumps straight to any era. Numbers count up live as each
   segment enters the viewport — every count target from the real data/v1 JSON,
   never invented:
     era transmissions/plays/sessions/distributor/milestones <- transmission.json
     archive totals <- transmission.json archive_totals; the plays cells also
       carry data-signal="plays" so The Signal repaints them live when
       /api/stats answers (the static snapshot stands otherwise).
   Data chapters pull LIVE from the real data/v1 JSON (no figures hardcoded, so
   future waves update the broadcast automatically):
     chapter-race    <- milestone-races.json (closest races + summit)
     chapter-record  <- milestone-races.json (records + just crossed)
     chapter-codex   <- codex-families.json  (word families)
     chapter-architects <- producer-deepdives.json (as-credited producers)
     chapter-seasons <- session-clusters.json (activity seasons + silences)
     chapter-deepcuts <- session-tools.json (deepest-sessions + deepest-transmissions rankings)
     chapter-horizon <- verified 2026-10-11 research pass, sourced inline
   If any optional file fails to load, its chapter degrades away gracefully.
   Titles/metadata only — never lyrics.
   Station frequencies (87.9–98.5 MHz) are station chrome — the pirate dial
   aesthetic from the identity system — not archive facts.
   Keyboard: the tuner is a radiogroup — Tab in, ←/→/↑/↓ tune between era
   stations (announced), Enter/Space tunes the focused station; the mobile era
   picker is a native select. No global arrow hijacking: the page scrolls
   natively. Focus moves to the segment heading on deliberate jumps
   (tuner click/Enter, picker, prev/next); passive scroll never yanks focus.
   Motion: count-ups ride requestAnimationFrame and set their final value even
   if anything fails; the static flash is opacity-only. Under
   prefers-reduced-motion the broadcast is a plain readable document: every
   number stated in full, no flash, no typing, instant scrolling, no autoplay.
   Progress (segment + visited map) persists via localStorage (resume offered,
   never auto-jumps). */
(function () {
  "use strict";

  var esc = window.ADM.esc;
  var fmt = window.ADM.fmt;
  var loadData = window.ADM.loadData;
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var MOBILE_Q = window.matchMedia ? window.matchMedia("(max-width: 640px)") : null;
  var AUTOPLAY_MS = 12000;
  var STORE_KEY = "adm.transmission.stop";
  var STORE_KEY_V = "adm.transmission.visited";
  /* Station chrome: the pirate dial. Aesthetic only — not archive facts. */
  var FREQS = ["87.9", "89.1", "91.3", "93.7", "96.2", "98.5"];

  var DATA = null, RACES = null, CODEX = null, ERASJ = null, YRS = null,
      CLUST = null, TOOLS = null, PD = null;
  var stops = [];           // [{kind,id,hash,label,name,span,freq,era,deepDive,render,brief}]
  var segEls = [];          // rendered <section> per stop
  var visited = {};         // stop index -> true
  var activeIdx = -1;
  var timer = null;
  var lastFlash = 0;
  var announceTimer = null;

  var $ = function (id) { return document.getElementById(id); };
  var entryEl = $("tx-entry"), bcEl = $("tx-broadcast");
  var segWrap = $("tx-segments"), signoffEl = $("tx-signoff"), indexEl = $("tx-index");
  var tunerEl = $("tx-tuner"), dialEl = $("tx-dial"), pickEl = $("tx-tuner-pick");
  var needleEl = $("tx-needle"), readoutEl = $("tx-readout");
  var staticEl = $("tx-static");
  var liveEl = $("tx-live");
  var autoplayBtn = $("tx-autoplay");

  function isMobile() { return MOBILE_Q && MOBILE_Q.matches; }

  /* ---------- views ---------- */
  function showBroadcast() {
    entryEl.hidden = true;
    bcEl.hidden = false;
  }
  function showEntry() {
    bcEl.hidden = true;
    entryEl.hidden = false;
  }

  function announce(msg) {
    if (!liveEl) return;
    if (announceTimer) { clearTimeout(announceTimer); announceTimer = null; }
    liveEl.textContent = "";
    announceTimer = setTimeout(function () {
      liveEl.textContent = msg;
      announceTimer = null;
    }, REDUCED ? 0 : 700);
  }

  function announceNow(msg) {
    if (!liveEl) return;
    if (announceTimer) { clearTimeout(announceTimer); announceTimer = null; }
    liveEl.textContent = "";
    liveEl.textContent = msg;
  }

  /* ---------- progress persistence (segment + visited map) ---------- */
  function remember() {
    try {
      localStorage.setItem(STORE_KEY, String(activeIdx));
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
    activeIdx = -1;
  }

  function visitedCount() { return Object.keys(visited).length; }

  function markVisited(i) {
    if (!visited[i]) {
      visited[i] = true;
      updateProgress();
    }
  }

  function updateProgress() {
    var n = visitedCount();
    var pl = $("tx-progress");
    if (pl) pl.textContent = n + " of " + stops.length + " segments visited.";
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
      ? '<a href="' + esc(s.deep_dive) + '">' + esc(s.name) + "</a> <span class=\"tx-dd\">deep dive</span>"
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

  /* Stat cell. n = raw count target for the live count-up (numbers only).
     The cell renders at zero and counts up when its segment enters; every
     no-motion/no-JS-observer path sets the final value immediately, so a
     failed animation can never leave a wrong number. dec = decimals,
     suffix = appended label. */
  function statCell(v, l, n, dec, suffix) {
    var attrs = "", initial = v;
    if (typeof n === "number" && isFinite(n)) {
      attrs = ' data-count="' + n + '"';
      if (dec) attrs += ' data-count-dec="' + dec + '"';
      if (suffix) attrs += ' data-count-suffix="' + esc(suffix) + '"';
      initial = fmtCount(0, dec || 0) + (suffix || "");
    }
    return '<div class="stat"><div class="stat-value"' + attrs + ">" + initial + '</div><div class="stat-label">' + l + "</div></div>";
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
      statCell(fmt(e.transmissions), "Transmissions", e.transmissions) +
      statCell(fmt(e.plays), "Plays", e.plays) +
      statCell(e.sessions, "Sessions", e.sessions) +
      statCell(e.milestones.length, "Milestones filed", e.milestones.length) +
      statCell(e.distributor, "Distributor releases", e.distributor) +
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
      statCell(RACES.play_races.length, "Play-count races", RACES.play_races.length) +
      statCell(fmt(nearest), "Nearest gap (plays)", nearest) +
      statCell(fmt(h.plays), "Summit plays", h.plays) +
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
      statCell(RACES.session_records.length, "Session records", RACES.session_records.length) +
      statCell(RACES.era_records.length, "Era records", RACES.era_records.length) +
      statCell(RACES.just_crossed.length, "Just crossed", RACES.just_crossed.length) +
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
      statCell(CODEX.family_count, "Word families", CODEX.family_count) +
      statCell(totalLinks, "Family-track links", totalLinks) +
      statCell(fmt(loudest.total_plays), "Loudest family plays", loudest.total_plays) +
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
      statCell(ins.producer_count, "As-credited producers", ins.producer_count) +
      statCell(ins.total_credits, "Title prod. credits", ins.total_credits) +
      statCell(ins.researched_count, "Researched profiles", ins.researched_count) +
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
      statCell(ins.session_count, "Upload sessions", ins.session_count) +
      statCell(ins.season_count, "Activity seasons", ins.season_count) +
      statCell(CLUST.gaps.length, "Session gaps", CLUST.gaps.length) +
      statCell(longS.days + " days", "Longest silence", longS.days, 0, " days") +
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
      var link = r.deep_dive ? '<a href="' + esc(r.deep_dive) + '">' + esc(r.name) + "</a>" : esc(r.name);
      return '<li class="tx-track"><span><span class="tx-rank">#' + r.rank + "</span> " + link +
        '<span class="tx-meta">' + r.track_count + " transmissions &middot; " + fmt(r.total_plays) +
        " plays &middot; " + esc(r.era_name) + "</span></span>" +
        '<span class="tx-plays">' + r.avg_plays_per_track + " avg</span></li>";
    }).join("");
    var deep = ins.deepest_session, quiet = ins.quietest_session;
    var tdc = TOOLS.track_deep_cuts || null;
    var tRows = "", tStats = "", tNote = "";
    if (tdc) {
      tRows = tdc.bottom_25.slice(0, 10).map(function (r) {
        var voices = r.voices.length ? " &middot; w/ " + esc(r.voices.join(", ")) : "";
        return '<li class="tx-track"><span><span class="tx-rank">#' + r.rank + "</span> " +
          '<a href="' + esc(r.page) + '">' + esc(r.title) + "</a>" +
          '<span class="tx-meta">' + esc(r.date) + " &middot; " + esc(r.era_name) + voices +
          "</span></span>" +
          '<span class="tx-plays">' + fmt(r.plays) + " plays</span></li>";
      }).join("");
      var ti = tdc.insights;
      tStats = statCell(fmt(ti.quietest.plays) + " plays", "Quietest transmission", ti.quietest.plays) +
        statCell(fmt(ti.median_plays), "Median plays / transmission", ti.median_plays) +
        statCell(ti.under_100_plays + " of 185", "Transmissions under 100 plays");
      tNote = '<div class="tx-block"><h3>The quietest transmissions</h3><ol>' + tRows + "</ol>" +
        '<p class="tx-note"><strong>The formula:</strong> ' + esc(tdc.formula) + "</p>" +
        '<p class="tx-note">The full quietest-25 lives on the ' +
        '<a href="sessions-explorer.html#se-trackdeep">sessions explorer</a>. ' +
        "Nine of the 185 vault transmissions sit under 100 plays; the median is " +
        fmt(ti.median_plays) + ".</p></div>";
    }
    return '<div class="stat-grid">' +
      statCell(dc.ranking.length, "Ranked sessions", dc.ranking.length) +
      statCell(dc.excluded_single_track_sessions, "Single-track sessions excluded", dc.excluded_single_track_sessions) +
      statCell(deep.avg_plays_per_track, "Deepest avg (plays/tx)", deep.avg_plays_per_track, 1) +
      tStats +
      statCell(TOOLS.plays_snapshot, "Snapshot") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' +
      "The quietest rooms in the vault, ranked by average plays per transmission. The deepest session on record is \u201c" +
      esc(deep.name) + "\u201d \u2014 " + deep.avg_plays_per_track + " plays per transmission across " +
      "its two tracks." +
      (tdc ? " And the quietest single transmission ever uploaded is \u201c" +
        esc(tdc.insights.quietest.title) + "\u201d \u2014 " +
        fmt(tdc.insights.quietest.plays) + " plays." : "") +
      " An editorial ranking, not an artist fact.</blockquote>" +
      '<div class="tx-block"><h3>The deepest sessions</h3><ol>' + rows + "</ol>" +
      '<p class="tx-note"><strong>The formula:</strong> ' + esc(dc.formula) + "</p>" +
      '<p class="tx-note">The quietest single session ever uploaded: \u201c' + esc(quiet.name) + "\u201d \u2014 " +
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

  /* ---------- data chapter: THE HORIZON (verified 2026-10-11 research pass) ---------- */
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

  function attachFreqs() {
    var n = 0;
    stops.forEach(function (s) {
      if (s.kind === "era") s.freq = FREQS[n++] || "";
    });
  }

  function eraIndex(i) {
    var n = 0;
    for (var k = 0; k < i; k++) { if (stops[k].kind === "era") n++; }
    return n;
  }

  function eraStops() { return stops.map(function (s, i) { return s.kind === "era" ? i : -1; }).filter(function (i) { return i >= 0; }); }

  /* ---------- share ---------- */
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
      "Segments visited: " + n + " of " + stops.length + (names.length ? " \u2014 " + names.join(" \u00b7 ") : ""),
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
        e.sessions + " sessions \u00b7 " + e.milestones.length + " milestones filed \u00b7 " +
        e.distributor + " distributor releases");
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
      announceNow(doneMsg);
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
      " segments visited. Favorite era by plays: " + stops[favoriteEra()].name + ".");
  }

  function copyStopLink(s, btn) {
    var url = window.location.href.split("#")[0] + "#" + s.hash;
    copyText(url, btn, "Stop link copied: " + s.label + " — " + s.name + ".");
  }

  function copyBrief(s, btn) {
    copyText(stopBrief(s), btn, "Stop brief copied: " + s.label + " — " + s.name + ".");
  }

  /* ================= THE BROADCAST ENGINE ================= */

  /* ---------- segment rendering ---------- */
  function segHeadingId(i) { return "tx-seg-h-" + i; }

  function renderSegment(s, i) {
    var freqLine = s.kind === "era"
      ? '<p class="tx-seg-freq" aria-hidden="true">' + esc(s.freq) + ' <span>MHz</span></p>'
      : '<p class="tx-seg-freq tx-seg-data" aria-hidden="true">DATA BAND</p>';
    var kick = s.kind === "era"
      ? "Era " + (eraIndex(i) + 1) + " of " + DATA.eras.length
      : "Data chapter";
    return '<section class="tx-seg" id="' + s.hash + '" data-stop="' + i + '" aria-labelledby="' + segHeadingId(i) + '">' +
      '<header class="tx-seg-head">' +
      '<p class="kicker"><span class="numeral">\u2726</span>' + kick + "</p>" +
      freqLine +
      '<h2 id="' + segHeadingId(i) + '" tabindex="-1">' + esc(s.name) + "</h2>" +
      '<p class="tx-span">' + esc(s.span || "") + "</p>" +
      (s.kind === "era" ? '<p class="tx-scene">' + esc(s.era.scene) + "</p>" : "") +
      "</header>" +
      '<div class="tx-seg-body">' + s.render() + "</div>" +
      '<footer class="tx-seg-foot">' +
      deepDivePara(s.deepDive) +
      '<div class="tx-seg-actions">' +
      '<button type="button" class="btn btn-sm btn-ghost" data-act="link">Copy stop link</button>' +
      '<button type="button" class="btn btn-sm btn-ghost" data-act="brief">Copy stop brief</button>' +
      "</div></footer></section>";
  }

  function renderSegments() {
    segEls = stops.map(function (s, i) {
      var tmp = document.createElement("div");
      tmp.innerHTML = renderSegment(s, i);
      var sec = tmp.firstChild;
      segWrap.appendChild(sec);
      return sec;
    });
  }

  /* ---------- station index (plain anchor jumps; the tuner is the dial) ---------- */
  function renderIndex() {
    indexEl.innerHTML = '<p class="kicker"><span class="numeral">\u2726</span>Station index</p>' +
      "<ol>" + stops.map(function (s, i) {
        var stat = s.kind === "era"
          ? fmt(s.era.transmissions) + " tx \u00b7 " + fmt(s.era.plays) + " plays"
          : s.span;
        return '<li><a href="#' + s.hash + '" data-jump="' + i + '">' +
          '<span class="ix-num">' + (s.kind === "era" ? "ERA" : "DATA") + "</span> " +
          '<span class="ix-name">' + esc(s.name) + "</span> " +
          '<span class="ix-stat">' + esc(stat || "") + "</span></a></li>";
      }).join("") + "</ol>";
  }

  /* ---------- sign-off ---------- */
  function renderSignoff() {
    var t = DATA.archive_totals;
    /* The plays cell carries data-signal="plays": The Signal (Vercel Wave B)
       repaints it with the live count when /api/stats answers; the static
       snapshot stands otherwise (the badge is the honesty mechanism). It also
       count-ups on entry like every other number. */
    var playsCell = '<div class="stat"><div class="stat-value" data-count="' + t.plays +
      '"><span data-signal="plays">0</span></div>' +
      '<div class="stat-label">Plays (' + DATA.plays_snapshot + " snapshot)</div></div>";
    signoffEl.innerHTML =
      '<p class="kicker"><span class="numeral">\u2726</span>Signal received</p>' +
      '<h2 id="tx-signoff-h" tabindex="-1">TRANSMISSION ENDS</h2>' +
      '<p class="signal-row"><span class="api-badge" id="tx-signal-badge" data-api-state="waking" role="status" aria-live="polite"></span></p>' +
      '<p class="tx-lede">You rode six eras and seven data chapters, 2018 to 2026. Here is the whole signal in one frame — and the full vault, if you want to keep digging.</p>' +
      '<div class="stat-grid tx-end-stats">' +
      statCell(fmt(t.transmissions), "Transmissions, 2018\u20132026", t.transmissions) +
      playsCell +
      statCell(t.sessions, "Upload sessions", t.sessions) +
      statCell(stops.length, "Segments traversed", stops.length) +
      "</div>" +
      '<div class="btn-row">' +
      '<a class="btn btn-neon" href="glance.html">Open the vault at a glance</a>' +
      '<button class="btn btn-ghost" id="tx-copy-end" type="button">Copy my transmission</button>' +
      '<button class="btn btn-ghost" id="tx-replay" type="button">\u21bb Replay the broadcast</button>' +
      "</div>" +
      '<div class="tx-share-out" id="tx-share-out" hidden></div>';
  }

  /* ---------- the tuner ---------- */
  function startYear(s) {
    var m = /^(\d{4})/.exec(s.span || "");
    return m ? m[1] : "";
  }

  function renderTuner() {
    var eraIdx = eraStops();
    dialEl.innerHTML = '<span class="tx-needle" id="tx-needle" aria-hidden="true">\u25be</span>' +
      eraIdx.map(function (i) {
        var s = stops[i];
        var seen = visited[i] ? ' <span class="tx-visited" aria-hidden="true">\u25cf</span>' : "";
        return '<button type="button" role="radio" aria-checked="false" class="tx-station" data-tune="' + i + '" ' +
          'aria-label="Tune to ' + esc(s.freq) + " MHz — " + esc(s.name) + '">' +
          '<span class="st-freq">' + esc(s.freq) + seen + "</span>" +
          '<span class="st-name">' + esc(s.name) + "</span>" +
          '<span class="st-years">' + esc(startYear(s)) + "</span></button>";
      }).join("");
    needleEl = $("tx-needle");
    pickEl.innerHTML = '<option value="">Jump to a segment\u2026</option>' + stops.map(function (s, i) {
      return '<option value="' + i + '">' + esc((s.kind === "era" ? "Era \u2014 " : "Chapter \u2014 ") + s.name) + "</option>";
    }).join("");
  }

  function moveNeedle() {
    if (!needleEl) return;
    var btn = dialEl.querySelector('[data-tune="' + activeIdx + '"]');
    if (!btn) return;
    var x = btn.offsetLeft + btn.offsetWidth / 2;
    needleEl.style.transform = "translateX(" + x + "px) translateX(-50%)";
  }

  /* Boot-sequence aesthetic for the readout: type TUNING, then land on the
     station. Visual only (aria-hidden) — the live region announces once. */
  var typeTimer = null;
  function setReadoutPlain(s) {
    if (typeTimer) { clearTimeout(typeTimer); typeTimer = null; }
    paintReadout(s.freq ? s.freq + " MHz \u00b7 SIGNAL FOUND" : "DATA BAND \u00b7 SIGNAL FOUND", s.name);
  }

  function setReadoutTyped(s) {
    if (REDUCED || isMobile()) { setReadoutPlain(s); return; }
    if (typeTimer) { clearTimeout(typeTimer); typeTimer = null; }
    var line1 = s.freq ? "TUNING " + s.freq + " \u2026" : "TUNING DATA BAND \u2026";
    var line2 = s.freq ? s.freq + " MHz \u00b7 SIGNAL FOUND" : "DATA BAND \u00b7 SIGNAL FOUND";
    var ci = 0;
    paintReadout("", s.name);
    (function tick() {
      ci++;
      paintReadout(line1.slice(0, ci), s.name);
      if (ci < line1.length) {
        typeTimer = setTimeout(tick, 26);
      } else {
        typeTimer = setTimeout(function () { paintReadout(line2, s.name); typeTimer = null; }, 320);
      }
    })();
  }

  function paintReadout(status, name) {
    if (!readoutEl) return;
    readoutEl.innerHTML =
      '<span class="tx-ro-status" aria-hidden="true">' + esc(status) + "</span>" +
      '<span class="tx-ro-name" aria-hidden="true">' + esc(name) + "</span>";
  }

  function syncTuner(i) {
    var btns = dialEl.querySelectorAll("[data-tune]");
    Array.prototype.forEach.call(btns, function (b) {
      var on = +b.getAttribute("data-tune") === i;
      b.setAttribute("aria-checked", on ? "true" : "false");
      if (on) b.classList.add("is-on"); else b.classList.remove("is-on");
      var dot = b.querySelector(".tx-visited");
      var si = +b.getAttribute("data-tune");
      if (visited[si] && !dot) {
        var f = b.querySelector(".st-freq");
        if (f) f.insertAdjacentHTML("beforeend", ' <span class="tx-visited" aria-hidden="true">\u25cf</span>');
      }
    });
    if (pickEl && String(pickEl.value) !== String(i)) pickEl.value = String(i);
    moveNeedle();
  }

  /* ---------- signal static: pure CSS/SVG, opacity only ---------- */
  function flashStatic() {
    if (REDUCED || isMobile() || !staticEl) return;
    var now = Date.now();
    if (now - lastFlash < 600) return; /* don't strobe on fast scroll */
    lastFlash = now;
    staticEl.classList.add("on");
    setTimeout(function () { staticEl.classList.remove("on"); }, 170);
  }

  /* ---------- count-up: numbers roll live as a segment enters ---------- */
  function fmtCount(v, dec) {
    if (dec > 0) {
      return v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
    }
    return Math.round(v).toLocaleString("en-US");
  }

  function countUp(el) {
    if (el.hasAttribute("data-counted")) return;
    el.setAttribute("data-counted", "1");
    var target = parseFloat(el.getAttribute("data-count"));
    var dec = parseInt(el.getAttribute("data-count-dec") || "0", 10);
    var suf = el.getAttribute("data-count-suffix") || "";
    if (!isFinite(target)) return;
    /* The plays cells carry a data-signal span the Signal may repaint live;
       count the span so a live repaint lands in the right place. */
    var inner = el.querySelector("[data-signal]") || el;
    var set = function (v) { inner.textContent = fmtCount(v, dec) + suf; };
    if (REDUCED || !window.requestAnimationFrame) { set(target); return; }
    set(0);
    var t0 = null, DUR = 1150;
    function frame(now) {
      if (t0 === null) t0 = now;
      var t = Math.min(1, (now - t0) / DUR);
      var e = 1 - Math.pow(1 - t, 3);
      set(target * e);
      if (t < 1) window.requestAnimationFrame(frame);
      else set(target);
    }
    window.requestAnimationFrame(frame);
  }

  function runCounts(root) {
    if (!root) return;
    var cells = root.querySelectorAll("[data-count]:not([data-counted])");
    Array.prototype.forEach.call(cells, countUp);
  }

  /* ---------- activation: tune (deliberate) vs scroll (passive) ---------- */
  function segLabel(i) {
    var s = stops[i];
    if (s.kind === "era") {
      var e = s.era;
      return s.name + " — " + fmt(e.transmissions) + " transmissions, " + fmt(e.plays) +
        " plays, " + e.sessions + " sessions, " + e.milestones.length + " milestones filed.";
    }
    return s.name + " — " + s.span + ".";
  }

  function activate(i, origin, opts) {
    opts = opts || {};
    if (i < 0 || i >= stops.length) return;
    var first = activeIdx < 0;
    activeIdx = i;
    markVisited(i);
    runCounts(segEls[i]);
    syncTuner(i);
    if (!first) flashStatic();
    if (origin === "tune") {
      setReadoutTyped(stops[i]);
      try { window.history.replaceState(null, "", "#" + stops[i].hash); } catch (e) { /* file:// */ }
      document.title = stops[i].name + " \u00b7 Transmission \u2014 Aster da Master";
    } else {
      setReadoutPlain(stops[i]);
    }
    if (origin === "tune") announceNow("Tuned to segment " + (i + 1) + " of " + stops.length + ": " + segLabel(i));
    else announce("Segment " + (i + 1) + " of " + stops.length + ": " + segLabel(i));
    remember();
    if (opts.focus) {
      var h = $(segHeadingId(i));
      if (h) h.focus({ preventScroll: true });
    }
  }

  /* While a tune's smooth scroll is in flight, scroll-origin activations are
     suppressed — the tune already activated its target; the observer just
     marks visited segments and runs their count-ups. */
  var tuneGuard = 0;

  function tune(i, opts) {
    opts = opts || {};
    if (!opts.auto) stopAutoplay();
    if (i < 0) i = 0;
    if (i >= stops.length) i = stops.length - 1;
    var sec = segEls[i];
    if (!sec) return;
    activate(i, "tune", opts);
    if (!REDUCED) tuneGuard = Date.now() + 1400;
    try {
      sec.scrollIntoView({ behavior: (REDUCED || opts.instant) ? "auto" : "smooth", block: "start" });
    } catch (e) {
      sec.scrollIntoView();
    }
  }

  function scrollToSignoff() {
    stopAutoplay();
    tuneGuard = 0;
    try {
      signoffEl.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" });
    } catch (e) {
      signoffEl.scrollIntoView();
    }
    runCounts(signoffEl);
    var h = $("tx-signoff-h");
    if (h) h.focus({ preventScroll: true });
    announceNow("Transmission ends: the vault at a glance.");
  }

  /* ---------- scroll observation ---------- */
  function watchSegments() {
    if (!("IntersectionObserver" in window)) {
      /* Ancient: everything counts up immediately, stated plainly. */
      segEls.forEach(function (sec) { runCounts(sec); });
      runCounts(signoffEl);
      return;
    }
    var segIO = new IntersectionObserver(function (entries) {
      var best = null, bestRatio = 0;
      entries.forEach(function (en) {
        if (en.isIntersecting && en.intersectionRatio > bestRatio) {
          bestRatio = en.intersectionRatio;
          best = +en.target.getAttribute("data-stop");
        }
      });
      if (best === null || best === activeIdx) return;
      /* every visible segment counts up and marks visited, immediately */
      markVisited(best);
      runCounts(segEls[best]);
      if (Date.now() < tuneGuard) return; /* a tune's scroll is in flight */
      activate(best, "scroll");
    }, { threshold: [0.35, 0.6] });
    segEls.forEach(function (sec) { segIO.observe(sec); });
    /* The sign-off counts up when it arrives, too. */
    var soIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { runCounts(signoffEl); soIO.disconnect(); }
      });
    }, { threshold: 0.35 });
    soIO.observe(signoffEl);
  }

  /* ---------- auto-play: the station plays the segments ---------- */
  function startAutoplay() {
    if (REDUCED || timer) return;
    autoplayBtn.setAttribute("aria-pressed", "true");
    autoplayBtn.innerHTML = "\u275a\u275a Pause";
    timer = setInterval(function () {
      var n = activeIdx + 1;
      if (n >= stops.length) { stopAutoplay(); scrollToSignoff(); return; }
      tune(n, { auto: true });
    }, AUTOPLAY_MS);
    announceNow("Auto-play on: tuning through the segments every 12 seconds. Scroll or press pause to take over.");
  }

  function stopAutoplay() {
    if (timer) { clearInterval(timer); timer = null; }
    if (!autoplayBtn) return;
    autoplayBtn.setAttribute("aria-pressed", "false");
    autoplayBtn.innerHTML = "\u25b6 Press play";
  }

  /* ---------- wiring ---------- */
  function wire() {
    $("tx-begin").addEventListener("click", function () {
      showBroadcast();
      tune(0, { instant: true });
      if (window.Signal) window.Signal.wireStats("tx-signal-badge");
    });
    var resumeBtn = $("tx-resume");
    if (resumeBtn) resumeBtn.addEventListener("click", function () {
      var v = savedStop();
      showBroadcast();
      tune(v == null ? 0 : Math.min(v, stops.length - 1), { instant: true });
      if (window.Signal) window.Signal.wireStats("tx-signal-badge");
    });
    var clearBtn = $("tx-clear");
    if (clearBtn) clearBtn.addEventListener("click", function () {
      clearProgress();
      updateProgress();
      syncTuner(-1);
      var rb = $("tx-resume");
      if (rb) rb.hidden = true;
      announceNow("Progress cleared. The broadcast is back at the start.");
    });

    /* tuner dial: click tunes; arrows retune (focus stays on the dial) */
    dialEl.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-tune]");
      if (!b) return;
      tune(+b.getAttribute("data-tune"), { focus: true });
      b.focus();
    });
    dialEl.addEventListener("keydown", function (ev) {
      var b = ev.target.closest("[data-tune]");
      if (!b) return;
      var cur = +b.getAttribute("data-tune");
      var eraIdx = eraStops();
      var pos = eraIdx.indexOf(cur);
      var n = null;
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") n = eraIdx[(pos + 1) % eraIdx.length];
      else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") n = eraIdx[(pos - 1 + eraIdx.length) % eraIdx.length];
      else if (ev.key === "Home") n = eraIdx[0];
      else if (ev.key === "End") n = eraIdx[eraIdx.length - 1];
      if (n === null || n === undefined) return;
      ev.preventDefault();
      tune(n);
      var nb = dialEl.querySelector('[data-tune="' + n + '"]');
      if (nb) nb.focus();
    });

    /* mobile era picker */
    if (pickEl) pickEl.addEventListener("change", function () {
      if (pickEl.value === "") return;
      tune(+pickEl.value, { focus: true });
    });

    /* broadcast transport */
    $("tx-prev").addEventListener("click", function () {
      tune(activeIdx <= 0 ? 0 : activeIdx - 1, { focus: true });
    });
    $("tx-next").addEventListener("click", function () {
      if (activeIdx >= stops.length - 1) scrollToSignoff();
      else tune(activeIdx + 1, { focus: true });
    });
    if (REDUCED) {
      autoplayBtn.hidden = true;
    } else {
      autoplayBtn.addEventListener("click", function () {
        if (timer) stopAutoplay();
        else startAutoplay();
      });
      /* the listener takes over on any manual scroll */
      var interrupt = function () {
        if (timer) stopAutoplay();
        tuneGuard = 0;
      };
      window.addEventListener("wheel", interrupt, { passive: true });
      window.addEventListener("touchmove", interrupt, { passive: true });
      window.addEventListener("pointerdown", interrupt, { passive: true });
    }

    /* per-segment copy buttons (delegated) */
    segWrap.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-act]");
      if (!b) return;
      var sec = ev.target.closest("[data-stop]");
      if (!sec) return;
      var s = stops[+sec.getAttribute("data-stop")];
      if (b.getAttribute("data-act") === "link") copyStopLink(s, b);
      else copyBrief(s, b);
    });

    /* station index: plain anchors — let them jump, the observer activates */
    indexEl.addEventListener("click", function (ev) {
      var a = ev.target.closest("[data-jump]");
      if (!a) return;
      stopAutoplay();
    });

    /* sign-off buttons (delegated — rendered before wire in boot) */
    signoffEl.addEventListener("click", function (ev) {
      if (ev.target.closest("#tx-copy-end")) copyTransmission(ev.target.closest("#tx-copy-end"));
      else if (ev.target.closest("#tx-replay")) {
        stopAutoplay();
        tuneGuard = 0;
        activate(0, "tune", {});
        try { window.scrollTo({ top: 0, behavior: REDUCED ? "auto" : "smooth" }); } catch (e) { window.scrollTo(0, 0); }
      }
    });

    window.addEventListener("resize", function () { moveNeedle(); });
  }

  /* ---------- boot ---------- */
  function boot(d) {
    DATA = d;
    restoreVisited();
    stops = buildStops();
    attachFreqs();
    var t = d.archive_totals;
    var q = function (sel) { return document.querySelector(sel); };
    q('[data-tx-total="transmissions"]').textContent = fmt(t.transmissions);
    q('[data-tx-total="plays"]').textContent = fmt(t.plays);
    q('[data-tx-total="sessions"]').textContent = fmt(t.sessions);
    q('[data-tx-total="stops"]').textContent = stops.length;

    renderTuner();
    renderSegments();
    renderIndex();
    renderSignoff();
    wire();
    paintReadout("STANDBY", "THE PIRATE BROADCAST");
    syncTuner(-1);

    /* deep link straight into the broadcast */
    var m = /^#((?:era|chapter)-[a-z0-9-]+)$/.exec(window.location.hash || "");
    if (m) {
      for (var k = 0; k < stops.length; k++) {
        if (stops[k].hash === m[1]) {
          showBroadcast();
          /* layout first, then tune */
          (function (kk) {
            setTimeout(function () { tune(kk, { instant: true }); }, 60);
          })(k);
          if (window.Signal) window.Signal.wireStats("tx-signal-badge");
          break;
        }
      }
      if (bcEl.hidden) showEntry();
    } else {
      var v = savedStop();
      if (v != null && v >= 0 && v < stops.length) {
        var rb = $("tx-resume");
        if (rb) {
          rb.hidden = false;
          rb.innerHTML = "Resume \u2014 " + esc(stops[v].name) + " &rarr;";
        }
      }
    }
    updateProgress();
    watchSegments();
    if (window.ADM.reveal) window.ADM.reveal();
  }

  Promise.all([
    loadData("data/v1/transmission.json"),
    loadData("data/v1/milestone-races.json").then(null, function () { return null; }),
    loadData("data/v1/codex-families.json").then(null, function () { return null; }),
    loadData("data/v1/eras.json").then(null, function () { return null; }),
    loadData("data/v1/years.json").then(null, function () { return null; }),
    loadData("data/v1/session-clusters.json").then(null, function () { return null; }),
    loadData("data/v1/session-tools.json").then(null, function () { return null; }),
    loadData("data/v1/producer-deepdives.json").then(null, function () { return null; })
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
      '<p class="chart-sub" role="alert">The transmission data failed to load. The archive pages are all static and fine — this broadcast just needs its JSON.</p>');
  });
})();
