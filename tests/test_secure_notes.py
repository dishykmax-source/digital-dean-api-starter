"""Інтеграційні перевірки приміток, звіту, варіанта 3 та регресії роботи 1."""
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import crypto_lab
from app.main import app
from app.repositories.secure_note_repository import ENVELOPE_FIELDS, secure_note_repository as repo
from app.security import keys

BASE = "/api/v1"
UNAVAILABLE = {"detail": "Protected note unavailable"}


@pytest.fixture(autouse=True)
def clean_state():
    repo.clear()
    keys.reset_key_store()
    yield
    repo.clear()


@pytest.fixture()
def client():
    return TestClient(app)


def make_student(client):
    payload = {"full_name": "Іван Петренко", "email": f"{uuid4().hex}@example.com",
               "group_code": "КН-31", "academic_status": "active"}
    response = client.post(f"{BASE}/students", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def make_note(client, student_id, text="Навчальна примітка"):
    response = client.post(f"{BASE}/students/{student_id}/secure-notes", json={"text": text})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def stored(student_id, note_id):
    return repo.get(UUID(student_id), UUID(note_id))


def test_student_lookup_integration(client):
    """Якщо тут помилка — змініть student_exists() у app/api/secure_notes.py."""
    sid = make_student(client)
    assert client.get(f"{BASE}/students/{sid}/secure-notes").status_code == 200
    assert client.get(f"{BASE}/students/{uuid4()}/secure-notes").status_code == 404


def test_create_and_read_note(client):
    sid = make_student(client)
    created = client.post(f"{BASE}/students/{sid}/secure-notes", json={"text": "  Привіт 🙂  "})
    assert created.status_code == 201
    body = created.json()
    assert set(body) == {"id", "student_id", "algorithm"}
    assert body["student_id"] == sid and body["algorithm"] == "AES-256-GCM"
    read = client.get(f"{BASE}/students/{sid}/secure-notes/{body['id']}")
    assert read.status_code == 200
    assert read.json() == {**body, "text": "  Привіт 🙂  "}


def test_internal_record_has_no_text_or_key(client):
    sid = make_student(client)
    text = "Секретна навчальна примітка про план"
    nid = make_note(client, sid, text)
    envelope = stored(sid, nid)
    assert set(envelope) == ENVELOPE_FIELDS
    assert "text" not in envelope and "key" not in envelope
    assert len(envelope["nonce"]) == 12 and len(envelope["tag"]) == 16
    assert len(envelope["ciphertext"]) == len(text.encode())
    assert text.encode() not in envelope["ciphertext"]
    key = keys.get_key_store().key
    assert all(key not in v for v in envelope.values() if isinstance(v, bytes))


def test_nonces_are_unique_across_notes(client):
    sid = make_student(client)
    nonces = {stored(sid, make_note(client, sid))["nonce"] for _ in range(5)}
    assert len(nonces) == 5


@pytest.mark.parametrize("text,status", [
    ("a" * 4096, 201), ("a" * 4097, 422), ("я" * 2048, 201), ("я" * 2049, 422),
    ("   ", 422), ("", 422),
])
def test_text_bounds(client, text, status):
    sid = make_student(client)
    assert client.post(f"{BASE}/students/{sid}/secure-notes", json={"text": text}).status_code == status


@pytest.mark.parametrize("body", [{"text": "ok", "key": "00"}, {"text": "ok", "algorithm": "x"}, {}])
def test_unknown_or_missing_fields(client, body):
    sid = make_student(client)
    assert client.post(f"{BASE}/students/{sid}/secure-notes", json=body).status_code == 422


def test_invalid_uuid_is_422(client):
    assert client.post(f"{BASE}/students/not-a-uuid/secure-notes", json={"text": "x"}).status_code == 422
    sid = make_student(client)
    assert client.get(f"{BASE}/students/{sid}/secure-notes/bad").status_code == 422


def test_unknown_student_and_note_404(client):
    assert client.post(f"{BASE}/students/{uuid4()}/secure-notes", json={"text": "x"}).status_code == 404
    sid = make_student(client)
    assert client.get(f"{BASE}/students/{sid}/secure-notes/{uuid4()}").status_code == 404


def test_note_of_another_student_is_404(client):
    a, b = make_student(client), make_student(client)
    nid = make_note(client, a)
    response = client.get(f"{BASE}/students/{b}/secure-notes/{nid}")
    assert response.status_code == 404 and "text" not in response.json()


def test_envelope_copied_to_other_student_is_rejected(client):
    a, b = make_student(client), make_student(client)
    nid = make_note(client, a, "Примітка студента A")
    copy = {**stored(a, nid), "student_id": UUID(b), "note_id": uuid4()}
    repo.add(copy)
    response = client.get(f"{BASE}/students/{b}/secure-notes/{copy['note_id']}")
    assert response.status_code == 500 and response.json() == UNAVAILABLE


def flip(value):
    return bytes([value[0] ^ 1]) + value[1:]


@pytest.mark.parametrize("change", [
    lambda e: {"ciphertext": flip(e["ciphertext"])},
    lambda e: {"tag": flip(e["tag"])},
    lambda e: {"key_id": uuid4()},
    lambda e: {"version": 2},
    lambda e: {"nonce": e["nonce"][:-1]},
    lambda e: {"backend": "evil"},
    lambda e: {"algorithm": "AES-128-GCM"},
])
def test_corrupted_envelope_gives_safe_500(client, change):
    sid = make_student(client)
    nid = make_note(client, sid, "Дані, які не можна видавати")
    envelope = stored(sid, nid)
    repo.add({**envelope, **change(envelope)})
    response = client.get(f"{BASE}/students/{sid}/secure-notes/{nid}")
    assert response.status_code == 500 and response.json() == UNAVAILABLE
    assert "Traceback" not in response.text and "Дані" not in response.text


def test_key_usage_limit_gives_503_but_old_notes_readable(client):
    keys.reset_key_store(limit=2)
    sid = make_student(client)
    first = make_note(client, sid, "перша")
    make_note(client, sid, "друга")
    blocked = client.post(f"{BASE}/students/{sid}/secure-notes", json={"text": "третя"})
    assert blocked.status_code == 503 and blocked.json() == UNAVAILABLE
    assert client.get(f"{BASE}/students/{sid}/secure-notes/{first}").json()["text"] == "перша"


def test_unknown_student_does_not_consume_nonce(client):
    keys.reset_key_store(limit=1)
    client.post(f"{BASE}/students/{uuid4()}/secure-notes", json={"text": "x"})
    make_note(client, make_student(client))  # єдине значення ще доступне


# --- Варіант 3: список метаданих приміток -----------------------------------
def test_variant3_list_metadata_only_for_target_student(client):
    a, b = make_student(client), make_student(client)
    ids = {make_note(client, a, "перша"), make_note(client, a, "друга")}
    make_note(client, b, "чужа")
    response = client.get(f"{BASE}/students/{a}/secure-notes")
    assert response.status_code == 200
    items = response.json()
    assert {i["id"] for i in items} == ids
    assert all(set(i) == {"id", "student_id", "algorithm"} and i["student_id"] == a for i in items)
    assert "перша" not in response.text and "ciphertext" not in response.text


def test_variant3_list_empty_and_unknown_student(client):
    sid = make_student(client)
    assert client.get(f"{BASE}/students/{sid}/secure-notes").json() == []
    assert client.get(f"{BASE}/students/{uuid4()}/secure-notes").status_code == 404


# --- Звіт вимірювань ----------------------------------------------------------
def sample_report():
    row = {"backend": "cryptography", "algorithm": "AES-256-GCM", "size_bytes": 1024,
           "operation": "encrypt", "series_mean_ns": [1.0] * 5, "median_ns": 1.0,
           "iqr_ns": 0.0, "throughput_mib_s": 1.0}
    return {"schema_version": 1, "run_id": "t", "environment": {}, "parameters": {}, "results": [row]}


def test_report_ok(client, tmp_path, monkeypatch):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(sample_report()), encoding="utf-8")
    monkeypatch.setattr(crypto_lab, "REPORT_PATH", path)
    response = client.get(f"{BASE}/lab/crypto/benchmark-results")
    assert response.status_code == 200 and response.json()["schema_version"] == 1


