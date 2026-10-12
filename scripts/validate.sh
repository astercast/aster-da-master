#!/usr/bin/env bash
# validate.sh — one-command validation pipeline for the Aster da Master archive.
#
# Stages:
#   1. JS syntax ......... node --check every shipped JS file (assets/js/)
#   2. JSON parse ........ every JSON file under api/, data/, skills/, scripts/
#   3. JSON Schema ....... draft-07 validation of all 16 docs under
#                         api/v1/schema/ (one per endpoint, incl. the index
#                         manifest and the era deep-dives)
#   4. Relative links .... every href/src in every HTML page resolves on disk;
#                         JS fetch() string literals resolve too. 0 broken.
#   5. Lyric-grep gate .. fail on any lyric-like content. Titles/metadata
#                         only: the substring "lyric" may appear ONLY in the
#                         standing-rule contexts (never/no lyrics, lyrics not
#                         reproduced, never quote lyrics, source domain
#                         lirik.web.id, and validator self-references).
#                         Lyric-section markers ([Chorus], Verse 1:, etc.) always fail.
#   6. Generator chain .. run the 15 generators in the documented dependency
#                         order (releases -> years -> circle -> codex ->
#                         sessions -> session_deepdives -> milestones ->
#                         milestone_watch -> firstlast -> glance -> search_index
#                         -> changelog -> transmission -> network -> eras).
#                         A clean re-run must
#                         produce zero diff outside changelog.html +
#                         api/v1/changelog.json (rebuilt from git log, so it
#                         legitimately grows after any new commit; its
#                         entry_count must equal the commit count).
#   7. Data version ..... every NEW_VERSION/VERSION constant across the
#                         version-writing generators agrees, and every
#                         "version" field in data/ + api/v1/ JSON equals it.
#   8. llms.txt fresh ... llms.txt's data-version line matches index.json;
#                         every index.json endpoint key is mentioned in
#                         llms.txt; the documented generator dependency order
#                         matches the canonical chain order; key catalog
#                         counts match the live JSON.
#
# Exit code: 0 only if every stage passes. Anything failing is a real issue
# to fix, not cosmetic churn.
#
# Usage: bash scripts/validate.sh   (from anywhere; resolves the repo itself)

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
STAGES=8
fail() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }
pass() { echo "  ok: $1"; PASS=$((PASS+1)); }
stage() { echo; echo "[$1/$STAGES] $2"; }

# ---------------------------------------------------------------- stage 1 ---
stage 1 "JS syntax (node --check)"
JS_OK=1
JS_N=0
while IFS= read -r f; do
  JS_N=$((JS_N+1))
  if ! node --check "$f" >/dev/null 2>&1; then
    fail "$f"; JS_OK=0
  fi
done < <(find assets/js scripts -name '*.js' 2>/dev/null | grep -v __pycache__ | sort)
if [ "$JS_OK" = 1 ]; then pass "$JS_N JS files parse"; fi

# ---------------------------------------------------------------- stage 2 ---
stage 2 "JSON parse"
JSON_N=0
JSON_BAD=0
while IFS= read -r f; do
  JSON_N=$((JSON_N+1))
  if ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" 2>/dev/null; then
    fail "invalid JSON: $f"; JSON_BAD=$((JSON_BAD+1))
  fi
done < <(find api data skills scripts -name '*.json' 2>/dev/null | grep -v __pycache__ | sort)
if [ "$JSON_BAD" = 0 ]; then pass "$JSON_N JSON files parse"; fi

# ---------------------------------------------------------------- stage 3 ---
stage 3 "JSON Schema (draft-07)"
python3 - <<'EOF'
import json, sys
from pathlib import Path
from jsonschema import Draft7Validator

ROOT = Path(".")
SCH = ROOT / "api" / "v1" / "schema"
failures = []

def schema(name):
    s = json.loads((SCH / name).read_text())
    Draft7Validator.check_schema(s)  # the schema itself must be valid draft-07
    return Draft7Validator(s)

# all 16 schemas are doc-level (one per endpoint, incl. the index manifest)
pairs = [("index.json", "index.json"), ("artist.json", "artist.json"),
         ("codex.json", "codex.json"), ("release-slugs.json", "release-slugs.json"),
         ("on-this-day.json", "on-this-day.json"), ("years.json", "years.json"),
         ("circle.json", "circle.json"), ("milestones.json", "milestones.json"),
         ("sessions.json", "sessions.json"), ("changelog.json", "changelog.json"),
         ("first-last.json", "first-last.json"),
         ("milestone-watch.json", "milestone-watch.json"),
         ("scene-figures.json", "scene-figures.json"),
         ("transmission.json", "transmission.json"),
         ("network.json", "network.json"),
         ("eras.json", "eras.json")]
