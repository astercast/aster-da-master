/* Aster da Master — global search overlay.
   Searches transmissions, collaborators, codex families, and eras.
   "/" opens (outside text fields), Esc closes, arrows + Enter navigate. */
(function () {
  "use strict";

  var openBtn = document.getElementById("search-open");
  var overlay = document.getElementById("search-overlay");
  var input = document.getElementById("search-input");
  var results = document.getElementById("search-results");
  if (!openBtn || !overlay || !input || !results) return;

  var items = [];
  var activeIdx = -1;
  var lastFocus = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function parseCollabs(title) {
    var names = [];
    var re = /(?:\bw\/\s*|\bft\.?\s+|\bfeat\.?\s+)/gi;
    var m;
    while ((m = re.exec(title)) !== null) {
      var rest = title.slice(m.index + m[0].length);
      rest = rest.split(/[([]/)[0].split(/prod\.?/i)[0];
      rest.split(/\s+[xX]\s+|\s*&\s*|\s*\+\s*|,|\s*\/\s*|\s+and\s+/).forEach(function (p) {
        p = p.replace(/^[ .!~)"']+|[ .!~)"']+$/g, "");
        if (p && p.length < 30 && !/aster\s*da\s*master/i.test(p) && !/prod/i.test(p)) {
          names.push(p);
        }
      });
    }
    return names;
  }

  function absUrl(path) {
    return new URL(path, document.baseURI).href;
  }

  function onIndexPage() {
    var p = location.pathname.replace(/\/+$/, "");
    return p === "" || /index\.html$/.test(p);
  }
  function home(anchor) {
    return onIndexPage() ? anchor : "index.html" + anchor;
  }

  function load() {
    return Promise.all([
      fetch(absUrl("data/artist.json")).then(function (r) { if (!r.ok) throw 0; return r.json(); }),
      fetch(absUrl("api/v1/release-slugs.json")).then(function (r) { if (!r.ok) throw 0; return r.json(); }),
      fetch(absUrl("data/codex.json")).then(function (r) { if (!r.ok) return null; return r.json(); }).catch(function () { return null; })
    ]).then(function (parts) {
      var d = parts[0], slugs = parts[1], codex = parts[2];
      var disc = d.discography || [];

      var collabCount = {};
      disc.forEach(function (r) {
        parseCollabs(r.title).forEach(function (n) {
          var k = n.toLowerCase();
          collabCount[k] = collabCount[k] || { name: n, n: 0 };
          collabCount[k].n++;
        });
      });

      disc.forEach(function (r, i) {
        items.push({
          kind: "Transmission",
          label: r.title,
          sub: r.type + " · " + (r.date || "date unknown") + (r.plays != null ? " · " + Number(r.plays).toLocaleString("en-US") + " plays" : ""),
          url: "releases/" + slugs[String(i)] + ".html",
          hay: r.title.toLowerCase()
        });
      });

      Object.keys(collabCount).forEach(function (k) {
        var c = collabCount[k];
        items.push({
          kind: "Collaborator",
          label: c.name,
          sub: c.n + (c.n === 1 ? " transmission" : " transmissions") + " together",
          url: "network.html",
          hay: c.name.toLowerCase()
        });
      });

      (d.eras || []).forEach(function (e) {
        items.push({
          kind: "Era",
          label: e.name,
          sub: e.span,
          url: home("#eras"),
          hay: (e.name + " " + e.span).toLowerCase()
        });
      });

      if (codex && codex.families) {
        codex.families.forEach(function (f) {
          items.push({
            kind: "Codex",
            label: f.name,
            sub: "word family · " + (f.tracks || []).length + " titles",
            url: home("#codex"),
            hay: (f.name + " " + (f.words || []).join(" ")).toLowerCase()
          });
        });
      }
    });
  }

  function score(hay, q) {
    if (hay.indexOf(q) === 0) return 2;
    if (hay.indexOf(q) !== -1) return 1;
    return 0;
  }

  function render(q) {
    q = q.trim().toLowerCase();
    activeIdx = -1;
    if (q.length < 2) {
      results.innerHTML = '<p class="search-empty">Type at least two characters — tracks, collaborators, eras, the codex.</p>';
      input.removeAttribute("aria-activedescendant");
      return;
    }
    var hits = [];
    for (var i = 0; i < items.length; i++) {
      var s = score(items[i].hay, q);
      if (s > 0) hits.push({ it: items[i], s: s });
    }
    hits.sort(function (a, b) { return b.s - a.s || a.it.label.localeCompare(b.it.label); });
    hits = hits.slice(0, 14);
    if (!hits.length) {
      results.innerHTML = '<p class="search-empty">Nothing in the archive answers to that. Try a track, a name, a word.</p>';
      input.removeAttribute("aria-activedescendant");
      return;
    }
    results.innerHTML = hits.map(function (h, i) {
      return '<a class="search-item" id="search-opt-' + i + '" role="option" aria-selected="false" href="' + esc(h.it.url) + '">' +
        '<span class="search-kind">' + esc(h.it.kind) + "</span>" +
        '<span class="search-label">' + esc(h.it.label) + "</span>" +
        '<span class="search-sub">' + esc(h.it.sub) + "</span></a>";
    }).join("");
  }

  function setActive(i) {
    var opts = results.querySelectorAll(".search-item");
    opts.forEach(function (o) { o.classList.remove("is-active"); o.setAttribute("aria-selected", "false"); });
    activeIdx = i;
    if (i >= 0 && opts[i]) {
      opts[i].classList.add("is-active");
      opts[i].setAttribute("aria-selected", "true");
      input.setAttribute("aria-activedescendant", opts[i].id);
      opts[i].scrollIntoView({ block: "nearest" });
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  }

  function open() {
    lastFocus = document.activeElement;
    overlay.hidden = false;
    document.body.classList.add("search-open");
    render(input.value);
    setTimeout(function () { input.focus(); }, 0);
  }

  function close() {
    overlay.hidden = true;
    document.body.classList.remove("search-open");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  openBtn.addEventListener("click", open);
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) close();
  });

  var debounce;
  input.addEventListener("input", function () {
    clearTimeout(debounce);
    debounce = setTimeout(function () { render(input.value); }, 120);
  });

  input.addEventListener("keydown", function (e) {
    var opts = results.querySelectorAll(".search-item");
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive(opts.length ? (activeIdx + 1) % opts.length : -1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive(opts.length ? (activeIdx - 1 + opts.length) % opts.length : -1);
    } else if (e.key === "Enter") {
      if (activeIdx >= 0 && opts[activeIdx]) {
        e.preventDefault();
        location.href = opts[activeIdx].getAttribute("href");
      }
    }
  });

  document.addEventListener("keydown", function (e) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || "");
    if (e.key === "/" && overlay.hidden && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
      e.preventDefault();
      open();
    } else if (e.key === "Escape" && !overlay.hidden) {
      close();
    }
  });

  load().catch(function () {
    results.innerHTML = '<p class="search-empty">The archive could not be loaded. Check your connection and try again.</p>';
  });
})();
