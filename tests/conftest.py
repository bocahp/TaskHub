from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.dependencies.task import get_task_repository
from app.main import app
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
