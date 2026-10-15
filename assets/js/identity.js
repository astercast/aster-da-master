/* Aster da Master: site chrome (rotation 20, the catalogue register).
   Injected, JS-only: the status beacon, the current-page nav marker,
   the footer sign-off line + UTC clock, and the reveal gap-close.
   Retired in rotation 20 (presentation only): the boot overlay
   ("TUNING 87.9…": the page now opens directly on the catalogue)
   and the scramble/decode text effects (headlines and nav links
   now sit still and read as printed). Every feature kept here is
   functional: it marks state or tells the time.
   Failure-safe: every feature guards on its DOM hooks: no match,
   no touch, page works. No-JS visitors get the full site, just no
   chrome. Vanilla, no dependencies. */
(function () {
  "use strict";

  /* The finished state is the CSS default; .js only enables enhancement. */
  document.documentElement.classList.add("js");

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- status beacon, injected after the brand: a plain text
     label with a static ink dot (motifs.css carries the register;
     no flicker since rotation 20) ---- */
  function beacon() {
    var brand = document.querySelector(".header-bar .brand");
    if (!brand || document.querySelector(".onair")) return;
    var s = document.createElement("span");
    s.className = "onair";
    s.setAttribute("aria-hidden", "true");
    s.innerHTML = "<i></i>ON AIR";
    brand.insertAdjacentElement("afterend", s);
  }

  /* ---- current-page marker: aria-current on the nav link for this page ---- */
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

  /* ---- footer sign-off line + live UTC clock ---- */
  function signoff() {
    var foot = document.querySelector(".site-footer .container");
    if (!foot || foot.querySelector(".signoff")) return;
    var d = document.createElement("div");
    d.className = "signoff";
    d.innerHTML =
      '<div><p class="signoff-title">ASTER DA MASTER</p>' +
      '<p class="signoff-sub">THE CATALOGUE STAYS OPEN</p></div>' +
      '<div class="signoff-clock"><span id="station-clock">--:--:--</span>' +
      '<span class="signoff-label">UTC</span></div>';
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
  beacon();
  markCurrent();
  signoff();

  /* Pre-existing gap (predates wave 31): pages that load only common.js
     (changelog, sessions) never invoke ADM.reveal(), so .reveal content
     stays at opacity 0 forever. identity.js runs on every page, so it
     closes the gap. Double-running alongside site.js/transmission.js is
     harmless: both just add .in on intersect. */
  if (window.ADM && typeof window.ADM.reveal === "function") {
    try { window.ADM.reveal(); } catch (e) {}
  }
})();

/* The station never sleeps. (If you're reading this: no lyrics in here , 
   just numbers. The keeper's orders.) */
if (window.console && typeof console.log === "function") {
  console.log("The station never sleeps.");
}
