"""Helper de deduplicación para resultados de búsqueda de torrents.

Objetivo: eliminar torrents idénticos que aparecen en distintos indexers,
evitando inflated de conteos y filas duplicadas.

Política de deduplicación:
1. Clave primaria: infohash extraído del magnetUrl (urn:btih:...).
   Si el infohash está presente y no es genérico (longitud esperada ~40 hex chars),
   usarlo como único identificador.
2. Fallback por nombre+tamaño: cuando no hay infohash, normalizar el título
   y comparar el tamaño con una tolerancia conservadora.
   Se evitan falsos positivos sobre tamaños genéricos (ej. "4.7 GB" aparece
   en muchos releases distintos).
3. Al duplicarse: conservar el torrent con MÁS seeders.
   Merge de tamaño: no se duplica el tamaño, se toma el tamaño del de más seeders.
   Seeders agregados: solo se cuentan los seeders del ganador, los del
   duplicado se descarte para el total de seeders del grupo, pero el enlace
  magnet del ganador se conserva.
4. Rendimiento: O(n) usando diccionarios y sets, sin bucles anidados O(n²).
5. Casos borde: infohash vacío o < 20 chars → fallback a nombre+tamaño.
   Tamaños idénticos y nombres idénticos pero de indexers distintos → dedup.
   Magnets sin xt: fallback a nombre+tamaño.
"""

import re
from typing import Optional, Dict, Any, Set, Tuple


# ---------------------------------------------------------------------------
# Extracción de infohash desde magnet URI
# ---------------------------------------------------------------------------

_BS32_RE = re.compile(r"[a-zA-Z0-9]{20,40}")  # suficiente para btih


def extract_infohash(magnet_url: Optional[str]) -> Optional[str]:
    """Extraer el infohash de un magnet:?xt=urn:btih:... URL.

    Devuelve el string hexadecimal bajo minúsculas, o None si no hay
    magnetUrl o no contiene un xt válido.
    """
    if not magnet_url:
        return None
    m = re.search(r"urn:btih:([a-zA-Z0-9]+)", magnet_url)
    if not m:
        return None
    hexhash = m.group(1)
    # Filtrar longitudes ridículamente cortas o largas (ruido)
    if len(hexhash) < 20 or len(hexhash) > 42:
        return None
    # Verificar que sea hexadecimal mayoritariamente
    hex_chars = set("0123456789abcdefABCDEF")
    if not set(hexhash).issubset(hex_chars):
        return None
    return hexhash.lower()


# ---------------------------------------------------------------------------
# Normalización de nombre para fallback
# ---------------------------------------------------------------------------

def _normalize_name(title: str) -> str:
    """Normalizar un título para comparaciones aproximadas.

    - Lowercase
    - Reemplazar puntos y guiones por espacios
    - Quitar sufijos de calidad comunes que no aportan info de contenido
    - Collapse de espacios
    """
    t = title.lower()
    # Reemplazar puntos y guiones por espacio
    t = t.replace(".", " ").replace("-", " ")
    # Colapsar múltiples espacios
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------------------
# Tolerancia de tamaño
# ---------------------------------------------------------------------------

# Tolerancia relativa de tamaño en GB para considerar dos releases como
# candidatos a duplicados. Si el tamaño relativo difiere en más de este
# porcentaje, no son duplicados.
SIZE_TOLERANCE_REL_PCT = 15.0  # 15% de tolerancia


def _size_tolera(tamaño_gb_1: float, tamaño_gb_2: float) -> bool:
    """Devolver True si los tamaños están dentro de la tolerancia relativa.

    Maneja el caso de tamaños cero y evita división por cero.
    """
    if tamaño_gb_1 == 0 and tamaño_gb_2 == 0:
        return True
    if tamaño_gb_1 == 0 or tamaño_gb_2 == 0:
        return False
    rel = max(tamaño_gb_1, tamaño_gb_2) / min(tamaño_gb_1, tamaño_gb_2)
    return rel <= (1 + SIZE_TOLERANCE_REL_PCT / 100.0)


