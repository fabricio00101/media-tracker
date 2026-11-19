import pytest
import sys
import os

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app
from extensions import cache, limiter

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "CACHE_TYPE": "NullCache",
    })
    with flask_app.app_context():
        cache.clear()
    yield flask_app

@pytest.fixture(autouse=True)
def clear_cache_before_test(app):
    with app.app_context():
        cache.clear()

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Los contadores de Flask-Limiter persisten durante toda la sesión de tests.

    Sin este fixture, un test que agota una cuota haría fallar a los siguientes.
    """
    limiter.reset()
    yield
    limiter.reset()

@pytest.fixture
def simple_cache_app(app):
    """Reemplaza NullCache por SimpleCache y lo restaura al terminar.

    Hace falta para probar comportamiento que depende de que la caché
    realmente guarde algo (p. ej. el lock anti cache-stampede).
    """
    app.config["CACHE_TYPE"] = "SimpleCache"
    cache.init_app(app)
    with app.app_context():
        cache.clear()

    yield app

    app.config["CACHE_TYPE"] = "NullCache"
    cache.init_app(app)
    with app.app_context():
        cache.clear()

@pytest.fixture
def client(app):
    return app.test_client()
