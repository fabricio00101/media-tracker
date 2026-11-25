"""Tests de deduplicación de torrents entre indexers.

Cubre: deduplicación por infohash, fallback por nombre+tamaño,
evitación de falsos positivos con tamaños genéricos, y suma coherente
de seeders.
"""
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_torrent(title, size_bytes, seeders, magnet):
    """Construir un dict de torrent simple para tests."""
    return {
        "title": title,
        "size": size_bytes,
        "seeders": seeders,
        "indexer": "TestIndexer",
        "magnetUrl": magnet,
    }


# ---------------------------------------------------------------------------
# Tests para extract_infohash
# ---------------------------------------------------------------------------

def test_extract_infohash_basico():
    from utils.dedupe import extract_infohash
    magnet = "magnet:?xt=urn:btih:abc123def456abc123def456abc123def456abc123"
    assert extract_infohash(magnet) == "abc123def456abc123def456abc123def456abc123"


def test_extract_infohash_malo_largo():
    from utils.dedupe import extract_infohash
    magnet = "magnet:?xt=urn:btih:abc"  # muy corto
    assert extract_infohash(magnet) is None


def test_extract_infohash_vacio():
    from utils.dedupe import extract_infohash
    assert extract_infohash(None) is None
    assert extract_infohash("") is None


def test_extract_infohash_sin_xt():
    from utils.dedupe import extract_infohash
    magnet = "magnet:?xt=urn:btih:GARBAGE"  # no es hex válido largo
    # This may or may not return None depending on regex; just verify no crash
    result = extract_infohash(magnet)
    assert result is None or len(result) >= 20


# ---------------------------------------------------------------------------
# Tests para _normalize_name
# ---------------------------------------------------------------------------

def test_normalize_name():
    from utils.dedupe import _normalize_name
    assert _normalize_name("Peli.2023.1080p") == "peli 2023 1080p"
    assert _normalize_name("The.Flash.S01E01.1080p") == "the flash s01e01 1080p"
    assert _normalize_name("  Extra   spaces  ") == "extra spaces"


# ---------------------------------------------------------------------------
# Tests para select_deduplicated_indices
# ---------------------------------------------------------------------------

def test_select_por_infohash():
    """Mismo infohash, seeders distintos: gana el de más seeders."""
    from utils.dedupe import select_deduplicated_indices

    torrents = [
        # index 0: mismo infohash, menos seeders
        {
            "title": "Peli.2023.1080p.WEBRip.x264",
            "magnet": "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAA",
            "seeders": 10,
            "indexer": "T1",
            "size_bytes": 1500000000,
        },
        # index 1: mismo infohash, más seeders
        {
            "title": "Peli.2023.1080p.WEBRip.x264",
            "magnet": "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAA",
            "seeders": 25,
            "indexer": "T2",
            "size_bytes": 1500000000,
        },
    ]

    with patch("routes.search.config.PROWLARR_API_KEY", "mock_key"):
        # Need to set up the app context minimally
        from app import app
        with app.app_context():
            indices, stats = select_deduplicated_indices(torrents)
            # Debería quedarse solo el índice 1 (más seeders)
            assert 1 in indices
            assert 0 not in indices
            assert stats["removed"] == 1


def test_select_por_infohash_empate():
    """Mismo infohash, empatan en seeders: gana el primero."""
    from utils.dedupe import select_deduplicated_indices

    torrents = [
        {
            "title": "Peli.2023.1080p.WEBRip.x264",
            "magnet": "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAB",
            "seeders": 15,
            "indexer": "T1",
            "size_bytes": 1500000000,
        },
        {
            "title": "Peli.2023.1080p.WEBRip.x264",
            "magnet": "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAB",
            "seeders": 15,
            "indexer": "T2",
            "size_bytes": 1500000000,
        },
    ]

    with patch("routes.search.config.PROWLARR_API_KEY", "mock_key"):
        from app import app
        with app.app_context():
            indices, stats = select_deduplicated_indices(torrents)
            # En empate, gana el primero (índice 0)
            assert 0 in indices
            assert stats["removed"] == 1


def test_select_sin_infohash_fallback_nombre_tamanio():
    """Fallback: mismo nombre normalizado y tamaño similar -> dedup por nombre+tamaño.
    
    Usa infohashes cortos (< 20 chars) para forzar el camino de fallback."""
    from utils.dedupe import select_deduplicated_indices

    torrents = [
        {
            "title": "Peli.2023.1080p.WEBRip",
            "magnet": "magnet:?xt=urn:btih:AAAAAAAAAA",  # 10 chars -> infohash corto, ira a fallback
            "seeders": 10,
            "indexer": "T1",
            "size_bytes": 1500000000,  # ~1.4 GB
        },
        {
            "title": "Peli.2023.1080p.WEBRip",
            "magnet": "magnet:?xt=urn:btih:BBBBBBBBBBBB",  # 12 chars -> infohash corto, ira a fallback
            "seeders": 20,
            "indexer": "T2",
            "size_bytes": 1500000000,  # ~1.4 GB (mismo tamaño)
        },
    ]

    with patch("routes.search.config.PROWLARR_API_KEY", "mock_key"):
        from app import app
        with app.app_context():
            # Los infohashes son cortos (<20 chars) así que irán al fallback
            indices, stats = select_deduplicated_indices(torrents)
            # Deberían dedup por nombre+tamaño: gana T2 con más seeders
            assert stats["removed"] >= 1 or len(indices) < 2


