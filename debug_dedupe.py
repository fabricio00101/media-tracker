from utils.dedupe import select_deduplicated_indices, _normalize_name, extract_infohash

torrents = [
    {
        "title": "Peli.2023.1080p.WEBRip.x264",
        "magnet": "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAA",
        "seeders": 10,
        "indexer": "T1",
        "size_bytes": 1500000000,
    },
    {
        "title": "Peli.2023.1080p.WEBRip.x264",
        "magnet": "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAA",
        "seeders": 25,
        "indexer": "T2",
        "size_bytes": 1500000000,
    },
]

simples = []
for idx, entry in enumerate(torrents):
    magnet = entry["magnet"]
    simples.append(
        {
            "original_index": idx,
            "title": entry["title"],
            "magnet": magnet,
            "seeders": entry["seeders"],
            "size_bytes": entry["size_bytes"],
            "indexer": entry["indexer"],
        }
    )

print("=== Phase 1: infohash ===")
infohash_winners = {}
absorbed_by_ih = set()

for s in simples:
    ih = extract_infohash(s["magnet"])
    print(f'Entry idx={s["original_index"]}: infohash={ih}, seeders={s["seeders"]}')
    if ih is not None:
        if ih in infohash_winners:
            winner = infohash_winners[ih]
            print(
                f'  -> Already have winner idx={winner["original_index"]} with seeders={winner["seeders"]}'
            )
            if s["seeders"] > winner["seeders"]:
                print(
                    f'  -> New one has more seeders ({s["seeders"]} > {winner["seeders"]}), replacing'
                )
                absorbed_by_ih.add(winner["original_index"])
                infohash_winners[ih] = s
                print(
                    f'  -> Updated winner to idx={s["original_index"]} with seeders={s["seeders"]}'
                )
            else:
                print(
                    f'  -> Current winner keeps spot ({winner["seeders"]} >= {s["seeders"]})'
                )
                absorbed_by_ih.add(s["original_index"])
        else:
            infohash_winners[ih] = s
            print(f'  -> First entry with this infohash, setting as winner')

print(f'infohash_winners keys: {list(infohash_winners.keys())}')
for k, v in infohash_winners.items():
    print(f'  infohash {k[:10]}...: winner idx={v["original_index"]}, seeders={v["seeders"]}')
print(f'absorbed_by_ih: {absorbed_by_ih}')

print()
print("=== Phase 2: fallback ===")
fallback_winners = {}

for s in simples:
    if s["original_index"] in absorbed_by_ih:
        print(f'Entry idx={s["original_index"]}: SKIPPED (absorbed by infohash)')
        continue
    norm_title = _normalize_name(s["title"])
    size_gb = s["size_bytes"] / (1024 ** 3)
    size_bucket = int(round(size_gb * 2))
    key = (norm_title, size_bucket)
    print(
        f'Entry idx={s["original_index"]}: norm_title={norm_title}, size_bucket={size_bucket}, key={key}'
    )

    if key in fallback_winners:
        winner = fallback_winners[key]
        print(
            f'  -> Already have winner idx={winner["original_index"]} with seeders={winner["seeders"]}'
        )
        if s["seeders"] > winner["seeders"]:
            print(f'  -> New one has more seeders, replacing')
            fallback_winners[key] = s
        else:
            print(f'  -> Current winner keeps spot')
    else:
        print(f'  -> First entry with this key, setting as winner')
        fallback_winners[key] = s

print(f'fallback_winners: {fallback_winners}')

print()
print("=== Phase 3: winner indices ===")
winner_indices = set()
for s in infohash_winners.values():
    print(f'Adding infohash winner idx={s["original_index"]}')
    winner_indices.add(s["original_index"])
for s in fallback_winners.values():
    in_absorbed = s["original_index"] in absorbed_by_ih
    print(f' Fallback winner idx={s["original_index"]}: absorbed={in_absorbed}')
    if not in_absorbed:
        winner_indices.add(s["original_index"])

print(f'Final winner_indices: {winner_indices}')
print()
print('--- Running full select_deduplicated_indices ---')
indices, stats = select_deduplicated_indices(torrents)
print(f'indices: {indices}')
print(f'stats: {stats}')