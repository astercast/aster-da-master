/* Aster da Master site — renders discography/platforms/socials from data/artist.json; reveal on scroll. */
(function () {
  "use strict";

  /* Web-craft failure-mode rule (see common.js): hidden pre-reveal state
     only applies when JS runs. */
  document.documentElement.classList.add("js");

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
      /* Slugify — identical to scripts/build_releases.py. Deep links to
         generated circle/ and codex/ pages. Prefers the shared helper. */
      var slugify = (window.ADM && window.ADM.slugify) || function (s) {
        return String(s == null ? "" : s).toLowerCase().replace(/&/g, " and ")
          .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "page";
      };
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
        }).join("") + "<li><a href=\"trilogy.html\">Open the trilogy watch &rarr;</a></li>";
      }

      /* Eras — cards plus data-computed "era intelligence" deep-dives */
      function spanYears(span) {
        var m = /(\d{4})(?:\s*[–—-]\s*(\d{4}))?/.exec(String(span || ""));
        if (!m) return null;
        return { start: parseInt(m[1], 10), end: parseInt(m[2] || m[1], 10) };
      }
      var erasEl = document.getElementById("eras-list");
      if (erasEl && Array.isArray(d.eras) && d.eras.length) {
        var discAll = Array.isArray(d.discography) ? d.discography : [];
        erasEl.innerHTML = d.eras.map(function (e) {
          var rels = (e.releases || []).map(function (t) {
            return "<li>" + esc(t) + "</li>";
          }).join("");
          var body = rels
            ? '<ul class="era-releases">' + rels + "</ul>"
            : '<p class="era-silence">No releases on record.</p>';

          /* Era intelligence — computed from the archive, not written by hand */
          var deep = "";
          var yr = spanYears(e.span);
          if (yr) {
            var inEra = discAll.filter(function (r) {
              var y = parseInt((r.date || "").slice(0, 4), 10);
              return y >= yr.start && y <= yr.end;
            });
            var eraPlays = inEra.reduce(function (s, r) { return s + (r.plays || 0); }, 0);
            var eraTop = inEra
              .filter(function (r) { return (r.plays || 0) > 0; })
              .sort(function (a, b) { return (b.plays || 0) - (a.plays || 0); })
              .slice(0, 5);
            var eraCollabs = {};
            var eraDisplay = {};
            inEra.forEach(function (r) {
              parseCollabs(r.title).forEach(function (n) {
                var k = n.toLowerCase();
                eraCollabs[k] = (eraCollabs[k] || 0) + 1;
                if (!eraDisplay[k] || n.length >= eraDisplay[k].length) eraDisplay[k] = n;
              });
            });
            var eraKeys = Object.keys(eraCollabs).sort(function (a, b) { return eraCollabs[b] - eraCollabs[a]; }).slice(0, 5);
            var topHtml = eraTop.length
              ? '<ol class="top-list">' + eraTop.map(function (r) {
                  return "<li><span>" + esc(r.title) + "</span>" +
                    '<span class="top-n">' + Number(r.plays).toLocaleString("en-US") + "</span></li>";
                }).join("") + "</ol>"
              : '<p class="chart-sub">No play-counted tracks in this span.</p>';
            var colHtml = eraKeys.length
              ? '<ul class="era-collabs">' + eraKeys.map(function (k) {
                  return "<li>" + esc(eraDisplay[k]) + ' <span class="top-n">&times;' + eraCollabs[k] + "</span></li>";
                }).join("") + "</ul>"
              : '<p class="chart-sub">Solo transmissions — no credited collaborators in this span.</p>';
            deep = '<details class="era-deep"><summary>Era intelligence &mdash; ' +
              inEra.length + " transmissions &middot; " +
              Number(eraPlays).toLocaleString("en-US") + " plays</summary>" +
              '<div class="era-deep-body">' +
              '<p class="chart-sub">Counted from the archive for ' + yr.start + "&ndash;" + yr.end +
              ". Play counts: SoundCloud vault only, snapshot 2026-10-11.</p>" +
              "<h4>Most played of the era</h4>" + topHtml +
              "<h4>Key collaborators</h4>" + colHtml +
              "</div></details>";
          }

          return '<article class="era-card">' +
            '<p class="era-span">' + esc(e.span) + "</p>" +
            "<h3>" + esc(e.name) + "</h3>" +
            '<p class="era-scene">' + esc(e.scene) + "</p>" +
            body + deep +
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
        /* Play velocity: plays per day since upload, from the 2026-10-11 snapshot.
           Favors recent uploads by construction — that IS the story (depth vs heat). */
        var SNAP = Date.UTC(2026, 9, 11);
        var velocity = vault
          .filter(function (r) { return r.date && /^\d{4}-\d{2}-\d{2}$/.test(r.date) && (r.plays || 0) > 0; })
          .map(function (r) {
            var days = Math.max(1, Math.round((SNAP - Date.parse(r.date + "T00:00:00Z")) / 86400000));
            return { title: r.title, plays: r.plays, date: r.date, v: r.plays / days };
          })
          .sort(function (a, b) { return b.v - a.v; })
          .slice(0, 15);

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
            return "<li><span><a href=\"circle/" + slugify(collabDisplay[k]) + ".html\">" +
              esc(collabDisplay[k]) + "</a></span><span class=\"top-n\">×" + collabCount[k] + "</span></li>";
          }).join("");
        }
        var velEl = document.getElementById("top-velocity");
        if (velEl) {
          velEl.innerHTML = velocity.map(function (r) {
            var rate = r.v >= 10 ? r.v.toFixed(1) : r.v.toFixed(2);
            return "<li><span>" + esc(r.title) + '<br><small class="chart-sub">' + esc(r.date) +
              " · " + fmt(r.plays) + " plays</small></span><span class=\"top-n\">" + rate + "/day</span></li>";
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
                '<h3><a href="codex/' + slugify(f.name) + '.html">' + esc(f.name) + "</a></h3>" +
                '<p class="codex-epithet">' + esc(f.epithet) + "</p>" +
                '<p class="codex-words">' + f.words.map(esc).join(" · ") + "</p>" +
                '<ol class="top-list codex-tracks">' + tracks + "</ol></article>";
            }).join("");
          })
          .catch(function () { /* codex keeps its static fallback */ });
      }

      /* Deep cuts — the buried transmissions: 15 lowest-play vault tracks
         with plays > 0, uploaded before 2025 (years to breathe). Pure data query. */
      var cutsGrid = document.getElementById("deepcuts-grid");
      if (cutsGrid && Array.isArray(d.discography)) {
        var cuts = d.discography
          .filter(function (r) { return r.type === "SoundCloud-only" && r.date && r.date < "2025-01-01" && (r.plays || 0) > 0; })
          .sort(function (a, b) { return (a.plays || 0) - (b.plays || 0); })
          .slice(0, 15);
        cutsGrid.innerHTML = cuts.map(function (r, i) {
          var plays = Number(r.plays || 0).toLocaleString("en-US");
          return '<li class="cut-card"><span class="cut-rank" aria-hidden="true">' + (i + 1) + "</span>" +
            '<div><h3>' + esc(r.title) + "</h3>" +
            '<p class="cut-meta">' + esc(r.date) + " · " + plays + " plays</p></div></li>";
        }).join("");
        var cutsNote = document.getElementById("deepcuts-note");
        if (cutsNote) cutsNote.hidden = false;
      }

      /* On this day — transmissions that landed on today's month/day,
         across all years. Powered by api/v1/on-this-day.json. */
      var otdList = document.getElementById("onthisday-list");
      var otdSub = document.getElementById("onthisday-sub");
      if (otdList) {
        var now = new Date();
        var mmdd = ("0" + (now.getMonth() + 1)).slice(-2) + "-" + ("0" + now.getDate()).slice(-2);
        var pretty = now.toLocaleDateString("en-US", { month: "long", day: "numeric" });
        if (otdSub) otdSub.textContent = "Transmissions that landed on " + pretty + " — across all nine years.";
        fetch("api/v1/on-this-day.json")
          .then(function (r) { if (!r.ok) throw new Error("on-this-day failed"); return r.json(); })
          .then(function (otd) {
            var todays = otd[mmdd] || [];
            if (!todays.length) {
              otdList.innerHTML = '<li class="otd-empty"><p>No transmissions landed on ' + esc(pretty) +
                " &mdash; the silence keeps its own counsel.</p></li>";
              return;
            }
            otdList.innerHTML = todays.map(function (t) {
              var year = (t.date || "").slice(0, 4);
              var plays = (t.plays != null)
                ? ' <span class="top-n">' + Number(t.plays).toLocaleString("en-US") + " plays</span>"
                : "";
              var meta = [year, t.type].filter(Boolean).join(" · ");
              return '<li class="otd-card"><a href="' + esc(t.page) + '"><h3>' + esc(t.title) + "</h3></a>" +
                '<p class="cut-meta">' + esc(meta) + "</p>" + plays + "</li>";
            }).join("");
          })
          .catch(function () {
            otdList.innerHTML = '<li class="otd-empty"><p>The calendar could not be read today.</p></li>';
          });
      }

      /* Cast lots — summon one random vault transmission, drawn blind */
      var summonBtn = document.getElementById("summon-btn");
      var lotsResult = document.getElementById("lots-result");
      if (summonBtn && lotsResult && Array.isArray(d.discography)) {
        var lotsPool = d.discography.filter(function (r) { return r.type === "SoundCloud-only"; });
        summonBtn.addEventListener("click", function () {
          if (!lotsPool.length) return;
          var r = lotsPool[Math.floor(Math.random() * lotsPool.length)];
          var plays = (r.plays != null) ? Number(r.plays).toLocaleString("en-US") + " plays" : "plays uncounted";
          lotsResult.innerHTML =
            '<article class="lots-card" aria-label="Summoned transmission">' +
            '<p class="kicker"><span class="numeral">&#10022;</span>The lots have spoken</p>' +
            "<h3>" + esc(r.title) + "</h3>" +
            '<p class="cut-meta">Uploaded ' + esc(r.date || "date unknown") + " · " + esc(plays) +
            " <span class=\"chart-sub\">(snapshot 2026-10-11)</span></p>" +
            '<div class="btn-row"><a class="btn btn-neon" href="https://soundcloud.com/asterdamaster" target="_blank" rel="noopener">Hear it on SoundCloud</a>' +
            '<button class="btn" id="summon-again" type="button">Summon another</button></div>' +
            "</article>";
          var again = document.getElementById("summon-again");
          if (again) again.addEventListener("click", function () { summonBtn.click(); });
        });
      }

      /* Milestones — the career told in firsts, computed at build time */
      var msList = document.getElementById("milestones-list");
      if (msList) {
        fetch("data/milestones.json")
          .then(function (r) { if (!r.ok) throw new Error("milestones failed"); return r.json(); })
          .then(function (m) {
            var fmt = function (n) { return Number(n).toLocaleString("en-US"); };
            msList.innerHTML = (m.milestones || []).map(function (ms) {
              var detail = "";
              if (ms.title) {
                var plays = (ms.plays != null) ? " · " + fmt(ms.plays) + " plays" : "";
                var cum = (ms.cumulative_plays != null) ? " · cumulative " + fmt(ms.cumulative_plays) : "";
                detail = "<p class=\"ms-track\">&#10022; " + esc(ms.title) + "</p>" +
                  '<p class=\"chart-sub\">' + esc(ms.date || "date unknown") + " · " + esc(ms.type || "") + esc(plays) + esc(cum) + "</p>";
              } else if (ms.id === "prolific-day") {
                detail = "<p class=\"ms-track\">&#10022; " + esc(ms.date) + " — " + ms.count + " uploads</p>";
              } else if (ms.id === "longest-silence") {
                detail = "<p class=\"ms-track\">&#10022; " + esc(ms.from) + " &rarr; " + esc(ms.to) + " — " + ms.days + " days</p>";
              }
              return '<li class="ms-card"><h3>' + esc(ms.name) + "</h3>" +
                '<p class="ms-fact">' + esc(ms.fact) + "</p>" + detail + "</li>";
            }).join("");
          })
          .catch(function () { /* section keeps its static fallback */ });
      }

      /* Milestone watch — tracks near round-number play counts */
      var watchBands = document.getElementById("watch-bands");
      var watchSummit = document.getElementById("watch-summit");
      if (watchBands) {
        fetch("data/milestone-watch.json")
          .then(function (r) { if (!r.ok) throw new Error("watch failed"); return r.json(); })
          .then(function (m) {
            var fmt = function (n) { return Number(n).toLocaleString("en-US"); };
            if (watchSummit && m.summit) {
              watchSummit.innerHTML =
                '<article class="ms-card reveal"><h3>The summit</h3>' +
                '<p class="ms-track">&#10022; <a href="' + esc(m.summit.page) + '">' + esc(m.summit.title) + "</a></p>" +
                '<p class="chart-sub">' + fmt(m.summit.plays) + " plays · " + esc(m.summit.date || "date unknown") + "</p>" +
                '<p class="ms-fact">' + esc(m.summit.note || "") + "</p></article>";
            }
            watchBands.innerHTML = (m.bands || []).map(function (b) {
              var rows = (b.tracks || []).map(function (t) {
                return '<li><a href="' + esc(t.page) + '">' + esc(t.title) + "</a>" +
                  ' <span class="dim">' + fmt(t.plays) + " plays · " + fmt(t.needed) +
                  " to " + fmt(b.target) + (t.date ? " · " + esc(t.date) : "") + "</span></li>";
              }).join("");
              var body = rows
                ? '<ol class="year-list">' + rows + "</ol>"
                : '<p class="chart-sub">Nothing in range — the summit stands alone.</p>';
              return '<section class="watch-band reveal" aria-label="' + esc(b.name) + '">' +
                "<h3>" + esc(b.name) + "</h3>" +
                '<p class="chart-sub">' + esc(b.blurb || "") + "</p>" + body + "</section>";
            }).join("");
          })
          .catch(function () { /* section keeps its static fallback */ });
      }

      /* First & last — the year opened with X and closed with Y */
      var flGrid = document.getElementById("firstlast-grid");
      if (flGrid) {
        fetch("data/first-last.json")
          .then(function (r) { if (!r.ok) throw new Error("first-last failed"); return r.json(); })
          .then(function (m) {
            var bookend = function (e, label) {
              return '<div class="fl-bookend"><p class="kicker">' + label + "</p>" +
                '<p class="fl-title"><a href="' + esc(e.page) + '">' + esc(e.title) + "</a></p>" +
                '<p class="chart-sub">' + esc(e.date) +
                (e.type ? " · " + esc(e.type) : "") + "</p></div>";
            };
            flGrid.innerHTML = (m.years || []).map(function (y) {
              return '<li class="fl-card"><h3>' + y.year + "</h3>" +
                bookend(y.opened_with, "Opened with") +
                bookend(y.closed_with, "Closed with") + "</li>";
            }).join("");
          })
          .catch(function () { /* section keeps its static fallback */ });
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

      /* Transmission wire — latest 8, duplicated for the seamless loop */
      var wire = document.getElementById("wire-track");
      if (wire && Array.isArray(d.discography)) {
        var latest = d.discography.slice().sort(function (x, y) {
          return String(y.date || "") < String(x.date || "") ? -1 : 1;
        }).slice(0, 8);
        var items = latest.map(function (r) {
          return '<span class="w-item"><b>' + esc(r.title || "") + "</b> · " + esc(r.date || "") + "</span>";
        }).join('<span class="w-sep">///</span>');
        wire.innerHTML = items + '<span class="w-sep">///</span>' + items + '<span class="w-sep">///</span>';
      }

      var book = document.getElementById("booking");
      if (book && d.booking && d.booking.email) {
        book.innerHTML = '<p class="chart-sub">Booking &amp; contact</p><a class="btn btn-neon" href="mailto:' +
          esc(d.booking.email) + '">' + esc(d.booking.email) + "</a>";
      }
    })
    .catch(function () { /* sections keep their static fallback content */ });
})();
