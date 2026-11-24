from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from app.repositories.student_repository import student_repository, DuplicateEmailError
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate, AcademicStatus

router = APIRouter(prefix="/api/v1/students", tags=["students"])


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate):
    try:
        return student_repository.create(payload)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already exists")


@router.get("", response_model=list[StudentRead])
def list_students(academic_status: AcademicStatus | None = Query(default=None)):
    return student_repository.list(academic_status.value if academic_status else None)


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: UUID):
    student = student_repository.get(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentRead)
def update_student(student_id: UUID, payload: StudentUpdate):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Empty update is not allowed")
    try:
        student = student_repository.update(student_id, payload)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already exists")
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
