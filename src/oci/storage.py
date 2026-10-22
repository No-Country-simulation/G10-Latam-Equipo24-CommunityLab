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

# Credential env vars that must be set (non-empty) before attempting OCI.
#
# Only credentials live here. The *target* is not a credential and both parts
# already have documented defaults: `OCI_BUCKET_NAME` falls back to
# `DEFAULT_BUCKET` and `OCI_NAMESPACE` falls back to the default configured in
# `src/oci/client.py`. Requiring them as credentials would silently downgrade
# an upload that used to work to a local snapshot.
OCI_REQUIRED_ENV = (
    "OCI_USER_ID",
    "OCI_FINGERPRINT",
    "OCI_TENANCY_ID",
    "OCI_REGION",
)

# The private key can arrive in two shapes and the SDK accepts both: a path to
# a `.pem` file (local checkout) or the PEM content itself (Streamlit Cloud
# secrets). One of the two is enough, so neither is required on its own.
OCI_KEY_ENV = (
    "OCI_PRIVATE_KEY_PATH",
    "OCI_PRIVATE_KEY",
)

# Every variable that holds a credential, for callers that need to clear them.
OCI_CREDENTIAL_ENV = OCI_REQUIRED_ENV + OCI_KEY_ENV

_LOCAL_STATE_DIR = Path("storage") / "estado"


def missing_oci_credentials() -> list[str]:
    """Names of the OCI credential env vars that are unset or empty.

    The list is what the caller is missing, so the log says *which* variables
    to set instead of only that something is missing. The private key counts
    as present when either of its two variables is set, so both names are
    reported only when neither one is.
    """
    missing = [name for name in OCI_REQUIRED_ENV if not os.getenv(name)]
    if not any(os.getenv(name) for name in OCI_KEY_ENV):
        missing.extend(OCI_KEY_ENV)
    return missing


def oci_credentials_complete() -> bool:
    """True when every OCI credential env var is set to a non-empty value."""
    return not missing_oci_credentials()


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
    when the ``oci`` SDK is not installed. JSON operations check the credential
    gate first and degrade to a local mirror under ``storage/estado/`` on any
    OCI failure, without ever raising.
    """

    def __init__(self, oci_client: OCIClient = None):
        self._oci_client = oci_client
        self._client = None
        self._namespace = None
        self._warned_missing: tuple[str, ...] = ()

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

        The credential gate is checked first: without credentials the call goes
        straight to the local mirror and logs which variables are missing,
        instead of building a client that fails on the first call.

        Returns ``True`` if the value was persisted (OCI or local mirror) and
        ``False`` only when both attempts fail. The boolean does not say
        *where* it was persisted. Never raises.
        """
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")

        missing = missing_oci_credentials()
        if missing:
            self._warn_missing_credentials(missing)
            return self._write_local_fallback(key, payload)

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

        Without credentials the local mirror is read directly. Otherwise a
        failed read (missing object, corrupt payload, SDK or network error)
        falls back to the local mirror, and ``default`` is returned when the
        mirror has nothing usable. Never raises.

        Known divergence: the mirror is written only when the OCI write fails
        and is not refreshed when the OCI write succeeds, so a stale mirror
        file can shadow an object that no longer exists in OCI.
        """
        missing = missing_oci_credentials()
        if missing:
            self._warn_missing_credentials(missing)
            return self._read_local_fallback(key, default)

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

        return self._read_local_fallback(key, default)

    def _warn_missing_credentials(self, missing: list[str]) -> None:
        """Log the missing credential vars once per distinct set of vars."""
        names = tuple(sorted(missing))
        if names == self._warned_missing:
            return
        self._warned_missing = names
        logger.warning(
            "OCI credentials incomplete (missing: %s); using the local mirror "
            "under %s instead.",
            ", ".join(names),
            _LOCAL_STATE_DIR.as_posix(),
        )

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

    def _read_local_fallback(self, key: str, default=None):
        """Read JSON from the local mirror. Returns ``default`` on failure."""
        path = _local_state_path(key)
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Local fallback read failed for %s (%s).", key, exc)
            return default
