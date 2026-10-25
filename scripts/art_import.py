#!/usr/bin/env python3
"""Turn the artist's own cover files into the sizes the site uses.
Put originals (png/jpg/webp, any size, square) in art-source/ named like the release page
slug, e.g. art-source/gravestone.png. Then:  python3 scripts/art_import.py
Writes assets/art/<slug>-480.webp, -960.webp, -1440.webp (never upscales)."""
import sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "art-source", ROOT / "assets" / "art"
OUT.mkdir(parents=True, exist_ok=True)
n = 0
for f in sorted(SRC.glob("*")) if SRC.exists() else []:
    if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"): continue
    im = Image.open(f).convert("RGB")
    w, h = im.size
    s = min(w, h); im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    for t in (480, 960, 1440):
        if s < t and t != 480: continue
        im.resize((min(t, s),) * 2, Image.LANCZOS).save(OUT / f"{f.stem}-{t}.webp", "WEBP", quality=82, method=6)
    n += 1; print("ok", f.stem, s)
print(n, "covers")
