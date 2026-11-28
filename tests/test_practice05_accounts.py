import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.connection import database, write_transaction
from app.db.initialize import initialize_database
from app.repositories.user_repository import UserRepository, UserNotFoundError, UserHasGradesError
from app.security.passwords import make_password_record, verify_password, ITERATIONS
from app.api.accounts import get_user_repository

PASSWORD = "Learning only practice 05!"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.sqlite3"
    initialize_database(path)
    return path


@pytest.fixture
def repository(db_path):
    return UserRepository(db_path)


def user_payload(login="demo_student", email="demo.student@example.com", status_id=1):
    return {"name": "Навчальний користувач", "email": email, "login": login,
            "password": PASSWORD, "status_id": status_id}


def create_user(repository, **kwargs):
    from app.schemas.user_account import UserCreate
    return repository.register_user(UserCreate.model_validate(user_payload(**kwargs)))


def test_initialize_is_repeatable_and_enables_foreign_keys(db_path):
    initialize_database(db_path)
    with database(db_path) as con:
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM status").fetchone()[0] == 3
        assert con.execute("SELECT count(*) FROM role").fetchone()[0] == 4
        assert {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")} >= {
            "status", "user", "role", "user_role", "course", "grade"}


def test_password_profile_unicode_and_random_salt():
    record1, salt1 = make_password_record("  Навчальний пароль 05!  ")
    record2, salt2 = make_password_record("  Навчальний пароль 05!  ")
    assert record1.startswith(f"pbkdf2_sha256${ITERATIONS}$")
    assert salt1 != salt2 and record1 != record2
    assert verify_password("  Навчальний пароль 05!  ", record1, salt1)
    assert not verify_password("Навчальний пароль 05!", record1, salt1)
    assert not verify_password("wrong", "pbkdf2_sha256$999999999$" + "0" * 64, salt1)
    assert not verify_password("wrong", record1, "not-hex")


def test_registration_defaults_inactive_and_login_checks_status(repository):
    from app.schemas.user_account import UserCreate
    inactive = repository.register_user(UserCreate.model_validate(user_payload(status_id=0)))
    assert inactive["status_id"] == 0
    assert repository.login("demo_student", PASSWORD) is False
    active = create_user(repository, login="active_user", email="active@example.com")
    assert active["status_id"] == 1
    assert repository.login("active_user", PASSWORD) is True
    assert repository.login("active_user", "incorrect password") is False
    assert repository.login("unknown", PASSWORD) is False


def test_block_is_idempotent_and_preserves_login_data(repository, db_path):
    user = create_user(repository)
    before = None
    with database(db_path) as con:
        before = tuple(con.execute('SELECT password,salt,name,email,login FROM "user" WHERE id=?', (user["id"],)).fetchone())
    blocked = repository.block_user(user["id"])
    assert blocked["status_id"] == 2
    assert repository.block_user(user["id"])["status_id"] == 2
    assert repository.login(user["login"], PASSWORD) is False
    with database(db_path) as con:
        after = tuple(con.execute('SELECT password,salt,name,email,login FROM "user" WHERE id=?', (user["id"],)).fetchone())
    assert before == after


def test_delete_not_found_and_grade_conflict_rolls_back(repository, db_path):
    user = create_user(repository)
    teacher = create_user(repository, login="teacher01", email="teacher@example.com")
    with database(db_path) as con, write_transaction(con):
        con.execute("INSERT INTO course(id,name) VALUES (?,?)", (10, "Test course"))
        con.execute("INSERT INTO user_role(user_id,role_id) VALUES (?,?)", (user["id"], 4))
        con.execute("INSERT INTO grade(student_id,teacher_id,course_id,grade) VALUES (?,?,?,?)",
                    (user["id"], teacher["id"], 10, 95))
    with pytest.raises(UserHasGradesError):
        repository.delete_user(user["id"])
    with database(db_path) as con:
        assert con.execute('SELECT 1 FROM "user" WHERE id=?', (user["id"],)).fetchone()
        assert con.execute("SELECT 1 FROM user_role WHERE user_id=?", (user["id"],)).fetchone()
        assert con.execute("SELECT 1 FROM grade WHERE student_id=?", (user["id"],)).fetchone()
    repository.delete_user(teacher["id"]) if False else None
    with pytest.raises(UserNotFoundError):
        repository.delete_user(9999)


def test_delete_cascades_roles_when_no_grade(repository, db_path):
    user = create_user(repository)
    with database(db_path) as con, write_transaction(con):
        con.execute("INSERT INTO user_role(user_id,role_id) VALUES (?,?)", (user["id"], 4))
    repository.delete_user(user["id"])
    with database(db_path) as con:
        assert con.execute('SELECT 1 FROM "user" WHERE id=?', (user["id"],)).fetchone() is None
        assert con.execute("SELECT 1 FROM user_role WHERE user_id=?", (user["id"],)).fetchone() is None


