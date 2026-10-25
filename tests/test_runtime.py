"""Tests for the runtime LLM backend selection helpers."""

import os

from src.ingest import runtime
from src.ingest.runtime import (
    LLM_BACKEND_ORDER,
    apply_backend,
    available_backends,
    resolve_backend,
    split_backends,
)


def test_available_backends_disables_missing_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setattr(runtime, "_ollama_importable", lambda: False)

    assert available_backends() == {
        "ollama": False,
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


def test_available_backends_ollama_cloud_with_key(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "fake")
    monkeypatch.setattr(runtime, "_ollama_importable", lambda: False)

    assert available_backends()["ollama"] is True


def test_available_backends_ollama_local_with_package(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setattr(runtime, "_ollama_importable", lambda: True)

    assert available_backends()["ollama"] is True


def test_available_backends_ollama_disabled_without_key_or_package(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setattr(runtime, "_ollama_importable", lambda: False)

    assert available_backends()["ollama"] is False


def test_llm_backend_order_covers_all_backends():
    assert set(LLM_BACKEND_ORDER) == set(available_backends())


def test_apply_backend_sets_environment_variable(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")

    assert apply_backend("ollama") == "ollama"
    assert os.environ["COMMUNITYLAB_LLM_BACKEND"] == "ollama"


def test_resolve_backend_prefers_explicit_name():
    assert resolve_backend("gemini") == "gemini"


def test_split_backends_respects_order(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "fake")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    activos, inactivos = split_backends()

    assert activos == ["ollama", "gemini", "openai", "rule_based"]
    assert inactivos == []


def test_split_backends_partitions_by_availability(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(runtime, "_ollama_importable", lambda: False)

    activos, inactivos = split_backends()

    assert activos == ["rule_based"]
    assert set(inactivos) == {"ollama", "gemini", "openai"}
