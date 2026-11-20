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


# ---------------------------------------------------------------------------
# Validaciones de parámetros (Etapa 1: Robustez)
# ---------------------------------------------------------------------------
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_search_param_validations(client):
    # Query excesivamente larga (>150)
    res = client.get(f"/api/search?query={'a' * 151}")
    assert res.status_code == 400
    assert "superar los 150 caracteres" in res.get_json()["error"]

    # Categoría inválida
    res = client.get("/api/search?query=avatar&category=invalid_cat")
    assert res.status_code == 400
    assert "Categoría inválida" in res.get_json()["error"]

    # Filtro de idioma inválido
    res = client.get("/api/search?query=avatar&lang_filter=klingon")
    assert res.status_code == 400
    assert "Filtro de idioma inválido" in res.get_json()["error"]

    # min_size_gb con NaN, Inf, negativo o mayor a 2000
    for bad_size in ["nan", "inf", "-inf", "-5", "2500", "no_number"]:
        res = client.get(f"/api/search?query=avatar&min_size_gb={bad_size}")
        assert res.status_code == 400
        assert "min_size_gb" in res.get_json()["error"] or "número finito" in res.get_json()["error"]

    # Calidad excesivamente larga
    res = client.get(f"/api/search?query=avatar&quality_tag={'q' * 35}")
    assert res.status_code == 400
    assert "filtro de calidad no puede superar" in res.get_json()["error"]


# ---------------------------------------------------------------------------
# Tolerancia a respuestas de Prowlarr
# ---------------------------------------------------------------------------
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_prowlarr_responses_robustness(client):
    # Prowlarr devuelve dict con Results
    res_obj = MagicMock()
    res_obj.status_code = 200
    res_obj.json.return_value = {
        "Results": [
            {"title": "Peli.Valida.2023.1080p", "size": 1024**3 * 5, "seeders": 10, "indexer": "Tracker1", "magnetUrl": "magnet:1"},
            None,  # Elemento no dict
            {"size": 1024**3 * 5},  # Elemento sin título
        ]
    }
    with patch("routes.search.requests.get", return_value=res_obj), \
         patch("routes.search.get_tmdb_info", return_value=None):
        r = client.get("/api/search?query=peli&min_size_gb=1")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total_torrents"] == 1

    # Prowlarr devuelve tipo no soportado (ej: string o int)
    res_bad = MagicMock()
    res_bad.status_code = 200
    res_bad.json.return_value = "Respuesta no esperada"
    with patch("routes.search.requests.get", return_value=res_bad):
        r = client.get("/api/search?query=otra_peli_diferente&min_size_gb=1")
        assert r.status_code == 502
        assert "Estructura de respuesta inesperada" in r.get_json()["error"]


# ---------------------------------------------------------------------------
# Detección de idiomas y audio (Etapa 2: Word boundaries y sin falsos positivos)
# ---------------------------------------------------------------------------
def test_detect_spanish_word_boundaries():
    from routes.search import _detect_spanish

    # Falsos positivos que antes podían coincidir con "lat"
    assert _detect_spanish("blade.runner.final.cut.1080p") is None
    assert _detect_spanish("plateau.2022.bluray") is None
    assert _detect_spanish("relativity.1080p") is None

    # Coincidencias legítimas
    assert _detect_spanish("matrix.1999.latino.1080p") == "Latino"
    assert _detect_spanish("matrix.1999.lat.1080p") == "Latino"
    assert _detect_spanish("matrix.1999.[arg].1080p") == "Latino"
    assert _detect_spanish("matrix.1999.castellano.1080p") == "Castellano"
    assert _detect_spanish("matrix.1999.es-es.1080p") == "Castellano"
    assert _detect_spanish("matrix.1999.vose.1080p") == "Subtitulado"
    assert _detect_spanish("matrix.1999.subtitulado.1080p") == "Subtitulado"


