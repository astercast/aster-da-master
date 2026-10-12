#!/usr/bin/env python3
"""Wave 34 — font self-hosting wiring (idempotent).

For every generator HEAD/FOOT template (scripts/*.py) and every shipped HTML
page (*.html):
  1. Delete all Google Fonts lines (fonts.googleapis.com / fonts.gstatic.com).
  2. In their place (first stylesheet slot, right before tokens.css), insert:
       <link rel="preload" href="{pre}assets/fonts/anton-latin.woff2" as="font"
             type="font/woff2" crossorigin>
       <link rel="stylesheet" href="{pre}assets/css/fonts.css">
     where {pre} is the same relative prefix the page uses for assets/
     (derived from the tokens.css link — "" at root, "../" one level down).

Re-running is a no-op: files without a Google Fonts line are untouched, and
the new lines are only inserted where a removal happened.

After running: re-run the 22-generator chain so emitted pages pick up the new
heads (validate.sh stage 6 then re-runs the chain itself and must stay
byte-stable).
"""
import re
import sys
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")

GOOGLE_RE = re.compile(
    r'^[ \t]*<link[^>]*href="https://fonts\.(googleapis|gstatic)\.com[^"]*"[^>]*>\s*$',
    re.M,
)
TOKENS_RE = re.compile(
    r'<link rel="stylesheet" href="([^"]*?)assets/css/tokens\.css">'
)

NEW_HEAD_TMPL = (
    '  <link rel="preload" href="{pre}assets/fonts/anton-latin.woff2"'
    ' as="font" type="font/woff2" crossorigin>\n'
    '  <link rel="stylesheet" href="{pre}assets/css/fonts.css">'
)


def edit(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    m = GOOGLE_RE.search(text)
    if not m:
        return False  # already wired (or never had remote fonts)
    tm = TOKENS_RE.search(text)
    if not tm:
        raise SystemExit(f"no tokens.css link found in {path}")
    pre = tm.group(1)
    replacement = NEW_HEAD_TMPL.format(pre=pre)
    # Remove every Google Fonts line, insert the new pair at the first one's
    # position so the ordering (first stylesheet in <head>) is preserved.
    count = [0]

    def sub_first(match):
        count[0] += 1
        return replacement if count[0] == 1 else ""

    new_text = GOOGLE_RE.sub(sub_first, text)
    # Clean up any blank line left behind by the multi-line removal.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = []
    for rel in sorted(ROOT.glob("scripts/*.py")) + sorted(ROOT.rglob("*.html")):
        if ".git" in rel.parts:
            continue
        if edit(rel):
            changed.append(str(rel.relative_to(ROOT)))
    print(f"{len(changed)} files wired to self-hosted fonts")
    for c in changed[:20]:
        print("  ", c)
    if len(changed) > 20:
        print(f"   ... and {len(changed) - 20} more")


if __name__ == "__main__":
    main()
