from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.db.session import get_db
from app.domain.enums import WorkspaceRole
from app.main import app
from app.models import Project, User, Workspace, WorkspaceMember


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
async def task_client(
    db_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    previous_overrides = app.dependency_overrides.copy()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


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
