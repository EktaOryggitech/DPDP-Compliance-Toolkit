# DPDP GUI Compliance Scanner - Detectors Module
from app.detectors.base import BaseDetector
from app.detectors.privacy_notice import PrivacyNoticeDetector
from app.detectors.consent import ConsentDetector
from app.detectors.dark_patterns import DarkPatternDetector
from app.detectors.children_data import ChildrenDataDetector
from app.detectors.data_principal_rights import (
    DataPrincipalRightsDetector,
    DataRetentionDetector,
)
from app.detectors.data_breach import (
    DataBreachNotificationDetector,
    SignificantDataFiduciaryDetector,
)

__all__ = [
    "BaseDetector",
    # Section 5 - Privacy Notice
    "PrivacyNoticeDetector",
    # Section 6 - Consent
    "ConsentDetector",
    # Section 9 - Children's Data
    "ChildrenDataDetector",
    # Sections 11-14 - Data Principal Rights
    "DataPrincipalRightsDetector",
    # Section 8 - Data Retention
    "DataRetentionDetector",
    # Section 8(6) - Breach Notification
    "DataBreachNotificationDetector",
    # Section 10 - Significant Data Fiduciary
    "SignificantDataFiduciaryDetector",
    # Dark Patterns
    "DarkPatternDetector",
]
