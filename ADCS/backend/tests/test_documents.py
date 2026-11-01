import uuid

from app.core.security import create_access_token
from app.models.academic import Course
from app.models.document import AcademicDocument, DocumentReview
from app.models.institution import Institution
from app.models.notification import AuditLog, Notification
from app.models.role import Role
from app.models.student import Lecturer, Student
from app.models.user import User


def _institution(db):
    suffix = uuid.uuid4().hex[:8]
    institution = Institution(name=f"Document Test {suffix}", code=f"DT{suffix}")
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


def _user(db, institution, role_name):
    role = db.query(Role).filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name, is_system=True)
        db.add(role)
        db.flush()
    user = User(
        email=f"{role_name}-{uuid.uuid4().hex[:8]}@test.com",
        full_name=f"Test {role_name}",
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )
    user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


def _student(db, institution):
    user = _user(db, institution, "student")
    profile = Student(
        institution_id=institution.id,
        user_id=user.id,
        student_number=f"STU-{uuid.uuid4().hex[:8]}",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return user, profile


def test_student_document_upload_review_history_and_institution_isolation(
    client, db, monkeypatch, tmp_path
):
    monkeypatch.setattr("app.api.documents.settings.DOCUMENT_STORAGE_PATH", tmp_path)
    institution = _institution(db)
    student_user, student = _student(db, institution)
    content = b"%PDF-1.7\nacademic record"
    _, other_student = _student(db, institution)

    spoofed_upload = client.post(
        "/api/v1/documents",
        data={"purpose": "student_document", "student_id": str(other_student.id)},
        files={"file": ("transcript.pdf", content, "application/pdf")},
        headers=_headers(student_user),
    )
    assert spoofed_upload.status_code == 403

    upload = client.post(
        "/api/v1/documents",
        data={"purpose": "student_document"},
        files={"file": ("transcript.pdf", content, "application/pdf")},
        headers=_headers(student_user),
    )
    assert upload.status_code == 201
    document = upload.json()
    assert document["student_id"] == student.id
    assert document["status"] == "pending"
    assert document["sha256"]
    document_id = document["id"]

    download = client.get(
        f"/api/v1/documents/{document_id}/download",
        headers=_headers(student_user),
    )
    assert download.status_code == 200
    assert download.content == content
    assert download.headers["x-content-type-options"] == "nosniff"
    assert client.post(
        f"/api/v1/documents/{document_id}/review",
        json={"status": "approved"},
        headers=_headers(student_user),
    ).status_code == 403

    reviewer = _user(db, institution, "compliance_officer")
    assert client.post(
        f"/api/v1/documents/{document_id}/review",
        json={"status": "rejected"},
        headers=_headers(reviewer),
    ).status_code == 422
    review = client.post(
        f"/api/v1/documents/{document_id}/review",
        json={"status": "rejected", "note": "The student number is unreadable."},
        headers=_headers(reviewer),
    )
    assert review.status_code == 200
    assert review.json()["status"] == "rejected"

    history = client.get(
        f"/api/v1/documents/{document_id}/history",
        headers=_headers(student_user),
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["note"] == "The student number is unreadable."
    assert db.query(DocumentReview).filter_by(document_id=document_id).count() == 1
    assert db.query(AuditLog).filter_by(
        resource_type="academic_document",
        resource_id=document_id,
    ).count() == 2
    assert db.query(Notification).filter_by(user_id=student_user.id).count() == 1

    other_institution = _institution(db)
    other_officer = _user(db, other_institution, "compliance_officer")
    assert client.get(
        f"/api/v1/documents/{document_id}",
        headers=_headers(other_officer),
    ).status_code == 404
    assert client.post(
        f"/api/v1/documents/{document_id}/review",
        json={"status": "approved"},
        headers=_headers(other_officer),
    ).status_code == 403


def test_document_upload_rejects_mismatched_and_oversized_files(
    client, db, monkeypatch, tmp_path
):
    monkeypatch.setattr("app.api.documents.settings.DOCUMENT_STORAGE_PATH", tmp_path)
    institution = _institution(db)
    student_user, _ = _student(db, institution)
    headers = _headers(student_user)
    existing_documents = db.query(AcademicDocument).count()

    invalid_type = client.post(
        "/api/v1/documents",
        data={"purpose": "student_document"},
        files={"file": ("record.pdf", b"<html>not a PDF</html>", "application/pdf")},
        headers=headers,
    )
    assert invalid_type.status_code == 415

    monkeypatch.setattr("app.api.documents.settings.MAX_DOCUMENT_SIZE_BYTES", 8)
    too_large = client.post(
        "/api/v1/documents",
        data={"purpose": "student_document"},
        files={"file": ("record.pdf", b"%PDF-1234", "application/pdf")},
        headers=headers,
    )
    assert too_large.status_code == 413
    assert db.query(AcademicDocument).count() == existing_documents
    assert list(tmp_path.iterdir()) == []


def test_lecturer_submission_requires_assigned_course(client, db, monkeypatch, tmp_path):
    monkeypatch.setattr("app.api.documents.settings.DOCUMENT_STORAGE_PATH", tmp_path)
    institution = _institution(db)
    lecturer_user = _user(db, institution, "lecturer")
    lecturer = Lecturer(
        institution_id=institution.id,
        user_id=lecturer_user.id,
        staff_number=f"STAFF-{uuid.uuid4().hex[:8]}",
    )
    db.add(lecturer)
    db.flush()
    course = Course(
        institution_id=institution.id,
        lecturer_id=lecturer.id,
        code=f"CS{uuid.uuid4().hex[:6]}",
        name="Academic Compliance",
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    other_lecturer = _user(db, institution, "lecturer")
    rejected = client.post(
        "/api/v1/documents",
        data={"purpose": "lecturer_submission", "course_id": str(course.id)},
        files={"file": ("marks.pdf", b"%PDF-1.7\nmarks", "application/pdf")},
        headers=_headers(other_lecturer),
    )
    assert rejected.status_code == 403

    accepted = client.post(
        "/api/v1/documents",
        data={"purpose": "lecturer_submission", "course_id": str(course.id)},
        files={"file": ("marks.pdf", b"%PDF-1.7\nmarks", "application/pdf")},
        headers=_headers(lecturer_user),
    )
    assert accepted.status_code == 201
    assert accepted.json()["course_id"] == course.id
    assert accepted.json()["student_id"] is None
