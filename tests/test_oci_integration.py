"""
Test Suite for OCI Object Storage Integration.
"""

import os
import sys
import pytest

# Append project root to sys.path to allow imports from src regardless of execution path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.oci.storage import OCIStorage

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
