import os
import logging
from flask import Flask, render_template, jsonify
from extensions import cache, limiter
from routes.search import search_bp
from routes.subtitles import subtitles_bp
from routes.deluge import deluge_bp

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

# Configuración de Caché
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300
cache.init_app(app)

# Configuración de Rate Limiter
limiter.init_app(app)

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": f"Límite de peticiones excedido: {e.description}"}), 429

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
