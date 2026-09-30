"""
Oracle Cloud Infrastructure (OCI) Client Module.
Handles authentication and provides the Object Storage client using OCI SDK.
"""

import os
import oci
from dotenv import load_dotenv

load_dotenv()

class OCIClient:
    """Centralized client for OCI connections using environment variables."""

    def __init__(self):
        self.config = {
            "user": os.getenv("OCI_USER_ID"),
            "key_file": os.getenv("OCI_PRIVATE_KEY_PATH"),
            "fingerprint": os.getenv("OCI_FINGERPRINT"),
            "tenancy": os.getenv("OCI_TENANCY_ID"),
            "region": os.getenv("OCI_REGION")
        }
        self.namespace = os.getenv("OCI_NAMESPACE", "axcyr94oehmi")
        self._client = None

    def get_object_storage_client(self) -> oci.object_storage.ObjectStorageClient:
        """Returns an authenticated instance of the Object Storage client."""
        if not self._client:
            self._client = oci.object_storage.ObjectStorageClient(self.config)
        return self._client
