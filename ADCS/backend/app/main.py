from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import init_db
from app.api.auth import router as auth_router
from app.api.auth_extra import router as auth_extra_router
from app.api.auth_google import router as auth_google_router
from app.api.institutions import router as institutions_router
from app.api.users import router as users_router
from app.api.students import router as students_router
from app.api.courses import router as courses_router
from app.api.academic import router as academic_router
from app.api.compliance_incidents import router as incidents_router
from app.api.compliance_cases import router as cases_router
from app.api.policies import router as policies_router
from app.api.risk import router as risk_router
from app.api.notifications import router as notifications_router
from app.api.reports import router as reports_router
from app.api.admin import router as admin_router
from app.api.documents import router as documents_router
from app.api.lecturers import router as lecturers_router
from app.api.compliance_analysis import router as compliance_analysis_router
from app.api.academic_structure import router as academic_structure_router
from app.api.settings import router as settings_router
from app.api.announcements import router as announcements_router
from app.api.support import router as support_router
from app.api.stats import router as stats_router
from app.api.ai_assistant import router as ai_router
from app.core.rate_limit import limiter

app = FastAPI(title=settings.APP_NAME, version="1.0.0", docs_url="/docs", redoc_url="/redoc")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
for r in [auth_router, auth_extra_router, auth_google_router, institutions_router, users_router, students_router,
          courses_router, academic_router, incidents_router, cases_router, policies_router,
           risk_router, notifications_router, reports_router, admin_router, documents_router,
           lecturers_router, compliance_analysis_router, academic_structure_router, settings_router,
           announcements_router, support_router, stats_router, ai_router]:
    app.include_router(r, prefix=API)


@app.on_event("startup")
def on_startup():
    init_db()



@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
