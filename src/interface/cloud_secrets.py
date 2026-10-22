"""Export Streamlit Community Cloud secrets into the process environment.

Every runtime setting in this project is read with ``os.getenv`` after an
optional ``load_dotenv()`` call, which works because a local checkout has a
``.env`` file. Streamlit Community Cloud has no ``.env``: the values live in
``.streamlit/secrets.toml`` and are exposed through ``st.secrets``, which
``os.getenv`` cannot see.

Importing this module maps each secret into ``os.environ`` (without
overwriting variables that are already set), so the exact same application
code runs locally and on the cloud with no branching.

Placement matters: import this module *before* ``src.pipeline`` /
``src.oci`` so the mapped variables are in place when those modules run
their own ``load_dotenv()`` calls.

Outside a Streamlit runtime (CLI scripts, tests) the import is a no-op.
"""

from __future__ import annotations

import atexit
import os
import stat
import tempfile


def export_secrets_to_environ() -> int:
    """Copy ``st.secrets`` entries into ``os.environ``.

    Returns the number of variables that were exported. Existing environment
    variables always win, and a missing Streamlit runtime or absent
    ``secrets.toml`` simply exports nothing.
    """
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:  # pragma: no cover - defensive: no Streamlit runtime
        return 0

    exported = 0
    try:
        items = list(secrets.items())
    except Exception:  # pragma: no cover - malformed/absent secrets.toml
        return 0

    for key, value in items:
        name = str(key)
        if name in os.environ:
            continue
        os.environ[name] = value if isinstance(value, str) else str(value)
        exported += 1
    return exported


def _try_remove(path: str) -> None:
    """Best-effort cleanup of a temporary file; never raises."""
    try:
        os.remove(path)
    except Exception:  # pragma: no cover - defensive cleanup
        pass


def _normalize_pem(content: str) -> str:
    r"""Return the PEM content with real line breaks.

    A PEM body is base64, so it never contains a backslash. When the secret
    arrives as a single line holding literal ``\n`` sequences (the provider
    kept the escape instead of turning it into a newline), the key would be
    invalid, so those sequences are turned into real line breaks. Content that
    already has real line breaks is returned unchanged.
    """
    if "\n" in content or "\\n" not in content:
        return content
    return content.replace("\\n", "\n")


def bootstrap_oci_private_key() -> str | None:
    """Materialize an inline PEM secret to a temporary file for OCI SDK.

    Streamlit Cloud exposes secrets as strings, but the OCI SDK requires a
    filesystem path. When ``OCI_PRIVATE_KEY`` is present and
    ``OCI_PRIVATE_KEY_PATH`` does not point to an existing file, this function
    writes the PEM content to a temp file with owner-only permissions (0600),
    points ``OCI_PRIVATE_KEY_PATH`` at it, and registers best-effort cleanup at
    process exit. If the path already exists, it is left untouched.

    Returns the resolved path, or ``None`` when no secret is available or the
    write fails.
    """
    pem_content = os.environ.get("OCI_PRIVATE_KEY")
    if not pem_content:
        return None

    pem_content = _normalize_pem(pem_content)

    existing_path = os.environ.get("OCI_PRIVATE_KEY_PATH")
    if existing_path and os.path.isfile(existing_path):
        return existing_path

    try:
        fd, temp_path = tempfile.mkstemp(suffix=".pem", prefix="oci_private_key_")
    except Exception:  # pragma: no cover - defensive: filesystem unavailable
        return None

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(pem_content)
        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:  # pragma: no cover - defensive: filesystem unavailable
        _try_remove(temp_path)
        return None

    os.environ["OCI_PRIVATE_KEY_PATH"] = temp_path
    atexit.register(_try_remove, temp_path)
    return temp_path


export_secrets_to_environ()
bootstrap_oci_private_key()
