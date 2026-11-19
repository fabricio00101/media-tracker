from concurrent.futures import ThreadPoolExecutor
from flask import current_app
import PTN

import config
from services.tmdb import get_tmdb_info
from utils.language_detector import detect_spanish, detect_audio, matches_language
from utils.validators import DEFAULT_PER_PAGE, MAX_PER_PAGE

TMDB_MAX_WORKERS = 6


def build_cache_key(
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


def resolve_titles(unique_titles):
    """Resuelve la información de TMDB de cada título único, en paralelo.

    `unique_titles` mapea search_key -> (título, año, es serie).
    Devuelve (title_to_tmdb_key, tmdb_cache).
    """
    if not unique_titles:
        return {}, {}

    keys = list(unique_titles.keys())
    flask_app = current_app._get_current_object()

    def resolve(search_key):
        raw_title, year, is_tv = unique_titles[search_key]
        with flask_app.app_context():
            # Import dinámico o referencia del namespace de routes.search para respetar parches de tests
            import routes.search as rs
            return rs.get_tmdb_info(raw_title, year, is_tv)

    with ThreadPoolExecutor(max_workers=min(TMDB_MAX_WORKERS, len(keys))) as pool:
        infos = list(pool.map(resolve, keys))

    title_to_tmdb_key = {}
    tmdb_cache = {}

    for search_key, info in zip(keys, infos):
        raw_title, year, is_tv = unique_titles[search_key]

        if info and info.get("title"):
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
                    "id": None,
                    "title": raw_title.title(),
                    "overview": "Sinopsis no disponible en TMDB o API Key no configurada.",
                    "poster_url": None,
                    "year": year,
                    "media_type": media_type,
                },
            )

    return title_to_tmdb_key, tmdb_cache


def process_results(
    results_data,
    category,
    min_size_gb,
    quality_tag,
    require_hdr,
    require_hevc,
    lang_filters,
):
    """Filtra, agrupa y ordena los resultados crudos de Prowlarr."""
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

        spanish_support = detect_spanish(title_lower)
        if not matches_language(spanish_support, lang_filters):
            continue

        audio_support = detect_audio(title_lower)
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
    title_to_tmdb_key, tmdb_cache = resolve_titles(unique_titles)

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
