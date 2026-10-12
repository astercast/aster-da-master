/* Aster da Master — THE PIRATE BROADCAST identity chrome (wave 31).
   Injected, JS-only: boot sequence, ON AIR beacon, scramble/decode
   reveals, nav tuner marker, station sign-off + clock.
   Failure-safe: every feature guards on its DOM hooks — no match, no
   touch, page works. No-JS visitors get the full site, just no chrome.
   All motion gated on prefers-reduced-motion. Vanilla, no dependencies. */
(function () {
  "use strict";

  /* The finished state is the CSS default; .js only enables enhancement. */
  document.documentElement.classList.add("js");

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var GLYPHS = "\u2588\u2593\u2592\u2591<>/\\|[]#+*01";

  /* ---- boot sequence: 3 typed lines, ~1.2s, once per session, skippable ---- */
  function boot() {
    if (reduced) return false;
    try {
      if (window.sessionStorage.getItem("adm-boot") === "1") return false;
    } catch (e) { return false; }
    var lines = ["TUNING 87.9 \u2026", "SIGNAL FOUND", "DECRYPTING ARCHIVE"];
    var ov = document.createElement("div");
    ov.className = "boot";
    ov.setAttribute("aria-hidden", "true");
    ov.innerHTML =
      '<div class="boot-box">' +
      '<p class="boot-freq">ASTER DA MASTER // PIRATE SIGNAL</p>' +
      '<div class="boot-lines"></div>' +
      '<p class="boot-skip">CLICK OR ANY KEY TO SKIP</p>' +
      "</div>";
    var box = ov.querySelector(".boot-lines");
    var done = false;
    function finish() {
      if (done) return;
      done = true;
      document.removeEventListener("keydown", onKey);
      try { window.sessionStorage.setItem("adm-boot", "1"); } catch (e) {}
      ov.classList.add("done");
      window.setTimeout(function () { if (ov.parentNode) ov.parentNode.removeChild(ov); }, 360);
    }
    function onKey() { finish(); }
    ov.addEventListener("click", finish);
    document.addEventListener("keydown", onKey);
    if (!document.body) return false;
    document.body.appendChild(ov);
    var li = 0;
    function typeLine() {
      if (done) return;
      if (li >= lines.length) { window.setTimeout(finish, 240); return; }
      var p = document.createElement("p");
      p.className = "boot-line";
      var caret = document.createElement("span");
      caret.className = "boot-caret";
      var stale = box.querySelector(".boot-caret");
      if (stale && stale.parentNode) stale.parentNode.removeChild(stale);
      box.appendChild(p);
      var text = lines[li++];
      var ci = 0;
      (function tick() {
        if (done) return;
        p.textContent = text.slice(0, ++ci);
        p.appendChild(caret);
        if (ci < text.length) window.setTimeout(tick, 22);
        else window.setTimeout(typeLine, 110);
      })();
    }
    typeLine();
    window.setTimeout(finish, 4000); /* hard cap: never trap the page */
    return true;
  }

  /* ---- scramble/decode: text-node walker, restores originals ---- */
  function scrambleText(el, dur) {
    if (reduced || !window.requestAnimationFrame) return;
    var nodes = [];
    (function walk(n) {
      for (var c = n.firstChild; c; c = c.nextSibling) {
        if (c.nodeType === 3) nodes.push(c);
        else if (c.nodeType === 1) walk(c);
      }
    })(el);
    if (!nodes.length) return;
    var orig = nodes.map(function (n) { return n.nodeValue; });
    if (!orig.join("").replace(/\s/g, "")) return;
    var start = window.performance.now();
    el.classList.add("decoding");
    function frame(now) {
      var t = Math.min(1, (now - start) / dur);
      for (var i = 0; i < nodes.length; i++) {
        var o = orig[i], out = "";
        for (var k = 0; k < o.length; k++) {
          var ch = o[k];
          out += (/\s/.test(ch) || Math.random() < t)
            ? ch
            : GLYPHS[(Math.random() * GLYPHS.length) | 0];
        }
        nodes[i].nodeValue = out;
      }
      if (t < 1) window.requestAnimationFrame(frame);
      else {
        for (var j = 0; j < nodes.length; j++) nodes[j].nodeValue = orig[j];
        el.classList.remove("decoding");
      }
    }
    window.requestAnimationFrame(frame);
  }

  /* ---- ON AIR beacon, injected after the brand ---- */
  function beacon() {
    var brand = document.querySelector(".header-bar .brand");
    if (!brand || document.querySelector(".onair")) return;
    var s = document.createElement("span");
    s.className = "onair";
    s.setAttribute("aria-hidden", "true");
    s.innerHTML = "<i></i>ON AIR";
    brand.insertAdjacentElement("afterend", s);
  }

  /* ---- tuner marker: aria-current on the nav link for this page ---- */
  function markCurrent() {
    var path = window.location.pathname.replace(/\/index\.html$/, "/");
    var links = document.querySelectorAll(".site-nav a, .mnav-panel a");
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      var href = a.getAttribute("href");
      if (!href || href.charAt(0) === "#" || /^[a-z][a-z0-9+.-]*:/i.test(href)) continue;
      var url;
      try { url = new URL(href, window.location.href).pathname.replace(/\/index\.html$/, "/"); }
      catch (e) { continue; }
      if (url === path) a.setAttribute("aria-current", "page");
    }
  }

  /* ---- station sign-off footer card + live UTC clock ---- */
  function signoff() {
    var foot = document.querySelector(".site-footer .container");
    if (!foot || foot.querySelector(".signoff")) return;
    var d = document.createElement("div");
    d.className = "signoff";
    d.innerHTML =
      '<div><p class="signoff-title">TRANSMISSION ENDS</p>' +
      '<p class="signoff-sub">THE STATION NEVER SLEEPS \u2014 ARCHIVE OPEN 24/7</p></div>' +
      '<div class="signoff-clock"><span id="station-clock">--:--:--</span>' +
      '<span class="signoff-label">STATION TIME \u00b7 UTC</span></div>';
    foot.appendChild(d);
    var clock = d.querySelector("#station-clock");
    function pad(n) { return ("0" + n).slice(-2); }
    function tick() {
      var t = new Date();
      clock.textContent = pad(t.getUTCHours()) + ":" + pad(t.getUTCMinutes()) + ":" + pad(t.getUTCSeconds());
    }
    tick();
    if (!reduced) window.setInterval(tick, 1000);
  }

  /* ---- run ---- */
  var booted = boot();
  beacon();
  markCurrent();
  signoff();

  /* Pre-existing gap (predates wave 31): pages that load only common.js
     (changelog, sessions) never invoke ADM.reveal(), so .reveal content
     stays at opacity 0 forever. identity.js runs on every page, so it
     closes the gap. Double-running alongside site.js/transmission.js is
     harmless — both just add .in on intersect. */
  if (window.ADM && typeof window.ADM.reveal === "function") {
    try { window.ADM.reveal(); } catch (e) {}
  }

  /* Headline decode: the call-sign tunes in. Body copy stays static. */
  var h1 = document.querySelector("main h1");
  if (h1 && !reduced) {
    window.setTimeout(function () { scrambleText(h1, 650); }, booted ? 1450 : 350);
  }

  /* Nav hover scramble: quick static burst on the link. */
  var navLinks = document.querySelectorAll(".site-nav a, .mnav-panel a");
  for (var n = 0; n < navLinks.length; n++) {
    (function (a) {
      var busy = false;
      a.addEventListener("mouseenter", function () {
        if (reduced || busy) return;
        busy = true;
        scrambleText(a, 240);
        window.setTimeout(function () { busy = false; }, 320);
      });
    })(navLinks[n]);
  }
})();

/* The station never sleeps. (If you're reading this: no lyrics in here —
   just numbers. The keeper's orders.) */
if (window.console && typeof console.log === "function") {
  console.log("%cThe station never sleeps.", "color:#00f090");
}
