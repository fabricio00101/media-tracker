import base64
import hmac
import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse

import requests
from flask import Blueprint, request, jsonify

from extensions import limiter
import config
from utils.security import redact_secrets

deluge_bp = Blueprint("deluge", __name__)

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5
TORRENT_MAX_BYTES = config.TORRENT_MAX_BYTES


class TorrentDownloadError(Exception):
    """Falla controlada al descargar un .torrent (mensaje apto para el cliente)."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def _json_error(message, status):
    """Respuesta JSON de error uniforme en español."""
    return jsonify({"error": message}), status


def _ip_is_blocked(ip_text):
    """True si la IP es un destino que nunca debe descargarse.

    Bloquea link-local (metadatos de cloud), no especificadas, multicast y
    reservadas, incluidos los equivalentes IPv4-mapeados en IPv6
    (::ffff:169.254.169.254). La política sobre rangos privados/loopback se
    documenta en config.py (SSRF_ALLOW_PRIVATE_TARGETS).
    """
    try:
        # Quita la zona IPv6 (fe80::1%eth0) antes de parsear
        addr = ipaddress.ip_address(str(ip_text).split("%")[0])
    except ValueError:
        return True

    # ::ffff:x.x.x.x debe evaluarse como la IPv4 subyacente
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        addr = mapped

    if addr.is_loopback:
        # En algunas versiones de Python ::1 también se marca como reservado.
        # Loopback se rige por la política de destinos privados configurada.
        return not config.SSRF_ALLOW_PRIVATE_TARGETS

    if (
        addr.is_link_local
        or addr.is_unspecified
        or addr.is_multicast
        or addr.is_reserved
    ):
        return True

    if not config.SSRF_ALLOW_PRIVATE_TARGETS and addr.is_private:
        return True

    return False


def _is_safe_remote_url(url):
    """Valida que una URL remota sea descargable sin exponer SSRF.

    Bloquea esquemas no web y destinos de metadatos (169.254.0.0/16 incluye
    169.254.169.254, fe80::/10, 0.0.0.0/8 y sus formas IPv4-mapeadas). Los
    hosts privados/loopback se permiten según la política configurada.
    """
    return _remote_url_rejection_reason(url) is None


def _remote_url_rejection_reason(url):
    """Explica por qué una URL no es segura, sin incluirla en la respuesta."""
    try:
        parsed = urlparse(url)
    except Exception:
        return "la URL tiene un formato inválido"

    if parsed.scheme not in ("http", "https"):
        return "solo se permiten URLs HTTP o HTTPS"
    if not parsed.hostname:
        return "la URL no contiene un host"

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return "el host no pudo resolverse por DNS"

    for info in infos:
        resolved_ip = info[4][0]
        if _ip_is_blocked(resolved_ip):
            logging.warning(
                "URL bloqueada por SSRF: host %s resuelve a %s (URL: %s)",
                parsed.hostname,
                resolved_ip,
                redact_secrets(url),
            )
            return (
                f"el host {parsed.hostname} resuelve a la dirección "
                f"{resolved_ip}, bloqueada por seguridad"
            )

    return None


def _looks_like_torrent(content):
    """Validación mínima de bencode: diccionario con la clave 'info'."""
    return content[:1] == b"d" and b"4:info" in content[:4096]


def _too_large_error():
    return TorrentDownloadError(
        f"El archivo .torrent supera el tamaño máximo permitido "
        f"({TORRENT_MAX_BYTES // (1024 * 1024)} MB).",
        502,
    )


def _read_limited(response, limit):
    """Lee el cuerpo en bloques y aborta si supera el tope indicado."""
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > limit:
                raise _too_large_error()
        except (TypeError, ValueError):
            # Cabecera ausente o malformada: el tope se controla al leer
            pass

    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise _too_large_error()
        chunks.append(chunk)
    return b"".join(chunks)


def _download_torrent(url):
    """Descarga un .torrent validando cada salto de redirección.

    Devuelve ("magnet", magnet_url) si una redirección apunta a un magnet, o
    ("torrent", bytes) con el contenido ya validado.
    """
    if not _is_safe_remote_url(url):
        rejection_reason = _remote_url_rejection_reason(url)
        if not rejection_reason:
            rejection_reason = "el destino no está permitido por seguridad"
        raise TorrentDownloadError(
            "URL de descarga rechazada: el destino no está permitido "
            f"({rejection_reason}).",
            400,
        )

    current = url
    for _ in range(MAX_REDIRECTS + 1):
        # allow_redirects=False SIEMPRE: cada Location se valida por separado.
        response = requests.get(
            current, timeout=120, allow_redirects=False, stream=True
        )

        if response.status_code in REDIRECT_STATUSES:
            raw_location = response.headers.get("Location", "")
            if not raw_location:
                raise TorrentDownloadError(
                    "Prowlarr devolvió una redirección sin destino.", 502
                )
            location = urljoin(current, raw_location)

            if location.lower().startswith("magnet:"):
                return "magnet", location
            if not _is_safe_remote_url(location):
                raise TorrentDownloadError(
                    "Redirección rechazada: el destino no está permitido.", 400
                )
            current = location
            continue

        response.raise_for_status()
        content = _read_limited(response, TORRENT_MAX_BYTES)
        if not _looks_like_torrent(content):
            raise TorrentDownloadError(
                "El contenido descargado no parece un archivo .torrent válido.", 502
            )
        return "torrent", content

    raise TorrentDownloadError(
        "Demasiadas redirecciones al descargar el .torrent.", 502
    )


def _is_authorized():
    """Comprueba el token opcional en tiempo constante."""
    if not config.API_SECRET_TOKEN:
        return True

    auth_header = request.headers.get("X-Api-Token") or request.headers.get(
        "Authorization", ""
    )
    if auth_header.startswith("Bearer "):
        auth_header = auth_header[7:].strip()

    try:
        return hmac.compare_digest(
            auth_header.encode("utf-8"), config.API_SECRET_TOKEN.encode("utf-8")
        )
    except Exception:
        return False


@deluge_bp.route("/api/deluge/add", methods=["POST"])
@limiter.limit("10 per minute")
def add_to_deluge():
    # Autorización opcional por token: si se configuró API_SECRET_TOKEN, se exige
    if not _is_authorized():
        return _json_error("No autorizado para interactuar con Deluge.", 403)

    if not config.DELUGE_URL or not config.DELUGE_PASSWORD:
        return _json_error(
            "Las credenciales de Deluge no están configuradas en .env "
            "(DELUGE_URL y DELUGE_PASSWORD).",
            500,
        )

    # M1: cualquier cuerpo que no sea un objeto JSON con "magnet" texto → 400 JSON
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _json_error(
            "El cuerpo debe ser un objeto JSON con el campo 'magnet'.", 400
        )

    magnet_url = data.get("magnet")
    if not isinstance(magnet_url, str) or not magnet_url.strip():
        return _json_error("Se requiere un magnet válido (texto no vacío).", 400)

    magnet_url = magnet_url.strip()
    json_rpc_url = f"{config.DELUGE_URL}/json"

    try:
        # La sesión se cierra siempre, incluso ante errores.
        session = requests.Session()
        try:
            login_payload = {
                "method": "auth.login",
                "params": [config.DELUGE_PASSWORD],
                "id": 1,
            }
            login_res = session.post(json_rpc_url, json=login_payload, timeout=10)
            login_res.raise_for_status()
            login_data = login_res.json()

            if not login_data.get("result"):
                return _json_error("Contraseña de Deluge incorrecta.", 401)

            if magnet_url.lower().startswith("magnet:"):
                add_payload = {
                    "method": "core.add_torrent_magnet",
                    "params": [magnet_url, {}],
                    "id": 2,
                }
            else:
                try:
                    tipo, valor = _download_torrent(magnet_url)
                except TorrentDownloadError as e:
                    return _json_error(e.message, e.status)
                except Exception as e:
                    logging.error(
                        "Fallo interceptando .torrent desde Prowlarr: %s",
                        redact_secrets(e),
                    )
                    return _json_error(
                        "Fallo interceptando .torrent desde Prowlarr local.", 500
                    )

                if tipo == "magnet":
                    add_payload = {
                        "method": "core.add_torrent_magnet",
                        "params": [valor, {}],
                        "id": 2,
                    }
                else:
                    b64_torrent = base64.b64encode(valor).decode("utf-8")
                    add_payload = {
                        "method": "core.add_torrent_file",
                        "params": ["descarga.torrent", b64_torrent, {}],
                        "id": 2,
                    }

            add_res = session.post(json_rpc_url, json=add_payload, timeout=10)
            add_res.raise_for_status()
            add_data = add_res.json()

            if add_data.get("error"):
                return _json_error(
                    f"Error insertando en Deluge: {add_data['error']}", 500
                )

            return jsonify({"message": "Añadido exitosamente a Deluge."})
        finally:
            session.close()

    except requests.exceptions.ConnectionError:
        return _json_error(
            f"No se pudo conectar a Deluge en {config.DELUGE_URL}", 503
        )
    except Exception as e:
        # A3: nunca se devuelve str(e) al cliente (puede incluir credenciales)
        logging.error("Error al contactar Deluge Web UI: %s", redact_secrets(e))
        return _json_error("Error interno contactando con Deluge.", 500)
