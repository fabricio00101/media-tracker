"""Estimación de características técnicas de un release a partir de su nombre.

Todo se deduce del título del torrent: no hay acceso al archivo real. Las
funciones son puras para poder testearlas sin red ni sistema de archivos.
"""

import re

from utils.audio_patterns import detect_audio_codec

# Resoluciones soportadas -> (ancho, alto) del cuadro completo.
# Los encodes con barras negras recortadas tienen menos píxeles reales, por lo
# que el bpp calculado queda levemente subestimado (criterio conservador).
RESOLUTION_DIMENSIONS = {
    "2160p": (3840, 2160),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "576p": (1024, 576),
    "480p": (854, 480),
}

# El nombre del release nunca indica los fps: se asume cine (24) siempre.
ASSUMED_FPS = 24.0

# Umbrales de bits por píxel (bpp) ordenados de mayor a menor, por familia.
# Se comparan con >= : el primer umbral que se cumple define el nivel.
CODEC_THRESHOLDS = {
    "hevc": [(0.12, "excelente"), (0.07, "muy_bueno"), (0.04, "correcto")],
    "h264": [(0.16, "excelente"), (0.10, "muy_bueno"), (0.07, "correcto")],
}

TIER_LABELS = {
    "remux": "Remux (máxima)",
    "excelente": "Excelente",
    "muy_bueno": "Muy buena",
    "correcto": "Correcta",
    "flojo": "Floja",
    "sin_datos": "Sin datos",
}

SOURCE_PATTERNS = [
    (r"\bremux\b", "REMUX"),
    (r"\b(bluray|blu-ray|bdrip|brrip)\b", "BluRay"),
    (r"\bweb[-_. ]?dl\b", "WEB-DL"),
    (r"\bweb[-_. ]?rip\b", "WEBRip"),
    (r"\bhdtv\b", "HDTV"),
    (r"\b(dvdrip|dvd)\b", "DVDRip"),
]

CODEC_PATTERNS = [
    (r"\b(x265|hevc|h\.?265)\b", "HEVC"),
    (r"\b(x264|h\.?264|avc)\b", "H.264"),
    (r"\bav1\b", "AV1"),
    (r"\b(xvid|divx)\b", "XviD"),
]

BIT_DEPTH_PATTERNS = [
    (r"\b10[ -]?bits?\b", 10),
    (r"\b8[ -]?bits?\b", 8),
]

HDR_PATTERNS = [
    (r"\b(dolby[ ._-]?vision|dovi|\bdv\b)", "DV"),
    (r"\bhdr10\+", "HDR10+"),
    (r"\b(hdr10|hdr)\b", "HDR10"),
    (r"\bhlg\b", "HLG"),
]

# Los códecs de audio viven en utils.audio_patterns (fuente única compartida
# con utils.language_detector). Acá solo se detectan los canales.

# Sin \b inicial: en "DDP5.1" el "5.1" está pegado a una letra y no habría límite.
CHANNEL_PATTERNS = [
    (r"7\.1(?!\d)", "7.1"),
    (r"5\.1(?!\d)", "5.1"),
    (r"2\.0(?!\d)", "2.0"),
    (r"\b(1\.0|mono)\b", "1.0"),
]

EDITION_PATTERNS = [
    (r"\bremastered\b", "Remasterizado"),
    (r"\bextended\b", "Extendida"),
    (r"\b(unrated|uncut)\b", "Sin cortes"),
    (r"\b(dc|director.?s cut)\b", "Director's Cut"),
    (r"\bimax\b", "IMAX"),
]

RESOLUTION_PATTERNS = [
    (r"\b2160p\b", "2160p"),
    (r"\b(4k|uhd)\b", "2160p"),
    (r"\b1080p\b", "1080p"),
    (r"\b720p\b", "720p"),
    (r"\b576p\b", "576p"),
    (r"\b480p\b", "480p"),
]


def _first_match(patterns, text):
    """Devuelve el valor del primer patrón que aparece en el texto."""
    for pattern, value in patterns:
        if re.search(pattern, text):
            return value
    return None


def _detect_source(title_lower):
    return _first_match(SOURCE_PATTERNS, title_lower)


