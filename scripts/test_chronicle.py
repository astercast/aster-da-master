#!/usr/bin/env python3
"""Pinned-fixture tests for the chronicle pure logic
(scripts/build_chronicle.py): era-by-year mapping + chronological ordering.

Run: python3 scripts/test_chronicle.py  (exit 0 = all pass)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from build_chronicle import era_for_year, event_sort_key  # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


# --- era_for_year: calendar year -> era; 2017 predates the eras ---
check("2017 -> pre-era", era_for_year(2017) == (None, "Before the vault"))
check("2018 -> the-first-rite", era_for_year(2018)[0] == "the-first-rite")
check("2019 -> the-first-rite", era_for_year(2019)[0] == "the-first-rite")
check("2020 -> the-prolific-year", era_for_year(2020)[0] == "the-prolific-year")
check("2021 -> the-cast-it-years", era_for_year(2021)[0] == "the-cast-it-years")
check("2022 -> the-cast-it-years", era_for_year(2022)[0] == "the-cast-it-years")
check("2023 -> the-somelowlifes-era",
      era_for_year(2023)[0] == "the-somelowlifes-era")
check("2024 -> the-somelowlifes-era",
      era_for_year(2024)[0] == "the-somelowlifes-era")
check("2025 -> the-silence", era_for_year(2025)[0] == "the-silence")
check("2026 -> the-return", era_for_year(2026)[0] == "the-return")


def ev(date, kind, title="t"):
    return {"date": date, "kind": kind, "title": title}


# --- event_sort_key: date, then milestone -> session -> collaboration ---
same_day = [ev("2020-01-01", "collaboration", "z"),
            ev("2020-01-01", "session", "a"),
            ev("2020-01-01", "milestone", "m")]
ordered = sorted(same_day, key=event_sort_key)
check("same-date kind order",
      [e["kind"] for e in ordered] == ["milestone", "session", "collaboration"])
check("date dominates kind",
      sorted([ev("2021-01-01", "milestone"), ev("2020-01-01", "collaboration")],
             key=event_sort_key)[0]["kind"] == "collaboration")
check("title breaks same-date same-kind ties",
      sorted([ev("2020-01-01", "session", "b"), ev("2020-01-01", "session", "a")],
             key=event_sort_key)[0]["title"] == "a")

print(f"test_chronicle: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