# ---------------------------------------------------------------------------
# Dict de deduplicación: grupos infohash -> entry ganador
# ---------------------------------------------------------------------------

_DedupeDict = Dict[str, Dict[str, Any]]


def deduplicate_torrents(
    torrents: list,
    get_infohash=None,
    get_title=None,
    get_size_bytes=None,
    get_seeders=None,
) -> list:
    """Deduplicar una lista de diccionarios de torrents.

    Args:
        torrents: lista de dicts con al menos los campos proveídos por
                  `get_*`. Cada `get_*` es una función que extrae el valor
                  del dict del torrent.
        get_infohash: fn(torrent_dict) -> str|None  (infohash desde magnet)
        get_title: fn(torrent_dict) -> str
        get_size_bytes: fn(torrent_dict) -> int  (bytes)
        get_seeders: fn(torrent_dict) -> int

    Returns:
        lista sin duplicated, con la política de "más seeders gana".
        Los totales (seeders, tamaño) ya reflejan la deduplicación.
    """
    if not torrents:
        return []

    # Funciones por defecto si no se pasan
    if get_infohash is None:
        def get_infohash(t):
            magnet = t.get("magnet") or t.get("magnetUrl") or ""
            return extract_infohash(magnet)
    if get_title is None:
        def get_title(t):
            return t.get("title", "")
    if get_size_bytes is None:
        def get_size_bytes(t):
            return t.get("size_bytes", t.get("size", 0)) or 0
    if get_seeders is None:
        def get_seeders(t):
            return t.get("seeders", 0) or 0

    # Phase 1: agrupar por infohash (clave primaria)
    # infohash -> index en la lista de resultados "ganadores"
    infohash_groups: Dict[str, int] = {}
    # Para rastrear qué índices ya fueron absorbidos por un infohash mayor
    absorbed: Set[int] = set()

    for i, tor in enumerate(torrents):
        ih = get_infohash(tor)
        if ih is not None:
            if ih in infohash_groups:
                # Ya tenemos un ganador para este infohash; decidir cuál tiene más seeders
                j = infohash_groups[ih]
                seeders_actual = get_seeders(tor)
                seeders_ganador = get_seeders(torrents[j])
                if seeders_actual > seeders_ganador:
                    # Este nuevo tiene más seeders, reemplazar al ganador
                    absorbed.add(j)
                    infohash_groups[ih] = i
                else:
                    # El actual ganador se queda, marcar este como absorbido
                    absorbed.add(i)
            else:
                infohash_groups[ih] = i

    # Phase 2: fallback por nombre+tamaño para los no agrupados por infohash
    # Usamos un dict clave = (norm_title_norm, size_bucket) -> índice ganador
    fallback_groups: Dict[Tuple[str, int], int] = {}

    for i, tor in enumerate(torrents):
        if i in absorbed:
            # Ya fue decidido por la fase de infohash (se quita del total)
            continue

        title = get_title(tor)
        norm_title = _normalize_name(title)
        size_bytes = get_size_bytes(tor)
        size_gb = size_bytes / (1024 ** 3)

        # Bucket de tamaño: redondear a medio GB para buckets de ~500 MB
        # Esto evita falsos positivos de "4.7 GB" genérico, al mismo tiempo que
        # agrupa releases de ~4.6 vs 4.8 GB.
        size_bucket = int(round(size_gb * 2))  # multiplos de 0.5 GB

        key = (norm_title, size_bucket)

        if key in fallback_groups:
            j = fallback_groups[key]
            seeders_actual = get_seeders(tor)
            seeders_ganador = get_seeders(torrents[j])
            if seeders_actual > seeders_ganador:
                fallback_groups[key] = i
            # Si el ganador ya existe, quedamos con el que tenga más seeders;
            # si empatan, nos quedamos con el primero (j) para estabilidad.
        else:
            fallback_groups[key] = i

    # Phase 3: construir el resultado final - quedarnos solo con los ganadores
    winner_indices: Set[int] = set()
    winner_indices.update(infohash_groups.values())
    winner_indices.update(fallback_groups.values())

    # Para cada ganador, recolectar su información y también acumular seeders
    # de los "perdedos" que compartían la misma clave (solo si el ganador
    # ya tiene más seeders, no sumamos los de abajo para evitar inflar).
    # Política: el ganador se queda con sus seeders; los duplicados se ignoran
    # para el total de seeders del grupo, pero sus metadatos (calidad, etc.)
    # ya vienen del ganador.

    resultados = []
    # Acumuladores de seeders "extra" de perdedos que tenemos en cuenta para
    # dar un mejor total: solo si el perdedor tiene seeders significativos
    # y los agregamos la mitad (redondeado hacia abajo) para no inflar pero
    # reconocer que hubo otros indexers. Alternativa más simple: solo el ganador.
    # Usaremos la política "solo ganador" para ser conservador.

    # Build a map from winner index to its torrent dict
    winner_torrents = {}
    for idx in winner_indices:
        winner_torrents[idx] = torrents[idx]

    # Ahora construimos los resultados consolidados.
    # Cada ganador se convierte en un "registro único" con su info.
    # Los perdedores por infohash o nombre+tamaño se descarte completamente
    # para seeders (se queda el de más seeders).
    for idx in sorted(winner_indices):
        tor = torrents[idx]
        size_bytes = get_size_bytes(tor)
        size_gb = round(size_bytes / (1024 ** 3), 2)
        seeders = get_seeders(tor)

        magnet = tor.get("magnet") or tor.get("magnetUrl") or ""

        resultados.append(
            {
                "title": tor.get("title"),
                "size_gb": size_gb,
                "seeders": seeders,
                "tracker": tor.get("indexer", "Desconocido"),
                "magnet": magnet,
                "infohash": extract_infohash(magnet),
                "deduped": True,  # marca que pasó por deduplicación
            }
        )

    return resultados


