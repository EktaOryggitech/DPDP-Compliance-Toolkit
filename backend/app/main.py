"""
DPDP GUI Compliance Scanner - Main Application
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import close_db, init_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    print("Database initialized")

    yield

    # Shutdown
    print("Shutting down...")
    await close_db()
    print("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## DPDP GUI Compliance Scanner

    An automated platform to assess data protection compliance across web applications
    and Windows desktop applications in accordance with the Digital Personal Data
    Protection Act, 2023.

    ### Features
    - **Web Application Scanning**: Playwright-based crawler with full site analysis
    - **Windows Application Scanning**: UI Automation + Vision AI hybrid approach
    - **Detection Modules**: Privacy notice, consent, dark patterns, children data, rights
    - **Interactive Dashboard**: Real-time progress, evidence gallery, trend analysis
    - **Compliance Reports**: PDF/Excel with remediation guidance

    ### DPDP Compliance Checks
    - Section 5: Privacy Notice
    - Section 6: Consent Mechanism
    - Section 6(6): Withdrawal Mechanism
    - Section 9: Children's Data
    - Sections 11-14: Data Principal Rights
    - Dark Patterns: All known patterns

    Developed by **Oryggi Technologies Pvt. Ltd.** for **NIC, Government of India**
    """,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/api/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
