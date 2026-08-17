"""MongoDB implementations of the repository ports."""

from datetime import date, datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.entities.conversation import Conversation, Message
from app.domain.entities.user import User
from app.domain.interfaces.repositories import (
    AuditLogRepository,
    ConversationRepository,
    MessageRepository,
    UsageStatsRepository,
    UserRepository,
)
from app.infrastructure.database.mongo import Collections, MongoManager


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise NotFoundError("Resurs topilmadi", details={"id": value}) from exc


def _doc_to_model(doc: dict[str, Any], model: type) -> Any:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return model.model_validate(doc)


def _model_to_doc(entity: Any) -> dict[str, Any]:
    doc = entity.model_dump(mode="python")
    entity_id = doc.pop("id")
    doc["_id"] = ObjectId(entity_id) if ObjectId.is_valid(entity_id) else entity_id
    return doc


class MongoUserRepository(UserRepository):
    def __init__(self, mongo: MongoManager):
        self._coll = mongo.collection(Collections.USERS)

    async def create(self, user: User) -> User:
        try:
            await self._coll.insert_one(_model_to_doc(user))
        except DuplicateKeyError as exc:
            raise ConflictError("Bu email allaqachon ro'yxatdan o'tgan") from exc
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        doc = await self._coll.find_one({"_id": _oid(user_id)})
        return _doc_to_model(doc, User) if doc else None

    async def get_by_email(self, email: str) -> User | None:
        doc = await self._coll.find_one({"email": email.lower()})
        return _doc_to_model(doc, User) if doc else None

    async def update(self, user_id: str, fields: dict[str, Any]) -> User:
        fields = {**fields, "updated_at": datetime.now(timezone.utc)}
        doc = await self._coll.find_one_and_update(
            {"_id": _oid(user_id)},
            {"$set": fields},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise NotFoundError("Foydalanuvchi topilmadi", details={"user_id": user_id})
        return _doc_to_model(doc, User)

    async def list_paginated(
        self, *, skip: int, limit: int, filters: dict[str, Any] | None = None
    ) -> tuple[list[User], int]:
        query = filters or {}
        total = await self._coll.count_documents(query)
        cursor = self._coll.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [_doc_to_model(d, User) async for d in cursor], total


class MongoConversationRepository(ConversationRepository):
    def __init__(self, mongo: MongoManager):
        self._coll = mongo.collection(Collections.CONVERSATIONS)

    async def create(self, conversation: Conversation) -> Conversation:
        await self._coll.insert_one(_model_to_doc(conversation))
        return conversation

    async def get(self, conversation_id: str, user_id: str) -> Conversation | None:
        doc = await self._coll.find_one({"_id": _oid(conversation_id), "user_id": user_id})
        return _doc_to_model(doc, Conversation) if doc else None

    async def list_for_user(self, user_id: str, *, skip: int, limit: int) -> list[Conversation]:
        cursor = (
            self._coll.find({"user_id": user_id})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [_doc_to_model(d, Conversation) async for d in cursor]

    async def update(self, conversation_id: str, fields: dict[str, Any]) -> None:
        fields = {**fields, "updated_at": datetime.now(timezone.utc)}
        await self._coll.update_one({"_id": _oid(conversation_id)}, {"$set": fields})

    async def delete(self, conversation_id: str, user_id: str) -> bool:
        result = await self._coll.delete_one({"_id": _oid(conversation_id), "user_id": user_id})
        return result.deleted_count == 1


class MongoMessageRepository(MessageRepository):
    def __init__(self, mongo: MongoManager):
        self._coll = mongo.collection(Collections.MESSAGES)

    async def add(self, message: Message) -> Message:
        await self._coll.insert_one(_model_to_doc(message))
        return message

    async def list_for_conversation(
        self, conversation_id: str, *, limit: int = 50, before_id: str | None = None
    ) -> list[Message]:
        query: dict[str, Any] = {"conversation_id": conversation_id}
        if before_id is not None:
            query["_id"] = {"$lt": _oid(before_id)}
        cursor = self._coll.find(query).sort("_id", -1).limit(limit)
        messages = [_doc_to_model(d, Message) async for d in cursor]
        return list(reversed(messages))  # chronological order

    async def set_feedback(self, message_id: str, feedback: int) -> None:
        result = await self._coll.update_one(
            {"_id": _oid(message_id)}, {"$set": {"feedback": feedback}}
        )
        if result.matched_count == 0:
            raise NotFoundError("Xabar topilmadi", details={"message_id": message_id})

    async def text_search(self, query: str, *, limit: int) -> list[Message]:
        cursor = (
            self._coll.find(
                {"$text": {"$search": query}}, {"score": {"$meta": "textScore"}}
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
        return [_doc_to_model(d, Message) async for d in cursor]


class MongoUsageStatsRepository(UsageStatsRepository):
    def __init__(self, mongo: MongoManager):
        self._coll = mongo.collection(Collections.USAGE_STATS)

    async def record(
        self, user_id: str, day: date, module: str, *, tokens: int, cost_usd: float
    ) -> None:
        await self._coll.update_one(
            {"user_id": user_id, "date": day.isoformat(), "module": module},
            {"$inc": {"tokens": tokens, "cost_usd": cost_usd, "requests": 1}},
            upsert=True,
        )

    async def aggregate_for_user(self, user_id: str, *, days: int) -> list[dict[str, Any]]:
        cursor = self._coll.aggregate(
            [
                {"$match": {"user_id": user_id}},
                {"$sort": {"date": -1}},
                {"$limit": days * 10},
                {
                    "$group": {
                        "_id": "$date",
                        "tokens": {"$sum": "$tokens"},
                        "cost_usd": {"$sum": "$cost_usd"},
                        "requests": {"$sum": "$requests"},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
        )
        return [
            {"date": d["_id"], **{k: d[k] for k in ("tokens", "cost_usd", "requests")}}
            async for d in cursor
        ]


class MongoAuditLogRepository(AuditLogRepository):
    def __init__(self, mongo: MongoManager):
        self._coll = mongo.collection(Collections.AUDIT_LOGS)

    async def record(
        self,
        *,
        actor_id: str,
        action: str,
        resource: str,
        ip: str | None = None,
        user_agent: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        await self._coll.insert_one(
            {
                "actor_id": actor_id,
                "action": action,
                "resource": resource,
                "ip": ip,
                "user_agent": user_agent,
                "before": before,
                "after": after,
                "created_at": datetime.now(timezone.utc),
            }
        )
