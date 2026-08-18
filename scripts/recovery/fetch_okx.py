#!/usr/bin/env python3
"""Scrape OKX cached asset data + full-size images for the NIULAI collection."""
import json, os, time, threading, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONTRACT = "0x5fd0d8fecf408f61080cea470249026d3e02fb3d"
BASE = os.path.join(ROOT, "work")
JDIR, IDIR = os.path.join(BASE, "okx"), os.path.join(BASE, "images")
for d in (JDIR, IDIR): os.makedirs(d, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HDR = {"User-Agent": UA, "Accept": "application/json", "Referer": "https://web3.okx.com/"}
lock = threading.Lock(); n = {"j": 0, "i": 0, "f": 0}

def get(url, hdr=HDR, timeout=40):
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

def work(tid):
    jp = os.path.join(JDIR, f"{tid}.json")
    # --- 1. asset JSON (traits + image uuid) ---
    if not (os.path.exists(jp) and os.path.getsize(jp) > 500):
        for a in range(5):
            try:
                url = (f"https://web3.okx.com/priapi/v1/nft/detail-info?contractAddress={CONTRACT}"
                       f"&tokenId={tid}&chain=56&looker=&t={int(time.time()*1000)}")
                raw = get(url)
                d = json.loads(raw.decode("utf8"))
                if d.get("code") != 0 or not d.get("data"): raise ValueError("bad payload")
                open(jp, "wb").write(raw); break
            except Exception:
                time.sleep(2 * (a + 1))
        else:
            with lock: n["f"] += 1
            print(f"JSON FAIL {tid}", flush=True); return
    with lock: n["j"] += 1
    # --- 2. full-size image (bare url = 1024x1024) ---
    ip = os.path.join(IDIR, f"{tid}.webp")
    if os.path.exists(ip) and os.path.getsize(ip) > 2000:
        with lock: n["i"] += 1
        return
    try:
        cover = json.load(open(jp, encoding="utf8"))["data"]["coverUrl"]
    except Exception:
        return
    if not cover:
        print(f"NO COVER {tid}", flush=True); return
    bare = cover.split("/type=")[0]                     # strip size variant -> full res
    for a in range(5):
        try:
            img = get(bare, hdr={"User-Agent": UA, "Referer": "https://web3.okx.com/"}, timeout=60)
            if len(img) < 2000 or img[:4] not in (b"RIFF", b"\x89PNG", b"\xff\xd8\xff\xe0", b"GIF8"):
                raise ValueError("not an image")
            open(ip, "wb").write(img)
            with lock:
                n["i"] += 1
                if n["i"] % 50 == 0: print(f"  json={n['j']} img={n['i']} fail={n['f']}", flush=True)
            return
        except Exception:
            time.sleep(2 * (a + 1))
    with lock: n["f"] += 1
    print(f"IMG FAIL {tid}", flush=True)

ids = list(range(1, 1000))
print(f"OKX scrape: {len(ids)} tokens", flush=True)
with ThreadPoolExecutor(max_workers=5) as ex: list(ex.map(work, ids))
print(f"DONE json={n['j']} img={n['i']} fail={n['f']}", flush=True)
