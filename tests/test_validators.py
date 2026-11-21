from utils.validators import validate_search_params, ValidationError


def test_validator_success():
    params = validate_search_params({
        "query": "Inception",
        "category": "movies",
        "min_size_gb": "5.5",
        "quality_tag": "1080p",
        "hdr": "true",
        "hevc": "false",
        "lang_filter": "latino,castellano",
        "page": "2",
        "per_page": "20",
    })
    assert params["query"] == "Inception"
    assert params["category"] == "movies"
    assert params["min_size_gb"] == 5.5
    assert params["quality_tag"] == "1080p"
    assert params["require_hdr"] is True
    assert params["require_hevc"] is False
    assert params["lang_filters"] == ["latino", "castellano"]
    assert params["page"] == 2
    assert params["per_page"] == 20


def test_validator_defaults():
    params = validate_search_params({"query": "Gladiator"})
    assert params["category"] == "all"
    # Default unificado con la UI (templates/index.html ya no tiene su propio 5)
    assert params["min_size_gb"] == 5.0
    assert params["quality_tag"] == ""
    assert params["require_hdr"] is False
    assert params["require_hevc"] is False
    assert params["lang_filters"] == ["all"]
    assert params["page"] == 1
    assert params["per_page"] == 16
