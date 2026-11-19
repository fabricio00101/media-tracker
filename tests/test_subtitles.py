from unittest.mock import patch, MagicMock

import requests


def _http_error(status_code):
    """HTTPError con un `.response` mínimo, como el que lanza requests."""
    err = requests.exceptions.HTTPError(f"HTTP {status_code}")
    err.response = MagicMock(status_code=status_code)
    return err

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


# ---------------------------------------------------------------------------
# Parámetros de búsqueda: películas vs series
# ---------------------------------------------------------------------------
def test_build_subtitles_params_pelicula():
    from routes.subtitles import _build_subtitles_params

    assert _build_subtitles_params("123", "movie", "", "") == {
        "languages": "es",
        "type": "movie",
        "tmdb_id": 123,
    }


def test_build_subtitles_params_serie():
    from routes.subtitles import _build_subtitles_params

    assert _build_subtitles_params("1399", "tv", "2", "5") == {
        "languages": "es",
        "type": "episode",
        "parent_tmdb_id": 1399,
        "season_number": 2,
        "episode_number": 5,
    }


@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_pelicula_envia_tmdb_id(mock_get, client):
    mock_res = MagicMock()
    mock_res.json.return_value = {"data": []}
    mock_res.raise_for_status.return_value = None
    mock_get.return_value = mock_res

    response = client.get("/api/subtitles/search?tmdb_id=550&media_type=movie")

    assert response.status_code == 200
    params = mock_get.call_args.kwargs["params"]
    assert params["tmdb_id"] == 550
    assert params["type"] == "movie"
    assert "parent_tmdb_id" not in params


@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_serie_envia_episodio(mock_get, client):
    mock_res = MagicMock()
    mock_res.json.return_value = {"data": []}
    mock_res.raise_for_status.return_value = None
    mock_get.return_value = mock_res

    response = client.get(
        "/api/subtitles/search?tmdb_id=1399&media_type=tv&season=2&episode=5"
    )

    assert response.status_code == 200
    params = mock_get.call_args.kwargs["params"]
    assert params["parent_tmdb_id"] == 1399
    assert params["season_number"] == 2
    assert params["episode_number"] == 5
    assert params["type"] == "episode"
    assert "tmdb_id" not in params


def test_search_subtitles_tmdb_id_no_numerico(client):
    """Sin TMDB_API_KEY el frontend mandaba 'undefined': ahora es 400."""
    response = client.get("/api/subtitles/search?tmdb_id=undefined")

    assert response.status_code == 400
    assert "TMDB ID" in response.get_json()["error"]


@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_serie_sin_episodio(client):
    response = client.get("/api/subtitles/search?tmdb_id=1399&media_type=tv&season=2")

    assert response.status_code == 400
    assert "temporada" in response.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# Errores de OpenSubtitles
# ---------------------------------------------------------------------------
@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_api_key_invalida(mock_get, client):
    mock_get.side_effect = _http_error(401)

    response = client.get("/api/subtitles/search?tmdb_id=550")

    assert response.status_code == 401
    assert "inválida" in response.get_json()["error"]


@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_limite_excedido(mock_get, client):
    mock_get.side_effect = _http_error(429)

    response = client.get("/api/subtitles/search?tmdb_id=550")

    assert response.status_code == 429
    assert "Límite" in response.get_json()["error"]


@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_error_generico(mock_get, client):
    mock_get.side_effect = Exception("boom")

    response = client.get("/api/subtitles/search?tmdb_id=550")

    assert response.status_code == 500
    assert "interno" in response.get_json()["error"]


@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_http_error_inesperado(mock_get, client):
    mock_get.side_effect = _http_error(500)

    response = client.get("/api/subtitles/search?tmdb_id=550")

    assert response.status_code == 500
    assert "OpenSubtitles" in response.get_json()["error"]


@patch("routes.subtitles.requests.get")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_search_subtitles_media_type_desconocido(mock_get, client):
    """Un media_type raro cae en movie en vez de romper."""
    mock_res = MagicMock()
    mock_res.json.return_value = {"data": []}
    mock_res.raise_for_status.return_value = None
    mock_get.return_value = mock_res

    response = client.get("/api/subtitles/search?tmdb_id=550&media_type=otro")

    assert response.status_code == 200
    assert mock_get.call_args.kwargs["params"]["type"] == "movie"


@patch("routes.subtitles.requests.post")
@patch("routes.subtitles.get_opensubtitles_token", return_value="tok")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_download_subtitle_sin_link(mock_token, mock_post, client):
    mock_res = MagicMock()
    mock_res.json.return_value = {}
    mock_res.raise_for_status.return_value = None
    mock_post.return_value = mock_res

    response = client.get("/api/subtitles/download?file_id=456")

    assert response.status_code == 502
    assert "enlace" in response.get_json()["error"]


@patch("routes.subtitles.requests.post")
@patch("routes.subtitles.get_opensubtitles_token", return_value="tok")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_download_subtitle_limite_de_descargas(mock_token, mock_post, client):
    mock_post.side_effect = _http_error(406)

    response = client.get("/api/subtitles/download?file_id=456")

    assert response.status_code == 406
    assert "Límite" in response.get_json()["error"]


@patch("routes.subtitles.requests.post")
@patch("routes.subtitles.get_opensubtitles_token", return_value="tok")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_download_subtitle_error_generico(mock_token, mock_post, client):
    mock_post.side_effect = Exception("boom")

    response = client.get("/api/subtitles/download?file_id=456")

    assert response.status_code == 500
    assert "interno" in response.get_json()["error"]


@patch("routes.subtitles.requests.post")
@patch("routes.subtitles.get_opensubtitles_token", return_value="tok")
@patch("routes.subtitles.config.OPENSUBTITLES_API_KEY", "mock_key")
def test_download_subtitle_http_error_inesperado(mock_token, mock_post, client):
    mock_post.side_effect = _http_error(500)

    response = client.get("/api/subtitles/download?file_id=456")

    assert response.status_code == 500
    assert "Error al descargar" in response.get_json()["error"]
