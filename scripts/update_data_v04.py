#!/usr/bin/env python3
"""Data migration v0.3.0 -> v0.4.0 for the Aster da Master site.

1. Adds a `source` provenance string to each of the 34 distributor releases.
   Per research report 2026-10-11: all 34 came from Apple Music artist profile
   1466301103 ("Aster Da Master") via the iTunes Search API primary metadata.
   Profile B (1369059395, "AsterDaMaster") holds only "Gravestone - Single"
   (2018-04-27) and a feature credit, neither of which is in this 34-release
   catalog, so no entry here carries the alt profile.
2. Appends the 9 SoundCloud-vault tracks surfaced by the 2026-10-11
   SoundCloud research from third-party indexes of his uploads. The profile URL
   itself was NOT found via public web research; every vault entry is
   confidence "single-source", date unknown, upload date/play counts unknown.
   Titles only - no lyrics anywhere.
3. Adds a top-level `vault` status object. Bumps version to 0.4.0.
4. Mirrors data/artist.json -> api/v1/artist.json.

Idempotent: safe to re-run (vault titles are matched by title+type).
"""
import json, copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "artist.json"
API = ROOT / "api" / "v1" / "artist.json"

DIST_SOURCE = "Apple Music profile 1466301103 (\u201cAster Da Master\u201d) \u00b7 iTunes Search API primary metadata \u00b7 verified 2026-10-11"

VAULT_TRACKS = [
    {
        "title": "All Kinds of Trips",
        "index": "SonicHits video index of his SoundCloud uploads",
    },
    {
        "title": "Best Friend",
        "index": "SonicHits video index of his SoundCloud uploads",
    },
    {
        "title": "Playin' by the Book",
        "index": "SonicHits video index of his SoundCloud uploads",
    },
    {
        "title": "White Noise",
        "index": "SonicHits video index of his SoundCloud uploads",
    },
    {
        "title": "candy w/ capoxxo (prod. razorwrist)",
        "index": "SonicHits video index of his SoundCloud uploads; producer credit also in main research report",
    },
    {
        "title": "fly like me w/ pvscale (prod. pvscale)",
        "index": "SonicHits video index of his SoundCloud uploads (distributor catalog has \"Fly Like Me (feat. Pvscale)\" - the w/-style upload is the SoundCloud version)",
    },
    {
        "title": "take me",
        "index": "letras.top / azlyrics.biz sitemaps and lirik.web.id title page (titles only - lyrics not reproduced)",
    },
    {
        "title": "(Memory Loaded October 600 & Aster Da Master)",
        "index": "Shazam \"Top Songs By Aster Da Master\" listing - SoundCloud collab upload",
    },
    {
        "title": "InternetWouldBlush (ft. Offline HP, Aster Da Master, & DirtyDoves) [prod. Lil' Flower]",
        "index": "Internet Phantoms Network podcast Ep. 9 song list (feature on Lil' Spursy's upload)",
        "citations": [
            {"label": "Internet Phantoms Network Ep. 9 song list", "url": "https://audioboom.com/posts/7580249"},
            {"label": "SonicHits artist video index", "url": "https://sonichits.com/artist/Aster_Da_Master"},
        ],
    },
]

VAULT_NOTE = (
    "SoundCloud-vault track: surfaced from third-party indexes of his SoundCloud uploads, "
    "not from distributor metadata. Upload date and play counts unknown (require in-platform access). "
    "Profile URL not found via public web research as of 2026-10-11."
)


def main():
    d = json.loads(DATA.read_text())
    assert d["version"] in ("0.3.0", "0.4.0"), d["version"]

    # 1. provenance on the 34 distributor releases
    for e in d["discography"]:
        if e["type"] in ("Album", "Single") and "source" not in e:
            e["source"] = DIST_SOURCE

    # 2. vault tracks (idempotent)
    existing = {(e["title"], e["type"]) for e in d["discography"]}
    for v in VAULT_TRACKS:
        if (v["title"], "SoundCloud-only") in existing:
            continue
        entry = {
            "title": v["title"],
            "date": None,
            "type": "SoundCloud-only",
            "links": [],
            "source": v["index"] + " \u00b7 verified 2026-10-11",
            "confidence": "single-source",
            "note": VAULT_NOTE,
        }
        if v.get("citations"):
            entry["citations"] = v["citations"]
        d["discography"].append(entry)

    # 3. top-level vault status
    d["vault"] = {
        "status": (
            "SoundCloud profile URL not found via public web research (2026-10-11); "
            "9 titles surfaced from third-party indexes of his uploads. Full track count "
            "unknown - requires in-platform access or the artist's own handle."
        ),
        "tracks_on_record": 9,
        "confidence": "single-source",
        "full_catalog": "unverified - the 9 titles below are a confirmed-minimum sample, not a complete catalog",
        "research_date": "2026-10-11",
    }
    d["version"] = "0.4.0"
    d["research_status"] = (
        "VERIFIED-2026-10-11 - identity resolved per research report; Spotify profile unverified; "
        "SoundCloud profile URL unresolved - 9 vault tracks single-sourced from third-party upload indexes"
    )

    DATA.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    API.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

    # sanity: no lyric content. Only allowed occurrences of the substring are
    # "lirik.web.id" (a source domain) and the explicit "lyrics not reproduced" note.
    import re
    text = json.dumps(d).lower()
    for m in re.finditer(r"lyric", text):
        ctx = text[max(0, m.start() - 60):m.end() + 60]
        assert "lirik.web.id" in ctx or "lyrics not reproduced" in ctx, f"lyric leak check: {ctx!r}"
    dist = [e for e in d["discography"] if e["type"] in ("Album", "Single")]
    vault = [e for e in d["discography"] if e["type"] == "SoundCloud-only"]
    assert len(dist) == 34 and all("source" in e for e in dist)
    assert len(vault) == 9
    print(f"v0.4.0: {len(dist)} distributor releases + {len(vault)} vault tracks; API mirror synced.")


if __name__ == "__main__":
    main()
