"""Tests for JSON input loader."""
import pytest
import tempfile
import json
from pathlib import Path
from src.ingest.input_loader import JSONInputLoader
from src.domain.models import InputMessage

def test_load_valid_json(tmp_path):
    sample = {
        "batch_id": "batch-001",
        "source": "discord",
        "channel": "#general",
        "processed_at": "2026-09-21T10:00:00Z",
        "interactions": [
            {
                "id": "msg-001",
                "content": "¡Gran curso!",
                "author": "estudiante-01",
                "channel": "#testimonios",
                "timestamp": "2026-09-15T14:30:00Z",
                "metadata": {"reactions": 5},
            }
        ],
    }
    file = tmp_path / "sample.json"
    file.write_text(json.dumps(sample))
    loader = JSONInputLoader()
    msgs = loader.load(str(file))
    assert len(msgs) == 1
    assert msgs[0].author == "estudiante-01"
    assert isinstance(msgs[0], InputMessage)

def test_load_missing_file():
    loader = JSONInputLoader()
    with pytest.raises(FileNotFoundError):
        loader.load("/nonexistent/path.json")

def test_load_invalid_json(tmp_path):
    invalid = {"batch_id": "bad"}
    file = tmp_path / "bad.json"
    file.write_text(json.dumps(invalid))
    loader = JSONInputLoader()
    with pytest.raises(ValueError):
        loader.load(str(file))
