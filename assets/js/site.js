/* Aster da Master site — renders discography/platforms/socials from data/artist.json; reveal on scroll. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Reveal on scroll */
  if ("IntersectionObserver" in window) {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); obs.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll(".reveal").forEach(function (el) { obs.observe(el); });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("in"); });
  }

  function linkList(links) {
    return (links || []).map(function (l) {
      return '<a href="' + esc(l.url) + '" target="_blank" rel="noopener">' + esc(l.label) + "</a>";
    }).join("");
  }

  fetch("data/artist.json")
    .then(function (r) { if (!r.ok) throw new Error("data failed"); return r.json(); })
    .then(function (d) {
      if (d.research_status && d.research_status.indexOf("PENDING") === 0) return; /* don't render placeholders */
      var a = d.artist || {};

      /* Featured release */
      var f = d.featured_release;
      var feat = document.getElementById("feature");
      if (f && feat) {
        feat.innerHTML =
          '<div class="feature-art" aria-hidden="true">' + esc((f.title || "?").charAt(0)) + "</div>" +
          "<div>" +
          '<p class="feature-meta">Latest transmission · ' + esc(f.date || "") + "</p>" +
          "<h3>" + esc(f.title || "") + "</h3>" +
          "<p>" + esc(f.blurb || "") + "</p>" +
          '<div class="btn-row">' + linkList(f.links).replace(/<a /g, '<a class="btn btn-sm" ') + "</div>" +
          "</div>";
      }

      /* Discography */
      var grid = document.getElementById("disco-grid");
      if (grid && Array.isArray(d.discography)) {
        grid.innerHTML = d.discography.map(function (r) {
          return '<article class="disco-card">' +
            '<span class="type">' + esc(r.type || "Release") + "</span>" +
            "<h3>" + esc(r.title) + "</h3>" +
            '<p class="date">' + esc(r.date || "") + "</p>" +
            '<div class="links">' + linkList(r.links) + "</div>" +
            "</article>";
        }).join("");
      }

      /* Platforms */
      var plats = document.getElementById("platform-grid");
      if (plats && Array.isArray(d.platforms)) {
        plats.innerHTML = d.platforms.map(function (p) {
          var label = esc(p.name);
          var note = "";
          if (p.verified === false) {
            note = '<br><small class="plat-note">' + esc(p.note || "unverified") + "</small>";
          }
          return '<a class="platform" href="' + esc(p.url) + '" target="_blank" rel="noopener">' +
            "<span>" + label + note + '</span><span class="arrow" aria-hidden="true">→</span></a>';
        }).join("");
      }

      /* Circle (collaborators) */
      var circ = document.getElementById("circle-grid");
      if (circ && Array.isArray(d.collaborators)) {
        circ.innerHTML = d.collaborators.map(function (c) {
          var flag = c.confidence === "single-source"
            ? '<span class="src-tag" title="Single-source credit — verified once, awaiting a second confirmation">single-source</span>'
            : "";
          return '<article class="circle-card">' +
            "<h3>" + esc(c.name) + flag + "</h3>" +
            '<p class="role">' + esc(c.role || "On record") + "</p>" +
            "</article>";
        }).join("");
      }

      /* About */
      var bio = document.getElementById("bio");
      if (bio && a.bio && a.bio.indexOf("TBD") !== 0) {
        bio.innerHTML = a.bio_paragraphs.map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
      }
      var facts = document.getElementById("fact-list");
      if (facts && Array.isArray(a.facts) && a.facts.length) {
        facts.innerHTML = a.facts.map(function (f2) {
          return '<li><span class="k">' + esc(f2.k) + "</span><span>" + esc(f2.v) + "</span></li>";
        }).join("");
      }

      /* Socials */
      var soc = document.getElementById("connect-grid");
      if (soc && Array.isArray(d.socials)) {
        soc.innerHTML = d.socials.map(function (s2) {
          return '<a class="platform" href="' + esc(s2.url) + '" target="_blank" rel="noopener">' +
            "<span>" + esc(s2.name) + '</span><span class="arrow" aria-hidden="true">→</span></a>';
        }).join("");
      }

      var book = document.getElementById("booking");
      if (book && d.booking && d.booking.email) {
        book.innerHTML = '<p class="chart-sub">Booking &amp; contact</p><a class="btn btn-neon" href="mailto:' +
          esc(d.booking.email) + '">' + esc(d.booking.email) + "</a>";
      }
    })
    .catch(function () { /* sections keep their static fallback content */ });
})();
