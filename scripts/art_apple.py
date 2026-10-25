#!/usr/bin/env python3
"""Fill data/art.json with cover art from Apple Music, using Apple's public iTunes
lookup (no key, no login). It writes only the address of the art, never a copy.

    python3 scripts/art_apple.py            # resolve every Apple release in data/artist.json
    python3 scripts/art_apple.py --check    # also fetch each cover once to prove it answers

Both distributor profiles are read (the main one and the alt-spelling one), their full
album lists are matched to our release records by title and date, and the result is a
manifest the page builder reads:
  data/art.json  {"<title>|<date>": {"source":"apple","collectionId":..,"base":"https://is1-ssl.mzstatic.com/.../artwork.jpg","page":"https://music.apple.com/...","checkedAt":".."}}
Apple's image address takes a size and a type on its end, so one base serves every size:
  <base>/300x300bb.webp   <base>/600x600bb.webp   <base>/1000x1000bb.webp
A release with no match stays on its sleeve. Nothing is invented.
"""
import json, re, sys, time, unicodedata, urllib.request, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = (1466301103, 1369059395)      # main profile, alt-spelling profile (see data/artist.json sources)
UA = "Mozilla/5.0 (compatible; aster-da-master-art/1.0; +https://github.com/astercast/aster-da-master)"


def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def norm(s):
    s = unicodedata.normalize("NFKD", s).lower()
    s = re.sub(r"\s*-\s*(single|ep)$", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def main():
    artist = json.loads((ROOT / "data" / "artist.json").read_text())
    found = {}
    for pid in PROFILES:
        r = get(f"https://itunes.apple.com/lookup?id={pid}&entity=album&limit=200")
        for c in r["results"]:
            if c.get("wrapperType") == "collection":
                found.setdefault(norm(c["collectionName"]), []).append(c)
        time.sleep(1)
    art, miss = {}, []
    today = datetime.date.today().isoformat()
    for x in artist["discography"]:
        if x["type"] == "SoundCloud-only":
            continue
        c = found.get(norm(x["title"]))
        if c and len(c) > 1:
            c = [y for y in c if y["releaseDate"][:10] == x.get("date")] or c
        if not c:
            miss.append(x["title"])
            continue
        c = c[0]
        base = re.sub(r"/\d+x\d+[a-z]*\.\w+$", "", c["artworkUrl100"])
        art[f'{x["title"]}|{x.get("date")}'] = {"source": "apple", "collectionId": c["collectionId"], "base": base,
                                              "page": c["collectionViewUrl"].split("?")[0], "checkedAt": today}
    if "--check" in sys.argv:
        for k, v in art.items():
            req = urllib.request.Request(v["base"] + "/300x300bb.webp", headers={"User-Agent": UA})
            assert urllib.request.urlopen(req, timeout=30).status == 200, k
            time.sleep(0.3)
    (ROOT / "data" / "art.json").write_text(json.dumps(art, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(art)} covers resolved; no match for: {miss or 'none'}")


if __name__ == "__main__":
    main()
