#!/usr/bin/env python3
"""The one-page infographic: Aster da Master in 60 seconds.

glance.html - every headline number, the top tracks, the eras, the
sessions, the circle, the codex - all computed from the verified data.
The "explain him in 60 seconds" page.

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change.
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
SESS = json.loads((ROOT / "data" / "sessions.json").read_text())
CODEX = json.loads((ROOT / "data" / "codex.json").read_text())
CIRCLE = json.loads((ROOT / "api" / "v1" / "circle.json").read_text())
OUT = ROOT / "glance.html"
SNAPSHOT = "2026-10-11"

NAV = """      <nav class="site-nav" aria-label="Primary">
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="scene/">Scene</a>
        <a href="timeline.html">Timeline</a>
        <a href="chronicle.html">Chronicle</a>
        <a href="transmission.html">Transmission</a>
        <a href="network.html">Network</a>
        <a href="milestone-race.html">Race</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html">Changelog</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="glance.html" aria-current="page">Glance</a>
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
        <a href="network.html">Network</a>
        <a href="milestone-race.html">Race</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html">Changelog</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="glance.html" aria-current="page">Glance</a>
        <a href="press-kit.html">Press kit</a>
      
        </nav>
      </details>"""

FOOTNAV = """      <nav aria-label="Footer">
        <a href="./">Home</a>
        <a href="./#discography">Discography</a>
        <a href="releases/">Releases</a>
        <a href="years/">Years</a>
        <a href="scene/">Scene</a>
        <a href="timeline.html">Timeline</a>
        <a href="chronicle.html">Chronicle</a>
        <a href="transmission.html">Transmission</a>
        <a href="network.html">Network</a>
        <a href="milestone-race.html">Race</a>
        <a href="decoder.html">Decoder</a>
        <a href="api-playground.html">API</a>
        <a href="agents.html">Agents</a>
        <a href="sessions.html">Sessions</a>
        <a href="changelog.html">Changelog</a>
        <a href="method.html">Method</a>
        <a href="trilogy.html">Trilogy</a>
        <a href="glance.html" aria-current="page">Glance</a>
        <a href="press-kit.html">Press kit</a>
      </nav>"""


def fmt(n):
    return f"{n:,}"


def main() -> int:
    releases = DATA["discography"]
    eras = DATA.get("eras", [])

    used, slugs = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        slugs.append(s)
    slug_of = {id(r): s for r, s in zip(releases, slugs)}

    vault = [r for r in releases if r.get("type") == "SoundCloud-only"]
    dist = [r for r in releases if r.get("type") != "SoundCloud-only"]
    total_plays = sum(r.get("plays") or 0 for r in vault)
    years = sorted({r["date"][:4] for r in vault if r.get("date")})
    year_span = f"{years[0]}–{years[-1]}" if years else "—"

    top5 = sorted(vault, key=lambda r: -(r.get("plays") or 0))[:5]
    top5_html = "".join(
        f'<li><a href="releases/{slug_of[id(r)]}.html">{escape(r["title"])}</a>'
        f' <span class="dim">{fmt(r.get("plays") or 0)} plays'
        f' &middot; {escape(r.get("date") or "")}</span></li>'
        for r in top5
    )

    era_html = "".join(
        f'<li><span>{escape(e["name"])}</span>'
        f'<span class="top-n">{escape(e.get("span") or "")}</span></li>'
        for e in eras
    )

    sessions = SESS["sessions"]
    top_sess = sorted(sessions,
                      key=lambda s: (-s["track_count"], -s["total_plays"]))[:3]
    sess_html = "".join(
        f'<li><a href="sessions/{slugify(s["name"])}.html">{escape(s["name"])}</a>'
        f' <span class="dim">{s["track_count"]} transmissions'
        f' &middot; {fmt(s["total_plays"])} plays</span></li>'
        for s in top_sess
    )

    collabs = sorted(
        ({"slug": k, **v} for k, v in CIRCLE.items()),
        key=lambda c: -c["shared_transmissions"],
    )[:5]
    collab_html = "".join(
        f'<li><a href="circle/{escape(c["slug"])}.html">{escape(c["name"])}</a>'
        f' <span class="dim">&times;{c["shared_transmissions"]} shared'
        f' &middot; {fmt(c["shared_plays"])} plays</span></li>'
        for c in collabs
    )

    families = CODEX["families"]
    codex_html = "".join(
        f'<li><a href="codex/{slugify(f["name"])}.html">{escape(f["name"])}</a>'
        f' <span class="dim">&times;{f["track_count"]} tracks</span></li>'
        for f in families
    )

    first = min(vault, key=lambda r: r.get("date") or "9999")
    last = max(vault, key=lambda r: r.get("date") or "")

    stats = [
        (fmt(len(releases)), "Transmissions archived"),
        (fmt(total_plays), "SoundCloud plays (snapshot)"),
        (year_span, "Years of output"),
        (fmt(len(sessions)), "Upload sessions"),
        (fmt(len(dist)), "Distributor releases"),
        (fmt(len(collabs and CIRCLE)), "Collaborators"),
        (fmt(len(families)), "Codex families"),
        (fmt(len(vault)), "Vault tracks"),
    ]
    stat_html = "".join(
        f'<div class="stat"><div class="stat-value">{escape(v)}</div>'
        f'<div class="stat-label">{escape(l)}</div></div>'
        for v, l in stats
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>At a glance — Aster da Master</title>
  <meta name="description" content="Aster da Master in 60 seconds: 219 transmissions, 257,394 plays, nine years, sixty-one sessions — every headline number from the verified archive.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/layout.css">
  <link rel="stylesheet" href="assets/css/components.css">
  <link rel="stylesheet" href="assets/css/motifs.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-bar">
      <a class="brand" href="./" aria-label="Aster da Master home">
        <span class="brand-mark" aria-hidden="true">A&#10022;</span>
        <span>ASTER DA MASTER</span>
      </a>
{NAV}
      <button class="search-btn" id="search-open" type="button" aria-label="Search the archive (keyboard shortcut: slash)">
        <span aria-hidden="true">&#8987;</span><kbd aria-hidden="true">/</kbd>
      </button>
    </div>
  </header>

  <div class="search-overlay" id="search-overlay" hidden>
    <div class="search-box" role="dialog" aria-modal="true" aria-labelledby="search-title">
      <p class="kicker" id="search-title"><span class="numeral">&#10022;</span>Search the archive</p>
      <input id="search-input" type="search" placeholder="Tracks, collaborators, eras, the codex&hellip;" aria-label="Search the archive" role="combobox" aria-expanded="true" aria-controls="search-results" autocomplete="off" spellcheck="false">
      <div id="search-results" role="listbox" aria-label="Search results"></div>
      <p class="search-hint"><kbd>/</kbd> to open &middot; <kbd>&#8593;</kbd><kbd>&#8595;</kbd> to move &middot; <kbd>Enter</kbd> to go &middot; <kbd>Esc</kbd> to close</p>
    </div>
  </div>

  <main id="main">
    <div class="container">
      <div class="section-head reveal">
        <span class="kicker"><span class="numeral">&#10022;</span>At a glance</span>
        <h1>Aster da Master in 60 seconds</h1>
        <p>Nine years of transmissions, every headline number from the verified archive. Sixty seconds here, or a lifetime in the <a href="releases/">full archive</a>.</p>
        <p class="chart-sub">Play counts are a {SNAPSHOT} snapshot and drift over time.</p>
      </div>

      <section class="section" aria-label="Headline numbers">
        <div class="stat-grid">{stat_html}</div>
      </section>

      <section class="section" aria-labelledby="g-top">
        <span class="kicker"><span class="numeral">&#10022;</span>The summit</span>
        <h2 id="g-top">Most played transmissions</h2>
        <ol class="year-list">{top5_html}</ol>
      </section>

      <section class="section" aria-labelledby="g-eras">
        <span class="kicker"><span class="numeral">&#10022;</span>The arc</span>
        <h2 id="g-eras">Six eras</h2>
        <ol class="top-list">{era_html}</ol>
      </section>

      <section class="section" aria-labelledby="g-sess">
        <span class="kicker"><span class="numeral">&#10022;</span>The studio diary</span>
        <h2 id="g-sess">Heaviest sessions</h2>
        <ol class="year-list">{sess_html}</ol>
        <p><a class="btn btn-sm" href="sessions.html">All 61 sessions &rarr;</a></p>
      </section>

      <section class="section" aria-labelledby="g-circle">
        <span class="kicker"><span class="numeral">&#10022;</span>The circle</span>
        <h2 id="g-circle">Most summoned collaborators</h2>
        <ol class="year-list">{collab_html}</ol>
        <p><a class="btn btn-sm" href="network.html">The full network &rarr;</a></p>
      </section>

      <section class="section" aria-labelledby="g-codex">
        <span class="kicker"><span class="numeral">&#10022;</span>The language</span>
        <h2 id="g-codex">Sixteen codex families</h2>
        <ol class="year-list">{codex_html}</ol>
      </section>

      <section class="section" aria-labelledby="g-bookends">
        <span class="kicker"><span class="numeral">&#10022;</span>The bookends</span>
        <h2 id="g-bookends">First and latest</h2>
        <p>Opened with <a href="releases/{slug_of[id(first)]}.html">{escape(first["title"])}</a> <span class="dim">({escape(first.get("date") or "")})</span> — latest is <a href="releases/{slug_of[id(last)]}.html">{escape(last["title"])}</a> <span class="dim">({escape(last.get("date") or "")})</span>.</p>
        <p><a class="btn btn-sm" href="timeline.html">Walk the timeline &rarr;</a></p>
      </section>
    </div>
  </main>

  <footer class="site-footer">
    <div class="container footer-grid">
      <p>&copy; 2026 ASTER DA MASTER &mdash; ALL SIGNALS RESERVED</p>
{FOOTNAV}
    </div>
  </footer>
  <script src="assets/js/common.js"></script>
  <script src="assets/js/identity.js"></script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"glance: 1 page -> glance.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
