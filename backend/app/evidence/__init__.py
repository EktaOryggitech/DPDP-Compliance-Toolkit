# DPDP GUI Compliance Scanner - Evidence Module
from app.evidence.screenshot import ScreenshotCapture, AnnotatedScreenshot
from app.evidence.annotator import EvidenceAnnotator
from app.evidence.storage import EvidenceStorage

__all__ = [
    "ScreenshotCapture",
    "AnnotatedScreenshot",
    "EvidenceAnnotator",
    "EvidenceStorage",
]
