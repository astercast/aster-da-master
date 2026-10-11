/* Collaboration network — artist at center, collaborators on rings by track count.
   Vanilla SVG, deterministic layout. Keyboard: Tab to a node, Enter/Space selects,
   arrow keys move between nodes. Full <details> list fallback for screen readers. */
(function () {
  "use strict";
  var esc = ADM.esc, fmt = ADM.fmt, parseCollabs = ADM.parseCollabs, slugify = ADM.slugify;
  ADM.reveal();

  var svg = document.getElementById("nw-svg");
  var panel = document.getElementById("nw-panel");
  var list = document.getElementById("nw-list");
  var NS = "http://www.w3.org/2000/svg";

  var W = 920, H = 620, CX = W / 2, CY = H / 2;

  function el(name, attrs, parent) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function trackLine(t) {
    var meta = [t.date || "date unknown", t.type, t.plays != null ? fmt(t.plays) + " plays" : null]
      .filter(Boolean).join(" · ");
    return "<li><span>" + esc(t.title) + "</span><span class=\"top-n\">" + esc(meta) + "</span></li>";
  }

  function selectNode(display, info, nodeEls) {
    nodeEls.forEach(function (n) { n.g.classList.remove("is-selected"); n.g.setAttribute("aria-pressed", "false"); });
    if (info.node) {
      info.node.g.classList.add("is-selected");
      info.node.g.setAttribute("aria-pressed", "true");
    }
    panel.innerHTML =
      "<h3>" + esc(display) + "</h3>" +
      "<p class=\"chart-sub\">" + info.tracks.length + " shared transmission" + (info.tracks.length === 1 ? "" : "s") + "</p>" +
      "<p><a class=\"btn btn-sm\" href=\"circle/" + slugify(display) + ".html\">Full page &rarr;</a></p>" +
      "<ol class=\"top-list\">" + info.tracks.map(trackLine).join("") + "</ol>";
  }

  ADM.loadData("data/artist.json").then(function (d) {
    var disc = d.discography || [];
    var collabs = {};
    disc.forEach(function (r) {
      parseCollabs(r.title).forEach(function (n) {
        var k = n.toLowerCase();
        collabs[k] = collabs[k] || { display: n, tracks: [] };
        if (n.length >= collabs[k].display.length) collabs[k].display = n;
        collabs[k].tracks.push({ title: r.title, date: r.date, plays: r.plays, type: r.type });
      });
    });
    var keys = Object.keys(collabs).sort(function (a, b) { return collabs[b].tracks.length - collabs[a].tracks.length; });
    if (!keys.length) {
      panel.innerHTML = "<p class=\"chart-sub\">No credited collaborators found in the archive.</p>";
      return;
    }

    /* deterministic layout: top 8 inner ring, rest outer ring */
    var inner = keys.slice(0, 8), outer = keys.slice(8);
    var R1 = 150, R2 = 245;
    var maxC = collabs[keys[0]].tracks.length;

    function pos(i, n, R) {
      var a = -Math.PI / 2 + (i / n) * Math.PI * 2;
      return { x: CX + R * Math.cos(a), y: CY + R * Math.sin(a) };
    }

    /* edges first (under nodes) */
    keys.forEach(function (k, i) {
      var p = i < inner.length ? pos(i, inner.length, R1) : pos(i - inner.length, outer.length, R2);
      var w = 1 + (collabs[k].tracks.length / maxC) * 4;
      el("line", {
        x1: CX, y1: CY, x2: p.x.toFixed(1), y2: p.y.toFixed(1),
        "class": "nw-edge", "stroke-width": w.toFixed(1)
      }, svg);
    });

    /* artist node */
    var artistG = el("g", { "class": "nw-node is-artist", tabindex: "0", role: "button", "aria-pressed": "false",
      "aria-label": "Aster da Master — select to reset" }, svg);
    el("circle", { cx: CX, cy: CY, r: 40, "class": "nw-circle" }, artistG);
    var at = el("text", { x: CX, y: CY + 5, "class": "nw-artist-label", "text-anchor": "middle" }, artistG);
    at.textContent = "A✦";

    /* collaborator nodes */
    var nodeEls = [];
    keys.forEach(function (k, i) {
      var info = collabs[k];
      var p = i < inner.length ? pos(i, inner.length, R1) : pos(i - inner.length, outer.length, R2);
      var r = 12 + (info.tracks.length / maxC) * 22;
      var g = el("g", {
        "class": "nw-node", tabindex: "0", role: "button", "aria-pressed": "false",
        "aria-label": info.display + ", " + info.tracks.length + " shared transmissions. Activate to list them."
      }, svg);
      el("circle", { cx: p.x.toFixed(1), cy: p.y.toFixed(1), r: r.toFixed(1), "class": "nw-circle" }, g);
      var t = el("text", { x: p.x.toFixed(1), y: (p.y + r + 16).toFixed(1), "class": "nw-label", "text-anchor": "middle" }, g);
      t.textContent = info.display;
      var c = el("text", { x: p.x.toFixed(1), y: (p.y + 4).toFixed(1), "class": "nw-count", "text-anchor": "middle" }, g);
      c.textContent = "×" + info.tracks.length;
      var rec = { g: g, k: k };
      nodeEls.push(rec);
      g._rec = rec;

      g.addEventListener("click", function () { selectNode(info.display, { tracks: info.tracks, node: rec }, nodeEls.concat([{ g: artistG }])); });
      g.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectNode(info.display, { tracks: info.tracks, node: rec }, nodeEls.concat([{ g: artistG }]));
        } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          e.preventDefault();
          var nx = nodeEls[(nodeEls.indexOf(rec) + 1) % nodeEls.length];
          nx.g.focus();
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          e.preventDefault();
          var pv = nodeEls[(nodeEls.indexOf(rec) - 1 + nodeEls.length) % nodeEls.length];
          pv.g.focus();
        }
      });
    });

    var allNodes = nodeEls.concat([{ g: artistG }]);
    function resetSel() {
      nodeEls.forEach(function (n) { n.g.classList.remove("is-selected"); n.g.setAttribute("aria-pressed", "false"); });
      artistG.classList.remove("is-selected");
      artistG.setAttribute("aria-pressed", "false");
      panel.innerHTML = "<p class=\"chart-sub\">Select a node to see their transmissions.</p>";
    }
    artistG.addEventListener("click", resetSel);
    artistG.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); resetSel(); }
    });

    /* list fallback — full screen-reader access, no SVG required */
    list.innerHTML = keys.map(function (k) {
      var info = collabs[k];
      return "<details><summary>" + esc(info.display) +
        " <span class=\"top-n\">×" + info.tracks.length + "</span></summary>" +
        "<p><a href=\"circle/" + slugify(info.display) + ".html\">Full page &rarr;</a></p>" +
        "<ol class=\"top-list\">" + info.tracks.map(trackLine).join("") + "</ol></details>";
    }).join("");
  }).catch(function () {
    panel.innerHTML = "<p class=\"chart-sub\">Could not load the archive data.</p>";
  });
})();
