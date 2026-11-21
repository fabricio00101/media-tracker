import re

from utils.audio_patterns import detect_audio_codec

# Traducción de la etiqueta canónica a la etiqueta de UI existente.
_AUDIO_DISPLAY = {
    "Atmos": "Dolby Atmos / TrueHD",
    "TrueHD": "Dolby Atmos / TrueHD",
    "DTS-HD": "DTS-HD / X",
    "DD+": "Dolby Digital Plus",
    "DD": "Dolby Digital",
    "DTS": "DTS",
    "AAC": "AAC",
}


def detect_spanish(title_lower):
    """Detecta el soporte de español a partir del título en minúsculas.

    Usa límites de palabra y patrones para evitar falsos positivos con substrings.
    """
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


def detect_audio(title_lower):
    """Detecta el formato de audio a partir del título en minúsculas.

    Usa la misma fuente de patrones que la estimación técnica; los códecs que
    no aportan información de idioma (FLAC/Opus/MP3) devuelven None.
    """
    return _AUDIO_DISPLAY.get(detect_audio_codec(title_lower))


def matches_language(spanish_support, lang_filters):
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
