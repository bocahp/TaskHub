from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ConflictException, NotFoundException
from app.db.session import engine
from app.repositories.task import InMemoryTaskRepository
from app.routers.database import router as database_router
from app.routers.health import router as health_router
from app.routers.tasks import router as tasks_router


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

app.state.task_repository = InMemoryTaskRepository()

app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(database_router)


@app.exception_handler(NotFoundException)
async def handle_not_found(
    request: Request,
    exc: NotFoundException,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message},
    )


@app.exception_handler(ConflictException)
async def handle_conflict(
    request: Request,
    exc: ConflictException,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message},
    )
