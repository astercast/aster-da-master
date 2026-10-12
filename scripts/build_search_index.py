#!/usr/bin/env python3
"""Build search + on-this-day API artifacts for the Aster da Master site.

Outputs (committed):
  api/v1/release-slugs.json  - discography index -> release page slug
                               (slug logic identical to scripts/build_releases.py)
  api/v1/on-this-day.json    - "MM-DD" -> tracks uploaded/released on that
                               month-day across all years (titles + metadata)

Both are registered in api/v1/index.json. Re-run after any discography change.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
API = ROOT / "api" / "v1"


def build_slugs(releases):
    used = set()
    slugs = []
    for r in releases:
        s = slugify(r["title"])
        base, n = s, 1
        while s in used:
            n += 1
            s = f"{base}-{n}"
        used.add(s)
        slugs.append(s)
    assert len(set(slugs)) == len(releases), "slug collision"
    return slugs


def main():
    releases = DATA["discography"]
    slugs = build_slugs(releases)

    slug_map = {str(i): s for i, s in enumerate(slugs)}
    (API / "release-slugs.json").write_text(
        json.dumps(slug_map, indent=1, ensure_ascii=False) + "\n"
    )

    otd = {}
    for i, r in enumerate(releases):
        date = r.get("date") or ""
        m = re.match(r"^\d{4}-(\d{2})-(\d{2})$", date)
        if not m:
            continue
        key = f"{m.group(1)}-{m.group(2)}"
        otd.setdefault(key, []).append(
            {
                "title": r["title"],
                "date": date,
                "type": r["type"],
                "plays": r.get("plays"),
                "page": f"releases/{slugs[i]}.html",
            }
        )
    for key in otd:
        otd[key].sort(key=lambda t: t["date"])
    (API / "on-this-day.json").write_text(
        json.dumps(otd, indent=1, ensure_ascii=False) + "\n"
    )

    index = json.loads((API / "index.json").read_text())
    index["version"] = "0.13.0"
    from api_manifest import render_manifest
    render_manifest(index, ROOT)

    print(f"release-slugs: {len(slug_map)} entries")
    print(f"on-this-day: {len(otd)} days with transmissions")


if __name__ == "__main__":
    main()
