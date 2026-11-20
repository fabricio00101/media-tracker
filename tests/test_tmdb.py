from unittest.mock import patch, MagicMock
from services.tmdb import get_tmdb_info

@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "mock_key")
def test_get_tmdb_info_success(mock_get):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "results": [
            {
                "id": 123,
                "title": "Test Movie",
                "overview": "Test Overview",
                "poster_path": "/test.jpg",
                "release_date": "2023-01-01"
            }
        ]
    }
    mock_get.return_value = mock_res

    info = get_tmdb_info("Test Movie", year="2023", is_tv=False)
    assert info is not None
    assert info["id"] == 123
    assert info["title"] == "Test Movie"
    assert info["poster_url"] == "https://image.tmdb.org/t/p/w500/test.jpg"
    assert info["year"] == "2023"
    assert info["media_type"] == "movie"


@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "mock_key")
def test_get_tmdb_info_serie_devuelve_media_type_tv(mock_get):
    """Las series se marcan como tv: OpenSubtitles las busca distinto."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "results": [
            {
                "id": 1399,
                "name": "Serie de Prueba",
                "overview": "Sinopsis",
                "poster_path": None,
                "first_air_date": "2011-04-17",
            }
        ]
    }
    mock_get.return_value = mock_res

    info = get_tmdb_info("Serie de Prueba", year="2011", is_tv=True)

    assert info["media_type"] == "tv"
    assert info["title"] == "Serie de Prueba"
    assert info["year"] == "2011"

@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "mock_key")
def test_get_tmdb_info_failure(mock_get):
    # Simular una excepción
    mock_get.side_effect = Exception("Connection error")

    info = get_tmdb_info("Test Movie", year="2023", is_tv=False)
    assert info is None


# ---------------------------------------------------------------------------
# Tests de Scoring, Selección de Candidatos y Concurrencia (Etapa 2)
# ---------------------------------------------------------------------------
@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "mock_key")
def test_get_tmdb_info_remake_selecciona_por_ano(mock_get):
    """En caso de remakes con mismo título, debe elegir la versión que coincida con el año."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "results": [
            {
                "id": 1,
                "title": "Dune",
                "release_date": "1984-12-14",
                "vote_count": 500,
            },
            {
                "id": 2,
                "title": "Dune",
                "release_date": "2021-09-15",
                "vote_count": 8000,
            },
        ]
    }
    mock_get.return_value = mock_res

    # Buscamos la versión 2021
    info = get_tmdb_info("Dune", year="2021", is_tv=False)
    assert info is not None
    assert info["id"] == 2
    assert info["year"] == "2021"


@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "mock_key")
def test_get_tmdb_info_descarta_candidatos_irrelevantes(mock_get):
    """Si los resultados devueltos no tienen relación con la búsqueda, no debe forzar el primero."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "results": [
            {
                "id": 99,
                "title": "Completamente Otra Película",
                "release_date": "1990-01-01",
                "vote_count": 1,
            }
        ]
    }
    mock_get.return_value = mock_res

    info = get_tmdb_info("Matrix", year="1999", is_tv=False)
    assert info is None


@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "mock_key")
def test_get_tmdb_info_reintento_429(mock_get):
    """Si TMDB responde 429, debe reintentar y resolver exitosamente."""
    res_429 = MagicMock()
    res_429.status_code = 429

    res_200 = MagicMock()
    res_200.status_code = 200
    res_200.json.return_value = {
        "results": [
            {"id": 10, "title": "Avatar", "release_date": "2009-12-18", "vote_count": 5000}
        ]
    }
    mock_get.side_effect = [res_429, res_200]

    with patch("services.tmdb.time.sleep", return_value=None), patch(
        "services.tmdb._fetch_runtime", return_value=None
    ):
        info = get_tmdb_info("Avatar", year="2009", is_tv=False)
        assert info is not None
        assert info["id"] == 10
        assert mock_get.call_count == 2