for fname, sname in pairs:
    doc = json.loads((ROOT / "api" / "v1" / fname).read_text())
    for e in schema(sname).iter_errors(doc):
        failures.append(f"{fname}: {e.message}")

if failures:
    print("  FAIL: schema violations:")
    for f in failures[:20]:
        print("   -", f)
    if len(failures) > 20:
        print(f"   ... and {len(failures)-20} more")
    sys.exit(1)
print("  ok: all 16 endpoints validate against their draft-07 schemas")
EOF
[ $? -eq 0 ] && pass "schema validation clean" || FAIL=$((FAIL+1))

# ---------------------------------------------------------------- stage 4 ---
stage 4 "relative-link check (0 broken)"
python3 - <<'EOF'
import json, re, sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(".")
ATTR = re.compile(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', re.I)
FETCH = re.compile(r'''(?:fetch|loadData)\(\s*["']([^"']+)["']''')
total = 0
broken = []

def resolve(base, link):
    link = link.strip()
    if not link or link.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
        return None
    if re.match(r"^(?:https?:)?//", link, re.I):
        return None  # external: out of scope for this check
    if "{" in link or "}" in link or "$" in link:
        return None  # JS template placeholder, not a real URL (guarded)
    link = unquote(link.split("#", 1)[0].split("?", 1)[0])
    if not link:
        return None
    if link.startswith("/"):
        return ROOT / link[1:]  # site-rooted; the repo root is the served root
    return base / link

def check_link(base, link, origin):
    global total
    target = resolve(base, link)
    if target is None:
        return
    total += 1
    t = Path(str(target).rstrip("/"))
    if t.is_dir():
        t = t / "index.html"  # a directory only resolves if it has an index
    if not t.exists():
        broken.append(f"{origin} -> {link}")

# every HTML page on the site (root + subdir indexes)
for page in sorted(ROOT.glob("*.html")) + sorted(ROOT.glob("*/index.html")):
    text = page.read_text()
    for m in ATTR.finditer(text):
        check_link(page.parent, m.group(1), page.relative_to(ROOT))
# subdir content pages (releases/, years/, circle/, codex/, sessions/, eras/)
for page in sorted(ROOT.glob("releases/*.html")) + sorted(ROOT.glob("years/*.html")) \
        + sorted(ROOT.glob("circle/*.html")) + sorted(ROOT.glob("codex/*.html")) \
        + sorted(ROOT.glob("sessions/*.html")) + sorted(ROOT.glob("eras/*.html")):
    text = page.read_text()
    for m in ATTR.finditer(text):
        check_link(page.parent, m.group(1), page.relative_to(ROOT))

# JS fetch()/loadData() string literals: evaluated from the page's perspective,
# so relative to the served root. loadData() here is the common.js helper.
for js in sorted((ROOT / "assets" / "js").glob("*.js")):
    text = js.read_text()
    for m in FETCH.finditer(text):
        check_link(ROOT, m.group(1), js.relative_to(ROOT))

# api-playground endpoint table: paths are site-root-relative
pg = open("assets/js/playground.js").read()
for m in re.finditer(r'''path:\s*["']([^"']+)["']''', pg):
    total += 1
    t = ROOT / m.group(1)
    if not t.exists():
        broken.append(f"api-playground endpoint -> {m.group(1)}")

print(f"  checked {total} links")
if broken:
    print(f"  FAIL: {len(broken)} broken links:")
    for b in broken[:25]:
        print("   -", b)
    if len(broken) > 25:
        print(f"   ... and {len(broken)-25} more")
    sys.exit(1)
print("  ok: 0 broken relative links")
EOF
[ $? -eq 0 ] && pass "link check" || FAIL=$((FAIL+1))

# ---------------------------------------------------------------- stage 5 ---
stage 5 "lyric-grep gate (titles/metadata only, never lyrics)"
python3 - <<'EOF'
import re, sys
from pathlib import Path

ROOT = Path(".")
# occurrences of the substring "lyric" are allowed ONLY in these contexts:
#  - the source domain lirik.web.id
#  - a negated standing-rule statement (no/never/not/without ... within a few words
#    before "lyric", e.g. "never quote or interpret lyrics", "no lyrics reproduced")
#  - validator self-references (lyric leak / lyric grep / lyric-like / lyric-section)
SELFREFS = ("lyric leak", "lyric grep", "lyric-grep", "lyric-like", "lyric-section")
NEGATED = re.compile(r"(no|never|not|n't|without)\b.{0,28}lyric", re.S)
# a lyric-section marker is a marker ALONE on its line (optionally bracketed /
# punctuated / wrapped in one HTML tag). Track titles like "[outro] Off Beat
# ft. Yung Vetta (prod. Addy)" always carry more text after the marker, so the
# bare-line anchor never flags a title.
SECTIONS = re.compile(
    r"(?m)^\s*(?:<[^>]+>\s*)*[\[\(]?\s*"
    r"(verse\s*\d*|chorus|hook|bridge|intro|outro|pre[\s-]?chorus|refrain|interlude|vamp|skit)"
    r"\s*[\]\)]?\s*[:\-]?\s*(?:<[^>]+>\s*)*$",
    re.I)

def content_files():
    for pat in ("*.html", "api/**/*.json", "data/**/*.json", "skills/*.md",
                "llms.txt", "llms-full.txt", "API.md", "AGENT.md"):
        for f in sorted(ROOT.glob(pat)):
            if f.is_file() and "__pycache__" not in str(f):
                yield f

leaks = []
for f in content_files():
    text = f.read_text(encoding="utf-8", errors="replace")
    low = text.lower()
    for m in re.finditer(r"lyric", low):
        ctx = low[max(0, m.start()-70):m.end()+70]
        if not ("lirik.web.id" in ctx or NEGATED.search(ctx) or any(s in ctx for s in SELFREFS)):
            leaks.append(f"{f.relative_to(ROOT)}: ...{ctx.strip()[:90]}...")
            break  # one report per file
    if SECTIONS.search(text):
        leaks.append(f"{f.relative_to(ROOT)}: lyric-section marker found")

if leaks:
    print("  FAIL: lyric-like content detected:")
    for l in leaks[:15]:
        print("   -", l)
    if len(leaks) > 15:
        print(f"   ... and {len(leaks)-15} more")
    sys.exit(1)
print("  ok: no lyric content; every 'lyric' occurrence is a standing-rule/provenance note")
EOF
[ $? -eq 0 ] && pass "lyric-grep gate" || FAIL=$((FAIL+1))

# ---------------------------------------------------------------- stage 6 ---
stage 6 "generator-chain order check (clean re-run -> zero unexpected diffs)"
# Canonical dependency order: releases -> years -> circle -> codex -> sessions
# -> session_deepdives -> milestones -> milestone_watch -> firstlast -> glance
# -> search_index -> changelog -> transmission -> network -> eras
CHAIN="build_releases build_years build_circle build_codex build_sessions \
build_session_deepdives build_milestones build_milestone_watch \
build_firstlast build_glance build_search_index build_changelog \
build_transmission build_network build_eras"
CHAIN_OK=1
for s in $CHAIN; do
  if ! python3 "scripts/$s.py" >/tmp/adm_validate_chain.log 2>&1; then
    fail "generator crashed: $s"
    tail -5 /tmp/adm_validate_chain.log | sed 's/^/    /'
    CHAIN_OK=0
  fi
done
# changelog.{html,json} legitimately grow after any new commit (built from git log).
# api/v1/index.json is a pure chain output (scripts/api_manifest.py rebuilds it
# canonically on every generator run); its changelog `records` count moves with
# the commit count, so it drifts for the same reason the changelog files do.
# Everything else must be byte-stable across a re-run.
DIFF=$(git diff --stat -- . ':!changelog.html' ':!api/v1/changelog.json' ':!api/v1/index.json' 2>/dev/null)
if [ -n "$DIFF" ]; then
  fail "generator re-run produced unexpected diffs:"
  echo "$DIFF" | head -12 | sed 's/^/    /'
  CHAIN_OK=0
fi
# Changelog sync convention (a changelog built from `git log` can never record
# its own sync commit, so two commits are the steady state):
#   (a) right after a rebuild: entry_count == commit count (HEAD not yet committed
#       the rebuild), or
#   (b) at rest: HEAD is the sync commit - it touches changelog.html +
#       api/v1/changelog.json, and (since wave 17) api/v1/index.json too,
#       because the manifest's changelog `records` count moves with every
#       commit. entry_count == commit count of HEAD~1, the top entry's hash
#       matches HEAD~1, and the manifest's changelog records == entry_count.
python3 - <<'EOF'
import json, subprocess, sys
from pathlib import Path

def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()

cl = json.loads(Path("api/v1/changelog.json").read_text())
n = int(git("rev-list", "--count", "HEAD"))
if cl["entry_count"] == n:
    print(f"  ok: changelog in sync with git history ({n} commits)")
    sys.exit(0)
touched = [f for f in git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines() if f.strip()]
idx = json.loads(Path("api/v1/index.json").read_text())
if ({"changelog.html", "api/v1/changelog.json"} <= set(touched)
        <= {"changelog.html", "api/v1/changelog.json", "api/v1/index.json"}
        and cl["entry_count"] == n - 1
        and cl["entries"][0]["hash"] == git("rev-parse", "--short", "HEAD~1")
        and idx["endpoints"]["changelog"]["records"] == cl["entry_count"]):
    print(f"  ok: changelog sync commit at HEAD; entries ({cl['entry_count']}) cover all content commits")
    sys.exit(0)
print(f"  FAIL: changelog entry_count {cl['entry_count']} vs {n} commits "
      f"(rebuild via the chain and commit changelog.html + api/v1/changelog.json)")
sys.exit(1)
EOF
[ $? -eq 0 ] && true || { CHAIN_OK=0; FAIL=$((FAIL+1)); }
if [ "$CHAIN_OK" = 1 ]; then pass "chain re-run: zero unexpected diffs; changelog in sync"; fi

# ---------------------------------------------------------------- stage 7 ---
stage 7 "data-version consistency"
python3 - <<'EOF'
import json, re, sys
from pathlib import Path

ROOT = Path(".")
errors = []

# every NEW_VERSION/VERSION constant in the version-writing generators must agree
consts = {}
for f in sorted((ROOT / "scripts").glob("build_*.py")):
    for m in re.finditer(r'(?:NEW_VERSION|VERSION)\s*=\s*"([^"]+)"', f.read_text()):
        consts.setdefault(m.group(1), []).append(f.name)
if len(consts) != 1:
    errors.append(f"version constants disagree: {consts}")
expected = next(iter(consts)) if consts else None

# every "version" field in data/ + api/v1/ JSON must equal it
if expected:
    for pat in ("data/*.json", "api/v1/*.json"):
        for f in sorted(ROOT.glob(pat)):
            d = json.loads(f.read_text())
            if isinstance(d, dict) and "version" in d and d["version"] != expected:
                errors.append(f"{f.relative_to(ROOT)}: version {d['version']} != {expected}")

if errors:
    print("  FAIL:")
    for e in errors:
        print("   -", e)
    sys.exit(1)
print(f"  ok: all generator constants and JSON version fields agree on {expected}")
EOF
[ $? -eq 0 ] && pass "data-version consistency" || FAIL=$((FAIL+1))

# ---------------------------------------------------------------- stage 8 ---
stage 8 "llms.txt freshness"
python3 - <<'EOF'
import json, re, sys
from pathlib import Path

ROOT = Path(".")
errors = []

idx = json.loads((ROOT / "api" / "v1" / "index.json").read_text())
ver = idx["version"]
endpoints = idx["endpoints"]
llms = (ROOT / "llms.txt").read_text()

m = re.search(r"Data version: (\d+\.\d+\.\d+)", llms)
if not m or m.group(1) != ver:
    errors.append(f"llms.txt data version ({m.group(1) if m else 'MISSING'}) != index.json {ver}")

missing = [k for k in endpoints if k not in llms]
if missing:
    errors.append(f"llms.txt omits endpoint keys: {missing}")

CHAIN_ORDER = ("releases", "years", "circle", "codex", "sessions",
               "session_deepdives", "milestones", "milestone_watch",
               "firstlast", "glance", "search_index", "changelog", "transmission",
               "network", "eras")
chain_str = " \u2192 ".join(CHAIN_ORDER)
if chain_str not in llms:
    errors.append("llms.txt generator dependency order doesn't match the canonical chain")

# catalog counts: 219 transmissions, 34 distributor releases, 185 SoundCloud tracks,
# 16 codex families, 21 collaborators, 61 sessions, 10 skills
artist = json.loads((ROOT / "data" / "artist.json").read_text())
circle_keys = json.loads((ROOT / "api" / "v1" / "circle.json").read_text())
disc = artist["discography"]
dist = [e for e in disc if e["type"] in ("Album", "Single")]
vault = [e for e in disc if e["type"] == "SoundCloud-only"]
codex = json.loads((ROOT / "data" / "codex.json").read_text())
sessions = json.loads((ROOT / "data" / "sessions.json").read_text())
skills = [f for f in (ROOT / "skills").glob("*.md") if f.name != "index.json"]
checks = [(str(len(disc)), "219"), (str(len(dist)), "34"), (str(len(vault)), "185"),
          (str(len(codex["families"])), "16"), (str(len(sessions["sessions"])), "61"),
          (str(len(circle_keys)), "21"), (str(len(skills)), "10")]
for actual, want in checks:
    if actual != want:
        errors.append(f"catalog drift: expected {want}, data says {actual}")
    elif f"**{want}" not in llms and want not in llms:
        errors.append(f"llms.txt missing count {want}")

if errors:
    print("  FAIL:")
    for e in errors:
        print("   -", e)
    sys.exit(1)
print(f"  ok: llms.txt matches index.json v{ver}, all {len(endpoints)} endpoints, chain order, catalog counts (219/34/185/16/21/61/10)")
EOF
[ $? -eq 0 ] && pass "llms.txt freshness" || FAIL=$((FAIL+1))

# ---------------------------------------------------------------- summary ---
echo
echo "validate.sh: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && echo "ALL STAGES PASS" || echo "VALIDATION FAILED"
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
