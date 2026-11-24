"""Cryptographic profiles for Practice 03."""
from dataclasses import dataclass

CONTEXT = b"digital-dean:practice-03:report-v1"
SIZES = (64, 1024, 65536, 1048576)

@dataclass(frozen=True)
class Profile:
    id: str
    kind: str
    key_bits: int | None = None
    kem: str | None = None
    enc_bytes: int = 0

PROFILES = {
    "rsa2048-oaep": Profile("rsa2048-oaep", "direct", 2048),
    "rsa3072-oaep": Profile("rsa3072-oaep", "direct", 3072),
    "rsa3072-oaep-aes256gcm": Profile("rsa3072-oaep-aes256gcm", "hybrid", 3072),
    "hpke-x25519-aes256gcm": Profile("hpke-x25519-aes256gcm", "hybrid", kem="x25519", enc_bytes=32),
    "hpke-p256-aes256gcm": Profile("hpke-p256-aes256gcm", "hybrid", kem="p256", enc_bytes=65),
}

def oaep_max_bytes(key_bits: int) -> int:
    if key_bits not in (2048, 3072):
        raise ValueError("unsupported RSA key size")
    return key_bits // 8 - 2 * 32 - 2
