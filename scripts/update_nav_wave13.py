#!/usr/bin/env python3
"""One-off: insert the Agents link into every site <nav> block (primary + mobile + footer).

Run once after wave 13. Also updates the NAV/FOOTNAV constants inside
scripts/build_*.py so future regenerations keep the link.

Rule: an "API" link immediately followed by a newline + another link is a
site nav entry (breadcrumbs read "API / Circle" and are skipped). The Agents
link goes right after the API link with matching indentation and prefix.
"""
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/aster-da-master")
SUBDIRS = ("releases", "years", "circle", "codex", "sessions")

API_RE = re.compile(
    r'^(?P<indent>[ \t]*)<a href="(?P<prefix>(?:\.\./)?)api-playground\.html"[^>]*>API</a>\n',
    re.MULTILINE,
)


def prefix_for(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return "../" if rel and rel[0] in SUBDIRS else ""


def insert_agents(text: str, prefix: str) -> str:
    def repl(m):
        if m.group("prefix") != prefix:
            return m.group(0)
        indent = m.group("indent")
        return (
            m.group(0)
            + f'{indent}<a href="{prefix}agents.html">Agents</a>\n'
        )
    return API_RE.sub(repl, text)


def main():
    changed = 0
    targets = sorted(ROOT.rglob("*.html")) + sorted((ROOT / "scripts").glob("build_*.py"))
    for path in targets:
        if "__pycache__" in path.parts:
            continue
        if path.name == "agents.html":
            continue  # already ships the link
        text = path.read_text(encoding="utf-8")
        if "agents.html" in text:
            continue
        prefix = prefix_for(path) if path.suffix == ".html" else ""
        new = insert_agents(text, prefix)
        # .py generators carry both "" and "../" variants; apply both
        if path.suffix == ".py":
            new = insert_agents(new, "../")
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print(f"nav updated in {changed} files")


if __name__ == "__main__":
    main()
