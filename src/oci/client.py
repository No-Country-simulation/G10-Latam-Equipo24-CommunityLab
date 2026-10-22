"""
Oracle Cloud Infrastructure (OCI) Client Module.
Handles authentication and provides the Object Storage client using OCI SDK.

The private key reaches the app in one of two shapes and both are supported
without touching the filesystem:

- ``OCI_PRIVATE_KEY_PATH``: a path to a ``.pem`` file (local checkout).
- ``OCI_PRIVATE_KEY``: the PEM content itself (Streamlit Cloud secrets).

When the path points to a file that exists, the file wins; otherwise the
content is used. The OCI SDK accepts the content directly through
``key_content``, so no temporary file is ever needed.
"""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


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


class OCIClient:
    """Centralized client for OCI connections using environment variables."""

    def __init__(self):
        key_file = os.getenv("OCI_PRIVATE_KEY_PATH")
        key_content = None
        if not (key_file and os.path.isfile(key_file)):
            raw_key = os.getenv("OCI_PRIVATE_KEY")
            if raw_key:
                key_content = _normalize_pem(raw_key)

        self.config = {
            "user": os.getenv("OCI_USER_ID"),
            "key_file": key_file,
            "key_content": key_content,
            "fingerprint": os.getenv("OCI_FINGERPRINT"),
            "tenancy": os.getenv("OCI_TENANCY_ID"),
            "region": os.getenv("OCI_REGION")
        }
        self.namespace = os.getenv("OCI_NAMESPACE", "axcyr94oehmi")
        self._client = None

    def get_object_storage_client(self) -> Any:
        """Returns an authenticated instance of the Object Storage client.

        The `oci` SDK is imported lazily so the repo can be imported without it
        installed (consistent with `src/utils/llm.py`).
        """
        if not self._client:
            try:
                import oci
            except ImportError as exc:
                raise ImportError(
                    "oci is not installed. Run: pip install oci"
                ) from exc
            self._client = oci.object_storage.ObjectStorageClient(self.config)
        return self._client
