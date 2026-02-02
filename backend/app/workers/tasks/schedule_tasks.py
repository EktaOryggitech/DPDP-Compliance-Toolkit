"""
DPDP GUI Compliance Scanner - Scheduled Tasks
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.application import Application, ApplicationType
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.schedule import ScanSchedule
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.schedule_tasks.check_scheduled_scans")
def check_scheduled_scans() -> Dict[str, Any]:
    """
    Check for scheduled scans that need to be executed.

    This task runs every minute via Celery Beat and:
    1. Queries all active schedules
    2. Checks if next_run_at has passed
    3. Triggers scan tasks for due schedules
    4. Updates next_run_at based on frequency
    """
    return asyncio.get_event_loop().run_until_complete(
        _check_scheduled_scans_async()
    )


async def _check_scheduled_scans_async() -> Dict[str, Any]:
    """Async implementation of scheduled scan check."""
    async with async_session_maker() as db:
        now = datetime.utcnow()

        # Get all active schedules that are due
        result = await db.execute(
            select(ScanSchedule).where(
                ScanSchedule.is_active == True,
                ScanSchedule.next_run_at <= now,
            )
        )
        due_schedules = result.scalars().all()

        triggered_scans = []

        for schedule in due_schedules:
            # Get the application
            application = await db.get(Application, schedule.application_id)
            if not application or not application.is_active:
                continue

            # Create a new scan (use STANDARD type for scheduled scans)
            scan = Scan(
                application_id=schedule.application_id,
                scan_type=ScanType.STANDARD,
                status=ScanStatus.PENDING,
            )
            db.add(scan)
            await db.flush()

            # Trigger the appropriate scan task
            from app.workers.tasks.scan_tasks import run_web_scan, run_windows_scan

            if application.type == ApplicationType.WEB:
                run_web_scan.delay(str(scan.id), str(application.id))
            else:
                run_windows_scan.delay(str(scan.id), str(application.id))

            # Update schedule
            schedule.last_run_at = now
            schedule.run_count += 1
            schedule.next_run_at = _calculate_next_run(schedule)

            triggered_scans.append(str(scan.id))

        await db.commit()

        return {
            "checked_at": now.isoformat(),
            "schedules_checked": len(due_schedules),
            "scans_triggered": triggered_scans,
        }


def _calculate_next_run(schedule: ScanSchedule) -> datetime:
    """Calculate the next run time based on schedule frequency."""
    from app.models.schedule import ScheduleFrequency

    now = datetime.utcnow()

    if schedule.frequency == ScheduleFrequency.DAILY:
        return now + timedelta(days=1)
    elif schedule.frequency == ScheduleFrequency.WEEKLY:
        return now + timedelta(weeks=1)
    elif schedule.frequency == ScheduleFrequency.BIWEEKLY:
        return now + timedelta(weeks=2)
    elif schedule.frequency == ScheduleFrequency.MONTHLY:
        return now + timedelta(days=30)
    else:
        return now + timedelta(days=1)


@celery_app.task(name="app.workers.tasks.schedule_tasks.cleanup_old_evidence")
def cleanup_old_evidence() -> Dict[str, Any]:
    """
    Clean up old evidence files from storage.

    This task runs daily via Celery Beat and:
    1. Finds scans older than retention period
    2. Deletes associated evidence files from MinIO
    3. Updates database records
    """
    return asyncio.get_event_loop().run_until_complete(
        _cleanup_old_evidence_async()
    )


async def _cleanup_old_evidence_async() -> Dict[str, Any]:
    """Async implementation of evidence cleanup."""
    # TODO: Implement evidence cleanup
    # - Query for scans older than retention period (e.g., 90 days)
    # - Delete evidence files from MinIO
    # - Optionally archive to cold storage
    # - Update Evidence records in database

    return {
        "cleaned_at": datetime.utcnow().isoformat(),
        "files_deleted": 0,
        "space_reclaimed_mb": 0,
    }
