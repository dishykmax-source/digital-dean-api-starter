"""Library-backed RSA-OAEP, RSA/AES-GCM and RFC 9180 HPKE adapters."""
import secrets
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from app.security.asymmetric.profiles import CONTEXT, PROFILES, oaep_max_bytes

class DecryptionError(Exception):
    """Uniform failure for invalid envelopes, keys, or contexts."""


def _oaep(label=CONTEXT):
    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=label)


def generate_keypair(profile: str):
    p = PROFILES[profile]
    if p.kind in ("direct", "hybrid") and p.key_bits:
        return rsa.generate_private_key(public_exponent=65537, key_size=p.key_bits)
    if p.kem == "x25519":
        return x25519.X25519PrivateKey.generate()
    if p.kem == "p256":
        return ec.generate_private_key(ec.SECP256R1())
    raise ValueError("Unknown profile")


def _hpke_suite(profile):
    try:
        from cryptography.hazmat.primitives.hpke import Suite, KEM, KDF, AEAD
    except ImportError as exc:
        raise RuntimeError("HPKE requires cryptography==48.0.1") from exc
    kem = KEM.X25519 if PROFILES[profile].kem == "x25519" else KEM.P256
    return Suite(kem, KDF.HKDF_SHA256, AEAD.AES_256_GCM)


def encrypt(profile: str, public_key, plaintext: bytes, context: bytes = CONTEXT) -> bytes:
    p = PROFILES[profile]
    if not isinstance(plaintext, bytes):
        raise TypeError("plaintext must be bytes")
    if p.kind == "direct":
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size != p.key_bits:
            raise ValueError("wrong public key for profile")
        return public_key.encrypt(plaintext, _oaep(context))
    if profile == "rsa3072-oaep-aes256gcm":
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size != 3072:
            raise ValueError("RSA-3072 public key required")
        key, nonce = AESGCM.generate_key(bit_length=256), secrets.token_bytes(12)
        wrapped = public_key.encrypt(key, _oaep(context))
        return wrapped + nonce + AESGCM(key).encrypt(nonce, plaintext, context)
    if p.kem:
        return _hpke_suite(profile).encrypt(plaintext, public_key, info=context)
    raise ValueError("Unknown profile")


def decrypt(profile: str, private_key, envelope: bytes, context: bytes = CONTEXT) -> bytes:
    p = PROFILES[profile]
    try:
        if not isinstance(envelope, bytes):
            raise ValueError("invalid envelope")
        if p.kind == "direct":
            if not isinstance(private_key, rsa.RSAPrivateKey) or private_key.key_size != p.key_bits or len(envelope) != p.key_bits // 8:
                raise ValueError("invalid RSA envelope")
            return private_key.decrypt(envelope, _oaep(context))
        if profile == "rsa3072-oaep-aes256gcm":
            if not isinstance(private_key, rsa.RSAPrivateKey) or private_key.key_size != 3072 or len(envelope) < 412:
                raise ValueError("invalid hybrid envelope")
            key = private_key.decrypt(envelope[:384], _oaep(context))
            if len(key) != 32:
                raise ValueError("invalid wrapped key")
            return AESGCM(key).decrypt(envelope[384:396], envelope[396:], context)
        if p.kem:
            return _hpke_suite(profile).decrypt(envelope, private_key, info=context)
        raise ValueError("unknown profile")
    except Exception as exc:
        if isinstance(exc, DecryptionError):
            raise
        raise DecryptionError("Decryption failed") from exc


def ciphertext_size(profile: str, payload_bytes: int) -> int:
    p = PROFILES[profile]
    return {"rsa2048-oaep": 256, "rsa3072-oaep": 384,
            "rsa3072-oaep-aes256gcm": payload_bytes + 412,
            "hpke-x25519-aes256gcm": payload_bytes + 48,
            "hpke-p256-aes256gcm": payload_bytes + 81}[profile]
