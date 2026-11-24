from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreate(BaseModel):
    # Без str_strip_whitespace: байти тексту мають відновлюватися точно.
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(min_length=1, max_length=4096)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty note")
        if len(value.encode("utf-8")) > 4096:
            raise ValueError("Note exceeds 4096 bytes")
        return value


class SecureNoteMeta(BaseModel):
    """Метадані примітки: без text, ключа та конверта."""
    id: UUID
    student_id: UUID
    algorithm: str


class SecureNoteCreated(SecureNoteMeta):
    pass


class SecureNoteRead(SecureNoteMeta):
    text: str
