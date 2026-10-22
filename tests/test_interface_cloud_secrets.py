"""Tests for mapping Streamlit Cloud secrets into the process environment."""

from __future__ import annotations

import os
import stat
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


PEM_CONTENT = "-----BEGIN PRIVATE KEY-----\nFAKE\n-----END PRIVATE KEY-----\n"
PEM_WITH_LITERAL_ESCAPES = (
    "-----BEGIN PRIVATE KEY-----\\nFAKE\\n-----END PRIVATE KEY-----\\n"
)


def _clear_oci_private_key_vars(monkeypatch):
    """Remove the OCI key variables and guarantee the teardown deletes them.

    ``monkeypatch.delenv`` on a variable that does not exist records nothing,
    so a value written later by the code under test would survive the test and
    leak into the next one. Setting the variable first records the original
    state, and the teardown then deletes it.
    """
    for name in ("OCI_PRIVATE_KEY", "OCI_PRIVATE_KEY_PATH"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


def test_bootstrap_writes_pem_to_temp_file_and_sets_path(monkeypatch, tmp_path):
    _clear_oci_private_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)

    path = cloud_secrets.bootstrap_oci_private_key()

    assert path is not None
    assert os.environ["OCI_PRIVATE_KEY_PATH"] == path
    with open(path, "r", encoding="utf-8") as f:
        assert f.read() == PEM_CONTENT
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_bootstrap_turns_literal_newline_escapes_into_line_breaks(monkeypatch):
    _clear_oci_private_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_WITH_LITERAL_ESCAPES)

    path = cloud_secrets.bootstrap_oci_private_key()

    assert path is not None
    with open(path, "r", encoding="utf-8") as f:
        assert f.read() == PEM_CONTENT


def test_bootstrap_keeps_a_multiline_secret_untouched(monkeypatch):
    _clear_oci_private_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)

    path = cloud_secrets.bootstrap_oci_private_key()

    assert path is not None
    with open(path, "r", encoding="utf-8") as f:
        assert f.read() == PEM_CONTENT
    assert "\\n" not in PEM_CONTENT


def test_bootstrap_preserves_existing_private_key_path(monkeypatch, tmp_path):
    existing = tmp_path / "existing.pem"
    existing.write_text("existing-key", encoding="utf-8")
    _clear_oci_private_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)
    monkeypatch.setenv("OCI_PRIVATE_KEY_PATH", str(existing))

    path = cloud_secrets.bootstrap_oci_private_key()

    assert path == str(existing)
    assert os.environ["OCI_PRIVATE_KEY_PATH"] == str(existing)
    assert existing.read_text(encoding="utf-8") == "existing-key"


def test_bootstrap_skips_when_secret_is_missing(monkeypatch):
    _clear_oci_private_key_vars(monkeypatch)

    assert cloud_secrets.bootstrap_oci_private_key() is None


def test_bootstrap_creates_temp_file_when_path_points_to_directory(monkeypatch, tmp_path):
    _clear_oci_private_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)
    monkeypatch.setenv("OCI_PRIVATE_KEY_PATH", str(tmp_path))

    path = cloud_secrets.bootstrap_oci_private_key()

    assert path is not None
    assert path != str(tmp_path)
    assert os.path.isfile(path)
    with open(path, "r", encoding="utf-8") as f:
        assert f.read() == PEM_CONTENT


def test_bootstrap_returns_none_on_write_failure(monkeypatch):
    _clear_oci_private_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)

    def _bad_mkstemp(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("tempfile.mkstemp", _bad_mkstemp)

    assert cloud_secrets.bootstrap_oci_private_key() is None