def test_detect_audio_patterns():
    from routes.search import _detect_audio

    assert _detect_audio("movie.2023.truehd.atmos.mkv") == "Dolby Atmos / TrueHD"
    assert _detect_audio("movie.2023.dts-hd.ma.mkv") == "DTS-HD / X"
    assert _detect_audio("movie.2023.eac3.mkv") == "Dolby Digital Plus"
    assert _detect_audio("movie.2023.dd5.1.mkv") == "Dolby Digital"
    assert _detect_audio("movie.2023.aac2.0.mkv") == "AAC"
    assert _detect_audio("movie.2023.flac.mkv") is None
@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_grouping_separates_movie_and_tv(client):
    items = [
        # Película
        {"title": "The.Flash.2023.1080p.WEBRip", "size": 1024**3 * 10, "seeders": 50, "indexer": "T1", "magnetUrl": "magnet:m"},
        # Serie homónima
        {"title": "The.Flash.2023.S01E01.1080p.WEBRip", "size": 1024**3 * 2, "seeders": 40, "indexer": "T2", "magnetUrl": "magnet:s"},
    ]
    res_mock = MagicMock()
    res_mock.status_code = 200
    res_mock.json.return_value = items

    # TMDB resuelve cada uno con su respectivo media_type
    def mock_tmdb(title, year=None, is_tv=False):
        return {
            "id": 100 if not is_tv else 200,
            "title": "The Flash",
            "overview": "Overview",
            "poster_url": None,
            "year": "2023",
            "media_type": "tv" if is_tv else "movie",
        }

    with patch("routes.search.requests.get", return_value=res_mock), \
         patch("routes.search.get_tmdb_info", side_effect=mock_tmdb):
        r = client.get("/api/search?query=The+Flash&min_size_gb=1")
        assert r.status_code == 200
        groups = r.get_json()["results"]
        assert len(groups) == 2
        media_types = {g["group_info"]["media_type"] for g in groups}
        assert media_types == {"movie", "tv"}


# ---------------------------------------------------------------------------
# Estimación técnica (bpp) y filtros derivados
# ---------------------------------------------------------------------------
def _mock_tmdb_con_runtime(title, year=None, is_tv=False):
    return {
        "id": abs(hash(title)) % 100000,
        "title": title,
        "overview": "Overview",
        "poster_url": None,
        "year": year or "2023",
        "media_type": "tv" if is_tv else "movie",
        "runtime": 100,
    }


def _mock_prowlarr_items(items):
    res = MagicMock()
    res.status_code = 200
    res.json.return_value = items
    return res


@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_search_incluye_estimacion_tecnica(client):
    items = [
        {
            "title": "Peli.2023.1080p.WEB-DL.HEVC.x265.10bit.DDP5.1-GRP",
            "size": 4 * 1024**3,
            "seeders": 5,
            "indexer": "T1",
            "magnetUrl": "magnet:x",
        }
    ]
    with patch("routes.search.requests.get", return_value=_mock_prowlarr_items(items)), \
         patch("routes.search.get_tmdb_info", side_effect=_mock_tmdb_con_runtime):
        r = client.get("/api/search?query=Peli&min_size_gb=1")
        assert r.status_code == 200

    tech = r.get_json()["results"][0]["torrents"][0]["tech"]
    assert tech["source"] == "WEB-DL"
    assert tech["video_codec"] == "HEVC"
    assert tech["bit_depth"] == 10
    assert tech["audio"] == "DD+ 5.1"
    assert tech["mbps"] == 5.73
    assert tech["bpp"] == 0.115
    assert tech["tier"] == "muy_bueno"
    assert tech["tier_label"] == "Muy buena"
    assert tech["estimated"] is True


@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_min_bpp_filtra_torrents_de_baja_calidad(client):
    items = [
        {
            "title": "Peli.2023.1080p.WEB-DL.x265",
            "size": 1 * 1024**3,  # ~0,029 bpp
            "seeders": 50,
            "indexer": "T1",
            "magnetUrl": "magnet:baja",
        },
        {
            "title": "Peli.2023.1080p.WEB-DL.x265.10bit",
            "size": 8 * 1024**3,  # ~0,23 bpp
            "seeders": 1,
            "indexer": "T2",
            "magnetUrl": "magnet:alta",
        },
    ]
    with patch("routes.search.requests.get", return_value=_mock_prowlarr_items(items)), \
         patch("routes.search.get_tmdb_info", side_effect=_mock_tmdb_con_runtime):
        r = client.get("/api/search?query=Peli&min_size_gb=0.5&min_bpp=0.07")
        assert r.status_code == 200

    torrents = r.get_json()["results"][0]["torrents"]
    assert len(torrents) == 1
    assert torrents[0]["magnet"] == "magnet:alta"


