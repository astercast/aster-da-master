/* TRANSMISSION — the flagship guided journey through the six eras.
   All client-side, all from api/v1/transmission.json. Titles/metadata only — never lyrics.
   Keyboard: ←/→ step eras (Home/End jump), Tab order follows the rail → panel → controls.
   Auto-play (~12s) is fully disabled under prefers-reduced-motion: manual stepping only. */
(function () {
  "use strict";

  var esc = window.ADM.esc;
  var fmt = window.ADM.fmt;
  var loadData = window.ADM.loadData;
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var AUTOPLAY_MS = 12000;

  var DATA = null;
  var view = "entry";       // entry | journey | map | end
  var era = 0;
  var visited = {};         // era index -> true
  var timer = null;

  var $ = function (id) { return document.getElementById(id); };
  var entryEl = $("tx-entry"), journeyEl = $("tx-journey"), mapEl = $("tx-map"), endEl = $("tx-end");
  var railEl = $("tx-rail"), innerEl = $("tx-era-inner"), eraEl = $("tx-era");
  var liveEl = $("tx-live");
  var autoplayBtn = $("tx-autoplay");

  function eras() { return DATA.eras; }

  /* ---------- views ---------- */
  function show(v) {
    view = v;
    entryEl.hidden = v !== "entry";
    journeyEl.hidden = v !== "journey";
    mapEl.hidden = v !== "map";
    endEl.hidden = v !== "end";
    if (v === "journey") focusEraHeading();
    if (v === "map") $("tx-map-heading").focus();
    if (v === "end") { renderEnd(); $("tx-end-heading").focus(); }
    if (v === "entry") $("tx-title").focus();
  }

  function announce(msg) { liveEl.textContent = ""; liveEl.textContent = msg; }

  function focusEraHeading() {
    var h = $("tx-era-heading");
    if (h) h.focus({ preventScroll: false });
  }

  /* ---------- rendering ---------- */
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

  function renderRail() {
    railEl.innerHTML = eras().map(function (e, i) {
      var cur = i === era ? ' aria-current="step"' : "";
      return '<li><button type="button" class="tx-node" data-era="' + i + '"' + cur + ">" +
        '<span class="n-num">' + ("0" + (i + 1)) + " / 06</span>" +
        '<span class="n-name">' + esc(e.name) + "</span>" +
        '<span class="tx-meta">' + esc(e.span) + "</span></button></li>";
    }).join("");
  }

  function renderEra() {
    var e = eras()[era];
    visited[era] = true;
    var stat = function (v, l) {
      return '<div class="stat"><div class="stat-value">' + v + '</div><div class="stat-label">' + l + "</div></div>";
    };
    var collabs = e.collaborators.length
      ? "<ul>" + e.collaborators.map(collabRow).join("") + "</ul>"
      : '<p class="tx-empty">No title-credited collaborators this era — every transmission stands alone.</p>';
    var miles = e.milestones.length
      ? "<ul>" + e.milestones.map(mileRow).join("") + "</ul>"
      : '<p class="tx-empty">No milestones filed for this era. The numbers speak.</p>';
    innerEl.innerHTML =
      '<div class="tx-era-kicker"><span class="kicker"><span class="numeral">\u2726</span>Era ' + (era + 1) + " of " + eras().length + "</span>" +
      '<span class="tx-span">' + esc(e.span) + "</span></div>" +
      '<h2 id="tx-era-heading" tabindex="-1">' + esc(e.name) + "</h2>" +
      '<p class="tx-scene">' + esc(e.scene) + "</p>" +
      '<div class="stat-grid">' +
      stat(fmt(e.transmissions), "Transmissions") +
      stat(fmt(e.plays), "Plays") +
      stat(e.sessions, "Sessions") +
      stat(e.distributor, "Distributor releases") +
      "</div>" +
      '<blockquote class="tx-signal"><span class="sig-lab">The signal</span>' + esc(e.signal) + "</blockquote>" +
      '<div class="tx-cols">' +
      '<div class="tx-block"><h3>Defining tracks</h3><ol>' + e.top_tracks.map(trackRow).join("") + "</ol></div>" +
      '<div class="tx-block"><h3>Key sessions</h3><ul>' + e.key_sessions.map(sessionRow).join("") + "</ul></div>" +
      '<div class="tx-block"><h3>Summoned voices</h3>' + collabs + "</div>" +
      '<div class="tx-block"><h3>Milestones</h3>' + miles + "</div>" +
      "</div>";
    renderRail();
    document.title = e.name + " \u00b7 Transmission \u2014 Aster da Master";
  }

  function renderMap() {
    $("tx-map-grid").innerHTML = eras().map(function (e, i) {
      return '<button type="button" class="tx-map-card" data-era="' + i + '">' +
        '<span class="c-num">ERA ' + ("0" + (i + 1)) + " \u00b7 " + esc(e.span) + "</span>" +
        '<span class="c-name">' + esc(e.name) + "</span>" +
        '<span class="c-stats">' + fmt(e.transmissions) + " transmissions \u00b7 " + fmt(e.plays) + " plays</span>" +
        "</button>";
    }).join("");
  }

  /* ---------- navigation ---------- */
  function goEra(i, opts) {
    opts = opts || {};
    stopAutoplay();
    if (i >= eras().length) { show("end"); return; }
    if (i < 0) i = 0;
    era = i;
    renderEra();
    var e = eras()[era];
    announce("Era " + (era + 1) + " of " + eras().length + ": " + e.name + ", " + e.span +
      ". " + fmt(e.transmissions) + " transmissions, " + fmt(e.plays) + " plays.");
    if (!REDUCED) {
      eraEl.classList.remove("tuning");
      void eraEl.offsetWidth; /* restart the tuning animation */
      eraEl.classList.add("tuning");
    }
    if (opts.focus !== false) focusEraHeading();
    if (view !== "journey") show("journey");
  }

  function nextEra(manual) { goEra(era + 1, { focus: manual !== false }); }
  function prevEra() { goEra(era - 1); }

  /* ---------- auto-play ---------- */
  function startAutoplay() {
    if (REDUCED || timer) return;
    autoplayBtn.setAttribute("aria-pressed", "true");
    autoplayBtn.innerHTML = "&#10074;&#10074; Pause";
    timer = setInterval(function () {
      if (era + 1 >= eras().length) { stopAutoplay(); show("end"); return; }
      era += 1;
      renderEra();
      var e = eras()[era];
      announce("Era " + (era + 1) + " of " + eras().length + ": " + e.name + ", " + e.span + ".");
    }, AUTOPLAY_MS);
    announce("Auto-play on: advancing every 12 seconds. Press pause to take over.");
  }

  function stopAutoplay() {
    if (timer) { clearInterval(timer); timer = null; }
    autoplayBtn.setAttribute("aria-pressed", "false");
    autoplayBtn.innerHTML = "&#9654; Press play";
  }

  /* ---------- share ---------- */
  function favoriteEra() {
    var idx = Object.keys(visited).map(Number);
    if (!idx.length) idx = [era];
    return idx.reduce(function (a, b) { return eras()[b].plays > eras()[a].plays ? b : a; });
  }

  function shareText() {
    var fe = eras()[favoriteEra()];
    var top = fe.top_tracks[0];
    var names = eras().map(function (e, i) { return visited[i] ? e.name : null; }).filter(Boolean);
    var n = Object.keys(visited).length;
    return [
      "MY TRANSMISSION \u2014 Aster da Master (2018 \u2192 2026)",
      "Eras visited: " + n + " of " + eras().length + (names.length ? " \u2014 " + names.join(" \u00b7 ") : ""),
      "Favorite era by plays: " + fe.name + " \u2014 " + fmt(fe.plays) + " plays across " + fe.transmissions + " transmissions",
      "Top track: \u201c" + top.title + "\u201d \u2014 " + fmt(top.plays) + " plays",
      "Signal: " + fe.signal,
      "Play counts: 2026-10-11 snapshot. Titles only, never lyrics."
    ].join("\n");
  }

  function copyTransmission(btn) {
    var done = function () {
      var label = btn.textContent;
      btn.textContent = "Copied \u2713";
      announce("Transmission copied: " + Object.keys(visited).length + " of " + eras().length +
        " eras visited. Favorite era by plays: " + eras()[favoriteEra()].name + ".");
      setTimeout(function () { btn.textContent = label; }, 2000);
    };
    var text = shareText();
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

  /* ---------- end card ---------- */
  function renderEnd() {
    var t = DATA.archive_totals;
    var stat = function (v, l) {
      return '<div class="stat"><div class="stat-value">' + v + '</div><div class="stat-label">' + l + "</div></div>";
    };
    $("tx-end-stats").innerHTML =
      stat(fmt(t.transmissions), "Transmissions, 2018\u20132026") +
      stat(fmt(t.plays), "Plays (2026-10-11 snapshot)") +
      stat(t.sessions, "Upload sessions") +
      stat(eras().length, "Eras traversed");
    var box = $("tx-share-out");
    box.textContent = shareText();
    box.hidden = false;
    document.title = "Signal received \u00b7 Transmission \u2014 Aster da Master";
  }

  /* ---------- wiring ---------- */
  function wire() {
    $("tx-begin").addEventListener("click", function () { era = 0; goEra(0); });
    $("tx-open-map").addEventListener("click", function () { renderMap(); show("map"); });
    $("tx-map-btn").addEventListener("click", function () { renderMap(); show("map"); });
    $("tx-map-back").addEventListener("click", function () { show("journey"); });
    $("tx-prev").addEventListener("click", prevEra);
    $("tx-next").addEventListener("click", function () { nextEra(true); });
    $("tx-replay").addEventListener("click", function () { stopAutoplay(); era = 0; goEra(0); });
    $("tx-copy").addEventListener("click", function () { copyTransmission($("tx-copy")); });
    $("tx-copy-end").addEventListener("click", function () { copyTransmission($("tx-copy-end")); });

    railEl.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-era]");
      if (b) goEra(parseInt(b.getAttribute("data-era"), 10));
    });
    $("tx-map-grid").addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-era]");
      if (b) goEra(parseInt(b.getAttribute("data-era"), 10));
    });

    if (REDUCED) {
      autoplayBtn.hidden = true; /* manual stepping only */
    } else {
      autoplayBtn.addEventListener("click", function () {
        if (timer) stopAutoplay();
        else startAutoplay();
      });
    }

    document.addEventListener("keydown", function (ev) {
      if (view !== "journey") return;
      var tag = (document.activeElement && document.activeElement.tagName) || "";
      if (/INPUT|TEXTAREA|SELECT/.test(tag)) return;
      if (ev.key === "ArrowRight") { ev.preventDefault(); nextEra(true); }
      else if (ev.key === "ArrowLeft") { ev.preventDefault(); prevEra(); }
      else if (ev.key === "Home") { ev.preventDefault(); goEra(0); }
      else if (ev.key === "End") { ev.preventDefault(); goEra(eras().length - 1); }
    });
  }

  /* ---------- boot ---------- */
  loadData("api/v1/transmission.json").then(function (d) {
    DATA = d;
    var t = d.archive_totals;
    document.querySelector('[data-tx-total="transmissions"]').textContent = fmt(t.transmissions);
    document.querySelector('[data-tx-total="plays"]').textContent = fmt(t.plays);
    document.querySelector('[data-tx-total="sessions"]').textContent = fmt(t.sessions);
    wire();
    if (window.ADM.reveal) window.ADM.reveal();
  }).catch(function () {
    $("tx-entry").insertAdjacentHTML("beforeend",
      '<p class="chart-sub" role="alert">The transmission data failed to load. The archive pages are all static and fine — this journey just needs its JSON.</p>');
  });
})();
