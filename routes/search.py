import re
import math
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, request, jsonify, current_app
import threading
import requests
import PTN
from extensions import limiter, cache
import config
from services.tmdb import get_tmdb_info

search_bp = Blueprint("search", __name__)

DEFAULT_PER_PAGE = 16
MAX_PER_PAGE = 50

# Límites de validación de parámetros de búsqueda
MIN_QUERY_LENGTH = 1
MAX_QUERY_LENGTH = 150
MIN_SIZE_GB_MIN = 0.0
MIN_SIZE_GB_MAX = 2000.0
MAX_QUALITY_TAG_LENGTH = 30
ALLOWED_CATEGORIES = {"all", "movies", "tv", "docs"}
ALLOWED_LANG_FILTERS = {"all", "latino", "castellano", "sub", "otros"}

# Cantidad máxima de consultas simultáneas a TMDB.
# TMDB limita por IP (~40 req / 10 s): pasar de acá provoca 429.
TMDB_MAX_WORKERS = 6


class ProwlarrError(Exception):
    """Error de comunicación con Prowlarr, con el código HTTP a devolver."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


# --- Control de concurrencia (evita el efecto "cache stampede") ----------------
# Varias peticiones iguales a la vez deben producir UNA sola consulta a Prowlarr.
# Administramos cada clave con un lock y un refcount para eliminarla sólo cuando
# ningún hilo la esté utilizando ni esperando.
_inflight_guard = threading.Lock()
_inflight_entries = {}


@contextmanager
def _inflight_lock(key):
    """Context manager que asegura el ciclo de vida del lock de búsqueda.

    Incrementa un refcount al solicitar el lock para la clave y sólo remueve
    la entrada del diccionario cuando el refcount llega a 0.
    """
    with _inflight_guard:
        if key not in _inflight_entries:
            _inflight_entries[key] = {"lock": threading.Lock(), "refcount": 0}
        entry = _inflight_entries[key]
        entry["refcount"] += 1

    lock = entry["lock"]
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()
        with _inflight_guard:
            entry["refcount"] -= 1
            if entry["refcount"] <= 0:
                _inflight_entries.pop(key, None)


def _parse_positive_int(value, default, minimum=1, maximum=None):
    """Convierte un parámetro de query string a entero acotado."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _build_cache_key(
    query, category, min_size_gb, quality_tag, require_hdr, require_hevc, lang_filters
):
    """Clave estable para cachear el conjunto completo de resultados agrupados."""
    return "search:" + "|".join(
        [
            query.lower(),
            category,
            f"{min_size_gb:.2f}",
            quality_tag,
            str(require_hdr),
            str(require_hevc),
            ",".join(sorted(lang_filters)),
        ]
    )


def _detect_spanish(title_lower):
    """Detecta el soporte de español a partir del título en minúsculas.

    Usa límites de palabra y patrones para evitar falsos positivos con substrings.
    """
    # Patrones para Español Latino
    latino_patterns = [
        r"\blatino\b",
        r"\bdual[-_ ]lat\b",
        r"\bes[-_ ]mx\b",
        r"\bspa[-_ ]lat\b",
        r"\blatam\b",
        r"\bargentina\b",
        r"\bmexic[ao]\b",
        r"\bchile\b",
        r"\bperu\b",
        r"\[arg\]",
        r"\[mex\]",
        r"\(arg\)",
        r"\(mex\)",
        r"\blat\b",
    ]
    if any(re.search(pat, title_lower) for pat in latino_patterns):
        return "Latino"

    # Patrones para Castellano (España)
    castellano_patterns = [
        r"\bcastellano\b",
        r"\bes[-_ ]es\b",
        r"\bspanish\b",
        r"\bespañol\b",
        r"\bespana\b",
        r"\bespaña\b",
        r"\bspain\b",
        r"\[esp\]",
        r"\(esp\)",
    ]
    if any(re.search(pat, title_lower) for pat in castellano_patterns):
        return "Castellano"

    # Patrones para Subtitulado
    sub_patterns = [
        r"\bsubs?\b",
        r"\bsubtitulado\b",
        r"\bvose\b",
        r"\bmulti[-_ ]subs?\b",
        r"\bsub\s+español\b",
        r"\bsub[-_ ]es\b",
    ]
    if any(re.search(pat, title_lower) for pat in sub_patterns):
        return "Subtitulado"

    return None


