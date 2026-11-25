from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.constants.messages import DATABASE_UNAVAILABLE
from app.core.exceptions import ServiceUnavailableException
from app.dependencies.database import DbSession

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/database")
async def check_database(
    session: DbSession,
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise ServiceUnavailableException(DATABASE_UNAVAILABLE) from exc

    return {
        "status": "ok",
        "database": "connected",
    }
