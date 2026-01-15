"""
DPDP GUI Compliance Scanner - Demo Data Seeder

Seeds the database with sample data for development and testing.
Run with: python -m app.scripts.seed_demo_data
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import BaseModel
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.application import Application, ApplicationType
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.finding import Finding, FindingSeverity, FindingStatus, CheckType

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_database():
    """Seed the database with demo data."""

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(Organization).limit(1))
        if result.scalar_one_or_none():
            print("Database already has data. Skipping seed.")
            return

        print("Seeding demo data...")

        # ===================
        # Create Organization
        # ===================
        org = Organization(
            id=uuid.uuid4(),
            name="National Informatics Centre",
            code="NIC",
            type="government",
            description="Premier technology organization of the Government of India",
            website="https://www.nic.in",
            contact_email="support@nic.in",
            dpo_name="Data Protection Officer",
            dpo_email="dpo@nic.in",
            is_active=True,
        )
        session.add(org)
        print(f"  Created organization: {org.name}")

        # ============
        # Create Users
        # ============
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@nic.in",
            name="System Administrator",
            password_hash=pwd_context.hash("admin123"),
            role=UserRole.ADMIN,
            organization_id=org.id,
            is_active=True,
            is_verified=True,
        )
        session.add(admin_user)

        auditor_user = User(
            id=uuid.uuid4(),
            email="auditor@nic.in",
            name="DPDP Compliance Auditor",
            password_hash=pwd_context.hash("auditor123"),
            role=UserRole.AUDITOR,
            organization_id=org.id,
            is_active=True,
            is_verified=True,
        )
        session.add(auditor_user)
        print(f"  Created users: admin@nic.in, auditor@nic.in")

        # ===================
        # Create Applications
        # ===================

        # Web Application 1
        app1 = Application(
            id=uuid.uuid4(),
            name="DigiLocker Portal",
            description="Digital document storage and verification platform",
            type=ApplicationType.WEB,
            url="https://www.digilocker.gov.in",
            organization_id=org.id,
            tags=["citizen-facing", "documents", "high-priority"],
            is_active=True,
        )
        session.add(app1)

        # Web Application 2
        app2 = Application(
            id=uuid.uuid4(),
            name="UMANG Mobile App Portal",
            description="Unified Mobile Application for New-age Governance",
            type=ApplicationType.WEB,
            url="https://web.umang.gov.in",
            organization_id=org.id,
            tags=["citizen-facing", "mobile", "services"],
            is_active=True,
        )
        session.add(app2)

        # Web Application 3
        app3 = Application(
            id=uuid.uuid4(),
            name="MyGov Portal",
            description="Citizen engagement platform",
            type=ApplicationType.WEB,
            url="https://www.mygov.in",
            organization_id=org.id,
            tags=["citizen-facing", "engagement"],
            is_active=True,
        )
        session.add(app3)

        # Windows Application
        app4 = Application(
            id=uuid.uuid4(),
            name="e-Office Desktop Client",
            description="Desktop client for e-Office file management",
            type=ApplicationType.WINDOWS,
            executable_path="C:\\Program Files\\eOffice\\eOffice.exe",
            window_title="e-Office Client",
            organization_id=org.id,
            tags=["internal", "file-management"],
            is_active=True,
        )
        session.add(app4)

        print(f"  Created applications: DigiLocker, UMANG, MyGov, e-Office")

        # =============
        # Create Scans
        # =============

        # Completed Scan 1 - DigiLocker (Good compliance)
        scan1 = Scan(
            id=uuid.uuid4(),
            application_id=app1.id,
            scan_type=ScanType.STANDARD,
            status=ScanStatus.COMPLETED,
            pages_scanned=45,
            total_pages=45,
            progress_percentage=100,
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=1, minutes=45),
            overall_score=85.5,
            findings_count=8,
            critical_count=0,
            high_count=1,
            medium_count=3,
            low_count=4,
            initiated_by=auditor_user.id,
        )
        session.add(scan1)

        # Completed Scan 2 - UMANG (Moderate compliance)
        scan2 = Scan(
            id=uuid.uuid4(),
            application_id=app2.id,
            scan_type=ScanType.DEEP,
            status=ScanStatus.COMPLETED,
            pages_scanned=78,
            total_pages=78,
            progress_percentage=100,
            started_at=datetime.utcnow() - timedelta(days=1),
            completed_at=datetime.utcnow() - timedelta(days=1) + timedelta(hours=3),
            overall_score=62.0,
            findings_count=15,
            critical_count=2,
            high_count=4,
            medium_count=5,
            low_count=4,
            initiated_by=auditor_user.id,
        )
        session.add(scan2)

        # Running Scan 3 - MyGov
        scan3 = Scan(
            id=uuid.uuid4(),
            application_id=app3.id,
            scan_type=ScanType.STANDARD,
            status=ScanStatus.RUNNING,
            pages_scanned=23,
            total_pages=60,
            progress_percentage=38,
            current_url="https://www.mygov.in/about-us",
            started_at=datetime.utcnow() - timedelta(minutes=15),
            initiated_by=admin_user.id,
        )
        session.add(scan3)

        # Pending Scan 4 - e-Office
        scan4 = Scan(
            id=uuid.uuid4(),
            application_id=app4.id,
            scan_type=ScanType.QUICK,
            status=ScanStatus.PENDING,
            initiated_by=admin_user.id,
        )
        session.add(scan4)

        print(f"  Created scans: 2 completed, 1 running, 1 pending")

        # ===============
        # Create Findings
        # ===============

        # Findings for Scan 1 (DigiLocker)
        findings_scan1 = [
            Finding(
                id=uuid.uuid4(),
                scan_id=scan1.id,
                check_type=CheckType.PRIVACY_NOTICE_VISIBILITY,
                dpdp_section="Section 5",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                confidence=0.95,
                location="https://www.digilocker.gov.in/privacy-policy",
                title="Privacy notice is prominently displayed",
                description="The privacy policy link is visible in the footer on all pages.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan1.id,
                check_type=CheckType.CONSENT_NOT_PRESELECTED,
                dpdp_section="Section 6",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.HIGH,
                confidence=0.92,
                location="https://www.digilocker.gov.in/signup",
                element_selector="input#newsletter-consent",
                title="Pre-selected consent checkbox detected",
                description="Newsletter subscription checkbox is pre-selected on the signup form.",
                remediation="Ensure all consent checkboxes are unchecked by default as per DPDP Section 6.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan1.id,
                check_type=CheckType.PRIVACY_NOTICE_MULTILANG,
                dpdp_section="Section 5",
                status=FindingStatus.PARTIAL,
                severity=FindingSeverity.MEDIUM,
                confidence=0.88,
                location="https://www.digilocker.gov.in/privacy-policy",
                title="Privacy notice available in limited languages",
                description="Privacy notice is available in English but not in Hindi or regional languages.",
                remediation="Provide privacy notice in Hindi and other scheduled languages as per DPDP requirements.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan1.id,
                check_type=CheckType.WITHDRAWAL_EASY,
                dpdp_section="Section 6(6)",
                status=FindingStatus.PARTIAL,
                severity=FindingSeverity.MEDIUM,
                confidence=0.85,
                location="https://www.digilocker.gov.in/settings",
                title="Consent withdrawal requires multiple steps",
                description="Users need to navigate through 3 screens to withdraw consent for data processing.",
                remediation="Implement one-click consent withdrawal mechanism as per Section 6(6).",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan1.id,
                check_type=CheckType.RIGHTS_GRIEVANCE,
                dpdp_section="Section 13",
                status=FindingStatus.PARTIAL,
                severity=FindingSeverity.MEDIUM,
                confidence=0.90,
                location="https://www.digilocker.gov.in/contact",
                title="Grievance mechanism needs improvement",
                description="Contact page exists but lacks dedicated grievance redressal section.",
                remediation="Add prominent grievance officer contact details and grievance form.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan1.id,
                check_type=CheckType.PRIVACY_NOTICE_READABILITY,
                dpdp_section="Section 5",
                status=FindingStatus.PASS,
                severity=FindingSeverity.LOW,
                confidence=0.87,
                location="https://www.digilocker.gov.in/privacy-policy",
                title="Privacy notice readability score adequate",
                description="Flesch reading ease score: 52 (Fairly Difficult). Consider simplifying language.",
            ),
        ]

        for finding in findings_scan1:
            session.add(finding)

        # Findings for Scan 2 (UMANG)
        findings_scan2 = [
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.DARK_PATTERN_PRESELECTED,
                dpdp_section="Dark Patterns",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.CRITICAL,
                confidence=0.96,
                location="https://web.umang.gov.in/register",
                element_selector="input#marketing-emails",
                title="Critical: Pre-selected marketing consent",
                description="Marketing email consent is pre-selected, constituting a dark pattern.",
                remediation="Remove pre-selection from all consent checkboxes immediately.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.DARK_PATTERN_CONFIRM_SHAMING,
                dpdp_section="Dark Patterns",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.CRITICAL,
                confidence=0.91,
                location="https://web.umang.gov.in/notifications",
                title="Critical: Confirm-shaming language detected",
                description="'No thanks, I don't want to stay updated' uses guilt-inducing language.",
                remediation="Use neutral language for decline options (e.g., 'No, thanks').",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.CHILDREN_AGE_VERIFICATION,
                dpdp_section="Section 9",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.HIGH,
                confidence=0.89,
                location="https://web.umang.gov.in/register",
                title="Missing age verification for minors",
                description="No age verification mechanism to identify users under 18 years.",
                remediation="Implement robust age verification and parental consent flow for minors.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.CONSENT_GRANULAR,
                dpdp_section="Section 6",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.HIGH,
                confidence=0.93,
                location="https://web.umang.gov.in/register",
                title="Bundled consent without granular options",
                description="Single consent checkbox covers multiple data processing purposes.",
                remediation="Provide separate consent options for each data processing purpose.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.PRIVACY_NOTICE_PURPOSE,
                dpdp_section="Section 5",
                status=FindingStatus.PARTIAL,
                severity=FindingSeverity.HIGH,
                confidence=0.88,
                location="https://web.umang.gov.in/privacy",
                title="Vague data processing purposes",
                description="Privacy notice uses vague terms like 'improve services' without specifics.",
                remediation="Clearly enumerate all specific purposes for data collection and processing.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.PRIVACY_NOTICE_CONTACT,
                dpdp_section="Section 5",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.HIGH,
                confidence=0.94,
                location="https://web.umang.gov.in/privacy",
                title="Missing Data Protection Officer contact",
                description="Privacy notice does not include DPO contact information.",
                remediation="Add Data Protection Officer name, email, and contact number.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.RIGHTS_ACCESS,
                dpdp_section="Section 11",
                status=FindingStatus.PARTIAL,
                severity=FindingSeverity.MEDIUM,
                confidence=0.86,
                location="https://web.umang.gov.in/profile",
                title="Limited data access functionality",
                description="Users can view basic profile data but cannot export complete data.",
                remediation="Implement data export feature allowing users to download all their data.",
            ),
            Finding(
                id=uuid.uuid4(),
                scan_id=scan2.id,
                check_type=CheckType.RIGHTS_ERASURE,
                dpdp_section="Section 12",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.MEDIUM,
                confidence=0.90,
                location="https://web.umang.gov.in/settings",
                title="No account deletion option",
                description="Users cannot request deletion of their account and associated data.",
                remediation="Implement account deletion feature with clear data erasure confirmation.",
            ),
        ]

        for finding in findings_scan2:
            session.add(finding)

        print(f"  Created findings: {len(findings_scan1)} for DigiLocker, {len(findings_scan2)} for UMANG")

        # Commit all changes
        await session.commit()
        print("\n✓ Demo data seeded successfully!")
        print("\nDemo Credentials:")
        print("  Admin:   admin@nic.in / admin123")
        print("  Auditor: auditor@nic.in / auditor123")


if __name__ == "__main__":
    asyncio.run(seed_database())
