"""
Oracle Cloud Infrastructure (OCI) Storage Module.
High-level operations on Object Storage (buckets, upload/download assets).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from src.oci.client import OCIClient

logger = logging.getLogger(__name__)

DEFAULT_BUCKET = "communitylab-activos-marketing"

# All environment variables that must be set (non-empty) before attempting OCI.
OCI_REQUIRED_ENV = (
    "OCI_USER_ID",
    "OCI_PRIVATE_KEY_PATH",
    "OCI_FINGERPRINT",
    "OCI_TENANCY_ID",
    "OCI_REGION",
    "OCI_BUCKET_NAME",
    "OCI_NAMESPACE",
)

_LOCAL_STATE_DIR = Path("storage") / "estado"


def oci_credentials_complete() -> bool:
    """True when every OCI credential env var is set to a non-empty value."""
    return all(os.getenv(name) for name in OCI_REQUIRED_ENV)


def _local_state_path(key: str) -> Path:
    """Local mirror path for an OCI object key.

    OCI keys such as ``estado/derivados-atendidos.json`` map directly to
    ``storage/estado/derivados-atendidos.json`` so local and remote shapes stay
    aligned.
    """
    relative = key.removeprefix("estado/")
    return _LOCAL_STATE_DIR / relative


def _read_response_body(data: Any) -> bytes:
    """Normalize OCI response data into bytes."""
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    return data.read()


class OCIStorage:
    """Manages storage operations in OCI Object Storage.

    The client is built lazily so constructing this class never raises, even
    when the ``oci`` SDK is not installed. JSON operations degrade to a local
    mirror under ``storage/estado/`` on any OCI failure and never raise.
    """

    def __init__(self, oci_client: OCIClient = None):
        self._oci_client = oci_client
        self._client = None
        self._namespace = None

    @property
    def client(self):
        """Lazy cached Object Storage client."""
        if self._client is None:
            oci_client = self._oci_client or OCIClient()
            self._client = oci_client.get_object_storage_client()
            self._namespace = oci_client.namespace
        return self._client

    @property
    def namespace(self) -> str:
        """OCI namespace (loaded lazily together with the client)."""
        if self._namespace is None:
            _ = self.client  # force client initialization
        return self._namespace

    def test_connection_and_upload(self, bucket_name: str, file_name: str = "test-integration.txt", content: str = "Hello from CommunityLab MVP!"):
        """Tests bucket connection by querying it and uploading a test file."""
        try:
            # 1. Validate bucket existence
            get_bucket_response = self.client.get_bucket(
                namespace_name=self.namespace,
                bucket_name=bucket_name
            )
            bucket_actual_name = get_bucket_response.data.name

            # 2. Upload test object
            self.client.put_object(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                object_name=file_name,
                put_object_body=content
            )
            return True, f"Successfully connected to bucket '{bucket_actual_name}' and uploaded file '{file_name}'."
        except Exception as e:
            return False, str(e)

    def put_json(self, bucket_name: str, key: str, data) -> bool:
        """Serialize ``data`` to JSON and write it to OCI, falling back locally.

        Returns ``True`` if the value was persisted (OCI or local mirror) and
        ``False`` only when both attempts fail. Never raises.
        """
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")

        try:
            self.client.put_object(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                object_name=key,
                put_object_body=payload,
            )
            return True
        except Exception as exc:
            logger.warning(
                "OCI put_json failed for %s/%s (%s); falling back to local mirror.",
                bucket_name,
                key,
                exc,
            )

        return self._write_local_fallback(key, payload)

    def get_json(self, bucket_name: str, key: str, default=None):
        """Read JSON from OCI, falling back to the local mirror.

        Returns ``default`` if the object is missing, corrupt, or unreadable.
        Never raises.
        """
        try:
            response = self.client.get_object(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                object_name=key,
            )
            body = _read_response_body(response.data)
            return json.loads(body.decode("utf-8"))
        except Exception as exc:
            logger.debug(
                "OCI get_json failed for %s/%s (%s); trying local mirror.",
                bucket_name,
                key,
                exc,
            )

        local_value = self._read_local_fallback(key)
        if local_value is not None:
            return local_value

        return default

    def _write_local_fallback(self, key: str, payload: bytes) -> bool:
        """Write ``payload`` to the local mirror. Returns True on success."""
        try:
            path = _local_state_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            return True
        except Exception as exc:
            logger.warning("Local fallback write failed for %s (%s).", key, exc)
            return False

    def _read_local_fallback(self, key: str):
        """Read JSON from the local mirror. Returns None on failure."""
        path = _local_state_path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Local fallback read failed for %s (%s).", key, exc)
            return None
