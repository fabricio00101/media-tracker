import requests
import config
from utils.security import redact_secrets


class ProwlarrError(Exception):
    """Error de comunicación con Prowlarr, con el código HTTP a devolver."""

    def __init__(self, message, code="PROWLARR_ERROR", status=502):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def fetch_prowlarr(query, category):
    """Consulta Prowlarr y devuelve la lista cruda de resultados verificados."""
    endpoint = f"{config.PROWLARR_URL}/api/v1/search"
    headers = {"X-Api-Key": config.PROWLARR_API_KEY}
    params = {"query": query, "type": "search"}

    if category == "movies":
        params["categories"] = [2000]
    elif category == "tv":
        params["categories"] = [5000]
    elif category == "docs":
        params["categories"] = [8000]

    if config.PROWLARR_SEARCH_LIMIT > 0:
        params["limit"] = config.PROWLARR_SEARCH_LIMIT

    try:
        # Timeout configurable: las búsquedas con muchos indexers tardan
        # 187-236 s (ver session_log.md); 30 s fallaba en la UI.
        response = requests.get(
            endpoint, params=params, headers=headers, timeout=config.PROWLARR_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError:
        raise ProwlarrError(
            f"No se pudo conectar con Prowlarr en {config.PROWLARR_URL}. "
            "Verifica que esté encendido.",
            code="PROWLARR_UNAVAILABLE",
            status=503,
        )
    except requests.exceptions.RequestException as e:
        raise ProwlarrError(
            f"Error comunicándose con Prowlarr: {redact_secrets(e)}",
            code="PROWLARR_COMMUNICATION_ERROR",
            status=502,
        )
    except ValueError:
        raise ProwlarrError(
            "Respuesta inválida de Prowlarr (no es un JSON válido).",
            code="PROWLARR_INVALID_JSON",
            status=500,
        )

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("Results"), list):
        items = data["Results"]
    else:
        raise ProwlarrError(
            "Estructura de respuesta inesperada de Prowlarr.",
            code="PROWLARR_UNEXPECTED_STRUCTURE",
            status=502,
        )

    valid_items = []
    for item in items:
        if isinstance(item, dict) and item.get("title"):
            valid_items.append(item)
    return valid_items
