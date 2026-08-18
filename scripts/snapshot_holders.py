#!/usr/bin/env python3
"""Snapshot the current owner of every token, for an airdrop on a relaunched contract.

Writes out/package/holders_snapshot.csv (token_id, owner) and holders_airdrop.json
(owner -> [token ids]), plus the block height the snapshot was taken at.
"""
import csv, json, os, threading, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONTRACT = "0x5fd0d8fecf408f61080cea470249026d3e02fb3d"
RPCS = ["https://bsc-dataseed.binance.org/", "https://bsc-dataseed1.defibit.io/",
        "https://bsc-dataseed1.ninicoin.io/", "https://rpc.ankr.com/bsc"]
PKG = ROOT
IDS = list(range(1, 1000))
lock = threading.Lock()
owners = {}


def rpc(method, params, rpc_url):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc_url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def owner_of(tid):
    data = "0x6352211e" + f"{tid:064x}"          # ownerOf(uint256)
    for attempt in range(6):
        url = RPCS[attempt % len(RPCS)]
        try:
            r = rpc("eth_call", [{"to": CONTRACT, "data": data}, "latest"], url)
            res = r.get("result")
            if not res or len(res) < 66:
                raise ValueError(r.get("error"))
            addr = "0x" + res[-40:]
            with lock:
                owners[tid] = addr
            return
        except Exception:
            continue
    with lock:
        owners[tid] = None


block = int(rpc("eth_blockNumber", [], RPCS[0])["result"], 16)
print(f"snapshot at block {block}")
with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(owner_of, IDS))

missing = [t for t in IDS if not owners.get(t)]
os.makedirs(PKG, exist_ok=True)
with open(os.path.join(PKG, "holders_snapshot.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["token_id", "owner"])
    for t in IDS:
        w.writerow([t, owners.get(t) or ""])

by_owner = defaultdict(list)
for t in IDS:
    if owners.get(t):
        by_owner[owners[t]].append(t)
with open(os.path.join(PKG, "holders_airdrop.json"), "w", encoding="utf-8") as f:
    json.dump({"block": block, "contract": CONTRACT, "unique_holders": len(by_owner),
               "holders": {k: sorted(v) for k, v in sorted(by_owner.items(), key=lambda x: -len(x[1]))}},
              f, indent=2)

print(f"resolved {999 - len(missing)}/999 tokens, {len(by_owner)} unique holders"
      + (f", FAILED: {missing[:10]}" if missing else ""))
top = sorted(by_owner.items(), key=lambda x: -len(x[1]))[:5]
for a, ts in top:
    print(f"  {a}  {len(ts)} tokens")
