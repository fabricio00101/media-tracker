import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import PTN
import logging

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Configuración base
JACKETT_URL = os.getenv("JACKETT_URL", "http://localhost:9117")
JACKETT_API_KEY = os.getenv("JACKETT_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

# Validaciones de seguridad de Entorno
if not JACKETT_API_KEY:
    logging.error(
        "Crítico: JACKETT_API_KEY no encontrada en .env. Las búsquedas fallarán."
    )
if not TMDB_API_KEY:
    logging.warning(
        "Aviso: TMDB_API_KEY no encontrada. La aplicación funcionará pero NO descargará pósters ni información oficial de TMDB."
    )


def get_tmdb_info(query_title, year=None, is_tv=False):
    if not TMDB_API_KEY:
        return None

    search_type = "tv" if is_tv else "movie"
    endpoint = f"https://api.themoviedb.org/3/search/{search_type}"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query_title,
        "language": "es-ES",
        "page": 1,
    }
    if year and not is_tv:
        params["primary_release_year"] = year
    elif year and is_tv:
        params["first_air_date_year"] = year

    try:
        res = requests.get(endpoint, params=params, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                first = results[0]
                poster_path = first.get("poster_path")
                poster_url = (
                    f"https://image.tmdb.org/t/p/w500{poster_path}"
                    if poster_path
                    else None
                )
                return {
                    "title": first.get("title") or first.get("name"),
                    "overview": first.get("overview"),
                    "poster_url": poster_url,
                    "year": (
                        first.get("release_date", "")[:4]
                        if not is_tv
                        else first.get("first_air_date", "")[:4]
                    ),
                }
    except Exception:
        pass
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search")
def search():
    query = request.args.get("query", "").strip()
    category = request.args.get("category", "all").strip().lower()

    try:
        min_size_gb = float(request.args.get("min_size_gb", 15))
    except ValueError:
        min_size_gb = 15.0

    quality_tag = request.args.get("quality_tag", "").strip().lower()

    if not JACKETT_API_KEY:
        return (
            jsonify(
                {
                    "error": "La API Key de Jackett no está configurada en el servidor. Revisa el archivo .env."
                }
            ),
            500,
        )

    if not query:
        return jsonify({"error": "El nombre de la búsqueda es requerido."}), 400

    endpoint = f"{JACKETT_URL}/api/v2.0/indexers/all/results"
    params = {
        "apikey": JACKETT_API_KEY,
        "Query": query,
    }

    if category == "movies":
        params["Category[]"] = 2000
    elif category == "tv":
        params["Category[]"] = 5000
    elif category == "docs":
        params["Category[]"] = 8000

    try:
        # Aumentamos el timeout a 160 segundos porque FlareSolverr (en Jackett) puede tardar hasta 150s en resolver Cloudflare
        response = requests.get(endpoint, params=params, timeout=160)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError:
        return (
            jsonify(
                {
                    "error": "No se pudo conectar con Jackett. ¿Asegúrate de que está ejecutándose en http://localhost:9117?"
                }
            ),
            503,
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error comunicándose con Jackett: {str(e)}"}), 502
    except ValueError:
        return (
            jsonify({"error": "Respuesta inválida de Jackett (no es un JSON válido)."}),
            500,
        )

    results_data = data.get("Results", [])

    # Estructura para agrupar
    groups = {}
    tmdb_cache = {}
    # Cache para evitar buscar el mismo título de PTN varias veces en TMDB
    title_to_tmdb_key = {}

    for item in results_data:
        title = item.get("Title", "")
        size_bytes = item.get("Size", 0)
        size_gb = size_bytes / (1024**3)

        if size_gb < min_size_gb:
            continue

        if quality_tag and quality_tag not in title.lower():
            continue

        magnet = item.get("MagnetUri") or item.get("Link")

        title_lower = title.lower()
        spanish_support = None

        if any(
            tag in title_lower
            for tag in [
                "latino",
                "dual-lat",
                "es-mx",
                "spa-lat",
                "lat",
                "argentina",
                "mexic",
                "colombia",
                "chile",
                "peru",
                "[arg]",
                "[mex]",
                "(arg)",
                "(mex)",
            ]
        ):
            spanish_support = "Latino"
        elif any(
            tag in title_lower
            for tag in [
                "castellano",
                "es-es",
                "spanish",
                "español",
                "españa",
                "spain",
                "[esp]",
                "(esp)",
            ]
        ):
            spanish_support = "Castellano"
        elif any(
            tag in title_lower
            for tag in ["subs", "subtitulado", "vose", "multi-sub", "sub español"]
        ):
            spanish_support = "Subtitulado"

        # Parsear con PTN para agrupar
        parsed = PTN.parse(title)

        # Limpiar el título lo más posible para ayudar a agrupar localmente
        raw_clean_title = str(parsed.get("title", title))
        normalized_title = raw_clean_title.lower().replace(".", " ").strip()

        year = parsed.get("year", "")

        is_tv_forced = category == "tv"
        is_tv_parsed = "episode" in parsed or "season" in parsed
        is_tv = is_tv_forced or is_tv_parsed

        # Clave preliminar de búsqueda (ej: "the last of us_2023_True")
        search_key = f"{normalized_title}_{year}_{is_tv}"

        # 1. Obtenemos o buscamos en TMDB
        if search_key not in title_to_tmdb_key:
            info = get_tmdb_info(raw_clean_title, year, is_tv)
            if info and info.get("title"):
                # Si TMDB nos devuelve un título oficial, usamos ese como llave real de grupo
                # Ej: TMDB dice que es "The Last of Us" (2023). Agrupamos todo ahí.
                real_group_key = f"tmdb_{info['title'].lower()}_{info.get('year', '')}"
                title_to_tmdb_key[search_key] = real_group_key
                if real_group_key not in tmdb_cache:
                    tmdb_cache[real_group_key] = info
            else:
                # Fallback si falla TMDB o no hay API key
                real_group_key = f"local_{search_key}"
                title_to_tmdb_key[search_key] = real_group_key
                if real_group_key not in tmdb_cache:
                    tmdb_cache[real_group_key] = {
                        "title": raw_clean_title.title(),
                        "overview": "Sinopsis no disponible en TMDB o API Key no configurada.",
                        "poster_url": None,
                        "year": year,
                    }

        # Detectar Temporada Completa
        is_full_season = False
        if is_tv:
            # 1. Chequeo por PTN (tiene "season" pero NO "episode")
            if "season" in parsed and "episode" not in parsed:
                is_full_season = True

            # 2. String fallback (en caso de que PTN no lo agarre pero esté en el string base)
            # Ejemplos: "Complete Season", "Season 1-3", "S01-S05", "S01E01-E10" (A veces denotan temp completas)
            elif any(
                s in title_lower for s in ["complete", "temporada", "season 1-", "s01-"]
            ):
                is_full_season = True

        group_key = title_to_tmdb_key[search_key]

        if group_key not in groups:
            groups[group_key] = {"info": tmdb_cache[group_key], "torrents": []}

        groups[group_key]["torrents"].append(
            {
                "title": title,
                "size_gb": round(size_gb, 2),
                "seeders": item.get("Seeders", 0) or 0,
                "tracker": item.get("Tracker", "Desconocido"),
                "magnet": magnet,
                "spanish_support": spanish_support,
                "quality": parsed.get("resolution", "Desconocida"),
                "codec": parsed.get("codec", ""),
                "season": parsed.get("season"),
                "episode": parsed.get("episode"),
                "is_full_season": is_full_season,
            }
        )

    # Convertir diccionario de grupos a lista y ordenar torrents en cada grupo
    # Prioridad 1: is_full_season (True va primero)
    # Prioridad 2: cantidad de seeders
    final_results = []
    for g_key, g_data in groups.items():
        g_data["torrents"].sort(
            key=lambda x: (x["is_full_season"], x["seeders"]), reverse=True
        )
        if len(g_data["torrents"]) > 0:
            final_results.append(
                {"group_info": g_data["info"], "torrents": g_data["torrents"]}
            )

    # Ordenar grupos por la cantidad de seeders de su mejor torrent
    final_results.sort(key=lambda g: g["torrents"][0]["seeders"], reverse=True)

    return jsonify({"results": final_results})


if __name__ == "__main__":
    env = os.getenv("FLASK_ENV", "production")
    if env == "development":
        logging.info("Iniciando servidor en modo DESARROLLO (Flask)...")
        app.run(debug=True, port=5000)
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
