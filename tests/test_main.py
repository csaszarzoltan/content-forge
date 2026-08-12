"""Basic tests for ContentForge API."""
import pytest

from src.main import app

# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

def test_root():
    assert app.title == "ContentForge"
