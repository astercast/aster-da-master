#!/usr/bin/env python3
"""Deep-dive pages for the top-10 upload sessions (by track count).

The top-10 sessions get studio-diary detail pages: the story the dates
tell, key collaborators, era placement, and every track. Run AFTER
scripts/build_sessions.py (which links these pages from sessions.html).

Output:
  sessions/<slug>.html   - one detail page per top-10 session

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change (after build_sessions.py).
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import nav_data  # noqa: E402  (canonical nav data — scripts/nav_data.py)
from build_releases import slugify  # noqa: E402  (single source of truth)
from build_sessions import session_slug  # noqa: E402  (shared slug rule)
from build_years import parse_collabs, era_for_year  # noqa: E402  (same parsers)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
SESS = json.loads((ROOT / "data" / "sessions.json").read_text())
OUT = ROOT / "sessions"
SNAPSHOT = "2026-10-11"

NAV = nav_data.nav_chunk("../", "eras")

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Aster da Master</title>
  <meta name="description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{title} — Aster da Master">
  <meta property="og:description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:image" content="../assets/og-card.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} — Aster da Master">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="../assets/og-card.png">
  <link rel="preload" href="../assets/fonts/anton-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="../assets/css/fonts.css">

  <link rel="stylesheet" href="../assets/css/tokens.css">
  <link rel="stylesheet" href="../assets/css/base.css">
  <link rel="stylesheet" href="../assets/css/layout.css">
  <link rel="stylesheet" href="../assets/css/components.css">
  <link rel="stylesheet" href="../assets/css/motifs.css">
  <link rel="stylesheet" href="../assets/css/layer2.css">
</head>
<body class="layer2">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-bar">
      <a class="brand" href="../" aria-label="Aster da Master home">
        <span class="brand-mark" aria-hidden="true">A&#10022;</span>
        <span>ASTER DA MASTER</span>
      </a>
      """ + NAV + """
    </div>
  </header>
  <main id="main">
    <div class="container">
"""

FOOT = """    </div>
  </main>
  <footer class="site-footer">
    <div class="container footer-grid">
      <p>&copy; 2026 ASTER DA MASTER &mdash; ALL SIGNALS RESERVED</p>
      """ + nav_data.footer_block("../", "eras") + """
    </div>
  </footer>
  <script src="../assets/js/common.js"></script>
  <script src="../assets/js/identity.js"></script>
</body>
</html>
"""

def fmt(n):
    return f"{n:,}"

def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"

