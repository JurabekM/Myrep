"""Index definitions for every collection.

`ensure_indexes` is idempotent — Mongo's create_indexes is a no-op for
already-existing identical indexes, so it runs on every startup.
"""

from pymongo import ASCENDING, DESCENDING, IndexModel, TEXT

from app.infrastructure.database.mongo import Collections, MongoManager

AUDIT_LOG_TTL_SECONDS = 365 * 24 * 3600  # 1 year retention

INDEXES: dict[str, list[IndexModel]] = {
    Collections.USERS: [
        IndexModel([("email", ASCENDING)], unique=True, name="uq_email"),
        IndexModel(
            [("phone", ASCENDING)],
            unique=True,
            name="uq_phone",
            partialFilterExpression={"phone": {"$type": "string"}},
        ),
        IndexModel([("role", ASCENDING), ("plan", ASCENDING)], name="ix_role_plan"),
    ],
    Collections.CONVERSATIONS: [
        IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)], name="ix_user_updated"),
        IndexModel([("module", ASCENDING)], name="ix_module"),
    ],
    Collections.MESSAGES: [
        IndexModel(
            [("conversation_id", ASCENDING), ("created_at", ASCENDING)], name="ix_conv_created"
        ),
        IndexModel([("content", TEXT)], name="tx_content", default_language="none"),
    ],
    Collections.DOCUMENTS: [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_user_created"),
        IndexModel([("status", ASCENDING)], name="ix_status"),
    ],
    Collections.KB_SOURCES: [
        IndexModel(
            [("url", ASCENDING)],
            unique=True,
            name="uq_url",
            partialFilterExpression={"url": {"$type": "string"}},
        ),
        IndexModel([("type", ASCENDING), ("updated_at", DESCENDING)], name="ix_type_updated"),
    ],
    Collections.PAYMENTS: [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_user_created"),
        IndexModel(
            [("provider", ASCENDING), ("external_id", ASCENDING)],
            unique=True,
            name="uq_provider_external",
        ),
    ],
    Collections.AUDIT_LOGS: [
        IndexModel([("actor_id", ASCENDING), ("created_at", DESCENDING)], name="ix_actor_created"),
        IndexModel(
            [("created_at", ASCENDING)],
            expireAfterSeconds=AUDIT_LOG_TTL_SECONDS,
            name="ttl_created",
        ),
    ],
    Collections.PROMPT_TEMPLATES: [
        IndexModel(
            [("key", ASCENDING), ("version", ASCENDING), ("locale", ASCENDING)],
            unique=True,
            name="uq_key_version_locale",
        ),
        IndexModel([("key", ASCENDING), ("active", ASCENDING)], name="ix_key_active"),
    ],
    Collections.FEATURE_FLAGS: [
        IndexModel([("key", ASCENDING)], unique=True, name="uq_key"),
    ],
    Collections.USAGE_STATS: [
        IndexModel(
            [("user_id", ASCENDING), ("date", ASCENDING), ("module", ASCENDING)],
            unique=True,
            name="uq_user_date_module",
        ),
    ],
}


async def ensure_indexes(mongo: MongoManager) -> None:
    for collection_name, models in INDEXES.items():
        await mongo.collection(collection_name).create_indexes(models)
