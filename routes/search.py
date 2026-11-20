from contextlib import contextmanager
from flask import Blueprint, request, jsonify
import threading
import requests

from extensions import limiter, cache
import config
from services.tmdb import get_tmdb_info
from services.prowlarr_service import fetch_prowlarr, ProwlarrError
from services.search_service import (
    build_cache_key,
    process_results,
    resolve_titles,
    sort_results,
    DEFAULT_PER_PAGE,
    MAX_PER_PAGE,
)
from utils.validators import validate_search_params, ValidationError
from utils.language_detector import detect_spanish, detect_audio, matches_language

# Exportaciones para mantener retrocompatibilidad total con tests existentes
_detect_spanish = detect_spanish
_detect_audio = detect_audio
_matches_language = matches_language
_resolve_titles = resolve_titles
_process_results = process_results
_build_cache_key = build_cache_key

search_bp = Blueprint("search", __name__)

# --- Control de concurrencia (evita el efecto "cache stampede") ----------------
_inflight_guard = threading.Lock()
_inflight_entries = {}


@contextmanager
def _inflight_lock(key):
    """Context manager que asegura el ciclo de vida del lock de búsqueda."""
    with _inflight_guard:
        if key not in _inflight_entries:
            _inflight_entries[key] = {"lock": threading.Lock(), "refcount": 0}
        entry = _inflight_entries[key]
        entry["refcount"] += 1

    lock = entry["lock"]
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()
        with _inflight_guard:
            entry["refcount"] -= 1
            if entry["refcount"] <= 0:
                _inflight_entries.pop(key, None)


def _fetch_prowlarr(query, category):
    """Wrapper retrocompatible para tests que parchean routes.search.requests.get o _fetch_prowlarr."""
    return fetch_prowlarr(query, category)


def _format_error(message, code):
    """Devuelve un payload de error consistente con mensaje plano y estructura para clientes enriquecidos."""
    return {"error": message, "error_detail": {"code": code, "message": message}}


@search_bp.route("/api/search")
@limiter.limit("30 per minute")
def search():
    if not config.PROWLARR_API_KEY:
        return (
            jsonify(
                _format_error(
                    "La API Key de Prowlarr no está configurada en el servidor. Revisa el archivo .env.",
                    "PROWLARR_KEY_MISSING",
                )
            ),
            500,
        )

    try:
        params = validate_search_params(request.args)
    except ValidationError as e:
        return jsonify(_format_error(e.message, e.code)), e.status

    query = params["query"]
    category = params["category"]
    min_size_gb = params["min_size_gb"]
    quality_tag = params["quality_tag"]
    require_hdr = params["require_hdr"]
    require_hevc = params["require_hevc"]
    lang_filters = params["lang_filters"]
    sdr_only = params["sdr_only"]
    min_bpp = params["min_bpp"]
    sort = params["sort"]
    page = params["page"]
    per_page = params["per_page"]

    cache_key = build_cache_key(
        query,
        category,
        min_size_gb,
        quality_tag,
        require_hdr,
        require_hevc,
        lang_filters,
        min_bpp,
        sdr_only,
    )

    # 1) Lectura rápida: si ya está en caché no se toca ningún lock
    final_results = cache.get(cache_key)

    if final_results is None:
        with _inflight_lock(cache_key):
            # 2) Doble chequeo: mientras esperábamos el lock, otro hilo pudo
            #    haber completado exactamente la misma búsqueda
            final_results = cache.get(cache_key)

            if final_results is None:
                try:
                    # Usamos _fetch_prowlarr para preservar parches de unittest en routes.search
                    results_data = _fetch_prowlarr(query, category)
                except ProwlarrError as e:
                    return jsonify(_format_error(e.message, e.code)), e.status

                final_results = process_results(
                    results_data,
                    category,
                    min_size_gb,
                    quality_tag,
                    require_hdr,
                    require_hevc,
                    lang_filters,
                    min_bpp,
                    sdr_only,
                )

                # Guardar el conjunto completo (la paginación no altera la clave)
                cache.set(cache_key, final_results, timeout=config.CACHE_5MIN)

    # El orden se aplica fuera de la caché: un mismo conjunto sirve para
    # cualquier criterio sin duplicar entradas en memoria.
    final_results = sort_results(final_results, sort)

    # 3) Paginar los grupos procesados
    total_groups = len(final_results)
    total_torrents = sum(len(group["torrents"]) for group in final_results)
    start = (page - 1) * per_page
    end = start + per_page
    page_results = final_results[start:end]

    return jsonify(
        {
            "results": page_results,
            "page": page,
            "per_page": per_page,
            "total_groups": total_groups,
            "total_torrents": total_torrents,
            "has_more": end < total_groups,
        }
    )
