import os
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Duraciones de caché unificadas
CACHE_24H = 86400
CACHE_1H = 3600
CACHE_5MIN = 300

# Secret Key de Flask para sesiones y protección criptográfica
SECRET_KEY = os.getenv("SECRET_KEY", "media-tracker-dev-insecure-key-change-in-production")

# Token opcional para proteger endpoints de mutación administrativa (ej: Deluge)
API_SECRET_TOKEN = os.getenv("API_SECRET_TOKEN", "").strip()

# Almacenamiento opcional para caché y rate-limiting (ej. redis://localhost:6379/0)
REDIS_URL = os.getenv("REDIS_URL", "").strip()

PROWLARR_URL = os.getenv("PROWLARR_URL", "http://localhost:9696").rstrip("/")
PROWLARR_API_KEY = os.getenv("PROWLARR_API_KEY", "").strip()

# Tope de resultados que se piden a Prowlarr por búsqueda. Evita procesar miles
# de duplicados cuando agrupamos igual por obra. 0 = sin límite.
try:
    PROWLARR_SEARCH_LIMIT = int(os.getenv("PROWLARR_SEARCH_LIMIT", "500"))
    if PROWLARR_SEARCH_LIMIT < 0 or PROWLARR_SEARCH_LIMIT > 2000:
        PROWLARR_SEARCH_LIMIT = 500
except ValueError:
    PROWLARR_SEARCH_LIMIT = 500

DELUGE_URL = os.getenv("DELUGE_URL", "").rstrip("/")
DELUGE_PASSWORD = os.getenv("DELUGE_PASSWORD", "").strip()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

OPENSUBTITLES_API_KEY = os.getenv("OPENSUBTITLES_API_KEY", "").strip()
OPENSUBTITLES_USER = os.getenv("OPENSUBTITLES_USER", "").strip()
OPENSUBTITLES_PASSWORD = os.getenv("OPENSUBTITLES_PASSWORD", "").strip()


def validate_config():
    """Valida la consistencia de las variables de entorno al arrancar la app."""
    # 1) Validar formato de URLs configuradas
    for name, url in [("PROWLARR_URL", PROWLARR_URL), ("DELUGE_URL", DELUGE_URL), ("REDIS_URL", REDIS_URL)]:
        if url:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                logging.warning("Configuración: '%s' no parece una URL válida ('%s').", name, url)

    # 2) Claves obligatorias y opcionales
    if not PROWLARR_API_KEY:
        logging.error("Crítico: PROWLARR_API_KEY no encontrada en .env. Las búsquedas fallarán.")
    if not TMDB_API_KEY:
        logging.warning("Aviso: TMDB_API_KEY no encontrada. No se descargarán pósters ni sinopsis de TMDB.")


validate_config()
