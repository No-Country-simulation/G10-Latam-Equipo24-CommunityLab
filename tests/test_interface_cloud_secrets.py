"""Tests for mapping Streamlit Cloud secrets into the process environment."""

from __future__ import annotations

import os
import sys
import types

from src.interface import cloud_secrets


class _StreamlitWithoutSecrets(types.ModuleType):
    """Stand-in for Streamlit outside a runtime, where ``st.secrets`` raises."""

    @property
    def secrets(self):  # pragma: no cover - exercised through the module lookup
        raise RuntimeError("No secrets found")


def _install_fake_streamlit(monkeypatch, secrets):
    module = (
        _StreamlitWithoutSecrets("streamlit")
        if secrets is None
        else types.ModuleType("streamlit")
    )
    if secrets is not None:
        module.secrets = secrets
    monkeypatch.setitem(sys.modules, "streamlit", module)


def test_export_maps_secrets_to_environ(monkeypatch):
    _install_fake_streamlit(monkeypatch, {"COMMUNITYLAB_LLM_BACKEND": "rule_based"})
    monkeypatch.delenv("COMMUNITYLAB_LLM_BACKEND", raising=False)

    exported = cloud_secrets.export_secrets_to_environ()

    assert exported == 1
    assert os.environ["COMMUNITYLAB_LLM_BACKEND"] == "rule_based"


def test_export_does_not_overwrite_existing_environment(monkeypatch):
    _install_fake_streamlit(monkeypatch, {"OLLAMA_MODEL": "from-secrets"})
    monkeypatch.setenv("OLLAMA_MODEL", "from-shell")

    exported = cloud_secrets.export_secrets_to_environ()

    assert exported == 0
    assert os.environ["OLLAMA_MODEL"] == "from-shell"


def test_export_is_noop_without_streamlit_secrets(monkeypatch):
    _install_fake_streamlit(monkeypatch, None)

    assert cloud_secrets.export_secrets_to_environ() == 0
