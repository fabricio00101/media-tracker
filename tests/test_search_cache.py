"""Tests de regresión de performance: caché, concurrencia y metadatos."""

import threading
import time
from unittest.mock import patch, MagicMock

import pytest
import requests

import routes.search as rs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _prowlarr_response(items):
    res = MagicMock()
    res.status_code = 200
    res.json.return_value = items
    res.raise_for_status.return_value = None
    return res


def _item(i):
    return {
        "title": f"Pelicula{i}.2023.1080p.WEBRip.x264",
        "size": 16106127360,
        "seeders": i,
        "indexer": "TestTracker",
        "magnetUrl": f"magnet:?xt=urn:btih:{i}",
    }


# ---------------------------------------------------------------------------
# 1) Cache stampede: N peticiones iguales -> 1 sola consulta a Prowlarr
# ---------------------------------------------------------------------------
@patch("routes.search.get_tmdb_info", return_value=None)
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_cache_stampede_una_sola_llamada(mock_tmdb, simple_cache_app):
    llamadas = {"n": 0}
    contador = threading.Lock()
    codigos = []

    def prowlarr_lento(url, **kwargs):
        with contador:
            llamadas["n"] += 1
        time.sleep(0.3)
        return _prowlarr_response([_item(1)])

    def hit():
        client = simple_cache_app.test_client()
        codigos.append(client.get("/api/search?query=matrix&min_size_gb=1").status_code)

    with patch("routes.search.requests.get", side_effect=prowlarr_lento):
        hilos = [threading.Thread(target=hit) for _ in range(8)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

    assert llamadas["n"] == 1, f"se hicieron {llamadas['n']} consultas, se esperaba 1"
    assert codigos == [200] * 8, codigos


@patch("routes.search.get_tmdb_info", return_value=None)
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_cache_hit_no_vuelve_a_consultar(mock_tmdb, simple_cache_app):
    """La segunda búsqueda idéntica debe salir de la caché."""
    llamadas = {"n": 0}

    def contar(url, **kwargs):
        llamadas["n"] += 1
        return _prowlarr_response([_item(1)])

    client = simple_cache_app.test_client()

    with patch("routes.search.requests.get", side_effect=contar):
        assert client.get("/api/search?query=gladiator&min_size_gb=1").status_code == 200
        assert client.get("/api/search?query=gladiator&min_size_gb=1").status_code == 200

    assert llamadas["n"] == 1, llamadas


# ---------------------------------------------------------------------------
# 2) Tope de resultados hacia Prowlarr
# ---------------------------------------------------------------------------
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_limit_enviado_a_prowlarr(client):
    with patch("routes.search.requests.get", side_effect=_prowlarr_response([])) as mock_get:
        assert client.get("/api/search?query=zzz&min_size_gb=1").status_code == 200

    _url, kwargs = mock_get.call_args
    assert kwargs["params"]["limit"] == 500


# ---------------------------------------------------------------------------
# 3) Resolución de metadatos
# ---------------------------------------------------------------------------
def test_resolve_titles_sin_entradas(app):
    with app.test_request_context("/"):
        assert rs._resolve_titles({}) == ({}, {})


def test_resolve_titles_en_paralelo(app):
    """Debe resolver todos los títulos únicos y no perder ninguno."""
    unicos = {f"key_{i}": (f"Titulo {i}", "2023", False) for i in range(12)}
    resueltos = []

    def fake(title, year=None, is_tv=False):
        resueltos.append(title)
        return {
            "id": 1,
            "title": title,
            "overview": "o",
            "poster_url": None,
            "year": year,
        }

    with app.test_request_context("/"):
        with patch("routes.search.get_tmdb_info", side_effect=fake):
            title_to_key, tmdb_cache = rs._resolve_titles(unicos)

    assert len(resueltos) == 12
    assert len(title_to_key) == 12
    assert all(k.startswith("tmdb_") for k in title_to_key.values())
    assert len(tmdb_cache) == 12


def test_resolve_titles_fallback_local(app):
    """Sin TMDB (o si falla) debe agrupar igual, con un grupo local."""
    with app.test_request_context("/"):
        with patch("routes.search.get_tmdb_info", return_value=None):
            title_to_key, tmdb_cache = rs._resolve_titles(
                {"k": ("Mi Pelicula", "2020", False)}
            )

    group_key = title_to_key["k"]
    assert group_key.startswith("local_")
    assert tmdb_cache[group_key]["title"] == "Mi Pelicula".title()
    assert "Sinopsis" in tmdb_cache[group_key]["overview"]
    assert tmdb_cache[group_key]["id"] is None
    assert tmdb_cache[group_key]["media_type"] == "movie"


def test_resolve_titles_fallback_local_serie(app):
    """Sin TMDB, una serie igual queda marcada como tv y sin id."""
    with app.test_request_context("/"):
        with patch("routes.search.get_tmdb_info", return_value=None):
            title_to_key, tmdb_cache = rs._resolve_titles(
                {"k": ("Mi Serie", "2020", True)}
            )

    group_key = title_to_key["k"]
    assert tmdb_cache[group_key]["id"] is None
    assert tmdb_cache[group_key]["media_type"] == "tv"


def test_resolve_titles_completa_media_type_de_cache_vieja(app):
    """Entradas memoizadas antes del cambio no traen media_type."""
    info_vieja = {
        "id": 1,
        "title": "Serie Vieja",
        "overview": "o",
        "poster_url": None,
        "year": "2020",
    }

    with app.test_request_context("/"):
        with patch("routes.search.get_tmdb_info", return_value=dict(info_vieja)):
            title_to_key, tmdb_cache = rs._resolve_titles(
                {"k": ("Serie Vieja", "2020", True)}
            )

    group_key = title_to_key["k"]
    assert tmdb_cache[group_key]["media_type"] == "tv"


# ---------------------------------------------------------------------------
# 4) Mapeo de errores de Prowlarr
# ---------------------------------------------------------------------------
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_prowlarr_sin_conexion_devuelve_503(client):
    with patch(
        "routes.search.requests.get",
        side_effect=requests.exceptions.ConnectionError("sin conexion"),
    ):
        resp = client.get("/api/search?query=algo&min_size_gb=1")

    assert resp.status_code == 503
    assert "Prowlarr" in resp.get_json()["error"]


@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_prowlarr_respuesta_invalida_devuelve_500(client):
    with patch("routes.search.requests.get", side_effect=ValueError("no json")):
        resp = client.get("/api/search?query=algo&min_size_gb=1")

    assert resp.status_code == 500
    assert "JSON" in resp.get_json()["error"]
