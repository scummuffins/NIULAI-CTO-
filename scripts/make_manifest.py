#!/usr/bin/env python3
"""Regenerate MANIFEST.csv last, so it covers every finished file including the README."""
import csv, hashlib, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PKG = sys.argv[1] if len(sys.argv) > 1 else ROOT
SKIP_DIRS = {".git", "__pycache__", "images_png", "work", "logs"}
rows = []
for root, dirs, files in os.walk(PKG):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for fn in sorted(files):
        if fn == "MANIFEST.csv":
            continue
        fp = os.path.join(root, fn)
        with open(fp, "rb") as f:
            b = f.read()
        rows.append([os.path.relpath(fp, PKG).replace("\\", "/"), len(b), hashlib.sha256(b).hexdigest()])

rows.sort(key=lambda r: r[0])
with open(os.path.join(PKG, "MANIFEST.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["file", "bytes", "sha256"])
    w.writerows(rows)
print(f"manifest: {len(rows)} files, {sum(r[1] for r in rows) / 1e6:.1f} MB")
