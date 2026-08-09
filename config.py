import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Duraciones de caché unificadas
CACHE_24H = 86400
CACHE_1H = 3600
CACHE_5MIN = 300

PROWLARR_URL = os.getenv("PROWLARR_URL", "http://localhost:9696")
PROWLARR_API_KEY = os.getenv("PROWLARR_API_KEY", "")
DELUGE_URL = os.getenv("DELUGE_URL", "").rstrip("/")
DELUGE_PASSWORD = os.getenv("DELUGE_PASSWORD", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

OPENSUBTITLES_API_KEY = os.getenv("OPENSUBTITLES_API_KEY", "")
OPENSUBTITLES_USER = os.getenv("OPENSUBTITLES_USER", "")
OPENSUBTITLES_PASSWORD = os.getenv("OPENSUBTITLES_PASSWORD", "").strip()

# Validaciones
if not PROWLARR_API_KEY:
    logging.error("Crítico: PROWLARR_API_KEY no encontrada en .env. Las búsquedas fallarán.")
if not TMDB_API_KEY:
    logging.warning("Aviso: TMDB_API_KEY no encontrada. No se descargará pósters ni información oficial de TMDB.")
