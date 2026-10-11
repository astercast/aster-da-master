#!/usr/bin/env python3
"""Generate collaborator archive pages for the Aster da Master site.

Output:
  circle/<slug>.html   - one page per title-credited collaborator (21)
  circle/index.html     - the circle index
  api/v1/circle.json    - machine-readable collaborator index
                          (registered in api/v1/index.json)

Per collaborator: shared tracks (titles/dates/plays, linked to release
pages), total shared plays, years active, era breakdown. Credits are
parsed from w//ft./feat. fragments in titles - as credited, verbatim,
nothing inferred. Producers are excluded (same rule as network.html).

Titles only - no lyrics anywhere. Idempotent: regenerates cleanly.
Re-run after any discography change. Also bumps data version to 0.8.0
and mirrors data/artist.json to api/v1/artist.json.
"""
import json
import re
import shutil
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_releases import slugify  # noqa: E402  (single source of truth)
from build_years import parse_collabs, era_for_year  # noqa: E402  (same parser as network.js)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
OUT = ROOT / "circle"
API = ROOT / "api" / "v1"
NEW_VERSION = "0.8.0"

NAV = """<nav class="site-nav" aria-label="Primary">
        <a href="../#discography">Discography</a>
        <a href="../releases/">Releases</a>
        <a href="../years/">Years</a>
        <a href="./">Circle</a>
        <a href="../timeline.html">Timeline</a>
        <a href="../network.html">Network</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a>
        <a href="../method.html">Method</a>
        <a href="../trilogy.html">Trilogy</a>
        <a href="../sessions.html">Sessions</a>
        <a href="../changelog.html">Changelog</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Aster da Master</title>
  <meta name="description" content="{desc}">
  <link rel="stylesheet" href="../assets/css/tokens.css">
  <link rel="stylesheet" href="../assets/css/base.css">
  <link rel="stylesheet" href="../assets/css/layout.css">
  <link rel="stylesheet" href="../assets/css/components.css">
</head>
<body>
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
      <nav aria-label="Footer">
        <a href="../">Home</a>
        <a href="../releases/">Releases</a>
        <a href="../years/">Years</a>
        <a href="./">Circle</a>
        <a href="../timeline.html">Timeline</a>
        <a href="../network.html">Network</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a>
        <a href="../method.html">Method</a>
        <a href="../trilogy.html">Trilogy</a>
        <a href="../sessions.html">Sessions</a>
        <a href="../changelog.html">Changelog</a>
        <a href="../press-kit.html">Press kit</a>
      </nav>
    </div>
  </footer>
</body>
</html>
"""


def fmt(n):
    return f"{n:,}"


def years_active(tracks):
    yrs = sorted({t["date"][:4] for t in tracks if t.get("date")})
    if not yrs:
        return "dates unknown"
    return yrs[0] if len(yrs) == 1 else f"{yrs[0]}–{yrs[-1]}"


