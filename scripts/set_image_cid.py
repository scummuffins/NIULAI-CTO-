#!/usr/bin/env python3
"""Stamp a real image CID into the rehost metadata.

The recovered metadata ships with an `ipfs://__IMAGE_CID__/...` placeholder. After you upload
images_png/ to IPFS and get a directory CID, run:

    python scripts/set_image_cid.py bafybei...yournewcid
    python scripts/set_image_cid.py bafybei...yournewcid --ext webp
    python scripts/set_image_cid.py bafybei...yournewcid --site https://yourdomain.xyz

It rewrites every metadata_rehost/<id>.json so that
    "image": "ipfs://<newcid>/0001.png"

--site is optional and adds back an `external_url` of `<site>/token/<id>`. It is left out by
default on purpose: the original `external_url` pointed at niulai.sbs, which is registered to a
third party and parked, and marketplaces turn that field into the item's clickable website link.
Only pass --site for a domain you control.

Re-run any time with a different CID; the script is idempotent.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "metadata_rehost")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    argv = sys.argv

    ext = argv[argv.index("--ext") + 1] if "--ext" in argv else "png"
    site = argv[argv.index("--site") + 1].rstrip("/") if "--site" in argv else None

    if not args:
        sys.exit("usage: set_image_cid.py <image-dir-cid> [--ext png|webp] [--site https://...]")
    cid = args[0].removeprefix("ipfs://").strip("/")
    if not re.fullmatch(r"(Qm[1-9A-HJ-NP-Za-km-z]{44}|ba[a-z2-7]{57,})", cid):
        sys.exit(f"'{cid}' does not look like a CIDv0/CIDv1")
    if site and not site.startswith(("http://", "https://")):
        sys.exit(f"--site must be a full URL, got '{site}'")
    if site and "niulai.sbs" in site:
        sys.exit("refusing to set external_url to niulai.sbs - that domain is not yours")

    n = 0
    for fn in sorted(os.listdir(PKG), key=lambda x: int(x.split(".")[0])):
        p = os.path.join(PKG, fn)
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        tid = int(fn.split(".")[0])
        d["image"] = f"ipfs://{cid}/{tid:04d}.{ext}"
        if site:
            d["external_url"] = f"{site}/token/{tid}"
        else:
            d.pop("external_url", None)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        n += 1

    print(f"rewrote {n} files -> ipfs://{cid}/<0001..0999>.{ext}")
    print(f"external_url: {site + '/token/<id>' if site else 'omitted (no trusted domain set)'}")
    print("\nnext: upload metadata_rehost/ as a directory, then deploy NiulaiV2 with")
    print('      baseURI_ = "ipfs://<metadata-dir-cid>/"   (trailing slash required)')


if __name__ == "__main__":
    main()
