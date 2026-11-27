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

---

# Session Log - Revisión de estado, normalización de docs y limpieza

**Date**: Fri Nov 27 2026
**Agent**: Subagent task for media-tracker status review fixes

## Qué se completó

- **Revisión de estado local + GitHub**: confirmado que el repo está en `main` sincronizada con `origin/main`, árbol limpio antes de empezar, y que la suite de tests pasa (147/147).
- **AGENTS.md corregido**: la sección "Contexto del proyecto" decía Flask 3.0.0; verificado contra `requirements.txt` real (Flask==3.1.3, waitress==3.0.2) y actualizado a Flask 3.1.3. El resto del archivo no se tocó.
- **`session_log_report.md` normalizado a UTF-8**: se detectó que el archivo era UTF-16 LE con BOM (120 bytes), por eso no se leía como texto. Se decodificó y se reescribió como UTF-8 sin BOM, sin pérdida de contenido. El contenido resultante es solo el título `# Informe de Calidad y Cobertura de Tests - Media Tracker` (archivo stub, no corrupto; no se inventó contenido ni se borró el archivo).
- **Artefactos de debug fuera del seguimiento de git**: `debug_dedupe.py`, `fix_dedupe.py` y `test_output.txt.bak` se quitaron del índice con `git rm --cached` (los archivos locales se conservan) y se agregaron a `.gitignore` para que no se vuelvan a trackear.
- **Verificación**: `python -m pytest` en verde antes y después de los cambios (147 passed). `git status`/`git diff` revisados antes del commit.
- **Commit**: un solo commit con todos los cambios (sin push, sin tocar ramas remotas).

## Qué quedó pendiente

- **Paginación de Prowlarr**: falta tomar la decisión registrada en `plan.md`.
- **Metadatos del repo en GitHub**: configurar licencia, descripción y topics.
- **Rama `feature/stitch-design-system`**: borrarla (quedó intacta en esta sesión).

## Decisiones

- **No borrar archivos locales**: para los artefactos de debug se usó `git rm --cached` (solo se des-indexan) en lugar de borrar, respetando la restricción de no eliminar archivos.
- **Encoding**: `session_log_report.md` se convirtió a UTF-8 sin BOM (estándar del repo); si el contenido hubiera estado ilegible se habría documentado en vez de regenerarlo.
- **Sin dependencias nuevas ni cambios de código**: la sesión se acotó a documentación, encoding y limpieza de tracking; `requirements.txt` no se modificó.
- **Commit único** con mensaje `chore:` siguiendo la convención del repo; sin push (pendiente de decisión del usuario).
