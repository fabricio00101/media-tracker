import os

dedupe_path = r"F:\Proyectos\media-tracker\utils\dedupe.py"
with open(dedupe_path, "r", encoding="utf-8") as f:
    content = f.read()

compat_function = """
def apply_deduplication_to_processed(prepared_entries):
    from . import select_deduplicated_indices as _sd
    indices, stats = _sd(prepared_entries)
    simple_torrents = []
    for idx in sorted(indices):
        entry = prepared_entries[idx]
        simple_torrents.append({
            "title": entry.get("title", ""),
            "magnet": entry.get("magnet", ""),
            "seeders": entry.get("seeders", 0) or 0,
            "size_bytes": entry.get("size_bytes", entry.get("size", 0)) or 0,
            "indexer": entry.get("tracker", "Desconocido"),
        })
    deduped = deduplicate_torrents(simple_torrents)
    removed = len(simple_torrents) - len(deduped)
    stats = {
        "original_count": len(simple_torrents),
        "after_dedup": len(deduped),
        "removed": removed,
        "by_infohash": 0,
        "by_name_size": 0,
    })
    return deduped, stats
"""

if "def apply_deduplication_to_processed" not in content:
    with open(dedupe_path, "w", encoding="utf-8") as f:
        f.write(content + compat_function)
    print("Added apply_deduplication_to_processed compatibility function")
else:
    print("Already exists")