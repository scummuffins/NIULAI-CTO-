# Relaunching 牛来 (NIULAI) on BNB Smart Chain

The original contract cannot be salvaged. This is the walkthrough for deploying a clean one and
moving every holder across at the same token id.

## Why the original contract is not reusable

All of this is verifiable on-chain today:

* **Only the owner can fix it.** `setBaseURI` (`0x55f804b3`) is `onlyOwner`. Simulated from any
  other address it reverts with `0x118cdaa7` (`OwnableUnauthorizedAccount`). The owner
  `0xa59b756b896e0a06efd8f8285fd972e9568d2bdd` is the party that abandoned the collection, so that
  route is closed.
* **Whoever controls it can break it again.** The same key that could restore the artwork can
  re-point it somewhere else at any time.
* **It can be bricked permanently.** `renounceOwnership` exists. Once called, `setBaseURI` becomes
  uncallable forever and no one could ever restore the art.
* **The 10% royalty is immutable.** The bytecode contains no `setDefaultRoyalty`,
  `setTokenRoyalty` or `deleteDefaultRoyalty`. 10% of every secondary sale is hardcoded to
  `0x311188bef22479ede7bd29b61a7ae7d84ba6b55c` and nobody - owner included - can ever redirect it.
* **The gateway cannot be recovered either.** `niulai.sbs` is registered through 2027-08-16 and
  parked, so `tokenURI` cannot be fixed from the DNS side.

A fresh contract costs the original on-chain history and needs re-verification on the
marketplaces. It buys back custody of the artwork, a royalty that is provably zero, and the
ability to make the metadata permanently unchangeable.

---

## Step 0 — Pin the art and metadata

Everything below assumes you are in the root of this repository.

**Rebuild the PNGs** (not committed, they are 795 MB):

```bash
python scripts/webp_to_png.py
```

**Pin the images.** Upload the whole `images_png/` folder as a *directory* to any pinning service —
Pinata, Filebase, web3.storage, 4everland. You want one CID for the directory, such that
`<cid>/0001.png` resolves. Note that CID.

> Pin on at least two services. The original collection died from exactly one pin lapsing.

**Stamp the image CID into the metadata:**

```bash
python scripts/set_image_cid.py bafybei...your-image-cid
```

That rewrites all 999 files in `metadata_rehost/` so `image` becomes
`ipfs://<your-cid>/0001.png`. Verify one before continuing:

```bash
cat metadata_rehost/368.json
```

**Pin the metadata.** Upload `metadata_rehost/` as a directory. Note that CID too. Check that
`<metadata-cid>/368.json` resolves and that its `image` field points at a PNG that also resolves.

---

## Step 1 — Deploy the contract

You need a funded deployer wallet on BNB Smart Chain (**chain id 56**). Budget ~0.05 BNB:
deployment is roughly 0.01–0.02 BNB and the airdrop is ~10 transactions.

`contracts/NiulaiV2.sol` is the contract. Compiled clean on solc 0.8.24 with no warnings.
It differs from the original in three deliberate ways:

* **Royalty is zero and can never change.** `royaltyInfo` is a hardcoded `pure` function returning
  `(address(0), 0)`. There is no royalty storage, no setter, and no internal escape hatch — a
  `pure` function cannot read state, so it can never return anything else. It still declares
  EIP-2981 so marketplaces read an explicit on-chain zero rather than falling back to their own
  configurable defaults.
* **The base URI is an `ipfs://` URI**, not a gateway domain.
* **`freezeMetadata()`** lets you permanently give up the ability to change the artwork.

### Deploy with Remix (no local toolchain)

1. Go to <https://remix.ethereum.org>, create `NiulaiV2.sol`, paste in the file from `contracts/`.
2. **Solidity Compiler** tab → version `0.8.24` or newer → *Compile*. Remix fetches the
   OpenZeppelin imports automatically.
