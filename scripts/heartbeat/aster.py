"""Aster heartbeat. Keyless sources only (Claude bundle 2026-10-24, RECORD S3):

  1. SoundCloud profile page - track_count + last_modified. A count that
     rises against the last pulse means a new upload exists. The page's
     play numbers are never parsed and never stored.
  2. SoundCloud RSS feed - titles, links, dates and art for the recent
     items only; a title not in the last feed state is the new upload's
     name for the transmission strip.
  3. Deezer artist albums - new album ids against the last state are new
     transmissions; only title/link/date/cover are kept.

Writes pulse.json plus its own small state files (sc-feed.json,
deezer.json). It never writes a play, stream, like, follower or milestone
number into any file; scripts/strip_public.py is the build-time backstop
and both stay true.
"""
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, __import__("os").path.dirname(__file__))
from lib import Pulse, get, get_json, now, read, write_if_changed  # noqa: E402

PROFILE = "https://soundcloud.com/asterdamaster"
DEEZER_ARTIST = "66649262"  # bundle RECORD S3: Deezer artist id on record

p = Pulse()

# --- 1 + 2: SoundCloud profile page, then its RSS feed -------------------
html = None
raw, err = get(PROFILE)
if raw:
    html = raw.decode("utf-8", "replace")
count = modified = None
uid = None
if html:
    m = re.search(r'"track_count"\s*:\s*(\d+)', html)
    count = int(m.group(1)) if m else None
    m = re.search(r'"last_modified"\s*:\s*"([^"]+)"', html)
    modified = m.group(1) if m else None
    m = re.search(r"soundcloud:users:(\d+)", html)
    uid = m.group(1) if m else None
prev_sc = next((s for s in p.prev.get("sources", []) if s["id"] == "soundcloud"), {})
if count is not None and prev_sc.get("items") and count > prev_sc["items"]:
    p.change("new-upload", "New SoundCloud upload detected", PROFILE)
p.source("soundcloud", "SoundCloud profile", count is not None,
         count or 0, err or "track_count not found", PROFILE)

rss_items = []
rss_err = None
if uid:
    feed_raw, rss_err = get(
        f"https://feeds.soundcloud.com/users/soundcloud:users:{uid}/sounds.rss")
    if feed_raw:
        try:
            ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
            root = ET.fromstring(feed_raw)
            for item in root.iter("item"):
                title = item.findtext("title")
                link = item.findtext("link")
                date = item.findtext("pubDate")
                img = item.find("itunes:image", ns)
                if title and link:
                    rss_items.append({
                        "title": title.strip(),
                        "link": link.strip(),
                        "date": date.strip() if date else None,
                        "artwork": img.get("href") if img is not None else None,
                    })
            rss_items = rss_items[:20]  # recent items only, per the bundle
        except Exception as e:  # a bent feed is a dead source, not a crash
            rss_err = type(e).__name__
            rss_items = []
old_titles = {i["title"] for i in read("sc-feed.json", {"items": []}).get("items", [])}
if rss_items and old_titles:
    for i in rss_items:
        if i["title"] not in old_titles:
            p.change("new-upload", i["title"], i["link"])
if rss_items:
    write_if_changed("sc-feed.json",
                     {"format": "sc-feed/1", "generated_at": now(), "items": rss_items})
p.source("soundcloud-rss", "SoundCloud RSS", bool(rss_items),
         len(rss_items), rss_err or ("no user id" if not uid else "empty feed"),
         "https://soundcloud.com/asterdamaster")

# --- 3: Deezer artist albums ---------------------------------------------
dz, dz_err = get_json(
    f"https://api.deezer.com/artist/{DEEZER_ARTIST}/albums?limit=100")
albums = []
if dz and isinstance(dz.get("data"), list):
    albums = [{
        "id": a["id"],
        "title": a.get("title"),
        "link": a.get("link"),
        "date": a.get("release_date"),
        "cover": a.get("cover_xl") or a.get("cover_big"),
    } for a in dz["data"] if a.get("id") and a.get("title")]
old_ids = {a["id"] for a in read("deezer.json", {"albums": []}).get("albums", [])}
if albums and old_ids:
    for a in albums:
        if a["id"] not in old_ids:
            p.change("new-release", a["title"], a["link"])
if albums:
    write_if_changed("deezer.json",
                     {"format": "deezer/1", "generated_at": now(), "albums": albums})
p.source("deezer", "Deezer artist albums", bool(albums), len(albums), dz_err,
         f"https://www.deezer.com/artist/{DEEZER_ARTIST}")

p.write()
print("heartbeat done:", {s["id"]: s["ok"] for s in p.sources.values()},
      "changes:", len(p.changes))
