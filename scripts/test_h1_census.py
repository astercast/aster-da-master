#!/usr/bin/env python3
"""Pinned census for duplicate <h1> TEXT across the whole site (Rotation 19).

Rotations 15-18 censused page <title>s, standalone version stamps and
duplicate id attributes; the exactly-one-<h1> sweep (QA-007/QA-008) only
ever COUNTED <h1>s per page. This battery pins the first census of the
<h1> TEXTS themselves, site-wide:

  430 pages carry 430 <h1>s with 420 distinct texts. Exactly 9 texts are
  duplicated, on 19 pages, and every group is legitimate by construction:

  - 8 groups (17 pages) are one person seen from different sections —
    a circle/ collaborator page, a producers/ producer deep dive and/or
    a scene/ 2026-activity page. The <h1> is the person's name verbatim;
    renaming anyone to force uniqueness would falsify the name. The
    pages are told apart by their distinct <title>s and sections.
  - "9 Trips" (2 pages) is two distinct catalog records sharing a real
    title (Rotation 16): their page titles are year-qualified —
    "9 Trips (2023)" / "9 Trips (2026)" — and the <h1> keeps the
    release's real name, exactly as that rotation decided.

Any NEW duplicate group, any change to a pinned group's page set, or two
pages of one group sharing a <title> fails here, so an illegitimate
duplicate <h1> cannot ship silently. The two generators that own most
of these pages (build_circle.py, build_producer_deepdives.py) also
assert <h1>-name uniqueness inside their own family at build time.

Usage: python3 scripts/test_h1_census.py   (exit 0 = all pass)
"""
import html
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name} {detail}")


def clean(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    return html.unescape(re.sub(r"\s+", " ", text).strip())


def page_facts(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    h1s = [clean(m) for m in
           re.findall(r"<h1[^>]*>(.*?)</h1>", text, re.S | re.I)]
    title = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    return h1s, (clean(title.group(1)) if title else "")


pages = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)
rel = {p: str(p.relative_to(ROOT)) for p in pages}
facts = {rel[p]: page_facts(p) for p in pages}

# The pinned legitimate duplicate groups: <h1> text -> exact page set.
EXPECTED_GROUPS = {
    "pvscale": ["circle/pvscale.html", "producers/pvscale.html",
                "scene/pvscale.html"],
    "capoxxo": ["circle/capoxxo.html", "scene/capoxxo-2026.html"],
    "Fish Narc": ["circle/fish-narc.html", "producers/fish-narc.html"],
    "Keyblayde808": ["circle/keyblayde808.html",
                     "producers/keyblayde808.html"],
    "lil soda boi": ["circle/lil-soda-boi.html",
                     "producers/lil-soda-boi.html"],
    "lil yu": ["circle/lil-yu.html", "scene/lil-yu.html"],
    "LILVICBXI": ["circle/lilvicbxi.html", "producers/lilvicbxi.html"],
    "Yung Cortex": ["circle/yung-cortex.html",
                    "producers/yung-cortex.html"],
    "9 Trips": ["releases/9-trips-2.html", "releases/9-trips.html"],
}
PERSON_GROUPS = [name for name in EXPECTED_GROUPS if name != "9 Trips"]

groups = defaultdict(list)
for page, (h1s, _title) in facts.items():
    for h1 in h1s:
        groups[h1].append(page)
duplicates = {name: sorted(ps) for name, ps in groups.items() if len(ps) > 1}

# --- aggregate counts -------------------------------------------------------
check("page-count", len(pages) == 430, f"got {len(pages)}")
check("exactly-one-h1-per-page",
      all(len(h1s) == 1 for h1s, _ in facts.values()),
      f"pages without exactly one h1: "
      f"{[p for p, (h, _) in facts.items() if len(h) != 1][:5]}")
check("distinct-h1-texts", len(groups) == 420, f"got {len(groups)}")
check("duplicate-group-count", len(duplicates) == 9,
      f"got {len(duplicates)}: {sorted(duplicates)}")

# --- each legitimate group, pinned page-for-page ----------------------------
for name, expected in EXPECTED_GROUPS.items():
    check(f"group-pin:{name}", duplicates.get(name) == sorted(expected),
          f"got {duplicates.get(name)}")

# --- legitimacy conditions ---------------------------------------------------
check("group-titles-distinct",
      all(len({facts[p][1] for p in ps}) == len(ps)
          for ps in duplicates.values()),
      "two pages in a duplicate group share a <title>")
check("person-groups-cross-section",
      all(len({p.split('/')[0] for p in EXPECTED_GROUPS[name]}) ==
          len(EXPECTED_GROUPS[name]) for name in PERSON_GROUPS),
      "a person group repeats a section family")
trips_titles = {p: facts[p][1] for p in EXPECTED_GROUPS["9 Trips"]}
check("nine-trips-year-qualified-titles",
      trips_titles.get("releases/9-trips.html") ==
      "9 Trips (2026) — Aster da Master" and
      trips_titles.get("releases/9-trips-2.html") ==
      "9 Trips (2023) — Aster da Master",
      f"got {trips_titles}")

# No directory (section family) may repeat an <h1> text internally, with
# the single pinned exception of the two "9 Trips" release pages.
intra = []
for name, ps in duplicates.items():
    dirs = [p.rsplit("/", 1)[0] if "/" in p else "." for p in ps]
    if len(set(dirs)) != len(dirs) and not (
            name == "9 Trips" and set(dirs) == {"releases"}):
        intra.append(name)
check("no-intra-family-duplicates", not intra, f"got {intra}")

print(f"\ntest_h1_census: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
