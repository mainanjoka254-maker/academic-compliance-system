import uuid
import uuid
import datetime

from app.models.institution import Institution
from app.models.user import User
from app.models.student import Student
from app.models.academic import AttendanceRecord, AssessmentRecord
from app.ai.risk_engine import RiskEngine
from app.core.security import hash_password


def test_risk_engine_high(db):
    inst = Institution(name="T", code=f"T{uuid.uuid4().hex[:6]}", is_active=True)
    db.add(inst); db.commit(); db.refresh(inst)
    user = User(email=f"s{uuid.uuid4().hex[:6]}@t.com", hashed_password=hash_password("pass"), full_name="Student", institution_id=inst.id, is_active=True, is_verified=True)
    db.add(user); db.commit(); db.refresh(user)
    stu = Student(user_id=user.id, institution_id=inst.id, student_number=f"STU{user.id}", status="active", gpa=1.5)
    db.add(stu); db.commit(); db.refresh(stu)
    for i in range(10):
        db.add(AttendanceRecord(institution_id=inst.id, student_id=stu.id, course_id=1, date=datetime.date(2025,1,1+i), status="present" if i < 5 else "absent"))
    for i in range(3):
        db.add(AssessmentRecord(institution_id=inst.id, student_id=stu.id, course_id=1, title=f"A{i}", submitted=False))
    db.commit()
    engine = RiskEngine(inst.id, db)
    res = engine.assess(stu)
    assert res["risk_level"] in ("moderate", "high")
    assert res["risk_score"] > 0
    assert any("Attendance" in f["factor"] for f in res["factors"])
    assert isinstance(res["recommendations"], list)


def test_risk_engine_low(db):
    inst = Institution(name="T2", code=f"T{uuid.uuid4().hex[:6]}", is_active=True)
    db.add(inst); db.commit(); db.refresh(inst)
    user = User(email=f"s{uuid.uuid4().hex[:6]}@t.com", hashed_password=hash_password("pass"), full_name="S2", institution_id=inst.id, is_active=True, is_verified=True)
    db.add(user); db.commit(); db.refresh(user)
    stu = Student(user_id=user.id, institution_id=inst.id, student_number=f"STU{user.id}", status="active", gpa=3.5)
    db.add(stu); db.commit(); db.refresh(stu)
    for i in range(10):
        db.add(AttendanceRecord(institution_id=inst.id, student_id=stu.id, course_id=1, date=datetime.date(2025,2,1+i), status="present"))
    db.commit()
    engine = RiskEngine(inst.id, db)
    res = engine.assess(stu)
    assert res["risk_level"] == "low"

