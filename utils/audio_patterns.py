"""Fuente única de detección de códecs de audio a partir del nombre del release.

La usan `utils.media_meta` (estimación técnica) y `utils.language_detector`
(etiqueta de audio en la UI) para no mantener dos listas de patrones distintas.
"""

import re

# Orden importante: los formatos más específicos van primero (Atmos antes que
# TrueHD, DD+ antes que DD). El grupo `dd\+` no lleva `\b` final porque el "+"
# es un carácter no-palabra: "DD+ 5.1" no tendría límite de palabra después.
AUDIO_CODEC_RULES = [
    (r"\batmos\b", "Atmos"),
    (r"\b(truehd|true-hd)\b", "TrueHD"),
    (r"\b(dts[- ]?hd|dtsx|dts[- ]?x)\b", "DTS-HD"),
    # DDP/EAC3 suele venir pegado a los canales: DDP5.1, DDP7.1, DD+5.1
    (r"\b(?:eac3|ddp\d?\.\d|ddp|dd\+)", "DD+"),
    (r"\b(ac3|dd5|dd2|dolby[ .]?digital)\b", "DD"),
    (r"\bdts\b", "DTS"),
    (r"\baac\d?", "AAC"),
    (r"\bflac\b", "FLAC"),
    (r"\bopus\b", "Opus"),
    (r"\bmp3\b", "MP3"),
]


def detect_audio_codec(title_lower):
    """Devuelve la etiqueta canónica del códec de audio o None."""
    for pattern, label in AUDIO_CODEC_RULES:
        if re.search(pattern, title_lower):
            return label
    return None
