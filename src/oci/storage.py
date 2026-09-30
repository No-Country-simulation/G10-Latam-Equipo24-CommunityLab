"""
Oracle Cloud Infrastructure (OCI) Storage Module.
High-level operations on Object Storage (buckets, upload/download assets).
"""

from src.oci.client import OCIClient


class OCIStorage:
    """Manages storage operations in OCI Object Storage."""

    def __init__(self, oci_client: OCIClient = None):
        self.oci_client = oci_client or OCIClient()
        self.client = self.oci_client.get_object_storage_client()
        self.namespace = self.oci_client.namespace

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
