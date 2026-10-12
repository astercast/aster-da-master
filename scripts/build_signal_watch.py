"""Build data/v1/signal-watch.json — The Signal 2.0 watch file.

Python mirror of lib/signal-watch.js (keep keying, threshold and
per_day rules in step — per_day is plain division over the real gap
between captures, reported only when that gap is at least 24 hours).

Capture pair, newest last:

  previous : the newest archived capture in data/captures/ that is
             older than the latest snapshot (immutable per-capture
             files written by the refresh runs). Falls back to the
             2026-10-11 research capture in data/v1/artist.json when
             no archive exists yet (the original seed pair).
  latest   : data/playcounts.snapshot.json — the most recent refresh
             capture, via SoundCloud api-v2.

The daily cron (api/cron/signal.js) rewrites this file with the same
shape once deployed captures exist. Hand-run, like the other refresh
tooling — not part of the validate.sh generator chain.

Also folds in: the newest upload on record (from the latest capture),
the next-up milestone board (from data/v1/milestone-watch.json bands),
and the snapshot history rows (from data/v1/stats-snapshots.json).
"""
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


def js_round2(v):
    """Mirror JS Math.round(v * 100) / 100 (half away from zero)."""
    return math.copysign(math.floor(abs(v) * 100 + 0.5), v) / 100


def parse_ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

ROOT = Path(__file__).resolve().parent.parent
THRESHOLDS = [100, 500, 1000, 5000, 10000, 20000, 30000]
VERSION = "0.19.0"


def norm_title(t):
    t = str(t or "")
    for curly in ("‘", "’", "ʼ"):
        t = t.replace(curly, "'")
    for curly in ("“", "”"):
        t = t.replace(curly, '"')
    return re.sub(r"\s+", " ", t.lower()).strip()


def index_tracks(tracks):
    out = {}
    for t in tracks:
        if not isinstance(t.get("title"), str):
            continue
        plays = t.get("plays")
        if not isinstance(plays, int) or plays < 0:
            continue
        key = "title:" + norm_title(t["title"])
        if key in out:  # genuine duplicate title in one capture
            key = key + "|" + str(t.get("upload_date") or t.get("date") or "")
        out[key] = {
            "title": t["title"],
            "upload_date": t.get("upload_date") or t.get("date"),
            "plays": plays,
            "url": t.get("url"),
        }
    return out


def _captures_compared():
    """Running count of captures diffed into the watch file: the count
    already recorded in the committed file, plus this new pair. First
    build (no file yet) is the seed pair = 2."""
    try:
        cur = json.loads((ROOT / "data/v1/signal-watch.json").read_text())
        n = cur.get("baseline", {}).get("captures_compared")
        if isinstance(n, int) and n >= 2:
            # Only advance when the latest capture actually moved on.
            if cur["baseline"].get("latest_capture_at") != _latest_snapshot_at():
                return n + 1
            return n
    except (ValueError, OSError, KeyError):
        pass
    return 2


def _latest_snapshot_at():
    try:
        return json.loads((ROOT / "data/playcounts.snapshot.json").read_text())["snapshot_at"]
    except (ValueError, OSError, KeyError):
        return None


