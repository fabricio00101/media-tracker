import time
import requests
import logging
from extensions import cache
import config

def get_opensubtitles_token():
    token_data = cache.get("opensubtitles_token_data")
    if token_data:
        token, timestamp = token_data
        # Verificar expiración manual (23 horas = 82800s)
        if time.time() - timestamp < 82800:
            return token

    if not config.OPENSUBTITLES_API_KEY or not config.OPENSUBTITLES_USER or not config.OPENSUBTITLES_PASSWORD:
        return None

    url = "https://api.opensubtitles.com/api/v1/login"
    headers = {
        "Api-Key": config.OPENSUBTITLES_API_KEY,
        "User-Agent": "RastreadorTorrents/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"username": config.OPENSUBTITLES_USER, "password": config.OPENSUBTITLES_PASSWORD}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        token = data.get("token")
        if token:
            cache.set("opensubtitles_token_data", (token, time.time()), timeout=config.CACHE_24H)
            return token
    except Exception as e:
        logging.error(f"Error autenticando con OpenSubtitles: {e}")
    return None
