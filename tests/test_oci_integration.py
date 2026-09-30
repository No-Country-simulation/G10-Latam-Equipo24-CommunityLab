"""
Test Suite for OCI Object Storage Integration.
"""

import os
import sys

# Append project root to sys.path to allow imports from src regardless of execution path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.oci.storage import OCIStorage

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
    test_oci_storage_integration()
