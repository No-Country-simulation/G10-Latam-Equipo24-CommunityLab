"""Tests for domain models."""
import pytest
from src.domain.models import (
    InputMessage,
    SentimentResult,
    SentimentType,
    CategorizationResult,
    RelevanceResult,
    RelevanceResult,
    AnalysisComplete,
    OutputBatch,
    AssetType,
    RiskLevel,
    ActionType,
)

def test_input_message_valid():
    data = {
        "id": "msg-001",
        "content": "Hola, estoy contento.",
        "author": "user-01",
        "channel": "#general",
        "timestamp": "2026-09-15T14:30:00Z",
        "metadata": {"reactions": 2},
    }
    msg = InputMessage(**data)
    assert msg.id == "msg-001"
    assert msg.content == "Hola, estoy contento."
    assert isinstance(msg, InputMessage)

def test_input_message_serialization_roundtrip():
    msg = InputMessage(
        id="msg-002",
        content="Contenido de prueba",
        author="author-02",
        channel="#test",
        timestamp="2026-01-01T00:00:00Z",
        metadata={},
    )
    data = msg.model_dump()
    reconstructed = InputMessage(**data)
    assert msg.id == reconstructed.id
    assert msg.content == reconstructed.content

def test_sentiment_result():
    result = SentimentResult(
        message_id="msg-003",
        sentiment=SentimentType.POSITIVO,
        score=0.95,
        reasoning="Test",
    )
    assert result.message_id == "msg-003"
    assert result.sentiment == SentimentType.POSITIVO

def test_output_batch():
    batch = OutputBatch(
        batch_id="batch-001",
        processed_at="2026-09-21T10:00:00Z",
        summary={"total_messages": 1},
        analysis=[],
        decisions=[],
        assets=[],
        oci_storage={},
        alerts=[],
        visualization={},
    )
    assert batch.batch_id == "batch-001"
