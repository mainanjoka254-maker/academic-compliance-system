from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from datetime import datetime, date

from app.schemas.common import ORMModel


class AcademicPolicyCreate(BaseModel):
    institution_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    content: str = Field(min_length=1)
    category: Optional[str] = None
    version: str = "1.0"
    effective_date: Optional[date] = None
    is_active: bool = True


class AcademicPolicyOut(ORMModel):
    id: int
    institution_id: int
    title: str
    code: Optional[str] = None
    content: str
    category: Optional[str] = None
    version: str
    is_active: bool
    effective_date: Optional[date] = None
    created_at: datetime


class ComplianceRuleCreate(BaseModel):
    institution_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    rule_type: Literal["attendance", "assessment", "gpa", "compliance_case"]
    threshold_value: Optional[float] = Field(default=None, ge=0)
    weight: float = Field(default=1.0, ge=0)
    severity: Literal["low", "moderate", "high", "critical"] = "moderate"
    is_active: bool = True


class ComplianceRuleOut(ORMModel):
    id: int
    institution_id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    rule_type: str
    threshold_value: Optional[float] = None
    weight: float
    severity: str
    is_active: bool


class ComplianceIncidentCreate(BaseModel):
    institution_id: Optional[int] = None
    student_id: Optional[int] = Field(default=None, gt=0)
    course_id: Optional[int] = Field(default=None, gt=0)
    incident_type: Literal["attendance", "assessment", "registration", "academic_misconduct", "deadline", "other"]
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    evidence: Optional[str] = Field(default=None, max_length=10000)
    priority: Literal["low", "medium", "high", "critical"] = "medium"


class ComplianceIncidentOut(ORMModel):
    id: int
    institution_id: int
    student_id: Optional[int] = None
    course_id: Optional[int] = None
    reported_by: Optional[int] = None
    incident_type: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    created_at: datetime


class ComplianceCaseCreate(BaseModel):
    student_id: int = Field(gt=0)
    incident_id: Optional[int] = Field(default=None, gt=0)
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    assigned_officer_id: Optional[int] = Field(default=None, gt=0)


class ComplianceCaseUpdate(BaseModel):
    status: Optional[Literal["reported", "under_review", "investigation", "awaiting_response", "resolved", "escalated", "closed"]] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    assigned_officer_id: Optional[int] = None
    decision: Optional[str] = None
    resolution_notes: Optional[str] = None


class ComplianceCaseOut(ORMModel):
    id: int
    institution_id: int
    student_id: int
    incident_id: Optional[int] = None
    case_number: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    decision: Optional[str] = None
    resolution_notes: Optional[str] = None
    assigned_officer_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class InvestigationCreate(BaseModel):
    case_id: int
    findings: Optional[str] = None
    evidence: Optional[str] = None


class InvestigationOut(ORMModel):
    id: int
    institution_id: int
    case_id: int
    investigator_id: Optional[int] = None
    findings: Optional[str] = None
    evidence: Optional[str] = None
    status: str
    created_at: datetime


class AppealCreate(BaseModel):
    case_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=10000)


class AppealOut(ORMModel):
    id: int
    institution_id: int
    case_id: int
    student_id: int
    content: str
    status: str
    response: Optional[str] = None
    created_at: datetime


class RiskAssessmentOut(ORMModel):
    id: int
    institution_id: int
    student_id: int
    risk_score: float
    risk_level: str
    factors: Optional[Any] = None
    recommendations: Optional[Any] = None
    attendance_rate: Optional[float] = None
    missed_assessments: int
    reviewed: bool
    created_at: datetime


class RiskAlertOut(ORMModel):
    id: int
    institution_id: int
    student_id: int
    level: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationOut(ORMModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime
