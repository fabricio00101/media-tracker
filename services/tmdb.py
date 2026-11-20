import re
import time
import threading
import unicodedata
import requests
import logging
from extensions import cache
import config

# Semáforo global en memoria para limitar consultas simultáneas a TMDB en la app
# Evita que múltiples búsquedas concurrentes saturen la IP y gatillen rate-limits (HTTP 429)
TMDB_CONCURRENCY_LIMIT = 6
tmdb_semaphore = threading.Semaphore(TMDB_CONCURRENCY_LIMIT)


def _normalize_title(text):
    """Limpia y normaliza texto para comparaciones de títulos."""
    if not text:
        return ""
    # Quitar acentos / diacríticos
    normalized = unicodedata.normalize("NFKD", str(text))
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    # Quitar caracteres especiales y pasar a minúsculas
    cleaned = re.sub(r"[^\w\s]", " ", without_accents.lower())
    return " ".join(cleaned.split())


def _score_tmdb_candidate(candidate, query_title, target_year, is_tv):
    """Calcula un puntaje de coincidencia para un candidato de TMDB.

    Puntúa según coincidencia de título, título original, año y popularidad.
    """
    score = 0
    norm_query = _normalize_title(query_title)

    cand_title = candidate.get("title") or candidate.get("name") or ""
    cand_orig_title = (
        candidate.get("original_title") or candidate.get("original_name") or ""
    )

    norm_cand_title = _normalize_title(cand_title)
    norm_cand_orig = _normalize_title(cand_orig_title)

    # 1) Coincidencia de título
    if norm_query == norm_cand_title:
        score += 60
    elif norm_query == norm_cand_orig:
        score += 55
    elif norm_query in norm_cand_title or norm_cand_title in norm_query:
        score += 35
    elif norm_query in norm_cand_orig or norm_cand_orig in norm_query:
        score += 30

    # 2) Coincidencia de año (si se especificó en la búsqueda)
    cand_date = (
        candidate.get("release_date", "")
        if not is_tv
        else candidate.get("first_air_date", "")
    )
    cand_year = str(cand_date)[:4] if cand_date else None

    if target_year and cand_year:
        try:
            diff = abs(int(target_year) - int(cand_year))
            if diff == 0:
                score += 30
            elif diff == 1:
                score += 15
            else:
                score -= min(30, diff * 10)
        except ValueError:
            pass

    # 3) Popularidad o votos (pequeño desempate para obras notorias)
    vote_count = candidate.get("vote_count", 0) or 0
    if vote_count > 100:
        score += 10
    elif vote_count > 10:
        score += 5

    return score


def _select_best_candidate(results, query_title, year, is_tv):
    """Selecciona el candidato de TMDB más relevante aplicando scoring."""
    if not results:
        return None

    scored = []
    for cand in results:
        if not isinstance(cand, dict):
            continue
        s = _score_tmdb_candidate(cand, query_title, year, is_tv)
        scored.append((s, cand))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_candidate = scored[0]

    # Umbral mínimo de confianza para evitar asociar películas completamente diferentes
    if best_score < 30:
        return None

    return best_candidate


def _fetch_runtime(media_type, tmdb_id):
    """Duración en minutos de una película o de un episodio de serie.

    Se usa para estimar el bitrate de cada torrent. Si TMDB no la informa o la
    consulta falla, devuelve None y la estimación queda como 'sin datos'.
    """
    if not config.TMDB_API_KEY or not tmdb_id:
        return None

    endpoint = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
    try:
        res = requests.get(
            endpoint,
            params={"api_key": config.TMDB_API_KEY, "language": "es-ES"},
            timeout=5,
        )
        if res.status_code != 200:
            return None
        data = res.json()
    except Exception as e:
        logging.warning(
            f"Error consultando duración en TMDB ({media_type} {tmdb_id}): {e}"
        )
        return None

    if media_type == "tv":
        runtimes = data.get("episode_run_time") or []
        return runtimes[0] if runtimes else None
    return data.get("runtime")


@cache.memoize(timeout=config.CACHE_24H)
def get_tmdb_info(query_title, year=None, is_tv=False):
    if not config.TMDB_API_KEY:
        return None

    search_type = "tv" if is_tv else "movie"
    endpoint = f"https://api.themoviedb.org/3/search/{search_type}"
    params = {
        "api_key": config.TMDB_API_KEY,
        "query": query_title,
        "language": "es-ES",
        "page": 1,
    }
    if year and not is_tv:
        params["primary_release_year"] = year
    elif year and is_tv:
        params["first_air_date_year"] = year

    # Límite global de concurrencia y backoff incremental en 429
    with tmdb_semaphore:
        for attempt in range(2):
            try:
                res = requests.get(endpoint, params=params, timeout=5)
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    best = _select_best_candidate(results, query_title, year, is_tv)
                    if not best:
                        return None

                    poster_path = best.get("poster_path")
                    poster_url = (
                        f"https://image.tmdb.org/t/p/w500{poster_path}"
                        if poster_path
                        else None
                    )
                    media_type = "tv" if is_tv else "movie"
                    return {
                        "id": best.get("id"),
                        "title": best.get("title") or best.get("name"),
                        "overview": best.get("overview"),
                        "poster_url": poster_url,
                        "year": (
                            best.get("release_date", "")[:4]
                            if not is_tv
                            else best.get("first_air_date", "")[:4]
                        ),
                        "media_type": media_type,
                        "runtime": _fetch_runtime(media_type, best.get("id")),
                    }
                elif res.status_code == 429:
                    # Rate limit alcanzado: esperar brevemente antes de reintentar
                    logging.warning(
                        "TMDB respondió con 429 (Too Many Requests). Reintentando..."
                    )
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    logging.warning(
                        f"TMDB status {res.status_code} al consultar '{query_title}'"
                    )
                    break
            except Exception as e:
                logging.warning(f"Error consultando TMDB para '{query_title}': {e}")
                break

    return None
