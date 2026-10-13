#!/usr/bin/env python3
"""One-off builder for scene-atlas.html (Rotation 10, Scene Atlas flagship).

Renders the static first charting (figure #1 by shared plays) and the
full 22-row chart log from the ONLY two data sources the Atlas is
allowed to use: data/v1/circle.json (the 21 title-credited
collaborators) and data/v1/scene-figures.json (the producer-credit
scene figure). The live page re-derives everything in
assets/js/scene-atlas.js from the same two files; this script exists
so the page reads correctly with no JS. Not part of the validate.sh
generator chain.
"""
import html
import json
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")


def esc(s):
    return html.escape(str(s), quote=True)


def figures():
    circle = json.loads((ROOT / "data/v1/circle.json").read_text())
    scene = json.loads((ROOT / "data/v1/scene-figures.json").read_text())
    out = []
    for k, v in circle.items():
        vn = v.get("verified_notes") or {}
        out.append({
            "id": k, "name": v["name"], "kind": "Title-credited collaborator",
            "page": v["page"], "n": v["shared_transmissions"],
            "plays": v["shared_plays"], "years": v["years_active"],
            "tracks": v["tracks"], "facts": vn.get("facts", []),
            "sources": vn.get("sources", []),
        })
    for k, v in scene.items():
        yrs = sorted(t["date"][:4] for t in v["tracks"])
        out.append({
            "id": k, "name": v["name"], "kind": v["kind"], "page": v["page"],
            "n": len(v["tracks"]), "plays": sum(t["plays"] for t in v["tracks"]),
            "years": f"{yrs[0]}\u2013{yrs[-1]}", "tracks": v["tracks"],
            "facts": v["facts"], "sources": v["sources"],
            "standing": v.get("standing", ""), "watch": v.get("watch"),
        })
    out.sort(key=lambda f: -f["plays"])
    return out