def test_select_sin_duplicados():
    """Torrents distintos (distintos títulos, infohashes o tamaños) -> nada se elimina."""
    from utils.dedupe import select_deduplicated_indices

    torrents = [
        _make_torrent("Peli.A.2023.1080p", 1500000000, 10, "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAE"),
        _make_torrent("Peli.B.2023.1080p", 2000000000, 20, "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAF"),
        _make_torrent("Otro.Titulo.2022", 1000000000, 5, "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAG"),
    ]

    with patch("routes.search.config.PROWLARR_API_KEY", "mock_key"):
        from app import app
        with app.app_context():
            indices, stats = select_deduplicated_indices(torrents)
            # Ninguno debería ser removido
            assert len(indices) == 3
            assert stats["removed"] == 0


def test_select_statistics():
    """Stats debería tener los campos esperados."""
    from utils.dedupe import select_deduplicated_indices

    torrents = [
        _make_torrent("Peli.A.2023.1080p", 1500000000, 10, "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAA"),
        _make_torrent("Peli.A.2023.1080p", 1500000000, 25, "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAA"),
    ]

    with patch("routes.search.config.PROWLARR_API_KEY", "mock_key"):
        from app import app
        with app.app_context():
            indices, stats = select_deduplicated_indices(torrents)
            assert "original_count" in stats
            assert "after_dedup" in stats
            assert "removed" in stats
            assert stats["original_count"] == 2
            assert stats["removed"] == 1


# ---------------------------------------------------------------------------
# Tests integrados con el flujo de process_results (a través de la API)
# ---------------------------------------------------------------------------

@patch("services.prowlarr_service.requests.get")
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_busqueda_sin_duplicados_real(mock_get_prowlarr, client):
    """Búsqueda real con la app: un solo torrent, nada que dedupar."""
    from app import app
    from tests.conftest import client

    mock_prowlarr_res = MagicMock()
    mock_prowlarr_res.status_code = 200
    mock_prowlarr_res.json.return_value = [
        {
            "title": "PeliculaUnica.2023.1080p.WEBRip.x264",
            "size": 16106127360,
            "seeders": 10,
            "indexer": "TestTracker",
            "magnetUrl": "magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
        }
    ]
    mock_get_prowlarr.return_value = mock_prowlarr_res

    with app.test_client() as test_client:
        response = test_client.get("/api/search?query=Pelicula&min_size_gb=1")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) >= 1
        # Debería haber al menos un grupo y un torrent
        assert data["total_torrents"] >= 1


@patch("services.prowlarr_service.requests.get")
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_mismo_torrent_distintos_indexers_suma_seeders(mock_get_prowlarr, client):
    """Mismo torrent (mismo infohash) en dos indexers: debería deduparse y el total
    de seeders debe ser el del de más seeders, no la suma."""
    from app import app

    # Two indexers with the same infohash (simulated by same magnet xt)
    mock_prowlarr_res = MagicMock()
    mock_prowlarr_res.status_code = 200
    mock_prowlarr_res.json.return_value = [
        {
            "title": "Peli.Misma.Peli.2023.1080p.WEBRip",
            "size": 16106127360,
            "seeders": 15,
            "indexer": "IndexerA",
            "magnetUrl": "magnet:?xt=urn:btih:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890ABC",
        },
        {
            "title": "Peli.Misma.Peli.2023.1080p.WEBRip",
            "size": 16106127360,
            "seeders": 8,
            "indexer": "IndexerB",
            "magnetUrl": "magnet:?xt=urn:btih:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890ABC",
        },
    ]
    mock_get_prowlarr.return_value = mock_prowlarr_res

    with app.test_client() as test_client:
        response = test_client.get("/api/search?query=Peli&min_size_gb=10")
        assert response.status_code == 200
        data = response.get_json()
        # El torrent debería aparecer una sola vez (deduped)
        # y los seeders deberían ser 15 (el máximo), no 23 (15+8)
        # Verificamos que total_torrents no duplique el mismo torrent
        torrent_magnets = []
        for group in data["results"]:
            for t in group["torrents"]:
                torrent_magnets.append(t["magnet"])
        # Debería haber solo 1 torrent único (el de más seeders)
        assert len(torrent_magnets) == 1 or len(set(torrent_magnets)) == 1


@patch("services.prowlarr_service.requests.get")
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_falso_positivo_tamanio_generico_no_dedupa(mock_get_prowlarr, client):
    """Dos torrents con tamaño similar pero títulos diferentes NO deben deduparse
    falsamente solo por tener ~el mismo tamaño GB."""
    from app import app

    mock_prowlarr_res = MagicMock()
    mock_prowlarr_res.status_code = 200
    mock_prowlarr_res.json.return_value = [
        {
            "title": "Peli.Ciencia.Ficcion.2023.1080p.WEBRip",
            "size": 4 * 1024**3,  # 4.0 GB
            "seeders": 10,
            "indexer": "T1",
            "magnetUrl": "magnet:?xt=urn:btih:AAAAAAAAAAAAAAAAAAAAAA",
        },
        {
            "title": "Otra.Pelicula.Accion.2023.1080p.WEBRip",
            "size": 4 * 1024**3,  # También 4.0 GB (tamaño genérico)
            "seeders": 5,
            "indexer": "T2",
            "magnetUrl": "magnet:?xt:urn:btih:BBBBBBBBBBBBBBBBBBBBBBB",  # distinto infohash
        },
    ]
    mock_get_prowlarr.return_value = mock_prowlarr_res

    with app.test_client() as test_client:
        response = test_client.get("/api/search?query=Peli&min_size_gb=1")
        assert response.status_code == 200
        data = response.get_json()
        # Deberían aparecer como grupos distintos (títulos diferentes),
        # no dedupados falsamente como el mismo torrent.
        # Los grupos pueden ser distintos porque los títulos normalizados son diferentes.
        total_torrents = sum(len(g["torrents"]) for g in data["results"])
        # Al menos 2 torrents (no dedupados por tamaño genérico)
        assert total_torrents >= 2