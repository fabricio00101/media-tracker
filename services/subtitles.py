import threading
import time
import requests
import logging
from extensions import cache
import config
from utils.security import redact_secrets

# Evita la carrera de varios hilos pidiendo login al mismo tiempo cuando el
# token todavía no está en caché.
_token_lock = threading.Lock()


def get_opensubtitles_token(force=False):
    """Token de OpenSubtitles, cacheado 23 h.

    Con `force=True` se ignora la caché: lo usa la ruta de descarga cuando la
    API responde 401 (token revocado o expirado antes de tiempo).
    """
    with _token_lock:
        return _get_opensubtitles_token_locked(force)


def _get_opensubtitles_token_locked(force=False):
    if not force:
        token_data = cache.get("opensubtitles_token_data")
        if token_data:
            token, timestamp = token_data
            # Verificar expiración manual (23 horas = 82800s)
            if time.time() - timestamp < 82800:
                return token

    if (
        not config.OPENSUBTITLES_API_KEY
        or not config.OPENSUBTITLES_USER
        or not config.OPENSUBTITLES_PASSWORD
    ):
        return None

    url = "https://api.opensubtitles.com/api/v1/login"
    headers = {
        "Api-Key": config.OPENSUBTITLES_API_KEY,
        "User-Agent": "RastreadorTorrents/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "username": config.OPENSUBTITLES_USER,
        "password": config.OPENSUBTITLES_PASSWORD,
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        token = data.get("token")
        if token:
            cache.set(
                "opensubtitles_token_data",
                (token, time.time()),
                timeout=config.CACHE_24H,
            )
            return token
    except Exception as e:
        logging.error("Error autenticando con OpenSubtitles: %s", redact_secrets(e))
    return None
