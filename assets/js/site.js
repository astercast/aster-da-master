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
        var playsLine = (isVault && r.plays != null)
          ? '<p class="plays">' + Number(r.plays).toLocaleString("en-US") +
            ' plays <span class="chart-sub">(snapshot 2026-10-11)</span></p>'
          : "";
        var typeLine = '<span class="type">' + esc(r.type || "Release") + "</span>" + conf;
        return '<article class="disco-card' + (isVault ? " is-vault" : "") + '" data-dtype="' + esc(r.type) + '">' +
          artTile(r) + typeLine +
          "<h3>" + esc(r.title) + "</h3>" +
          '<p class="date">' + dateLine + "</p>" + playsLine +
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

      /* On the horizon (teased, unconfirmed) */
      var horizon = document.getElementById("horizon");
      var horizonList = document.getElementById("horizon-list");
      if (horizon && horizonList && Array.isArray(d.upcoming) && d.upcoming.length) {
        horizon.hidden = false;
        horizonList.innerHTML = d.upcoming.map(function (u) {
          return "<li><strong>" + esc(u.title) + "</strong> &mdash; " + esc(u.status) + "</li>";
        }).join("");
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

      /* Numbers — stats dashboard, computed live from the verified archive */
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
      var statCards = document.getElementById("stat-cards");
      if (statCards && Array.isArray(d.discography)) {
        var disc = d.discography;
        var vault = disc.filter(function (r) { return r.type === "SoundCloud-only"; });
        var dist = disc.filter(function (r) { return r.type !== "SoundCloud-only"; });
        var totalPlays = vault.reduce(function (s, r) { return s + (r.plays || 0); }, 0);
        var years = {};
        disc.forEach(function (r) {
          if (!r.date) return;
          var y = r.date.slice(0, 4);
          years[y] = years[y] || { vault: 0, dist: 0, plays: 0 };
          if (r.type === "SoundCloud-only") { years[y].vault++; years[y].plays += (r.plays || 0); }
          else { years[y].dist++; }
        });
        var yearKeys = Object.keys(years).sort();
        var topTracks = vault.slice().sort(function (a, b) { return (b.plays || 0) - (a.plays || 0); }).slice(0, 10);
        var collabCount = {};
        var collabDisplay = {};
        disc.forEach(function (r) {
          parseCollabs(r.title).forEach(function (n) {
            var k = n.toLowerCase();
            collabCount[k] = (collabCount[k] || 0) + 1;
            if (!collabDisplay[k] || n.length >= collabDisplay[k].length) collabDisplay[k] = n;
          });
        });
        var topCollabs = Object.keys(collabCount).sort(function (a, b) { return collabCount[b] - collabCount[a]; }).slice(0, 10);
        var fmt = function (n) { return Number(n).toLocaleString("en-US"); };

        statCards.innerHTML = [
          { v: fmt(totalPlays), l: "SoundCloud plays", s: "across " + vault.length + " vault tracks · snapshot 2026-10-11" },
          { v: fmt(disc.length), l: "Transmissions on record", s: dist.length + " distributor + " + vault.length + " vault" },
          { v: yearKeys.length, l: "Years of output", s: yearKeys[0] + " – " + yearKeys[yearKeys.length - 1] },
          { v: esc(topTracks[0] ? topTracks[0].title : "—"), l: "Most played transmission", s: topTracks[0] ? fmt(topTracks[0].plays) + " plays" : "" }
        ].map(function (c) {
          return '<article class="stat-card"><p class="stat-num">' + c.v + '</p>' +
            '<p class="stat-label">' + esc(c.l) + '</p><p class="chart-sub">' + esc(c.s) + "</p></article>";
        }).join("");

        var playsBars = document.getElementById("plays-bars");
        if (playsBars) {
          var maxP = Math.max.apply(null, yearKeys.map(function (y) { return years[y].plays; }).concat([1]));
          playsBars.innerHTML = yearKeys.map(function (y) {
            var w = Math.round((years[y].plays / maxP) * 100);
            return '<div class="bar-row"><span class="bar-y">' + esc(y) + '</span>' +
              '<span class="bar-track"><span class="bar-fill" style="width:' + w + '%"></span></span>' +
              '<span class="bar-v">' + fmt(years[y].plays) + "</span></div>";
          }).join("");
        }
        var tracksBars = document.getElementById("tracks-bars");
        if (tracksBars) {
          var maxT = Math.max.apply(null, yearKeys.map(function (y) { return years[y].vault + years[y].dist; }).concat([1]));
          tracksBars.innerHTML = yearKeys.map(function (y) {
            var wv = Math.round((years[y].vault / maxT) * 100);
            var wd = Math.round((years[y].dist / maxT) * 100);
            return '<div class="bar-row"><span class="bar-y">' + esc(y) + '</span>' +
              '<span class="bar-track"><span class="bar-fill is-dist" style="width:' + wd + '%"></span>' +
              '<span class="bar-fill" style="width:' + wv + '%"></span></span>' +
              '<span class="bar-v">' + (years[y].vault + years[y].dist) + "</span></div>";
          }).join("") +
            '<p class="chart-sub"><span class="legend-sw is-dist"></span>distributor <span class="legend-sw"></span>vault</p>';
        }
        var topEl = document.getElementById("top-tracks");
        if (topEl) {
          topEl.innerHTML = topTracks.map(function (r) {
            return "<li><span>" + esc(r.title) + "</span><span class=\"top-n\">" + fmt(r.plays) + "</span></li>";
          }).join("");
        }
        var colEl = document.getElementById("top-collabs");
        if (colEl) {
          colEl.innerHTML = topCollabs.map(function (k) {
            return "<li><span>" + esc(collabDisplay[k]) + "</span><span class=\"top-n\">×" + collabCount[k] + "</span></li>";
          }).join("");
        }
      }

      /* Codex — vocabulary families, computed at build time into data/codex.json */
      var codexGrid = document.getElementById("codex-grid");
      if (codexGrid) {
        fetch("data/codex.json")
          .then(function (r) { if (!r.ok) throw new Error("codex failed"); return r.json(); })
          .then(function (c) {
            codexGrid.innerHTML = (c.families || []).map(function (f) {
              var tracks = (f.tracks || []).map(function (t) {
                var meta = [t.date || "date unknown", t.type].join(" · ");
                var plays = (t.plays != null) ? ' <span class="top-n">' + Number(t.plays).toLocaleString("en-US") + "</span>" : "";
                return "<li><span>" + esc(t.title) + '<br><small class="chart-sub">' + esc(meta) + "</small></span>" + plays + "</li>";
              }).join("");
              return '<article class="codex-card"><p class="codex-count">' + f.track_count + '</p>' +
                "<h3>" + esc(f.name) + "</h3>" +
                '<p class="codex-epithet">' + esc(f.epithet) + "</p>" +
                '<p class="codex-words">' + f.words.map(esc).join(" · ") + "</p>" +
                '<ol class="top-list codex-tracks">' + tracks + "</ol></article>";
            }).join("");
          })
          .catch(function () { /* codex keeps its static fallback */ });
      }

      /* Platforms */
      var plats = document.getElementById("platform-grid");
      if (plats && Array.isArray(d.platforms)) {
        plats.innerHTML = d.platforms.map(function (p) {
          var label = esc(p.name);
          var note = "";
          if (p.verified === false || !p.url) {
            note = '<br><small class="plat-note">' + esc(p.note || "unverified") + "</small>";
          }
          var inner = "<span>" + label + note + "</span>" +
            (p.url ? '<span class="arrow" aria-hidden="true">→</span>' : "");
          return p.url
            ? '<a class="platform" href="' + esc(p.url) + '" target="_blank" rel="noopener">' + inner + "</a>"
            : '<span class="platform is-static" title="' + esc(p.note || "") + '">' + inner + "</span>";
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
