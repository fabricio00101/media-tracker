from unittest.mock import patch, MagicMock

@patch("routes.search.requests.get")
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
@patch("routes.search.get_tmdb_info")
def test_search_api_success(mock_get_tmdb, mock_get_prowlarr, client):
    # Mock TMDB
    mock_get_tmdb.return_value = {
        "id": 999,
        "title": "Un Título",
        "overview": "Overview",
        "poster_url": "http://img",
        "year": "2023"
    }

    # Mock Prowlarr
    mock_prowlarr_res = MagicMock()
    mock_prowlarr_res.status_code = 200
    mock_prowlarr_res.json.return_value = [
        {
            "title": "Un.Titulo.2023.1080p.WEBRip.x264",
            "size": 16106127360,  # 15 GB
            "seeders": 10,
            "indexer": "TestTracker",
            "magnetUrl": "magnet:?xt=urn:btih:123"
        }
    ]
    mock_get_prowlarr.return_value = mock_prowlarr_res

    response = client.get("/api/search?query=Test&min_size_gb=10")
    assert response.status_code == 200
    data = response.get_json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["group_info"]["title"] == "Un Título"
    assert len(data["results"][0]["torrents"]) == 1

@patch("routes.search.requests.get")
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_search_api_empty_query(mock_get_prowlarr, client):
    response = client.get("/api/search?query=")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
