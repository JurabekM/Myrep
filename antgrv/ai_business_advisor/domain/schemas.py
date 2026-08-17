from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    confidence_score: float = Field(default=1.0)
    sources: List[str] = Field(default_factory=list)

class DocumentChunk(BaseModel):
    text: str
    metadata: dict
