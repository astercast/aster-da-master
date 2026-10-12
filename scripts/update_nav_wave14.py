#!/usr/bin/env python3
"""One-off: insert the Transmission link into every site <nav> block
(primary + mobile + footer).

Run once after wave 14. Also updates the NAV/FOOTNAV constants inside
scripts/build_*.py so future regenerations keep the link.

Rule: a "Timeline" link alone on its line is a site nav entry (breadcrumbs
keep anchors on one line with " / " separators and are skipped). The
Transmission link goes right after the Timeline link with matching
indentation and prefix, keeping Transmission prominent as the flagship.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions")

TIMELINE_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)timeline\.html"[^>]*>Timeline</a>\n',
    re.MULTILINE,
)

# Release pages use a compact nav with no Timeline link; wave 13 placed the
# Agents link after the API link there, so Transmission follows the same rule.
API_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)api-playground\.html"[^>]*>API</a>\n',
    re.MULTILINE,
)


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_after(m, prefix, label):
    indent = m.group("indent")
    return m.group(0) + f'{indent}<a href="{prefix}transmission.html">Transmission</a>\n'


def insert_transmission(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        return insert_after(m, prefix, "Transmission")
    return TIMELINE_RE.sub(repl, text)


def insert_after_api(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        return insert_after(m, prefix, "Transmission")
    return API_RE.sub(repl, text)


def main():
    changed = 0
    targets = sorted(ROOT.rglob("*.html")) + sorted((ROOT / "scripts").glob("build_*.py"))
    for path in targets:
        if "__pycache__" in path.parts:
            continue
        if path.name == "transmission.html":
            continue  # already ships the link
        text = path.read_text(encoding="utf-8")
        if "transmission.html" in text:
            continue
        prefix = prefix_for(path) if path.suffix == ".html" else ""
        new = insert_transmission(text, prefix)
        # .py generators carry both "" and "../" variants; apply both
        if path.suffix == ".py":
            new = insert_transmission(new, "../")
        # release pages use a compact nav with no Timeline link: follow the
        # wave-13 rule and place Transmission after the API link instead
        if "transmission.html" not in new:
            new2 = insert_after_api(new, prefix)
            if path.suffix == ".py":
                new2 = insert_after_api(new2, "../")
            new = new2
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print(f"nav updated in {changed} files")


if __name__ == "__main__":
    main()
