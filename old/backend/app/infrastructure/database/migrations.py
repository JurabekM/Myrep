"""Lightweight, ordered Mongo migration runner.

Each migration is an async callable registered with @migration(n). Applied
versions are recorded in the `_migrations` collection; the runner is safe to
call on every startup and applies only pending migrations, in order.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.logging import get_logger
from app.infrastructure.database.mongo import Collections, MongoManager

logger = get_logger(__name__)

MigrationFn = Callable[[AsyncIOMotorDatabase], Awaitable[None]]

_REGISTRY: dict[int, tuple[str, MigrationFn]] = {}


def migration(version: int) -> Callable[[MigrationFn], MigrationFn]:
    def decorator(fn: MigrationFn) -> MigrationFn:
        if version in _REGISTRY:
            raise ValueError(f"Duplicate migration version {version}")
        _REGISTRY[version] = (fn.__name__, fn)
        return fn

    return decorator


async def run_migrations(mongo: MongoManager) -> int:
    """Apply pending migrations; return how many were applied."""
    coll = mongo.collection(Collections.MIGRATIONS)
    applied_versions = {doc["version"] async for doc in coll.find({}, {"version": 1})}
    applied_count = 0
    for version in sorted(_REGISTRY):
        if version in applied_versions:
            continue
        name, fn = _REGISTRY[version]
        logger.info("migration_start", version=version, name=name)
        await fn(mongo.db)
        await coll.insert_one(
            {"version": version, "name": name, "applied_at": datetime.now(timezone.utc)}
        )
        applied_count += 1
        logger.info("migration_done", version=version, name=name)
    return applied_count


# ---------------------------------------------------------------------------
# Migrations (append-only; never edit an applied migration)
# ---------------------------------------------------------------------------


@migration(1)
async def seed_feature_flags(db: AsyncIOMotorDatabase) -> None:
    defaults = [
        {"key": "voice_output", "enabled": True, "rollout_pct": 100, "plans": []},
        {"key": "legal_assistant", "enabled": True, "rollout_pct": 100, "plans": []},
        {"key": "local_llm", "enabled": False, "rollout_pct": 0, "plans": ["enterprise"]},
        {"key": "team_workspaces", "enabled": False, "rollout_pct": 0, "plans": ["business"]},
    ]
    for flag in defaults:
        await db[Collections.FEATURE_FLAGS].update_one(
            {"key": flag["key"]}, {"$setOnInsert": flag}, upsert=True
        )


@migration(2)
async def seed_prompt_templates(db: AsyncIOMotorDatabase) -> None:
    """System prompts live in DB so admins can iterate without redeploys.
    Initial content is loaded from the versioned YAML prompt library."""
    from app.ai.prompts.loader import load_builtin_prompts

    for prompt in load_builtin_prompts():
        await db[Collections.PROMPT_TEMPLATES].update_one(
            {"key": prompt["key"], "version": prompt["version"], "locale": prompt["locale"]},
            {"$setOnInsert": prompt},
            upsert=True,
        )
