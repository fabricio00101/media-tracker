"""Tests del servicio de subtítulos: get_opensubtitles_token().

Este módulo se testea por separado de las rutas porque su lógica de caché y
reautenticación nunca se ejecuta completa desde /api/subtitles/*.
"""

from unittest.mock import patch, MagicMock

import services.subtitles as subs_mod


# ---------------------------------------------------------------------------
# Helpers de credenciales (monkeypatch evita el orden ambiguo de @patch)
# ---------------------------------------------------------------------------

def _configurar_credenciales(monkeypatch):
    monkeypatch.setattr(subs_mod.config, "OPENSUBTITLES_API_KEY", "key")
    monkeypatch.setattr(subs_mod.config, "OPENSUBTITLES_USER", "user")
    monkeypatch.setattr(subs_mod.config, "OPENSUBTITLES_PASSWORD", "pass")


def _configurar_sin_credenciales(monkeypatch):
    monkeypatch.setattr(subs_mod.config, "OPENSUBTITLES_API_KEY", "")
    monkeypatch.setattr(subs_mod.config, "OPENSUBTITLES_USER", "")
    monkeypatch.setattr(subs_mod.config, "OPENSUBTITLES_PASSWORD", "")


def _respuesta_json(payload):
    """MagicMock que imita requests.Response.json()."""
    res = MagicMock()
    res.status_code = 200
    res.json.return_value = payload
    res.raise_for_status.return_value = None
    return res


# ---------------------------------------------------------------------------
# get_opensubtitles_token
# ---------------------------------------------------------------------------

def test_get_opensubtitles_token_cache_hit(monkeypatch):
    """Token válido en caché se devuelve sin tocar la red."""
    _configurar_credenciales(monkeypatch)
    with patch("services.subtitles.cache") as mock_cache, \
         patch("services.subtitles.time.time", return_value=1000):
        mock_cache.get.return_value = ("tok_cache", 999)  # hace 1 s, no expiró

        token = subs_mod.get_opensubtitles_token()

    assert token == "tok_cache"
    mock_cache.get.assert_called_once_with("opensubtitles_token_data")
    mock_cache.set.assert_not_called()


def test_get_opensubtitles_token_sin_credenciales(monkeypatch):
    """Sin credenciales, retorna None sin intentar login."""
    _configurar_sin_credenciales(monkeypatch)
    with patch("services.subtitles.cache") as mock_cache, \
         patch("services.subtitles.requests.post") as mock_post:
        mock_cache.get.return_value = None

        token = subs_mod.get_opensubtitles_token()

    assert token is None
    mock_post.assert_not_called()


def test_get_opensubtitles_token_login_exitoso(monkeypatch):
    """Login 200 con token: guarda en caché y devuelve el token."""
    _configurar_credenciales(monkeypatch)
    with patch("services.subtitles.cache") as mock_cache, \
         patch("services.subtitles.requests.post") as mock_post, \
         patch("services.subtitles.time.time", return_value=1000):
        mock_cache.get.return_value = None
        mock_post.return_value = _respuesta_json({"token": "abc123"})

        token = subs_mod.get_opensubtitles_token()

    assert token == "abc123"
    mock_cache.set.assert_called_once()
    clave, valor = mock_cache.set.call_args[0][:2]
    assert clave == "opensubtitles_token_data"
    assert valor[0] == "abc123"


def test_get_opensubtitles_token_login_sin_token(monkeypatch):
    """Login 200 pero sin 'token' en respuesta → None y no guarda en caché."""
    _configurar_credenciales(monkeypatch)
    with patch("services.subtitles.cache") as mock_cache, \
         patch("services.subtitles.requests.post") as mock_post, \
         patch("services.subtitles.time.time", return_value=1000):
        mock_cache.get.return_value = None
        mock_post.return_value = _respuesta_json({})

        token = subs_mod.get_opensubtitles_token()

    assert token is None
    mock_cache.set.assert_not_called()


def test_get_opensubtitles_token_login_excepcion(monkeypatch):
    """Excepción en el login → None y no guarda en caché."""
    _configurar_credenciales(monkeypatch)
    with patch("services.subtitles.cache") as mock_cache, \
         patch("services.subtitles.requests.post") as mock_post, \
         patch("services.subtitles.time.time", return_value=1000):
        mock_cache.get.return_value = None
        mock_post.side_effect = Exception("red caída")

        token = subs_mod.get_opensubtitles_token()

    assert token is None
    mock_cache.set.assert_not_called()
