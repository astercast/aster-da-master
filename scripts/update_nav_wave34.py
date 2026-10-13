#!/usr/bin/env python3
"""One-off: insert the "Tuner" link into every site <nav> block
(primary + mobile + footer), right after the Transmission link.

Run once for Rotation 9 (The Tuner flagship). Also updates the NAV
constants inside scripts/build_*.py so future regenerations keep the
link, mirroring scripts/update_nav_wave33.py (Chronicle).

Rule: a "Transmission" link alone on its line is a site nav entry
(inline content links sit inside paragraphs and are skipped). The
Tuner link keeps the matching indentation and ../ prefix.

Idempotent: skips files that already mention tuner.html.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions", "eras",
           "producers", "scene")

TX_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)transmission\.html"[^>]*>Transmission</a>\n',
    re.MULTILINE,
)

SKIP = {"tuner.html", "update_nav_wave34.py"}


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_after_transmission(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return (m.group(0) +
                f'{indent}<a href="{prefix}tuner.html">Tuner</a>\n')
    return TX_RE.sub(repl, text)


def main():
    changed = 0
    targets = sorted(ROOT.rglob("*.html")) + sorted((ROOT / "scripts").glob("build_*.py"))
    for path in targets:
        if "__pycache__" in path.parts:
            continue
        if path.name in SKIP:
            continue  # tuner.html already ships the link
        text = path.read_text(encoding="utf-8")
        if "tuner.html" in text:
            continue
        prefix = prefix_for(path) if path.suffix == ".html" else ""
        new = insert_after_transmission(text, prefix)
        # .py generators carry both "" and "../" variants; apply both
        if path.suffix == ".py":
            new = insert_after_transmission(new, "../")
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print(f"{changed} files updated")


if __name__ == "__main__":
    main()
