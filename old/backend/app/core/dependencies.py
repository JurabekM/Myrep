"""FastAPI dependency-injection providers.

A single AppContainer is built at startup (lifespan) and stored on
app.state; Depends() providers pull services from it. Services themselves
receive plain constructor args, so they stay framework-free.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import TokenService, TwoFactorService
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.repositories import (
    AuditLogRepository,
    ConversationRepository,
    MessageRepository,
    UsageStatsRepository,
    UserRepository,
)
from app.infrastructure.cache.redis import RedisManager
from app.infrastructure.database.mongo import MongoManager
from app.infrastructure.repositories.mongo_repositories import (
    MongoAuditLogRepository,
    MongoConversationRepository,
    MongoMessageRepository,
    MongoUsageStatsRepository,
    MongoUserRepository,
)
from app.infrastructure.storage.gridfs import GridFSStorage
from app.infrastructure.vector.qdrant import QdrantManager

from app.ai.prompts.loader import PromptRepository
from app.ai.router import ModelRouter, build_provider_registry
from app.ai.safety.pipeline import SafetyEvaluator

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AppContainer:
    settings: Settings
    mongo: MongoManager
    redis: RedisManager
    qdrant: QdrantManager
    storage: GridFSStorage
    token_service: TokenService
    two_factor_service: TwoFactorService
    users: UserRepository
    conversations: ConversationRepository
    messages: MessageRepository
    usage_stats: UsageStatsRepository
    audit_logs: AuditLogRepository
    ai_router: ModelRouter
    safety: SafetyEvaluator
    prompts: PromptRepository


async def build_container(settings: Settings | None = None) -> AppContainer:
    settings = settings or get_settings()
    mongo = MongoManager(settings)
    redis = RedisManager(settings)
    qdrant = QdrantManager(settings)
    await mongo.connect()
    await redis.connect()
    await qdrant.connect()
    usage_stats = MongoUsageStatsRepository(mongo)
    ai_router = ModelRouter(build_provider_registry(settings), settings, usage_stats)
    return AppContainer(
        settings=settings,
        mongo=mongo,
        redis=redis,
        qdrant=qdrant,
        storage=GridFSStorage(mongo, settings),
        token_service=TokenService(settings, redis),
        two_factor_service=TwoFactorService(settings),
        users=MongoUserRepository(mongo),
        conversations=MongoConversationRepository(mongo),
        messages=MongoMessageRepository(mongo),
        usage_stats=usage_stats,
        audit_logs=MongoAuditLogRepository(mongo),
        ai_router=ai_router,
        safety=SafetyEvaluator(ai_router),
        prompts=PromptRepository(mongo),
    )


async def shutdown_container(container: AppContainer) -> None:
    await container.qdrant.disconnect()
    await container.redis.disconnect()
    await container.mongo.disconnect()


def get_container(request: Request) -> AppContainer:
    return request.app.state.container  # type: ignore[no-any-return]


Container = Annotated[AppContainer, Depends(get_container)]


async def get_current_user(
    container: Container,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Avtorizatsiya talab qilinadi")
    payload = container.token_service.verify_access_token(credentials.credentials)
    user = await container.users.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise AuthenticationError("Foydalanuvchi topilmadi yoki bloklangan")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("Bu amal uchun ruxsat yo'q")
        return user

    return Depends(checker)


AdminUser = Annotated[User, require_roles(UserRole.ADMIN)]
ModeratorUser = Annotated[User, require_roles(UserRole.ADMIN, UserRole.MODERATOR)]
