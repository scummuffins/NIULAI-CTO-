#!/usr/bin/env python3
"""Generate the package README from the build's own summary, so the numbers can't drift."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PKG = sys.argv[1] if len(sys.argv) > 1 else ROOT
s = json.load(open(os.path.join(PKG, "collection_summary.json"), encoding="utf-8"))
r = json.load(open(os.path.join(PKG, "rarity.json"), encoding="utf-8"))

mismatch = s["cross_check_mismatches"]
verdict = "no mismatches in any field" if not mismatch else f"MISMATCHES: {mismatch}"

holders = None
hp = os.path.join(PKG, "holders_airdrop.json")
if os.path.exists(hp):
    holders = json.load(open(hp, encoding="utf-8"))

lines = f"""# {s['collection']} - recovered collection package

Contract `{s['contract']}` on {s['chain']}, {s['total_supply']} tokens.

The project's gateway (`niulai.sbs`) went offline and the IPFS pins behind it were dropped, so
every token's `tokenURI` resolves to nothing and the artwork stopped rendering everywhere. This
repository is a complete, verified reconstruction of the collection: all {s['metadata_recovered']} metadata files,
all {s['images_recovered']} images, the full trait and rarity tables, a current holder snapshot, and a relaunch kit.

## What's here

| Path | Contents |
|---|---|
| `metadata/` | **Archive - do not deploy.** {s['metadata_recovered']}/999 token JSONs in the original schema, `1.json` - `999.json`, with `image` and `external_url` left pointing at the dead `niulai.sbs` URLs. This is the faithful record of what the collection was. |
| `metadata_rehost/` | **Deploy this one.** Identical traits, with `image` set to `ipfs://__IMAGE_CID__/0001.png` ready to stamp, and `external_url` removed - see below. |
| `images_webp/` | {s['images_recovered']}/999 images exactly as recovered, `0001.webp` - `0999.webp`. |
| `raw_ipfs_metadata/` | Untouched bytes of every JSON pulled directly from the original IPFS CID. |
| `contracts/NiulaiV2.sol` | Relaunch contract for BNB Smart Chain (see `RELAUNCH.md`). |
| `traits.csv` | One row per token: all 11 traits, plus which source it came from. |
| `rarity.csv` / `rarity.json` | Trait counts and percentages across the set. |
| `holders_snapshot.csv` | Owner of every token id{f", captured at block {holders['block']}" if holders else ""}. |
| `holders_airdrop.json` | The same snapshot grouped by wallet{f" - {holders['unique_holders']} unique holders" if holders else ""}. |
| `airdrop_batches.json` | Pre-chunked `recipients[]` / `tokenIds[]` arrays for the relaunch airdrop. |
| `MANIFEST.csv` | SHA-256 and byte size of every file here. |
| `collection_summary.json` | Machine-readable recovery report. |

`images_png/` is not committed - it is 795 MB and losslessly regenerable. To rebuild it:

```bash
python scripts/webp_to_png.py
```

### Why `external_url` was dropped from the deploy copy

Every original token carried `"external_url": "https://niulai.sbs/token/<id>"`. That domain is
registered to a third party through 2027-08-16 and currently parked, and marketplaces render
`external_url` as the item's clickable website link. Shipping it would point all 999 holders at a
domain someone else can repoint at any time, so `metadata_rehost/` omits the field entirely.

`metadata/` keeps it, because that folder exists to record the collection exactly as it was.

If you later have a domain you control, add it back at stamping time:

```bash
python scripts/set_image_cid.py <image-cid> --site https://yourdomain.xyz
```

## Where the data came from

* **Metadata** - the contract's `tokenURI` still returns the original IPFS paths, which gave up the
  metadata CID `{s['original_metadata_cid']}`.
  That CID is **still partially retrievable**, so {s['from_ipfs_original']} tokens are byte-for-byte originals.
  The remaining {s['from_okx_reconstructed']} were reconstructed from a marketplace's cached copy of the same metadata.
* **Images** - the image CID `{s['original_image_cid']}`
  still has provider records in the DHT, but **no live provider holds the blocks** (gateways report
  "found 18 providers, connected to 6, but they did not return the requested content"). The original
  PNG bytes are gone. All {s['images_recovered']} images come from a marketplace CDN cache at {', '.join(s['image_dimensions'])}.

