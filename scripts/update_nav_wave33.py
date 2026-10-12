#!/usr/bin/env python3
"""One-off: insert the chronicle "Chronicle" link into every site <nav> block
(primary + mobile + footer).

Run once after wave 33. Also updates the NAV/FOOTNAV constants inside
scripts/build_*.py so future regenerations keep the link.

Rule: a "Timeline" link alone on its line is a site nav entry (breadcrumbs
keep anchors on one line with " / " separators and are skipped). The
Chronicle link goes right after the Timeline link with matching indentation
and prefix, keeping the chronological explorers together.

Idempotent: skips files that already mention chronicle.html.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions", "eras",
           "producers", "scene")

TIMELINE_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)timeline\.html"[^>]*>Timeline</a>\n',
    re.MULTILINE,
)

SKIP = {"chronicle.html", "update_nav_wave33.py"}


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_after_timeline(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return (m.group(0) +
                f'{indent}<a href="{prefix}chronicle.html">Chronicle</a>\n')
    return TIMELINE_RE.sub(repl, text)


def main():
    changed = 0
    targets = sorted(ROOT.rglob("*.html")) + sorted((ROOT / "scripts").glob("build_*.py"))
    for path in targets:
        if "__pycache__" in path.parts:
            continue
        if path.name in SKIP:
            continue  # chronicle.html already ships the link
        text = path.read_text(encoding="utf-8")
        if "chronicle.html" in text:
            continue
        prefix = prefix_for(path) if path.suffix == ".html" else ""
        new = insert_after_timeline(text, prefix)
        # .py generators carry both "" and "../" variants; apply both
        if path.suffix == ".py":
            new = insert_after_timeline(new, "../")
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print(f"{changed} files updated")


if __name__ == "__main__":
    main()
