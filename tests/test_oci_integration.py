"""
Test Suite for OCI Object Storage Integration.
"""

import json
import os
from io import BytesIO
from pathlib import Path

import pytest

from src.oci.storage import OCIStorage, OCI_REQUIRED_ENV, oci_credentials_complete


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


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """OCIStorage backed by an in-memory fake client and isolated cwd."""
    monkeypatch.chdir(tmp_path)
    return OCIStorage(oci_client=_FakeOCIClient())


def test_put_json_and_get_json_round_trip(storage):
    data = {"origen": "test", "items": [1, 2, 3]}
    assert storage.put_json("test-bucket", "estado/round-trip.json", data) is True
    assert storage.get_json("test-bucket", "estado/round-trip.json") == data


def test_get_json_missing_key_returns_default(storage):
    assert storage.get_json("test-bucket", "estado/missing.json", default={}) == {}


def test_get_json_corrupt_json_returns_default(storage):
    class _CorruptClient(_FakeObjectStorageClient):
        def get_object(self, namespace_name, bucket_name, object_name):
            class _Response:
                data = BytesIO(b"{this is not valid json")

            return _Response()

    broken_fake = _FakeOCIClient()
    broken_fake.get_object_storage_client = _CorruptClient
    storage = OCIStorage(oci_client=broken_fake)

    assert storage.get_json("test-bucket", "estado/corrupt.json", default=[]) == []


def test_put_json_and_get_json_never_raise_when_sdk_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_BrokenOCIClient())

    # These calls must not raise even though the client cannot be built.
    storage.put_json("test-bucket", "estado/x.json", {"a": 1})
    storage.get_json("test-bucket", "estado/x.json", default=None)


def test_put_json_falls_back_locally_when_sdk_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_BrokenOCIClient())

    data = {"clave": "valor"}
    storage.put_json("test-bucket", "estado/local-fallback.json", data)

    local_path = Path("storage/estado/local-fallback.json")
    assert local_path.exists()
    assert json.loads(local_path.read_text(encoding="utf-8")) == data


def test_get_json_falls_back_locally_when_sdk_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = OCIStorage(oci_client=_BrokenOCIClient())

    local_path = Path("storage/estado/local-only.json")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps({"local": True}), encoding="utf-8")

    assert storage.get_json("test-bucket", "estado/local-only.json") == {"local": True}


def test_oci_credentials_complete_requires_seven_variables(monkeypatch):
    for var in OCI_REQUIRED_ENV:
        monkeypatch.setenv(var, "set")

    assert oci_credentials_complete() is True

    monkeypatch.setenv("OCI_BUCKET_NAME", "")
    assert oci_credentials_complete() is False


def test_oci_required_env_contains_bucket_and_namespace():
    assert "OCI_BUCKET_NAME" in OCI_REQUIRED_ENV
    assert "OCI_NAMESPACE" in OCI_REQUIRED_ENV


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
