import re


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
