#!/usr/bin/env python3
"""One-off: insert the "Atlas" link into every site <nav> block
(primary + mobile + footer), right after the Tuner link.

Run once for Rotation 10 (The Scene Atlas flagship). Also updates the
NAV constants inside scripts/build_*.py so future regenerations keep
the link, mirroring scripts/update_nav_wave34.py (Tuner).

Rule: a "Tuner" link alone on its line is a site nav entry (inline
content links sit inside paragraphs and are skipped). The Atlas link
keeps the matching indentation and ../ prefix.

Idempotent: skips files that already mention scene-atlas.html.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions", "eras",
           "producers", "scene")

TUNER_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)tuner\.html"[^>]*>Tuner</a>\n',
    re.MULTILINE,
)

SKIP = {"scene-atlas.html", "update_nav_wave35.py"}


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_after_tuner(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return (m.group(0) +
                f'{indent}<a href="{prefix}scene-atlas.html">Atlas</a>\n')
    return TUNER_RE.sub(repl, text)


def main():
    changed = 0
    targets = sorted(ROOT.rglob("*.html")) + sorted((ROOT / "scripts").glob("build_*.py"))
    for path in targets:
        if "__pycache__" in path.parts:
            continue
        if path.name in SKIP:
            continue  # scene-atlas.html already ships the link
        text = path.read_text(encoding="utf-8")
        if "scene-atlas.html" in text:
            continue
        prefix = prefix_for(path) if path.suffix == ".html" else ""
        new = insert_after_tuner(text, prefix)
        # .py generators carry both "" and "../" variants; apply both
        if path.suffix == ".py":
            new = insert_after_tuner(new, "../")
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print(f"{changed} files updated")


if __name__ == "__main__":
    main()
