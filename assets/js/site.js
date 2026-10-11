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

  function artTile(r) {
    var initial = esc((r.title || "?").charAt(0));
    var mono = '<div class="disco-art disco-mono" aria-hidden="true"' + (r.artwork ? " hidden" : "") + ">" + initial + "</div>";
    if (!r.artwork) return mono;
    return '<img class="disco-art" src="' + esc(r.artwork) + '" alt="' + esc(r.title) + ' cover art" loading="lazy" ' +
      'onerror="this.hidden=true;this.nextElementSibling.hidden=false;">' + mono;
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

      /* Discography — with provenance lines and a vault filter */
      var grid = document.getElementById("disco-grid");
      var discoMeta = document.getElementById("disco-meta");
      var vaultNote = document.getElementById("vault-note");
      function discoCard(r) {
        var isVault = r.type === "SoundCloud-only";
        var conf = (r.confidence === "single-source")
          ? '<span class="src-tag" title="Single-source record \u2014 verified once, awaiting a second confirmation">single-source</span>'
          : "";
        var srcLine = r.source
          ? '<p class="src" title="Data provenance">' + esc(r.source) + "</p>"
          : "";
        var dateLine = r.date ? esc(r.date) : "date unknown";
        var typeLine = '<span class="type">' + esc(r.type || "Release") + "</span>" + conf;
        return '<article class="disco-card' + (isVault ? " is-vault" : "") + '" data-dtype="' + esc(r.type) + '">' +
          artTile(r) + typeLine +
          "<h3>" + esc(r.title) + "</h3>" +
          '<p class="date">' + dateLine + "</p>" +
          '<div class="links">' + linkList(r.links) + "</div>" +
          srcLine +
          "</article>";
      }
      function discoFilterFn(filter) {
        return function (r) {
          if (filter === "all") return true;
          if (filter === "vault") return r.type === "SoundCloud-only";
          return r.type === filter;
        };
      }
      function renderDisco(filter) {
        var items = (d.discography || []).filter(discoFilterFn(filter));
        grid.innerHTML = items.map(discoCard).join("");
        var nAll = (d.discography || []).length;
        var nVault = (d.discography || []).filter(function (r) { return r.type === "SoundCloud-only"; }).length;
        var nDist = nAll - nVault;
        if (discoMeta) {
          discoMeta.textContent = nAll + " transmissions on record: " + nDist +
            " distributor releases + " + nVault + " from the SoundCloud vault.";
        }
        if (vaultNote) {
          vaultNote.hidden = filter !== "vault";
        }
      }
      if (grid && Array.isArray(d.discography)) {
        renderDisco("all");
        document.querySelectorAll("[data-disco-filter]").forEach(function (btn) {
          btn.addEventListener("click", function () {
            document.querySelectorAll("[data-disco-filter]").forEach(function (b) {
              var on = b === btn;
              b.classList.toggle("is-on", on);
              b.setAttribute("aria-pressed", on ? "true" : "false");
            });
            renderDisco(btn.getAttribute("data-disco-filter"));
          });
        });
        if (vaultNote && d.vault && d.vault.status) {
          vaultNote.querySelector("p").textContent = d.vault.status;
        }
      }

      /* Eras */
      var erasEl = document.getElementById("eras-list");
      if (erasEl && Array.isArray(d.eras) && d.eras.length) {
        erasEl.innerHTML = d.eras.map(function (e) {
          var rels = (e.releases || []).map(function (t) {
            return "<li>" + esc(t) + "</li>";
          }).join("");
          var body = rels
            ? '<ul class="era-releases">' + rels + "</ul>"
            : '<p class="era-silence">No releases on record.</p>';
          return '<article class="era-card">' +
            '<p class="era-span">' + esc(e.span) + "</p>" +
            "<h3>" + esc(e.name) + "</h3>" +
            '<p class="era-scene">' + esc(e.scene) + "</p>" +
            body +
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
