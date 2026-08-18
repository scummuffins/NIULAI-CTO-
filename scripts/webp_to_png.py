#!/usr/bin/env python3
"""Regenerate images_png/ from the committed images_webp/.

The PNGs are ~795 MB and losslessly derivable, so they are not committed. This rebuilds
them with the original 0001.png .. 0999.png naming.
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "images_webp")
DST = os.path.join(ROOT, "images_png")
os.makedirs(DST, exist_ok=True)

made = skipped = 0
for i in range(1, 1000):
    s = os.path.join(SRC, f"{i:04d}.webp")
    d = os.path.join(DST, f"{i:04d}.png")
    if not os.path.exists(s):
        print(f"missing source {s}")
        continue
    if os.path.exists(d) and os.path.getsize(d) > 2000:
        skipped += 1
        continue
    with Image.open(s) as im:
        im.convert("RGBA").save(d, "PNG", optimize=True)
    made += 1
    if made % 100 == 0:
        print(f"  {made} converted", flush=True)

print(f"done: {made} written, {skipped} already present -> {DST}")
