"""
Test Suite for OCI Object Storage Integration.
"""

import json
import os
from io import BytesIO
from pathlib import Path

import pytest

from src.oci.storage import (
    OCIStorage,
    OCI_CREDENTIAL_ENV,
    OCI_KEY_ENV,
    OCI_REQUIRED_ENV,
    missing_oci_credentials,
    oci_credentials_complete,
)


class _FakeObjectStorageClient:
    """In-memory OCI Object Storage client for unit tests."""

    def __init__(self):
        self._objects = {}

    def put_object(self, namespace_name, bucket_name, object_name, put_object_body):
        if isinstance(put_object_body, (bytes, bytearray)):
            body = bytes(put_object_body)
        elif isinstance(put_object_body, str):
            body = put_object_body.encode("utf-8")
        else:
            body = put_object_body.read()
        self._objects[(namespace_name, bucket_name, object_name)] = body

    def get_object(self, namespace_name, bucket_name, object_name):
        key = (namespace_name, bucket_name, object_name)
        if key not in self._objects:
            raise Exception("Object not found")

        class _Response:
            data = BytesIO(self._objects[key])

        return _Response()


class _FakeOCIClient:
    """Fake OCI client that never touches the network."""

    def __init__(self):
        self.namespace = "test-namespace"

    def get_object_storage_client(self):
        return _FakeObjectStorageClient()


class _BrokenOCIClient:
    """Simulates an environment where the OCI SDK is not installed."""

    def __init__(self):
        self.namespace = "broken-namespace"

    def get_object_storage_client(self):
        raise ImportError("oci SDK is not installed")


class _RecordingOCIClient(_FakeOCIClient):
    """Fake client that counts how many times the OCI client was built."""

    def __init__(self):
        super().__init__()
        self.builds = 0

    def get_object_storage_client(self):
        self.builds += 1
        return super().get_object_storage_client()


@pytest.fixture
def credentials(monkeypatch):
    """Fake OCI credentials so the credential gate lets a call reach OCI."""
    for var in OCI_CREDENTIAL_ENV:
        monkeypatch.setenv(var, "set")
    return True


@pytest.fixture
def no_credentials(monkeypatch):
    """Blank every credential var.

    The vars are emptied instead of deleted on purpose: `load_dotenv()` would
    restore them from a real `.env` file.
    """
    for var in OCI_CREDENTIAL_ENV:
        monkeypatch.setenv(var, "")
    return True


@pytest.fixture
def storage(tmp_path, monkeypatch, credentials):
    """OCIStorage backed by an in-memory fake client and isolated cwd."""
    monkeypatch.chdir(tmp_path)
    return OCIStorage(oci_client=_FakeOCIClient())


def test_constructing_storage_does_not_build_the_client(tmp_path, monkeypatch, credentials):
    """The OCI client is built on first use, not on construction."""
    monkeypatch.chdir(tmp_path)
    recording = _RecordingOCIClient()

    storage = OCIStorage(oci_client=recording)
    assert recording.builds == 0

    _ = storage.client
    assert recording.builds == 1

    # The client is cached: a second use does not build it again.
    _ = storage.client
    assert recording.builds == 1


def test_put_json_and_get_json_round_trip(storage):
    data = {"origen": "test", "items": [1, 2, 3]}
    assert storage.put_json("test-bucket", "estado/round-trip.json", data) is True
    assert storage.get_json("test-bucket", "estado/round-trip.json") == data


def test_get_json_missing_key_returns_default(storage):
    assert storage.get_json("test-bucket", "estado/missing.json", default={}) == {}


def test_get_json_corrupt_json_returns_default(credentials):
    class _CorruptClient(_FakeObjectStorageClient):
        def get_object(self, namespace_name, bucket_name, object_name):
            class _Response:
                data = BytesIO(b"{this is not valid json")

            return _Response()

    broken_fake = _FakeOCIClient()
    broken_fake.get_object_storage_client = _CorruptClient
    storage = OCIStorage(oci_client=broken_fake)

    assert storage.get_json("test-bucket", "estado/corrupt.json", default=[]) == []


def test_put_json_and_get_json_never_raise_when_sdk_missing(tmp_path, monkeypatch, credentials):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_BrokenOCIClient())

    # These calls must not raise even though the client cannot be built.
    storage.put_json("test-bucket", "estado/x.json", {"a": 1})
    storage.get_json("test-bucket", "estado/x.json", default=None)


def test_put_json_falls_back_locally_when_sdk_missing(tmp_path, monkeypatch, credentials):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_BrokenOCIClient())

    data = {"clave": "valor"}
    storage.put_json("test-bucket", "estado/local-fallback.json", data)

    local_path = Path("storage/estado/local-fallback.json")
    assert local_path.exists()
    assert json.loads(local_path.read_text(encoding="utf-8")) == data


def test_get_json_falls_back_locally_when_sdk_missing(tmp_path, monkeypatch, credentials):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_BrokenOCIClient())

    local_path = Path("storage/estado/local-only.json")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps({"local": True}), encoding="utf-8")

    assert storage.get_json("test-bucket", "estado/local-only.json") == {"local": True}


