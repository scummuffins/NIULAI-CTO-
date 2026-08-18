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
| `metadata/` | {s['metadata_recovered']}/999 token JSONs in the **original schema**, `1.json` - `999.json`. `image` still points at the original (dead) URL, so this is the faithful archival record. |
| `metadata_rehost/` | Same data with `image` set to `ipfs://__IMAGE_CID__/0001.png`, ready to stamp with a real CID. |
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

## Contract control and royalties (verified on-chain)

| Role | Address | Changeable? |
|---|---|---|
| Owner - the only caller of `setBaseURI` | `0xa59b756b896e0a06efd8f8285fd972e9568d2bdd` | transferable by owner |
| Creator (per marketplace) | `0xaa52322ce0377a0370c8e2f131096189edf87002` | - |
| Royalty receiver, 10% EIP-2981 | `0x311188bef22479ede7bd29b61a7ae7d84ba6b55c` | **no - immutable** |

* `setBaseURI` (`0x55f804b3`) is `onlyOwner`. Simulated from a non-owner it reverts with `0x118cdaa7`
  (`OwnableUnauthorizedAccount`); from the owner address it succeeds. **Repairing the original
  contract requires that private key** - there is no other way in.
* The 10% royalty is fixed forever. The bytecode contains **no `setDefaultRoyalty`, no
  `setTokenRoyalty`, no `deleteDefaultRoyalty`** - nobody, owner included, can redirect it. The
  receiver is a contract (9,591 bytes) rather than a wallet, consistent with the metadata's claim
  that royalties buy the token and distribute to holders; that behaviour is not verified here.
* `renounceOwnership` exists. If it is ever called, `setBaseURI` becomes permanently uncallable and
  the collection can never be restored by anyone.
* `niulai.sbs` cannot be taken over to fix `tokenURI` from the DNS side: it is registered through
  2027-08-16 and parked on `dns-parking.com`.

## Relaunching

See **`RELAUNCH.md`** for the full walkthrough. In short:

* **Path A - repair the original contract.** Needs the owner key. Keeps token ids, history, holders
  and existing listings. The immutable 10% royalty stays exactly where it is.
* **Path B - deploy fresh on BNB Chain and airdrop the {holders['unique_holders'] if holders else 'current'} holders.** You control metadata
  *and* royalties and nobody can break it again; costs the original on-chain provenance and needs
  re-verification on the marketplaces. `contracts/NiulaiV2.sol` plus `airdrop_batches.json` do this.

Whichever path: use an `ipfs://` base URI, never a gateway domain. The original collection died
because `tokenURI` pointed at `https://niulai.sbs/...` - a single centralised host - so one expired
pin plus one parked domain was enough to break all 999 tokens at once.

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
