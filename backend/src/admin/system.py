"""System information and versioning endpoints."""

from config import settings
from fastapi import APIRouter, Request

router = APIRouter(prefix="/system", tags=["admin"])


@router.get("/versions", include_in_schema=True)
async def get_system_versions(request: Request) -> dict:
    """
    Get system version information: app version, DB schema, content versions.

    Used by admin dashboard to display current system state and backup compatibility info.
    """
    try:
        # Get DB schema version
        pool = getattr(request.app.state, "pool", None)
        db_schema_version = "unknown"
        if pool is not None:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"
                )
                if row:
                    db_schema_version = row["version_num"]
    except Exception:
        db_schema_version = "error"

    return {
        "app_version": settings.APP_VERSION,
        "app_build": settings.BUILD_ID,
        "db_schema_version": db_schema_version,
        "content_structure_version": 2,
        "python_version": settings.PYTHON_VERSION if hasattr(settings, "PYTHON_VERSION") else "unknown",
        "api_environment": settings.ENV,
        "endpoints": {
            "health": "/api/v1/health/deep",
            "versions": "/api/v1/admin/system/versions",
        },
    }
