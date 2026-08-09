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

@patch("services.tmdb.requests.get")
@patch("services.tmdb.config.TMDB_API_KEY", "mock_key")
def test_get_tmdb_info_failure(mock_get):
    # Simular una excepción
    mock_get.side_effect = Exception("Connection error")

    info = get_tmdb_info("Test Movie", year="2023", is_tv=False)
    assert info is None