def _detect_codec(title_lower):
    return _first_match(CODEC_PATTERNS, title_lower)


def _detect_bit_depth(title_lower):
    return _first_match(BIT_DEPTH_PATTERNS, title_lower)


def _detect_hdr(title_lower):
    return _first_match(HDR_PATTERNS, title_lower)


def _detect_resolution(title_lower):
    return _first_match(RESOLUTION_PATTERNS, title_lower)


def _detect_audio(title_lower):
    """Combina códec (fuente única compartida) y cantidad de canales."""
    codec = detect_audio_codec(title_lower)
    channels = _first_match(CHANNEL_PATTERNS, title_lower)
    if codec and channels:
        return f"{codec} {channels}"
    return codec or channels


def _detect_edition(title_lower):
    return _first_match(EDITION_PATTERNS, title_lower)


def _detect_group(title):
    """El grupo de release suele ser el último token: 'Pelicula.2024-GRUPO'."""
    match = re.search(r"-([A-Za-z0-9]{2,20})\s*$", (title or "").strip())
    return match.group(1) if match else None


def parse_release_meta(title):
    """Extrae las características visibles en el nombre del release."""
    title = title or ""
    title_lower = title.lower()
    source = _detect_source(title_lower)
    return {
        "source": source,
        "resolution": _detect_resolution(title_lower),
        "video_codec": _detect_codec(title_lower),
        "bit_depth": _detect_bit_depth(title_lower),
        "hdr": _detect_hdr(title_lower),
        "audio": _detect_audio(title_lower),
        "edition": _detect_edition(title_lower),
        "group": _detect_group(title),
        "is_remux": source == "REMUX",
    }


def _codec_family(video_codec):
    """Solo interesa distinguir H.264 del resto para elegir los umbrales."""
    if (video_codec or "").upper() in ("H.264", "XVID"):
        return "h264"
    return "hevc"


def _tier_for_bpp(bpp, family):
    for threshold, tier in CODEC_THRESHOLDS[family]:
        if bpp >= threshold:
            return tier
    return "flojo"


def empty_estimate(resolution=None):
    """Estimación sin datos suficientes (sin duración de TMDB, sin resolución)."""
    return {
        "resolution": resolution,
        "mbps": None,
        "bpp": None,
        "tier": "sin_datos",
        "tier_label": TIER_LABELS["sin_datos"],
        "score": 0,
        "low_bitrate": False,
        "estimated": True,
        "fps": ASSUMED_FPS,
    }


def estimate_quality(size_bytes, runtime_min, meta, fps=ASSUMED_FPS):
    """Estima bitrate y bits por píxel usando el tamaño y la duración de TMDB.

    `meta` es el resultado de parse_release_meta(). Devuelve siempre la misma
    estructura; si faltan datos, el nivel queda en 'sin_datos'.
    """
    meta = meta or {}
    resolution = meta.get("resolution")
    estimate = empty_estimate(resolution)
    estimate["fps"] = fps

    if not size_bytes or not runtime_min:
        return estimate

    mbps = size_bytes * 8 / (runtime_min * 60) / 1e6

    if meta.get("is_remux"):
        # Un remux es copia directa del disco: el bpp no lo describe.
        estimate["mbps"] = round(mbps, 2)
        estimate["tier"] = "remux"
        estimate["tier_label"] = TIER_LABELS["remux"]
        estimate["score"] = 100
        return estimate

    dimensions = RESOLUTION_DIMENSIONS.get(resolution or "")
    if not dimensions:
        estimate["mbps"] = round(mbps, 2)
        return estimate

    width, height = dimensions
    bpp = mbps * 1e6 / (width * height * fps)
    family = _codec_family(meta.get("video_codec"))
    tier = _tier_for_bpp(bpp, family)
    excellent_bpp = CODEC_THRESHOLDS[family][0][0]

    estimate.update(
        {
            "mbps": round(mbps, 2),
            "bpp": round(bpp, 3),
            "tier": tier,
            "tier_label": TIER_LABELS[tier],
            "score": min(100, round(bpp / excellent_bpp * 100)),
            "low_bitrate": resolution == "1080p" and mbps < 2.0,
        }
    )
    return estimate