def collab_page(name, slug, tracks, slug_of, eras, prev_s, next_s):
    total_plays = sum(t.get("plays") or 0 for t in tracks)
    era_counts = {}
    for t in tracks:
        y = (t.get("date") or "")[:4]
        era = era_for_year(int(y), eras) if y.isdigit() else None
        key = era["name"] if era else "Unplaced"
        era_counts[key] = era_counts.get(key, 0) + 1
    era_html = "".join(
        f"<li><span>{escape(e)}</span><span class=\"top-n\">&times;{n}</span></li>"
        for e, n in sorted(era_counts.items(), key=lambda kv: -kv[1])
    )

    rows = "".join(
        f'<li><a href="../releases/{slug_of[id(t["_r"])]}.html">{escape(t["title"])}</a>'
        f' <span class="dim">{escape(t.get("date") or "date unknown")}'
        + (f" &middot; {fmt(t['plays'])} plays" if t.get("plays") else "")
        + f" &middot; {escape(t['type'])}</span></li>"
        for t in sorted(tracks, key=lambda t: t.get("date") or "")
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
        <a href="../">Home</a> / <a href="../network.html">Network</a>
        <a href="../decoder.html">Decoder</a>
        <a href="../api-playground.html">API</a> / <a href="./">Circle</a> / <span aria-current="page">{escape(name)}</span>
      </nav>
      <section class="section" aria-labelledby="cc-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The circle</span>
        <h2 id="cc-h">{escape(name)}</h2>
        <div class="stat-grid">
          <div class="stat"><div class="stat-value">{len(tracks)}</div><div class="stat-label">Shared transmissions</div></div>
          <div class="stat"><div class="stat-value">{fmt(total_plays)}</div><div class="stat-label">Shared plays</div></div>
          <div class="stat"><div class="stat-value">{escape(years_active(tracks))}</div><div class="stat-label">Years active</div></div>
        </div>
        <p class="chart-sub">Play counts are the 2026-10-11 vault snapshot. Credits parsed from <em>w/</em> and <em>ft.</em> fragments in titles &mdash; as credited, verbatim; producers excluded.</p>
      </section>

      <section class="section" aria-labelledby="ce-h">
        <span class="kicker"><span class="numeral">&#10022;</span>Era breakdown</span>
        <h3 id="ce-h">Where the collaborations landed</h3>
        <ol class="top-list">{era_html}</ol>
      </section>

      <section class="section" aria-labelledby="ct-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The shared record</span>
        <h3 id="ct-h">Every shared transmission, in order</h3>
        <ol class="year-list">{rows}</ol>
      </section>

      <nav class="year-pager" aria-label="Collaborator navigation">
        {prev_link}
        <a class="btn btn-sm" href="./">The full circle</a>
        {next_link}
      </nav>
"""
    return HEAD.format(
        title=f"{name} — collaborator",
        desc=f"{name} and Aster da Master: {len(tracks)} shared transmissions, {fmt(total_plays)} plays.",
    ) + body + FOOT


def index_page(entries):
    cards = "".join(
        f'<a class="year-card" href="{e["slug"]}.html">'
        f'<span class="year-card-y">{escape(e["name"])}</span>'
        f'<span class="year-card-n">{e["n"]} shared &middot; {fmt(e["plays"])} plays</span>'
        f'<span class="year-card-e">{escape(e["years"])}</span>'
        f"</a>"
        for e in entries
    )
    body = f"""
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="../">Home</a> / <span aria-current="page">Circle</span>
      </nav>
      <section class="section" aria-labelledby="ci-h">
        <span class="kicker"><span class="numeral">&#10022;</span>The circle</span>
        <h2 id="ci-h">Everyone he summoned, one page each</h2>
        <p>Every collaborator credited in a title across 219 transmissions. Counts and plays are data, not editorial.</p>
        <div class="year-grid">{cards}</div>
      </section>
"""
    return HEAD.format(
        title="The circle — collaborator archive",
        desc="Every Aster da Master collaborator: shared tracks, plays, years active.",
    ) + body + FOOT


def main():
    releases = DATA["discography"]
    eras = DATA.get("eras", [])

    # Release slugs: identical algorithm to build_search_index.py.
    used, slugs = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        slugs.append(s)
    assert len(set(slugs)) == len(releases), "release slug collision"
    slug_of = {id(r): s for r, s in zip(releases, slugs)}

    collabs = {}
    for r in releases:
        for n in parse_collabs(r["title"]):
            k = n.lower()
            if k not in collabs:
                collabs[k] = {"display": n, "tracks": []}
            if len(n) >= len(collabs[k]["display"]):
                collabs[k]["display"] = n
            collabs[k]["tracks"].append(
                {"title": r["title"], "date": r.get("date"), "plays": r.get("plays"),
                 "type": r["type"], "_r": r}
            )

    ordered = sorted(collabs.items(), key=lambda kv: (-len(kv[1]["tracks"]), kv[1]["display"].lower()))

    # Collaborator slugs (deduped; single source of truth for JS deep links).
    cused, entries = set(), []
    for key, info in ordered:
        s = slugify(info["display"])
        base, n = s, 1
        while s in cused:
            n += 1
            s = f"{base}-{n}"
        cused.add(s)
        tracks = info["tracks"]
        entries.append({
            "key": key, "name": info["display"], "slug": s,
            "tracks": tracks,
            "n": len(tracks),
            "plays": sum(t.get("plays") or 0 for t in tracks),
            "years": years_active(tracks),
        })
    assert len({e["slug"] for e in entries}) == len(entries), "collaborator slug collision"

    OUT.mkdir(exist_ok=True)
    for i, e in enumerate(entries):
        prev_s = entries[i - 1]["slug"] if i > 0 else None
        next_s = entries[i + 1]["slug"] if i < len(entries) - 1 else None
        (OUT / f'{e["slug"]}.html').write_text(
            collab_page(e["name"], e["slug"], e["tracks"], slug_of, eras, prev_s, next_s),
            encoding="utf-8",
        )

    (OUT / "index.html").write_text(index_page(entries), encoding="utf-8")

    api_circle = {
        e["slug"]: {
            "name": e["name"], "page": f"circle/{e['slug']}.html",
            "shared_transmissions": e["n"], "shared_plays": e["plays"],
            "years_active": e["years"],
            "tracks": [
                {"title": t["title"], "date": t.get("date"), "plays": t.get("plays"), "type": t["type"]}
                for t in sorted(e["tracks"], key=lambda t: t.get("date") or "")
            ],
        }
        for e in entries
    }
    (API / "circle.json").write_text(
        json.dumps(api_circle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Version bump + mirror (same convention as build_codex.py).
    DATA["version"] = NEW_VERSION
    (ROOT / "data" / "artist.json").write_text(
        json.dumps(DATA, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    shutil.copyfile(ROOT / "data" / "artist.json", API / "artist.json")
    idx = json.loads((API / "index.json").read_text())
    idx["version"] = NEW_VERSION
    eps = idx.setdefault("endpoints", {})
    if isinstance(eps, dict):
        eps["circle"] = "api/v1/circle.json"
    (API / "index.json").write_text(
        json.dumps(idx, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"circle: {len(entries)} pages + index + api/v1/circle.json; version -> {NEW_VERSION}")


if __name__ == "__main__":
    main()
