"""
DPDP GUI Compliance Scanner - Authentication API Routes
"""
from typing import Annotated
from datetime import datetime, timedelta
import redis.asyncio as redis

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, CurrentUser
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    Token,
    UserResponse,
    PasswordChangeRequest,
)
from app.schemas.common import Message

router = APIRouter()

# Redis client for session tracking
_redis_client = None

async def get_redis_client():
    """Get or create Redis client for session tracking."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def update_session_activity(user_id: str):
    """Update the last activity timestamp for a user session."""
    client = await get_redis_client()
    session_key = f"session:{user_id}:last_activity"
    await client.setex(
        session_key,
        settings.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60,  # TTL in seconds
        datetime.utcnow().isoformat()
    )


async def check_session_active(user_id: str) -> bool:
    """Check if user session is still active (not expired due to inactivity)."""
    client = await get_redis_client()
    session_key = f"session:{user_id}:last_activity"
    last_activity = await client.get(session_key)
    return last_activity is not None


async def invalidate_session(user_id: str):
    """Invalidate user session (force logout)."""
    client = await get_redis_client()
    session_key = f"session:{user_id}:last_activity"
    await client.delete(session_key)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: DbSession,
):
    """
    Register a new user.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=request.email,
        name=request.name,
        password_hash=get_password_hash(request.password),
        role=request.role,
        organization_id=request.organization_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: DbSession,
):
    """
    Login and get JWT tokens.
    """
    # Find user by username or email
    from sqlalchemy import or_
    result = await db.execute(
        select(User).where(
            or_(User.username == request.email, User.email == request.email)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Create tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    # Initialize session activity tracking
    await update_session_activity(str(user.id))

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        inactivity_timeout=settings.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60,  # in seconds
        heartbeat_interval=settings.HEARTBEAT_INTERVAL_SECONDS,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            organization_id=user.organization_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
        ),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: DbSession,
):
    """
    Refresh access token using refresh token.
    """
    user_id = verify_token(refresh_token, token_type="refresh")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current user information.
    """
    return current_user


@router.post("/change-password", response_model=Message)
async def change_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Change current user's password.
    """
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    return Message(message="Password changed successfully")


@router.post("/heartbeat")
async def heartbeat(current_user: CurrentUser):
    """
    Heartbeat endpoint to keep session alive.
    Called periodically by frontend to update last activity time.
    Returns session status and remaining time.
    """
    user_id = str(current_user.id)

    # Check if session is still valid
    is_active = await check_session_active(user_id)

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to inactivity",
            headers={"X-Session-Expired": "inactivity"},
        )

    # Update last activity
    await update_session_activity(user_id)

    return {
        "status": "active",
        "message": "Session refreshed",
        "inactivity_timeout": settings.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60,
        "heartbeat_interval": settings.HEARTBEAT_INTERVAL_SECONDS,
    }


@router.post("/logout", response_model=Message)
async def logout(current_user: CurrentUser):
    """
    Logout user and invalidate session.
    """
    await invalidate_session(str(current_user.id))
    return Message(message="Logged out successfully")


@router.get("/session-config")
async def get_session_config():
    """
    Get session configuration (public endpoint).
    Used by frontend to know timeout settings.
    """
    return {
        "inactivity_timeout": settings.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60,  # in seconds
        "heartbeat_interval": settings.HEARTBEAT_INTERVAL_SECONDS,
    }