def main():
    figs = figures()
    first = figs[0]
    tracks_html = "".join(
        f'<li>{esc(t["title"])} <span class="dim">{esc(t["date"])} &middot; '
        f'{t["plays"]:,} plays &middot; {esc(t["type"])}</span></li>'
        for t in sorted(first["tracks"], key=lambda t: t["date"]))
    log_rows = "".join(
        f'<tr data-fig="{esc(f["id"])}"><td class="n">{i:02d}</td>'
        f'<td><a href="{esc(f["page"])}">{esc(f["name"])}</a></td>'
        f'<td>{esc(f["kind"])}</td><td class="n">{f["n"]}</td>'
        f'<td class="n">{f["plays"]:,}</td><td>{esc(f["years"])}</td>'
        f'<td>{len(f["facts"])} recorded</td></tr>\n'
        for i, f in enumerate(figs, 1))
    page = TEMPLATE.replace("%%FIRST_TRACKS%%", tracks_html)
    page = page.replace("%%LOG_ROWS%%", log_rows)
    (ROOT / "scene-atlas.html").write_text(page, encoding="utf-8")
    print(f"scene-atlas.html written: {len(figs)} figures, "
          f"first = {first['name']} ({first['plays']:,} plays)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Scene Atlas — Aster da Master</title>
  <meta name="description" content="The Scene Atlas: every figure around the Aster da Master archive charted as a point on one pirate cartographer's chart — the 21 title-credited collaborators plus the producer-credit scene figure, plotted only from data the archive already carries.">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Scene Atlas — Aster da Master">
  <meta property="og:description" content="The Scene Atlas: every figure around the Aster da Master archive charted as a point on one pirate cartographer's chart — the 21 title-credited collaborators plus the producer-credit scene figure, plotted only from data the archive already carries.">
  <link rel="canonical" href="/scene-atlas.html">
  <meta property="og:image" content="assets/og-card.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Scene Atlas — Aster da Master">
  <meta name="twitter:description" content="The Scene Atlas: every figure around the Aster da Master archive charted as a point on one pirate cartographer's chart — the 21 title-credited collaborators plus the producer-credit scene figure, plotted only from data the archive already carries.">
  <meta name="twitter:image" content="assets/og-card.png">
  <link rel="preload" href="assets/fonts/anton-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="assets/css/fonts.css">
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/layout.css">
  <link rel="stylesheet" href="assets/css/components.css">
  <link rel="stylesheet" href="assets/css/motifs.css">
  <link rel="stylesheet" href="assets/css/scene-atlas.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>

  <header class="site-header">
    <div class="container header-bar">
      <a class="brand" href="./" aria-label="Aster da Master home">
        <span class="brand-mark" aria-hidden="true">A&#10022;</span>
        <span>ASTER DA MASTER</span>
      </a>
      <nav class="site-nav" aria-label="Primary">
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="scene/">Scene</a>
        <a href="timeline.html">Timeline</a>
        <a href="chronicle.html">Chronicle</a>
        <a href="transmission.html">Transmission</a>
        <a href="tuner.html">Tuner</a>
        <a href="scene-atlas.html" aria-current="page">Atlas</a>
        <a href="network.html">Network</a>
        <a href="milestone-race.html">Race</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html">Changelog</a>
        <a href="glance.html">Glance</a>
        <a href="press-kit.html">Press kit</a>
      </nav>
      <details class="mnav">
        <summary><span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>Menu</summary>
        <nav class="mnav-panel" aria-label="Mobile">
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="scene/">Scene</a>
        <a href="timeline.html">Timeline</a>
        <a href="chronicle.html">Chronicle</a>
        <a href="transmission.html">Transmission</a>
        <a href="tuner.html">Tuner</a>
        <a href="scene-atlas.html" aria-current="page">Atlas</a>
        <a href="network.html">Network</a>
        <a href="milestone-race.html">Race</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html">Changelog</a>
        <a href="glance.html">Glance</a>
        <a href="press-kit.html">Press kit</a>
        </nav>
      </details>
      <button class="search-btn" id="search-open" type="button" aria-label="Search the archive (keyboard shortcut: slash)">
        <span aria-hidden="true">&#8981;</span><kbd aria-hidden="true">/</kbd>
      </button>
    </div>
  </header>

  <div class="search-overlay" id="search-overlay" hidden>
    <div class="search-box" role="dialog" aria-modal="true" aria-labelledby="search-title">
      <p class="kicker" id="search-title"><span class="numeral">&#10022;</span>Search the archive</p>
      <input id="search-input" type="search" placeholder="Tracks, collaborators, eras, the codex&hellip;" aria-label="Search the archive" role="combobox" aria-expanded="true" aria-controls="search-results" autocomplete="off" spellcheck="false">
      <div id="search-results" role="listbox" aria-label="Search results"></div>
      <p class="search-hint"><kbd>/</kbd> to open &middot; <kbd>&uarr;</kbd><kbd>&darr;</kbd> to move &middot; <kbd>Enter</kbd> to go &middot; <kbd>Esc</kbd> to close</p>
    </div>
  </div>

  <main id="main">
    <section class="section atlas-hero" aria-labelledby="atlas-h">
      <div class="container">
        <span class="onair"><i aria-hidden="true"></i>Charting the waters around the broadcast</span>
        <h1 class="atlas-title" id="atlas-h">Scene <span class="atlas-title-dim">Atlas</span></h1>
        <p class="atlas-lede">A pirate cartographer&rsquo;s chart of the scene around the music. <strong>Every figure the archive actually records is a plotted point</strong> — their real role, their shared transmissions, and only the connections the data itself states. Where the record is thin, the chart says so and plots them thin. Nothing is filled in from the fog.</p>
        <div class="btn-row">
          <a class="btn btn-neon" href="#chart">Start charting &darr;</a>
          <a class="btn btn-ghost" href="#chart-log">The full chart log</a>
        </div>
        <div class="atlas-stats" aria-label="Atlas totals">
          <div><b>22</b><span>figures charted</span></div>
          <div><b>21</b><span>title-credited collaborators</span></div>
          <div><b>1</b><span>producer-credit scene figure</span></div>
          <div><b>46</b><span>shared track entries plotted</span></div>
          <div><b>8</b><span>with verified notes</span></div>
          <div><b>14</b><span>plotted honestly thin</span></div>
        </div>
      </div>
    </section>

    <section class="section" id="chart" aria-labelledby="chart-h">
      <div class="container">
        <span class="kicker"><span class="numeral">&#10022;</span>The chart</span>
        <h2 id="chart-h">One route, twenty-two soundings</h2>
        <p class="chart-sub">The route runs deepest first: figures are charted in order of shared plays, exactly as the two source files record them (a shared track counts once per figure credited on it, so soundings overlap where a track carries several names). Select any sounding to open its chart card.</p>

        <div>
          <p class="ctl-label" id="atlas-filter-label">Show — chart by record</p>
          <div class="chip-row" id="atlas-filters" role="group" aria-labelledby="atlas-filter-label">
            <button type="button" class="chip" data-filter="all" aria-pressed="true">All figures <small>22</small></button>
            <button type="button" class="chip" data-filter="collaborator" aria-pressed="false">Collaborators <small>21</small></button>
            <button type="button" class="chip" data-filter="scene" aria-pressed="false">Scene figure <small>1</small></button>
            <button type="button" class="chip" data-filter="verified" aria-pressed="false">Verified notes <small>8</small></button>
            <button type="button" class="chip" data-filter="thin" aria-pressed="false">Honestly thin <small>14</small></button>
          </div>
        </div>

        <div class="atlas-deck">
          <ol class="atlas-route" id="atlas-route" aria-label="Charted figures, deepest first"></ol>
          <div class="atlas-card-slot">
            <article class="atlas-card" id="atlas-card">
              <div class="atlas-card-head">
                <span class="atlas-rank">SOUNDING 01 / 22</span>
                <span class="atlas-kind">Title-credited collaborator</span>
              </div>
              <h2 class="atlas-card-name">Yung Vetta</h2>
              <div class="atlas-card-facts">
                <div><b>7</b><span>shared transmissions</span></div>
                <div><b>17,893</b><span>shared plays</span></div>
                <div><b>2018&ndash;2019</b><span>years on the chart</span></div>
                <div><b>0</b><span>verified notes recorded</span></div>
              </div>
              <p class="atlas-card-note">The archive carries no verified notes for Yung Vetta yet — only the shared record below. Plotted honestly thin: the sounding is real, the coastline beyond it is not drawn.</p>
              <h3 class="atlas-sub">The shared record, in order</h3>
              <ol class="year-list">%%FIRST_TRACKS%%</ol>
              <div class="atlas-card-actions">
                <a class="btn btn-neon" href="circle/yung-vetta.html">Full circle page &rarr;</a>
              </div>
            </article>
            <p class="atlas-status" id="atlas-status">Charted from the archive&rsquo;s own two scene files. A figure can be shared: the chart writes its name into the address bar as you plot it.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="routes-h">
      <div class="container">
        <span class="kicker"><span class="numeral">&#10022;</span>Crossings</span>
        <h2 id="routes-h">Routes the data itself draws</h2>
        <p class="chart-sub">A crossing exists only where the <em>same track title</em> appears in two figures&rsquo; own shared records — the archive&rsquo;s title lists, compared literally. Five titles cross. No other routes are drawn, because the data states no others.</p>
        <ul class="atlas-routes" id="atlas-routes">
          <li><strong>NIGHT MODE ft. MAX FERRARI x YUNG VETTA x JAX</strong> <span class="dim">— Max Ferrari &times; Yung Vetta &times; JAX (2019-07-09 &middot; 10,083 plays)</span></li>
          <li><strong>master key ft. Lil Wintr x Marcelo (prod. ginseng)</strong> <span class="dim">— Lil Wintr &times; Marcelo (2019-12-06 &middot; 9,615 plays)</span></li>
          <li><strong>DESTINY (ft. JAX &amp; Max Ferrari) ~ [prod. louky]</strong> <span class="dim">— JAX &times; Max Ferrari (2018-08-20 &middot; 2,000 plays)</span></li>
          <li><strong>Master Key (feat. Lil Wintr &amp; Marcelo)</strong> <span class="dim">— Lil Wintr &times; Marcelo (2019-12-06 &middot; plays not carried — the distributor single entry)</span></li>
          <li><strong>nitemode2019 w/ Max+Vetty prod. NaXi.wav</strong> <span class="dim">— Max &times; Vetty (2024-11-05 &middot; 17 plays)</span></li>
        </ul>
      </div>
    </section>

    <section class="section" id="chart-log" aria-labelledby="chart-log-h">
      <div class="container">
        <span class="kicker"><span class="numeral">&#10022;</span>The printed chart</span>
        <h2 id="chart-log-h">The full chart log</h2>
        <details class="chart-log" open>
          <summary>All 22 figures, deepest first — <span id="chart-log-count">22 soundings</span>. Select any row to open its chart card.</summary>
          <table>
            <thead><tr><th class="n" scope="col">#</th><th scope="col">Figure</th><th scope="col">Recorded role</th><th class="n" scope="col">Tracks</th><th class="n" scope="col">Shared plays</th><th scope="col">Years</th><th scope="col">Verified notes</th></tr></thead>
            <tbody id="chart-log-body">
%%LOG_ROWS%%            </tbody>
          </table>
        </details>
        <p class="chart-sub">Provenance: plotted only from <code>data/v1/circle.json</code> (the 21 title-credited collaborators and their shared records) and <code>data/v1/scene-figures.json</code> (the producer-credit scene figure, with its recorded standing, facts, sources, and release watch). No other source feeds this chart; no connection, date, or biographical claim appears here that those files do not carry. Titles and metadata only.</p>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container footer-grid">
      <p>&copy; 2026 ASTER DA MASTER &mdash; ALL SIGNALS RESERVED</p>
      <nav aria-label="Footer">
        <a href="./">Home</a>
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="scene/">Scene</a>
        <a href="timeline.html">Timeline</a>
        <a href="chronicle.html">Chronicle</a>
        <a href="transmission.html">Transmission</a>
        <a href="tuner.html">Tuner</a>
        <a href="scene-atlas.html" aria-current="page">Atlas</a>
        <a href="network.html">Network</a>
        <a href="milestone-race.html">Race</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html">Changelog</a>
        <a href="glance.html">Glance</a>
        <a href="press-kit.html">Press kit</a>
      </nav>
    </div>
  </footer>
  <script src="assets/js/common.js"></script>
  <script src="assets/js/search.js"></script>
  <script src="assets/js/identity.js"></script>
  <script src="assets/js/scene-atlas.js"></script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
