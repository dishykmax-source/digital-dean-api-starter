"""Криптографічні профілі практичної роботи 2 (таблиця 1 методички)."""

KEY_BYTES = {
    "AES-128-GCM": 16,
    "AES-256-GCM": 32,
    "ChaCha20-Poly1305": 32,
}
NONCE_BYTES = 12
TAG_BYTES = 16

ALGORITHMS = tuple(KEY_BYTES)
BACKENDS = ("cryptography", "pycryptodome")

# Шість комбінацій «бібліотека × алгоритм»
COMBINATIONS = [(backend, algorithm) for algorithm in ALGORITHMS for backend in BACKENDS]

# Базова конфігурація приміток
NOTE_ALGORITHM = "AES-256-GCM"
DEFAULT_BACKEND = "cryptography"
ENVELOPE_VERSION = 1


def validate_profile(algorithm, key, nonce):
    if algorithm not in KEY_BYTES:
        raise ValueError("Unsupported algorithm")
    if not isinstance(key, (bytes, bytearray)) or len(key) != KEY_BYTES[algorithm]:
        raise ValueError("Invalid key length")
    if not isinstance(nonce, (bytes, bytearray)) or len(nonce) != NONCE_BYTES:
        raise ValueError("Invalid nonce length")
