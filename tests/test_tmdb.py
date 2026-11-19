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
