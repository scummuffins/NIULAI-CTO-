# Relaunching 牛来 (NIULAI) on BNB Smart Chain

Two ways forward. Read the trade-off before picking one — it is not reversible.

| | Path A — repair the original | Path B — fresh contract |
|---|---|---|
| Needs the owner private key | **yes** | no |
| Keeps token ids 1–999 | yes | yes |
| Keeps on-chain history & provenance | yes | no |
| Keeps existing listings / floor | yes | no, needs re-verification |
| Who receives the 10% royalty | fixed forever at `0x311188be…b55c` | whoever you choose |
| Can it be broken again | yes — owner can re-point or renounce | no, once you call `freezeMetadata()` |

Path A is one transaction. Path B is the only option if the owner key is unreachable.

---

## Step 0 — Pin the art and metadata (both paths need this)

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

## Path A — repair the original contract

Only the owner address `0xa59b756b896e0a06efd8f8285fd972e9568d2bdd` can do this.

1. Open <https://bscscan.com/address/0x5fd0d8fecf408f61080cea470249026d3e02fb3d#writeContract>
2. Connect the owner wallet.
3. Call `setBaseURI` with the **trailing slash included**:
   ```
   ipfs://<metadata-cid>/
   ```
4. Confirm. Costs a few cents of BNB.
5. Check `tokenURI(368)` under *Read Contract* — it should return `ipfs://<metadata-cid>/368.json`.
6. Refresh metadata on each marketplace (OKX and Element both have a "refresh metadata" action per
   item; collection-wide refreshes usually need a support request).

Done. Every token renders again, history intact. The 10% royalty keeps flowing to
`0x311188be…b55c` — that is immutable and nothing can change it.

---

## Path B — deploy a fresh contract on BNB Chain

### B1. What you need

* A funded deployer wallet on BNB Smart Chain (**chain id 56**). Budget ~0.05 BNB: deployment is
  roughly 0.01–0.02 BNB and the airdrop is ~10 transactions.
* The contract at `contracts/NiulaiV2.sol`.
* `airdrop_batches.json` — the current holders, pre-chunked into 10 batches of ≤100 tokens.

`NiulaiV2.sol` differs from the original in three deliberate ways: the base URI is an `ipfs://` URI
rather than a gateway domain, the royalty receiver is changeable, and `freezeMetadata()` lets you
permanently give up the ability to alter the art.

### B2. Deploy with Remix (no local toolchain)

1. Go to <https://remix.ethereum.org>, create `NiulaiV2.sol`, paste in the file from `contracts/`.
2. **Solidity Compiler** tab → version `0.8.24` or newer → *Compile*. Remix fetches the
   OpenZeppelin imports automatically.
3. **Deploy & Run** tab → Environment: *Injected Provider* → confirm your wallet is on BNB Smart
   Chain (chain id 56).
4. Select contract `NiulaiV2` and fill the three constructor arguments:

   | Argument | Value |
   |---|---|
   | `baseURI_` | `ipfs://<metadata-cid>/` — **trailing slash required** |
   | `royaltyReceiver` | the address that should receive secondary royalties |
   | `royaltyBps` | `1000` for 10%, matching the original |

5. *Deploy*, confirm in the wallet, and save the contract address.

### B3. Verify the source on BscScan

Needed for marketplaces to display it properly and for holders to trust it.

Easiest route is Remix's **Contract Verification** plugin (activate it in the plugin manager, pick
BscScan, paste a free BscScan API key). Or with Foundry:

```bash
forge verify-contract <deployed-address> NiulaiV2 --chain 56 --etherscan-api-key <key>
```

### B4. Airdrop to the existing holders

`airdrop_batches.json` contains 10 batches. Each has a `recipients` array and a `tokenIds` array,
index-aligned, grouped by wallet. Token ids are preserved — whoever holds #368 today receives #368.

For each batch, call `airdrop` from the owner wallet (Remix *Deployed Contracts*, or BscScan
*Write Contract*), pasting the two arrays:

```
recipients: ["0x008e...", "0x00b2...", ...]
tokenIds:   [840, 56, ...]
```

Do batch 1 first and confirm it lands before sending the rest. After all 10, check
`totalSupply()` returns `999`.

To re-snapshot holders first — worth doing if time has passed, since tokens keep trading:

```bash
python scripts/snapshot_holders.py
python scripts/make_airdrop_batches.py 100
```

### B5. Lock it down

Once the art renders correctly everywhere and you are certain the CIDs are stable and pinned in
more than one place:

```
freezeMetadata()
```

One-way. After that no one — including you — can ever change the artwork. That is the guarantee the
original collection could not offer, and it is the strongest signal to holders that this cannot
happen twice.

### B6. Relist

* **OKX** and **Element** both index BNB Chain contracts automatically, but collection ownership,
  royalties, name, banner and socials need claiming through each platform's creator flow.
* Set royalties on the marketplace side to match the on-chain EIP-2981 value.
* Point holders at this repository so the recovery and the trait data are auditable.

---

## Sanity checklist

- [ ] `<image-cid>/0001.png` resolves on two independent gateways
- [ ] `<metadata-cid>/1.json` and `/999.json` both resolve
- [ ] A metadata file's `image` field resolves to a real PNG
- [ ] Base URI ends with `/`
- [ ] `tokenURI(1)` returns `…/1.json`, not `…/1`
- [ ] Path B only: `totalSupply()` is 999 after the airdrop
- [ ] Path B only: source verified on BscScan
- [ ] Both CIDs pinned on at least two services, with billing that will not lapse
