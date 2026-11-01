import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import ensure_institution_access, is_super_admin, require_roles
from app.core.security import get_current_user
from app.models.academic import Course, CourseEnrollment
from app.models.document import AcademicDocument, DocumentReview
from app.models.notification import AuditLog, Notification
from app.models.student import Lecturer, Student
from app.models.user import User
from app.schemas.document import DocumentOut, DocumentReviewCreate, DocumentReviewOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Academic Documents"])

STAFF_ROLES = {"university_admin", "registrar", "compliance_officer"}
ALLOWED_FILES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}


def _role_names(user: User) -> set[str]:
    return {role.name for role in user.roles}


def _document_scope(db: Session, user: User):
    query = db.query(AcademicDocument)
    roles = _role_names(user)
    if is_super_admin(user):
        return query
    if user.institution_id is None:
        raise HTTPException(status_code=403, detail="An institution is required")
    if roles.intersection(STAFF_ROLES):
        return query.filter(AcademicDocument.institution_id == user.institution_id)
    if "student" in roles:
        student = db.query(Student).filter(
            Student.user_id == user.id,
            Student.institution_id == user.institution_id,
        ).first()
        if not student:
            return query.filter(False)
        enrolled_courses = db.query(CourseEnrollment.course_id).filter(
            CourseEnrollment.student_id == student.id,
            CourseEnrollment.institution_id == user.institution_id,
            CourseEnrollment.status == "enrolled",
        )
        return query.filter(
            AcademicDocument.institution_id == user.institution_id,
            or_(
                AcademicDocument.student_id == student.id,
                AcademicDocument.course_id.in_(enrolled_courses),
            ),
        )
    if "lecturer" in roles:
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == user.id,
            Lecturer.institution_id == user.institution_id,
        ).first()
        if not lecturer:
            return query.filter(False)
        assigned_courses = db.query(Course.id).filter(
            Course.lecturer_id == lecturer.id,
            Course.institution_id == user.institution_id,
        )
        return query.filter(
            AcademicDocument.institution_id == user.institution_id,
            or_(
                AcademicDocument.uploaded_by_id == user.id,
                AcademicDocument.course_id.in_(assigned_courses),
            ),
        )
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _clean_filename(filename: str | None) -> str:
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    if not name or len(name) > 255:
        raise HTTPException(status_code=400, detail="A valid filename is required")
    return name


def _validate_file(filename: str, content_type: str | None, content: bytes) -> tuple[str, str]:
    extension = Path(filename).suffix.lower()
    allowed = ALLOWED_FILES.get(extension)
    if not allowed:
        raise HTTPException(status_code=415, detail="Only PDF, PNG, and JPEG documents are supported")
    expected_type, signature = allowed
    if content_type != expected_type or not content.startswith(signature):
        raise HTTPException(status_code=415, detail="File content does not match the permitted file type")
    return extension, expected_type


def _document_path(storage_key: str) -> Path:
    storage_root = Path(settings.DOCUMENT_STORAGE_PATH).resolve()
    path = (storage_root / storage_key).resolve()
    if path.parent != storage_root:
        raise HTTPException(status_code=404, detail="Document file not found")
    return path


@router.get("", response_model=list[DocumentOut])
def list_documents(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if institution_id is not None and not is_super_admin(current_user):
        ensure_institution_access(current_user, institution_id)
    query = _document_scope(db, current_user)
    if institution_id is not None:
        query = query.filter(AcademicDocument.institution_id == institution_id)
    return query.order_by(AcademicDocument.created_at.desc()).all()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DocumentOut)
