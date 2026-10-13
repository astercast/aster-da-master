/* The Tuner — tuner.html.
 * The full catalog as a broadcast dial. Data: data/v1/artist.json (the
 * artist record; discography is the catalog) + data/v1/release-slugs.json
 * (catalog index -> release page). Every stop renders only fields the
 * record actually carries — plays exist on vault tracks only, artwork on
 * distributor entries only, track counts on albums only. Nothing is
 * filled in, estimated, or invented; a failed fetch leaves the printed
 * first stop standing and says so. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(n) { return Number(n).toLocaleString("en-US"); }
  function pad(n, w) { var s = String(n); while (s.length < w) s = "0" + s; return s; }

  var FORMAT = {
    "SoundCloud-only": { key: "tracks", label: "Vault track", chip: "TRACK" },
    "Single": { key: "singles", label: "Single", chip: "SINGLE" },
    "Album": { key: "albums", label: "Album", chip: "ALBUM" }
  };

  var els = {
    years: document.getElementById("era-chips"),
    formats: document.getElementById("format-chips"),
    dial: document.getElementById("dial"),
    prev: document.getElementById("dial-prev"),
    next: document.getElementById("dial-next"),
    random: document.getElementById("dial-random"),
    needle: document.getElementById("tuner-needle"),
    stopNo: document.getElementById("stop-no"),
    stopMeta: document.getElementById("stop-meta"),
    progress: document.getElementById("tuner-progress-bar"),
    card: document.getElementById("tx-card"),
    status: document.getElementById("tuner-status"),
    logBody: document.getElementById("dial-log-body"),
    logCount: document.getElementById("dial-log-count")
  };
  if (!els.dial || !els.card) return;

  var ALL = [];        // every entry, chronological, with catalog index + slug
  var list = [];       // current filtered band
  var pos = 0;
  var yearFilter = "all";
  var formatFilter = "all";
  var minT = 0, maxT = 1;

  function filtered() {
    return ALL.filter(function (e) {
      if (yearFilter !== "all" && e.year !== yearFilter) return false;
      if (formatFilter !== "all" && FORMAT[e.type].key !== formatFilter) return false;
      return true;
    });
  }

  function needlePct(e) {
    var t = new Date(e.date + "T00:00:00Z").getTime();
    return Math.max(0, Math.min(100, ((t - minT) / (maxT - minT)) * 100));
  }

  function fact(b, span) {
    return "<div><b>" + esc(b) + "</b><span>" + esc(span) + "</span></div>";
  }

  function renderCard() {
    var e = list[pos];
    if (!e) return;
    var f = FORMAT[e.type];
    var facts = "";
    if (e.plays != null) facts += fact(fmt(e.plays), "plays — vault snapshot 2026-10-11");
    if (e.tracks) facts += fact(e.tracks, "tracks");
    if (e.label) facts += fact(e.label, "label");
    facts += fact(e.year, "era");
    facts += fact(f.label, "format");

    var note = "";
    if (e.note && e.note.indexOf("SoundCloud-vault track") !== 0) {
      var n = e.note;
      if (n.length > 220) n = n.slice(0, 217).replace(/\s+\S*$/, "") + "…";
      note = '<p class="tx-note">' + esc(n) + "</p>";
    }

    var actions = "";
    if (e.slug) {
      actions += '<a class="btn btn-neon" href="releases/' + esc(e.slug) + '.html">Release page &rarr;</a>';
    }
    (e.links || []).slice(0, 3).forEach(function (l) {
      if (l && l.url) {
        actions += '<a class="btn btn-ghost btn-sm" href="' + esc(l.url) +
          '" target="_blank" rel="noopener">' + esc(l.label || "Listen") + " &nearr;</a>";
      }
    });

    var plate = e.artwork
      ? '<img src="' + esc(e.artwork) + '" alt="Cover art — ' + esc(e.title) + '" loading="lazy">'
      : '<div class="plate-num"><b>' + pad(e.stop, 3) + '</b><span>' + esc(f.chip) +
        " · " + esc(e.year) + "</span></div>";

    els.card.innerHTML =
      '<div class="tx-plate">' + plate + "</div>" +
      '<div class="tx-body">' +
        '<div class="tx-meta"><span class="tx-type">' + esc(f.chip) + "</span>" +
          "<span>" + esc(e.date) + "</span><span>Stop " + pad(e.stop, 3) + " of " + ALL.length + "</span></div>" +
        '<h2 class="tx-title">' + esc(e.title) + "</h2>" +
        '<div class="tx-facts">' + facts + "</div>" +
        note +
        '<div class="tx-actions">' + actions + "</div>" +
      "</div>";

    els.stopNo.innerHTML = "STOP <em>" + pad(e.stop, 3) + "</em> / " + ALL.length;
    els.stopMeta.textContent =
      "Band " + (pos + 1) + " of " + list.length + " · " +
      (yearFilter === "all" ? "all eras" : yearFilter) + " · " +
      (formatFilter === "all" ? "all formats" : formatFilter) + " · " + e.date;
    els.needle.style.left = needlePct(e).toFixed(2) + "%";
    els.progress.style.width = (list.length > 1 ? (pos / (list.length - 1)) * 100 : 100) + "%";
    els.dial.setAttribute("aria-valuetext",
      "Stop " + e.stop + " of " + ALL.length + ": " + e.title + ", " + e.date + ", " + f.label);
    if (e.slug) {
      try { history.replaceState(null, "", "#" + e.slug); } catch (err) { /* file:// */ }
    }
    var live = els.logBody.querySelector("tr.is-live");
    if (live) live.classList.remove("is-live");
    var row = els.logBody.querySelector('tr[data-stop="' + e.stop + '"]');
    if (row) row.classList.add("is-live");
  }

  function tune(newPos, focusDial) {
    if (!list.length) return;
    pos = Math.max(0, Math.min(list.length - 1, newPos));
    els.dial.max = String(list.length - 1);
    els.dial.value = String(pos);
    renderCard();
    if (focusDial) els.dial.focus();
  }

  function applyFilters(keepStop) {
    list = filtered();
    var idx = 0;
    if (keepStop != null) {
      for (var i = 0; i < list.length; i++) if (list[i].stop === keepStop) { idx = i; break; }
    }
    tune(idx, false);
    els.status.textContent = list.length + (list.length === 1 ? " transmission" : " transmissions") +
      " on this band.";
    els.status.classList.remove("is-lost");
  }

  function chip(label, sub, pressed, onClick) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.setAttribute("aria-pressed", pressed ? "true" : "false");
    b.innerHTML = esc(label) + (sub != null ? " <small>" + esc(sub) + "</small>" : "");
    b.addEventListener("click", onClick);
    return b;
  }

  function renderControls() {
    var years = [];
    var counts = {};
    ALL.forEach(function (e) {
      if (!counts[e.year]) { counts[e.year] = 0; years.push(e.year); }
      counts[e.year]++;
    });
    years.sort();
    els.years.innerHTML = "";
    els.years.appendChild(chip("All eras", ALL.length, yearFilter === "all", function () {
      yearFilter = "all"; renderControls(); applyFilters(currentStop());
    }));
    years.forEach(function (y) {
      els.years.appendChild(chip(y, counts[y], yearFilter === y, function () {
        yearFilter = y; renderControls(); applyFilters(currentStop());
      }));
    });

    var fcounts = { tracks: 0, singles: 0, albums: 0 };
    ALL.forEach(function (e) { fcounts[FORMAT[e.type].key]++; });
    var fopts = [["all", "All formats", ALL.length],
                 ["tracks", "Tracks", fcounts.tracks],
                 ["singles", "Singles", fcounts.singles],
                 ["albums", "Albums", fcounts.albums]];
    els.formats.innerHTML = "";
    fopts.forEach(function (o) {
      els.formats.appendChild(chip(o[1], o[2], formatFilter === o[0], function () {
        formatFilter = o[0]; renderControls(); applyFilters(currentStop());
      }));
    });
  }

  function currentStop() { return list[pos] ? list[pos].stop : null; }

  function renderLog() {
    var html = "";
    ALL.forEach(function (e) {
      var f = FORMAT[e.type];
      html += '<tr data-stop="' + e.stop + '" tabindex="0" role="button" aria-label="Tune to ' +
        esc(e.title) + '">' +
        '<td class="n">' + pad(e.stop, 3) + "</td>" +
        "<td>" + esc(e.title) + "</td>" +
        "<td>" + esc(e.date) + "</td>" +
        "<td>" + esc(f.chip) + "</td>" +
        '<td class="p">' + (e.plays != null ? fmt(e.plays) : "—") + "</td>" +
        '<td class="src">' + (e.slug
          ? '<a href="releases/' + esc(e.slug) + '.html">Release page &rarr;</a>' : "") + "</td></tr>";
    });
    els.logBody.innerHTML = html;
    els.logCount.textContent = ALL.length + " stops";
    Array.prototype.forEach.call(els.logBody.querySelectorAll("tr"), function (tr) {
      function go(ev) {
        if (ev.target && ev.target.closest && ev.target.closest("a")) return;
        var stop = Number(tr.getAttribute("data-stop"));
        yearFilter = "all"; formatFilter = "all"; renderControls();
        applyFilters(stop);
        document.getElementById("tuner").scrollIntoView({ block: "start" });
        els.dial.focus();
      }
      tr.addEventListener("click", go);
      tr.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(ev); }
      });
    });
  }

  els.dial.addEventListener("input", function () { tune(Number(els.dial.value), false); });
  els.prev.addEventListener("click", function () { tune(pos - 1, false); });
  els.next.addEventListener("click", function () { tune(pos + 1, false); });
  els.random.addEventListener("click", function () {
    if (list.length < 2) return;
    var n = pos;
    while (n === pos) n = Math.floor(Math.random() * list.length);
    tune(n, false);
  });

  function fail() {
    els.status.textContent =
      "Signal lost — the catalog file did not load, so the printed first stop stands as the record. " +
      "The full catalog lives in the release index and the discography on the home page.";
    els.status.classList.add("is-lost");
  }

  Promise.all([
    fetch("data/v1/artist.json", { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error("artist " + r.status); return r.json();
    }),
    fetch("data/v1/release-slugs.json", { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error("slugs " + r.status); return r.json();
    }).catch(function () { return {}; })
  ]).then(function (res) {
    var artist = res[0], slugs = res[1] || {};
    var disc = (artist && artist.discography) || [];
    ALL = disc.map(function (e, i) {
      return {
        stop: i + 1, // catalog stop = position after the chronological sort below
        title: e.title, date: e.date, year: String(e.date).slice(0, 4),
        type: e.type, plays: e.plays != null ? Number(e.plays) : null,
        label: e.label || null, tracks: e.tracks || null,
        artwork: e.artwork || null, links: e.links || [],
        note: e.note || null, slug: slugs[String(i)] || null, _i: i
      };
    });
    ALL.sort(function (a, b) {
      if (a.date !== b.date) return a.date < b.date ? -1 : 1;
      return a.title.toLowerCase() < b.title.toLowerCase() ? -1 : 1;
    });
    ALL.forEach(function (e, idx) { e.stop = idx + 1; });
    if (!ALL.length) { fail(); return; }
    var times = ALL.map(function (e) { return new Date(e.date + "T00:00:00Z").getTime(); });
    minT = Math.min.apply(null, times); maxT = Math.max.apply(null, times);
    if (maxT <= minT) maxT = minT + 1;

    renderControls();
    renderLog();

    var startStop = null;
    var hash = (location.hash || "").replace(/^#/, "");
    if (hash) {
      for (var i = 0; i < ALL.length; i++) if (ALL[i].slug === hash) { startStop = ALL[i].stop; break; }
    }
    applyFilters(startStop);
  }).catch(fail);
})();