def test_put_json_without_credentials_skips_oci_and_writes_local_mirror(
    tmp_path, monkeypatch, no_credentials
):
    """Without credentials the call never builds an OCI client."""
    monkeypatch.chdir(tmp_path)
    recording = _RecordingOCIClient()
    storage = OCIStorage(oci_client=recording)

    data = {"clave": "valor"}
    assert storage.put_json("test-bucket", "estado/sin-credenciales.json", data) is True

    assert recording.builds == 0
    local_path = Path("storage/estado/sin-credenciales.json")
    assert json.loads(local_path.read_text(encoding="utf-8")) == data


def test_get_json_without_credentials_reads_local_mirror(
    tmp_path, monkeypatch, no_credentials
):
    monkeypatch.chdir(tmp_path)
    recording = _RecordingOCIClient()
    storage = OCIStorage(oci_client=recording)

    local_path = Path("storage/estado/solo-local.json")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps({"local": True}), encoding="utf-8")

    assert storage.get_json("test-bucket", "estado/solo-local.json") == {"local": True}
    assert recording.builds == 0


def test_get_json_without_credentials_returns_default_when_mirror_is_empty(
    tmp_path, monkeypatch, no_credentials
):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_RecordingOCIClient())

    assert storage.get_json("test-bucket", "estado/nada.json", default={"vacio": True}) == {
        "vacio": True
    }


def test_missing_oci_credentials_reports_the_missing_variables(monkeypatch, no_credentials):
    assert missing_oci_credentials() == list(OCI_REQUIRED_ENV) + list(OCI_KEY_ENV)

    monkeypatch.setenv("OCI_REGION", "sa-sa-santiago-1")
    assert missing_oci_credentials() == [
        name for name in OCI_REQUIRED_ENV if name != "OCI_REGION"
    ] + list(OCI_KEY_ENV)


def test_missing_credentials_are_logged_once(tmp_path, monkeypatch, no_credentials, caplog):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_RecordingOCIClient())

    with caplog.at_level("WARNING", logger="src.oci.storage"):
        storage.put_json("test-bucket", "estado/una.json", {"a": 1})
        storage.put_json("test-bucket", "estado/dos.json", {"b": 2})
        storage.get_json("test-bucket", "estado/una.json")

    warnings = [rec for rec in caplog.records if "missing" in rec.getMessage()]
    assert len(warnings) == 1
    assert "OCI_USER_ID" in warnings[0].getMessage()


def test_oci_credentials_complete_requires_every_credential_variable(monkeypatch):
    for var in OCI_REQUIRED_ENV:
        monkeypatch.setenv(var, "set")

    assert oci_credentials_complete() is False

    monkeypatch.setenv("OCI_PRIVATE_KEY_PATH", "set")
    assert oci_credentials_complete() is True

    monkeypatch.setenv("OCI_FINGERPRINT", "")
    assert oci_credentials_complete() is False


def test_either_key_variable_is_enough(monkeypatch):
    """The key can arrive as a path or as content; one of the two is enough."""
    for var in OCI_REQUIRED_ENV:
        monkeypatch.setenv(var, "set")

    monkeypatch.setenv("OCI_PRIVATE_KEY", "pem-content")
    assert oci_credentials_complete() is True
    assert missing_oci_credentials() == []

    monkeypatch.setenv("OCI_PRIVATE_KEY", "")
    assert oci_credentials_complete() is False
    assert missing_oci_credentials() == list(OCI_KEY_ENV)


def test_required_env_holds_credentials_not_target():
    """The bucket and the namespace are targets with defaults, not credentials."""
    assert "OCI_BUCKET_NAME" not in OCI_REQUIRED_ENV
    assert "OCI_NAMESPACE" not in OCI_REQUIRED_ENV
    assert set(OCI_REQUIRED_ENV) == {
        "OCI_USER_ID",
        "OCI_FINGERPRINT",
        "OCI_TENANCY_ID",
        "OCI_REGION",
    }
    assert set(OCI_KEY_ENV) == {
        "OCI_PRIVATE_KEY_PATH",
        "OCI_PRIVATE_KEY",
    }


def test_credential_env_lists_every_variable_that_holds_a_secret():
    """Fixtures that clear the credentials need the whole list, key included."""
    assert set(OCI_CREDENTIAL_ENV) == set(OCI_REQUIRED_ENV) | set(OCI_KEY_ENV)


@pytest.mark.skipif(
    not os.getenv("OCI_USER_ID") or not os.getenv("OCI_PRIVATE_KEY_PATH"),
    reason="OCI credentials not configured in CI environment"
)
def test_oci_storage_integration():
    """Tests full integration with the OCI bucket."""
    bucket_name = os.getenv("OCI_BUCKET_NAME", "communitylab-activos-marketing")

    storage = OCIStorage()
    success, message = storage.test_connection_and_upload(
        bucket_name=bucket_name,
        file_name="test-integration.txt",
        content="Automated test from CommunityLab test suite."
    )

    assert success is True, f"OCI integration failed: {message}"
    print(f"✅ {message}")


if __name__ == "__main__":
    if not os.getenv("OCI_USER_ID"):
        print("⚠️ OCI credentials not found in environment. Skipping test execution.")
    else:
        test_oci_storage_integration()
