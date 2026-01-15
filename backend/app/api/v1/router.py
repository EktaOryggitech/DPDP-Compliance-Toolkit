"""
DPDP GUI Compliance Scanner - API v1 Router
"""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    organizations,
    applications,
    scans,
    findings,
    reports,
    schedules,
)

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(scans.router, prefix="/scans", tags=["Scans"])
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["Schedules"])
