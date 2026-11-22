from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_test_generator.app import create_app
from ai_test_generator.providers import DemoProvider
from tests.server import live_server


@pytest.fixture
def client():
    with TestClient(create_app(DemoProvider())) as client:
        yield client


@pytest.fixture
def app_url():
    frontend = Path(__file__).parents[1] / "frontend" / "dist"
    if not (frontend / "index.html").is_file():
        pytest.fail("Build the React UI first: cd frontend && npm ci && npm run build")
    with live_server(create_app(DemoProvider(), frontend)) as url:
        yield url
