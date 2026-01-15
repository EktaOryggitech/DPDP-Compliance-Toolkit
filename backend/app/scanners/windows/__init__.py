# DPDP GUI Compliance Scanner - Windows Scanner Module
from app.scanners.windows.controller import WindowsController
from app.scanners.windows.scanner import WindowsScanner
from app.scanners.windows.vision import WindowsVisionAnalyzer, VisionAnalysisResult
from app.scanners.windows.ocr_processor import OCRProcessor, ProcessedText

__all__ = [
    "WindowsController",
    "WindowsScanner",
    "WindowsVisionAnalyzer",
    "VisionAnalysisResult",
    "OCRProcessor",
    "ProcessedText",
]
