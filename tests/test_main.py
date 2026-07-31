"""Basic tests for ContentForge API."""
from src.main import app

import pytest




# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

def test_root():
    assert app.title == "ContentForge"
