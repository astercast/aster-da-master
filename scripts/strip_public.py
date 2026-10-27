"""Remove every play-count style number from the files the site publishes. Run in the Vercel build, after api_manifest.py.
Fails the build (exit 1) if any banned key is still found anywhere in a published JSON file,
or if any play/follower/stream/like/listener figure appears in a published text file
(R303, review-aster-1 item 1: the owner's no-numbers rule covers text files too, not just JSON).
Also withholds from the published output the files that carry counts by design and are not
part of the served site: data/*.snapshot.json (the frozen Signal capture store) and
scripts/verify_agent_workflows.js (the local proof script). They stay in the repo; the
build workspace copy is removed here so Vercel never serves them."""
import json, glob, os, re, sys
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

# --- text guard (R303): no figure tied to plays/followers/streams/likes/listeners
# in any published text file. Patterns: "30,088 plays", "9,615 of 10,000 plays",
# "30,088-play", "13,618 shared plays".
FIGURE = re.compile(
    r"(?<![\d,.\-/])\d[\d,]*(?:\.\d+)?\s+(?:of\s+\d[\d,]*(?:\.\d+)?\s+)?(?:shared\s+)?(plays|followers|streams|likes|listeners)\b"
    r"|(?<![\d,.\-/])\d[\d,]*(?:\.\d+)?-(plays?|followers?|streams?|likes?|listeners?)\b", re.I)
# the published agent/text surface (internal ops docs like WAVELOG.md and
# GO_LIVE.md are build records, not published text; their long dated lines
# would false-positive the figure pattern on date fragments)
text_files = sorted(["llms.txt", "llms-full.txt", "API.md", "AGENT.md", "README.md"] + glob.glob("skills/*.md"))
text_bad = []
for f in text_files:
    for n, line in enumerate(open(f, encoding="utf-8"), 1):
        if FIGURE.search(line):
            text_bad.append((f, n, line.strip()[:120]))
if text_bad:
    print("play/follower figures in published text files:")
    for hit in text_bad: print(hit)
    sys.exit(1)
print(f"text guard clean across {len(text_files)} published text files")

# --- withhold count-carrying non-site files from the published output
withheld = []
for f in glob.glob("data/*.snapshot.json") + ["scripts/verify_agent_workflows.js"]:
    if os.path.exists(f):
        os.remove(f); withheld.append(f)
print(f"withheld from published output: {withheld}")
