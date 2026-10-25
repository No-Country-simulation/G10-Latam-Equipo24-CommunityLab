"""Tests for the runtime LLM backend selection helpers."""

import os

from src.ingest.runtime import (
    LLM_BACKEND_ORDER,
    apply_backend,
    available_backends,
    resolve_backend,
)


def test_available_backends_disables_missing_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert available_backends() == {
        "ollama": True,
        "gemini": False,
        "openai": False,
        "rule_based": True,
    }


def test_available_backends_enables_gemini_with_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert available_backends()["gemini"] is True
    assert available_backends()["openai"] is False


def test_available_backends_enables_openai_with_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    assert available_backends()["openai"] is True
    assert available_backends()["gemini"] is False


def test_llm_backend_order_covers_all_backends():
    assert set(LLM_BACKEND_ORDER) == set(available_backends())


def test_apply_backend_sets_environment_variable(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_LLM_BACKEND", raising=False)

    assert apply_backend("ollama") == "ollama"
    assert os.environ["COMMUNITYLAB_LLM_BACKEND"] == "ollama"


def test_resolve_backend_prefers_explicit_name():
    assert resolve_backend("gemini") == "gemini"
