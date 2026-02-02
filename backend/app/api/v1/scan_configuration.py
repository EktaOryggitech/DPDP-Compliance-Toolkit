"""
DPDP GUI Compliance Scanner - Scan Configuration API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.scan_configuration import ScanConfiguration
from app.models.user import UserRole
from app.schemas.scan_configuration import (
    ScanConfigurationResponse,
    ScanConfigurationUpdate,
    QUICK_DEFAULT,
    STANDARD_DEFAULT,
    DEEP_DEFAULT,
)

router = APIRouter()


async def get_or_create_config(db: DbSession) -> ScanConfiguration:
    """Get the global scan configuration, creating it if it doesn't exist."""
    result = await db.execute(select(ScanConfiguration).limit(1))
    config = result.scalar_one_or_none()

    if config is None:
        # Create default configuration
        config = ScanConfiguration(
            quick_pages=QUICK_DEFAULT,
            standard_pages=STANDARD_DEFAULT,
            deep_pages=DEEP_DEFAULT,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config


@router.get("", response_model=ScanConfigurationResponse)
async def get_scan_configuration(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get current scan configuration.

    Returns the global scan type page count configuration with bounds for validation.
    """
    config = await get_or_create_config(db)
    return ScanConfigurationResponse.model_validate(config)


@router.put(
    "",
    response_model=ScanConfigurationResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_scan_configuration(
    update_data: ScanConfigurationUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Update scan configuration.

    Admin only. Updates the page count settings for each scan type.
    """
    config = await get_or_create_config(db)

    # Update only provided fields
    if update_data.quick_pages is not None:
        config.quick_pages = update_data.quick_pages
    if update_data.standard_pages is not None:
        config.standard_pages = update_data.standard_pages
    if update_data.deep_pages is not None:
        config.deep_pages = update_data.deep_pages

    await db.commit()
    await db.refresh(config)

    return ScanConfigurationResponse.model_validate(config)
