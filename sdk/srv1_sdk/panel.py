"""Shell uchun panel tavsifi. Shell shu JSON bo'yicha chizadi; plagin GUI kodi yozmaydi.

`source` va `path` — plaginning o'z API'siga nisbatan yo'l (`/stats`), ya'ni
`/api/v1/plugins/<nom>/api/stats`. `topic` — `plugin.<nom>.` dan keyingi qism.
"""

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

_PATH = Field(pattern=r"^/[A-Za-z0-9_\-./]*$", max_length=200)
LANGUAGES = ("uz", "ru", "en")


def _check_localized(value: str | dict[str, str]) -> str | dict[str, str]:
    if isinstance(value, dict):
        unknown = set(value) - set(LANGUAGES)
        if unknown or not value:
            raise ValueError(f"til kalitlari faqat {LANGUAGES} bo'lishi mumkin")
    return value


# Bitta satr (hamma tilda bir xil) yoki `{"uz": ..., "ru": ..., "en": ...}`.
LocalizedText = Annotated[str | dict[str, str], AfterValidator(_check_localized)]


def localize(text: str | dict[str, str], language: str) -> str:
    """Kerakli tildagi matn; yo'q bo'lsa `en`, `uz`, so'ng mavjud birinchisi."""
    if isinstance(text, str):
        return text
    for candidate in (language, "en", "uz"):
        if candidate in text:
            return text[candidate]
    return next(iter(text.values()))


HttpMethod = Literal["GET", "POST", "PUT", "DELETE"]


class _Widget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LabelWidget(_Widget):
    type: Literal["label"] = "label"
    text: LocalizedText


class ValueWidget(_Widget):
    """`source` dan JSON olib, `field` kalitini ko'rsatadi."""

    type: Literal["value"] = "value"
    label: LocalizedText
    source: Annotated[str, _PATH]
    field: str
    refresh_s: float = Field(default=5.0, ge=0.5)


class ButtonWidget(_Widget):
    type: Literal["button"] = "button"
    label: LocalizedText
    method: HttpMethod = "POST"
    path: Annotated[str, _PATH]
    confirm: bool = False


class FormField(_Widget):
    name: str
    label: LocalizedText
    kind: Literal["text", "number", "bool", "choice"] = "text"
    choices: tuple[str, ...] = ()
    required: bool = True


class FormWidget(_Widget):
    """Maydonlar `GET`da so'rov parametri, boshqa metodlarda JSON tana bo'lib yuboriladi."""

    type: Literal["form"] = "form"
    label: LocalizedText
    method: HttpMethod = "POST"
    path: Annotated[str, _PATH]
    fields: tuple[FormField, ...]


class TableColumn(_Widget):
    key: str
    title: LocalizedText
    # size — baytlar (shell birlik qo'shadi); datetime — Unix vaqti (soniya).
    format: Literal["text", "size", "datetime"] = "text"


class RowAction(_Widget):
    """Tanlangan qator ustidagi amal: `params` dagi kalitlar qatordan olinib, JSON tana bo'ladi."""

    label: LocalizedText
    method: HttpMethod = "POST"
    path: Annotated[str, _PATH]
    params: tuple[str, ...]
    confirm: bool = False


class TableWidget(_Widget):
    """`source` JSON ro'yxat (obyektlar) qaytaradi.

    `filters` bo'lsa, ular so'rov parametri bo'lib yuboriladi (qidiruv jadvali).
    """

    type: Literal["table"] = "table"
    label: LocalizedText
    source: Annotated[str, _PATH]
    columns: tuple[TableColumn, ...]
    refresh_s: float = Field(default=5.0, ge=0.5)
    auto_refresh: bool = True
    filters: tuple[FormField, ...] = ()
    row_actions: tuple[RowAction, ...] = ()


class LogWidget(_Widget):
    """`source` satrlar ro'yxatini qaytaradi; `filters` so'rov parametri bo'lib yuboriladi."""

    type: Literal["log"] = "log"
    label: LocalizedText
    source: Annotated[str, _PATH]
    refresh_s: float = Field(default=3.0, ge=0.5)
    filters: tuple[FormField, ...] = ()


class QueryWidget(_Widget):
    """Ko'p qatorli so'rov matni + natija jadvali (ustunlar javobdan olinadi).

    Matn `path` ga `POST {<field>: matn}` bo'lib yuboriladi. Javob:
    `{columns: [{name, type}], rows: [[...]], truncated, seconds}`.
    """

    type: Literal["query"] = "query"
    label: LocalizedText
    path: Annotated[str, _PATH]
    field: str = Field(default="sql", pattern=r"^[a-z_]{1,32}$")
    placeholder: LocalizedText = ""


class ChartWidget(_Widget):
    """`plugin.<nom>.<topic>` hodisasidagi `field` qiymatining jonli grafigi."""

    type: Literal["chart"] = "chart"
    label: LocalizedText
    topic: str = Field(pattern=r"^[a-z0-9_.-]{1,64}$")
    field: str
    window: int = Field(default=120, ge=10, le=5000)


Widget = Annotated[
    LabelWidget
    | ValueWidget
    | ButtonWidget
    | FormWidget
    | TableWidget
    | LogWidget
    | QueryWidget
    | ChartWidget,
    Field(discriminator="type"),
]


class PanelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: LocalizedText
    widgets: tuple[Widget, ...] = Field(max_length=64)


def parse_panel(raw: Any) -> PanelSpec | None:  # noqa: ANN401 — plagin qaytargan xom qiymat
    """Plagin `PanelSpec` yoki `dict` qaytarishi mumkin; `None` — panel yo'q."""
    if raw is None or isinstance(raw, PanelSpec):
        return raw
    return PanelSpec.model_validate(raw)
