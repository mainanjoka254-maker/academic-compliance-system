from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DocumentOut(ORMModel):
    id: int
    institution_id: int
    student_id: int | None
    course_id: int | None
    uploaded_by_id: int
    purpose: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class DocumentReviewCreate(BaseModel):
    status: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=2000)


class DocumentReviewOut(ORMModel):
    id: int
    reviewer_id: int | None
    previous_status: str
    status: str
    note: str | None
    created_at: datetime
