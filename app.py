import hmac
import os
import logging
import secrets
from flask import (
    Flask,
    g,
    render_template,
    jsonify,
    request,
    send_from_directory,
    session,
)
from extensions import cache, limiter
from routes.search import search_bp
from routes.subtitles import subtitles_bp
from routes.deluge import deluge_bp
from routes import deluge as deluge_routes
import config
from utils.validators import DEFAULT_MIN_SIZE_GB

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max payload limit


# CSP afinada a los orígenes que la app usa realmente (verificados en
# index.html y error.html): Tailwind CDN, Google Fonts, Font Awesome (cdnjs,
# solo error.html) y pósters de TMDB. El Play CDN de Tailwind inyecta <style>
# en el DOM (por eso style-src lleva 'unsafe-inline') y compila en el
# navegador (se permite 'unsafe-eval' para no depender de ese detalle).
CSP_TEMPLATE = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-eval' 'nonce-{nonce}' https://cdn.tailwindcss.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
    "https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
    "img-src 'self' data: https://image.tmdb.org; "
    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'self'"
)


@app.before_request
def generar_nonce_csp():
    """Genera un nonce por request para los <script> embebidos de las plantillas.

    Se registra antes que el del rate limiter: así el nonce existe incluso en
    respuestas abortadas (429).
    """
    g.csp_nonce = secrets.token_urlsafe(16)


@app.context_processor
def exponer_nonce_csp():
    """Hace visible el nonce en cualquier plantilla (index.html y error.html)."""
    return {"csp_nonce": getattr(g, "csp_nonce", "")}


