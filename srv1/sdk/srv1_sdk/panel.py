"""Shell uchun panel tavsifi. Shell shu JSON bo'yicha chizadi; plagin GUI kodi yozmaydi.

`source` va `path` — plaginning o'z API'siga nisbatan yo'l (`/stats`), ya'ni
`/api/v1/plugins/<nom>/api/stats`. `topic` — `plugin.<nom>.` dan keyingi qism.
"""

from typing import Annotated, Any, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

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
    # Xavfli amal: shell yuborishdan oldin tasdiq so'raydi.
    confirm: bool = False


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
    """`plugin.<nom>.<topic>` hodisasidagi `field` qiymatining jonli grafigi.

    `history` berilsa, panel ochilganda `GET <history>?limit=<window>` chaqiriladi:
    javob — obyektlar ro'yxati (eskidan yangiga), har biridan `field` olinadi.
    Busiz grafik faqat panel ochiq turgan paytdagi hodisalarni ko'rsatadi.
    """

    type: Literal["chart"] = "chart"
    label: LocalizedText
    topic: str = Field(pattern=r"^[a-z0-9_.-]{1,64}$")
    field: str
    window: int = Field(default=120, ge=10, le=5000)
    history: Annotated[str, _PATH] | None = None
    # Ikkalasi berilsa, Y o'qi shu oraliqda qotiriladi (masalan foiz uchun 0–100).
    y_min: float | None = None
    y_max: float | None = None

    @model_validator(mode="after")
    def _y_range(self) -> Self:
        if (self.y_min is None) != (self.y_max is None):
            raise ValueError("y_min va y_max birga beriladi")
        if self.y_min is not None and self.y_max is not None and self.y_max <= self.y_min:
            raise ValueError("y_max y_min dan katta bo'lishi kerak")
        return self


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
