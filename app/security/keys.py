"""Ключ приміток: створюється один раз на життєвий цикл процесу.

Ключ існує лише в пам'яті, не потрапляє в API, журнали чи файли.
Після перезапуску створюється новий ключ і нова послідовність nonce.
"""
import secrets
import uuid
from dataclasses import dataclass, field

from app.security.nonce import NonceSequence
from app.security.profiles import KEY_BYTES, NOTE_ALGORITHM


@dataclass
class KeyStore:
    algorithm: str
    key_id: uuid.UUID
    key: bytes = field(repr=False)
    nonce_sequence: NonceSequence = field(repr=False)

    def lookup(self, key_id):
        """Повертає ключ лише для відомого key_id, інакше None."""
        try:
            if uuid.UUID(str(key_id)) == self.key_id:
                return self.key
        except ValueError:
            pass
        return None


def create_key_store(limit: int = 1_000_000) -> KeyStore:
    return KeyStore(
        algorithm=NOTE_ALGORITHM,
        key_id=uuid.uuid4(),
        key=secrets.token_bytes(KEY_BYTES[NOTE_ALGORITHM]),
        nonce_sequence=NonceSequence(limit=limit),
    )


_key_store = create_key_store()


def get_key_store() -> KeyStore:
    return _key_store


def reset_key_store(limit: int = 1_000_000) -> KeyStore:
    """Лише для тестів: новий ключ і новий лічильник."""
    global _key_store
    _key_store = create_key_store(limit=limit)
    return _key_store
