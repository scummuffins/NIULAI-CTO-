# Recovery scripts

These document how the collection was pulled back together and are kept for auditability.
They expect a `work/` directory at the repo root holding the raw scraped sources
(`work/metadata`, `work/okx`, `work/images`), which is not committed.

* `fetch_metadata2.py` - pulls metadata from the original IPFS CID using progressive
  cache-warming rounds, since most of it needs a slow DHT lookup on first request.
* `fetch_okx.py` - pulls the marketplace's cached asset records and full-size images.
* `build_package.py` - cross-verifies the two sources field by field, merges them, and
  emits the metadata, trait and rarity tables in this repo.
