from collections.abc import AsyncIterator, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.dependencies.task import get_task_repository
from app.domain.enums import WorkspaceRole
from app.main import app
from app.models import Project, User, Workspace, WorkspaceMember
from app.repositories.task import InMemoryTaskRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    repository = InMemoryTaskRepository()

    app.dependency_overrides[get_task_repository] = lambda: repository

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_session(anyio_backend: str) -> AsyncIterator[AsyncSession]:
    if settings.test_database_url is None:
        pytest.fail("TEST_DATABASE_URL must be configured")

    engine = create_async_engine(
        settings.test_database_url,
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()

            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )

            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def task_context(
    db_session: AsyncSession,
) -> tuple[UUID, UUID]:
    user = User(
        email=f"{uuid4().hex}@example.test",
        full_name="Test User",
        hashed_password="test-password-hash",
    )

    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        name=f"Test Workspace {uuid4().hex[:8]}",
        owner_id=user.id,
    )

    db_session.add(workspace)
    await db_session.flush()

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
    )

    db_session.add(membership)
    await db_session.flush()

    project = Project(
        workspace_id=workspace.id,
        name=f"Test Project {uuid4().hex[:8]}",
    )

    db_session.add(project)
    await db_session.flush()

    return project.id, user.id
