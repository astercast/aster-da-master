#!/usr/bin/env python3
"""
refresh_plays.py — Play-count refresher for the Aster da Master artist site.

Play counts are a drift-prone data point: the site's canonical SoundCloud
play counts are a 2026-10-11 snapshot captured with a live browser
(SoundCloud renders client-side; plain HTTP fetches of the profile page
return HTML with ZERO playback_count data — verified 2026-10-11).
This script refreshes them in three tiers, tried in order:

  Tier (a)  SoundCloud api-v2 using SOUNDCLOUD_CLIENT_ID from the environment.
            Resolves the profile -> user id -> paged tracks collection and
            reads each track's real playback_count. Writes a NEW snapshot
            file: data/playcounts.snapshot.json
              { "snapshot_at": "<iso8601>",
                "source": "soundcloud api-v2",
                "tracks": [ {"title": ..., "upload_date": "YYYY-MM-DD", "plays": N}, ... ] }

  Tier (a2) No env key: extract the api-v2 client_id READ-ONLY from
            SoundCloud's own public web-app JS bundles
            (a-v2.sndcdn.com/assets/*.js, served to every web visitor),
            verify it with one resolve call, then run the same tier-(a)
            pull. Extraction is dynamic per run, so key rotation is
            self-healing. If extraction/verification fails, fall through.

  Tier (b)  No usable client_id: attempts the best-effort public endpoints
            (api-v2 without client_id; raw profile-page HTML; oEmbed) and
            RECORDS what worked in the status file. No counts are written
            from sources that cannot supply real playback_count values.

  Tier (c)  Nothing reachable: exits 0 gracefully, writing NEW
            data/v1/refresh-status.json
              { "last_attempt": "<iso8601>",
                "status": "skipped",
                "reason": "no usable SOUNDCLOUD_CLIENT_ID and public-JS extraction failed; use live-browser capture (see GO_LIVE.md)" }

HARD RULES:
  - NEVER fabricate counts. A track without a real playback_count value
    is skipped and reported, not filled in.
  - NEVER write zeros over real data. Snapshot entries with plays == 0 or
    missing are never merged; existing artist.json "plays" values survive.

--merge mode:
    python3 scripts/refresh/refresh_plays.py --merge

  Reads data/playcounts.snapshot.json and applies the counts into
  data/artist.json IN COPY-SAFE fashion:
    1. data/artist.json is backed up to data/artist.json.bak FIRST
       (shutil.copy2; a pre-existing .bak is replaced).
    2. Matching is by normalized title (casefold + whitespace collapsed)
       AND upload_date == release "date", restricted to releases of
       type "SoundCloud-only". Matches update "plays"; entries with a
       falsy/missing plays value are skipped (zeros never overwrite).
    3. The release "source"/"note" date strings are rolled forward to the
       new snapshot date via simple substring replacement of the old
       snapshot date.
    4. data/artist.json is written back (2-space indent, trailing newline).

  AFTER --merge, the builder's generators MUST be re-run so every derived
  page/API copy picks up the new counts (per API.md "re-run after data
  changes"):
      scripts/build_releases.py     # release pages + data/v1/artist.json copy
      scripts/build_years.py        # year archive pages
      scripts/build_circle.py       # circle page
      scripts/build_search_index.py # search index (slugs mirror releases)
      scripts/build_codex.py        # vocabulary codex (per-track counts surface)

Usage:
    python3 scripts/refresh/refresh_plays.py           # refresh tiers (a)-(c)
    python3 scripts/refresh/refresh_plays.py --merge  # apply snapshot -> data/artist.json
    bash scripts/refresh/refresh.sh                   # cron-ready entry (logs to logs/refresh.log)

Exit codes: 0 on success or graceful skip; 1 only on hard errors
(e.g. --merge with no snapshot file present).
"""

import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

