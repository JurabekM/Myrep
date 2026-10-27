"""Sinxronlash endpointlari (ADR-0011)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from zanjir_server.api.deps import Ctx, Engineer, Viewer, fail
from zanjir_server.api.schemas import Strict
from zanjir_server.sync.service import PushRejected, PushService, pull

router = APIRouter(prefix="/sync", tags=["sync"])
log = logging.getLogger("zanjir.sync")


class PushOp(Strict):
    client_op_id: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    table: Annotated[str, StringConstraints(max_length=40)]
    row: dict[str, Any]


class PushIn(Strict):
    ops: list[PushOp] = Field(min_length=1)


class OpResult(BaseModel):
    client_op_id: str
    status: str


class PushOut(BaseModel):
    results: list[OpResult]
    server_rev: int


class PullOut(BaseModel):
    changes: list[dict[str, Any]]
    server_rev: int
    has_more: bool


@router.get("/pull")
async def sync_pull(
    p: Viewer, ctx: Ctx, since: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int | None, Query(ge=1)] = None
) -> PullOut:
    lim = min(limit or ctx.settings.sync_pull_limit, ctx.settings.sync_pull_limit)
    async with ctx.db.org_session(p.org_id) as s:
        changes, more = await pull(s, p.org_id, since, lim)
    last = changes[-1]["server_rev"] if changes else since
    return PullOut(changes=changes, server_rev=last, has_more=more)


@router.post("/push")
async def sync_push(body: PushIn, p: Engineer, ctx: Ctx) -> PushOut:
    if len(body.ops) > ctx.settings.sync_max_ops:
        fail(413, "too_many_ops")
    try:
        async with ctx.db.org_session(p.org_id) as s:
            ops = await PushService(s, p, ctx.now()).run([o.model_dump() for o in body.ops])
            rev = (await s.execute(text("SELECT zanjir_org_rev()"))).scalar_one()
    except PushRejected as e:
        ctx.metrics.sync_rejected.labels(e.reason.split(":")[0]).inc()
        log.warning("push_rejected", extra={"fields": {"reason": e.reason, "ops": len(body.ops)}})
        fail(422, "push_rejected", reason=e.reason, op_id=e.op_id)
    except (IntegrityError, DBAPIError) as e:
        # Kechiktirilgan FK, yagonalik, CHECK — paket rad etiladi. Xato matni (ichida ma'lumot bor) yozilmaydi.
        ctx.metrics.sync_rejected.labels("constraint_violation").inc()
        log.warning("push_rejected", extra={"fields": {"reason": "constraint_violation", "error": type(e).__name__}})
        fail(422, "push_rejected", reason="constraint_violation", op_id=None)
    return PushOut(results=[OpResult(client_op_id=o.client_op_id, status=o.status) for o in ops], server_rev=rev or 0)
