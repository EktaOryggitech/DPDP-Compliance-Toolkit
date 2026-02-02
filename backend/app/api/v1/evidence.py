"""
DPDP GUI Compliance Scanner - Evidence API Routes

Serves evidence files (screenshots) from MinIO storage.
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.evidence.storage import EvidenceStorage, MINIO_AVAILABLE

router = APIRouter()


@router.get("/screenshot/{scan_id}/{year}/{month}/{day}/{filename}")
async def get_screenshot(
    scan_id: str,
    year: str,
    month: str,
    day: str,
    filename: str,
):
    """
    Serve a screenshot from MinIO storage.

    This endpoint proxies the image through the backend to avoid
    CORS and signature issues with direct MinIO access.

    Note: This endpoint does not require authentication because:
    1. The URL contains UUIDs (scan_id, filename) that are hard to guess
    2. Images need to be loaded by <img> tags which can't send auth headers
    3. The screenshots don't contain sensitive data beyond what's visible in the app
    """
    if not MINIO_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service not available"
        )

    try:
        storage = EvidenceStorage()
        object_path = f"scans/{scan_id}/{year}/{month}/{day}/{filename}"

        # Download the image from MinIO
        content = await storage.download_evidence(object_path)

        # Determine content type
        content_type = "image/jpeg"
        if filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith(".gif"):
            content_type = "image/gif"

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Cache-Control": "private, max-age=3600",  # Cache for 1 hour
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screenshot not found: {str(e)}"
        )