def _detect_audio(title_lower):
    """Detecta el formato de audio a partir del título en minúsculas."""
    if re.search(r"\b(atmos|truehd|true-hd)\b", title_lower):
        return "Dolby Atmos / TrueHD"
    if re.search(r"\b(dts-hd|dts:x|dts-x|dtshd)\b", title_lower):
        return "DTS-HD / X"
    if re.search(r"\b(eac3|ddp5\.1|ddp|dd\+)\b", title_lower):
        return "Dolby Digital Plus"
    if re.search(r"\b(dd5\.1|dolby|ac3)\b", title_lower):
        return "Dolby Digital"
    if re.search(r"\bdts\b", title_lower):
        return "DTS"
    if re.search(r"\baac(\d|\b)", title_lower):
        return "AAC"
    return None


def _matches_language(spanish_support, lang_filters):
    """Aplica el filtro server-side de idioma. 'all' no filtra nada."""
    if "all" in lang_filters:
        return True
    if "latino" in lang_filters and spanish_support == "Latino":
        return True
    if "castellano" in lang_filters and spanish_support == "Castellano":
        return True
    if "sub" in lang_filters and spanish_support == "Subtitulado":
        return True
    if "otros" in lang_filters and spanish_support is None:
        return True
    return False


def _resolve_titles(unique_titles):
    """Resuelve la información de TMDB de cada título único, en paralelo.

    `unique_titles` mapea search_key -> (título, año, es serie).
    Devuelve (title_to_tmdb_key, tmdb_cache).
    """
    if not unique_titles:
        return {}, {}

    keys = list(unique_titles.keys())

    # Flask no comparte el context de aplicación entre hilos: cada worker
    # debe crear el suyo para que flask_caching pueda resolver su backend.
    flask_app = current_app._get_current_object()

    def resolve(search_key):
        raw_title, year, is_tv = unique_titles[search_key]
        with flask_app.app_context():
            return get_tmdb_info(raw_title, year, is_tv)

    with ThreadPoolExecutor(max_workers=min(TMDB_MAX_WORKERS, len(keys))) as pool:
        infos = list(pool.map(resolve, keys))

    title_to_tmdb_key = {}
    tmdb_cache = {}

    for search_key, info in zip(keys, infos):
        raw_title, year, is_tv = unique_titles[search_key]

        if info and info.get("title"):
            # Las entradas memoizadas antes de este cambio no traen media_type:
            # sin él, una serie se buscaría como película en OpenSubtitles.
            media_type = info.get("media_type") or ("tv" if is_tv else "movie")
            info["media_type"] = media_type
            group_key = f"tmdb_{media_type}_{info['title'].lower()}_{info.get('year', '')}"
            title_to_tmdb_key[search_key] = group_key
            tmdb_cache.setdefault(group_key, info)
        else:
            media_type = "tv" if is_tv else "movie"
            group_key = f"local_{media_type}_{search_key}"
            title_to_tmdb_key[search_key] = group_key
            tmdb_cache.setdefault(
                group_key,
                {
                    # Sin TMDB no hay id: el frontend oculta la búsqueda de
                    # subtítulos en vez de mandar "undefined" a OpenSubtitles.
                    "id": None,
                    "title": raw_title.title(),
                    "overview": "Sinopsis no disponible en TMDB o API Key no configurada.",
                    "poster_url": None,
                    "year": year,
                    "media_type": media_type,
                },
            )

    return title_to_tmdb_key, tmdb_cache


def _fetch_prowlarr(query, category):
    """Consulta Prowlarr y devuelve la lista cruda de resultados."""
    endpoint = f"{config.PROWLARR_URL}/api/v1/search"
    # La clave viaja por header: los query strings terminan en logs y proxies
    headers = {"X-Api-Key": config.PROWLARR_API_KEY}
    params = {"query": query, "type": "search"}

    if category == "movies":
        params["categories"] = [2000]
    elif category == "tv":
        params["categories"] = [5000]
    elif category == "docs":
        params["categories"] = [8000]

    # Limita el volumen devuelto: agrupamos después y sobran duplicados
    if config.PROWLARR_SEARCH_LIMIT > 0:
        params["limit"] = config.PROWLARR_SEARCH_LIMIT

    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError:
        raise ProwlarrError(
            f"No se pudo conectar con Prowlarr en {config.PROWLARR_URL}. "
            "Verifica que esté encendido.",
            status=503,
        )
    except requests.exceptions.RequestException as e:
        raise ProwlarrError(f"Error comunicándose con Prowlarr: {str(e)}", status=502)
    except ValueError:
        raise ProwlarrError("Respuesta inválida de Prowlarr (no es un JSON válido).", 500)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("Results"), list):
        items = data["Results"]
    else:
        raise ProwlarrError("Estructura de respuesta inesperada de Prowlarr.", 502)

    # Filtrar defensivamente sólo aquellos elementos que sean diccionarios válidos
    valid_items = []
    for item in items:
        if isinstance(item, dict) and item.get("title"):
            valid_items.append(item)
    return valid_items


