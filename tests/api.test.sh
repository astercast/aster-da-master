#!/usr/bin/env bash
# tests/api.test.sh — Wave-A verification for "The Signal" (aster-signal).
# Per ARCHITECTURE.md §12.2, adapted to the §7.4 roster.
#
# usage: BASE=http://localhost:3000 ./tests/api.test.sh
# Run from the repo root. The local function runtime is tests/local_server.js
# (a Vercel routing emulator); the same suite runs against a preview URL.
set -uo pipefail
BASE="${BASE:-http://localhost:3000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass=0; fail=0
ok_()   { pass=$((pass+1)); echo "ok   $1"; }
bad_()  { fail=$((fail+1)); echo "FAIL $1"; }
chk() { # chk <name> <command...>
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then ok_ "$name"; else bad_ "$name"; fi
}

echo "== The Signal — api.test.sh (BASE=$BASE)"

# 1. health -----------------------------------------------------------------
chk "health 200" curl -sf "$BASE/api/health"
chk "health envelope valid" bash -c \
  "curl -sf '$BASE/api/health' | python3 tests/assert_envelope.py --schema data/v1/schema/envelope.json"
chk "health status ok|degraded + roster functions" bash -c \
  "curl -sf '$BASE/api/health' | python3 -c \"
import json,sys
e=json.load(sys.stdin); d=e['data']
assert d['status'] in ('ok','degraded'), d['status']
assert d['service']=='aster-signal'
assert d['functions']==['health','stats','uploads','watch','cron/signal'], d['functions']
assert set(d['checks'])=={'static_fallback_present','cron_secret_configured','github_token_configured'}
\""

# 2. every roster endpoint returns an ok:true envelope ------------------------
for p in stats uploads "uploads?since=2026-09-01" "uploads?limit=3" "uploads?since=2026-01-01&limit=200"; do
  chk "envelope $p" bash -c \
    "curl -sf '$BASE/api/$p' | python3 -c \"
import json,sys
e=json.load(sys.stdin)
assert e['ok'] is True, 'ok!=true'
assert 'request_id' in e['meta'], 'no request_id'
\""
done

# stats payload shape: numbers only, no invented content ---------------------
chk "stats payload shape" bash -c \
  "curl -sf '$BASE/api/stats' | python3 -c \"
import json,sys
e=json.load(sys.stdin); d=e['data']
assert isinstance(d['tracks_captured'], int) and d['tracks_captured'] > 0
assert isinstance(d['total_plays'], int) and d['total_plays'] > 0
assert isinstance(d['snapshot_at'], str)
assert isinstance(d['top_tracks'], list) and len(d['top_tracks']) <= 10
for t in d['top_tracks']:
    assert set(t) >= {'title','plays','delta_7d'}
    assert isinstance(t['plays'], int)
    assert t['delta_7d'] is None or isinstance(t['delta_7d'], int)
print('tracks_captured=%d total_plays=%d' % (d['tracks_captured'], d['total_plays']))
\""

# watch payload shape (Signal 2.0) ---------------------------------------------
chk "watch envelope + shape" bash -c \
  "curl -sf '$BASE/api/watch' | python3 -c \"
import json,sys
e=json.load(sys.stdin); d=e['data']
assert d['kind']=='all'
s=d['summary']
assert s['tracks_watched']==185 and s['total_plays']>0
assert isinstance(d['new_uploads'], list) and isinstance(d['movers'], list)
assert isinstance(d['crossings'], list) and isinstance(d['next_up'], list)
for m in d['movers']:
    assert m['after']-m['before']==m['delta']
    assert m['per_day'] is None or isinstance(m['per_day'], (int,float))
assert d['live_dates']['checked_at']=='2026-10-13'
assert len(d['live_dates']['events'])>=5
print('watch tracks=%d movers=%d dates=%d' % (s['tracks_watched'], len(d['movers']), len(d['live_dates']['events'])))
\""
chk "watch kind filter" bash -c \
  "curl -sf '$BASE/api/watch?kind=dates' | python3 -c \"
import json,sys
d=json.load(sys.stdin)['data']
assert d['kind']=='dates' and 'live_dates' in d and 'movers' not in d
\""
chk "watch bad kind 400" bash -c \
  "curl -s '$BASE/api/watch?kind=bogus' | python3 -c \"
import json,sys
e=json.load(sys.stdin)
assert e['ok'] is False and e['error']['code']=='BAD_INPUT', e
\""

# uploads payload shape -------------------------------------------------------
chk "uploads payload shape" bash -c \
  "curl -sf '$BASE/api/uploads?since=2020-01-01&limit=5' | python3 -c \"
