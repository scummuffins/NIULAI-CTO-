# 牛来 NFT (NIULAI) - recovered collection package

Contract `0x5fd0d8fecf408f61080cea470249026d3e02fb3d` on BNB Smart Chain (56), 999 tokens.

The project's gateway (`niulai.sbs`) went offline and the IPFS pins behind it were dropped, so
every token's `tokenURI` resolves to nothing and the artwork stopped rendering everywhere. This
repository is a complete, verified reconstruction of the collection: all 999 metadata files,
all 999 images, the full trait and rarity tables, a current holder snapshot, and a relaunch kit.

## What's here

| Path | Contents |
|---|---|
| `metadata/` | **Archive - do not deploy.** 999/999 token JSONs in the original schema, `1.json` - `999.json`, with `image` and `external_url` left pointing at the dead `niulai.sbs` URLs. This is the faithful record of what the collection was. |
| `metadata_rehost/` | **Deploy this one.** Identical traits, with `image` set to `ipfs://__IMAGE_CID__/0001.png` ready to stamp, and `external_url` removed - see below. |
| `images_webp/` | 999/999 images exactly as recovered, `0001.webp` - `0999.webp`. |
| `raw_ipfs_metadata/` | Untouched bytes of every JSON pulled directly from the original IPFS CID. |
| `contracts/NiulaiV2.sol` | Relaunch contract for BNB Smart Chain (see `RELAUNCH.md`). |
| `traits.csv` | One row per token: all 11 traits, plus which source it came from. |
| `rarity.csv` / `rarity.json` | Trait counts and percentages across the set. |
| `holders_snapshot.csv` | Owner of every token id, captured at block 116668329. |
| `holders_airdrop.json` | The same snapshot grouped by wallet - 358 unique holders. |
| `airdrop_batches.json` | Pre-chunked `recipients[]` / `tokenIds[]` arrays for the relaunch airdrop. |
| `MANIFEST.csv` | SHA-256 and byte size of every file here. |
| `collection_summary.json` | Machine-readable recovery report. |

`images_png/` is not committed - it is 795 MB and losslessly regenerable. To rebuild it:

```bash
python scripts/webp_to_png.py
```

### How the deploy copy differs from the archive

`metadata_rehost/` is identical to `metadata/` in name, traits and trait order. Exactly three
fields differ, all deliberately:

**1. `image`** - points at `ipfs://__IMAGE_CID__/<id>.png` for stamping, instead of the dead
`niulai.sbs` URL.

**2. `external_url` - removed.** Every original token carried
`"external_url": "https://niulai.sbs/token/<id>"`. That domain is registered to a third party
through 2027-08-16 and currently parked, and marketplaces render `external_url` as the item's
clickable website link - shipping it would point all 999 holders at a domain someone else can
repoint at any time. To add one back for a domain you control:

```bash
python scripts/set_image_cid.py <image-cid> --site https://yourdomain.xyz
```

**3. `description` - the royalty promise is dropped.** The originals all ended with
`，二级市场 10% 版税每小时买入 $牛来 并自动分发给持有者。` ("10% secondary royalty buys the token
hourly and auto-distributes to holders"). The relaunch contract has a permanently zero royalty, so
that clause would be a promise the contract cannot keep. The deploy copy ends at `共 999 枚。`
instead; character, rarity and supply text are untouched.

`metadata/` keeps all three original values, because that folder exists to record the collection
exactly as it was.

## Where the data came from

* **Metadata** - the contract's `tokenURI` still returns the original IPFS paths, which gave up the
  metadata CID `bafybeibmduyrrt4y7i5kwthdg4xcdvoyytekzubc3qvxistsh5yclyycfu`.
  That CID is **still partially retrievable**, so 937 tokens are byte-for-byte originals.
  The remaining 62 were reconstructed from a marketplace's cached copy of the same metadata.
* **Images** - the image CID `bafybeiaxbf5pzat7tyitaaodoombb5vrrg5iipbwgbppfz36ncutilxp4y`
  still has provider records in the DHT, but **no live provider holds the blocks** (gateways report
  "found 18 providers, connected to 6, but they did not return the requested content"). The original
  PNG bytes are gone. All 999 images come from a marketplace CDN cache at 1024x1024.

## Confidence

* The two independent sources overlap on **937 tokens**, compared field by field
  (`name`, `description`, `image`, `external_url`, and the full ordered attribute list):
  **no mismatches in any field**. That is what justifies trusting the reconstructed tokens.
* Every token carries exactly 11 traits in the original order: 稀有度 / 角色 / 姿势 / 五官 / 贴图 / 衣服 / 配饰 / 背景 / 特效 / 见证者 / 画质.
* Independently recomputed rarity matches the per-token percentages published by the marketplace.
* Metadata missing: none. Images missing: none.
* `MANIFEST.csv` carries a SHA-256 for every file; 40/40 random spot-checks verified.

## Known fidelity limit

The images are **not byte-identical to the originals**. The CDN they were recovered from stores lossy
VP8 WebP, so the pixels went through one re-encode before anyone could reach them. `images_webp/` is
that data unmodified; regenerated PNGs are a lossless container around it, not a recovery of the
original file. Dimensions (1024x1024) and all artwork content are intact.
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

A clean contract plus an airdrop to the 358 holders is the only viable route.
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

* **稀有度** - 4 values: 普通 (854), 稀有 (122), 史诗 (19), 传说 (4)
* **角色** - 7 values: 牛来 (236), 路人牛 (213), 豹拉 (181), 牛妈 (127), 灵蛇 (96), 狼狗 (90) ... +1 more
* **姿势** - 3 values: 直立呆站 (511), T-pose残留 (302), 单手举起 (186)
* **五官** - 5 values: 豆眼 (407), 死鱼眼 (256), 斗鸡眼 (142), 五星眼 (98), 少了一只眼 (96)
* **贴图** - 4 values: 原厂贴图 (622), UV接缝可见 (209), 贴图丢失 (150), 牛市金身 (18)
* **衣服** - 14 values: 无 (377), 红披风 (87), 黑皮夹克 (62), 股民西装马甲 (60), 校服外套 (56), 红领巾 (54) ... +8 more
* **配饰** - 24 values: 无 (194), 电影票根 (96), 保龄球果子 (52), 方向盘 (52), 牛奶瓶 (45), 一把韭菜 (44) ... +18 more
* **背景** - 17 values: 大平地 (151), 影厅 (92), 梦境 (75), 悬崖推土车 (69), 牛角古树 (65), 荒漠 (63) ... +11 more
* **特效** - 6 values: 无 (416), 弹幕 (205), 加场印章 (112), 票房计数器 (94), 穿模标注 (90), 涨停标签 (82)
* **见证者** - 2 values: 云雀缺席 (580), 云雀在场 (419)
* **画质** - 2 values: 影院翻拍 (562), 片源直出 (437)
