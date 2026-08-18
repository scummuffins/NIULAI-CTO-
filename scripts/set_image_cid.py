#!/usr/bin/env python3
"""Stamp a real image CID into the rehost metadata.

The recovered metadata still points at the dead niulai.sbs gateway. After you upload
out/package/images_png (or images_webp) to IPFS and get a directory CID, run:

    python scripts/set_image_cid.py bafybei...yournewcid [--ext png]

It rewrites every out/package/metadata_rehost/<id>.json so that
    "image": "ipfs://<newcid>/0001.png"
Re-run it any time with a different CID; the placeholder is restored on each pass.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PKG = os.path.join(ROOT, "metadata_rehost")
PLACEHOLDER = "__IMAGE_CID__"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ext = "png"
    if "--ext" in sys.argv:
        ext = sys.argv[sys.argv.index("--ext") + 1]
    if not args:
        sys.exit("usage: set_image_cid.py <image-dir-cid> [--ext png|webp]")
    cid = args[0].removeprefix("ipfs://").strip("/")
    if not re.fullmatch(r"(Qm[1-9A-HJ-NP-Za-km-z]{44}|ba[a-z2-7]{57,})", cid):
        sys.exit(f"'{cid}' does not look like a CIDv0/CIDv1")

    n = 0
    for fn in sorted(os.listdir(PKG), key=lambda x: int(x.split(".")[0])):
        p = os.path.join(PKG, fn)
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        tid = int(fn.split(".")[0])
        d["image"] = f"ipfs://{cid}/{tid:04d}.{ext}"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        n += 1
    print(f"rewrote {n} files -> ipfs://{cid}/<0001..0999>.{ext}")
    print("next: upload metadata_rehost/ as a directory, then call")
    print("      setBaseURI('ipfs://<metadata-dir-cid>/') on 0x5fd0...fb3d (owner-only)")


if __name__ == "__main__":
    main()
