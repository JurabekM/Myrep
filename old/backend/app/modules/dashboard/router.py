"""User dashboard: usage analytics, topic distribution, business health."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.core.dependencies import Container, CurrentUser
from app.infrastructure.database.mongo import Collections

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_CACHE_TTL = 300


@router.get("/usage")
async def usage(
    user: CurrentUser, container: Container, days: int = Query(30, ge=1, le=365)
) -> dict:
    cache_key = f"dash:usage:{user.id}:{days}"
    cached = await container.redis.get_json(cache_key)
    if cached is not None:
        return cached
    series = await container.usage_stats.aggregate_for_user(user.id, days=days)
    result = {
        "series": series,
        "totals": {
            "tokens": sum(r["tokens"] for r in series),
            "requests": sum(r["requests"] for r in series),
            "cost_usd": round(sum(r["cost_usd"] for r in series), 4),
        },
    }
    await container.redis.set_json(cache_key, result, _CACHE_TTL)
    return result


@router.get("/topics")
async def topics(
    user: CurrentUser, container: Container, days: int = Query(30, ge=1, le=365)
) -> dict:
    """Question distribution by module and by AI-assigned category."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    conversations = container.mongo.collection(Collections.CONVERSATIONS)
    messages = container.mongo.collection(Collections.MESSAGES)

    by_module = [
        {"module": row["_id"], "count": row["count"]}
        async for row in conversations.aggregate(
            [
                {"$match": {"user_id": user.id, "updated_at": {"$gte": since}}},
                {"$group": {"_id": "$module", "count": {"$sum": "$message_count"}}},
                {"$sort": {"count": -1}},
            ]
        )
    ]
    conv_ids = [
        str(row["_id"])
        async for row in conversations.find({"user_id": user.id}, {"_id": 1}).limit(500)
    ]
    by_category = [
        {"category": row["_id"], "count": row["count"]}
        async for row in messages.aggregate(
            [
                {
                    "$match": {
                        "conversation_id": {"$in": conv_ids},
                        "safety.category": {"$ne": None},
                        "created_at": {"$gte": since},
                    }
                },
                {"$group": {"_id": "$safety.category", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 16},
            ]
        )
    ]
    return {"by_module": by_module, "by_category": by_category}


@router.get("/activity-heatmap")
async def activity_heatmap(
    user: CurrentUser, container: Container, days: int = Query(90, ge=7, le=365)
) -> dict:
    """Message counts bucketed by weekday × hour (Tashkent time)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    conversations = container.mongo.collection(Collections.CONVERSATIONS)
    conv_ids = [
        str(row["_id"]) async for row in conversations.find({"user_id": user.id}, {"_id": 1})
    ]
    messages = container.mongo.collection(Collections.MESSAGES)
    cells = [
        {"weekday": row["_id"]["dow"], "hour": row["_id"]["hour"], "count": row["count"]}
        async for row in messages.aggregate(
            [
                {
                    "$match": {
                        "conversation_id": {"$in": conv_ids},
                        "role": "user",
                        "created_at": {"$gte": since},
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "dow": {
                                "$dayOfWeek": {
                                    "date": "$created_at", "timezone": "Asia/Tashkent"
                                }
                            },
                            "hour": {
                                "$hour": {"date": "$created_at", "timezone": "Asia/Tashkent"}
                            },
                        },
                        "count": {"$sum": 1},
                    }
                },
            ]
        )
    ]
    return {"cells": cells, "days": days}


@router.get("/business-health")
async def business_health(user: CurrentUser, container: Container) -> dict:
    """Composite score from profile completeness + platform engagement."""
    profile = user.profile
    profile_fields = [
        profile.industry, profile.business_type, profile.goals,
        profile.location, profile.employees, profile.annual_revenue_uzs,
    ]
    profile_score = sum(1 for f in profile_fields if f) / len(profile_fields)

    series = await container.usage_stats.aggregate_for_user(user.id, days=30)
    active_days = len(series)
    engagement_score = min(active_days / 20, 1.0)

    health = round((profile_score * 0.4 + engagement_score * 0.6) * 100)
    recommendations = []
    if profile_score < 1:
        recommendations.append("Biznes profilingizni to'ldiring — AI maslahatlar aniqroq bo'ladi")
    if active_days < 5:
        recommendations.append("Platformadan muntazam foydalaning: haftalik reja va KPI so'rang")
    return {
        "score": health,
        "profile_completeness": round(profile_score * 100),
        "engagement": round(engagement_score * 100),
        "recommendations": recommendations,
    }