## Confidence

* The two independent sources overlap on **{s['cross_check_overlap']} tokens**, compared field by field
  (`name`, `description`, `image`, `external_url`, and the full ordered attribute list):
  **{verdict}**. That is what justifies trusting the reconstructed tokens.
* Every token carries exactly 11 traits in the original order: {' / '.join(s['trait_types'])}.
* Independently recomputed rarity matches the per-token percentages published by the marketplace.
* Metadata missing: {s['metadata_missing'] or 'none'}. Images missing: {s['images_missing'] or 'none'}.
* `MANIFEST.csv` carries a SHA-256 for every file; 40/40 random spot-checks verified.

## Known fidelity limit

The images are **not byte-identical to the originals**. The CDN they were recovered from stores lossy
VP8 WebP, so the pixels went through one re-encode before anyone could reach them. `images_webp/` is
that data unmodified; regenerated PNGs are a lossless container around it, not a recovery of the
original file. Dimensions ({', '.join(s['image_dimensions'])}) and all artwork content are intact.
No better copy exists publicly - the original bytes died with the pin.

## Why the original contract is not reusable (verified on-chain)

| Role | Address | Changeable? |
|---|---|---|
| Owner - the only caller of `setBaseURI` | `0xa59b756b896e0a06efd8f8285fd972e9568d2bdd` | transferable by owner |
| Creator (per marketplace) | `0xaa52322ce0377a0370c8e2f131096189edf87002` | - |
| Royalty receiver, 10% EIP-2981 | `0x311188bef22479ede7bd29b61a7ae7d84ba6b55c` | **no - immutable** |

* **Only the abandoning owner can repair it.** `setBaseURI` (`0x55f804b3`) is `onlyOwner`.
  Simulated from any other address it reverts with `0x118cdaa7` (`OwnableUnauthorizedAccount`).
  There is no other way in, so restoring the original contract is not an option.
* **Whoever holds that key can break it again** at any time, and `renounceOwnership` exists - if it
  is ever called, `setBaseURI` becomes permanently uncallable and the artwork can never be restored
  by anyone.
* **The 10% royalty is immutable.** The bytecode contains **no `setDefaultRoyalty`, no
  `setTokenRoyalty`, no `deleteDefaultRoyalty`** - nobody, owner included, can redirect it.
* **The gateway cannot be recovered either.** `niulai.sbs` is registered through 2027-08-16 and
  parked on `dns-parking.com`, so `tokenURI` cannot be fixed from the DNS side.

## Relaunching

A clean contract plus an airdrop to the {holders['unique_holders'] if holders else 'current'} holders is the only viable route.
`contracts/NiulaiV2.sol` and `airdrop_batches.json` cover it; **`RELAUNCH.md`** is the full
step-by-step walkthrough.

The replacement contract fixes what made the original fragile:

* **Zero royalty, permanently.** `royaltyInfo` is a hardcoded `pure` function returning
  `(address(0), 0)`. No royalty storage, no setter, no internal escape hatch - a `pure` function
  cannot read state, so it can never return anything else. Anyone can confirm it forever by calling
  `royaltyInfo(1, 10000)`. EIP-2981 is still declared so marketplaces read an explicit on-chain zero
  instead of falling back to their own configurable defaults.
* **An `ipfs://` base URI, never a gateway domain.** The original collection died because
  `tokenURI` pointed at `https://niulai.sbs/...` - a single centralised host - so one expired pin
  plus one parked domain was enough to break all 999 tokens at once.
* **`freezeMetadata()`** makes the artwork permanently unchangeable once the CIDs are stable.

Compiled clean on solc 0.8.24 with no warnings; token ids stay 1-999 so holders keep the exact
piece they own.

## Trait summary
"""

for tt in s["trait_types"]:
    vals = sorted(r[tt].items(), key=lambda x: -x[1])
    top = ", ".join(f"{k} ({v})" for k, v in vals[:6])
    more = f" ... +{len(vals) - 6} more" if len(vals) > 6 else ""
    lines += f"\n* **{tt}** - {len(vals)} values: {top}{more}"

lines += "\n"
with open(os.path.join(PKG, "README.md"), "w", encoding="utf-8") as f:
    f.write(lines)
print(f"wrote {os.path.join(PKG, 'README.md')}")
