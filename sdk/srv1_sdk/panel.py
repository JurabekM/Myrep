"""Shell uchun panel tavsifi. Shell shu JSON bo'yicha chizadi; plagin GUI kodi yozmaydi.

`source` va `path` — plaginning o'z API'siga nisbatan yo'l (`/stats`), ya'ni
`/api/v1/plugins/<nom>/api/stats`. `topic` — `plugin.<nom>.` dan keyingi qism.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_PATH = Field(pattern=r"^/[A-Za-z0-9_\-./]*$", max_length=200)
HttpMethod = Literal["GET", "POST", "PUT", "DELETE"]


class _Widget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LabelWidget(_Widget):
    type: Literal["label"] = "label"
    text: str


class ValueWidget(_Widget):
    """`source` dan JSON olib, `field` kalitini ko'rsatadi."""

    type: Literal["value"] = "value"
    label: str
    source: Annotated[str, _PATH]
    field: str
    refresh_s: float = Field(default=5.0, ge=0.5)


class ButtonWidget(_Widget):
    type: Literal["button"] = "button"
    label: str
    method: HttpMethod = "POST"
    path: Annotated[str, _PATH]
    confirm: bool = False


class FormField(_Widget):
    name: str
    label: str
    kind: Literal["text", "number", "bool", "choice"] = "text"
    choices: tuple[str, ...] = ()
    required: bool = True


class FormWidget(_Widget):
    """Maydonlar `GET`da so'rov parametri, boshqa metodlarda JSON tana bo'lib yuboriladi."""

    type: Literal["form"] = "form"
    label: str
    method: HttpMethod = "POST"
    path: Annotated[str, _PATH]
    fields: tuple[FormField, ...]


class TableColumn(_Widget):
    key: str
    title: str


class TableWidget(_Widget):
    """`source` JSON ro'yxat (obyektlar) qaytaradi."""

    type: Literal["table"] = "table"
    label: str
    source: Annotated[str, _PATH]
    columns: tuple[TableColumn, ...]
    refresh_s: float = Field(default=5.0, ge=0.5)


class ChartWidget(_Widget):
    """`plugin.<nom>.<topic>` hodisasidagi `field` qiymatining jonli grafigi."""

    type: Literal["chart"] = "chart"
    label: str
    topic: str = Field(pattern=r"^[a-z0-9_.-]{1,64}$")
    field: str
    window: int = Field(default=120, ge=10, le=5000)


Widget = Annotated[
    LabelWidget | ValueWidget | ButtonWidget | FormWidget | TableWidget | ChartWidget,
    Field(discriminator="type"),
]


class PanelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=60)
    widgets: tuple[Widget, ...] = Field(max_length=64)


def parse_panel(raw: Any) -> PanelSpec | None:  # noqa: ANN401 — plagin qaytargan xom qiymat
    """Plagin `PanelSpec` yoki `dict` qaytarishi mumkin; `None` — panel yo'q."""
    if raw is None or isinstance(raw, PanelSpec):
        return raw
    return PanelSpec.model_validate(raw)