def test_report_missing_is_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(crypto_lab, "REPORT_PATH", tmp_path / "none.json")
    assert client.get(f"{BASE}/lab/crypto/benchmark-results").status_code == 404


@pytest.mark.parametrize("content", ["{not json", json.dumps({**sample_report(), "schema_version": 2})])
def test_report_invalid_is_500(client, tmp_path, monkeypatch, content):
    path = tmp_path / "report.json"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(crypto_lab, "REPORT_PATH", path)
    response = client.get(f"{BASE}/lab/crypto/benchmark-results")
    assert response.status_code == 500 and response.json() == {"detail": "Benchmark results unavailable"}


def test_benchmark_produces_36_rows_and_180_series(tmp_path):
    from benchmarks.crypto_benchmark import run_benchmark
    report = run_benchmark(tmp_path, sizes=(16, 32, 64), warmup=1, operations=3, log=lambda *_: None)
    assert report["schema_version"] == 1 and len(report["results"]) == 36
    assert all(len(r["series_mean_ns"]) == 5 for r in report["results"])
    assert len((tmp_path / "raw.csv").read_text(encoding="utf-8").splitlines()) == 181


# --- Регресія роботи 1 --------------------------------------------------------
def test_students_still_work(client):
    sid = make_student(client)
    assert client.get(f"{BASE}/students/{sid}").status_code == 200
    assert client.patch(f"{BASE}/students/{sid}", json={"group_code": "КН-32"}).status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
