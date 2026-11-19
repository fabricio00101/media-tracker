import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Duraciones de caché unificadas
CACHE_24H = 86400
CACHE_1H = 3600
CACHE_5MIN = 300

# Almacenamiento opcional para caché y rate-limiting (ej. redis://localhost:6379/0)
REDIS_URL = os.getenv("REDIS_URL", "").strip()

PROWLARR_URL = os.getenv("PROWLARR_URL", "http://localhost:9696")
PROWLARR_API_KEY = os.getenv("PROWLARR_API_KEY", "")

# Tope de resultados que se piden a Prowlarr por búsqueda. Evita procesar miles
# de duplicados cuando agrupamos igual por obra. 0 = sin límite.
try:
    PROWLARR_SEARCH_LIMIT = int(os.getenv("PROWLARR_SEARCH_LIMIT", "500"))
except ValueError:
    PROWLARR_SEARCH_LIMIT = 500

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
