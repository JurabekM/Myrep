"""`hello` — namuna plagin. Yangi plagin yozishda shu fayldan nusxa oling.

Ko'rsatadi: API router, davriy vazifa, hodisa nashri va obunasi, o'z papkasiga
yozish, audit va panel tavsifi. `plugin.toml` da `mode = "subprocess"` qilinsa,
shu kod o'zgarishsiz alohida jarayonda ishlaydi.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from srv1_sdk.context import PluginContext
from srv1_sdk.hookspec import hookimpl
from srv1_sdk.panel import (
    ButtonWidget,
    ChartWidget,
    FormField,
    FormWidget,
    LabelWidget,
    PanelSpec,
    ValueWidget,
)
from srv1_sdk.types import EventHandler, Job

TICK_INTERVAL_S = 10.0
NOTES_FILE = "notes.txt"


@dataclass(slots=True)
class _State:
    ticks: int = 0
    ticks_seen: int = 0
    started: bool = False


_state = _State()


class Greeting(BaseModel):
    message: str


class Stats(BaseModel):
    ticks: int
    ticks_seen: int
    notes: int


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=200)


def _note_count(ctx: PluginContext) -> int:
    notes = ctx.data_path(NOTES_FILE)
    return len(notes.read_text(encoding="utf-8").splitlines()) if notes.is_file() else 0


async def _tick(ctx: PluginContext) -> None:
    _state.ticks += 1
    ctx.publish("tick", {"n": _state.ticks})


@hookimpl
def srv1_start(ctx: PluginContext) -> None:
    _state.ticks = _state.ticks_seen = 0
    _state.started = True
    ctx.log("info", "hello_started")


@hookimpl
def srv1_stop(ctx: PluginContext) -> None:
    _state.started = False


@hookimpl
def srv1_router(ctx: PluginContext) -> APIRouter:
    router = APIRouter()

    @router.get("/greet")
    async def greet(name: str = "dunyo") -> Greeting:  # pyright: ignore[reportUnusedFunction]
        return Greeting(message=f"Salom, {name}!")

    @router.get("/stats")
    async def stats() -> Stats:  # pyright: ignore[reportUnusedFunction]
        return Stats(ticks=_state.ticks, ticks_seen=_state.ticks_seen, notes=_note_count(ctx))

    @router.post("/tick")
    async def tick_now() -> Stats:  # pyright: ignore[reportUnusedFunction]
        await _tick(ctx)
        return await stats()

    @router.post("/notes", status_code=201)
    async def add_note(note: NoteIn) -> Stats:  # pyright: ignore[reportUnusedFunction]
        with ctx.data_path(NOTES_FILE).open("a", encoding="utf-8") as fh:
            fh.write(note.text.replace("\n", " ") + "\n")
        return await stats()

    @router.delete("/notes")
    async def clear_notes() -> Stats:  # pyright: ignore[reportUnusedFunction]
        notes = ctx.data_path(NOTES_FILE)
        existed = notes.is_file()
        notes.unlink(missing_ok=True)
        await ctx.audit("file.delete", str(notes), ok=True, detail={"existed": existed})
        return await stats()

    return router


@hookimpl
def srv1_jobs(ctx: PluginContext) -> list[Job]:
    async def tick() -> None:
        await _tick(ctx)

    return [Job(id="tick", func=tick, interval_s=TICK_INTERVAL_S)]


@hookimpl
def srv1_subscriptions(ctx: PluginContext) -> list[EventHandler]:
    async def on_tick(topic: str, data: Mapping[str, Any]) -> None:
        _state.ticks_seen += 1

    return [EventHandler(f"plugin.{ctx.name}.tick", on_tick)]


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


@hookimpl
def srv1_panel(ctx: PluginContext) -> PanelSpec:
    return PanelSpec(
        title=_t("Salom", "Привет", "Hello"),
        widgets=(
            LabelWidget(
                text=_t(
                    "Namuna plagin: har 10 soniyada bitta «tick» hodisasi.",
                    "Пример плагина: одно событие «tick» каждые 10 секунд.",
                    "Sample plugin: one “tick” event every 10 seconds.",
                )
            ),
            ValueWidget(
                label=_t("Ticklar", "Тики", "Ticks"), source="/stats", field="ticks", refresh_s=2.0
            ),
            ValueWidget(
                label=_t("Eslatmalar", "Заметки", "Notes"),
                source="/stats",
                field="notes",
                refresh_s=2.0,
            ),
            ChartWidget(
                label=_t("Tick raqami", "Номер тика", "Tick number"), topic="tick", field="n"
            ),
            ButtonWidget(label=_t("Hozir tick", "Тик сейчас", "Tick now"), path="/tick"),
            FormWidget(
                label=_t("Salomlashish", "Приветствие", "Greeting"),
                method="GET",
                path="/greet",
                fields=(FormField(name="name", label=_t("Ism", "Имя", "Name"), required=False),),
            ),
            FormWidget(
                label=_t("Eslatma qo'shish", "Добавить заметку", "Add a note"),
                path="/notes",
                fields=(FormField(name="text", label=_t("Matn", "Текст", "Text")),),
            ),
            ButtonWidget(
                label=_t("Eslatmalarni o'chirish", "Удалить заметки", "Delete notes"),
                method="DELETE",
                path="/notes",
                confirm=True,
            ),
        ),
    )