def main():
    snap = json.loads((ROOT / "data/playcounts.snapshot.json").read_text())
    snaps = json.loads((ROOT / "data/v1/stats-snapshots.json").read_text())
    mwatch = json.loads((ROOT / "data/v1/milestone-watch.json").read_text())

    # Previous capture: newest archived capture older than the latest
    # snapshot; fall back to the 2026-10-11 research capture (seed pair).
    prev_tracks, prev_at, prev_source = None, None, None
    cap_dir = ROOT / "data/captures"
    if cap_dir.is_dir():
        archived = []
        for f in sorted(cap_dir.glob("*.json")):
            try:
                d = json.loads(f.read_text())
            except (ValueError, OSError):
                continue
            if d.get("snapshot_at") and d["snapshot_at"] < snap["snapshot_at"]:
                archived.append((d["snapshot_at"], f, d))
        if archived:
            archived.sort(key=lambda x: x[0])
            _, pf, pd = archived[-1]
            prev_tracks = pd["tracks"]
            prev_at = pd["snapshot_at"]
            prev_source = f"data/captures/{pf.name} — previous Signal capture, SoundCloud api-v2"
    if prev_tracks is None:
        artist = json.loads((ROOT / "data/v1/artist.json").read_text())
        prev_tracks = [e for e in artist["discography"]
                       if e["type"] == "SoundCloud-only"]
        prev_at = "2026-10-11"
        prev_source = "data/v1/artist.json — 2026-10-11 research capture"

    prev = index_tracks(prev_tracks)
    curr = index_tracks(snap["tracks"])

    # per_day gate (mirrors lib/signal-watch.js): plain division over the
    # real elapsed time, only when the gap is at least 24 hours.
    t_prev, t_curr = parse_ts(prev_at), parse_ts(snap["snapshot_at"])
    elapsed_days = None
    if t_prev and t_curr and t_curr > t_prev:
        elapsed_days = (t_curr - t_prev).total_seconds() / 86400
    rate_ok = elapsed_days is not None and elapsed_days >= 1

    new_uploads, removed, movers, crossings = [], [], [], []
    for key, c in curr.items():
        p = prev.get(key)
        if p is None:
            new_uploads.append({"title": c["title"], "uploaded_at": c["upload_date"],
                                "plays": c["plays"], "url": c["url"]})
            continue
        if c["plays"] != p["plays"]:
            delta = c["plays"] - p["plays"]
            movers.append({"title": c["title"], "before": p["plays"], "after": c["plays"],
                           "delta": delta,
                           "per_day": js_round2(delta / elapsed_days) if rate_ok else None,
                           "url": c["url"] or p["url"]})
        for th in THRESHOLDS:
            if p["plays"] < th <= c["plays"]:
                crossings.append({"title": c["title"], "threshold": th,
                                  "before": p["plays"], "after": c["plays"],
                                  "url": c["url"] or p["url"]})
    for key, p in prev.items():
        if key not in curr:
            removed.append({"title": p["title"], "uploaded_at": p["upload_date"],
                            "plays": p["plays"], "url": p["url"]})
    movers.sort(key=lambda m: (-abs(m["delta"]), m["title"]))
    crossings.sort(key=lambda x: (-x["threshold"], x["title"]))

    newest = max(curr.values(), key=lambda t: (t["upload_date"] or "", t["title"]))
    next_up = []
    for band in mwatch.get("bands", []):
        for t in band.get("tracks", []):
            next_up.append({"title": t["title"], "plays": t["plays"],
                            "target": band["target"], "needed": t["needed"],
                            "page": t.get("page")})
    next_up.sort(key=lambda t: t["needed"])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {
        "version": VERSION,
        "generated_at": now,
        "service": "aster-signal",
        "watch_version": "2.0.0",
        "method": (
            "Each capture of the SoundCloud vault is diffed against the previous one. "
            "Tracks are keyed by normalized title (case, apostrophe style and whitespace "
            "unified) or permalink when a live refresh captured one — upload dates drift "
            "between capture methods and are never used as identity. A track in the new "
            "capture with no key in the old is a new upload. per_day is plain division over "
            "the real gap between captures and is only reported when that gap is at least "
            "24 hours; below that it is null rather than invented."
        ),
        "baseline": {
            "previous_capture_at": prev_at,
            "previous_source": prev_source,
            "latest_capture_at": snap["snapshot_at"],
            "latest_source": "data/playcounts.snapshot.json — Signal capture, SoundCloud api-v2",
            "elapsed_days": js_round2(elapsed_days) if elapsed_days is not None else None,
            "captures_compared": _captures_compared(),
        },
        "summary": {
            "tracks_watched": len(curr),
            "total_plays": sum(t["plays"] for t in curr.values()),
            "total_delta": sum(m["delta"] for m in movers),
            "new_uploads": len(new_uploads),
            "removed": len(removed),
            "movers": len(movers),
            "crossings": len(crossings),
            "newest_upload": {"title": newest["title"], "uploaded_at": newest["upload_date"]},
        },
        "new_uploads": new_uploads,
        "removed": removed,
        "movers": movers,
        "crossings": crossings,
        "next_up": next_up,
        "history": [
            {"snapshot_at": r["snapshot_at"], "total_plays": r["total_plays"],
             "tracks_captured": r["tracks_captured"]}
            for r in snaps.get("snapshots", [])
        ],
    }
    out = ROOT / "data/v1/signal-watch.json"
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    s = doc["summary"]
    print(f"signal-watch.json written: {s['tracks_watched']} tracks, "
          f"{s['new_uploads']} new, {s['movers']} movers, {s['crossings']} crossings, "
          f"total {s['total_plays']} ({s['total_delta']:+d})")


if __name__ == "__main__":
    main()
