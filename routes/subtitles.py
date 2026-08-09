from flask import Blueprint, request, jsonify
import requests
import logging
from extensions import limiter, cache
import config
from services.subtitles import get_opensubtitles_token

subtitles_bp = Blueprint("subtitles", __name__)

@subtitles_bp.route("/api/subtitles/search")
@limiter.limit("10 per minute")
@cache.cached(timeout=config.CACHE_1H, query_string=True)
def search_subtitles():
    tmdb_id = request.args.get("tmdb_id")
    if not tmdb_id:
        return jsonify({"error": "Se requiere un TMDB ID"}), 400

    if not config.OPENSUBTITLES_API_KEY:
        return (
            jsonify({"error": "API Key de OpenSubtitles no configurada en el servidor"}),
            401,
        )

    url = "https://api.opensubtitles.com/api/v1/subtitles"
    params = {"tmdb_id": tmdb_id, "languages": "es,es-mx"}

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
    file_id = request.args.get("file_id")
    if not file_id:
        return jsonify({"error": "file_id is required"}), 400

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
        return jsonify({"link": data.get("link")})
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 406:
            return jsonify({"error": "Límite de descargas excedido de tu cuenta"}), 406
        return jsonify({"error": f"Error al descargar: {e}"}), 500
    except Exception as e:
        logging.error(f"Error al obtener link de descarga: {e}")
        return jsonify({"error": "Error interno al obtener link de descarga"}), 500
