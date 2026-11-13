"""Plagin hook'lari (pluggy). Plagin moduli kerakli funksiyalarni `@hookimpl` bilan belgilaydi."""

from __future__ import annotations

from collections.abc import Awaitable, Sequence
from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    from fastapi import APIRouter

    from srv1_sdk.context import PluginContext
    from srv1_sdk.panel import PanelSpec
    from srv1_sdk.types import EventHandler, Job

PROJECT = "srv1"

hookspec = pluggy.HookspecMarker(PROJECT)
hookimpl = pluggy.HookimplMarker(PROJECT)


class PluginSpec:
    """Hamma hook ixtiyoriy. `ctx` — shu plaginning `PluginContext`i."""

    @hookspec(firstresult=True)
    def srv1_start(self, ctx: PluginContext) -> Awaitable[None] | None:
        """Plagin yoqilganda bir marta. `async def` bo'lishi mumkin."""

    @hookspec(firstresult=True)
    def srv1_stop(self, ctx: PluginContext) -> Awaitable[None] | None:
        """Plagin o'chirilganda yoki yadro to'xtaganda. `async def` bo'lishi mumkin."""

    @hookspec(firstresult=True)
    def srv1_router(self, ctx: PluginContext) -> APIRouter | None:
        """Plagin API'si; `/api/v1/plugins/<nom>/api/...` ostida ko'rinadi."""

    @hookspec(firstresult=True)
    def srv1_subscriptions(self, ctx: PluginContext) -> Sequence[EventHandler] | None:
        """Hodisa obunalari."""

    @hookspec(firstresult=True)
    def srv1_jobs(self, ctx: PluginContext) -> Sequence[Job] | None:
        """Rejalashtirilgan vazifalar."""

    @hookspec(firstresult=True)
    def srv1_panel(self, ctx: PluginContext) -> PanelSpec | dict[str, Any] | None:
        """Shell uchun panel tavsifi."""
