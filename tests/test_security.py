"""Tests de regresión de seguridad: SSRF, fuerza bruta y manejo de credenciales."""

import socket
from unittest.mock import patch, MagicMock

import pytest
import requests

import routes.deluge as deluge_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fake_dns(mapping):
    """Devuelve un getaddrinfo falso: evita resolución DNS real en los tests."""

    def _getaddrinfo(host, port, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror(-2, "Name or service not known")
        ip = mapping[host]
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _getaddrinfo


# ---------------------------------------------------------------------------
# 1) SSRF: _is_safe_remote_url
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "url, mapping, esperado",
    [
        # Esquemas no web: siempre rechazados
        ("file:///C:/Windows/win.ini", {}, False),
        ("ftp://example.com/x.torrent", {}, False),
        ("javascript:alert(1)", {}, False),
        ("", {}, False),
        # Destinos link-local / metadata: rechazados
        ("http://169.254.169.254/latest/meta-data/", {"m": "169.254.169.254"}, False),
        ("http://metadata/", {"metadata": "169.254.169.254"}, False),
        ("http://[fe80::1]/", {"fe80::1": "fe80::1"}, False),
        # 0.0.0.0 apunta a localhost: rechazado
        ("http://0.0.0.0:80/", {"0.0.0.0": "0.0.0.0"}, False),
        # Host no resoluble: rechazado
        ("http://no-existe.invalid/", {}, False),
        # Hosts válidos: permitidos (Prowlarr suele estar en red privada)
        ("http://192.168.1.10:9696/api/v1/search", {"192.168.1.10": "192.168.1.10"}, True),
        ("http://localhost:9696/", {"localhost": "127.0.0.1"}, True),
        ("https://example.com/dl", {"example.com": "93.184.216.34"}, True),
    ],
)
def test_is_safe_remote_url(url, mapping, esperado):
    with patch("routes.deluge.socket.getaddrinfo", side_effect=fake_dns(mapping)):
        assert deluge_mod._is_safe_remote_url(url) is esperado


# ---------------------------------------------------------------------------
# 2) Endpoint Deluge: validaciones
# ---------------------------------------------------------------------------
@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_rechaza_url_ssrf(client):
    """Un magnet que apunta a metadatos internos debe morir antes de tocar la red."""
    auth = MagicMock()
    auth.status_code = 200
    auth.json.return_value = {"result": True}

    mock_session = MagicMock()
    mock_session.post.return_value = auth

    with patch("routes.deluge.requests.Session", return_value=mock_session), patch(
        "routes.deluge.requests.get"
    ) as mock_get:
        resp = client.post(
            "/api/deluge/add",
            json={"magnet": "http://169.254.169.254/latest/meta-data/"},
        )
        assert resp.status_code == 400
        assert "no está permitido" in resp.get_json()["error"]
        mock_get.assert_not_called()


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_sin_magnet_devuelve_400(client):
    resp = client.post("/api/deluge/add", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


@patch("routes.deluge.config.DELUGE_URL", "")
@patch("routes.deluge.config.DELUGE_PASSWORD", "")
def test_deluge_sin_credenciales_devuelve_500(client):
    resp = client.post("/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:123"})
    assert resp.status_code == 500
    assert ".env" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# 3) Fuerza bruta: el endpoint que recibe la contraseña tiene límite
# ---------------------------------------------------------------------------
@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_tiene_rate_limit(client):
    """Era el único endpoint sin @limiter: la contraseña viaja en JSON-RPC."""

    def _conexion_rechazada(*args, **kwargs):
        raise requests.exceptions.ConnectionError("sin conexion")

    with patch("routes.deluge.requests.Session") as mock_session:
        mock_session.return_value.post.side_effect = _conexion_rechazada

        codes = [
            client.post(
                "/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:123"}
            ).status_code
            for _ in range(11)
        ]

    # 10 dentro de la cuota (fallan por conexión, no por límite), la 11.ª bloqueada
    assert codes[:10] == [503] * 10, codes
    assert codes[10] == 429, codes


# ---------------------------------------------------------------------------
# 4) La API key de Prowlarr viaja por header, nunca por query string
# ---------------------------------------------------------------------------
@patch("routes.search.config.PROWLARR_API_KEY", "super-secreta")
@patch("routes.search.requests.get")
def test_prowlarr_api_key_por_header(mock_get, client):
    mock_res = mock_get.return_value
    mock_res.status_code = 200
    mock_res.json.return_value = []
    mock_res.raise_for_status.return_value = None

    resp = client.get("/api/search?query=matrix&min_size_gb=1")
    assert resp.status_code == 200

    _url, kwargs = mock_get.call_args
    assert kwargs["headers"]["X-Api-Key"] == "super-secreta"
    assert "apikey" not in kwargs["params"]
