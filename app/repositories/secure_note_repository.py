"""Сховище зашифрованих приміток у пам'яті. Поле text не зберігається."""
from threading import Lock
from uuid import UUID

ENVELOPE_FIELDS = frozenset(
    {"version", "student_id", "note_id", "algorithm", "backend",
     "key_id", "nonce", "ciphertext", "tag"}
)


class SecureNoteRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, dict] = {}
        self._lock = Lock()

    def add(self, envelope: dict) -> None:
        if set(envelope) != ENVELOPE_FIELDS:
            raise ValueError("Envelope must contain exactly the defined fields")
        with self._lock:
            self._items[envelope["note_id"]] = dict(envelope)

    def get(self, student_id: UUID, note_id: UUID):
        """Запис повертається лише для його власного студента."""
        with self._lock:
            item = self._items.get(note_id)
            if item is None or item["student_id"] != student_id:
                return None
            return dict(item)

    def list_for_student(self, student_id: UUID) -> list[dict]:
        with self._lock:
            return [dict(i) for i in self._items.values() if i["student_id"] == student_id]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


secure_note_repository = SecureNoteRepository()
