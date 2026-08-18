#!/usr/bin/env python3
"""Snapshot the owner of every token, for an airdrop on a relaunched contract.

    python scripts/snapshot_holders.py                      # current chain tip
    python scripts/snapshot_holders.py --block 116665113    # fixed historical block
    python scripts/snapshot_holders.py --rpc https://...    # use your own endpoint

Pinning a block makes the snapshot reproducible and auditable: announce the height in advance,
take it afterwards, and anyone can re-run this and get identical output.

IMPORTANT: public BNB Chain RPCs are *pruned*. They only keep recent state, so `--block` fails
with "missing trie node" / "header not found" for anything more than a few hundred blocks back.
For historical snapshots pass an archive endpoint with --rpc (Ankr, QuickNode, Alchemy, Chainstack
and NodeReal all offer BSC archive access).

Outputs are only written if all 999 tokens resolve, so a partial run can never clobber a good
snapshot. holders_airdrop.json is stamped with the block height used.
"""
import csv, json, os, sys, threading, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

CONTRACT = "0x5fd0d8fecf408f61080cea470249026d3e02fb3d"
DEFAULT_RPCS = ["https://bsc-dataseed.binance.org/", "https://bsc-dataseed1.defibit.io/",
                "https://bsc-dataseed1.ninicoin.io/", "https://bsc-rpc.publicnode.com"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = ROOT
IDS = list(range(1, 1000))

RPCS = [sys.argv[sys.argv.index("--rpc") + 1]] if "--rpc" in sys.argv else DEFAULT_RPCS
lock = threading.Lock()
owners = {}
errors = []


def rpc(method, params, rpc_url):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc_url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def owner_of(tid):
    data = "0x6352211e" + f"{tid:064x}"          # ownerOf(uint256)
    last = None
    for attempt in range(6):
        url = RPCS[attempt % len(RPCS)]
        try:
            r = rpc("eth_call", [{"to": CONTRACT, "data": data}, BLOCK_TAG], url)
            if "error" in r:
                last = r["error"].get("message")
                continue
            res = r.get("result")
            if not res or len(res) < 66:
                last = f"short result {res!r}"
                continue
            with lock:
                owners[tid] = "0x" + res[-40:]
            return
        except Exception as e:
            last = str(e)
    with lock:
        owners[tid] = None
        errors.append(last)


if "--block" in sys.argv:
    block = int(sys.argv[sys.argv.index("--block") + 1])
    BLOCK_TAG = hex(block)
    print(f"snapshot pinned to block {block} ({BLOCK_TAG})")
else:
    block = int(rpc("eth_blockNumber", [], RPCS[0])["result"], 16)
    BLOCK_TAG = "latest"
    print(f"snapshot at current tip, block {block}")

with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(owner_of, IDS))

missing = [t for t in IDS if not owners.get(t)]
if missing:
    print(f"\nFAILED: only {999 - len(missing)}/999 tokens resolved - nothing written.")
    seen = list(dict.fromkeys(e for e in errors if e))[:3]
    for e in seen:
        print(f"  RPC said: {e}")
    if BLOCK_TAG != "latest":
        print("\n  A pinned block needs an ARCHIVE node; public BNB RPCs prune old state.")
        print("  Retry with:  --block <n> --rpc https://<your-archive-endpoint>")
    sys.exit(1)

with open(os.path.join(PKG, "holders_snapshot.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["token_id", "owner"])
    for t in IDS:
        w.writerow([t, owners[t]])

by_owner = defaultdict(list)
for t in IDS:
    by_owner[owners[t]].append(t)
with open(os.path.join(PKG, "holders_airdrop.json"), "w", encoding="utf-8") as f:
    json.dump({"block": block, "contract": CONTRACT, "unique_holders": len(by_owner),
               "holders": {k: sorted(v) for k, v in sorted(by_owner.items(), key=lambda x: -len(x[1]))}},
              f, indent=2)

print(f"resolved 999/999 tokens, {len(by_owner)} unique holders at block {block}")
if BLOCK_TAG == "latest":
    print(f"  -> to reproduce this snapshot later: --block {block} --rpc <archive-endpoint>")
for a, ts in sorted(by_owner.items(), key=lambda x: -len(x[1]))[:5]:
    print(f"  {a}  {len(ts)} tokens")
