# Session Log - Torrent Deduplication Implementation

**Date**: Wed Nov 25 2026  
**Agent**: Subagent task for media-tracker deduplication

## What Was Completed

### 1. Deduplication Policy and Design

Implemented deduplication of torrents between Prowlarr indexers to prevent inflated counts and duplicate rows. The core policy:

- **Primary key**: `infohash` extracted from `magnet:?xt=urn:btih:...` URL. If present and not generic (20-42 hex chars), used as the unique identifier.
- **Fallback**: When no valid infohash, normalize title + size with tolerance. Uses `_normalize_name()` (lowercase, replace `.`/`-` by space, collapse spaces) and size buckets rounded to 0.5 GB intervals to avoid false positives on generic sizes like "4.7 GB".
- **When duplicating**: Conserve the torrent with **more seeders**. Size is not doubled — the winner's size is kept. Duplicate seeders are not counted toward the group total.
- **Totals impact**: `total_torrents` and per-group seeders counts only count unique torrents. Pagination (`total_torrents`, `has_more`) reflects deduplicated counts.
- **Performance**: O(n) using dicts/sets, no O(n²) nested loops. About ~500 torrents per request handled efficiently.
- **Border cases**: Infohash < 20 chars → fallback. Magnets without `xt` → fallback. Sizes within 15% relative tolerance → candidate for dedup. Same infohash but different indexers → keep high-seeders version.

### 2. Files Created/Modified

**New file: `utils/dedupe.py`**
- `extract_infohash(magnet_url)` — extracts infohash from magnet URI, returns None if invalid/short
- `_normalize_name(title)` — normalizes title for approximate comparison
- `_size_tolera(t1, t2)` — relative size tolerance check (15%)
- `deduplicate_torrents(torrents, get_*_fn)` — core dedup by infohash then fallback; returns cleaned list
- `select_deduplicated_indices(prepared_entries)` — analyzes `prepared` list (output of first pass in `process_results`) and returns `(winner_indices, stats)` set of indices to keep + removal stats
- `apply_deduplication_to_processed(prepared_entries)` — retained for compatibility, delegates to `select_deduplicated_indices`

**Modified file: `services/search_service.py`**
- Added import: `from utils.dedupe import select_deduplicated_indices`
- In `process_results()`, after the first pass (filter/parse) and before TMDB resolution:
  - Call `select_deduplicated_indices(prepared)` to identify duplicate entries
  - Filter `prepared` to keep only winner entries (those with most seeders per infohash/name+size)
  - This reduces the set before TMDB metadata resolution and group building

**New file: `tests/test_dedupe.py`**
- 13 tests covering:
  - `extract_infohash`: basic, bad length, empty, no xt
  - `_normalize_name`: basic normalization
  - `select_deduplicated_indices`: infohash winner, tie by seeders, fallback name+size, no duplicates, stats fields
  - Integration tests: search without duplicates, same torrent on different indexers (seeders max not sum), false positive generic size doesn't dedup

### 3. Test Results

- **134/134** existing tests pass (test_search.py + test_search_cache.py)
- **13/13** new deduplication tests pass
- **147/147** total tests pass across the entire suite
- No existing tests were modified; all new tests are additive

### 4. Risks and Limitations

| Risk | Severity | Description |
|------|----------|-------------|
| Infohash extraction fails on non-standard magnets | Low | Falls back to title+size comparison; still provides deduplication |
| Size tolerance (15%) too wide / too narrow | Medium | Tested with generic "4.7 GB" scenarios; 15% balances false positives vs. real different releases |
| Same title + same size from different releases | Low | Size bucketing (0.5 GB intervals) helps differentiate; fallback also checks full title normalized |
| Performance with very large result sets (>500) | Low | Currently O(n); verified up to ~500 torrents per request |
| Interference with existing cache stampede logic | None | Deduplication happens before cache check; cache key unchanged |

## Policy Chosen and Why

The deduplication policy was designed to balance three competing needs:

1. **Eliminate inflated counts**: Same torrent appearing in multiple indexers should not double-count seeders or rows.
2. **Avoid false positives**: Two different releases with similar names and sizes (e.g., a 4.7 GB movie vs. another 4.7 GB movie) should NOT be deduped unless they're truly the same. The 15% relative tolerance + 0.5 GB bucketing handles this.
3. **Keep the best version**: When the same torrent appears on multiple indexers, keep the one with more seeders (more reliable/active). Size is not doubled.

The infohash-based approach is the most reliable when available (it's the actual BT info hash). The fallback by normalized name + size is the safety net for magnets without infohash or poorly formatted URIs.

## Files Changed

| File | Type | Description |
|------|------|-------------|
| `utils/dedupe.py` | New | Deduplication helper with infohash extraction, name normalization, and selection logic |
| `services/search_service.py` | Modified | Added dedup call in `process_results()` after first pass, before TMDB resolution |
| `tests/test_dedupe.py` | New | 13 tests covering all dedup paths and edge cases |

## Verification Commands

```bash
# Core search tests (must pass)
python -m pytest tests/test_search.py tests/test_search_cache.py -q

# Full test suite
python -m pytest -q  # 147 passed
```