"""MongoDB connection lifecycle (motor, async).

A single client is created at app startup and shared via DI. Collection
accessors are typed helpers so repositories never hard-code names twice.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Collections:
    USERS = "users"
    CONVERSATIONS = "conversations"
    MESSAGES = "messages"
    DOCUMENTS = "documents"
    KB_SOURCES = "kb_sources"
    PAYMENTS = "payments"
    AUDIT_LOGS = "audit_logs"
    PROMPT_TEMPLATES = "prompt_templates"
    FEATURE_FLAGS = "feature_flags"
    USAGE_STATS = "usage_stats"
    MIGRATIONS = "_migrations"


class MongoManager:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        self._client = AsyncIOMotorClient(
            str(self._settings.mongo_dsn),
            maxPoolSize=50,
            minPoolSize=5,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation="standard",
        )
        # Fail fast on unreachable server instead of at first query.
        await self._client.admin.command("ping")
        logger.info("mongo_connected", db=self._settings.mongo_db_name)

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("mongo_disconnected")

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._client is None:
            raise RuntimeError("MongoManager.connect() has not been called")
        return self._client[self._settings.mongo_db_name]

    def collection(self, name: str) -> AsyncIOMotorCollection:
        return self.db[name]
