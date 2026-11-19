"""Tests de regresión para routes/deluge.py: ramas de éxito y error del endpoint.

Cubre lo que test_security.py no toca: flujos felices, errores de Deluge,
redirecciones de Prowlarr y descarga física de .torrent.
"""

from unittest.mock import patch, MagicMock

import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code=200, json_data=None, raise_exc=None, content=b""):
    """Devuelve un MagicMock que imita un requests.Response."""
    res = MagicMock()
    res.status_code = status_code
    res.json.return_value = json_data if json_data is not None else {}
    res.content = content
    if raise_exc:
        res.raise_for_status.side_effect = raise_exc
    else:
        res.raise_for_status.return_value = None
    return res


def test_is_safe_remote_url_urlparse_falla():
    """Si urlparse lanza, la URL se considera insegura (defensa en profundidad)."""
    with patch("routes.deluge.urlparse", side_effect=ValueError("malformada")):
        from routes.deluge import _is_safe_remote_url

        assert _is_safe_remote_url("http://example.com/x") is False


# ---------------------------------------------------------------------------
# 1) Magnet: flujos de éxito y error en Deluge
# ---------------------------------------------------------------------------

@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_magnet_exitoso(client):
    """Magnet válido: login OK + add_torrent_magnet OK → 200."""
    login_res = _mock_response(json_data={"result": True})
    add_res = _mock_response(json_data={})

    mock_session = MagicMock()
    mock_session.post.side_effect = [login_res, add_res]

    with patch("routes.deluge.requests.Session", return_value=mock_session):
        resp = client.post(
            "/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:abc"}
        )
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Añadido exitosamente a Deluge."
    assert mock_session.post.call_count == 2


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_add_con_error_en_respuesta(client):
    """add_torrent_magnet devuelve 'error' en el JSON → 500."""
    login_res = _mock_response(json_data={"result": True})
    add_res = _mock_response(json_data={"error": "Torrent ya existe"})

    mock_session = MagicMock()
    mock_session.post.side_effect = [login_res, add_res]

    with patch("routes.deluge.requests.Session", return_value=mock_session):
        resp = client.post(
            "/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:abc"}
        )
    assert resp.status_code == 500
    assert "Error insertando en Deluge" in resp.get_json()["error"]


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_add_res_raise_for_status(client):
    """add_res.raise_for_status() lanza → 500 (except Exception externo)."""
    login_res = _mock_response(json_data={"result": True})
    add_res = _mock_response(status_code=500, raise_exc=Exception("HTTP 500"))

    mock_session = MagicMock()
    mock_session.post.side_effect = [login_res, add_res]

    with patch("routes.deluge.requests.Session", return_value=mock_session):
        resp = client.post(
            "/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:abc"}
        )
    assert resp.status_code == 500
    assert "Error interno contactando con Deluge" in resp.get_json()["error"]


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_login_result_falso(client):
    """Login 200 pero result falsy → 401."""
    login_res = _mock_response(json_data={"result": False})

    mock_session = MagicMock()
    mock_session.post.return_value = login_res

    with patch("routes.deluge.requests.Session", return_value=mock_session):
        resp = client.post(
            "/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:abc"}
        )
    assert resp.status_code == 401
    assert "Contraseña de Deluge incorrecta" in resp.get_json()["error"]


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_login_connection_error(client):
    """ConnectionError en login → 503."""
    def _conexion_rechazada(*args, **kwargs):
        raise requests.exceptions.ConnectionError("sin conexion")

    mock_session = MagicMock()
    mock_session.post.side_effect = _conexion_rechazada

    with patch("routes.deluge.requests.Session", return_value=mock_session):
        resp = client.post(
            "/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:abc"}
        )
    assert resp.status_code == 503
    assert "No se pudo conectar a Deluge" in resp.get_json()["error"]


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_login_excepcion_generica(client):
    """Excepción genérica en login → 500."""
    mock_session = MagicMock()
    mock_session.post.side_effect = Exception("algo falló")

    with patch("routes.deluge.requests.Session", return_value=mock_session):
        resp = client.post(
            "/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:abc"}
        )
    assert resp.status_code == 500
    assert "Error interno contactando con Deluge" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# 2) URL HTTP → descarga de .torrent
# ---------------------------------------------------------------------------

