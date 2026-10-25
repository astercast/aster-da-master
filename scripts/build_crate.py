#!/usr/bin/env python3
"""Build the Crate's public data + the release feed.

Outputs (both published, both number-free by construction):
  data/v1/releases.json - title/date/type/artwork/label/slug per release,
                          artwork resolved own-file > Apple Music (by
                          address, data/art.json) > the record's own
                          artwork. This is the one data file the presented
                          crate reads; it carries no play, stream, like,
                          follower or milestone field of any kind.
  feed.xml              - Atom feed of the same releases, newest first.

Run after data/artist.json or data/art.json changes:
    python3 scripts/build_crate.py
"""
import json
from html import escape as xml_escape
from pathlib import Path

from build_releases import slugify  # single source of truth for slugs

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "artist.json").read_text())
ART = json.loads((ROOT / "data" / "art.json").read_text()) if (ROOT / "data" / "art.json").exists() else {}
ART_DIR = ROOT / "assets" / "art"


def slug_list(releases):
    used, out = set(), []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        out.append(s)
    assert len(set(out)) == len(releases), "slug collision"
    return out


def artwork_for(r, slug):
    """(artwork_url, apple_page_or_None) with the bundle's ladder:
    the artist's own file first, Apple Music by address second, the
    record's own artwork last; nothing is invented."""
    if (ART_DIR / f"{slug}-960.webp").exists():
        return f"/assets/art/{slug}-960.webp", None
    a = ART.get(f'{r["title"]}|{r.get("date")}')
    if a and a.get("source") == "apple":
        return a["base"] + "/600x600bb.jpg", a["page"]
    return r.get("artwork"), None


def main():
    releases = DATA["discography"]
    slugs = slug_list(releases)
    rows = []
    for r, slug in zip(releases, slugs):
        artwork, page = artwork_for(r, slug)
        row = {
            "title": r["title"],
            "date": r.get("date"),
            "type": r["type"],
            "artwork": artwork,
            "label": r.get("label"),
            "slug": slug,
        }
        if page:
            row["artwork_page"] = page
        rows.append(row)
    out = ROOT / "data" / "v1" / "releases.json"
    out.write_text(json.dumps({"discography": rows}, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    newest_first = sorted(rows, key=lambda x: (x["date"] or "", x["title"].lower()),
                          reverse=True)
    updated = (newest_first[0]["date"] or "2017-01-01") + "T00:00:00Z"
    entries = []
    for r in newest_first:
        d = r["date"] or "2017-01-01"
        entries.append(
            "  <entry>\n"
            f"    <title>{xml_escape(r['title'])}</title>\n"
            f'    <link href="/releases/{r["slug"]}.html"/>\n'
            f"    <id>tag:asterdamaster,releases:{r['slug']}</id>\n"
            f"    <updated>{d}T00:00:00Z</updated>\n"
            f"    <summary>{xml_escape(r['type'])} \u00b7 {xml_escape(d)}</summary>\n"
            "  </entry>"
        )
    feed = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        "  <title>Aster da Master - Releases</title>\n"
        '  <link href="/feed.xml" rel="self"/>\n'
        '  <link href="/"/>\n'
        "  <id>tag:asterdamaster,feed:releases</id>\n"
        f"  <updated>{updated}</updated>\n"
        + "\n".join(entries) + "\n</feed>\n"
    )
    (ROOT / "feed.xml").write_text(feed, encoding="utf-8")
    with_art = sum(1 for r in rows if r["artwork"])
    print(f"releases.json: {len(rows)} releases ({with_art} with artwork); feed.xml written")


if __name__ == "__main__":
    main()
