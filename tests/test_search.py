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


@patch("routes.search.requests.get")
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
@patch("routes.search.get_tmdb_info")
def test_search_api_pagination(mock_get_tmdb, mock_get_prowlarr, client):
    # Cada título produce una obra distinta para poder paginar grupos
    def fake_tmdb(title, year=None, is_tv=False):
        return {
            "id": abs(hash(title)) % 100000,
            "title": title,
            "overview": "Overview",
            "poster_url": None,
            "year": year or "2023",
        }

    mock_get_tmdb.side_effect = fake_tmdb

    items = [
        {
            "title": f"Pelicula{i}.2023.1080p.WEBRip.x264",
            "size": 16106127360,  # 15 GB
            "seeders": i,
            "indexer": "TestTracker",
            "magnetUrl": f"magnet:?xt=urn:btih:{i}",
        }
        for i in range(20)
    ]

    mock_prowlarr_res = MagicMock()
    mock_prowlarr_res.status_code = 200
    mock_prowlarr_res.json.return_value = items
    mock_get_prowlarr.return_value = mock_prowlarr_res

    # Página 1: 5 grupos de 20
    r1 = client.get("/api/search?query=Test&min_size_gb=1&page=1&per_page=5")
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["page"] == 1
    assert d1["per_page"] == 5
    assert d1["total_groups"] == 20
    assert d1["total_torrents"] == 20
    assert len(d1["results"]) == 5
    assert d1["has_more"] is True

    # Página 4 (última completa): no hay más
    r4 = client.get("/api/search?query=Test&min_size_gb=1&page=4&per_page=5")
    d4 = r4.get_json()
    assert len(d4["results"]) == 5
    assert d4["has_more"] is False

    # Página 5 (fuera de rango): vacía
    r5 = client.get("/api/search?query=Test&min_size_gb=1&page=5&per_page=5")
    d5 = r5.get_json()
    assert d5["results"] == []
    assert d5["has_more"] is False

    # per_page se acota al máximo permitido (50)
    r_big = client.get("/api/search?query=Test&min_size_gb=1&page=1&per_page=999")
    assert r_big.get_json()["per_page"] == 50
