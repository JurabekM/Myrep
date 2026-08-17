from fastapi import APIRouter

from app.inference.chatbot_service import get_chatbot_service
from app.schemas.chatbot import ChatRequest, ChatResponse

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    result = get_chatbot_service().reply(payload.message, payload.language)
    return ChatResponse(**result)
