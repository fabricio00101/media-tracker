from flask import Blueprint, request, jsonify
import requests
import PTN
from extensions import limiter, cache
import config
from services.tmdb import get_tmdb_info

search_bp = Blueprint("search", __name__)

@search_bp.route("/api/search")
@limiter.limit("30 per minute")
@cache.cached(timeout=config.CACHE_5MIN, query_string=True)
def search():
    query = request.args.get("query", "").strip()
    category = request.args.get("category", "all").strip().lower()
    lang_filter_raw = request.args.get("lang_filter", "all").strip().lower()
    lang_filters = [x.strip() for x in lang_filter_raw.split(",") if x.strip()]

    try:
        min_size_gb = float(request.args.get("min_size_gb", 15))
    except ValueError:
        min_size_gb = 15.0

    quality_tag = request.args.get("quality_tag", "").strip().lower()
    require_hdr = request.args.get("hdr", "false").lower() == "true"
    require_hevc = request.args.get("hevc", "false").lower() == "true"

    if not config.PROWLARR_API_KEY:
        return (
            jsonify(
                {
                    "error": "La API Key de Prowlarr no está configurada en el servidor. Revisa el archivo .env."
                }
            ),
            500,
        )

    if not query:
        return jsonify({"error": "El nombre de la búsqueda es requerido."}), 400

    endpoint = f"{config.PROWLARR_URL}/api/v1/search"
    params = {"apikey": config.PROWLARR_API_KEY, "query": query, "type": "search"}

    if category == "movies":
        params["categories"] = [2000]
    elif category == "tv":
        params["categories"] = [5000]
    elif category == "docs":
        params["categories"] = [8000]

    try:
        response = requests.get(endpoint, params=params, timeout=160)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError:
        return (
            jsonify(
                {
                    "error": f"No se pudo conectar con Prowlarr en {config.PROWLARR_URL}. Verifica que esté encendido."
                }
            ),
            503,
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error comunicándose con Prowlarr: {str(e)}"}), 502
    except ValueError:
        return (
            jsonify(
                {"error": "Respuesta inválida de Prowlarr (no es un JSON válido)."}
            ),
            500,
        )

    if isinstance(data, list):
        results_data = data
    else:
        results_data = data.get("Results", [])

    groups = {}
    tmdb_cache = {}
    title_to_tmdb_key = {}

    for item in results_data:
        title = item.get("title", "")
        size_bytes = item.get("size", 0)
        size_gb = size_bytes / (1024**3)

        if size_gb < min_size_gb:
            continue

        title_lower = title.lower()

        if quality_tag and quality_tag not in title_lower:
            continue

        if require_hdr and "hdr" not in title_lower:
            continue

        if require_hevc and not any(
            tag in title_lower for tag in ["hevc", "x265", "h265", "h.265"]
        ):
            continue

        magnet = item.get("magnetUrl") or item.get("downloadUrl") or item.get("infoUrl")

        spanish_support = None

        if any(
            tag in title_lower
            for tag in [
                "latino", "dual-lat", "es-mx", "spa-lat", "lat", "argentina",
                "mexic", "colombia", "chile", "peru", "[arg]", "[mex]", "(arg)", "(mex)",
            ]
        ):
            spanish_support = "Latino"
        elif any(
            tag in title_lower
            for tag in [
                "castellano", "es-es", "spanish", "español", "españa", "spain",
                "[esp]", "(esp)",
            ]
        ):
            spanish_support = "Castellano"
        elif any(
            tag in title_lower
            for tag in ["subs", "subtitulado", "vose", "multi-sub", "sub español"]
        ):
            spanish_support = "Subtitulado"

        # Filtro de idioma server-side
        if "all" not in lang_filters:
            matched = False
            if "latino" in lang_filters and spanish_support == "Latino":
                matched = True
            elif "castellano" in lang_filters and spanish_support == "Castellano":
                matched = True
            elif "sub" in lang_filters and spanish_support == "Subtitulado":
                matched = True
            elif "otros" in lang_filters and spanish_support is None:
                matched = True
            
            if not matched:
                continue

        audio_support = None
        if any(tag in title_lower for tag in ["atmos", "truehd", "true-hd"]):
            audio_support = "Dolby Atmos / TrueHD"
        elif any(tag in title_lower for tag in ["dts-hd", "dts:x", "dts-x", "dtshd"]):
            audio_support = "DTS-HD / X"
        elif any(tag in title_lower for tag in ["eac3", "ddp5.1", "ddp", "dd+"]):
            audio_support = "Dolby Digital Plus"
        elif any(tag in title_lower for tag in ["dd5.1", "dolby", "ac3"]):
            audio_support = "Dolby Digital"
        elif any(tag in title_lower for tag in ["dts"]):
            audio_support = "DTS"
        elif any(tag in title_lower for tag in ["aac"]):
            audio_support = "AAC"

        parsed = PTN.parse(title)
        raw_clean_title = str(parsed.get("title", title))
        normalized_title = raw_clean_title.lower().replace(".", " ").strip()
        year = parsed.get("year", "")

        is_tv_forced = category == "tv"
        is_tv_parsed = "episode" in parsed or "season" in parsed
        is_tv = is_tv_forced or is_tv_parsed

        search_key = f"{normalized_title}_{year}_{is_tv}"

        if search_key not in title_to_tmdb_key:
            info = get_tmdb_info(raw_clean_title, year, is_tv)
            if info and info.get("title"):
                real_group_key = f"tmdb_{info['title'].lower()}_{info.get('year', '')}"
                title_to_tmdb_key[search_key] = real_group_key
                if real_group_key not in tmdb_cache:
                    tmdb_cache[real_group_key] = info
            else:
                real_group_key = f"local_{search_key}"
                title_to_tmdb_key[search_key] = real_group_key
                if real_group_key not in tmdb_cache:
                    tmdb_cache[real_group_key] = {
                        "title": raw_clean_title.title(),
                        "overview": "Sinopsis no disponible en TMDB o API Key no configurada.",
                        "poster_url": None,
                        "year": year,
                    }

        is_full_season = False
        if is_tv:
            if "season" in parsed and "episode" not in parsed:
                is_full_season = True
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
                "seeders": item.get("seeders", 0) or 0,
                "tracker": item.get("indexer", "Desconocido"),
                "magnet": magnet,
                "spanish_support": spanish_support,
                "audio_support": audio_support,
                "quality": parsed.get("resolution", "Desconocida"),
                "codec": parsed.get("codec", ""),
                "season": parsed.get("season"),
                "episode": parsed.get("episode"),
                "is_full_season": is_full_season,
            }
        )

    final_results = []
    for g_key, g_data in groups.items():
        g_data["torrents"].sort(
            key=lambda x: (x["is_full_season"], x["seeders"]), reverse=True
        )
        if len(g_data["torrents"]) > 0:
            final_results.append(
                {"group_info": g_data["info"], "torrents": g_data["torrents"]}
            )

    final_results.sort(key=lambda g: g["torrents"][0]["seeders"], reverse=True)

    return jsonify({"results": final_results})