# ---------------------------------------------------------------------------
# Función de conveniencia para usar directamente en process_results
# ---------------------------------------------------------------------------

def select_deduplicated_indices(
    prepared_entries: list,
) -> tuple:
    """Seleccionar los índices de entries a conservar después de deduplicar.

    Analyse la lista `prepared` (output de la primera pasada de process_results)
    y determine qué entries son duplicados de cuáles, basándose en:
    1. Clave primaria: infohash desde magnetUrl
    2. Fallback: nombre normalizado + tamaño

    Devuelve los índices de los entries "ganadores" (los de más seeders)
    y estadísticas sobre qué fue removido.

    Returns:
        (indices_ganadores, stats_dedup) donde:
        - indices_ganadores: set de enteros, posiciones en `prepared_entries`
          de los entries que deben conservarse.
        - stats_dedup: diccionario con conteos de la operación.
    """
    import copy

    if not prepared_entries:
        return set(), {"original_count": 0, "removed": 0, "after_dedup": 0}

    # Build simple torrent dicts for dedup analysis, preserving original indices
    # Each: {index, title, magnet, seeders, size_bytes, indexer}
    simples = []
    for idx, entry in enumerate(prepared_entries):
        # Entry puede tener formato {item: {magnetUrl, seeders, size}, title, ...}
        # o formato directo {title, magnet, seeders, size} (para tests/unidades)
        if "item" in entry and isinstance(entry["item"], dict):
            item = entry["item"]
            magnet = item.get("magnetUrl", item.get("downloadUrl", ""))
            seeders = item.get("seeders", 0) or 0
            size_bytes = (item.get("size") or 0) or 0
            indexer = item.get("indexer", "Desconocido")
        else:
            # Formato directo: usar fields del propio entry
            magnet = entry.get("magnet", "")
            seeders = entry.get("seeders", 0) or 0
            size_bytes = (entry.get("size_bytes") or entry.get("size", 0)) or 0
            indexer = entry.get("indexer", "Desconocido")
        simples.append(
            {
                "original_index": idx,
                "title": entry.get("title", ""),
                "magnet": magnet,
                "seeders": seeders,
                "size_bytes": size_bytes,
                "indexer": indexer,
            }
        )

    # Phase 1: deduplicación por infohash
    # infohash -> {index in simples, seeders}
    infohash_winners: Dict[str, Dict[str, Any]] = {}
    # Track which original indices are absorbed (removed by infohash)
    absorbed_by_ih: Set[int] = set()

    for s in simples:
        ih = extract_infohash(s["magnet"])
        if ih is not None:
            if ih in infohash_winners:
                # Ya hay un ganador para este infohash
                winner = infohash_winners[ih]
                if s["seeders"] > winner["seeders"]:
                    # Este nuevo tiene más seeders, reemplazar
                    absorbed_by_ih.add(winner["original_index"])
                    infohash_winners[ih] = s
                else:
                    # El ganador actual se queda, este se absorbe
                    absorbed_by_ih.add(s["original_index"])
            else:
                infohash_winners[ih] = s

    # Phase 2: fallback por nombre+tamaño para entries no absorbidos por infohash
    # Usamos (norm_title, size_bucket) -> winner
    fallback_winners: Dict[Tuple[str, int], Dict[str, Any]] = {}

    for s in simples:
        if s["original_index"] in absorbed_by_ih:
            # Ya fue decidido por infohash, saltar (aunque podría también
            # participar en fallback; pero para simplificar y evitar
            # complicaciones, lo dejamos solo en infohash)
            continue

        norm_title = _normalize_name(s["title"])
        size_gb = s["size_bytes"] / (1024 ** 3)
        size_bucket = int(round(size_gb * 2))  # multiplos de 0.5 GB

        key = (norm_title, size_bucket)

        if key in fallback_winners:
            winner = fallback_winners[key]
            if s["seeders"] > winner["seeders"]:
                fallback_winners[key] = s
            # Si empatan, nos quedamos con el que ya tenía el key (first-past)
        else:
            fallback_winners[key] = s

    # Phase 3: recolectar índices ganadores
    # Un entry gana si fue seleccionado por infohash O por fallback
    winner_indices: Set[int] = set()
    # Añadir winners de infohash
    for s in infohash_winners.values():
        winner_indices.add(s["original_index"])
    # Añadir winners de fallback (que no fueron absorbidos por infohash)
    for s in fallback_winners.values():
        if s["original_index"] not in absorbed_by_ih:
            winner_indices.add(s["original_index"])

    # Phase 4: stats
    removed = len(prepared_entries) - len(winner_indices)
    stats = {
        "original_count": len(prepared_entries),
        "after_dedup": len(winner_indices),
        "removed": removed,
        "by_infohash": sum(
            1 for s in simples if s["original_index"] in absorbed_by_ih
        ),
        "by_name_size": len(simples) - len(infohash_winners) - len(absorbed_by_ih),
    }

    return winner_indices, stats

    # Aplicar deduplicación
    deduped = deduplicate_torrents(simple_torrents)

    # Calcular stats
    removed = len(simple_torrents) - len(deduped)
    stats = {
        "original_count": len(simple_torrents),
        "after_dedup": len(deduped),
        "removed": removed,
        "by_infohash": 0,  # podríamos contar más detalle si quisieras
        "by_name_size": 0,
    }

    return deduped, stats
def apply_deduplication_to_processed(prepared_entries):
    from . import select_deduplicated_indices as _sd
    indices, stats = _sd(prepared_entries)
    simple_torrents = []
    for idx in sorted(indices):
        entry = prepared_entries[idx]
        simple_torrents.append({
            "title": entry.get("title", ""),
            "magnet": entry.get("magnet", ""),
            "seeders": entry.get("seeders", 0) or 0,
            "size_bytes": entry.get("size_bytes", entry.get("size", 0)) or 0,
            "indexer": entry.get("tracker", "Desconocido"),
        })
    deduped = deduplicate_torrents(simple_torrents)
    removed = len(simple_torrents) - len(deduped)
    stats = {
        "original_count": len(simple_torrents),
        "after_dedup": len(deduped),
        "removed": removed,
        "by_infohash": 0,
        "by_name_size": 0,
    }
    return deduped, stats
