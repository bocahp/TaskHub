from typing import Annotated
from uuid import UUID

from fastapi import Path

ProjectId = Annotated[UUID, Path()]
TaskId = Annotated[UUID, Path()]
WorkspaceId = Annotated[UUID, Path()]
UserId = Annotated[UUID, Path()]
