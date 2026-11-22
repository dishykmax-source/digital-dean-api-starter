import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.student_repository import student_repository


@pytest.fixture
def client():
    student_repository.clear()
    with TestClient(app) as test_client:
        yield test_client
    student_repository.clear()


@pytest.fixture
def student_payload():
    return {
        "full_name": "Олена Коваль",
        "email": "olena.koval@example.com",
        "group_code": "КН-31",
        "academic_status": "active",
    }
