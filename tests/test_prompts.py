"""
Unit tests for central prompt templates and LLM client resilience.
"""

import pytest
import os
from src.prompts.templates import UNIFIED_ANALYSIS_PROMPT
from src.utils.llm import GeminiClient, LLMError


def test_unified_analysis_prompt_structure():
    """Verifies that the unified analysis prompt contains all required contract fields."""
    assert "sentiment" in UNIFIED_ANALYSIS_PROMPT
    assert "categorization" in UNIFIED_ANALYSIS_PROMPT
    assert "relevance" in UNIFIED_ANALYSIS_PROMPT
    assert "duda_tecnica" in UNIFIED_ANALYSIS_PROMPT
    assert "testimonio" in UNIFIED_ANALYSIS_PROMPT


def test_gemini_client_rate_limit_handling():
    """Verifies that GeminiClient correctly wraps HTTP 429 / rate limit errors into LLMError."""
    client = GeminiClient()
    
    # We patch generativeai to raise a simulated rate limit exception
    class MockException(Exception):
        pass

    import unittest.mock as mock
    with mock.patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_instance = mock_model_cls.return_value
        mock_instance.generate_content.side_effect = Exception("429 Too Many Requests: ResourceExhausted quota exceeded")

        with pytest.raises(LLMError) as exc_info:
            client.generate("test prompt")
        
        assert "rate limit exceeded" in str(exc_info.value).lower()
