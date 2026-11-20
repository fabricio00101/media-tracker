from utils.media_meta import estimate_quality, parse_release_meta

GIB = 1024**3


# ---------------------------------------------------------------------------
# parse_release_meta: todo se deduce del nombre del release
# ---------------------------------------------------------------------------
def test_parse_release_completo():
    meta = parse_release_meta(
        "The.End.Of.Oak.Street.2026.1080p.WEB-DL.HEVC.x265.10Bit.DDP5.1-KINGDOM"
    )
    assert meta["source"] == "WEB-DL"
    assert meta["resolution"] == "1080p"
    assert meta["video_codec"] == "HEVC"
    assert meta["bit_depth"] == 10
    assert meta["hdr"] is None
    assert meta["audio"] == "DD+ 5.1"
    assert meta["group"] == "KINGDOM"
    assert meta["is_remux"] is False


def test_parse_release_remux_hdr():
    meta = parse_release_meta("Dune.2021.2160p.REMUX.HDR10.TrueHD.Atmos-GRUPO")
    assert meta["source"] == "REMUX"
    assert meta["resolution"] == "2160p"
    assert meta["hdr"] == "HDR10"
    assert meta["audio"] == "Atmos"
    assert meta["is_remux"] is True


def test_parse_release_sin_datos():
    meta = parse_release_meta("Pelicula.Desconocida")
    assert meta["source"] is None
    assert meta["resolution"] is None
    assert meta["video_codec"] is None
    assert meta["bit_depth"] is None
    assert meta["hdr"] is None


def test_parse_release_x264_bluray():
    meta = parse_release_meta("Movie.2010.1080p.BluRay.x264.AC3.5.1-GRP")
    assert meta["source"] == "BluRay"
    assert meta["video_codec"] == "H.264"
    assert meta["audio"] == "DD 5.1"


# ---------------------------------------------------------------------------
# estimate_quality
# ---------------------------------------------------------------------------
def test_estimacion_hevc_excelente():
    meta = parse_release_meta("Pelicula.2020.1080p.WEB-DL.x265.10bit")
    est = estimate_quality(8 * GIB, 100, meta)
    # 8 GiB en 100 min ≈ 11,45 Mbps sobre 1080p@24 ≈ 0,23 bpp
    assert est["tier"] == "excelente"
    assert est["mbps"] == 11.45
    assert est["bpp"] > 0.12
    assert est["low_bitrate"] is False
    assert est["score"] == 100


def test_estimacion_hevc_justa():
    meta = parse_release_meta("Pelicula.2020.1080p.WEB-DL.x265")
    est = estimate_quality(1.5 * GIB, 100, meta)
    # 1,5 GiB en 100 min ≈ 2,15 Mbps ≈ 0,043 bpp
    assert est["tier"] == "correcto"
    assert est["score"] < 50


def test_estimacion_h264_umbral_mas_exigente():
    meta = parse_release_meta("Pelicula.2020.1080p.WEBRip.x264")
    est = estimate_quality(4 * GIB, 100, meta)
    # 0,115 bpp: excelente en HEVC, pero solo "muy buena" en H.264
    assert est["tier"] == "muy_bueno"


def test_estimacion_remux_siempre_maxima():
    meta = parse_release_meta("Pelicula.2020.1080p.REMUX.AVC")
    est = estimate_quality(30 * GIB, 100, meta)
    assert est["tier"] == "remux"
    assert est["score"] == 100


def test_estimacion_sin_runtime():
    meta = parse_release_meta("Pelicula.2020.1080p.WEB-DL.x265")
    est = estimate_quality(4 * GIB, None, meta)
    assert est["tier"] == "sin_datos"
    assert est["bpp"] is None
    assert est["mbps"] is None
    assert est["score"] == 0


def test_estimacion_sin_resolucion():
    meta = parse_release_meta("Pelicula.2020.WEB-DL.x265")
    est = estimate_quality(4 * GIB, 100, meta)
    assert est["tier"] == "sin_datos"
    assert est["bpp"] is None
    assert est["mbps"] == 5.73


def test_estimacion_bitrate_bajo_en_1080p():
    meta = parse_release_meta("Pelicula.2020.1080p.x265")
    est = estimate_quality(1 * GIB, 120, meta)
    assert est["mbps"] < 2.0
    assert est["low_bitrate"] is True


def test_estimacion_720p():
    meta = parse_release_meta("Pelicula.2020.720p.WEB-DL.x265")
    est = estimate_quality(2 * GIB, 100, meta)
    # 2,86 Mbps sobre 1280x720@24 ≈ 0,13 bpp
    assert est["tier"] == "excelente"
    assert 0.12 < est["bpp"] < 0.14