3. **Deploy & Run** tab → Environment: *Injected Provider* → confirm your wallet is on BNB Smart
   Chain (chain id 56).
4. Select contract `NiulaiV2`. There is **one** constructor argument:

   | Argument | Value |
   |---|---|
   | `baseURI_` | `ipfs://<metadata-cid>/` — **trailing slash required** |

   There are no royalty parameters; the zero royalty is fixed in code.
5. *Deploy*, confirm in the wallet, and save the contract address.

### Confirm the royalty is zero

Right after deploying, on BscScan *Read Contract*:

```
royaltyInfo(1, 10000)  ->  (0x0000000000000000000000000000000000000000, 0)
```

Anyone can run this check, at any time, forever.

---

## Step 2 — Verify the source on BscScan

Needed for marketplaces to display it properly and for holders to trust it.

Easiest route is Remix's **Contract Verification** plugin (activate it in the plugin manager, pick
BscScan, paste a free BscScan API key). Or with Foundry:

```bash
forge verify-contract <deployed-address> NiulaiV2 --chain 56 --etherscan-api-key <key>
```

---

## Step 3 — Airdrop the existing holders

`airdrop_batches.json` holds the snapshot pre-chunked into 10 batches of ≤100 tokens. Each has a
`recipients` array and a `tokenIds` array, index-aligned and grouped by wallet. Token ids are
preserved — whoever holds #368 receives #368.

For each batch, call `airdrop` from the owner wallet (Remix *Deployed Contracts*, or BscScan
*Write Contract*), pasting the two arrays:

```
recipients: ["0x008e...", "0x00b2...", ...]
tokenIds:   [840, 56, ...]
```

Do batch 1 first and confirm it lands before sending the rest. After all 10, check
`totalSupply()` returns `999`.

### Re-taking the snapshot

Tokens keep trading, so re-snapshot close to the airdrop:

```bash
python scripts/snapshot_holders.py
python scripts/make_airdrop_batches.py 100
```

For a fair, auditable cut-off, announce a block height in advance and pin the snapshot to it:

```bash
python scripts/snapshot_holders.py --block 116665113 --rpc https://<archive-endpoint>
```

Public BNB RPCs prune state and will fail with `missing trie node` on anything more than a few
hundred blocks back, so historical snapshots need an archive endpoint (Ankr, QuickNode, Alchemy,
Chainstack, NodeReal). The script writes nothing unless all 999 tokens resolve, so a failed run
can never clobber a good snapshot.

---

## Step 4 — Lock it down

Once the art renders correctly everywhere and you are certain the CIDs are stable and pinned in
more than one place:

```
freezeMetadata()
```

One-way. After that no one — including you — can ever change the artwork. Combined with the
hardcoded zero royalty, that leaves nothing about this collection that any future key holder can
alter. That is the guarantee the original could not offer.

---

## Step 5 — Relist

* **OKX** and **Element** both index BNB Chain contracts automatically, but collection ownership,
  name, banner and socials need claiming through each platform's creator flow.
* Set marketplace-side royalties to zero to match the on-chain EIP-2981 value. On-chain zero is the
  strongest signal available, but marketplaces can still apply their own platform-level fees, so
  check each one's collection settings after claiming.
* Point holders at this repository so the recovery and the trait data are auditable.

---

## Sanity checklist

- [ ] `<image-cid>/0001.png` resolves on two independent gateways
- [ ] `<metadata-cid>/1.json` and `/999.json` both resolve
- [ ] A metadata file's `image` field resolves to a real PNG
- [ ] Base URI ends with `/`
- [ ] `tokenURI(1)` returns `…/1.json`, not `…/1`
- [ ] `royaltyInfo(1, 10000)` returns `(0x0…0, 0)`
- [ ] `totalSupply()` is 999 after the airdrop
- [ ] Source verified on BscScan
- [ ] Both CIDs pinned on at least two services, with billing that will not lapse
- [ ] `freezeMetadata()` called once you are confident
