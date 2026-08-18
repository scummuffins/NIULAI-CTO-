#!/usr/bin/env python3
"""Cross-verify IPFS originals against OKX's cache, then build the final NIULAI package."""
import csv, hashlib, io, json, os, shutil
from collections import Counter, defaultdict
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = ROOT
OUT = os.path.join(BASE, "out")
META, OKX, IMGS = (os.path.join(OUT, d) for d in ("metadata", "okx", "images"))
PKG = os.path.join(OUT, "package")
META_CID = "bafybeibmduyrrt4y7i5kwthdg4xcdvoyytekzubc3qvxistsh5yclyycfu"
IMG_CID = "bafybeiaxbf5pzat7tyitaaodoombb5vrrg5iipbwgbppfz36ncutilxp4y"
TRAIT_ORDER = ["稀有度", "角色", "姿势", "五官", "贴图", "衣服", "配饰", "背景", "特效", "见证者", "画质"]
IDS = list(range(1, 1000))


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def from_okx(tid):
    """Rebuild the original metadata schema from OKX's cached record."""
    p = os.path.join(OKX, f"{tid}.json")
    if not os.path.exists(p):
        return None
    d = load(p).get("data") or {}
    sp = d.get("specialProperties")
    if not sp:
        return None
    props = json.loads(sp) if isinstance(sp, str) else sp
    if not props:
        return None
    # OKX normalises the ASCII '#' to fullwidth '#' - undo that to match the originals
    return {
        "name": (d.get("name") or "").replace("\uff03", "#"),
        "description": (d.get("info") or "").replace("\uff03", "#"),
        "image": f"https://niulai.sbs/ipfs/{IMG_CID}/{tid:04d}.png",
        "attributes": [{"trait_type": p["name"], "value": p["key"]} for p in props],
        "external_url": f"https://niulai.sbs/token/{tid}",
    }


# ------------------------------------------------------------------ 1. load sources
orig, okx = {}, {}
for t in IDS:
    p = os.path.join(META, f"{t}.json")
    if os.path.exists(p) and os.path.getsize(p) > 200:
        try:
            orig[t] = load(p)
        except Exception:
            pass
    r = from_okx(t)
    if r:
        okx[t] = r
print(f"sources: ipfs-original={len(orig)}  okx-reconstructed={len(okx)}")

# ------------------------------------------------------------------ 2. cross-verify
overlap = sorted(set(orig) & set(okx))
mismatch = defaultdict(list)
for t in overlap:
    a, b = orig[t], okx[t]
    for f in ("name", "description", "image", "external_url"):
        if a.get(f) != b.get(f):
            mismatch[f].append(t)
    if [(x["trait_type"], x["value"]) for x in a["attributes"]] != \
       [(x["trait_type"], x["value"]) for x in b["attributes"]]:
        mismatch["attributes"].append(t)
verdict = "ALL FIELDS MATCH" if not mismatch else "MISMATCHES " + str({k: len(v) for k, v in mismatch.items()})
print(f"cross-check on {len(overlap)} overlapping tokens: {verdict}")
for k, v in mismatch.items():
    print(f"   {k}: first 10 -> {v[:10]}")

# ------------------------------------------------------------------ 3. merge
final, provenance = {}, {}
for t in IDS:
    if t in orig:
        final[t], provenance[t] = orig[t], "ipfs-original"
    elif t in okx:
        final[t], provenance[t] = okx[t], "okx-reconstructed"
missing = [t for t in IDS if t not in final]
print(f"final metadata: {len(final)}/999  missing={missing if missing else 'none'}")

# ------------------------------------------------------------------ 4. integrity checks
problems = []
for t, m in final.items():
    ats = m.get("attributes", [])
    if len(ats) != 11:
        problems.append(f"#{t}: {len(ats)} attributes (expected 11)")
    if [a["trait_type"] for a in ats] != TRAIT_ORDER:
        problems.append(f"#{t}: trait order/names differ")
    if m.get("name") != f"\u725b\u6765 #{t:04d}":
        problems.append(f"#{t}: unexpected name {m.get('name')!r}")
    if not m.get("image", "").endswith(f"/{t:04d}.png"):
        problems.append(f"#{t}: image path mismatch")
print("schema check: " + ("OK - every token has the 11 traits in the original order"
                          if not problems else str(problems[:10])))

# ------------------------------------------------------------------ 5. build package
for sub in ("metadata", "metadata_rehost", "images_png", "images_webp", "raw_ipfs_metadata"):
    os.makedirs(os.path.join(PKG, sub), exist_ok=True)

