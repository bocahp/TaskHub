from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.db.session import engine
from app.routers.auth import router as auth_router
from app.routers.database import router as database_router
from app.routers.health import router as health_router
from app.routers.tasks import router as tasks_router
from app.routers.users import router as users_router
from app.routers.workspaces import router as workspaces_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title="TaskHub API",
    description="Task Management API built with FastAPI",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(workspaces_router)
app.include_router(tasks_router)
app.include_router(database_router)


@app.exception_handler(AppException)
async def handle_app_exception(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
        headers=headers,
    )
