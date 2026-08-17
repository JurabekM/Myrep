from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ChatHistory:
    id: Optional[int]
    session_id: str
    role: str # 'user' or 'assistant'
    content: str
    timestamp: datetime = datetime.now()

@dataclass
class UserData:
    id: Optional[int]
    key: str
    value: str
    updated_at: datetime = datetime.now()
