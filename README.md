# TaskHub - Task Management API

TaskHub is a task management backend application built with FastAPI as part of the Python Tech Stack module.

## 1. Tech Stack

- Python 3.14
- FastAPI
- Pydantic v2
- Uvicorn
- Pytest
- HTTPX
- Ruff
- Mypy

## 2. Project Structure

```text
FastAPIProject/
│
├── app/
│   ├── constants/
│   ├── core/
│   ├── dependencies/
│   ├── domain/
│   ├── repositories/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── main.py
│
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_tasks.py
│
├── .gitignore
├── README.md
└── pyproject.toml
```

## 3. Setup

### Create Virtual Environment

```powershell
python -m venv .venv
```

### Activate Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies

```powershell
python -m pip install -e ".[dev]"
```

## 4. Run Application

Start the FastAPI development server:

```powershell
uvicorn app.main:app --reload
```

The application will run at:

```text
http://127.0.0.1:8000
```

## 5. API Documentation

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health Check: http://127.0.0.1:8000/health

## 6. Task API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/v1/tasks | Create a new task |
| GET | /api/v1/tasks | Retrieve all tasks |
| GET | /api/v1/tasks/{task_id} | Retrieve a task by ID |
| PATCH | /api/v1/tasks/{task_id} | Update a task |
| DELETE | /api/v1/tasks/{task_id} | Delete a task |

## 7. Testing

Run automated tests:

```powershell
pytest -v
```

Run code quality checks:

```powershell
ruff check .
ruff format --check .
mypy app
```

## 8. Current Implementation

- FastAPI application initialization.
- APIRouter for API organization.
- Health Check endpoint.
- Layered Architecture.
- Pydantic v2 request and response schemas.
- Task CRUD operations.
- Dependency Injection.
- Custom exception handling.
- In-memory Task Repository.
- Automated API tests.
- Input validation for PATCH requests.

## 9. Testing Results

- Pytest: 8 tests passed.
- Ruff Check: All checks passed.
- Ruff Format: All files formatted.
- Mypy: No issues found.

## 10. Development Progress

| Day     | Topic                              | Status |
|---------|------------------------------------|---------|
| Day 1   | Core Setup & Architecture          | Completed |
| Day 2   | Database: SQLAlchemy 2.x & Alembic | Pending |
| Day 3-7 | Business Logic & Core Features     | Pending |
| Day 8   | Review, Refactor & Optimization    | Pending |

## 11. Notes

The current implementation uses an in-memory repository for task storage. Data is not persistent and will be lost when the application restarts.

Database integration using SQLAlchemy 2.x Async, PostgreSQL, and Alembic will be implemented in the next development phase.