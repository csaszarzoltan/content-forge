"""Basic tests for ContentForge API."""
from src.main import app

def test_root():
    assert app.title == "ContentForge"
