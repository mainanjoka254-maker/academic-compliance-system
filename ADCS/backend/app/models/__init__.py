from app.models.base import TimestampMixin
from app.models.institution import Institution
from app.models.department import Department
from app.models.academic_structure import Faculty, AcademicProgram, lecturer_program_assignments
from app.models.role import Role, user_roles
from app.models.user import User
from app.models.student import Student, Lecturer
from app.models.academic import AcademicTerm, Course, CourseEnrollment, AttendanceRecord, AssessmentRecord
from app.models.compliance import AcademicPolicy, ComplianceRule, ComplianceIncident
from app.models.compliance_case import ComplianceCase, Investigation, Appeal, CaseAudit
from app.models.risk import RiskAssessment, RiskAlert
from app.models.notification import Notification, NotificationDelivery, AuditLog, EmailVerificationToken, PasswordResetToken
from app.models.oauth import GoogleOAuthState
from app.models.document import AcademicDocument, DocumentReview
from app.models.user_setting import UserSetting, UserNotificationPreference, UserPrivacyPreference
from app.models.announcement import Announcement
from app.models.support_ticket import SupportTicket, SupportTicketMessage
from app.models.accreditation import AccreditationFramework
from app.models.user_profile import UserProfile, StudentProfile, LecturerProfile, StaffProfile
from app.models.session import UserSession, LoginHistory
from app.models.activity import UserActivityLog

__all__ = [
    "TimestampMixin", "Institution", "Department", "Faculty", "AcademicProgram",
    "lecturer_program_assignments", "Role", "user_roles", "User",
    "Student", "Lecturer", "AcademicTerm", "Course", "CourseEnrollment",
    "AttendanceRecord", "AssessmentRecord", "AcademicPolicy", "ComplianceRule",
    "ComplianceIncident", "ComplianceCase", "Investigation", "Appeal", "CaseAudit",
    "RiskAssessment", "RiskAlert", "Notification", "NotificationDelivery", "AuditLog",
    "EmailVerificationToken", "PasswordResetToken", "GoogleOAuthState",
    "AcademicDocument", "DocumentReview", "UserSetting", "UserNotificationPreference",
    "UserPrivacyPreference", "Announcement", "SupportTicket", "SupportTicketMessage",
    "AccreditationFramework", "UserProfile", "StudentProfile", "LecturerProfile",
    "StaffProfile", "UserSession", "LoginHistory", "UserActivityLog",
]