import json,sys
e=json.load(sys.stdin); d=e['data']
assert isinstance(d['count'], int) and d['count'] <= 5
for u in d['uploads']:
    assert set(u) >= {'title','uploaded_at','url','first_seen_at'}
print('count=%d' % d['count'])
\""

# 3. envelope schema validation (jsonschema, draft 2020-12) -------------------
for p in health stats uploads watch; do
  chk "schema $p" bash -c \
    "curl -sf '$BASE/api/$p' | python3 tests/assert_envelope.py --schema data/v1/schema/envelope.json"
done

# 4. cron without secret -> 401 -----------------------------------------------
chk "cron 401 no secret" bash -c \
  "[ \"\$(curl -s -o /dev/null -w '%{http_code}' '$BASE/api/cron/signal')\" = 401 ]"
chk "cron 401 envelope shape" bash -c \
  "curl -s '$BASE/api/cron/signal' | python3 -c \"
import json,sys
e=json.load(sys.stdin)
assert e['ok'] is False and e['error']['code']=='UNAUTHORIZED', e
\""

# 5. cron with wrong secret -> 401 ---------------------------------------------
chk "cron 401 bad secret" bash -c \
  "[ \"\$(curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer wrong' '$BASE/api/cron/signal')\" = 401 ]"

# 6. bad input -> 400 envelope -------------------------------------------------
for q in "uploads?since=not-a-date" "uploads?limit=abc" "uploads?limit=0"; do
  chk "bad input 400 ($q)" bash -c \
    "curl -s '$BASE/api/$q' | python3 -c \"
import json,sys
e=json.load(sys.stdin)
assert e['ok'] is False and e['error']['code']=='BAD_INPUT', e
assert 'fields' in e['error']['details'], e
\""
done
chk "limit clamped 1-200 (limit=201 -> 200)" bash -c \
  "curl -sf '$BASE/api/uploads?since=2020-01-01&limit=201' | python3 -c \"
import json,sys
e=json.load(sys.stdin)
assert e['ok'] is True and e['data']['count'] <= 200, e
\""
chk "bad input http 400" bash -c \
  "[ \"\$(curl -s -o /dev/null -w '%{http_code}' '$BASE/api/uploads?since=zzz')\" = 400 ]"

# 7. static fallback present ----------------------------------------------------
for f in refresh-status.json uploads.json stats-snapshots.json artist.json release-slugs.json changelog.json signal-watch.json live-dates.json; do
  chk "static fallback $f" curl -sf "$BASE/data/v1/$f"
done

# 8. vercel.json lint: cron not more frequent than daily ------------------------
chk "cron daily-or-slower" python3 -c "
import json
v = json.load(open('vercel.json'))
crons = v.get('crons', [])
assert len(crons) == 1, crons
for c in crons:
    f = c['schedule'].split()
    assert len(f) == 5, c
    assert f[0] != '*' and '*/' not in f[0] and '*/' not in f[1], c
    assert c['path'] == '/api/cron/signal', c
"
chk "vercel.json functions: explicit paths, no runtime pin" python3 -c "
import json, re
v = json.load(open('vercel.json'))
fns = v['functions']
# No broad globs: every key is an explicit api/*.js path that exists on disk.
import os
assert fns, 'functions map must not be empty'
for path, cfg in fns.items():
    assert '*' not in path, path
    assert re.fullmatch(r'api(/[a-z-]+)*/[a-z-]+\.js', path), path
    assert os.path.exists(path), path
    assert cfg and isinstance(cfg, dict), path
    assert cfg.get('maxDuration') == 10, (path, cfg)
# NEVER pin runtime for Node functions (Vercel rejects nodejsXX.x outright).
assert 'runtime' not in json.dumps(fns), 'runtime key must be omitted'
assert v['installCommand'] == \"echo 'no dependencies'\"
assert 'node_modules' not in json.dumps(v)
"

# 9. cache headers on public GET (§1.6) — GET with -D, not -I: functions are
# GET-only by design, and -I sends HEAD which correctly 405s.
chk "cache headers s-maxage=600" bash -c \
  "curl -s -o /dev/null -D - '$BASE/api/stats' | grep -qi 's-maxage=600'"
chk "cron no-store" bash -c \
  "curl -s -o /dev/null -D - -H 'Authorization: Bearer x' '$BASE/api/cron/signal' | grep -qi 'no-store'"

echo
echo "pass=$pass fail=$fail"
[ "$fail" = 0 ]
