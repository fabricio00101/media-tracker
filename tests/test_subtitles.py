from unittest.mock import patch, MagicMock

@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_success(mock_get, client):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "data": [{"id": "sub123", "attributes": {"language": "es"}}]
    }
    mock_get.return_value = mock_res

    response = client.get("/api/subtitles/search?tmdb_id=123")
    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert len(data["data"]) == 1

@patch("routes.subtitles.requests.post")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
@patch("routes.subtitles.get_opensubtitles_token")
def test_download_subtitle_success(mock_get_token, mock_post, client):
    mock_get_token.return_value = "mock_token"

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"link": "http://download-link"}
    mock_post.return_value = mock_res

    response = client.get("/api/subtitles/download?file_id=456")
    assert response.status_code == 200
    data = response.get_json()
    assert data["link"] == "http://download-link"


def test_search_subtitles_sin_tmdb_id(client):
    response = client.get("/api/subtitles/search")
    assert response.status_code == 400
    assert "error" in response.get_json()


@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "")
def test_search_subtitles_sin_api_key(client):
    response = client.get("/api/subtitles/search?tmdb_id=123")
    assert response.status_code == 401
    assert "OpenSubtitles" in response.get_json()["error"]


def test_download_subtitle_sin_file_id(client):
    response = client.get("/api/subtitles/download")
    assert response.status_code == 400
    assert "error" in response.get_json()


@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
@patch("routes.subtitles.get_opensubtitles_token", return_value=None)
def test_download_subtitle_sin_token_devuelve_401(mock_token, client):
    response = client.get("/api/subtitles/download?file_id=456")
    assert response.status_code == 401
    assert ".env" in response.get_json()["error"]