def _process_results(
    results_data,
    category,
    min_size_gb,
    quality_tag,
    require_hdr,
    require_hevc,
    lang_filters,
):
    """Filtra, agrupa y ordena los resultados crudos de Prowlarr.

    Se ejecuta en dos pasadas para poder resolver TMDB en paralelo:
      1) filtros baratos + parseo + recolección de títulos únicos.
      2) agrupación usando la información ya resuelta.
    """
    prepared = []
    unique_titles = {}

    # --- 1ª pasada: filtros y parseo ---------------------------------------
    for item in results_data:
        title = item.get("title", "")
        size_gb = (item.get("size", 0) or 0) / (1024**3)

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

        spanish_support = _detect_spanish(title_lower)
        if not _matches_language(spanish_support, lang_filters):
            continue

        audio_support = _detect_audio(title_lower)
        parsed = PTN.parse(title)

        raw_clean_title = str(parsed.get("title", title))
        normalized_title = raw_clean_title.lower().replace(".", " ").strip()
        year = parsed.get("year", "")

        is_tv_forced = category == "tv"
        is_tv = is_tv_forced or "episode" in parsed or "season" in parsed

        search_key = f"{normalized_title}_{year}_{is_tv}"
        unique_titles.setdefault(search_key, (raw_clean_title, year, is_tv))

        prepared.append(
            {
                "item": item,
                "title": title,
                "title_lower": title_lower,
                "size_gb": size_gb,
                "parsed": parsed,
                "search_key": search_key,
                "spanish_support": spanish_support,
                "audio_support": audio_support,
                "is_tv": is_tv,
            }
        )

    # --- Resolución de metadatos en paralelo ------------------------------
    title_to_tmdb_key, tmdb_cache = _resolve_titles(unique_titles)

    # --- 2ª pasada: agrupación --------------------------------------------
    groups = {}

    for entry in prepared:
        item = entry["item"]
        parsed = entry["parsed"]
        title_lower = entry["title_lower"]
        is_tv = entry["is_tv"]

        is_full_season = False
        if is_tv:
            if "season" in parsed and "episode" not in parsed:
                is_full_season = True
            elif any(
                s in title_lower
                for s in ["complete", "temporada", "season 1-", "s01-"]
            ):
                is_full_season = True

        magnet = item.get("magnetUrl") or item.get("downloadUrl") or item.get("infoUrl")
        group_key = title_to_tmdb_key[entry["search_key"]]

        if group_key not in groups:
            groups[group_key] = {"info": tmdb_cache[group_key], "torrents": []}

        groups[group_key]["torrents"].append(
            {
                "title": entry["title"],
                "size_gb": round(entry["size_gb"], 2),
                "seeders": item.get("seeders", 0) or 0,
                "tracker": item.get("indexer", "Desconocido"),
                "magnet": magnet,
                "spanish_support": entry["spanish_support"],
                "audio_support": entry["audio_support"],
                "quality": parsed.get("resolution", "Desconocida"),
                "codec": parsed.get("codec", ""),
                "season": parsed.get("season"),
                "episode": parsed.get("episode"),
                "is_full_season": is_full_season,
            }
        )

    final_results = []
    for g_data in groups.values():
        if not g_data["torrents"]:
            continue
        g_data["torrents"].sort(
            key=lambda x: (x["is_full_season"], x["seeders"]), reverse=True
        )
        final_results.append(
            {"group_info": g_data["info"], "torrents": g_data["torrents"]}
        )

    final_results.sort(key=lambda g: g["torrents"][0]["seeders"], reverse=True)
    return final_results


