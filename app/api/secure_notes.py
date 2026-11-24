"""Захищені службові примітки: POST, GET і (варіант 3) список метаданих."""
import inspect
import importlib
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from app.repositories.secure_note_repository import secure_note_repository as repo
from app.schemas.secure_note import (
    NoteCreate, SecureNoteCreated, SecureNoteMeta, SecureNoteRead,
)
from app.security import keys
from app.security.adapters import CiphertextError, open_bytes, seal_bytes
from app.security.context import note_aad
from app.security.profiles import (
    ALGORITHMS, BACKENDS, DEFAULT_BACKEND, ENVELOPE_VERSION, NONCE_BYTES,
    NOTE_ALGORITHM, TAG_BYTES,
)

UNAVAILABLE = "Protected note unavailable"

router = APIRouter(prefix="/students/{student_id}/secure-notes", tags=["secure-notes"])


# --------------------------------------------------------------------------
# Перевірка існування студента (репозиторій з практичної роботи 1).
# Якщо автопошук не підходить до вашого коду, замініть ТІЛО student_exists()
# одним викликом вашого репозиторію, напр.: return student_repository.get(student_id) is not None
# --------------------------------------------------------------------------
_REPO_MODULES = ("app.repositories.student_repository", "app.api.students")
_GETTERS = ("get", "get_by_id", "get_student", "find_by_id", "find", "read")


def _find_student_getters():
    for module_name in _REPO_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        for _, obj in vars(module).items():
            if inspect.ismodule(obj) or inspect.isclass(obj):
                continue
            if "repositor" in type(obj).__name__.lower() or "repositor" in getattr(obj, "__name__", "").lower():
                for name in _GETTERS:
                    getter = getattr(obj, name, None)
                    if callable(getter):
                        yield getter
        for name in ("get_student", "get_student_by_id"):
            func = getattr(module, name, None)
            if inspect.isfunction(func):
                yield func


def student_exists(student_id: UUID) -> bool:
    for getter in _find_student_getters():
        for candidate in (student_id, str(student_id)):
            try:
                result = getter(candidate)
            except (KeyError, LookupError, HTTPException):
                return False
            except TypeError:
                continue
            return result is not None
    raise RuntimeError(
        "Не знайдено репозиторій студентів: змініть student_exists() у app/api/secure_notes.py"
    )


def _require_student(student_id: UUID) -> None:
    if not student_exists(student_id):
        raise HTTPException(status_code=404, detail="Student not found")


def _open_envelope(student_id: UUID, note_id: UUID, envelope: dict) -> str:
    """Перевіряє конверт і розшифровує; будь-яка помилка -> ValueError/CiphertextError."""
    if envelope["version"] != ENVELOPE_VERSION:
        raise ValueError("Unsupported envelope version")
    algorithm = envelope["algorithm"]
    if algorithm not in ALGORITHMS or envelope["backend"] not in BACKENDS:
        raise ValueError("Unsupported algorithm or backend")
    nonce, tag, ciphertext = envelope["nonce"], envelope["tag"], envelope["ciphertext"]
    if not (isinstance(nonce, bytes) and len(nonce) == NONCE_BYTES):
        raise ValueError("Invalid nonce")
    if not (isinstance(tag, bytes) and len(tag) == TAG_BYTES):
        raise ValueError("Invalid tag")
    if not isinstance(ciphertext, bytes):
        raise ValueError("Invalid ciphertext")
    key = keys.get_key_store().lookup(envelope["key_id"])
    if key is None:
        raise ValueError("Unknown key")
    # Контекст відновлюється із запиту, а не з конверта.
    aad = note_aad(student_id, note_id, algorithm, envelope["key_id"])
    plaintext = open_bytes(envelope["backend"], algorithm, key, nonce, ciphertext, tag, aad)
    return plaintext.decode("utf-8")  # лише після успішної перевірки тега


@router.post("", status_code=201, response_model=SecureNoteCreated,
             responses={404: {"description": "Student not found"},
                        503: {"description": "Key usage limit reached"}})
def create_secure_note(student_id: UUID, payload: NoteCreate):
    _require_student(student_id)
    store = keys.get_key_store()
    note_id = uuid4()
    try:
        nonce = store.nonce_sequence.next()  # резервується до шифрування
    except RuntimeError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    aad = note_aad(student_id, note_id, NOTE_ALGORITHM, store.key_id)
    ciphertext, tag = seal_bytes(
        DEFAULT_BACKEND, NOTE_ALGORITHM, store.key, nonce,
        payload.text.encode("utf-8"), aad,
    )
    repo.add({
        "version": ENVELOPE_VERSION,
        "student_id": student_id,
        "note_id": note_id,
        "algorithm": NOTE_ALGORITHM,
        "backend": DEFAULT_BACKEND,
        "key_id": store.key_id,
        "nonce": nonce,
        "ciphertext": ciphertext,
        "tag": tag,
    })
    return SecureNoteCreated(id=note_id, student_id=student_id, algorithm=NOTE_ALGORITHM)


# Варіант 3: список метаданих приміток студента (без text та конверта).
@router.get("", response_model=list[SecureNoteMeta],
            responses={404: {"description": "Student not found"}})
def list_secure_notes(student_id: UUID):
    _require_student(student_id)
    return [
        SecureNoteMeta(id=e["note_id"], student_id=e["student_id"], algorithm=e["algorithm"])
        for e in repo.list_for_student(student_id)
    ]


@router.get("/{note_id}", response_model=SecureNoteRead,
            responses={404: {"description": "Student or note not found"},
                       500: {"description": "Protected note unavailable"}})
def read_secure_note(student_id: UUID, note_id: UUID):
    _require_student(student_id)
    envelope = repo.get(student_id, note_id)
    if envelope is None:
        raise HTTPException(status_code=404, detail="Secure note not found")
    try:
        text = _open_envelope(student_id, note_id, envelope)
    except (CiphertextError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=500, detail=UNAVAILABLE)
    return SecureNoteRead(id=note_id, student_id=student_id,
                          algorithm=envelope["algorithm"], text=text)