@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_sdr_only_descarta_hdr(client):
    items = [
        {
            "title": "Peli.2023.1080p.WEB-DL.x265.HDR10",
            "size": 5 * 1024**3,
            "seeders": 10,
            "indexer": "T1",
            "magnetUrl": "magnet:hdr",
        },
        {
            "title": "Peli.2023.1080p.WEB-DL.x265",
            "size": 5 * 1024**3,
            "seeders": 5,
            "indexer": "T2",
            "magnetUrl": "magnet:sdr",
        },
    ]
    with patch("routes.search.requests.get", return_value=_mock_prowlarr_items(items)), \
         patch("routes.search.get_tmdb_info", side_effect=_mock_tmdb_con_runtime):
        r = client.get("/api/search?query=Peli&min_size_gb=1&sdr_only=true")
        assert r.status_code == 200

    torrents = r.get_json()["results"][0]["torrents"]
    assert len(torrents) == 1
    assert torrents[0]["magnet"] == "magnet:sdr"


@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_orden_por_bpp(client):
    items = [
        {
            "title": "Peli.Floja.2023.1080p.WEB-DL.x265",
            "size": 1 * 1024**3,
            "seeders": 99,
            "indexer": "T1",
            "magnetUrl": "magnet:floja",
        },
        {
            "title": "Peli.Buena.2023.1080p.WEB-DL.x265",
            "size": 8 * 1024**3,
            "seeders": 1,
            "indexer": "T2",
            "magnetUrl": "magnet:buena",
        },
    ]
    with patch("routes.search.requests.get", return_value=_mock_prowlarr_items(items)), \
         patch("routes.search.get_tmdb_info", side_effect=_mock_tmdb_con_runtime):
        por_seeders = client.get("/api/search?query=Peli&min_size_gb=0.5&sort=seeders_desc")
        por_bpp = client.get("/api/search?query=Peli&min_size_gb=0.5&sort=bpp_desc")

    titulos_seeders = [g["group_info"]["title"] for g in por_seeders.get_json()["results"]]
    titulos_bpp = [g["group_info"]["title"] for g in por_bpp.get_json()["results"]]
    assert titulos_seeders[0] == "Peli Floja"
    assert titulos_bpp[0] == "Peli Buena"


@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_orden_por_bpp_dentro_del_grupo(client):
    items = [
        {
            "title": "Peli.2023.1080p.WEB-DL.x265",
            "size": 1 * 1024**3,
            "seeders": 50,
            "indexer": "T1",
            "magnetUrl": "magnet:baja",
        },
        {
            "title": "Peli.2023.1080p.WEB-DL.x265.10bit",
            "size": 8 * 1024**3,
            "seeders": 1,
            "indexer": "T2",
            "magnetUrl": "magnet:alta",
        },
    ]
    with patch("routes.search.requests.get", return_value=_mock_prowlarr_items(items)), \
         patch("routes.search.get_tmdb_info", side_effect=_mock_tmdb_con_runtime):
        r = client.get("/api/search?query=Peli&min_size_gb=0.5&sort=bpp_desc")
        assert r.status_code == 200

    torrents = r.get_json()["results"][0]["torrents"]
    assert torrents[0]["magnet"] == "magnet:alta"


@patch("routes.search.config.PROWLARR_API_KEY", "mock_key")
def test_validacion_min_bpp_y_sort(client):
    res = client.get("/api/search?query=peli&min_bpp=5")
    assert res.status_code == 400
    assert "min_bpp" in res.get_json()["error"]

    res = client.get("/api/search?query=peli&min_bpp=abc")
    assert res.status_code == 400
    assert "min_bpp" in res.get_json()["error"]

    res = client.get("/api/search?query=peli&sort=inventado")
    assert res.status_code == 400
    assert "orden inválido" in res.get_json()["error"]
