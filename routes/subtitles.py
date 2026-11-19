from flask import Blueprint, request, jsonify
import requests
import logging
from extensions import limiter, cache
import config
from services.subtitles import get_opensubtitles_token

subtitles_bp = Blueprint("subtitles", __name__)

# OpenSubtitles usa ISO 639-1. Solo "es" es un código válido: "es-mx" hacía
# que la API respondiera vacío o con error según el caso.
OPENSUBTITLES_LANGUAGES = "es"


def _build_subtitles_params(tmdb_id, media_type, season, episode):
    """Construye los parámetros de búsqueda de OpenSubtitles.

    Películas: se buscan por `tmdb_id`.
    Series: requieren `parent_tmdb_id` + `season_number` + `episode_number`;
    buscar una serie por `tmdb_id` devuelve resultados sin relación.
    """
    params = {"languages": OPENSUBTITLES_LANGUAGES}

    if media_type == "tv":
        params.update(
            {
                "type": "episode",
                "parent_tmdb_id": int(tmdb_id),
                "season_number": int(season),
                "episode_number": int(episode),
            }
        )
    else:
        params.update({"type": "movie", "tmdb_id": int(tmdb_id)})

    return params


@subtitles_bp.route("/api/subtitles/search")
@limiter.limit("10 per minute")
@cache.cached(timeout=config.CACHE_1H, query_string=True)
def search_subtitles():
    tmdb_id = (request.args.get("tmdb_id") or "").strip()
    media_type = (request.args.get("media_type") or "movie").strip().lower()
    season = (request.args.get("season") or "").strip()
    episode = (request.args.get("episode") or "").strip()

    # Un id no numérico (típicamente "undefined" cuando falta TMDB_API_KEY)
    # terminaba generando enlaces de búsqueda basura en OpenSubtitles.
    if not tmdb_id.isdigit():
        return (
            jsonify(
                {
                    "error": "TMDB ID inválido: debe ser numérico. "
                    "Verifica que TMDB_API_KEY esté configurada en .env."
                }
            ),
            400,
        )

    if media_type not in ("movie", "tv"):
        media_type = "movie"

    if media_type == "tv" and not (season.isdigit() and episode.isdigit()):
        return (
            jsonify(
                {"error": "Para series se requieren temporada y episodio."}
            ),
            400,
        )

    if not config.OPENSUBTITLES_API_KEY:
        return (
            jsonify(
                {
                    "error": "OpenSubtitles no está configurado: "
                    "falta OPENSUBTITLES_API_KEY en .env."
                }
            ),
            401,
        )

    url = "https://api.opensubtitles.com/api/v1/subtitles"
    params = _build_subtitles_params(tmdb_id, media_type, season, episode)

    headers = {
        "Api-Key": config.OPENSUBTITLES_API_KEY,
        "User-Agent": "RastreadorTorrents/1.0",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return jsonify({"error": "API Key de OpenSubtitles inválida"}), 401
        elif e.response.status_code == 429:
            return (
                jsonify({"error": "Límite de peticiones de OpenSubtitles excedido"}),
                429,
            )
        return jsonify({"error": f"Error de OpenSubtitles: {e}"}), 500
    except Exception as e:
        logging.error(f"Error al buscar subtitulos: {e}")
        return jsonify({"error": "Error interno al buscar subtitulos"}), 500


@subtitles_bp.route("/api/subtitles/download")
@limiter.limit("10 per minute")
def download_subtitle():
    file_id = (request.args.get("file_id") or "").strip()
    if not file_id.isdigit():
        return jsonify({"error": "file_id inválido: debe ser numérico"}), 400

    token = get_opensubtitles_token()
    if not token:
        return (
            jsonify(
                {
                    "error": "No se pudo autenticar con OpenSubtitles. Revisa las credenciales USER y PASSWORD en .env"
                }
            ),
            401,
        )

    url = "https://api.opensubtitles.com/api/v1/download"
    headers = {
        "Api-Key": config.OPENSUBTITLES_API_KEY,
        "Authorization": f"Bearer {token}",
        "User-Agent": "RastreadorTorrents/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"file_id": int(file_id)}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        link = data.get("link")
        if not link:
            return (
                jsonify(
                    {"error": "OpenSubtitles no devolvió un enlace de descarga."}
                ),
                502,
            )
        return jsonify({"link": link})
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 406:
            return jsonify({"error": "Límite de descargas excedido de tu cuenta"}), 406
        return jsonify({"error": f"Error al descargar: {e}"}), 500
    except Exception as e:
        logging.error(f"Error al obtener link de descarga: {e}")
        return jsonify({"error": "Error interno al obtener link de descarga"}), 500
