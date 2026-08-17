import uuid

from app.models.enums import AuthProvider, Language
from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str | None
    auth_provider: AuthProvider
    language: Language
    is_active: bool
