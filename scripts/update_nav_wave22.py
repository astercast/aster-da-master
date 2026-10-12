#!/usr/bin/env python3
"""One-off: insert the milestone-race "Race" link into every site <nav> block
(primary + mobile + footer).

Run once after wave 22. Also updates the NAV/FOOTNAV constants inside
scripts/build_*.py so future regenerations keep the link.

Rule: a "Network" link alone on its line is a site nav entry (breadcrumbs
keep anchors on one line with " / " separators and are skipped). The Race
link goes right after the Network link with matching indentation and
prefix, keeping the interactive experiences together.

Release pages use a compact nav with no Network link: follow the wave-13/14
rule and place Race after the Transmission link instead.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions")

NETWORK_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)network\.html"[^>]*>Network</a>\n',
    re.MULTILINE,
)
TRANSMISSION_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)transmission\.html"[^>]*>Transmission</a>\n',
    re.MULTILINE,
)

SKIP = {"milestone-race.html", "update_nav_wave22.py"}


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_after_network(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return (m.group(0) +
                f'{indent}<a href="{prefix}milestone-race.html">Race</a>\n')
    return NETWORK_RE.sub(repl, text)


def insert_after_transmission(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return (m.group(0) +
                f'{indent}<a href="{prefix}milestone-race.html">Race</a>\n')
    return TRANSMISSION_RE.sub(repl, text)


def main():
    changed = 0
    targets = sorted(ROOT.rglob("*.html")) + sorted((ROOT / "scripts").glob("build_*.py"))
    for path in targets:
        if "__pycache__" in path.parts:
            continue
        if path.name in SKIP:
            continue  # milestone-race.html already ships the link
        text = path.read_text(encoding="utf-8")
        if "milestone-race.html" in text:
            continue
        prefix = prefix_for(path) if path.suffix == ".html" else ""
        new = insert_after_network(text, prefix)
        # .py generators carry both "" and "../" variants; apply both
        if path.suffix == ".py":
            new = insert_after_network(new, "../")
        # release pages use a compact nav with no Network link: follow the
        # wave-13/14 rule and place Race after the Transmission link instead
        if "milestone-race.html" not in new:
            new2 = insert_after_transmission(new, prefix)
            if path.suffix == ".py":
                new2 = insert_after_transmission(new2, "../")
            new = new2
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print(f"{changed} files updated")


if __name__ == "__main__":
    main()
