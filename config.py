import os
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Duraciones de caché unificadas
CACHE_24H = 86400
CACHE_1H = 3600
CACHE_5MIN = 300

# Valor por defecto de desarrollo: se avisa al arrancar si sigue en uso.
DEFAULT_SECRET_KEY = "media-tracker-dev-insecure-key-change-in-production"

# Secret Key de Flask para sesiones y protección criptográfica
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)

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

# Timeout (segundos) de cada consulta a Prowlarr. Las búsquedas reales con
# hasta 19 indexers tardaron entre 187 y 236 s (ver session_log.md), así que
# el default es holgado y configurable desde .env (PROWLARR_TIMEOUT).
try:
    PROWLARR_TIMEOUT = int(os.getenv("PROWLARR_TIMEOUT", "300"))
    if PROWLARR_TIMEOUT < 10 or PROWLARR_TIMEOUT > 600:
        PROWLARR_TIMEOUT = 300
except ValueError:
    PROWLARR_TIMEOUT = 300

DELUGE_URL = os.getenv("DELUGE_URL", "").rstrip("/")
DELUGE_PASSWORD = os.getenv("DELUGE_PASSWORD", "").strip()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

# Política SSRF de la descarga de .torrent:
# - SIEMPRE se bloquean link-local (169.254.0.0/16, fe80::/10), 0.0.0.0/8,
#   multicast y rangos reservados, incluidos sus equivalentes IPv4-mapeados.
# - Por defecto SÍ se permiten destinos privados y loopback porque Prowlarr y
#   Deluge suelen correr en la misma máquina o en la LAN (PROWLARR_URL por
#   defecto es http://localhost:9696). Con false solo se aceptan IPs públicas.
SSRF_ALLOW_PRIVATE_TARGETS = os.getenv(
    "SSRF_ALLOW_PRIVATE_TARGETS", "true"
).strip().lower() not in ("false", "0", "no")

# Tope de resoluciones de TMDB por búsqueda. Evita lanzar cientos de peticiones
# cuando Prowlarr devuelve muchos títulos distintos. 0 = sin límite.
try:
    TMDB_MAX_RESOLUTIONS = int(os.getenv("TMDB_MAX_RESOLUTIONS", "40"))
    if TMDB_MAX_RESOLUTIONS < 0 or TMDB_MAX_RESOLUTIONS > 500:
        TMDB_MAX_RESOLUTIONS = 40
except ValueError:
    TMDB_MAX_RESOLUTIONS = 40

# Tope de tamaño para un archivo .torrent descargado desde Prowlarr.
TORRENT_MAX_BYTES = 10 * 1024 * 1024

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

    # 3) Advertencias de seguridad (no bloquean el arranque)
    if SECRET_KEY == DEFAULT_SECRET_KEY:
        logging.warning(
            "Seguridad: SECRET_KEY usa el valor de desarrollo. Definí SECRET_KEY en .env "
            "antes de exponer la app fuera de tu equipo."
        )
    if not API_SECRET_TOKEN:
        logging.warning(
            "Seguridad: API_SECRET_TOKEN está vacío; /api/deluge/add no exige token. "
            "Definilo en .env si el endpoint es accesible desde la red."
        )


validate_config()
