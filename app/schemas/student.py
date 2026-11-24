from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AcademicStatus(str, Enum):
    ACTIVE = "active"
    ACADEMIC_LEAVE = "academic_leave"
    EXPELLED = "expelled"
    GRADUATED = "graduated"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudentCreate(StrictModel):
    full_name: str = Field(min_length=5, max_length=120)
    email: EmailStr
    group_code: str = Field(pattern=r"^[A-Za-zА-Яа-яІіЇїЄєҐґ]+-[0-9]{2}$")
    academic_status: AcademicStatus


class StudentRead(StrictModel):
    id: UUID
    full_name: str
    email: EmailStr
    group_code: str
    academic_status: AcademicStatus


class StudentUpdate(StrictModel):
    full_name: str = Field(default=None, min_length=5, max_length=120)
    email: EmailStr = None
    group_code: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яІіЇїЄєҐґ]+-[0-9]{2}$")
    academic_status: AcademicStatus = None
