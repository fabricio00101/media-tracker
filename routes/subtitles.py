from flask import Blueprint, request, jsonify
import requests
import logging
from extensions import limiter, cache
import config
from services.subtitles import get_opensubtitles_token
from utils.security import redact_secrets

subtitles_bp = Blueprint("subtitles", __name__)

# OpenSubtitles usa ISO 639-1. Solo "es" es un código válido: "es-mx" hacía
# que la API respondiera vacío o con error según el caso.
OPENSUBTITLES_LANGUAGES = "es"


def _is_successful_response(rv):
    """Decide si una respuesta se cachea: solo las exitosas (200).

    `cache.cached` invoca `response_filter` con el valor crudo que devolvió la
    vista, que puede ser una tupla `(cuerpo, status)` o un objeto Response.
    Cachear un 400/401/429/500 lo dejaría pegado 1 hora.
    """
    if isinstance(rv, tuple):
        # (cuerpo, status) o (cuerpo, status, headers): status debe ser 200.
        if len(rv) < 2 or not isinstance(rv[1], int):
            return False
        return rv[1] == 200
    # Respuesta simple (jsonify): solo se cachea si su status es 200.
    return getattr(rv, "status_code", None) == 200


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
@cache.cached(
    timeout=config.CACHE_1H,
    query_string=True,
    response_filter=_is_successful_response,
)
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
        status = e.response.status_code if e.response is not None else 500
        if status == 401:
            return jsonify({"error": "API Key de OpenSubtitles inválida"}), 401
        if status == 429:
            return (
                jsonify({"error": "Límite de peticiones de OpenSubtitles excedido"}),
                429,
            )
        logging.error("Error de OpenSubtitles al buscar: %s", redact_secrets(e))
        return jsonify({"error": "Error de OpenSubtitles al buscar subtítulos."}), 500
    except Exception as e:
        logging.error("Error al buscar subtitulos: %s", redact_secrets(e))
        return jsonify({"error": "Error interno al buscar subtitulos"}), 500


def _request_download_link(file_id, token):
    """Pide a OpenSubtitles el link de descarga usando un token concreto."""
    url = "https://api.opensubtitles.com/api/v1/download"
    headers = {
        "Api-Key": config.OPENSUBTITLES_API_KEY,
        "Authorization": f"Bearer {token}",
        "User-Agent": "RastreadorTorrents/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return requests.post(
        url, headers=headers, json={"file_id": int(file_id)}, timeout=10
    )


@subtitles_bp.route("/api/subtitles/download")
@limiter.limit("10 per minute")
def download_subtitle():
    file_id = (request.args.get("file_id") or "").strip()
    if not file_id.isdigit():
        return jsonify({"error": "file_id inválido: debe ser numérico"}), 400

    # El login va en su propio try: si el servicio lanza (caché corrupta,
    # backend caído), devolvemos un error JSON en vez del 500 genérico de Flask.
    try:
        token = get_opensubtitles_token()
    except Exception as e:
        logging.error("Error obteniendo token de OpenSubtitles: %s", redact_secrets(e))
        return jsonify({"error": "Error interno al autenticar con OpenSubtitles"}), 500

    if not token:
        return (
            jsonify(
                {
                    "error": "No se pudo autenticar con OpenSubtitles. Revisa las credenciales USER y PASSWORD en .env"
                }
            ),
            401,
        )

    try:
        response = _request_download_link(file_id, token)

        # Token revocado o vencido antes de las 23 h: un único re-login.
        if response.status_code == 401:
            token = get_opensubtitles_token(force=True)
            if not token:
                return (
                    jsonify(
                        {
                            "error": "OpenSubtitles rechazó el token y no se pudo renovar la sesión."
                        }
                    ),
                    401,
                )
            response = _request_download_link(file_id, token)

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
        status = e.response.status_code if e.response is not None else 500
        if status == 406:
            return jsonify({"error": "Límite de descargas excedido de tu cuenta"}), 406
        logging.error("Error al descargar subtítulo: %s", redact_secrets(e))
        return (
            jsonify({"error": "Error al descargar el subtítulo desde OpenSubtitles."}),
            500,
        )
    except Exception as e:
        logging.error("Error al obtener link de descarga: %s", redact_secrets(e))
        return jsonify({"error": "Error interno al obtener link de descarga"}), 500
