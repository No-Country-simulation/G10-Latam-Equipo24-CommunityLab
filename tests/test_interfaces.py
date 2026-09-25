"""Tests for domain interfaces (abstract checks)."""
import pytest
from src.domain.interfaces import (
    DataLoader,
    SentimentAnalyzer,
    Categorizer,
    RelevanceScorer,
    DecisionEngine,
    AssetGenerator,
    StorageClient,
)

def test_interfaces_are_abstract():
    # These ABCs cannot be instantiated directly
    with pytest.raises(TypeError):
        DataLoader()
    with pytest.raises(TypeError):
        SentimentAnalyzer()
    with pytest.raises(TypeError):
        Categorizer()
    with pytest.raises(TypeError):
        RelevanceScorer()
    with pytest.raises(TypeError):
        DecisionEngine()
    with pytest.raises(TypeError):
        AssetGenerator()
    with pytest.raises(TypeError):
        StorageClient()
