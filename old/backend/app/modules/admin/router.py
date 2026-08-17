"""Admin panel API: users, analytics, prompts, KB, feature flags, moderation."""

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field, HttpUrl

from app.core.dependencies import AdminUser, Container, ModeratorUser
from app.core.exceptions import NotFoundError
from app.domain.entities.user import Plan, UserRole
from app.infrastructure.database.mongo import Collections

router = APIRouter(prefix="/admin", tags=["admin"])


# ------------------------------------------------------------------- users


class UserPatchRequest(BaseModel):
    role: UserRole | None = None
    plan: Plan | None = None
    is_active: bool | None = None


@router.get("/users")
async def list_users(
    admin: AdminUser,
    container: Container,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    plan: Plan | None = None,
) -> dict:
    filters = {"plan": plan.value} if plan else None
    users, total = await container.users.list_paginated(skip=skip, limit=limit, filters=filters)
    return {
        "total": total,
        "items": [
            {
                "id": u.id, "email": u.email, "full_name": u.full_name,
                "role": u.role, "plan": u.plan, "is_active": u.is_active,
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: str, req: UserPatchRequest, admin: AdminUser, container: Container
) -> dict:
    fields = {k: v for k, v in req.model_dump(exclude_none=True).items()}
    before = await container.users.get_by_id(user_id)
    if before is None:
        raise NotFoundError("Foydalanuvchi topilmadi")
    updated = await container.users.update(user_id, fields)
    await container.audit_logs.record(
        actor_id=admin.id,
        action="admin.user_update",
        resource=user_id,
        before={k: getattr(before, k) for k in fields},
        after=fields,
    )
    return {"id": updated.id, "role": updated.role, "plan": updated.plan,
            "is_active": updated.is_active}


# --------------------------------------------------------------- analytics


@router.get("/analytics")
async def analytics(admin: ModeratorUser, container: Container) -> dict:
    since_30d = datetime.now(timezone.utc) - timedelta(days=30)
    users = container.mongo.collection(Collections.USERS)
    usage = container.mongo.collection(Collections.USAGE_STATS)

    total_users = await users.count_documents({})
    new_users_30d = await users.count_documents({"created_at": {"$gte": since_30d}})
    by_plan = [
        {"plan": row["_id"], "count": row["count"]}
        async for row in users.aggregate(
            [{"$group": {"_id": "$plan", "count": {"$sum": 1}}}]
        )
    ]
    ai_usage = [
        {"module": row["_id"], "tokens": row["tokens"], "cost_usd": round(row["cost"], 2)}
        async for row in usage.aggregate(
            [
                {
                    "$group": {
                        "_id": "$module",
                        "tokens": {"$sum": "$tokens"},
                        "cost": {"$sum": "$cost_usd"},
                    }
                },
                {"$sort": {"tokens": -1}},
            ]
        )
    ]
    return {
        "total_users": total_users,
        "new_users_30d": new_users_30d,
        "by_plan": by_plan,
        "ai_usage": ai_usage,
    }


# ----------------------------------------------------------------- prompts


class PromptUpsertRequest(BaseModel):
    key: str = Field(min_length=3, max_length=80)
    locale: str = Field(default="uz", max_length=10)
    content: str = Field(min_length=10, max_length=32_000)


@router.get("/prompts")
async def list_prompts(admin: AdminUser, container: Container) -> dict:
    cursor = container.mongo.collection(Collections.PROMPT_TEMPLATES).find(
        {}, sort=[("key", 1), ("version", -1)]
    )
    return {
        "items": [
            {
                "key": d["key"], "version": d["version"], "locale": d["locale"],
                "active": d["active"], "content": d["content"],
            }
            async for d in cursor
        ]
    }


@router.post("/prompts", status_code=status.HTTP_201_CREATED)
async def upsert_prompt(
    req: PromptUpsertRequest, admin: AdminUser, container: Container
) -> dict:
    coll = container.mongo.collection(Collections.PROMPT_TEMPLATES)
    latest = await coll.find_one(
        {"key": req.key, "locale": req.locale}, sort=[("version", -1)]
    )
    new_version = (latest["version"] + 1) if latest else 1
    # Deactivate previous versions; new one becomes active.
    await coll.update_many(
        {"key": req.key, "locale": req.locale}, {"$set": {"active": False}}
    )
    await coll.insert_one(
        {
            "key": req.key, "version": new_version, "locale": req.locale,
            "content": req.content, "active": True,
        }
    )
    await container.audit_logs.record(
        actor_id=admin.id, action="admin.prompt_update", resource=req.key,
        after={"version": new_version},
    )
    return {"key": req.key, "version": new_version}


# ---------------------------------------------------------- knowledge base


class KBIngestRequest(BaseModel):
    url: HttpUrl


class KBManualRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    text: str = Field(min_length=200, max_length=400_000)


@router.get("/kb/sources")
async def kb_sources(admin: ModeratorUser, container: Container) -> dict:
    cursor = container.mongo.collection(Collections.KB_SOURCES).find(
        {}, sort=[("updated_at", -1)]
    ).limit(500)
    return {
        "items": [
            {
                "id": str(d["_id"]), "type": d["type"], "title": d.get("title"),
                "url": d.get("url"), "chunks_count": d.get("chunks_count", 0),
                "updated_at": d.get("updated_at"),
            }
            async for d in cursor
        ]
    }


@router.post("/kb/ingest-lex", status_code=status.HTTP_202_ACCEPTED)
async def kb_ingest_lex(req: KBIngestRequest, admin: AdminUser, container: Container) -> dict:
    from app.infrastructure.queue.tasks import ingest_lex_url

    task = ingest_lex_url.delay(str(req.url))
    return {"status": "queued", "task_id": task.id}


@router.post("/kb/manual", status_code=status.HTTP_201_CREATED)
async def kb_manual(req: KBManualRequest, admin: AdminUser, container: Container) -> dict:
    from app.rag.ingestion import KnowledgeIngestionService

    service = KnowledgeIngestionService(container.mongo, container.qdrant, container.ai_router)
    return await service.ingest_manual_text(req.title, req.text)


# ------------------------------------------------------------ feature flags


class FeatureFlagRequest(BaseModel):
    enabled: bool
    rollout_pct: int = Field(ge=0, le=100)
    plans: list[Plan] = Field(default_factory=list)


@router.get("/feature-flags")
async def feature_flags(admin: AdminUser, container: Container) -> dict:
    cursor = container.mongo.collection(Collections.FEATURE_FLAGS).find({})
    return {
        "items": [
            {
                "key": d["key"], "enabled": d["enabled"],
                "rollout_pct": d.get("rollout_pct", 100), "plans": d.get("plans", []),
            }
            async for d in cursor
        ]
    }


@router.put("/feature-flags/{key}")
async def set_feature_flag(
    key: str, req: FeatureFlagRequest, admin: AdminUser, container: Container
) -> dict:
    await container.mongo.collection(Collections.FEATURE_FLAGS).update_one(
        {"key": key},
        {"$set": {"enabled": req.enabled, "rollout_pct": req.rollout_pct,
                  "plans": [p.value for p in req.plans]}},
        upsert=True,
    )
    await container.audit_logs.record(
        actor_id=admin.id, action="admin.flag_update", resource=key,
        after=req.model_dump(mode="json"),
    )
    return {"key": key, "enabled": req.enabled}


# ------------------------------------------------------------------- logs


@router.get("/audit-logs")
async def audit_logs(
    admin: AdminUser,
    container: Container,
    actor_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    query: dict = {"actor_id": actor_id} if actor_id else {}
    cursor = (
        container.mongo.collection(Collections.AUDIT_LOGS)
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    return {
        "items": [
            {
                "id": str(d["_id"]), "actor_id": d["actor_id"], "action": d["action"],
                "resource": d["resource"], "ip": d.get("ip"),
                "created_at": d["created_at"],
            }
            async for d in cursor
        ]
    }


# -------------------------------------------------------------- moderation


@router.get("/moderation/flagged")
async def flagged_messages(
    admin: ModeratorUser,
    container: Container,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Low-confidence or negatively-rated answers for human review."""
    cursor = (
        container.mongo.collection(Collections.MESSAGES)
        .find(
            {
                "role": "assistant",
                "$or": [{"safety.confidence": {"$lt": 0.4}}, {"feedback": -1}],
            }
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    return {
        "items": [
            {
                "id": str(d["_id"]), "conversation_id": d["conversation_id"],
                "content": d["content"][:500], "safety": d.get("safety"),
                "feedback": d.get("feedback"), "created_at": d["created_at"],
            }
            async for d in cursor
        ]
    }
