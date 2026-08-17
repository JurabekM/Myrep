"""Supabase / PostgREST transport.

Talks plain HTTPS to a PostgREST endpoint (Supabase's free Postgres tier is the
default target), so it works from any office network without extra ports or a
database driver. The server side is a single append-only table — see
``SETUP_SQL`` and the README.
"""

from __future__ import annotations

import json
from typing import Any

from app.sync.transports.base import Change, TransportError

try:  # pragma: no cover - optional at import time
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

TABLE = "bc_changes"
TIMEOUT = 20

#: Run this once in the Supabase SQL editor to prepare the project.
SETUP_SQL = """
-- BuildControl sinxronizatsiya jurnali
create table if not exists public.bc_changes (
    seq     bigserial primary key,
    tenant  text        not null,
    device  text        not null,
    entity  text        not null,
    uid     text        not null,
    op      text        not null default 'upsert',
    payload jsonb       not null default '{}'::jsonb,
    ts      timestamptz not null default now()
);

create index if not exists bc_changes_tenant_seq_idx
    on public.bc_changes (tenant, seq);

alter table public.bc_changes enable row level security;

-- Test bosqichi uchun: anon kalit bilan o'qish va yozishga ruxsat.
-- Ishlab chiqarishda buni Supabase Auth bilan cheklang.
drop policy if exists bc_changes_rw on public.bc_changes;
create policy bc_changes_rw on public.bc_changes
    for all to anon, authenticated
    using (true) with check (true);
"""


class SupabaseTransport:
    """Append-only change log stored in a Supabase (PostgREST) table."""

    key = "supabase"

    def __init__(self, url: str, api_key: str, tenant: str = "default") -> None:
        self.url = (url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.tenant = tenant or "default"
        if requests is None:  # pragma: no cover - dependency guard
            raise TransportError("`requests` kutubxonasi o'rnatilmagan")
        if not self.url or not self.api_key:
            raise TransportError("Supabase URL yoki API kaliti to'ldirilmagan")

    # -- helpers -------------------------------------------------------------- #
    @property
    def _endpoint(self) -> str:
        return f"{self.url}/rest/v1/{TABLE}"

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(self, method: str, **kwargs: Any):
        try:
            response = requests.request(
                method,
                self._endpoint,
                headers=self._headers(kwargs.pop("headers", None)),
                timeout=TIMEOUT,
                **kwargs,
            )
        except Exception as exc:  # network errors of any kind
            raise TransportError(f"Serverga ulanib bo'lmadi: {exc}") from exc
        if response.status_code >= 400:
            detail = response.text[:300]
            if response.status_code in (401, 403):
                raise TransportError(f"Kirish rad etildi ({response.status_code}). {detail}")
            if response.status_code == 404:
                raise TransportError(
                    f"'{TABLE}' jadvali topilmadi — Supabase SQL editor'da SETUP_SQL ni bajaring."
                )
            raise TransportError(f"Server xatosi {response.status_code}: {detail}")
        return response

    # -- transport API -------------------------------------------------------- #
    def describe(self) -> str:
        return f"{self.url}  ({self.tenant})"

    def check(self) -> str:
        response = self._request(
            "GET",
            params={
                "tenant": f"eq.{self.tenant}",
                "select": "seq",
                "order": "seq.desc",
                "limit": 1,
            },
            headers={"Prefer": "count=exact"},
        )
        rows = response.json()
        last = rows[0]["seq"] if rows else 0
        total = response.headers.get("content-range", "").split("/")[-1]
        return f"OK · oxirgi seq={last} · jami={total or '?'}"

    def push(self, changes: list[Change]) -> int:
        if not changes:
            return 0
        body = [change.to_wire(self.tenant) for change in changes]
        self._request(
            "POST",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Prefer": "return=minimal"},
        )
        return len(changes)

    def pull(self, after: str, limit: int = 500) -> list[Change]:
        try:
            last = int(after or 0)
        except ValueError:
            last = 0
        response = self._request(
            "GET",
            params={
                "tenant": f"eq.{self.tenant}",
                "seq": f"gt.{last}",
                "select": "seq,device,entity,uid,op,payload,ts",
                "order": "seq.asc",
                "limit": limit,
            },
        )
        return [Change.from_wire(row, str(row["seq"])) for row in response.json()]
