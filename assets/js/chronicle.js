/* THE CHRONICLE — one merged chronological stream.
   Renders api/v1/chronicle.json live: 61 sessions, 9 dated milestones,
   44 title-credited collaboration appearances. Era / kind / voice filters,
   full-text search, oldest<->newest order, shareable filter state via the
   URL hash, collaborator cross-link buttons on every row.

   Accessibility: native form controls, aria-live result count, skip link,
   focus-visible styles from the shared CSS, semantic list. No animation in
   this script at all, so prefers-reduced-motion needs no special path.
   Mobile-first via the shared CSS. */
(function () {
  "use strict";

  var esc = window.ADM.esc;
  var fmt = window.ADM.fmt;
  var loadData = window.ADM.loadData;

  var DATA = null;
  var slugByName = {};   // collaborator display name -> slug (cross-links)

  var state = {
    era: "all",          // "all" | era id | "pre"
    kinds: { milestone: true, session: true, collaboration: true },
    collab: "all",       // "all" | collaborator slug
    q: "",
    sort: "asc"          // "asc" | "desc"
  };

  var $ = function (id) { return document.getElementById(id); };
  var streamEl, countEl, statsEl;

  var KIND_GLYPH = { milestone: "\u25c6", session: "\u25cf", collaboration: "\u25b2" };
  var KIND_LABEL = { milestone: "Milestone", session: "Session", collaboration: "Collaboration" };

  /* ---------------- state from the hash ---------------- */
  function readHash() {
    var h = (window.location.hash || "").replace(/^#/, "");
    if (!h) return null;
    if (h.indexOf("event=") === 0) return { event: h.slice(6) };
    var out = {};
    h.split("&").forEach(function (pair) {
      var kv = pair.split("=");
      if (kv.length === 2) out[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1]);
    });
    return out;
  }

  function applyHashState(h) {
    if (!h || h.event) return;
    if (h.era) state.era = h.era;
    if (h.kind) {
      var on = {};
      h.kind.split(",").forEach(function (k) { on[k] = true; });
      Object.keys(state.kinds).forEach(function (k) { state.kinds[k] = !!on[k]; });
    }
    if (h.collab) state.collab = h.collab;
    if (typeof h.q === "string") state.q = h.q;
    if (h.sort === "desc" || h.sort === "asc") state.sort = h.sort;
  }

  function writeHash() {
    var parts = [];
    if (state.era !== "all") parts.push("era=" + encodeURIComponent(state.era));
    var kindsOn = Object.keys(state.kinds).filter(function (k) { return state.kinds[k]; });
    if (kindsOn.length !== 3) parts.push("kind=" + kindsOn.join(","));
    if (state.collab !== "all") parts.push("collab=" + encodeURIComponent(state.collab));
    if (state.q) parts.push("q=" + encodeURIComponent(state.q));
    if (state.sort !== "asc") parts.push("sort=" + state.sort);
    var h = parts.length ? "#" + parts.join("&") : "#";
    if (window.location.hash !== h) {
      window.history.replaceState(null, "", h === "#" ? window.location.pathname : h);
    }
  }

  /* ---------------- filtering ---------------- */
  function eventCollabSlugs(e) {
    // every collaborator slug attached to an event (cross-link targets)
    if (e.kind === "collaboration" && e.collab_slug) return [e.collab_slug];
    var out = [];
    (e.collaborators || []).forEach(function (name) {
      if (slugByName[name]) out.push(slugByName[name]);
    });
    if (e.collab_slug && out.indexOf(e.collab_slug) === -1) out.push(e.collab_slug);
    return out;
  }

  function matches(e) {
    if (!state.kinds[e.kind]) return false;
    if (state.era === "pre") {
      if (e.era_id !== null) return false;
    } else if (state.era !== "all" && e.era_id !== state.era) {
      return false;
    }
    if (state.collab !== "all" && eventCollabSlugs(e).indexOf(state.collab) === -1) {
      return false;
    }
    if (state.q) {
      var hay = (e.title + " " + e.detail + " " + e.era_name + " " +
        (e.collaborators || []).join(" ")).toLowerCase();
      if (hay.indexOf(state.q.toLowerCase()) === -1) return false;
    }
    return true;
  }

  /* ---------------- rendering ---------------- */
  function statCell(value, label) {
    return '<div class="stat"><div class="stat-value">' + value +
      '</div><div class="stat-label">' + label + "</div></div>";
  }

  function renderStats() {
    var ins = DATA.insights;
    statsEl.innerHTML =
      statCell(fmt(ins.event_count), "Events in the stream") +
      statCell(esc(ins.first_date) + "<br>" + esc(ins.last_date), "Span") +
      statCell(ins.by_kind.milestone, "Milestones") +
      statCell(ins.by_kind.session, "Sessions") +
      statCell(ins.by_kind.collaboration, "Collaborations") +
      statCell(esc(ins.busiest_year.year), "Busiest year (" + ins.busiest_year.events + " events)");
  }

  function renderEraOptions() {
    var sel = $("ch-era");
    var opts = '<option value="all">All eras</option>';
    DATA.eras.forEach(function (e) {
      opts += '<option value="' + esc(e.id) + '">' + esc(e.name) + "</option>";
    });
    opts += '<option value="pre">Before the vault (2017)</option>';
    sel.innerHTML = opts;
    sel.value = state.era;
  }

  function renderCollabOptions() {
    var sel = $("ch-collab");
    var opts = '<option value="all">All voices</option>';
    DATA.collaborators.forEach(function (c) {
      opts += '<option value="' + esc(c.slug) + '">' + esc(c.name) +
        " (" + c.appearances + ")</option>";
    });
    sel.innerHTML = opts;
    // guard: a stale hash slug that no longer exists falls back to "all"
    var known = DATA.collaborators.some(function (c) { return c.slug === state.collab; });
    if (state.collab !== "all" && !known) state.collab = "all";
    sel.value = state.collab;
  }

  function rowHtml(e) {
    var kindCls = "ch-kind ch-kind-" + e.kind;
    var dateTxt = e.end_date ? esc(e.date) + " \u2192 " + esc(e.end_date) : esc(e.date);
    var voices = "";
    var slugs = eventCollabSlugs(e);
    if (slugs.length) {
      var btns = slugs.map(function (s) {
        var c = DATA.collaborators.filter(function (x) { return x.slug === s; })[0];
        var name = c ? c.name : s;
        var pressed = state.collab === s ? "true" : "false";
        return '<button type="button" class="ch-xlink" data-collab="' + esc(s) + '"' +
          ' aria-pressed="' + pressed + '" aria-label="Show only ' + esc(name) +
          ' events">' + esc(name) + "</button>";
      }).join("");
      voices = '<p class="ch-voices"><span>Voices:</span>' + btns + "</p>";
    }
    var links = (e.links || []).map(function (l) {
      return '<a href="' + esc(l.href) + '">' + esc(l.label) + "</a>";
    }).join("");
    var plays = e.plays !== null && e.plays !== undefined ?
      '<span>' + fmt(e.plays) + " plays</span>" : "";
    var meta = [esc(e.era_name), plays].filter(Boolean).join(" \u00b7 ");
    return '<li class="ch-row" id="event-' + esc(e.id) + '">' +
      '<div class="ch-row-top"><span class="ch-date">' + dateTxt + "</span>" +
      '<span class="' + kindCls + '"><span aria-hidden="true">' + KIND_GLYPH[e.kind] +
      "</span> " + KIND_LABEL[e.kind] + "</span></div>" +
      "<h3>" + esc(e.title) + "</h3>" +
      '<p class="ch-detail">' + esc(e.detail) + "</p>" +
      (meta ? '<p class="ch-meta">' + meta + "</p>" : "") +
      (links ? '<p class="ch-links">' + links + "</p>" : "") +
      voices +
      "</li>";
  }

  function render() {
    var list = DATA.events.filter(matches);
    if (state.sort === "desc") list = list.slice().reverse();
    if (!list.length) {
      streamEl.innerHTML = "";
      var empty = document.createElement("div");
      empty.className = "ch-empty";
      var p1 = document.createElement("p");
      p1.textContent = "No events match these filters.";
      var p2 = document.createElement("p");
      var rbtn = document.createElement("button");
      rbtn.type = "button";
      rbtn.className = "btn btn-sm";
      rbtn.textContent = "Reset filters";
      rbtn.addEventListener("click", resetFilters);
      p2.appendChild(rbtn);
      empty.appendChild(p1);
      empty.appendChild(p2);
      streamEl.appendChild(empty);
    } else {
      streamEl.innerHTML = list.map(rowHtml).join("");
      streamEl.querySelectorAll(".ch-xlink").forEach(function (btn) {
        btn.addEventListener("click", function () {
          setCollab(btn.getAttribute("data-collab"));
        });
      });
    }
    var total = DATA.events.length;
    var order = state.sort === "desc" ? "newest first" : "oldest first";
    countEl.textContent = list.length === total ?
      total + " events \u2014 the whole run, " + order :
      list.length + " of " + total + " events (" + order + ")";
  }

  /* ---------------- controls ---------------- */
  function syncControls() {
    $("ch-era").value = state.era;
    $("ch-kind-milestone").checked = state.kinds.milestone;
    $("ch-kind-session").checked = state.kinds.session;
    $("ch-kind-collaboration").checked = state.kinds.collaboration;
    $("ch-collab").value = state.collab;
    if ($("ch-q").value !== state.q) $("ch-q").value = state.q;
    $("ch-sort").value = state.sort;
  }

  function setCollab(slug) {
    // clicking the active voice's button again clears the filter (toggle)
    state.collab = (state.collab === slug) ? "all" : slug;
    syncControls();
    writeHash();
    render();
  }

  function resetFilters() {
    state.era = "all";
    state.kinds = { milestone: true, session: true, collaboration: true };
    state.collab = "all";
    state.q = "";
    state.sort = "asc";
    syncControls();
    writeHash();
    render();
    $("ch-filters-h").scrollIntoView();
  }

  function wireControls() {
    $("ch-era").addEventListener("change", function (ev) {
      state.era = ev.target.value; writeHash(); render();
    });
    ["milestone", "session", "collaboration"].forEach(function (k) {
      $("ch-kind-" + k).addEventListener("change", function (ev) {
        state.kinds[k] = ev.target.checked; writeHash(); render();
      });
    });
    $("ch-collab").addEventListener("change", function (ev) {
      state.collab = ev.target.value; writeHash(); render();
    });
    var qTimer = null;
    $("ch-q").addEventListener("input", function (ev) {
      window.clearTimeout(qTimer);
      qTimer = window.setTimeout(function () {
        state.q = ev.target.value.trim(); writeHash(); render();
      }, 250);
    });
    $("ch-sort").addEventListener("change", function (ev) {
      state.sort = ev.target.value; writeHash(); render();
    });
    $("ch-reset").addEventListener("click", resetFilters);
    $("ch-copy").addEventListener("click", function () {
      writeHash();
      var url = window.location.href;
      var done = function () {
        var b = $("ch-copy");
        b.textContent = "Link copied";
        window.setTimeout(function () { b.textContent = "Copy link to this view"; }, 2000);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(done, function () { fallbackCopy(url, done); });
      } else {
        fallbackCopy(url, done);
      }
    });
    // the form must never submit/reload (Enter in the search box)
    $("ch-filters").addEventListener("submit", function (ev) { ev.preventDefault(); });
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* clipboard unavailable */ }
    document.body.removeChild(ta);
    done();
  }

  /* ---------------- boot ---------------- */
  function fail() {
    countEl.textContent = "The chronicle data failed to load.";
    streamEl.innerHTML = '<div class="ch-empty"><p>The stream could not be tuned. ' +
      'The data lives at <a href="api/v1/chronicle.json">api/v1/chronicle.json</a>.</p></div>';
    window.ADM.reveal();
  }

  function boot() {
    streamEl = $("ch-stream");
    countEl = $("ch-count");
    statsEl = $("ch-stats");
    loadData("api/v1/chronicle.json").then(function (data) {
      DATA = data;
      DATA.collaborators.forEach(function (c) { slugByName[c.name] = c.slug; });
      var h = readHash();
      applyHashState(h);
      renderStats();
      renderEraOptions();
      renderCollabOptions();
      syncControls();
      wireControls();
      render();
      // deep link to one event: scroll it into view and mark it
      if (h && h.event) {
        var target = $("event-" + h.event);
        if (target) {
          target.scrollIntoView();
          target.setAttribute("tabindex", "-1");
          target.focus({ preventScroll: true });
        }
      }
      window.ADM.reveal();
    }, fail);
  }

  boot();
})();