async def upload_document(
    request: Request,
    purpose: Literal["student_document", "lecturer_submission"] = Form(...),
    file: UploadFile = File(...),
    student_id: int | None = Form(default=None),
    course_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roles = _role_names(current_user)
    institution_id: int

    if purpose == "student_document":
        if course_id is not None:
            raise HTTPException(status_code=422, detail="Student documents cannot be attached to a course")
        student = None
        if "student" in roles and not is_super_admin(current_user):
            student = db.query(Student).filter(
                Student.user_id == current_user.id,
                Student.institution_id == current_user.institution_id,
            ).first()
            if not student or (student_id is not None and student_id != student.id):
                raise HTTPException(status_code=403, detail="Students may upload documents only to their own profile")
        elif roles.intersection(STAFF_ROLES) or is_super_admin(current_user):
            if student_id is None:
                raise HTTPException(status_code=422, detail="student_id is required for staff uploads")
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            ensure_institution_access(current_user, student.institution_id)
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        institution_id = student.institution_id
        student_id = student.id
    else:
        if student_id is not None or course_id is None or "lecturer" not in roles:
            raise HTTPException(status_code=403, detail="Lecturer submissions require an assigned course")
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == current_user.id,
            Lecturer.institution_id == current_user.institution_id,
        ).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        if not lecturer or not course or course.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Course is not assigned to this lecturer")
        if course.institution_id != lecturer.institution_id:
            raise HTTPException(status_code=403, detail="Cross-institution submissions are not allowed")
        institution_id = course.institution_id

    original_filename = _clean_filename(file.filename)
    content = await file.read(settings.MAX_DOCUMENT_SIZE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > settings.MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the maximum permitted size")
    extension, verified_content_type = _validate_file(original_filename, file.content_type, content)

    storage_key = f"{uuid.uuid4().hex}{extension}"
    storage_path = _document_path(storage_key)
    try:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content)
    except OSError as exc:
        logger.exception("Unable to store academic document")
        raise HTTPException(status_code=500, detail="Document could not be stored") from exc

    document = AcademicDocument(
        institution_id=institution_id,
        student_id=student_id,
        course_id=course_id,
        uploaded_by_id=current_user.id,
        purpose=purpose,
        original_filename=original_filename,
        storage_key=storage_key,
        content_type=verified_content_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
    db.add(document)
    try:
        db.flush()
        db.add(AuditLog(
            institution_id=institution_id,
            user_id=current_user.id,
            action="document.uploaded",
            resource_type="academic_document",
            resource_id=document.id,
            ip_address=request.client.host if request.client else None,
            details=f"purpose={purpose}",
        ))
        db.commit()
        db.refresh(document)
    except SQLAlchemyError as exc:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        logger.exception("Unable to save academic document metadata")
        raise HTTPException(status_code=500, detail="Document metadata could not be saved") from exc
    return document


@router.get("/{document_id:int}", response_model=DocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = _document_scope(db, current_user).filter(AcademicDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id:int}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = _document_scope(db, current_user).filter(AcademicDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    path = _document_path(document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.original_filename,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.get("/{document_id:int}/history", response_model=list[DocumentReviewOut])
def get_document_history(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = _document_scope(db, current_user).filter(AcademicDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return db.query(DocumentReview).filter(
        DocumentReview.document_id == document.id,
    ).order_by(DocumentReview.created_at.asc()).all()


@router.post("/{document_id:int}/review", response_model=DocumentOut)
def review_document(
    document_id: int,
    payload: DocumentReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
):
    document = db.query(AcademicDocument).filter(AcademicDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_institution_access(current_user, document.institution_id)
    if document.uploaded_by_id == current_user.id:
        raise HTTPException(status_code=403, detail="Users cannot review their own uploads")
    if document.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending documents can be reviewed")
    if payload.status == "rejected" and not (payload.note and payload.note.strip()):
        raise HTTPException(status_code=422, detail="A reason is required when rejecting a document")

    previous_status = document.status
    document.status = payload.status
    document.reviewed_by_id = current_user.id
    document.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    document.review_note = payload.note.strip() if payload.note else None
    db.add(DocumentReview(
        document_id=document.id,
        reviewer_id=current_user.id,
        previous_status=previous_status,
        status=payload.status,
        note=document.review_note,
    ))
    recipient_id = document.student.user_id if document.student_id else document.uploaded_by_id
    db.add(Notification(
        institution_id=document.institution_id,
        user_id=recipient_id,
        type="document_review",
        title=f"Document {payload.status}",
        message=f"{document.original_filename} was {payload.status}.",
        link="/dashboard",
    ))
    db.add(AuditLog(
        institution_id=document.institution_id,
        user_id=current_user.id,
        action=f"document.{payload.status}",
        resource_type="academic_document",
        resource_id=document.id,
        ip_address=request.client.host if request.client else None,
        details=document.review_note,
    ))
    db.commit()
    db.refresh(document)
    return document
