#!/usr/bin/env python3
"""Write index.html: the name, one sleeve, and the whole catalogue by year.

Reads data/artist.json only. Catalogue marks (ADM 0001 ...) are minted exactly
as scripts/build_releases.py mints them, so the two always agree. Nothing here
reads or prints a play count, a listener number or a stream total: the data
layer keeps them, the presented site never shows them.
"""
import json
from datetime import datetime
from html import escape
from pathlib import Path

import build_releases as br

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "artist.json").read_text())
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

LISTEN = [
    ("SoundCloud", "https://soundcloud.com/asterdamaster"),
    ("Apple Music", "https://music.apple.com/us/artist/aster-da-master/1466301103"),
    ("iHeart", "https://www.iheart.com/artist/aster-da-master-33038534/"),
]


def slugs_for(releases):
    used, out = set(), []
    for r in releases:
        base = s = br.slugify(r["title"]); n = 1
        while s in used:
            n += 1; s = f"{base}-{n}"
        used.add(s); out.append(s)
    return out


def kind(r):
    return "SoundCloud" if r["type"] == "SoundCloud-only" else r["type"]


def month_year(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{MONTHS[m - 1]} {y}"


def build():
    rel = DATA["discography"]
    slugs = slugs_for(rel)
    marks = br.catalog_marks(rel, slugs)            # slug -> "ADM 0221"
    top = len(rel)
    rows = []
    for r, s in zip(rel, slugs):
        n = int(marks[s][4:])
        rows.append({"r": r, "slug": s, "mark": marks[s], "n": n, "h": n / top})
    rows.sort(key=lambda x: x["n"], reverse=True)   # newest first
    newest = rows[0]

    years = {}
    for x in rows:
        years.setdefault(x["r"]["date"][:4], []).append(x)

    blocks = []
    for i, (y, items) in enumerate(years.items()):
        lis = []
        for x in items:
            r = x["r"]
            mon = MONTHS[int(r["date"][5:7]) - 1]
            tag = "<b>Album</b> &middot; " if r["type"] == "Album" else ""
            lis.append(
                f'<li data-t="{escape(r["title"].lower(), quote=True)}"><a href="releases/{x["slug"]}.html">'
                f'<i class="hz" style="--h:{x["h"]:.3f}" aria-hidden="true"></i>'
                f'<span class="t">{escape(r["title"])}</span>'
                f'<span class="m">{tag}{x["mark"]} &middot; {mon}</span></a></li>')
        word = "release" if len(items) == 1 else "releases"
        blocks.append(
            f'<details class="year"{" open" if i < 2 else ""}><summary><span class="yr">{y}</span>'
            f'<span class="n">{len(items)} {word}</span></summary><ol>{"".join(lis)}</ol></details>')

    first_year, last_year = min(years), max(years)
    listen = " &middot; ".join(f'<a href="{u}" rel="noopener">{escape(n)}</a>' for n, u in LISTEN)
    nr = newest["r"]
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aster da Master</title>
  <meta name="description" content="Aster da Master. Underground, internet-made music since 2017. The whole catalogue, newest first.">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Aster da Master">
  <meta property="og:description" content="Underground, internet-made music since 2017. The whole catalogue, newest first.">
  <link rel="canonical" href="/">
  <meta property="og:image" content="assets/og-card.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#EFEEEA">
  <link rel="preload" href="assets/fonts/ibm-plex-sans-300-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="assets/css/fonts.css">
  <link rel="stylesheet" href="assets/css/aster.css">
  <link rel="stylesheet" href="assets/css/sleeve.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="hd">
    <a class="hd-name" href="./">Aster da Master</a>
    <nav class="site-nav" aria-label="Primary">
      <a href="releases/">Releases</a>
      <a href="story.html">Story</a>
      <a href="about.html">About</a>
      <a href="press-kit.html">Press kit</a>
    </nav>
  </header>
  <main id="main">
    <section class="room" aria-labelledby="name">
      <h1 id="name">Aster da Master</h1>
      <p class="room-tag">He transcends music.</p>
      <figure class="sleeve" style="--h:{newest["h"]:.3f}">
        <a class="sleeve-face" href="releases/{newest["slug"]}.html">
          <span class="sleeve-cat">{newest["mark"]}</span>
          <span class="sleeve-horizon" aria-hidden="true"></span>
          <span class="sleeve-title">{escape(nr["title"])}
            <span class="sleeve-meta">{kind(nr)} &middot; {month_year(nr["date"])}</span>
          </span>
        </a>
        <figcaption class="sleeve-listen">Listen on {listen}</figcaption>
      </figure>
    </section>
    <section class="catalogue" aria-labelledby="cat-h">
      <div class="cat-head">
        <h2 id="cat-h">Catalogue</h2>
        <label class="find"><span class="vh">Find a release</span><input id="find" type="search" placeholder="Find a release" autocomplete="off"></label>
      </div>
      <p class="cat-count" id="cat-count" aria-live="polite">{len(rows)} releases, {first_year} to {last_year}</p>
      {"".join(blocks)}
      <p class="cat-more"><a href="releases/">Filter by type</a></p>
    </section>
  </main>
  <footer class="site-footer">
    <div class="container footer-grid">
      <p>&copy; 2026 Aster da Master</p>
      <nav aria-label="Footer">
        <a href="./">Home</a>
        <a href="releases/">Releases</a>
        <a href="story.html">Story</a>
        <a href="about.html">About</a>
        <a href="press-kit.html">Press kit</a>
      </nav>
    </div>
  </footer>
  <script src="assets/js/identity.js"></script>
  <script src="assets/js/catalogue.js" defer></script>
</body>
</html>
"""
    (ROOT / "index.html").write_text(html)
    print(f"index.html: {len(rows)} releases, {len(years)} years, newest {newest['mark']}")


if __name__ == "__main__":
    build()
