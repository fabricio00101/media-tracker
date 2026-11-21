"""Utilidades de seguridad compartidas (redacción de secretos en logs)."""

import re

# Oculta credenciales que viajan en query strings o payloads logueados.
# La API v3 de TMDB exige api_key en la URL, así que un `str(e)` de requests
# puede filtrarla al log; esta función la enmascara antes de registrar.
_SECRET_PATTERN = re.compile(
    r"(?i)\b(api_key|apikey|token|password|secret)=([^&\s,}\"']+)"
)


def redact_secrets(text):
    """Devuelve el texto con los valores de credenciales enmascarados."""
    return _SECRET_PATTERN.sub(r"\1=***", str(text))
