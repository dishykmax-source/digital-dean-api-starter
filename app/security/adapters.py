"""Два бібліотечні адаптери AEAD з єдиним інтерфейсом seal_bytes / open_bytes.

cryptography приєднує тег до шифротексту, PyCryptodome повертає його окремо;
адаптер зводить обидва формати до пари (ciphertext, tag).
"""
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

from app.security.profiles import BACKENDS, TAG_BYTES, validate_profile


class CiphertextError(Exception):
    """Перевірка автентичності не пройдена або запис пошкоджено."""


def _check_backend(backend):
    if backend not in BACKENDS:
        raise ValueError("Unsupported backend")


def _pycryptodome_cipher(algorithm, key, nonce, is_aes):
    # Імпорт відкладено: пакет потрібен лише для комбінацій pycryptodome.
    from Crypto.Cipher import AES, ChaCha20_Poly1305

    if is_aes:
        return AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=TAG_BYTES)
    return ChaCha20_Poly1305.new(key=key, nonce=nonce)


def seal_bytes(backend, algorithm, key, nonce, data, aad):
    """Повертає (ciphertext, tag). Ключ і nonce генерує викликач."""
    validate_profile(algorithm, key, nonce)
    _check_backend(backend)
    is_aes = algorithm.startswith("AES-")
    if backend == "cryptography":
        factory = AESGCM if is_aes else ChaCha20Poly1305
        combined = factory(key).encrypt(nonce, data, aad)
        return combined[:-TAG_BYTES], combined[-TAG_BYTES:]
    cipher = _pycryptodome_cipher(algorithm, key, nonce, is_aes)
    cipher.update(aad)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return bytes(ciphertext), bytes(tag)


def open_bytes(backend, algorithm, key, nonce, ct, tag, aad):
    """Повертає початкові байти лише після успішної перевірки тега."""
    validate_profile(algorithm, key, nonce)
    _check_backend(backend)
    if not isinstance(tag, (bytes, bytearray)) or len(tag) != TAG_BYTES:
        raise CiphertextError("Verification failed")
    is_aes = algorithm.startswith("AES-")
    try:
        if backend == "cryptography":
            factory = AESGCM if is_aes else ChaCha20Poly1305
            return factory(key).decrypt(nonce, bytes(ct) + bytes(tag), aad)
        cipher = _pycryptodome_cipher(algorithm, key, nonce, is_aes)
        cipher.update(aad)
        return bytes(cipher.decrypt_and_verify(ct, tag))
    except (InvalidTag, ValueError) as exc:
        raise CiphertextError("Verification failed") from exc
