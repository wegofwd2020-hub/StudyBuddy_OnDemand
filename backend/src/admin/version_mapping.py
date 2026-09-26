"""Version mapping: link GitHub tags to DB schema versions."""


from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/versions", tags=["admin"])


class VersionMapping(BaseModel):
    """Maps an app version (git tag) to its DB schema version."""
    app_version: str
    db_schema_version: int
    released_at: str
    notes: str | None = None


@router.get("/mapping/{app_version}", include_in_schema=True)
async def get_version_mapping(
    app_version: str, request: Request
) -> dict:
    """
    Get DB schema version for a given app version (git tag).

    Example: GET /api/v1/admin/versions/mapping/v0.2.0
    Returns: {app_version: "v0.2.0", db_schema_version: 71, released_at: "2026-09-26"}
    """
    pool = getattr(request.app.state, "pool", None)

    if pool is None:
        return {"error": "Database not available", "app_version": app_version}

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT app_version, db_schema_version, released_at, notes
                FROM version_mapping
                WHERE app_version = $1
                ORDER BY released_at DESC
                LIMIT 1
                """,
                app_version,
            )

            if row:
                return {
                    "app_version": row["app_version"],
                    "db_schema_version": row["db_schema_version"],
                    "released_at": row["released_at"],
                    "notes": row["notes"],
                    "found": True,
                }
            else:
                return {
                    "error": f"No mapping found for version {app_version}",
                    "app_version": app_version,
                    "found": False,
                }
    except Exception as e:
        return {
            "error": str(e),
            "app_version": app_version,
        }


@router.get("/mapping", include_in_schema=True)
async def list_version_mappings(request: Request) -> dict:
    """
    List all known app version → DB schema version mappings.
    Useful for determining compatibility.
    """
    pool = getattr(request.app.state, "pool", None)

    if pool is None:
        return {"error": "Database not available", "mappings": []}

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT app_version, db_schema_version, released_at, notes
                FROM version_mapping
                ORDER BY released_at DESC
                LIMIT 50
                """
            )

            return {
                "mappings": [
                    {
                        "app_version": row["app_version"],
                        "db_schema_version": row["db_schema_version"],
                        "released_at": row["released_at"],
                        "notes": row["notes"],
                    }
                    for row in rows
                ],
                "count": len(rows),
            }
    except Exception as e:
        return {
            "error": str(e),
            "mappings": [],
        }
