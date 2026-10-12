/* TRANSMISSION 2.0 — the flagship guided journey: six eras + three data chapters.
   Era stops come from api/v1/transmission.json (incl. the 2026 extras block on
   The Return). Data chapters pull LIVE from api/v1/milestone-races.json and
   api/v1/codex-families.json at load time — no figures hardcoded, so future
   waves update the journey automatically. If those files fail to load, the
   journey degrades gracefully to the six era stops.
   Titles/metadata only — never lyrics.
   Keyboard: in the journey, ←/→ step stops (Home/End jump), Esc in the map
   returns to the journey. Tab order follows rail → panel → controls.
   Auto-play (~12s) is fully disabled under prefers-reduced-motion: manual
   stepping only. Progress persists via localStorage (resume from last stop). */
(function () {
  "use strict";

  var esc = window.ADM.esc;
  var fmt = window.ADM.fmt;
  var loadData = window.ADM.loadData;
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var AUTOPLAY_MS = 12000;
  var STORE_KEY = "adm.transmission.stop";

  var DATA = null, RACES = null, CODEX = null;
  var view = "entry";       // entry | journey | map | end
  var stops = [];           // [{kind,id,hash,label,name,span,era,deepDive,render}]
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
    if (v === "entry") $("tx-title").focus();
  }

  function announce(msg) { liveEl.textContent = ""; liveEl.textContent = msg; }

  function focusStopHeading() {
    var h = $("tx-era-heading");
    if (h) h.focus({ preventScroll: false });
  }

  function remember() {
    try { localStorage.setItem(STORE_KEY, String(stop)); } catch (e) { /* private mode */ }
  }

  function savedStop() {
    try {
      var v = parseInt(localStorage.getItem(STORE_KEY), 10);
      return isNaN(v) ? null : v;
    } catch (e) { return null; }
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
    var contenders = RACES.summit_race.contenders.slice(0, 3).map(function (c) {
      var link = c.page ? '<a href="' + esc(c.page) + '">' + esc(c.title) + "</a>" : esc(c.title);
      return '<li class="tx-track"><span>' + link +
        '<span class="tx-meta">' + esc(c.date) + "</span></span>" +
        '<span class="tx-plays">' + fmt(c.plays) + " plays</span></li>";
    }).join("");
    return '<div class="stat-grid">' +
      statCell(RACES.play_races.length, "Play-count races") +
      statCell(fmt(Math.min.apply(null, races.map(function (r) { return r.needed; }))), "Nearest gap (plays)") +
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
      "</div>";
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
      '<div class="tx-block"><h3>Loudest families by transmissions</h3><ul>' + rows + "</ul></div>";
  }

  /* ---------- stop assembly ---------- */
  function buildStops() {
    var list = DATA.eras.map(function (e) {
      return {
        kind: "era", era: e, id: "era-" + e.id, hash: "era-" + e.id,
        label: "Era", name: e.name, span: e.span,
        deepDive: { href: "eras/" + e.id + ".html", text: "Deep dive: " + e.name },
        render: function () { return renderEraPanel(e); }
      };
    });
    if (RACES) {
      list.push({
        kind: "chapter", id: "chapter-race", hash: "chapter-race",
        label: "Data chapter", name: "The Race", span: "four play-count races \u00b7 the summit chase",
        deepDive: { href: "milestone-race.html", text: "Deep dive: the milestone race" },
        render: renderRace
      });
      list.push({
        kind: "chapter", id: "chapter-record", hash: "chapter-record",
        label: "Data chapter", name: "The Record Book", span: "session records \u00b7 era records \u00b7 just crossed",
        deepDive: { href: "milestone-race.html", text: "Deep dive: the milestone race" },
        render: renderRecordBook
      });
    }
    if (CODEX) {
      list.push({
        kind: "chapter", id: "chapter-codex", hash: "chapter-codex",
        label: "Data chapter", name: "The Codex", span: "sixteen word families \u00b7 the vocabulary",
        deepDive: { href: "decoder.html", text: "Deep dive: the decoder" },
        render: renderCodex
      });
    }
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
      return '<div class="tx-map-item">' +
        '<button type="button" class="tx-map-card" data-stop="' + i + '">' +
        '<span class="c-num">' + esc(s.label.toUpperCase()) + " " + pad(i) + seen + "</span>" +
        '<span class="c-name">' + esc(s.name) + "</span>" +
        '<span class="c-stats">' + esc(s.span || "") + "</span>" +
        "</button>" +
        '<a class="tx-map-dd" href="' + esc(s.deepDive.href) + '">' + esc(s.deepDive.text) + " &rarr;</a>" +
        "</div>";
    }).join("");
  }

  /* ---------- navigation ---------- */
  function goStop(i, opts) {
    opts = opts || {};
    stopAutoplay();
    if (i >= stops.length) { show("end"); return; }
    if (i < 0) i = 0;
    stop = i;
    renderStop();
    remember();
    var s = stops[stop];
    /* deep-linkable stops: era deep-dive pages link back as #era-<id> */
    try {
      window.history.replaceState(null, "", "#" + s.hash);
    } catch (err) { /* file:// or sandboxed contexts: the link still works */ }
    announce("Stop " + (stop + 1) + " of " + stops.length + ": " + s.label + " — " + s.name +
      (s.span ? ", " + s.span : "") + ".");
    if (!REDUCED) {
      eraEl.classList.remove("tuning");
      void eraEl.offsetWidth; /* restart the tuning animation */
      eraEl.classList.add("tuning");
    }
    if (opts.focus !== false) focusStopHeading();
    if (view !== "journey") show("journey");
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
    var n = Object.keys(visited).length;
    return [
      "MY TRANSMISSION \u2014 Aster da Master (2018 \u2192 2026)",
      "Stops visited: " + n + " of " + stops.length + (names.length ? " \u2014 " + names.join(" \u00b7 ") : ""),
      "Favorite era by plays: " + fe.name + " \u2014 " + fmt(fe.era.plays) + " plays across " + fe.era.transmissions + " transmissions",
      "Top track: \u201c" + top.title + "\u201d \u2014 " + fmt(top.plays) + " plays",
      "Signal: " + fe.era.signal,
      "Play counts: " + DATA.plays_snapshot + " snapshot. Titles only, never lyrics."
    ].join("\n");
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
      "Transmission copied: " + Object.keys(visited).length + " of " + stops.length +
      " stops visited. Favorite era by plays: " + stops[favoriteEra()].name + ".");
  }

  function copyStopLink(btn) {
    var s = stops[stop];
    var url = window.location.href.split("#")[0] + "#" + s.hash;
    copyText(url, btn, "Stop link copied: " + s.label + " — " + s.name + ".");
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
    $("tx-open-map").addEventListener("click", function () { renderMap(); show("map"); });
    $("tx-map-btn").addEventListener("click", function () { renderMap(); show("map"); });
    $("tx-map-back").addEventListener("click", function () { show("journey"); });
    $("tx-prev").addEventListener("click", prevStop);
    $("tx-next").addEventListener("click", function () { nextStop(true); });
    $("tx-stop-link").addEventListener("click", function () { copyStopLink($("tx-stop-link")); });
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
    if (window.ADM.reveal) window.ADM.reveal();
  }

  Promise.all([
    loadData("api/v1/transmission.json"),
    loadData("api/v1/milestone-races.json").then(null, function () { return null; }),
    loadData("api/v1/codex-families.json").then(null, function () { return null; })
  ]).then(function (res) {
    RACES = res[1];
    CODEX = res[2];
    boot(res[0]);
  }).catch(function () {
    $("tx-entry").insertAdjacentHTML("beforeend",
      '<p class="chart-sub" role="alert">The transmission data failed to load. The archive pages are all static and fine — this journey just needs its JSON.</p>');
  });
})();
