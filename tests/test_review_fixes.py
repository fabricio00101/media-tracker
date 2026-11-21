"""Tests de regresión de los hallazgos de la revisión técnica (2026-11-21).

Cubre los casos que la suite original no tocaba: redirecciones SSRF, límites
de descarga, cuerpos JSON inválidos, token de API, fechas nulas de TMDB y
redacción de secretos en logs.
"""

import socket
from unittest.mock import MagicMock, patch

import pytest

import routes.deluge as deluge_mod
from utils.audio_patterns import detect_audio_codec
from utils.security import redact_secrets


def _fake_dns(mapping):
    """Devuelve un getaddrinfo falso: evita resolución DNS real en los tests."""

    def _getaddrinfo(host, port, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror(-2, "Name or service not known")
        ip = mapping[host]
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _getaddrinfo


def _response(status_code=200, headers=None, content=b""):
    """Response mínima con iter_content() para simular descargas en streaming."""
    res = MagicMock()
    res.status_code = status_code
    res.headers = headers or {}
    res.raise_for_status.return_value = None

    def _iter_content(chunk_size=65536):
        for offset in range(0, len(content), chunk_size):
            yield content[offset : offset + chunk_size]

    res.iter_content.side_effect = _iter_content
    return res


# ---------------------------------------------------------------------------
# A1 — SSRF: IPv4 mapeada en IPv6 y validación de cada redirección
# ---------------------------------------------------------------------------
def test_is_safe_remote_url_bloquea_ipv4_mapeada():
    """::ffff:169.254.169.254 debe evaluarse como la IPv4 de metadatos."""
    host = "::ffff:169.254.169.254"
    with patch(
        "routes.deluge.socket.getaddrinfo",
        side_effect=_fake_dns({host: host}),
    ):
        assert deluge_mod._is_safe_remote_url(f"http://[{host}]/") is False


def test_download_torrent_valida_cada_redireccion():
    """Un 302 hacia un host prohibido se rechaza sin hacer un segundo GET."""
    redirect = _response(302, {"Location": "http://metadata.local/x.torrent"})

    with patch(
        "routes.deluge._is_safe_remote_url", side_effect=[True, False]
    ), patch("routes.deluge.requests.get", return_value=redirect) as mock_get:
        with pytest.raises(deluge_mod.TorrentDownloadError) as exc:
            deluge_mod._download_torrent("http://prowlarr.local/dl")

    assert exc.value.status == 400
    assert mock_get.call_count == 1
    for _args, kwargs in mock_get.call_args_list:
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True


def test_download_torrent_acepta_redirect_a_magnet():
    """Un 302 hacia un magnet termina en add_torrent_magnet sin segundo GET."""
    redirect = _response(302, {"Location": "magnet:?xt=urn:btih:abc"})

    with patch("routes.deluge._is_safe_remote_url", return_value=True), patch(
        "routes.deluge.requests.get", return_value=redirect
    ) as mock_get:
        tipo, valor = deluge_mod._download_torrent("http://prowlarr.local/dl")

    assert (tipo, valor) == ("magnet", "magnet:?xt=urn:btih:abc")
    assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# A2 — Límites de descarga y validación de bencode
# ---------------------------------------------------------------------------
def test_download_torrent_rechaza_content_length_excesivo():
    """La cabecera Content-Length se comprueba antes de leer el cuerpo."""
    size = deluge_mod.TORRENT_MAX_BYTES + 1
    res = _response(200, {"Content-Length": str(size)})

    with patch("routes.deluge._is_safe_remote_url", return_value=True), patch(
        "routes.deluge.requests.get", return_value=res
    ):
        with pytest.raises(deluge_mod.TorrentDownloadError) as exc:
            deluge_mod._download_torrent("http://prowlarr.local/dl")

    assert exc.value.status == 502
    assert "tamaño máximo" in exc.value.message
    res.iter_content.assert_not_called()


def test_download_torrent_rechaza_cuerpo_sin_bencode():
    """Un HTML (o cualquier contenido no bencode) no se envía a Deluge."""
    content = b"<html>esto no es un torrent</html>"
    res = _response(200, {"Content-Length": str(len(content))}, content)

    with patch("routes.deluge._is_safe_remote_url", return_value=True), patch(
        "routes.deluge.requests.get", return_value=res
    ):
        with pytest.raises(deluge_mod.TorrentDownloadError) as exc:
            deluge_mod._download_torrent("http://prowlarr.local/dl")

    assert exc.value.status == 502
    assert "no parece" in exc.value.message


# ---------------------------------------------------------------------------
# M1 — Cuerpos inválidos siempre devuelven 400 JSON
# ---------------------------------------------------------------------------
@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
@pytest.mark.parametrize(
    "kwargs",
    [
        {"data": "{", "content_type": "application/json"},
        {"json": None},
        {"json": {"magnet": ["no", "texto"]}},
        {"json": {"magnet": "   "}},
        {"data": "magnet:?xt=abc", "content_type": "text/plain"},
    ],
)
def test_deluge_cuerpo_invalido_devuelve_400_json(kwargs, client):
    resp = client.post("/api/deluge/add", **kwargs)
    assert resp.status_code == 400
    assert resp.is_json
    assert resp.get_json()["error"]


# ---------------------------------------------------------------------------
# M10 — Token de API
# ---------------------------------------------------------------------------
@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
@patch("routes.deluge.config.API_SECRET_TOKEN", "token-secreto")
def test_deluge_exige_token_cuando_esta_configurado(client):
    """Sin token → 403; con el header correcto → flujo normal."""
    login = MagicMock()
    login.status_code = 200
    login.raise_for_status.return_value = None
    login.json.return_value = {"result": True}

    add = MagicMock()
    add.status_code = 200
    add.raise_for_status.return_value = None
    add.json.return_value = {}

    session = MagicMock()
    session.post.side_effect = [login, add]

    payload = {"magnet": "magnet:?xt=urn:btih:abc"}

    with patch("routes.deluge.requests.Session", return_value=session):
        sin_token = client.post("/api/deluge/add", json=payload)
        con_token = client.post(
            "/api/deluge/add", json=payload, headers={"X-Api-Token": "token-secreto"}
        )

    assert sin_token.status_code == 403
    assert con_token.status_code == 200
    assert session.post.call_count == 2


# ---------------------------------------------------------------------------
# A3 / M3 / bajo — saneamiento, fecha nula y regex de audio
# ---------------------------------------------------------------------------
def test_redact_secrets_enmascara_api_key():
    texto = "https://api.themoviedb.org/3/search?api_key=SECRETO123&query=x"
    resultado = redact_secrets(texto)
    assert "SECRETO123" not in resultado
    assert "api_key=***" in resultado


@patch("services.tmdb._fetch_runtime", return_value=120)
@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "clave-de-prueba")
def test_tmdb_release_date_none_no_revienta(mock_get, _mock_runtime):
    """Un release_date nulo no debe provocar TypeError al cortar el año."""
    from services.tmdb import get_tmdb_info

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "results": [
            {
                "id": 1,
                "title": "Peli",
                "release_date": None,
                "vote_count": 1000,
            }
        ]
    }

    info = get_tmdb_info("Peli", 2020)
    assert info is not None
    assert info["year"] == ""


def test_detect_audio_codec_dd_plus():
    """Regresión de la regex `dd\\+` con \\b final, que nunca matcheaba."""
    assert detect_audio_codec("peli 1080p dd+ 5.1 x264") == "DD+"