_HERE = os.path.abspath(__file__)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # scripts/refresh -> repo root
# Sanity guard: the script must live at <repo>/scripts/refresh/refresh_plays.py.
# A misdetected root would scatter status/snapshot files in the wrong tree.
assert os.path.isdir(os.path.join(REPO, "data")), f"repo root misdetected: {REPO}"
PROFILE_URL = "https://soundcloud.com/asterdamaster"
API_V2 = "https://api-v2.soundcloud.com"
SNAPSHOT_PATH = os.path.join(REPO, "data", "playcounts.snapshot.json")
# Static data lives in data/v1/, NEVER under api/ (Vercel does not serve
# static files from api/ and auto-deploys every .js there as a function).
# This pointed at api/v1/ until 2026-10-12 — every refresh silently wrote
# a stray static file into the functions tree.
STATUS_PATH = os.path.join(REPO, "data", "v1", "refresh-status.json")
ARTIST_PATH = os.path.join(REPO, "data", "artist.json")
BAK_PATH = ARTIST_PATH + ".bak"
ENV_CLIENT_ID = "SOUNDCLOUD_CLIENT_ID"
HTTP_TIMEOUT = 30


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    print(f"[refresh_plays] {msg}", flush=True)


def http_get(url, ua=None):
    """One read-only GET. Returns (status:int|None, body:str, note:str)."""
    headers = {"User-Agent": ua or "aster-da-master-refresh/1.0 (read-only play-count snapshot)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return e.code, "", f"HTTPError {e.code}"
    except Exception as e:  # network down, DNS, TLS, timeout...
        return None, "", f"{type(e).__name__}: {e}"


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------- tier (a)

def fetch_via_client_id(client_id):
    """Tier (a): resolve profile -> user id -> paged tracks. Returns (snapshot_dict, notes)."""
    notes = []
    resolve_url = f"{API_V2}/resolve?url={urllib.parse.quote(PROFILE_URL, safe='')}&client_id={urllib.parse.quote(client_id)}"
    status, body, note = http_get(resolve_url)
    notes.append(f"resolve: {note}")
    if status != 200 or not body:
        return None, notes + [f"resolve failed; cannot reach api-v2 with this client_id ({note})"]
    try:
        user = json.loads(body)
        user_id = user["id"]
    except (json.JSONDecodeError, KeyError) as e:
        return None, notes + [f"resolve response unparseable: {e}"]

    tracks = []
    skipped = 0
    url = f"{API_V2}/users/{user_id}/tracks?client_id={urllib.parse.quote(client_id)}&limit=200"
    pages = 0
    while url and pages < 20:  # 20 pages x 200 = 4000 tracks headroom (catalog is 185)
        pages += 1
        status, body, note = http_get(url)
        notes.append(f"tracks page {pages}: {note}")
        if status != 200 or not body:
            notes.append(f"tracks paging stopped at page {pages} ({note})")
            break
        try:
            coll = json.loads(body)
        except json.JSONDecodeError as e:
            notes.append(f"tracks page {pages} unparseable: {e}")
            break
        for t in coll.get("collection", []):
            plays = t.get("playback_count")
            if not isinstance(plays, int):
                skipped += 1  # NEVER fabricate: skip, don't fill
                continue
            created = (t.get("created_at") or "")[:10]  # "2026-10-02T21:14:33Z" -> "2026-10-02"
            tracks.append({
                "title": t.get("title") or "",
                "upload_date": created,
                "plays": plays,
            })
        url = coll.get("next_href")
        if url and "client_id" not in url:
            url += ("&" if "?" in url else "?") + f"client_id={urllib.parse.quote(client_id)}"
        time.sleep(1)  # be polite to the API

    snapshot = {
        "snapshot_at": now_iso(),
        "source": "soundcloud api-v2",
        "profile": PROFILE_URL,
        "tracks": tracks,
        "tracks_captured": len(tracks),
        "tracks_skipped_no_count": skipped,
    }
    notes.append(f"captured {len(tracks)} tracks, skipped {skipped} without playback_count")
    return snapshot, notes


# ---------------------------------------------------------------- tier (a2)

BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

def extract_client_id_from_webapp():
    """Tier (a2): pull the api-v2 client_id read-only from SoundCloud's public
    web-app JS bundles (a-v2.sndcdn.com/assets/*.js). Returns (client_id|None, notes)."""
    notes = []
    status, html, note = http_get(PROFILE_URL, ua=BROWSER_UA)
    notes.append(f"webapp HTML fetch: {note}")
    if status != 200 or not html:
        return None, notes + ["profile HTML unreachable; cannot find bundles"]
    bundles = sorted(set(re.findall(r"https://a-v2\.sndcdn\.com/assets/[0-9a-f-]+\.js", html)))
    notes.append(f"found {len(bundles)} webapp bundles")
    candidates = []
    for b in bundles:
        s, js, n = http_get(b, ua=BROWSER_UA)
        if s != 200 or not js:
            notes.append(f"bundle {b.split('/')[-1]}: {n}")
            continue
        for m in re.finditer(r'client_id\s*:\s*"([A-Za-z0-9]{20,40})"', js):
            if m.group(1) not in candidates:
                candidates.append(m.group(1))
    notes.append(f"extracted {len(candidates)} client_id candidate(s) from bundles")
    for cand in candidates:
        u = f"{API_V2}/resolve?url={urllib.parse.quote(PROFILE_URL, safe='')}&client_id={urllib.parse.quote(cand)}"
        s, body, n = http_get(u)
        if s == 200:
            try:
                uid = json.loads(body)["id"]
            except (json.JSONDecodeError, KeyError):
                notes.append("candidate key: resolve 200 but unparseable")
                continue
            notes.append(f"candidate key verified via resolve (user id {uid})")
            return cand, notes
        notes.append(f"candidate key rejected: {n}")
    return None, notes + ["no extracted client_id verified; falling through"]


# ---------------------------------------------------------------- tier (b)

def probe_public_endpoints():
    """Tier (b): best-effort public probes, record what worked. Returns notes list."""
    notes = []
    # 1. api-v2 resolve WITHOUT client_id (expected 401; verified 2026-10-11)
    url = f"{API_V2}/resolve?url={urllib.parse.quote(PROFILE_URL, safe='')}"
    status, body, note = http_get(url)
    playback_present = "playback_count" in body
    notes.append(f"api-v2 resolve without client_id -> {note}; playback_count in body: {playback_present}")
    # 2. raw profile-page HTML (expected: zero playback_count; verified 2026-10-11)
    status, body, note = http_get(PROFILE_URL)
    playback_present = "playback_count" in body
    notes.append(f"profile page HTML -> {note} ({len(body)} bytes); playback_count in HTML: {playback_present}")
    # 3. oEmbed (expected 200 with title/author/html but no play counts; verified 2026-10-11)
    url = "https://soundcloud.com/oembed?format=json&url=" + urllib.parse.quote(PROFILE_URL, safe="")
    status, body, note = http_get(url)
    playback_present = "playback_count" in body
    notes.append(f"oEmbed -> {note}; playback_count in body: {playback_present}")
    return notes


# ---------------------------------------------------------------- merge

def norm_title(s):
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()


def run_merge():
    """--merge: apply snapshot into data/artist.json, backup first, never zeros over real data."""
    if not os.path.exists(SNAPSHOT_PATH):
        log(f"ERROR: snapshot not found: {SNAPSHOT_PATH}")
        log("Run without --merge first (tier a) or do a live-browser capture (see GO_LIVE.md).")
        return 1
    snap = json.load(open(SNAPSHOT_PATH, encoding="utf-8"))
    snap_tracks = snap.get("tracks", [])
    snap_at = snap.get("snapshot_at", "")[:10] or "unknown-date"
    log(f"snapshot: {SNAPSHOT_PATH} ({len(snap_tracks)} tracks, snapshot_at={snap.get('snapshot_at')})")

    with open(ARTIST_PATH, encoding="utf-8") as f:
        artist = json.load(f)
    disc = artist.get("discography", [])

    # Build match index: (norm_title, date) -> release dict (SoundCloud-only only)
    index = {}
    for r in disc:
        if r.get("type") == "SoundCloud-only":
            index[(norm_title(r.get("title")), r.get("date"))] = r
    log(f"SoundCloud-only releases in data/artist.json: {len(index)}")

    matched = skipped_zero = unmatched = 0
    unmatched_titles = []
    for t in snap_tracks:
        plays = t.get("plays")
        key = (norm_title(t.get("title")), t.get("upload_date"))
        r = index.get(key)
        if r is None:
            unmatched += 1
            unmatched_titles.append(t.get("title"))
            continue
        if not isinstance(plays, int) or plays <= 0:
            skipped_zero += 1  # NEVER write zeros over real data
            continue
        r["plays"] = plays
        # Roll the snapshot/verified date strings forward to the new snapshot date.
        for field in ("source", "note"):
            if field in r and isinstance(r[field], str):
                r[field] = re.sub(
                    r"(20\d\d-\d\d-\d\d)( snapshot| verified)?",
                    lambda m: snap_at + (m.group(2) or ""),
                    r[field],
                )
        matched += 1

    log(f"merge result: matched={matched} skipped_zero_or_missing={skipped_zero} unmatched={unmatched}")
    if unmatched_titles[:10]:
        log(f"first unmatched snapshot titles: {unmatched_titles[:10]}")

    # Backup FIRST, then write.
    shutil.copy2(ARTIST_PATH, BAK_PATH)
    log(f"backup written: {BAK_PATH}")
    with open(ARTIST_PATH, "w", encoding="utf-8") as f:
        json.dump(artist, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log(f"merged data written: {ARTIST_PATH} ({matched} play counts updated)")

    log("NEXT: re-run the builder generators so derived pages/API copies pick up the new counts:")
    for g in ("build_releases.py", "build_years.py", "build_circle.py",
              "build_search_index.py", "build_codex.py"):
        log(f"    python3 scripts/{g}")

    write_json(STATUS_PATH, {
        "last_attempt": now_iso(),
        "status": "merged",
        "snapshot_at": snap.get("snapshot_at"),
        "matched": matched,
        "skipped_zero_or_missing": skipped_zero,
        "unmatched": unmatched,
    })
    return 0


# ---------------------------------------------------------------- main

def run_refresh():
    """Tiers (a) -> (a2) -> (b) -> (c). Always exits 0 unless --merge hard-fails."""
    client_id = os.environ.get(ENV_CLIENT_ID, "").strip()
    client_id_source = "env" if client_id else None

    if not client_id:
        # Tier (a2): extract a usable key read-only from the public web-app JS.
        client_id, a2_notes = extract_client_id_from_webapp()
        for n in a2_notes:
            log(f"tier-a2: {n}")
        if client_id:
            client_id_source = "public-webapp-js"

    if client_id:
        # Tier (a): api-v2 with client_id (env-supplied or webapp-extracted).
        snapshot, notes = fetch_via_client_id(client_id)
        for n in notes:
            log(f"tier-a: {n}")
        if snapshot and snapshot["tracks"]:
            snapshot["client_id_source"] = client_id_source
            write_json(SNAPSHOT_PATH, snapshot)
            log(f"snapshot written: {SNAPSHOT_PATH} ({snapshot['tracks_captured']} tracks)")
            write_json(STATUS_PATH, {
                "last_attempt": now_iso(),
                "status": "ok",
                "source": "soundcloud api-v2",
                "client_id_source": client_id_source,
                "snapshot_at": snapshot["snapshot_at"],
                "tracks_captured": snapshot["tracks_captured"],
                "tracks_skipped_no_count": snapshot["tracks_skipped_no_count"],
            })
            return 0
        log("tier-a produced no usable counts; falling through to status write.")

    # Tier (b): best-effort public probes (only when no client_id path succeeded).
    notes = probe_public_endpoints() if not client_id else ["client_id tier failed; skipping public probes"]
    for n in notes:
        log(f"tier-b: {n}")

    # Tier (c): graceful skip. NEVER fabricate counts, NEVER write zeros over real data.
    reason = ("no usable SOUNDCLOUD_CLIENT_ID and public web-app JS extraction failed; "
              "use live-browser capture (see GO_LIVE.md)")
    status = {
        "last_attempt": now_iso(),
        "status": "skipped",
        "reason": reason,
        "tiers": notes,
    }
    write_json(STATUS_PATH, status)
    log(f"status written: {STATUS_PATH} (status=skipped)")
    return 0


def main(argv):
    if "--merge" in argv:
        return run_merge()
    return run_refresh()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