def rank_word(i: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(i, f"{i}th")

def session_story(s, rank: int):
    """Factual story lines from the session's own dates. No narrative invented."""
    lines = []
    n, days = s["track_count"], s["days"]
    if s["start"] == s["end"]:
        lines.append(
            f"{n} transmissions uploaded in a single day — {s['start']}. "
            f"Nothing before or after within seven days; the session stands alone."
        )
    else:
        lines.append(
            f"{n} transmissions across {days} days, {s['start']} to {s['end']} — "
            "a sustained run with no gap longer than a week."
        )
    if rank == 1:
        lines.append(
            "The most prolific upload session on record — no other session "
            "put out more transmissions."
        )
    else:
        lines.append(
            f"The {rank_word(rank)} most prolific session on record by transmission count."
        )
    lines.append(
        f"{fmt(s['total_plays'])} total plays across the session's tracks "
        f"(snapshot {SNAPSHOT})."
    )
    return lines

def session_collabs(s):
    collabs = {}
    for t in s["tracks"]:
        for c in parse_collabs(t["title"]):
            k = c.lower()
            if k not in collabs:
                collabs[k] = {"name": c, "n": 0}
            collabs[k]["n"] += 1
    return sorted(collabs.values(), key=lambda c: (-c["n"], c["name"].lower()))[:5]

def session_eras(s, eras):
    names = []
    for y in {s["start"][:4], s["end"][:4]}:
        if y.isdigit():
            e = era_for_year(int(y), eras)
            if e and e["name"] not in names:
                names.append(e["name"])
    return names

def deepdive_page(s, slug, rank, collabs, era_names, prev_s, next_s):
    story = "".join(f"<li>{escape(line)}</li>" for line in session_story(s, rank))
    if collabs:
        collab_html = "".join(
            f'<li><span>{escape(c["name"])}</span>'
            f'<span class="top-n">&times;{c["n"]}</span></li>'
            for c in collabs
        )
        collab_sec = f"""
      <section class="section" aria-labelledby="sc-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The summoned</span>
        <h2 id="sc-h">Key collaborators in this session</h2>
        <ol class="top-list">{collab_html}</ol>
        <p class="chart-sub">Credits parsed from <em>w/</em> and <em>ft.</em> fragments in titles &mdash; as credited, verbatim; producers excluded.</p>
      </section>"""
    else:
        collab_sec = """
      <section class="section" aria-labelledby="sc-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The summoned</span>
        <h2 id="sc-h">A solo run</h2>
        <p>No collaborator credits in this session's titles — every transmission stands alone.</p>
      </section>"""
    era_line = (
        f"Landed in <strong>{escape(' & '.join(era_names))}</strong>."
        if era_names else "Era placement unconfirmed."
    )
    rows = "".join(
        f'<li><a href="../{escape(t["page"])}">{escape(t["title"])}</a>'
        f' <span class="dim">{escape(t["date"])}'
        + (f" &middot; {fmt(t['plays'])} plays" if t.get("plays") else "")
        + "</span></li>"
        for t in s["tracks"]
    )
    prev_link = (
        f'<a class="btn btn-sm" href="{prev_s}.html" rel="prev">&larr; Prev</a>'
        if prev_s else '<span class="btn btn-sm" aria-disabled="true">&larr;</span>'
    )
    next_link = (
        f'<a class="btn btn-sm" href="{next_s}.html" rel="next">Next &rarr;</a>'
        if next_s else '<span class="btn btn-sm" aria-disabled="true">&rarr;</span>'
    )
    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <a href="../sessions.html">Sessions</a> / <span aria-current="page">{escape(s["name"])}</span>
      </nav>
      <section class="section" aria-labelledby="ss-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Session deep dive · {rank_word(rank)} by volume</span>
        <h1 id="ss-h">{escape(s["name"])}</h1>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{s["track_count"]}</div><div class="stat-label">Transmissions</div></div>
          <div class="stat"><div class="stat-value">{fmt(s["total_plays"])}</div><div class="stat-label">Total plays</div></div>
          <div class="stat"><div class="stat-value">{s["days"]}</div><div class="stat-label">Days</div></div>
        </div>
        <p class="chart-sub">Play counts are the {SNAPSHOT} vault snapshot.</p>
      </section>

      <section class="section" aria-labelledby="st-h">
        <span class="kicker"><span class="numeral">&#10022;</span>What the dates say</span>
        <h2 id="st-h">The story, told by the calendar</h2>
        <ul class="story-list">{story}</ul>
        <p>{era_line}</p>
      </section>
      {collab_sec}

      <section class="section" aria-labelledby="sl-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The record</span>
        <h2 id="sl-h">Every transmission in this session</h2>
        <ol class="year-list">{rows}</ol>
      </section>

      <nav class="year-pager" aria-label="Session deep-dive navigation">
        {prev_link}
        <a class="btn btn-sm" href="../sessions.html">All sessions</a>
        <a class="btn btn-sm" href="../sessions-explorer.html">Sessions explorer</a>
        <a class="btn btn-sm" href="../milestone-race.html">Milestone race</a>
        {next_link}
      </nav>
"""
    return HEAD.format(
        title=f"{s['name']} — session deep dive",
        desc=f"{s['name']}: {s['track_count']} transmissions, {fmt(s['total_plays'])} plays. The studio diary, up close.",
        canonical=f"/sessions/{slug}.html",
    ) + body + FOOT

def main() -> int:
    eras = DATA.get("eras", [])
    sessions = SESS["sessions"]
    top = sorted(sessions, key=lambda s: (-s["track_count"], -s["total_plays"]))[:10]
    slugs = [session_slug(s["name"]) for s in top]
    assert len(set(slugs)) == len(slugs), "session slug collision"

    OUT.mkdir(exist_ok=True)
    for i, s in enumerate(top):
        slug = slugs[i]
        prev_s = slugs[i - 1] if i > 0 else None
        next_s = slugs[i + 1] if i < 9 else None
        html = deepdive_page(
            s, slug, i + 1,
            session_collabs(s),
            session_eras(s, eras),
            prev_s, next_s,
        )
        (OUT / f"{slug}.html").write_text(html, encoding="utf-8")

    print(f"session deep-dives: {len(top)} pages -> sessions/")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