@app.after_request
def set_security_headers(response):
    """Agrega cabeceras de seguridad HTTP estándar para producción."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Aísla la ventana de terceros sin romper la app
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # Nonce propio de esta respuesta: si no hubo before_request, se genera uno
    # igual (las respuestas sin plantilla embebida no lo necesitan coherente).
    nonce = getattr(g, "csp_nonce", None) or secrets.token_urlsafe(16)
    response.headers["Content-Security-Policy"] = CSP_TEMPLATE.format(nonce=nonce)
    # HSTS únicamente cuando la petición llegó por HTTPS: nunca castiga el
    # despliegue local por HTTP ni exige detección de TLS en el proxy.
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


def _redis_available(url):
    """Comprueba que Redis exista y responda. Devuelve False ante cualquier fallo."""
    if not url:
        return False
    try:
        import redis  # import local: el proyecto funciona aunque redis no esté instalado

        client = redis.Redis.from_url(
            url, socket_connect_timeout=1, socket_timeout=1
        )
        client.ping()
        return True
    except Exception as e:
        logging.warning(
            "Redis no disponible en '%s' (%s). Se usará almacenamiento en memoria.",
            url,
            e,
        )
        return False


USE_REDIS = _redis_available(getattr(config, "REDIS_URL", ""))

# Configuración de Caché y Rate Limiter
if USE_REDIS:
    app.config["CACHE_TYPE"] = "RedisCache"
    app.config["CACHE_REDIS_URL"] = config.REDIS_URL
    app.config["RATELIMIT_STORAGE_URI"] = config.REDIS_URL
    logging.info("Caché y rate-limit usando Redis en %s", config.REDIS_URL)
else:
    app.config["CACHE_TYPE"] = "SimpleCache"
    logging.info(
        "Caché y rate-limit en memoria. Configura REDIS_URL para persistencia."
    )

app.config["CACHE_DEFAULT_TIMEOUT"] = config.CACHE_5MIN
cache.init_app(app)
limiter.init_app(app)


def error_page_context(code, description=None):
    """Traduce un código de estado a textos en español para la página de error.

    Sin esto, un 404 mostraba literalmente "500 - Error Interno del Servidor".
    """
    texts = {
        404: {
            "title": "Página no encontrada",
            "subtitle": "404 - No encontramos lo que buscas",
            "description": (
                "La página o el recurso no existe. Puede que el enlace esté mal "
                "escrito o que ya no esté disponible."
            ),
        },
        500: {
            "title": "Error del Servidor",
            "subtitle": "500 - Error Interno del Servidor",
            "description": (
                "Lo sentimos, pero algo inesperado ocurrió en nuestros servidores. "
                "Nuestro equipo técnico ha sido notificado."
            ),
        },
        405: {
            "title": "Método no permitido",
            "subtitle": "405 - Esta operación no está disponible acá",
            "description": (
                "El recurso no admite la operación solicitada. "
                "Volvé al inicio y probá desde la página principal."
            ),
        },
        413: {
            "title": "Contenido demasiado grande",
            "subtitle": "413 - El archivo supera el tamaño máximo",
            "description": (
                "El contenido enviado supera el límite permitido por el servidor. "
                "Reducilo e intentá de nuevo."
            ),
        },
    }

    entry = texts.get(
        code,
        {
            "title": "Algo salió mal",
            "subtitle": f"{code} - Error",
            "description": description or "Ocurrió un error inesperado. Inténtalo de nuevo.",
        },
    )
    entry["code"] = code
    return entry


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": f"Límite de peticiones excedido: {e.description}"}), 429


@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(413)
@app.errorhandler(500)
def handle_errors(e):
    # Las rutas de API mantienen respuestas JSON; el resto usa la página de error
    if request.path.startswith("/api/"):
        return jsonify({"error": e.description}), e.code
    return render_template("error.html", **error_page_context(e.code, e.description)), e.code

# Registro de Blueprints
app.register_blueprint(search_bp)
app.register_blueprint(subtitles_bp)
app.register_blueprint(deluge_bp)


# --- Token de sesión para /api/deluge/add -----------------------------------
# El secreto estático (API_SECRET_TOKEN) NUNCA se envía al navegador: cada
# visita a "/" recibe un token propio guardado en la sesión firmada de Flask,
# que el JS lee desde el meta tag "api-token". routes/deluge.py sigue
# validando contra el secreto (no se modifica); acá se envuelve su validación
# para aceptar además el token de sesión, manteniendo el secreto como
# alternativa para clientes externos que no usan el navegador.

def _extraer_token_pedido():
    """Devuelve el token enviado en X-Api-Token o Authorization: Bearer."""
    token = request.headers.get("X-Api-Token") or request.headers.get(
        "Authorization", ""
    )
    if token.startswith("Bearer "):
        token = token[7:].strip()
    return token


def _token_de_sesion_valido():
    """True si el token del request coincide con el de la sesión actual."""
    esperado = session.get("api_token")
    if not esperado:
        return False
    recibido = _extraer_token_pedido()
    if not recibido:
        return False
    try:
        return hmac.compare_digest(
            recibido.encode("utf-8"), esperado.encode("utf-8")
        )
    except Exception:
        return False


def _aceptar_token_de_sesion():
    """Envuelve la validación de routes/deluge.py para aceptar el token de sesión."""
    original = getattr(deluge_routes, "_is_authorized", None)
    if original is None:
        logging.error(
            "routes.deluge._is_authorized no existe: el token de sesión no "
            "será aceptado en /api/deluge/add."
        )
        return

    def _is_authorized_con_sesion():
        if _token_de_sesion_valido():
            return True
        return original()

    deluge_routes._is_authorized = _is_authorized_con_sesion


_aceptar_token_de_sesion()


@app.route("/")
def index():
    # Token por sesión: el secreto del servidor jamás se renderiza en el HTML.
    if not session.get("api_token"):
        session["api_token"] = secrets.token_urlsafe(32)
    return render_template(
        "index.html",
        default_min_size_gb=DEFAULT_MIN_SIZE_GB,
        api_token=session["api_token"],
    )


@app.route("/assets/<path:filename>")
def serve_asset(filename):
    """Sirve imágenes del proyecto (p. ej. la captura usada en og:image)."""
    return send_from_directory(os.path.join(app.root_path, "assets"), filename)


def _server_host():
    """Host de escucha configurable; por defecto solo localhost."""
    return os.getenv("HOST", "127.0.0.1")


def _server_port():
    """Puerto de escucha configurable."""
    try:
        return int(os.getenv("PORT", "5000"))
    except ValueError:
        return 5000


if __name__ == "__main__":
    env = os.getenv("FLASK_ENV", "production")
    host = _server_host()
    port = _server_port()
    if env == "development":
        logging.info("Iniciando servidor en modo DESARROLLO (Flask) en %s:%s...", host, port)
        # debug nunca activo: el depurador expone código y ejecución arbitraria
        app.run(host=host, debug=False, port=port)
    else:
        try:
            from waitress import serve

            logging.info(
                "Iniciando servidor en modo PRODUCCIÓN (Waitress) en %s:%s...",
                host,
                port,
            )
            serve(app, host=host, port=port)
        except ImportError:
            logging.warning(
                "Waitress no está instalado. Ejecutando con servidor de desarrollo (inseguro para pro)."
            )
            app.run(host=host, port=port)
