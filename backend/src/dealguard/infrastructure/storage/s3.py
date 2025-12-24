"""S3-compatible storage for document files."""

from typing import Any, cast
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from dealguard.config import get_settings
from dealguard.shared.concurrency import to_thread_limited
from dealguard.shared.exceptions import StorageError
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


class S3Storage:
    """S3-compatible storage for documents.

    Works with AWS S3 in production and MinIO for local development.

    Note: Uses a bounded threadpool helper (`to_thread_limited`) to run boto3
    sync calls without blocking the async event loop.
    """

    def __init__(self) -> None:
        settings = get_settings()

        # Configure S3 client
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )

    def _get_key(self, organization_id: UUID, document_id: UUID, filename: str) -> str:
        """Generate S3 key for a document.

        Structure: org-{org_id}/contracts/{doc_id}/{filename}
        """
        return f"org-{organization_id}/contracts/{document_id}/{filename}"

    async def upload(
        self,
        content: bytes,
        organization_id: UUID,
        filename: str,
        mime_type: str,
    ) -> tuple[str, UUID]:
        """Upload a document to S3.

        Args:
            content: File content as bytes
            organization_id: Organization the file belongs to
            filename: Original filename
            mime_type: MIME type of the file

        Returns:
            Tuple of (S3 key, document_id)

        Raises:
            StorageError: If upload fails
        """
        document_id = uuid4()
        key = self._get_key(organization_id, document_id, filename)

        try:
            # Run sync boto3 call in thread pool to avoid blocking event loop
            await to_thread_limited(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=mime_type,
                Metadata={
                    "organization_id": str(organization_id),
                    "original_filename": filename,
                },
            )

            logger.info(
                "file_uploaded",
                key=key,
                size=len(content),
                organization_id=str(organization_id),
            )

            return key, document_id

        except ClientError as e:
            logger.error("s3_upload_failed", key=key, error=str(e))
            raise StorageError(f"Datei konnte nicht hochgeladen werden: {e}")

    async def download(self, key: str) -> bytes:
        """Download a document from S3.

        Args:
            key: S3 object key

        Returns:
            File content as bytes

        Raises:
            StorageError: If download fails
        """
        try:
            response = cast(
                dict[str, Any],
                await to_thread_limited(self.client.get_object, Bucket=self.bucket, Key=key),
            )
            # Reading the body is also blocking IO
            body = cast(Any, response["Body"])
            return cast(bytes, await to_thread_limited(body.read))

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                raise StorageError("Datei nicht gefunden")
            logger.error("s3_download_failed", key=key, error=str(e))
            raise StorageError(f"Datei konnte nicht heruntergeladen werden: {e}")

    async def delete(self, key: str) -> None:
        """Delete a document from S3.

        Args:
            key: S3 object key

        Raises:
            StorageError: If deletion fails
        """
        try:
            await to_thread_limited(self.client.delete_object, Bucket=self.bucket, Key=key)
            logger.info("file_deleted", key=key)

        except ClientError as e:
            logger.error("s3_delete_failed", key=key, error=str(e))
            raise StorageError(f"Datei konnte nicht gelöscht werden: {e}")

    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned URL for downloading.

        Args:
            key: S3 object key
            expires_in: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL string

        Raises:
            StorageError: If URL generation fails
        """
        try:
            url = cast(
                str,
                await to_thread_limited(
                self.client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
                ),
            )
            return url

        except ClientError as e:
            logger.error("presigned_url_failed", key=key, error=str(e))
            raise StorageError(f"Download-URL konnte nicht erstellt werden: {e}")

    async def exists(self, key: str) -> bool:
        """Check if a document exists in S3.

        Args:
            key: S3 object key

        Returns:
            True if exists, False otherwise
        """
        try:
            await to_thread_limited(self.client.head_object, Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
