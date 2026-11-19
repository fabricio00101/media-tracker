import os
import logging
from flask import Flask, render_template, jsonify, request
from extensions import cache, limiter
from routes.search import search_bp
from routes.subtitles import subtitles_bp
from routes.deluge import deluge_bp
import config

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max payload limit


@app.after_request
def set_security_headers(response):
    """Agrega cabeceras de seguridad HTTP estándar para producción."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    env = os.getenv("FLASK_ENV", "production")
    if env == "development":
        logging.info("Iniciando servidor en modo DESARROLLO (Flask)...")
        app.run(host="0.0.0.0", debug=True, port=5000)
    else:
        try:
            from waitress import serve

            logging.info(
                "Iniciando servidor en modo PRODUCCIÓN (Waitress) en el puerto 5000..."
            )
            serve(app, host="0.0.0.0", port=5000)
        except ImportError:
            logging.warning(
                "Waitress no está instalado. Ejecutando con servidor de desarrollo (inseguro para pro)."
            )
            app.run(host="0.0.0.0", port=5000)
