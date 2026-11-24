"""Модульні перевірки криптографічного шару (таблиця 6, сценарії 1-8)."""
import json
import threading
from secrets import token_bytes

import pytest

from app.security.adapters import CiphertextError, open_bytes, seal_bytes
from app.security.context import note_aad
from app.security.nonce import NonceSequence
from app.security.profiles import BACKENDS, COMBINATIONS, KEY_BYTES, validate_profile

COMBO = pytest.mark.parametrize("backend,algorithm", COMBINATIONS)
AAD = b"practice-02-test"


def fresh(algorithm):
    return token_bytes(KEY_BYTES[algorithm]), token_bytes(12)


@COMBO
@pytest.mark.parametrize("data", [b"", b"x", "Привіт, світе".encode("utf-8"), token_bytes(70000)], ids=["empty", "one-byte", "utf8", "large-70kb"])
def test_exact_roundtrip(backend, algorithm, data):
    key, nonce = fresh(algorithm)
    ct, tag = seal_bytes(backend, algorithm, key, nonce, data, AAD)
    assert len(ct) == len(data) and len(tag) == 16
    assert open_bytes(backend, algorithm, key, nonce, ct, tag, AAD) == data


@COMBO
def test_tampered_ciphertext(backend, algorithm):
    key, nonce = fresh(algorithm)
    ct, tag = seal_bytes(backend, algorithm, key, nonce, b"demo", AAD)
    changed = bytes([ct[0] ^ 1]) + ct[1:]
    with pytest.raises(CiphertextError):
        open_bytes(backend, algorithm, key, nonce, changed, tag, AAD)


@COMBO
def test_tampered_tag(backend, algorithm):
    key, nonce = fresh(algorithm)
    ct, tag = seal_bytes(backend, algorithm, key, nonce, b"demo", AAD)
    with pytest.raises(CiphertextError):
        open_bytes(backend, algorithm, key, nonce, ct, bytes([tag[0] ^ 1]) + tag[1:], AAD)


@COMBO
def test_truncated_tag_rejected(backend, algorithm):
    key, nonce = fresh(algorithm)
    ct, tag = seal_bytes(backend, algorithm, key, nonce, b"demo", AAD)
    with pytest.raises(CiphertextError):
        open_bytes(backend, algorithm, key, nonce, ct, tag[:-1], AAD)


@COMBO
def test_tampered_aad(backend, algorithm):
    key, nonce = fresh(algorithm)
    ct, tag = seal_bytes(backend, algorithm, key, nonce, b"demo", AAD)
    with pytest.raises(CiphertextError):
        open_bytes(backend, algorithm, key, nonce, ct, tag, AAD + b"!")


@COMBO
def test_wrong_key_same_length(backend, algorithm):
    key, nonce = fresh(algorithm)
    other_key = token_bytes(len(key))
    ct, tag = seal_bytes(backend, algorithm, key, nonce, b"demo", AAD)
    with pytest.raises(CiphertextError):
        open_bytes(backend, algorithm, other_key, nonce, ct, tag, AAD)


@COMBO
def test_wrong_key_length_is_separate_error(backend, algorithm):
    key, nonce = fresh(algorithm)
    with pytest.raises(ValueError):
        seal_bytes(backend, algorithm, key[:-1], nonce, b"demo", AAD)


@COMBO
def test_different_nonce_rejected(backend, algorithm):
    key, nonce = fresh(algorithm)
    ct, tag = seal_bytes(backend, algorithm, key, nonce, b"demo", AAD)
    other = bytes([nonce[0] ^ 1]) + nonce[1:]
    with pytest.raises(CiphertextError):
        open_bytes(backend, algorithm, key, other, ct, tag, AAD)


@pytest.mark.parametrize("algorithm", list(KEY_BYTES))
@pytest.mark.parametrize("sealer,opener", [(BACKENDS[0], BACKENDS[1]), (BACKENDS[1], BACKENDS[0])])
def test_cross_library_compatibility(algorithm, sealer, opener):
    key, nonce = fresh(algorithm)  # нова пара для кожного напряму
    data = "Міжбібліотечна перевірка".encode()
    ct, tag = seal_bytes(sealer, algorithm, key, nonce, data, AAD)
    assert open_bytes(opener, algorithm, key, nonce, ct, tag, AAD) == data


def test_profile_validation_rejects_bad_parameters():
    key, nonce = fresh("AES-256-GCM")
    with pytest.raises(ValueError):
        validate_profile("AES-512-GCM", key, nonce)
    with pytest.raises(ValueError):
        validate_profile("AES-256-GCM", key, nonce[:-1])
    with pytest.raises(ValueError):
        seal_bytes("unknown-lib", "AES-256-GCM", key, nonce, b"x", AAD)


def test_nonce_sequence_unique_and_ordered():
    seq = NonceSequence()
    values = [seq.next() for _ in range(5)]
    assert all(len(v) == 12 for v in values)
    assert values == [i.to_bytes(12, "big") for i in range(5)]


def test_nonce_sequence_limit_does_not_reset():
    seq = NonceSequence(limit=2)
    seq.next(); seq.next()
    with pytest.raises(RuntimeError):
        seq.next()
    with pytest.raises(RuntimeError):
        seq.next()


def test_nonce_sequence_threaded_no_duplicates():
    seq, bucket = NonceSequence(), []

    def work():
        local = [seq.next() for _ in range(500)]
        bucket.extend(local)

    threads = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(bucket) == 4000 and len(set(bucket)) == 4000


def test_note_aad_is_canonical_and_binds_fields():
    a = note_aad("11111111-1111-4111-8111-111111111111",
                 "22222222-2222-4222-8222-222222222222", "AES-256-GCM",
                 "33333333-3333-4333-8333-333333333333")
    assert json.loads(a)["version"] == 1
    assert a == note_aad("11111111-1111-4111-8111-111111111111",
                         "22222222-2222-4222-8222-222222222222", "AES-256-GCM",
                         "33333333-3333-4333-8333-333333333333")
    assert a != note_aad("11111111-1111-4111-8111-111111111112",
                         "22222222-2222-4222-8222-222222222222", "AES-256-GCM",
                         "33333333-3333-4333-8333-333333333333")
