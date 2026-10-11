#!/usr/bin/env python3
"""Build the Vocabulary Codex from the verified discography.

Reads data/artist.json (219 titles), counts recurring ritual vocabulary
across titles, and emits data/codex.json + api/v1/codex.json.

Method: titles are lowercased and leet-normalized (1->l, 0->o, 3->e,
4->a, 5->s, 7->t) for MATCHING ONLY; single-word keywords match on word
boundaries, multi-word keywords match as phrases. Every claim the codex
makes is a count - no meanings are invented.

Also bumps data version 0.5.0 -> 0.6.0 and mirrors to api/v1/.
"""
import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "artist.json"
CODEX_OUT = ROOT / "data" / "codex.json"
API_OUT = ROOT / "api" / "v1" / "codex.json"
API_ARTIST = ROOT / "api" / "v1" / "artist.json"
API_INDEX = ROOT / "api" / "v1" / "index.json"

LEET = str.maketrans({"1": "l", "0": "o", "3": "e", "4": "a", "5": "s", "7": "t"})


def norm(title):
    return title.lower().translate(LEET)


def tokens(title):
    return set(re.findall(r"[a-z']+", norm(title)))


# (arcane name, ritual epithet (counting claim only), keywords)
FAMILIES = [
    ("The Modes",
     "The mode-words. Five transmissions carry them - lite, nite, and night.",
     ["litemode", "nitemode", "night mode"]),
    ("The Castings",
     "Five transmissions bear the word cast - the central verb of the catalog.",
     ["cast"]),
    ("Keys",
     "Three transmissions turn on a key.",
     ["key"]),
    ("Vessels",
     "Two transmissions name a vessel to drink from - an urn, a cup.",
     ["urn", "cup"]),
    ("Wards & the Spirit",
     "A ward placed. A spirit at peace. Two transmissions of protection.",
     ["ward", "spirit"]),
    ("The Rites",
     "The ceremonial forms: ritual, solstice, freestyle, anthem, intro, outro, interlude.",
     ["ritual", "solstice", "freestyle", "anthem", "intro", "outro", "interlude"]),
    ("Light",
     "Lightning, white fire, sun, gold, and things that shine.",
     ["lightning", "white", "sun", "gold", "shine", "shines"]),
    ("Dark",
     "The night and the dark, named twice over.",
     ["dark", "night"]),
    ("Journeys",
     "Trips taken and a walk offered - the road vocabulary.",
     ["trip", "trips", "walk"]),
    ("The Cold",
     "Four transmissions about the world getting colder - a series unto itself.",
     ["cold", "colder"]),
    ("Power",
     "Power claimed, power denied, power gone.",
     ["power"]),
    ("The Pack",
     "Two transmissions for the dogs.",
     ["dog", "dogs"]),
    ("Lucid States",
     "A lucid boy and a dreamed-of you - the dream vocabulary.",
     ["lucid", "dream", "dreamed"]),
    ("Time",
     "Time to grow. Time, defied.",
     ["time"]),
    ("Soul",
     "Two transmissions carry the soul - one shaking, one shining.",
     ["soul"]),
    ("Fire & Water",
     "White fire. Water and sun. The elements, named once each.",
     ["fire", "water"]),
]


def matches(title, keyword):
    n = norm(title)
    if " " in keyword:
        return keyword in n
    return keyword in tokens(title)


def main():
    data = json.loads(DATA.read_text())
    releases = data["discography"]

    families = []
    for name, epithet, keywords in FAMILIES:
        matched_words = []
        tracks = []
        seen = set()
        for kw in keywords:
            hits = [r for r in releases if matches(r["title"], kw)]
            if hits:
                matched_words.append(kw)
                for r in hits:
                    key = (r["title"], r.get("date"))
                    if key not in seen:
                        seen.add(key)
                        tracks.append({
                            "title": r["title"],
                            "date": r.get("date"),
                            "plays": r.get("plays"),
                            "type": r.get("type", "Release"),
                        })
        if not tracks:
            continue
        tracks.sort(key=lambda t: (t["date"] or "9999", t["title"]))
        families.append({
            "name": name,
            "epithet": epithet,
            "words": matched_words,
            "track_count": len(tracks),
            "tracks": tracks,
        })

    codex = {
        "version": "0.6.0",
        "generated": date.today().isoformat(),
        "method": ("Word-boundary matching over lowercased, leet-normalized titles "
                   "(1->l, 0->o, 3->e, 4->a, 5->s, 7->t); multi-word phrases matched "
                   "as phrases. Counts are of titles containing the word. No meanings invented."),
        "families": families,
    }

    CODEX_OUT.write_text(json.dumps(codex, indent=2, ensure_ascii=False) + "\n")
    API_OUT.write_text(json.dumps(codex, indent=2, ensure_ascii=False) + "\n")
    print(f"codex: {len(families)} families, "
          f"{sum(f['track_count'] for f in families)} family-track links")

    # Bump version + mirror artist.json
    data["version"] = "0.6.0"
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    shutil.copyfile(DATA, API_ARTIST)
    idx = json.loads(API_INDEX.read_text())
    idx["version"] = "0.6.0"
    endpoints = idx.setdefault("endpoints", {})
    if isinstance(endpoints, dict):
        endpoints.setdefault("codex", "api/v1/codex.json")
    API_INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")
    print("version -> 0.6.0; api/v1 mirrored")


if __name__ == "__main__":
    main()
