from flask import Blueprint, request, jsonify
import threading

from extensions import limiter, cache
import config
from services.tmdb import get_tmdb_info
from services.prowlarr_service import fetch_prowlarr, ProwlarrError
from services.search_service import (
    build_cache_key,
    process_results,
    resolve_titles,
    sort_results,
)
from utils.validators import validate_search_params, ValidationError
from utils.language_detector import detect_spanish, detect_audio, matches_language

# Exportaciones para mantener retrocompatibilidad total con tests existentes
_detect_spanish = detect_spanish
_detect_audio = detect_audio
_matches_language = matches_language
_process_results = process_results
_build_cache_key = build_cache_key


def _resolve_titles(unique_titles):
    """Inyecta la dependencia de TMDB desde este módulo.

    services.search_service ya no importa routes.search; los tests pueden
    seguir parcheando routes.search.get_tmdb_info.
    """
    return resolve_titles(unique_titles, resolver=get_tmdb_info)


search_bp = Blueprint("search", __name__)

# --- Control de concurrencia (evita el efecto "cache stampede") ----------------
# El registro vive en la memoria del proceso. Con varios workers/procesos no se
# comparte; para eso haría falta un lock distribuido (Redis). Con un único
# proceso evita las consultas duplicadas sin retener locks durante el I/O.
_inflight_guard = threading.Lock()
_inflight_events = {}


def _join_or_lead(cache_key):
    """Devuelve (evento, es_líder). No retiene locks durante las llamadas de red."""
    with _inflight_guard:
        event = _inflight_events.get(cache_key)
        if event is None:
            event = threading.Event()
            _inflight_events[cache_key] = event
            return event, True
        return event, False


def _release_lead(cache_key, event):
    """Quita el registro y despierta a los seguidores que esperaban."""
    with _inflight_guard:
        _inflight_events.pop(cache_key, None)
    event.set()


def _compute_results(
    query,
    category,
    min_size_gb,
    quality_tag,
    require_hdr,
    require_hevc,
    lang_filters,
    min_bpp,
    sdr_only,
):
    """Consulta Prowlarr y procesa los resultados (puede lanzar ProwlarrError)."""
    results_data = _fetch_prowlarr(query, category)
    return process_results(
        results_data,
        category,
        min_size_gb,
        quality_tag,
        require_hdr,
        require_hevc,
        lang_filters,
        min_bpp,
        sdr_only,
        resolver=get_tmdb_info,
    )


def _load_results(
    cache_key,
    query,
    category,
    min_size_gb,
    quality_tag,
    require_hdr,
    require_hevc,
    lang_filters,
    min_bpp,
    sdr_only,
):
    """Devuelve el conjunto de resultados deduplicando búsquedas idénticas."""
    final_results = cache.get(cache_key)
    if final_results is not None:
        return final_results

    event, es_lider = _join_or_lead(cache_key)
    if es_lider:
        try:
            # Doble chequeo: otro hilo pudo completarlo justo antes.
            final_results = cache.get(cache_key)
            if final_results is None:
                final_results = _compute_results(
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
                cache.set(cache_key, final_results, timeout=config.CACHE_5MIN)
            return final_results
        finally:
            _release_lead(cache_key, event)

    # Seguidor: espera sin mantener locks. Si el líder falló, calcula él mismo.
    event.wait(timeout=120)
    final_results = cache.get(cache_key)
    if final_results is not None:
        return final_results
    return _compute_results(
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


def _fetch_prowlarr(query, category):
    """Wrapper retrocompatible para tests que parchean routes.search._fetch_prowlarr."""
    return fetch_prowlarr(query, category)


def _format_error(message, code):
    """Devuelve un payload de error consistente con mensaje plano y estructura para clientes enriquecidos."""
    return {"error": message, "error_detail": {"code": code, "message": message}}


@search_bp.route("/api/search")
# Cuota holgada: comparten el contador la búsqueda en tiempo real (debounce
# de 1200 ms), el botón "Cargar más" (páginas > 1) y los reintentos del
# frontend. Con 30/min se agotaba en uso normal.
@limiter.limit("60 per minute")
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
    try:
        final_results = _load_results(
            cache_key,
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
    except ProwlarrError as e:
        return jsonify(_format_error(e.message, e.code)), e.status

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
