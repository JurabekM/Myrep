"""`hosting` plagini paneli (uch tilda)."""

from srv1_sdk.panel import (
    FormField,
    FormWidget,
    LabelWidget,
    LogWidget,
    PanelSpec,
    RowAction,
    TableColumn,
    TableWidget,
    ValueWidget,
)


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


_NAME = FormField(name="name", label=_t("Loyiha nomi", "Имя проекта", "Project name"))


def _action(uz: str, ru: str, en: str, path: str, *, confirm: bool = False) -> RowAction:
    return RowAction(label=_t(uz, ru, en), path=path, params=("name",), confirm=confirm)


def build_panel() -> PanelSpec:
    return PanelSpec(
        title=_t("Hosting", "Хостинг", "Hosting"),
        widgets=(
            ValueWidget(label="Caddy", source="/status", field="caddy"),
            ValueWidget(
                label=_t("Ishlayapti", "Работает", "Running"), source="/status", field="running"
            ),
            ValueWidget(
                label=_t("Uxlayapti", "Спит", "Sleeping"), source="/status", field="sleeping"
            ),
            ValueWidget(label=_t("Xato", "Сбой", "Failed"), source="/status", field="failed"),
            ValueWidget(
                label=_t("Ochiq tunnellar", "Открытые туннели", "Open tunnels"),
                source="/status",
                field="tunnels",
            ),
            TableWidget(
                label=_t("Loyihalar", "Проекты", "Projects"),
                source="/projects",
                refresh_s=3,
                columns=(
                    TableColumn(key="name", title=_t("Nom", "Имя", "Name")),
                    TableColumn(key="kind", title=_t("Turi", "Тип", "Type")),
                    TableColumn(key="state", title=_t("Holat", "Состояние", "State")),
                    TableColumn(key="url", title=_t("Manzil", "Адрес", "Address")),
                    TableColumn(
                        key="public_url",
                        title=_t("Internetdagi manzil", "Адрес в интернете", "Public address"),
                    ),
                    TableColumn(key="port", title=_t("Port", "Порт", "Port")),
                    TableColumn(key="memory", title="RAM", format="size"),
                    TableColumn(key="error", title=_t("Xato", "Ошибка", "Error")),
                ),
                row_actions=(
                    _action("Ishga tushirish", "Запустить", "Start", "/start"),
                    _action("Toʻxtatish", "Остановить", "Stop", "/stop"),
                    _action("Qayta ishga tushirish", "Перезапустить", "Restart", "/restart"),
                    _action(
                        "Internetga ochish",
                        "Открыть в интернет",
                        "Open to internet",
                        "/tunnel/open",
                        confirm=True,
                    ),
                    _action("Tunnelni yopish", "Закрыть туннель", "Close tunnel", "/tunnel/close"),
                    _action(
                        "Roʻyxatdan chiqarish",
                        "Убрать из списка",
                        "Remove",
                        "/remove",
                        confirm=True,
                    ),
                ),
            ),
            LabelWidget(
                text=_t(
                    "Loyiha fayllari: <maʼlumotlar>/projects/<nom>/. Buyruqda {port} ajratilgan "
                    "portga almashadi; dastur PORT muhit oʻzgaruvchisini ham oladi.",
                    "Файлы проекта: <данные>/projects/<имя>/. В команде {port} заменяется "
                    "выделенным портом; программа также получает переменную PORT.",
                    "Project files: <data>/projects/<name>/. In the command {port} is replaced "
                    "with the allocated port; the program also receives the PORT variable.",
                )
            ),
            LabelWidget(
                text=_t(
                    "«Internetga ochish» loyihani trycloudflare.com dagi tasodifiy manzilda "
                    "HAMMAGA ochadi (parolsiz). Yadro qayta ishga tushsa, tunnellar yopiladi.",
                    "«Открыть в интернет» делает проект доступным ВСЕМ по случайному адресу "
                    "trycloudflare.com (без пароля). После перезапуска ядра туннели закрыты.",
                    "“Open to internet” exposes the project to EVERYONE at a random "
                    "trycloudflare.com address (no password). A core restart closes all tunnels.",
                )
            ),
            FormWidget(
                label=_t("Loyiha qoʻshish", "Добавить проект", "Add project"),
                path="/projects",
                fields=(
                    _NAME,
                    FormField(
                        name="kind",
                        label=_t("Turi", "Тип", "Type"),
                        kind="choice",
                        choices=("static", "python", "node"),
                    ),
                    FormField(
                        name="command",
                        label=_t("Buyruq", "Команда", "Command"),
                        required=False,
                    ),
                    FormField(
                        name="idle_minutes",
                        label=_t(
                            "Uxlatish, daqiqa (0 — yoʻq)",
                            "Сон через, мин (0 — нет)",
                            "Sleep after, min (0 — never)",
                        ),
                        kind="number",
                        required=False,
                    ),
                    FormField(
                        name="memory_limit_mb",
                        label=_t("RAM limiti, MB", "Лимит ОЗУ, МБ", "RAM limit, MB"),
                        kind="number",
                        required=False,
                    ),
                ),
            ),
            LogWidget(
                label=_t("Loyiha jurnali", "Журнал проекта", "Project log"),
                source="/log",
                filters=(_NAME,),
            ),
        ),
    )
