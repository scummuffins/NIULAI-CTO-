#!/usr/bin/env python3
"""Turn the holder snapshot into ready-to-paste airdrop() batches.

Produces out/package/airdrop_batches.json: a list of {recipients: [...], tokenIds: [...]}
pairs, each small enough for one BNB Chain transaction. Paste the two arrays straight
into Remix / BscScan's writeContract form for NiulaiV2.airdrop.
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PKG = ROOT
BATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 100

rows = list(csv.DictReader(open(os.path.join(PKG, "holders_snapshot.csv"), encoding="utf-8")))
pairs = [(int(r["token_id"]), r["owner"]) for r in rows if r["owner"]]
missing = [r["token_id"] for r in rows if not r["owner"]]
if missing:
    sys.exit(f"snapshot incomplete, {len(missing)} tokens unresolved: {missing[:10]}")

# group by owner so each holder's tokens land together - cheaper and easier to eyeball
pairs.sort(key=lambda p: (p[1], p[0]))

batches = []
for i in range(0, len(pairs), BATCH):
    chunk = pairs[i:i + BATCH]
    batches.append({
        "batch": len(batches) + 1,
        "count": len(chunk),
        "recipients": [o for _, o in chunk],
        "tokenIds": [t for t, _ in chunk],
    })

with open(os.path.join(PKG, "airdrop_batches.json"), "w", encoding="utf-8") as f:
    json.dump({"total_tokens": len(pairs), "batch_size": BATCH,
               "batches": len(batches), "data": batches}, f, indent=2)

print(f"{len(pairs)} tokens -> {len(batches)} batches of up to {BATCH}")
print(f"wrote {os.path.join(PKG, 'airdrop_batches.json')}")
print("\nbatch 1 preview:")
print("  recipients:", json.dumps(batches[0]["recipients"][:3])[:-1] + ", ...]")
print("  tokenIds  :", json.dumps(batches[0]["tokenIds"][:3])[:-1] + ", ...]")
