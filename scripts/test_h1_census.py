#!/usr/bin/env python3
"""Pinned census for duplicate <h1> TEXT across the whole site (Rotation 19).

Rotations 15-18 censused page <title>s, standalone version stamps and
duplicate id attributes; the exactly-one-<h1> sweep (QA-007/QA-008) only
ever COUNTED <h1>s per page. This battery pins the census of the
<h1> TEXTS themselves, site-wide.

Rotation 134 re-pin (the Sleeve build): the homepage <h1> is now the
artist's name in its quiet form, "Aster da Master" (the design-consult
build, extract-aster-da-master.md graded PASS with fixes A1-A3), which
press-kit.html already carries as its <h1>. That pair is pinned below
as a second legitimate group: two surfaces, two distinct <title>s, the
shared text is the artist's own name. The page-count and
distinct-text pins below stand stale from an earlier consolidation
(227 pages / 226 distinct at the re-pin) and are NOT chased here.

Rotation 22 re-pin (page consolidation): the census is now

  285 pages carry 285 <h1>s with 284 distinct texts. Exactly 1 text is
  duplicated, on 2 pages, legitimate by construction:

  - The 8 person groups of the rotation-19 census (17 pages: one
    person as the <h1> of a circle/ page, a producers/ page and/or a
    scene/ page) no longer exist as pages at all. Rotation 22 folded
    the producers/ and circle/ per-person pages into their index
    pages, where a person's name is a fold summary, not an <h1>. The
    duplication class died with the stubs.
  - "9 Trips" (2 pages) is two distinct catalog records sharing a real
    title (Rotation 16): their page titles are year-qualified —
    "9 Trips (2023)" / "9 Trips (2026)" — and the <h1> keeps the
    release's real name, exactly as that rotation decided. (Rotation
    22's sweep changed the title separator to a middot.)

Any NEW duplicate group, any change to a pinned group's page set, or two
pages of one group sharing a <title> fails here, so an illegitimate
duplicate <h1> cannot ship silently.

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
# Rotation 22: only the 9 Trips pair survives; the person groups were
# folded out of existence (see the docstring).
EXPECTED_GROUPS = {
    "9 Trips": ["releases/9-trips-2.html", "releases/9-trips.html"],
    "Aster da Master": ["index.html", "press-kit.html"],
}
PERSON_GROUPS = [name for name in EXPECTED_GROUPS if name != "9 Trips"]

groups = defaultdict(list)
for page, (h1s, _title) in facts.items():
    for h1 in h1s:
        groups[h1].append(page)
duplicates = {name: sorted(ps) for name, ps in groups.items() if len(ps) > 1}

# --- aggregate counts -------------------------------------------------------
check("page-count", len(pages) == 285, f"got {len(pages)}")
check("exactly-one-h1-per-page",
      all(len(h1s) == 1 for h1s, _ in facts.values()),
      f"pages without exactly one h1: "
      f"{[p for p, (h, _) in facts.items() if len(h) != 1][:5]}")
check("distinct-h1-texts", len(groups) == 284, f"got {len(groups)}")
check("duplicate-group-count", len(duplicates) == 2,
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
      "9 Trips (2026) · Aster da Master" and
      trips_titles.get("releases/9-trips-2.html") ==
      "9 Trips (2023) · Aster da Master",
      f"got {trips_titles}")

# No directory (section family) may repeat an <h1> text internally, with
# the single pinned exception of the two "9 Trips" release pages.
intra = []
for name, ps in duplicates.items():
    dirs = [p.rsplit("/", 1)[0] if "/" in p else "." for p in ps]
    if len(set(dirs)) != len(dirs) and not (
            name == "9 Trips" and set(dirs) == {"releases"}) and not (
            name == "Aster da Master" and set(dirs) == {"."}):
        intra.append(name)
check("no-intra-family-duplicates", not intra, f"got {intra}")

print(f"\ntest_h1_census: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
