import pytest
import sys
import os

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app
from extensions import cache

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

@pytest.fixture
def client(app):
    return app.test_client()
