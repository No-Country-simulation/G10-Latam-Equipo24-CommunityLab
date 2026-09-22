"""Tests for input normalizer."""
import pytest
from src.ingest.normalizer import InputNormalizer
from src.domain.models import InputMessage

def test_normalize_discord_message():
    raw = {
        "author": "alice",
        "content": "Excelente sesión",
        "timestamp": "2026-09-15T14:30:00Z",
        "reactions": 3,
    }
    normalizer = InputNormalizer()
    msg = normalizer.normalize("discord", raw)
    assert isinstance(msg, InputMessage)
    assert msg.author == "alice"
    assert msg.content == "Excelente sesión"
    assert msg.channel == "#discord"
    assert msg.metadata.get("reactions") == 3
    # ID should be non-empty
    assert msg.id
