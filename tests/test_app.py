"""Tests de la aplicación: página principal, handlers de error y Redis."""

from app import app, _redis_available, USE_REDIS, error_page_context


# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------
def test_index_devuelve_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'id="searchForm"' in resp.data


# ---------------------------------------------------------------------------
# Handlers de error: HTML para la web, JSON para la API
# ---------------------------------------------------------------------------
def test_404_html_usa_pagina_de_error(client):
    resp = client.get("/ruta-que-no-existe")
    assert resp.status_code == 404
    assert b"Error del Servidor" not in resp.data, "un 404 no debe decir 500"
    assert "Página no encontrada".encode() in resp.data
    assert "404 - No encontramos lo que buscas".encode() in resp.data


def test_404_api_devuelve_json(client):
    resp = client.get("/api/que-no-existe")
    assert resp.status_code == 404

    data = resp.get_json()
    assert data is not None, "las rutas /api/* deben responder JSON, no HTML"
    assert "error" in data
    assert data["error"]


# ---------------------------------------------------------------------------
# Contexto dinámico de la página de error
# ---------------------------------------------------------------------------
def test_contexto_error_404():
    ctx = error_page_context(404)
    assert ctx["code"] == 404
    assert ctx["title"] == "Página no encontrada"
    assert ctx["subtitle"].startswith("404")


def test_contexto_error_500():
    ctx = error_page_context(500)
    assert ctx["code"] == 500
    assert ctx["title"] == "Error del Servidor"
    assert ctx["subtitle"].startswith("500")


def test_contexto_error_desconocido_usa_el_codigo():
    """Códigos no previstos (429, 503, ...) deben mostrar su propio número."""
    ctx = error_page_context(503, "Servicio caído")
    assert ctx["code"] == 503
    assert "503" in ctx["subtitle"]
    assert ctx["description"] == "Servicio caído"


def test_contexto_error_sin_description_no_falla():
    ctx = error_page_context(418)
    assert ctx["code"] == 418
    assert ctx["description"]


# ---------------------------------------------------------------------------
# Detección de Redis con degradación a memoria
# ---------------------------------------------------------------------------
def test_redis_sin_url_devuelve_false():
    assert _redis_available("") is False


def test_redis_inaccesible_devuelve_false():
    # Puerto 1: conexión rechazada al instante, sin esperas de timeout
    assert _redis_available("redis://127.0.0.1:1/0") is False


def test_use_redis_es_booleano():
    """USE_REDIS se calcula al arrancar y debe ser un booleano, no una cadena."""
    assert isinstance(USE_REDIS, bool)


def test_sin_redis_url_no_usa_redis():
    """Si no hay REDIS_URL declarada, el arranque debe degradar a memoria."""
    import config

    if not config.REDIS_URL:
        assert USE_REDIS is False
