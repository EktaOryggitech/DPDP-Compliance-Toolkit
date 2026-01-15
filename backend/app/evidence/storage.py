"""
DPDP GUI Compliance Scanner - Evidence Storage

Manages storage of evidence files in MinIO object storage.
"""
import asyncio
import io
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, BinaryIO, Dict, List, Optional

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

from app.core.config import settings
from app.evidence.screenshot import AnnotatedScreenshot


@dataclass
class StoredEvidence:
    """Stored evidence file metadata."""
    id: str
    scan_id: str
    finding_id: Optional[str]
    file_path: str
    file_type: str
    file_size: int
    bucket: str
    url: str
    uploaded_at: datetime
    metadata: Dict[str, Any]


class EvidenceStorage:
    """
    MinIO-based storage for evidence files.

    Features:
    - Upload screenshots and HTML evidence
    - Generate presigned URLs for viewing
    - Organize evidence by scan and finding
    - Automatic cleanup of old evidence
    """

    def __init__(self):
        if not MINIO_AVAILABLE:
            raise RuntimeError("minio package is required for evidence storage")

        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the evidence bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"Error creating bucket: {e}")

    async def upload_screenshot(
        self,
        screenshot: AnnotatedScreenshot,
        scan_id: str,
        finding_id: Optional[str] = None,
    ) -> StoredEvidence:
        """
        Upload a screenshot to storage.

        Args:
            screenshot: AnnotatedScreenshot to upload
            scan_id: Associated scan ID
            finding_id: Optional associated finding ID

        Returns:
            StoredEvidence with storage metadata
        """
        # Use annotated version if available
        file_path = screenshot.annotated_path or screenshot.original_path

        def _upload():
            # Generate object path
            date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
            object_name = f"scans/{scan_id}/{date_prefix}/{screenshot.id}.jpg"

            # Get file size
            file_size = os.path.getsize(file_path)

            # Upload file
            with open(file_path, "rb") as f:
                self.client.put_object(
                    self.bucket_name,
                    object_name,
                    f,
                    file_size,
                    content_type="image/jpeg",
                    metadata={
                        "scan_id": scan_id,
                        "finding_id": finding_id or "",
                        "url": screenshot.url_or_window,
                        "timestamp": screenshot.timestamp.isoformat(),
                        "annotated": str(screenshot.annotated_path is not None),
                    },
                )

            return object_name, file_size

        object_name, file_size = await asyncio.to_thread(_upload)

        return StoredEvidence(
            id=screenshot.id,
            scan_id=scan_id,
            finding_id=finding_id,
            file_path=object_name,
            file_type="screenshot",
            file_size=file_size,
            bucket=self.bucket_name,
            url=f"s3://{self.bucket_name}/{object_name}",
            uploaded_at=datetime.utcnow(),
            metadata={
                "url_or_window": screenshot.url_or_window,
                "width": screenshot.width,
                "height": screenshot.height,
                "annotations_count": len(screenshot.annotations),
            },
        )

    async def upload_html_evidence(
        self,
        html_content: str,
        scan_id: str,
        page_url: str,
        finding_id: Optional[str] = None,
    ) -> StoredEvidence:
        """
        Upload HTML content as evidence.

        Args:
            html_content: HTML string to store
            scan_id: Associated scan ID
            page_url: Source page URL
            finding_id: Optional associated finding ID

        Returns:
            StoredEvidence with storage metadata
        """
        evidence_id = str(uuid.uuid4())

        def _upload():
            date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
            object_name = f"scans/{scan_id}/{date_prefix}/{evidence_id}.html"

            # Convert to bytes
            html_bytes = html_content.encode("utf-8")
            file_size = len(html_bytes)

            # Upload
            self.client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(html_bytes),
                file_size,
                content_type="text/html",
                metadata={
                    "scan_id": scan_id,
                    "finding_id": finding_id or "",
                    "page_url": page_url,
                },
            )

            return object_name, file_size

        object_name, file_size = await asyncio.to_thread(_upload)

        return StoredEvidence(
            id=evidence_id,
            scan_id=scan_id,
            finding_id=finding_id,
            file_path=object_name,
            file_type="html",
            file_size=file_size,
            bucket=self.bucket_name,
            url=f"s3://{self.bucket_name}/{object_name}",
            uploaded_at=datetime.utcnow(),
            metadata={"page_url": page_url},
        )

    async def upload_file(
        self,
        file_content: BinaryIO,
        filename: str,
        content_type: str,
        scan_id: str,
        finding_id: Optional[str] = None,
    ) -> StoredEvidence:
        """
        Upload a generic file as evidence.

        Args:
            file_content: File-like object with content
            filename: Original filename
            content_type: MIME type
            scan_id: Associated scan ID
            finding_id: Optional associated finding ID

        Returns:
            StoredEvidence with storage metadata
        """
        evidence_id = str(uuid.uuid4())

        def _upload():
            date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
            ext = os.path.splitext(filename)[1]
            object_name = f"scans/{scan_id}/{date_prefix}/{evidence_id}{ext}"

            # Get file size
            file_content.seek(0, 2)
            file_size = file_content.tell()
            file_content.seek(0)

            # Upload
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_content,
                file_size,
                content_type=content_type,
                metadata={
                    "scan_id": scan_id,
                    "finding_id": finding_id or "",
                    "original_filename": filename,
                },
            )

            return object_name, file_size

        object_name, file_size = await asyncio.to_thread(_upload)

        return StoredEvidence(
            id=evidence_id,
            scan_id=scan_id,
            finding_id=finding_id,
            file_path=object_name,
            file_type=content_type,
            file_size=file_size,
            bucket=self.bucket_name,
            url=f"s3://{self.bucket_name}/{object_name}",
            uploaded_at=datetime.utcnow(),
            metadata={"original_filename": filename},
        )

    async def get_presigned_url(
        self,
        object_path: str,
        expires_hours: int = 24,
    ) -> str:
        """
        Generate a presigned URL for viewing/downloading evidence.

        Args:
            object_path: Path to object in bucket
            expires_hours: URL expiration time in hours

        Returns:
            Presigned URL string
        """
        def _get_url():
            return self.client.presigned_get_object(
                self.bucket_name,
                object_path,
                expires=timedelta(hours=expires_hours),
            )

        return await asyncio.to_thread(_get_url)

    async def download_evidence(
        self,
        object_path: str,
    ) -> bytes:
        """
        Download evidence file content.

        Args:
            object_path: Path to object in bucket

        Returns:
            File content as bytes
        """
        def _download():
            response = self.client.get_object(self.bucket_name, object_path)
            content = response.read()
            response.close()
            response.release_conn()
            return content

        return await asyncio.to_thread(_download)

    async def delete_evidence(
        self,
        object_path: str,
    ) -> bool:
        """
        Delete an evidence file.

        Args:
            object_path: Path to object in bucket

        Returns:
            True if deleted successfully
        """
        def _delete():
            try:
                self.client.remove_object(self.bucket_name, object_path)
                return True
            except S3Error:
                return False

        return await asyncio.to_thread(_delete)

    async def list_scan_evidence(
        self,
        scan_id: str,
    ) -> List[Dict[str, Any]]:
        """
        List all evidence files for a scan.

        Args:
            scan_id: Scan ID to list evidence for

        Returns:
            List of evidence file metadata
        """
        def _list():
            prefix = f"scans/{scan_id}/"
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True,
            )

            evidence_list = []
            for obj in objects:
                evidence_list.append({
                    "path": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })

            return evidence_list

        return await asyncio.to_thread(_list)

    async def cleanup_old_evidence(
        self,
        days_old: int = 90,
    ) -> int:
        """
        Delete evidence older than specified days.

        Args:
            days_old: Delete evidence older than this many days

        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        def _cleanup():
            deleted_count = 0
            objects = self.client.list_objects(
                self.bucket_name,
                recursive=True,
            )

            for obj in objects:
                if obj.last_modified < cutoff_date:
                    try:
                        self.client.remove_object(self.bucket_name, obj.object_name)
                        deleted_count += 1
                    except S3Error:
                        pass

            return deleted_count

        return await asyncio.to_thread(_cleanup)
