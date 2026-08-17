from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    language: str = "uz"  # uz | ru | en


class ChatResponse(BaseModel):
    intent: str
    reply: str
