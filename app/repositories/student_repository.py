from uuid import UUID, uuid4
from app.schemas.student import StudentCreate, StudentUpdate


class DuplicateEmailError(Exception):
    pass


class StudentRepository:
    def __init__(self) -> None:
        self._students: dict[UUID, dict] = {}

    def clear(self) -> None:
        self._students.clear()

    def _ensure_unique_email(self, email: str, exclude_id: UUID | None = None) -> None:
        normalized = email.casefold()
        for student_id, student in self._students.items():
            if student_id != exclude_id and student["email"].casefold() == normalized:
                raise DuplicateEmailError

    def create(self, data: StudentCreate) -> dict:
        values = data.model_dump(mode="json")
        self._ensure_unique_email(values["email"])
        student = {"id": uuid4(), **values}
        self._students[student["id"]] = student
        return student.copy()

    def list(self, academic_status: str | None = None) -> list[dict]:
        values = list(self._students.values())
        if academic_status is not None:
            values = [s for s in values if s["academic_status"] == academic_status]
        return [s.copy() for s in values]

    def get(self, student_id: UUID) -> dict | None:
        student = self._students.get(student_id)
        return student.copy() if student else None

    def update(self, student_id: UUID, data: StudentUpdate) -> dict | None:
        current = self._students.get(student_id)
        if current is None:
            return None
        changes = data.model_dump(exclude_unset=True, mode="json")
        if "email" in changes and changes["email"] is not None:
            self._ensure_unique_email(changes["email"], exclude_id=student_id)
        updated = {**current, **changes}
        self._students[student_id] = updated
        return updated.copy()


student_repository = StudentRepository()
