import requests
import logging
from extensions import cache
import config

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
                    "id": first.get("id"),
                    "title": first.get("title") or first.get("name"),
                    "overview": first.get("overview"),
                    "poster_url": poster_url,
                    "year": (
                        first.get("release_date", "")[:4]
                        if not is_tv
                        else first.get("first_air_date", "")[:4]
                    ),
                }
    except Exception as e:
        logging.warning(f"Error consultando TMDB para '{query_title}': {e}")
    return None
