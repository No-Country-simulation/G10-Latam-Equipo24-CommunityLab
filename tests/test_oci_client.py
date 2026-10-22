"""Tests for the OCI client configuration.

The private key can reach the app in two shapes: a path to a ``.pem`` file
(local checkout) or the PEM content itself (Streamlit Cloud secrets). The
client has to accept both without writing anything to disk.
"""

from __future__ import annotations

from src.oci.client import OCIClient

PEM_CONTENT = "-----BEGIN PRIVATE KEY-----\nFAKE\n-----END PRIVATE KEY-----\n"
PEM_WITH_LITERAL_ESCAPES = (
    "-----BEGIN PRIVATE KEY-----\\nFAKE\\n-----END PRIVATE KEY-----\\n"
)


def _clear_key_vars(monkeypatch):
    """Remove both key variables and guarantee the teardown deletes them.

    ``monkeypatch.delenv`` on a variable that does not exist records nothing,
    so a value written later by the code under test would survive the test and
    leak into the next one. Setting the variable first records the original
    state, and the teardown then deletes it.
    """
    for name in ("OCI_PRIVATE_KEY", "OCI_PRIVATE_KEY_PATH"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


def test_client_prefers_the_key_file_when_it_exists(monkeypatch, tmp_path):
    key_file = tmp_path / "key.pem"
    key_file.write_text(PEM_CONTENT, encoding="utf-8")
    _clear_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY_PATH", str(key_file))
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)

    config = OCIClient().config

    assert config["key_file"] == str(key_file)
    assert config["key_content"] is None


def test_client_falls_back_to_the_key_content_when_the_file_is_missing(monkeypatch):
    _clear_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY_PATH", "/nonexistent/key.pem")
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)

    config = OCIClient().config

    assert config["key_file"] == "/nonexistent/key.pem"
    assert config["key_content"] == PEM_CONTENT


def test_client_uses_the_key_content_when_there_is_no_path(monkeypatch):
    _clear_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)

    config = OCIClient().config

    assert config["key_file"] is None
    assert config["key_content"] == PEM_CONTENT


def test_client_normalizes_literal_newline_escapes(monkeypatch):
    _clear_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_WITH_LITERAL_ESCAPES)

    config = OCIClient().config

    assert config["key_content"] == PEM_CONTENT


def test_client_keeps_a_multiline_key_content_untouched(monkeypatch):
    _clear_key_vars(monkeypatch)
    monkeypatch.setenv("OCI_PRIVATE_KEY", PEM_CONTENT)

    config = OCIClient().config

    assert config["key_content"] == PEM_CONTENT
    assert "\\n" not in config["key_content"]


def test_client_without_any_key_has_neither_file_nor_content(monkeypatch):
    _clear_key_vars(monkeypatch)

    config = OCIClient().config

    assert config["key_file"] is None
    assert config["key_content"] is None