def test_api_contract_and_safe_public_response(tmp_path):
    path = tmp_path / "api.sqlite3"
    initialize_database(path)
    test_repo = UserRepository(path)
    app.dependency_overrides[get_user_repository] = lambda: test_repo
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/users", json=user_payload())
            assert created.status_code == 201
            body = created.json()
            assert set(body) == {"id", "name", "email", "login", "status_id"}
            assert client.post("/api/v1/auth/login", json={"login":"demo_student", "password":PASSWORD}).json() is True
            assert client.patch(f"/api/v1/users/{body['id']}/block").json()["status_id"] == 2
            assert client.post("/api/v1/auth/login", json={"login":"demo_student", "password":PASSWORD}).json() is False
            deleted = client.delete(f"/api/v1/users/{body['id']}")
            assert deleted.status_code == 204 and deleted.content == b""
            assert client.delete(f"/api/v1/users/{body['id']}").status_code == 404
            bad = client.post("/api/v1/users", json={**user_payload(login="other_user", email="other@example.com"), "role_id":1})
            assert bad.status_code == 422
            assert "password" not in bad.text and PASSWORD not in bad.text
    finally:
        app.dependency_overrides.clear()



def test_password_record_matches_fixed_pbkdf2_profile(monkeypatch):
    import hashlib
    import app.security.passwords as passwords

    fixed_salt = bytes(range(16))
    monkeypatch.setattr(passwords.secrets, "token_bytes", lambda size: fixed_salt)
    raw = "  Exact Unicode пароль 05!  "
    record, salt_hex = passwords.make_password_record(raw)
    expected = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), fixed_salt, 600_000, dklen=32)
    assert salt_hex == fixed_salt.hex()
    assert record == f"pbkdf2_sha256$600000${expected.hex()}"


def test_password_profile_rejects_malformed_parameters_before_kdf(monkeypatch):
    import app.security.passwords as passwords

    def forbidden(*args, **kwargs):
        raise AssertionError("PBKDF2 must not run for malformed records")

    monkeypatch.setattr(passwords.hashlib, "pbkdf2_hmac", forbidden)
    assert not passwords.verify_password("candidate", "md5$600000$" + "0" * 64, "0" * 32)
    assert not passwords.verify_password("candidate", "pbkdf2_sha256$999999999$" + "0" * 64, "0" * 32)
    assert not passwords.verify_password("candidate", "pbkdf2_sha256$600000$xyz", "0" * 32)
    assert not passwords.verify_password("candidate", "pbkdf2_sha256$600000$" + "0" * 64, "z" * 32)


def test_sqlite_constraints_reject_invalid_relations_and_duplicate_pairs(repository, db_path):
    student = create_user(repository, login="student_sql", email="student.sql@example.com")
    teacher = create_user(repository, login="teacher_sql", email="teacher.sql@example.com")
    with database(db_path) as con:
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO grade(student_id,teacher_id,course_id,grade) VALUES (?,?,?,?)",
                        (student["id"], teacher["id"], 999, 90))
        con.execute("INSERT INTO course(id,name) VALUES (?,?)", (20, "Databases"))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO grade(student_id,teacher_id,course_id,grade) VALUES (?,?,?,?)",
                        (student["id"], teacher["id"], 20, 101))
        con.execute("INSERT INTO grade(student_id,teacher_id,course_id,grade) VALUES (?,?,?,?)",
                    (student["id"], teacher["id"], 20, 90))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO grade(student_id,teacher_id,course_id,grade) VALUES (?,?,?,?)",
                        (student["id"], teacher["id"], 20, 91))
        con.execute("INSERT INTO user_role(user_id,role_id) VALUES (?,?)", (student["id"], 4))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO user_role(user_id,role_id) VALUES (?,?)", (student["id"], 4))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO user_role(user_id,role_id) VALUES (?,?)", (student["id"], 999))


def test_delete_teacher_with_grade_is_conflict_and_keeps_all_rows(repository, db_path):
    student = create_user(repository, login="student_ref", email="student.ref@example.com")
    teacher = create_user(repository, login="teacher_ref", email="teacher.ref@example.com")
    with database(db_path) as con, write_transaction(con):
        con.execute("INSERT INTO course(id,name) VALUES (?,?)", (30, "Security"))
        con.execute("INSERT INTO grade(student_id,teacher_id,course_id,grade) VALUES (?,?,?,?)",
                    (student["id"], teacher["id"], 30, 88))
    with pytest.raises(UserHasGradesError):
        repository.delete_user(teacher["id"])
    with database(db_path) as con:
        assert con.execute('SELECT 1 FROM "user" WHERE id=?', (teacher["id"],)).fetchone()
        assert con.execute("SELECT 1 FROM grade WHERE teacher_id=?", (teacher["id"],)).fetchone()


def test_api_duplicate_conflicts_and_invalid_payload_are_sanitized(tmp_path):
    path = tmp_path / "api-errors.sqlite3"
    initialize_database(path)
    test_repo = UserRepository(path)
    app.dependency_overrides[get_user_repository] = lambda: test_repo
    try:
        with TestClient(app) as client:
            first = client.post("/api/v1/users", json=user_payload())
            assert first.status_code == 201
            duplicate_login = client.post("/api/v1/users", json=user_payload(email="different@example.com"))
            assert duplicate_login.status_code == 409
            duplicate_email = client.post("/api/v1/users", json=user_payload(login="different_login"))
            assert duplicate_email.status_code == 409
            invalid = client.post("/api/v1/users", json={**user_payload(login="valid_new"), "status_id": True})
            assert invalid.status_code == 422
            assert PASSWORD not in invalid.text
            assert "input" not in invalid.text and "ctx" not in invalid.text
            assert client.patch("/api/v1/users/9999/block").status_code == 404
            assert client.delete("/api/v1/users/9999").status_code == 404
    finally:
        app.dependency_overrides.clear()
