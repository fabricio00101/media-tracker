from concurrent.futures import ThreadPoolExecutor
from flask import current_app
import PTN

import config
from services.tmdb import get_tmdb_info
from utils.language_detector import detect_spanish, detect_audio, matches_language
from utils.media_meta import estimate_quality, parse_release_meta
from utils.validators import DEFAULT_PER_PAGE, MAX_PER_PAGE

TMDB_MAX_WORKERS = 6


def build_cache_key(
    query,
    category,
    min_size_gb,
    quality_tag,
    require_hdr,
    require_hevc,
    lang_filters,
    min_bpp=0.0,
    sdr_only=False,
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
            f"{float(min_bpp or 0):.3f}",
            str(bool(sdr_only)),
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


def _build_tech(entry, tmdb_info):
    """Arma el bloque técnico estimado de un torrent.

    Combina lo deducido del nombre del release con la duración de TMDB. Si no
    hay runtime, `estimate_quality` devuelve 'sin_datos' sin romper el resto.
    """
    meta = entry["meta"]
    runtime = (tmdb_info or {}).get("runtime")
    tech = {
        "source": meta.get("source"),
        "resolution": meta.get("resolution"),
        "video_codec": meta.get("video_codec"),
        "bit_depth": meta.get("bit_depth"),
        "hdr": meta.get("hdr"),
        "audio": meta.get("audio"),
        "edition": meta.get("edition"),
        "release_group": meta.get("group"),
    }
    tech.update(estimate_quality(entry["size_bytes"], runtime, meta))
    return tech


def process_results(
    results_data,
    category,
    min_size_gb,
    quality_tag,
    require_hdr,
    require_hevc,
    lang_filters,
    min_bpp=0.0,
    sdr_only=False,
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

        # Características deducidas del nombre del release (sin descargar nada)
        meta = parse_release_meta(title)
        if sdr_only and meta.get("hdr"):
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
                "size_bytes": item.get("size", 0) or 0,
                "parsed": parsed,
                "meta": meta,
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

        # Estimación de calidad: necesita la duración real de TMDB
        tech = _build_tech(entry, tmdb_cache[group_key])
        if (
            min_bpp
            and tech.get("bpp") is not None
            and tech["bpp"] < min_bpp
        ):
            continue

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
                "tech": tech,
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


def _year_value(group_info):
    """Año como entero; 0 si falta o no es numérico (para ordenar sin romper)."""
    try:
        return int(str((group_info or {}).get("year") or "").strip()[:4])
    except (TypeError, ValueError):
        return 0


def _max_score(torrents):
    """Mejor puntaje de calidad del grupo; -1 si ningún torrent tiene datos."""
    scores = [
        (t.get("tech") or {}).get("score")
        for t in torrents
        if (t.get("tech") or {}).get("score")
    ]
    return max(scores) if scores else -1


def sort_results(final_results, sort_mode="seeders_desc"):
    """Devuelve una copia ordenada de los grupos ya procesados.

    Se aplica después de leer la caché para no guardar una copia por criterio
    de ordenamiento. No muta los objetos cacheados.
    """
    ordered = []
    for group in final_results or []:
        torrents = list(group.get("torrents") or [])
        if sort_mode == "bpp_desc":
            torrents.sort(
                key=lambda t: (
                    (t.get("tech") or {}).get("score") or 0,
                    t.get("seeders") or 0,
                ),
                reverse=True,
            )
        else:
            torrents.sort(
                key=lambda t: (bool(t.get("is_full_season")), t.get("seeders") or 0),
                reverse=True,
            )
        ordered.append({"group_info": group.get("group_info"), "torrents": torrents})

    if sort_mode == "bpp_desc":
        ordered.sort(key=lambda g: _max_score(g["torrents"]), reverse=True)
    elif sort_mode == "year_desc":
        ordered.sort(key=lambda g: _year_value(g["group_info"]), reverse=True)
    elif sort_mode == "year_asc":
        # Los grupos sin año quedan al final, no antes de las películas antiguas
        ordered.sort(key=lambda g: _year_value(g["group_info"]) or 9999)
    elif sort_mode == "title_asc":
        ordered.sort(
            key=lambda g: ((g["group_info"] or {}).get("title") or "").lower()
        )
    else:
        ordered.sort(
            key=lambda g: max(
                (t.get("seeders") or 0 for t in g["torrents"]), default=0
            ),
            reverse=True,
        )
    return ordered
