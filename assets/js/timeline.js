/* Career timeline — every transmission 2018–2026, plotted client-side from data/artist.json.
   Gold lane = distributor releases; neon points = vault tracks, height by log play count. */
(function () {
  "use strict";
  var esc = ADM.esc, fmt = ADM.fmt, spanYears = ADM.spanYears;
  ADM.reveal();

  var svg = document.getElementById("tl-svg");
  var tip = document.getElementById("tl-tip");
  var yearsCtl = document.getElementById("tl-years");
  var summary = document.getElementById("tl-summary");
  var NS = "http://www.w3.org/2000/svg";

  var W = 1000, H = 560, ML = 46, MR = 18, MT = 64, MB = 54;
  var LANE_H = 92; /* distributor lane height at top */

  function el(name, attrs, parent) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function showTip(html, x, y) {
    tip.innerHTML = html;
    tip.hidden = false;
    var wrap = tip.parentElement.getBoundingClientRect();
    tip.style.left = Math.min(Math.max(x + 14, 8), wrap.width - 240) + "px";
    tip.style.top = Math.max(y - 10, 8) + "px";
  }
  function hideTip() { tip.hidden = true; }

  function render(d, year) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    hideTip();

    var disc = d.discography || [];
    var vault = disc.filter(function (r) { return r.type === "SoundCloud-only" && r.date; });
    var dist = disc.filter(function (r) { return r.type !== "SoundCloud-only" && r.date; });

    var t0 = year ? Date.UTC(year, 0, 1) : Date.UTC(2018, 0, 1);
    var t1 = year ? Date.UTC(year + 1, 0, 1) : Date.UTC(2027, 0, 1);
    function inRange(r) { var t = Date.parse(r.date + "T00:00:00Z"); return t >= t0 && t < t1; }
    vault = vault.filter(inRange);
    dist = dist.filter(inRange);

    var iw = W - ML - MR, ih = H - MT - MB;
    function X(date) {
      var t = Date.parse(date + "T00:00:00Z");
      return ML + ((t - t0) / (t1 - t0)) * iw;
    }
    /* vault zone: below the distributor lane */
    var vz0 = MT + LANE_H, vz1 = H - MB;
    var maxLog = Math.log10(30088 + 1);
    function Y(plays) {
      var l = Math.log10((plays || 0) + 1);
      return vz1 - (l / maxLog) * (vz1 - vz0);
    }

    /* era bands */
    (d.eras || []).forEach(function (e) {
      var s = spanYears(e.span);
      if (!s) return;
      var b0 = Math.max(Date.UTC(s.start, 0, 1), t0);
      var b1 = Math.min(Date.UTC(s.end + 1, 0, 1), t1);
      if (b1 <= b0) return;
      var x0 = ML + ((b0 - t0) / (t1 - t0)) * iw;
      var x1 = ML + ((b1 - t0) / (t1 - t0)) * iw;
      el("rect", { x: x0.toFixed(1), y: MT, width: Math.max(x1 - x0, 2).toFixed(1), height: ih, "class": "tl-era" }, svg);
      if (x1 - x0 > 70) {
        var t = el("text", { x: (x0 + 8).toFixed(1), y: MT + 18, "class": "tl-era-label" }, svg);
        t.textContent = e.name;
      }
    });

    /* distributor lane */
    el("rect", { x: ML, y: MT, width: iw, height: LANE_H, "class": "tl-lane" }, svg);
    var laneLabel = el("text", { x: ML + 8, y: MT + 20, "class": "tl-lane-label" }, svg);
    laneLabel.textContent = "DISTRIBUTOR · " + dist.length;
    var laneY = MT + LANE_H / 2 + 8;
    dist.forEach(function (r) {
      var x = X(r.date);
      var g = el("g", {
        "class": "tl-pt is-dist", tabindex: "0", role: "img",
        "aria-label": r.title + ", distributor " + (r.type || "") + ", released " + r.date
      }, svg);
      el("path", { d: "M " + x.toFixed(1) + " " + (laneY - 7) + " L " + (x + 7).toFixed(1) + " " + laneY + " L " + x.toFixed(1) + " " + (laneY + 7) + " L " + (x - 7).toFixed(1) + " " + laneY + " Z", "class": "tl-dia" }, g);
      bindTip(g, "<strong>" + esc(r.title) + "</strong><br>Distributor " + esc(r.type || "") + " · " + esc(r.date), x, laneY);
    });

    /* vault points */
    var vzLabel = el("text", { x: ML + 8, y: vz0 + 20, "class": "tl-lane-label" }, svg);
    vzLabel.textContent = "VAULT · " + vault.length + " tracks";
    vault.forEach(function (r) {
      var x = X(r.date), y = Y(r.plays);
      var p = Math.log10((r.plays || 0) + 1) / maxLog;
      var rad = 3 + p * 5;
      var g = el("g", {
        "class": "tl-pt", tabindex: "0", role: "img",
        "aria-label": r.title + ", uploaded " + r.date + ", " + fmt(r.plays || 0) + " plays"
      }, svg);
      el("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: rad.toFixed(1), "class": "tl-dot" }, g);
      bindTip(g, "<strong>" + esc(r.title) + "</strong><br>" + esc(r.date) + " · " + fmt(r.plays || 0) + " plays", x, y);
    });

    /* x axis ticks */
    function tickLabel(t, x) {
      var tx = el("text", { x: x.toFixed(1), y: H - MB + 22, "class": "tl-tick" }, svg);
      tx.textContent = t;
    }
    if (year) {
      var months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
      for (var m = 0; m < 12; m++) {
        var mx = ML + (m / 12) * iw;
        el("line", { x1: mx, y1: H - MB, x2: mx, y2: H - MB + 6, "class": "tl-grid" }, svg);
        tickLabel(months[m], mx + 8);
      }
    } else {
      for (var yy = 2018; yy <= 2026; yy++) {
        var yx = ML + ((Date.UTC(yy, 0, 1) - t0) / (t1 - t0)) * iw;
        el("line", { x1: yx, y1: MT, x2: yx, y2: H - MB, "class": "tl-grid" }, svg);
        tickLabel(String(yy), yx + 6);
      }
    }
    el("line", { x1: ML, y1: H - MB, x2: W - MR, y2: H - MB, "class": "tl-axis" }, svg);

    /* year summary (accessible list) */
    var byYear = {};
    disc.forEach(function (r) {
      if (!r.date || !inRange(r)) return;
      var y = r.date.slice(0, 4);
      byYear[y] = byYear[y] || { n: 0, plays: 0 };
      byYear[y].n++;
      byYear[y].plays += (r.plays || 0);
    });
    summary.innerHTML = Object.keys(byYear).sort().map(function (y) {
      return "<li><span>" + esc(y) + "</span><span>" + byYear[y].n + " transmissions · " + fmt(byYear[y].plays) + " plays</span></li>";
    }).join("");
  }

  function bindTip(g, html, x, y) {
    function px(v, horizontal) {
      /* convert svg units to css px inside the wrap */
      var r = svg.getBoundingClientRect();
      return (v / (horizontal ? W : H)) * (horizontal ? r.width : r.height);
    }
    g.addEventListener("mouseenter", function () { showTip(html, px(x, true), px(y, false)); });
    g.addEventListener("mouseleave", hideTip);
    g.addEventListener("focus", function () { showTip(html, px(x, true), px(y, false)); });
    g.addEventListener("blur", hideTip);
    g.addEventListener("click", function () { showTip(html, px(x, true), px(y, false)); });
    g.addEventListener("keydown", function (e) { if (e.key === "Escape") { hideTip(); g.blur(); } });
  }

  ADM.loadData("data/artist.json").then(function (d) {
    var years = [null, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
    var current = null;
    yearsCtl.innerHTML = "";
    years.forEach(function (y) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "btn btn-sm" + (y === null ? " is-active" : "");
      b.textContent = y === null ? "All years" : String(y);
      b.setAttribute("aria-pressed", y === null ? "true" : "false");
      b.addEventListener("click", function () {
        current = y;
        yearsCtl.querySelectorAll("button").forEach(function (o) {
          o.classList.remove("is-active");
          o.setAttribute("aria-pressed", "false");
        });
        b.classList.add("is-active");
        b.setAttribute("aria-pressed", "true");
        render(d, current);
      });
      yearsCtl.appendChild(b);
    });
    render(d, null);
  }).catch(function () {
    svg.innerHTML = "";
    var t = document.createElementNS(NS, "text");
    t.setAttribute("x", W / 2); t.setAttribute("y", H / 2);
    t.setAttribute("class", "tl-error"); t.setAttribute("text-anchor", "middle");
    t.textContent = "Could not load the archive data.";
    svg.appendChild(t);
  });
})();
