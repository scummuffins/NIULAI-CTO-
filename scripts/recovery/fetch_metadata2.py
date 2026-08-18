#!/usr/bin/env python3
"""Fetch NIULAI metadata from the original IPFS CID using progressive cache-warming rounds.

Requesting an uncached file makes the gateway start resolving it via the DHT; a short-timeout
sweep therefore both collects what is already cached and warms the rest for the next round.
"""
import json, os, time, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CID = "bafybeibmduyrrt4y7i5kwthdg4xcdvoyytekzubc3qvxistsh5yclyycfu"
OUT = os.path.join(ROOT, "work", "metadata")
os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
GWS = ["https://ipfs.filebase.io/ipfs/{cid}/{f}",
       "https://{cid}.ipfs.dweb.link/{f}",
       "https://{cid}.ipfs.w3s.link/{f}",
       "https://{cid}.ipfs.4everland.io/{f}"]
lock = threading.Lock(); got = {"n": 0}

def have(tid):
    p = os.path.join(OUT, f"{tid}.json")
    return os.path.exists(p) and os.path.getsize(p) > 200

def grab(tid, timeout, gws):
    if have(tid): return True
    for gw in gws:
        try:
            req = urllib.request.Request(gw.format(cid=CID, f=f"{tid}.json"),
                                         headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r: raw = r.read()
            d = json.loads(raw.decode("utf8"))
            assert "attributes" in d and "image" in d and "name" in d
            open(os.path.join(OUT, f"{tid}.json"), "wb").write(raw)
            with lock: got["n"] += 1
            return True
        except Exception:
            continue
    return False

ids = list(range(1, 1000))
# (workers, timeout, gateways) — short sweeps first to warm the gateway cache
ROUNDS = [(16, 6, GWS[:1]), (16, 12, GWS[:1]), (14, 25, GWS[:2]), (10, 45, GWS),
          (10, 60, GWS), (8, 75, GWS), (8, 90, GWS), (6, 100, GWS)]
for rn, (w, to, gws) in enumerate(ROUNDS, 1):
    todo = [i for i in ids if not have(i)]
    if not todo:
        break
    print(f"round {rn}: {len(todo)} remaining (workers={w} timeout={to}s)", flush=True)
    with ThreadPoolExecutor(max_workers=w) as ex:
        list(ex.map(lambda i: grab(i, to, gws), todo))
    print(f"  -> have {sum(have(i) for i in ids)}/999", flush=True)

missing = [i for i in ids if not have(i)]
print(f"DONE have={999-len(missing)}/999 missing={len(missing)}", flush=True)
if missing: print("MISSING:", missing, flush=True)