@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
@patch("routes.deluge._is_safe_remote_url", return_value=True)
def test_deluge_descarga_torrent_exitoso(mock_safe, client):
    """URL HTTP segura: descarga 200 → core.add_torrent_file → 200."""
    login_res = _mock_response(json_data={"result": True})
    t_res = _mock_response(content=b"contenido-del-torrent")
    add_res = _mock_response(json_data={})

    mock_session = MagicMock()
    mock_session.post.side_effect = [login_res, add_res]

    with patch("routes.deluge.requests.Session", return_value=mock_session), \
         patch("routes.deluge.requests.get", return_value=t_res):
        resp = client.post(
            "/api/deluge/add",
            json={"magnet": "http://prowlarr:9696/api/download/123"},
        )
    assert resp.status_code == 200
    assert mock_session.post.call_count == 2
    # La segunda llamada debe ser add_torrent_file (no magnet)
    add_call = mock_session.post.call_args_list[1]
    assert "add_torrent_file" in str(add_call)


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
@patch("routes.deluge._is_safe_remote_url", return_value=True)
def test_deluge_descarga_torrent_falla(mock_safe, client):
    """raise_for_status en la descarga lanza → 500."""
    login_res = _mock_response(json_data={"result": True})
    t_res = _mock_response(status_code=404, raise_exc=Exception("HTTP 404"))

    mock_session = MagicMock()
    mock_session.post.return_value = login_res

    with patch("routes.deluge.requests.Session", return_value=mock_session), \
         patch("routes.deluge.requests.get", return_value=t_res):
        resp = client.post(
            "/api/deluge/add",
            json={"magnet": "http://prowlarr:9696/api/download/123"},
        )
    assert resp.status_code == 500
    assert "Fallo interceptando" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# 3) Redirecciones de Prowlarr (302)
# ---------------------------------------------------------------------------

@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
@patch("routes.deluge._is_safe_remote_url", return_value=True)
def test_deluge_redireccion_302_a_magnet(mock_safe, client):
    """302 con Location magnet: → add_torrent_magnet con esa URL → 200."""
    login_res = _mock_response(json_data={"result": True})
    t_res = MagicMock()
    t_res.status_code = 302
    t_res.headers = {"Location": "magnet:?xt=urn:btih:redir"}
    add_res = _mock_response(json_data={})

    mock_session = MagicMock()
    mock_session.post.side_effect = [login_res, add_res]

    with patch("routes.deluge.requests.Session", return_value=mock_session), \
         patch("routes.deluge.requests.get", return_value=t_res):
        resp = client.post(
            "/api/deluge/add",
            json={"magnet": "http://prowlarr:9696/api/download/123"},
        )
    assert resp.status_code == 200
    add_call = mock_session.post.call_args_list[1]
    assert "magnet:?xt=urn:btih:redir" in str(add_call)


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
@patch("routes.deluge._is_safe_remote_url", return_value=True)
def test_deluge_redireccion_302_sin_location(mock_safe, client):
    """302 sin Location → 502."""
    login_res = _mock_response(json_data={"result": True})
    t_res = MagicMock()
    t_res.status_code = 302
    t_res.headers = {}

    mock_session = MagicMock()
    mock_session.post.return_value = login_res

    with patch("routes.deluge.requests.Session", return_value=mock_session), \
         patch("routes.deluge.requests.get", return_value=t_res):
        resp = client.post(
            "/api/deluge/add",
            json={"magnet": "http://prowlarr:9696/api/download/123"},
        )
    assert resp.status_code == 502
    assert "sin destino" in resp.get_json()["error"]


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_deluge_redireccion_a_url_no_segura(client):
    """302 a URL que _is_safe_remote_url rechaza → 400."""
    login_res = _mock_response(json_data={"result": True})
    t_res = MagicMock()
    t_res.status_code = 302
    t_res.headers = {"Location": "http://evil.com/x.torrent"}

    mock_session = MagicMock()
    mock_session.post.return_value = login_res

    # _is_safe_remote_url se llama 2 veces: URL original (True) y redirección (False)
    with patch("routes.deluge.requests.Session", return_value=mock_session), \
         patch("routes.deluge.requests.get", return_value=t_res), \
         patch("routes.deluge._is_safe_remote_url", side_effect=[True, False]):
        resp = client.post(
            "/api/deluge/add",
            json={"magnet": "http://prowlarr:9696/api/download/123"},
        )
    assert resp.status_code == 400
    assert "Redirección rechazada" in resp.get_json()["error"]


@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
@patch("routes.deluge._is_safe_remote_url", return_value=True)
def test_deluge_redireccion_web_segunda_peticion_falla(mock_safe, client):
    """302 a URL web, segunda GET falla → 500."""
    login_res = _mock_response(json_data={"result": True})
    t_res = MagicMock()
    t_res.status_code = 302
    t_res.headers = {"Location": "http://prowlarr:9696/api/actual/123"}
    t_res2 = _mock_response(status_code=500, raise_exc=Exception("HTTP 500"))

    mock_session = MagicMock()
    mock_session.post.return_value = login_res

    with patch("routes.deluge.requests.Session", return_value=mock_session), \
         patch("routes.deluge.requests.get", side_effect=[t_res, t_res2]):
        resp = client.post(
            "/api/deluge/add",
            json={"magnet": "http://prowlarr:9696/api/download/123"},
        )
    assert resp.status_code == 500
    assert "Fallo interceptando" in resp.get_json()["error"]
