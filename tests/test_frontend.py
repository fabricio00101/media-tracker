"""Tests de regresión del frontend: XSS, delegación de eventos y sintaxis."""

import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "js" / "app.js"
NODE = shutil.which("node")


@pytest.fixture(scope="module")
def app_js():
    return APP_JS.read_text(encoding="utf-8")


def test_sin_handlers_inline(app_js):
    """Regresión del fix de XSS: los atributos de evento inline no deben volver.

    Escapar con entidades HTML no basta dentro de un onclick: el parser
    decodifica antes de que JavaScript vea el código.
    """
    for prohibido in ("onclick=", "onerror=", "onload=", "onmouseover="):
        assert prohibido not in app_js, f"'{prohibido}' volvió a app.js"


def test_escape_html_esta_presente(app_js):
    assert "const escapeHtml" in app_js
    for entidad in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
        assert entidad in app_js, f"falta la entidad {entidad}"


def test_usa_delegacion_de_eventos(app_js):
    """Las acciones dependientes de datos externos usan data-* + closest()."""
    assert "data-fav-info" in app_js
    assert "data-sub-id" in app_js
    assert ".closest(" in app_js


@pytest.mark.skipif(NODE is None, reason="node no está instalado")
def test_sintaxis_javascript():
    res = subprocess.run(
        [NODE, "--check", str(APP_JS)], capture_output=True, text=True, timeout=60
    )
    assert res.returncode == 0, res.stderr


@pytest.mark.skipif(NODE is None, reason="node no está instalado")
def test_escape_html_neutraliza_xss():
    """Ejecuta escapeHtml() real contra payloads de ejemplo."""
    res = subprocess.run(
        [NODE, str(ROOT / "tests" / "frontend_escape_check.js")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stdout + res.stderr
