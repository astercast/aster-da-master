"""Remove every play-count style number from the files the site publishes. Run in the Vercel build, after api_manifest.py.
Fails the build (exit 1) if any banned key is still found anywhere in a published JSON file."""
import json, glob, re, sys
BANNED = re.compile(r"^(plays?|play_?counts?|streams?|listens?|likes?|reposts?|comments?_?count|followers?(_count)?|per_day|milestone.*|crossed.*)$", re.I)
def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items() if not BANNED.match(k)}
    if isinstance(o, list): return [clean(x) for x in o]
    return o
def banned_keys(o, hits):
    if isinstance(o, dict):
        for k, v in o.items():
            if BANNED.match(k): hits.append(k)
            banned_keys(v, hits)
    elif isinstance(o, list):
        for x in o: banned_keys(x, hits)
files = glob.glob("data/*.json") + glob.glob("data/v1/*.json")
changed = 0
for f in files:
    d = json.load(open(f, encoding="utf-8")); c = clean(d)
    if c != d: json.dump(c, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1); changed += 1
bad = []
for f in files:
    h = []; banned_keys(json.load(open(f, encoding="utf-8")), h)
    if h: bad.append((f, sorted(set(h))))
print(f"stripped {changed} files; {len(bad)} still dirty")
if bad: print(bad); sys.exit(1)