img_report = []
for t in IDS:
    src = os.path.join(IMGS, f"{t}.webp")
    if not os.path.exists(src):
        img_report.append((t, "MISSING", "", 0))
        continue
    raw = open(src, "rb").read()
    dst_png = os.path.join(PKG, "images_png", f"{t:04d}.png")
    dst_webp = os.path.join(PKG, "images_webp", f"{t:04d}.webp")
    if os.path.exists(dst_png) and os.path.getsize(dst_png) > 2000 and os.path.exists(dst_webp):
        with Image.open(dst_png) as im:          # header-only read, no re-encode
            img_report.append((t, "ok", f"{im.width}x{im.height}", len(raw)))
        continue
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    shutil.copyfile(src, dst_webp)
    im.save(dst_png, "PNG", optimize=True)
    img_report.append((t, "ok", f"{im.width}x{im.height}", len(raw)))

for t, m in final.items():
    with open(os.path.join(PKG, "metadata", f"{t}.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    rh = dict(m)
    rh["image"] = f"ipfs://__IMAGE_CID__/{t:04d}.png"
    with open(os.path.join(PKG, "metadata_rehost", f"{t}.json"), "w", encoding="utf-8") as f:
        json.dump(rh, f, ensure_ascii=False, indent=2)
    p = os.path.join(META, f"{t}.json")
    if os.path.exists(p):
        shutil.copyfile(p, os.path.join(PKG, "raw_ipfs_metadata", f"{t}.json"))

# ------------------------------------------------------------------ 6. traits + rarity
counts = defaultdict(Counter)
for t, m in final.items():
    for a in m["attributes"]:
        counts[a["trait_type"]][a["value"]] += 1
n = len(final)

with open(os.path.join(PKG, "traits.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["token_id", "name", "source"] + TRAIT_ORDER)
    for t in IDS:
        if t not in final:
            continue
        m = final[t]
        d = {a["trait_type"]: a["value"] for a in m["attributes"]}
        w.writerow([t, m["name"], provenance[t]] + [d.get(k, "") for k in TRAIT_ORDER])

with open(os.path.join(PKG, "rarity.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["trait_type", "value", "count", "percent"])
    for tt in TRAIT_ORDER:
        for v, c in counts[tt].most_common():
            w.writerow([tt, v, c, f"{c / n * 100:.2f}%"])

with open(os.path.join(PKG, "rarity.json"), "w", encoding="utf-8") as f:
    json.dump({tt: dict(counts[tt]) for tt in TRAIT_ORDER}, f, ensure_ascii=False, indent=2)

# validate computed rarity against OKX's published percentages
dev = []
for t in list(okx)[:400]:
    p = os.path.join(OKX, f"{t}.json")
    for pr in json.loads(load(p)["data"]["specialProperties"]):
        mine = counts[pr["name"]][pr["key"]] / n * 100
        theirs = float(pr["percentage"].rstrip("%"))
        if abs(mine - theirs) > 0.75:
            dev.append((pr["name"], pr["key"], round(mine, 2), theirs))
print(f"rarity vs OKX published percentages: {'consistent' if not dev else str(len(set(dev))) + ' deviations'}")
for d in list(dict.fromkeys(dev))[:8]:
    print("   ", d)

# ------------------------------------------------------------------ 7. manifest + summary
with open(os.path.join(PKG, "MANIFEST.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["file", "bytes", "sha256"])
    for root, _, files in os.walk(PKG):
        for fn in sorted(files):
            if fn == "MANIFEST.csv":
                continue
            fp = os.path.join(root, fn)
            b = open(fp, "rb").read()
            w.writerow([os.path.relpath(fp, PKG).replace("\\", "/"), len(b), hashlib.sha256(b).hexdigest()])

ok_imgs = [r for r in img_report if r[1] == "ok"]
dims = Counter(r[2] for r in ok_imgs)
summary = {
    "collection": "\u725b\u6765 NFT (NIULAI)",
    "contract": "0x5fd0d8fecf408f61080cea470249026d3e02fb3d",
    "chain": "BNB Smart Chain (56)",
    "total_supply": 999,
    "original_metadata_cid": META_CID,
    "original_image_cid": IMG_CID,
    "metadata_recovered": len(final),
    "from_ipfs_original": sum(1 for v in provenance.values() if v == "ipfs-original"),
    "from_okx_reconstructed": sum(1 for v in provenance.values() if v == "okx-reconstructed"),
    "images_recovered": len(ok_imgs),
    "image_dimensions": dict(dims),
    "images_missing": [r[0] for r in img_report if r[1] == "MISSING"],
    "metadata_missing": missing,
    "trait_types": TRAIT_ORDER,
    "cross_check_overlap": len(overlap),
    "cross_check_mismatches": {k: len(v) for k, v in mismatch.items()},
}
with open(os.path.join(PKG, "collection_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"\nimages: {len(ok_imgs)}/999  dims={dict(dims)}  missing={summary['images_missing'][:10]}")
print(f"package -> {PKG}")
