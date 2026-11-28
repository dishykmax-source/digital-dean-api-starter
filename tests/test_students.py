def create(client, payload):
    return client.post("/api/v1/students", json=payload)


def test_create_and_server_uuid(client, student_payload):
    response = create(client, student_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["academic_status"] == "active"
    assert body["full_name"] == student_payload["full_name"]


def test_invalid_email_rejected(client, student_payload):
    student_payload["email"] = "not-an-email"
    assert create(client, student_payload).status_code == 422
    assert client.get("/api/v1/students").json() == []


def test_list_students(client, student_payload):
    create(client, student_payload)
    response = client.get("/api/v1/students")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_existing_and_missing(client, student_payload):
    created = create(client, student_payload).json()
    assert client.get(f"/api/v1/students/{created['id']}").json() == created
    missing = client.get("/api/v1/students/00000000-0000-0000-0000-000000000001")
    assert missing.status_code == 404
    assert "traceback" not in missing.text.lower()


def test_patch_changes_only_sent_field(client, student_payload):
    created = create(client, student_payload).json()
    response = client.patch(f"/api/v1/students/{created['id']}", json={"group_code": "КН-32"})
    assert response.status_code == 200
    body = response.json()
    assert body["group_code"] == "КН-32"
    assert body["full_name"] == created["full_name"]
    assert body["email"] == created["email"]
    assert body["academic_status"] == "active"


def test_unknown_field_rejected(client, student_payload):
    created = create(client, student_payload).json()
    response = client.patch(f"/api/v1/students/{created['id']}", json={"is_admin": True})
    assert response.status_code == 422


def test_empty_patch_rejected(client, student_payload):
    created = create(client, student_payload).json()
    assert client.patch(f"/api/v1/students/{created['id']}", json={}).status_code == 422


def test_academic_status_filter(client, student_payload):
    create(client, student_payload)
    second = {**student_payload, "email": "leave@example.com", "academic_status": "academic_leave"}
    create(client, second)
    response = client.get("/api/v1/students", params={"academic_status": "academic_leave"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "leave@example.com"


def test_invalid_academic_status_rejected(client, student_payload):
    student_payload["academic_status"] = "unknown_status"
    assert create(client, student_payload).status_code == 422


def test_patch_invalid_academic_status_rejected(client, student_payload):
    created = create(client, student_payload).json()
    response = client.patch(f"/api/v1/students/{created['id']}", json={"academic_status": "unknown_status"})
    assert response.status_code == 422


def test_duplicate_email_conflict_case_insensitive(client, student_payload):
    assert create(client, student_payload).status_code == 201
    duplicate = {**student_payload, "email": student_payload["email"].upper()}
    assert create(client, duplicate).status_code == 409


def test_patch_email_duplicate_conflict(client, student_payload):
    first = create(client, student_payload).json()
    second_payload = {**student_payload, "email": "second@example.com"}
    second = create(client, second_payload).json()
    response = client.patch(f"/api/v1/students/{second['id']}", json={"email": first["email"]})
    assert response.status_code == 409
