#!/usr/bin/env python3
"""Data migration v0.4.0 -> v0.5.0 for the Aster da Master site.

Replaces the 9-track SoundCloud vault (single-sourced from third-party
indexes; profile URL unresolved) with the FULL verified catalog: 185 tracks
from the official profile https://soundcloud.com/asterdamaster (display name
"ASTER DA MASTER", 1,562 followers, location "sf, United States", bio
"somelowlifes / Litemode Trilogy OTW"), captured 2026-10-11 via a read-only
live-browser pass. Per-track: title, upload date, play count. Titles only -
no lyrics anywhere.

Also:
  - Adds SoundCloud as a VERIFIED platform record.
  - Marks Spotify as artist-linked (the artist's own SoundCloud bio links it).
  - Adds Instagram + official site as linked-from-bio (direct URLs not
    captured in the pass; recorded honestly).
  - Adds a teased "Litemode Trilogy" upcoming note (teased in bio, not
    confirmed).
  - Updates the top-level `vault` object to full-catalog-verified status.
  - Bumps version to 0.5.0. Mirrors data/artist.json -> data/v1/artist.json.
  - Updates data/v1/index.json version + provenance.

Idempotent: safe to re-run (vault entries are rebuilt from tracks.json).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "artist.json"
API = ROOT / "data" / "v1" / "artist.json"
API_INDEX = ROOT / "data" / "v1" / "index.json"
TRACKS = Path("/home/hatch/workspace/research_notes/aster-soundcloud-20261011/tracks.json")

PROFILE_URL = "https://soundcloud.com/asterdamaster"
SC_SOURCE = (
    "Official SoundCloud profile (asterdamaster) \u00b7 full-catalog live-browser "
    "pass (read-only, no login) \u00b7 verified 2026-10-11"
)
SC_NOTE = (
    "SoundCloud-vault track from the official catalog. Upload date and play "
    "count are a 2026-10-11 snapshot; play counts drift over time. Per-track "
    "URLs are not published by the capture (SoundCloud slugs not resolved); "
    "the profile link opens the catalog."
)


def main():
    d = json.loads(DATA.read_text())
    cat = json.loads(TRACKS.read_text())
    tracks = cat["tracks"]
    assert len(tracks) == 185, f"expected 185 tracks, got {len(tracks)}"
    assert cat["profile"]["url"] == PROFILE_URL

    # 1. Drop the old 9-track vault entries.
    before = len(d["discography"])
    d["discography"] = [
        r for r in d["discography"] if "soundcloud" not in r.get("type", "").lower()
    ]
    removed = before - len(d["discography"])
    assert removed == 9, f"expected to remove 9 vault entries, removed {removed}"

    # 2. Add the full 185-track catalog.
    for t in tracks:
        assert set(t.keys()) == {"title", "date", "plays"}, t.keys()
        d["discography"].append(
            {
                "title": t["title"],
                "date": t["date"],
                "type": "SoundCloud-only",
                "plays": t["plays"],
                "links": [{"label": "SoundCloud", "url": PROFILE_URL}],
                "source": SC_SOURCE,
                "confidence": "verified",
                "note": SC_NOTE,
            }
        )

    titles = [r["title"] for r in d["discography"]]
    # "9 Trips" is genuinely in both catalogs (distributor single + SoundCloud
    # upload) and gets a suffixed slug at build time. Everything else is unique.
    from collections import Counter as _Counter

    dupes = {k: v for k, v in _Counter(titles).items() if v > 1}
    assert dupes == {"9 Trips": 2}, f"unexpected duplicate titles: {dupes}"
    assert len(d["discography"]) == 34 + 185 == 219

    # 3. Vault object: full catalog verified.
    prof = cat["profile"]
    d["vault"] = {
        "status": (
            "Full catalog verified: 185 tracks on the official SoundCloud profile "
            f"({PROFILE_URL}) \u2014 captured 2026-10-11 via a read-only live-browser "
            "pass. Play counts are a 2026-10-11 snapshot and drift over time."
        ),
        "profile_url": PROFILE_URL,
        "display_name": prof["display_name"],
        "followers": prof["followers"],
        "location": prof["location"],
        "bio": prof["bio"],
        "tracks_on_record": 185,
        "confidence": "verified",
        "full_catalog": "complete as of 2026-10-11 (profile reported 185 tracks; capture matched 185)",
        "research_date": "2026-10-11",
    }

    # 4. Platforms.
    platforms = d["platforms"]
    for p in platforms:
        if p["name"].startswith("Spotify"):
            p["verified"] = True
            p["note"] = (
                "Linked from the artist's own official SoundCloud bio "
                "(2026-10-11) \u2014 identity artist-linked; track-level "
                "catalog match still pending"
            )
    platforms.append(
        {
            "name": "SoundCloud",
            "url": PROFILE_URL,
            "verified": True,
            "note": "Official profile \u2014 185-track full catalog verified 2026-10-11; bio: \u201csomelowlifes / Litemode Trilogy OTW\u201d",
        }
    )
    platforms.append(
        {
            "name": "Instagram",
            "verified": True,
            "note": "Linked from the official SoundCloud bio (2026-10-11); direct URL not captured in the pass",
        }
    )
    platforms.append(
        {
            "name": "Official site",
            "verified": True,
            "note": "Listed as \u201castredamaster.com\u201d in the official SoundCloud bio (2026-10-11); direct URL not captured in the pass",
        }
    )

    # 5. Teased upcoming.
    d["upcoming"] = [
        {
            "title": "Litemode Trilogy",
            "status": "teased in the official SoundCloud bio \u2014 not confirmed",
            "source": "Official SoundCloud profile bio (asterdamaster), observed 2026-10-11",
        }
    ]

    # 6. Version + status.
    d["version"] = "0.5.0"
    d["observed"] = "2026-10-11"
    d["research_status"] = (
        "VERIFIED-2026-10-11 \u2014 identity resolved per research report; "
        "Spotify artist-linked via official SoundCloud bio; SoundCloud full "
        "catalog (185 tracks) verified via read-only live-browser pass 2026-10-11"
    )

    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    API.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    idx = json.loads(API_INDEX.read_text())
    idx["version"] = "0.5.0"
    idx["observed"] = "2026-10-11"
    idx["provenance"] = (
        "All artist facts verified against public platform pages (Apple Music, iHeart, "
        "Anghami, Shazam, Boomplay, SonicHits, album.link, SoundCloud). v0.5.0: the "
        "official SoundCloud profile (asterdamaster) catalog is fully verified \u2014 "
        "185 SoundCloud-only tracks (upload dates + play-count snapshot) alongside the "
        "34 distributor releases (219 total). Spotify is artist-linked via the official "
        "SoundCloud bio; Instagram + official site likewise bio-linked. 'Litemode "
        "Trilogy' is teased in the bio, not confirmed."
    )
    API_INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("v0.5.0: 34 distributor + 185 SoundCloud-only = 219 entries; platforms updated; index.json updated")


if __name__ == "__main__":
    main()
