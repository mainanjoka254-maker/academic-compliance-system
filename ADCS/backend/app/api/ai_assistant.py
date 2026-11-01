from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    roles = [r.name for r in current_user.roles]
    role = roles[0] if roles else "student"
    return {
        "reply": f"Hello {current_user.full_name}. As a {role}, I can help with ADCS features, compliance requirements, and your authorized records. Your question: {payload.message}",
        "role": role,
    }