@search_bp.route("/api/search")
@limiter.limit("30 per minute")
def search():
    if not config.PROWLARR_API_KEY:
        return (
            jsonify(
                {
                    "error": "La API Key de Prowlarr no está configurada en el servidor. Revisa el archivo .env."
                }
            ),
            500,
        )

    # 1) Validación de query
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"error": "El nombre de la búsqueda es requerido."}), 400
    if len(query) > MAX_QUERY_LENGTH:
        return (
            jsonify(
                {"error": f"La búsqueda no puede superar los {MAX_QUERY_LENGTH} caracteres."}
            ),
            400,
        )

    # 2) Validación de categoría
    category = request.args.get("category", "all").strip().lower()
    if category not in ALLOWED_CATEGORIES:
        return (
            jsonify(
                {
                    "error": f"Categoría inválida '{category}'. Valores permitidos: {', '.join(sorted(ALLOWED_CATEGORIES))}."
                }
            ),
            400,
        )

    # 3) Validación de filtros de idioma
    lang_filter_raw = request.args.get("lang_filter", "all").strip().lower()
    lang_filters = [x.strip() for x in lang_filter_raw.split(",") if x.strip()]
    if not lang_filters:
        lang_filters = ["all"]
    invalid_langs = [l for l in lang_filters if l not in ALLOWED_LANG_FILTERS]
    if invalid_langs:
        return (
            jsonify(
                {
                    "error": f"Filtro de idioma inválido: {', '.join(invalid_langs)}. Valores permitidos: {', '.join(sorted(ALLOWED_LANG_FILTERS))}."
                }
            ),
            400,
        )

    # 4) Validación de tamaño mínimo
    raw_min_size = request.args.get("min_size_gb", 15)
    try:
        min_size_gb = float(raw_min_size)
        if not math.isfinite(min_size_gb) or min_size_gb < MIN_SIZE_GB_MIN or min_size_gb > MIN_SIZE_GB_MAX:
            return (
                jsonify(
                    {
                        "error": f"El tamaño mínimo debe ser un número finito entre {MIN_SIZE_GB_MIN} y {MIN_SIZE_GB_MAX} GB."
                    }
                ),
                400,
            )
    except (ValueError, TypeError):
        return (
            jsonify({"error": "El parámetro min_size_gb debe ser un valor numérico válido."}),
            400,
        )

    # 5) Validación de calidad y flags adicionales
    quality_tag = request.args.get("quality_tag", "").strip().lower()
    if len(quality_tag) > MAX_QUALITY_TAG_LENGTH:
        return (
            jsonify(
                {
                    "error": f"El filtro de calidad no puede superar los {MAX_QUALITY_TAG_LENGTH} caracteres."
                }
            ),
            400,
        )

    require_hdr = request.args.get("hdr", "false").lower() == "true"
    require_hevc = request.args.get("hevc", "false").lower() == "true"

    # Paginación server-side (se pagina sobre grupos de obras, no sobre torrents)
    page = _parse_positive_int(request.args.get("page", 1), 1)
    per_page = _parse_positive_int(
        request.args.get("per_page", DEFAULT_PER_PAGE),
        DEFAULT_PER_PAGE,
        maximum=MAX_PER_PAGE,
    )

    cache_key = _build_cache_key(
        query,
        category,
        min_size_gb,
        quality_tag,
        require_hdr,
        require_hevc,
        lang_filters,
    )

    # 1) Lectura rápida: si ya está en caché no se toca ningún lock
    final_results = cache.get(cache_key)

    if final_results is None:
        with _inflight_lock(cache_key):
            # 2) Doble chequeo: mientras esperábamos el lock, otro hilo pudo
            #    haber completado exactamente la misma búsqueda
            final_results = cache.get(cache_key)

            if final_results is None:
                try:
                    results_data = _fetch_prowlarr(query, category)
                except ProwlarrError as e:
                    return jsonify({"error": str(e)}), e.status

                final_results = _process_results(
                    results_data,
                    category,
                    min_size_gb,
                    quality_tag,
                    require_hdr,
                    require_hevc,
                    lang_filters,
                )

                # Guardar el conjunto completo (la paginación no altera la clave)
                cache.set(cache_key, final_results, timeout=config.CACHE_5MIN)

    # 3) Paginar los grupos procesados
    total_groups = len(final_results)
    total_torrents = sum(len(group["torrents"]) for group in final_results)
    start = (page - 1) * per_page
    end = start + per_page
    page_results = final_results[start:end]

    return jsonify(
        {
            "results": page_results,
            "page": page,
            "per_page": per_page,
            "total_groups": total_groups,
            "total_torrents": total_torrents,
            "has_more": end < total_groups,
        }
    )
