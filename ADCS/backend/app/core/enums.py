import enum


class RoleName(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    UNIVERSITY_ADMIN = "university_admin"
    REGISTRAR = "registrar"
    LECTURER = "lecturer"
    STUDENT = "student"
    COMPLIANCE_OFFICER = "compliance_officer"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class CaseStatus(str, enum.Enum):
    REPORTED = "reported"
    UNDER_REVIEW = "under_review"
    INVESTIGATION = "investigation"
    AWAITING_RESPONSE = "awaiting_response"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class IncidentType(str, enum.Enum):
    ATTENDANCE = "attendance"
    ASSESSMENT = "assessment"
    REGISTRATION = "registration"
    ACADEMIC_MISCONDUCT = "academic_misconduct"
    DEADLINE = "deadline"
    OTHER = "other"


class NotificationType(str, enum.Enum):
    COMPLIANCE_WARNING = "compliance_warning"
    MISSED_DEADLINE = "missed_deadline"
    ATTENDANCE_CONCERN = "attendance_concern"
    NEW_CASE = "new_case"
    INVESTIGATION_UPDATE = "investigation_update"
    APPEAL_RESPONSE = "appeal_response"
    ACCOUNT_VERIFICATION = "account_verification"
    PASSWORD_RESET = "password_reset"
    RISK_ALERT = "risk_alert"
    DOCUMENT_REVIEW = "document_review"
