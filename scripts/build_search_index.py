#!/usr/bin/env python3
"""Build search + on-this-day API artifacts for the Aster da Master site.

Outputs (committed):
  data/v1/release-slugs.json  - discography index -> release page slug
                               (slug logic identical to scripts/build_releases.py)
  data/v1/on-this-day.json    - "MM-DD" -> tracks uploaded/released on that
                               month-day across all years (titles + metadata)

Both are registered in data/v1/index.json. Re-run after any discography change.

This generator does not own the data version: it preserves whatever
version data/v1/index.json already carries (the version-writing
generators own it), exactly as build_changelog / build_firstlast /
build_transmission do. It must never stamp its own version constant —
a standalone run once wrote a stale hand-kept version back over the
chain's current one (retired Rotation 17); the assert in main() keeps
that class from returning silently.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_releases import slugify  # noqa: E402  (single source of truth)

DATA = json.loads((ROOT / "data" / "artist.json").read_text())
API = ROOT / "data" / "v1"


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
    # Preserve the current data version — never stamp a second,
    # hand-kept constant here (see module docstring). The version is
    # derived from the manifest on disk, so a standalone run produces
    # exactly what the validate.sh chain produces.
    version_before = index.get("version")
    assert version_before, "data/v1/index.json carries no version to preserve"
    from api_manifest import render_manifest
    render_manifest(index, ROOT)
    version_after = json.loads((API / "index.json").read_text()).get("version")
    assert version_after == version_before, (
        f"search-index build changed the data version "
        f"({version_before} -> {version_after}); this generator does "
        f"not own the version and must preserve it"
    )

    print(f"release-slugs: {len(slug_map)} entries")
    print(f"on-this-day: {len(otd)} days with transmissions")


if __name__ == "__main__":
    main()
