"""`itops` plagini paneli (uch tilda)."""

from srv1_sdk.panel import (
    ButtonWidget,
    FormField,
    FormWidget,
    PanelSpec,
    RowAction,
    TableColumn,
    TableWidget,
    ValueWidget,
)


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


_SEARCH = FormField(name="search", label=_t("Qidiruv", "Поиск", "Search"), required=False)
_NAME = TableColumn(key="name", title=_t("Nom", "Имя", "Name"))
_PROTECTED = TableColumn(key="protected", title=_t("Himoyalangan", "Защищён", "Protected"))


def _process_table() -> TableWidget:
    return TableWidget(
        label=_t("Jarayonlar", "Процессы", "Processes"),
        source="/processes",
        refresh_s=5,
        filters=(
            _SEARCH,
            FormField(
                name="sort",
                label=_t("Saralash", "Сортировка", "Sort by"),
                kind="choice",
                choices=("memory", "cpu", "name", "pid"),
                required=False,
            ),
        ),
        columns=(
            TableColumn(key="pid", title="PID"),
            _NAME,
            TableColumn(key="user", title=_t("Foydalanuvchi", "Пользователь", "User")),
            TableColumn(key="cpu", title="CPU %"),
            TableColumn(key="memory", title=_t("Xotira", "Память", "Memory"), format="size"),
            TableColumn(
                key="started", title=_t("Boshlangan", "Запущен", "Started"), format="datetime"
            ),
            _PROTECTED,
        ),
        row_actions=(
            RowAction(
                label=_t("Jarayonni toʻxtatish", "Завершить процесс", "End process"),
                path="/processes/kill",
                params=("pid", "started"),
                confirm=True,
            ),
        ),
    )


def _service_table() -> TableWidget:
    return TableWidget(
        label=_t("Windows xizmatlari", "Службы Windows", "Windows services"),
        source="/services",
        refresh_s=10,
        filters=(
            _SEARCH,
            FormField(
                name="state",
                label=_t("Holat", "Состояние", "State"),
                kind="choice",
                choices=("", "running", "stopped"),
                required=False,
            ),
        ),
        columns=(
            _NAME,
            TableColumn(key="state", title=_t("Holat", "Состояние", "State")),
            TableColumn(key="start", title=_t("Ishga tushish", "Запуск", "Startup")),
            TableColumn(key="pid", title="PID"),
            _PROTECTED,
            # Uzun matn oxirida: holat ustuni ko'rinmay qolmasin.
            TableColumn(key="title", title=_t("Tavsif", "Описание", "Title")),
        ),
        row_actions=(
            RowAction(
                label=_t("Ishga tushirish", "Запустить", "Start"),
                path="/services/start",
                params=("name",),
            ),
            RowAction(
                label=_t("Toʻxtatish", "Остановить", "Stop"),
                path="/services/stop",
                params=("name",),
                confirm=True,
            ),
            RowAction(
                label=_t("Qayta ishga tushirish", "Перезапустить", "Restart"),
                path="/services/restart",
                params=("name",),
                confirm=True,
            ),
        ),
    )


def _scan_widgets() -> tuple[TableWidget | FormWidget | ValueWidget, ...]:
    return (
        TableWidget(
            label=_t("Mahalliy tarmoqlar", "Локальные сети", "Local networks"),
            source="/networks",
            refresh_s=30,
            columns=(
                TableColumn(key="network", title=_t("Tarmoq", "Сеть", "Network")),
                TableColumn(key="address", title=_t("Oʻz manzil", "Свой адрес", "Own address")),
            ),
            row_actions=(
                RowAction(
                    label=_t("Skanerlash", "Сканировать", "Scan"),
                    path="/scan",
                    params=("network",),
                    confirm=True,
                ),
            ),
        ),
        ValueWidget(
            label=_t("Skaner holati", "Состояние сканера", "Scan state"),
            source="/scan",
            field="state",
            refresh_s=1,
        ),
        ValueWidget(
            label=_t("Skaner jarayoni", "Ход сканирования", "Scan progress"),
            source="/scan",
            field="progress",
            refresh_s=1,
        ),
        TableWidget(
            label=_t("Topilgan qurilmalar", "Найденные устройства", "Devices found"),
            source="/scan/hosts",
            refresh_s=3,
            columns=(
                TableColumn(key="ip", title="IP"),
                TableColumn(key="mac", title="MAC"),
                TableColumn(key="name", title=_t("Nom", "Имя", "Name")),
                TableColumn(key="ports", title=_t("Ochiq portlar", "Открытые порты", "Open ports")),
                TableColumn(key="seen", title=_t("Manba", "Источник", "Seen via")),
            ),
        ),
    )


def _backup_widgets() -> tuple[ValueWidget | ButtonWidget | TableWidget, ...]:
    return (
        ValueWidget(
            label=_t("Zaxira holati", "Состояние копирования", "Backup state"),
            source="/status",
            field="backup_state",
            refresh_s=2,
        ),
        ValueWidget(
            label=_t("Jadval (cron)", "Расписание (cron)", "Schedule (cron)"),
            source="/status",
            field="backup_cron",
        ),
        ButtonWidget(
            label=_t("Hozir zaxira olish", "Создать копию сейчас", "Back up now"),
            path="/backups/run",
        ),
        TableWidget(
            label=_t("Zaxira nusxalar", "Резервные копии", "Backups"),
            source="/backups",
            refresh_s=5,
            columns=(
                TableColumn(key="name", title=_t("Fayl", "Файл", "File")),
                TableColumn(key="size", title=_t("Hajm", "Размер", "Size"), format="size"),
                TableColumn(
                    key="created", title=_t("Yaratilgan", "Создана", "Created"), format="datetime"
                ),
            ),
            row_actions=(
                RowAction(
                    label=_t("Oʻchirish", "Удалить", "Delete"),
                    path="/backups/remove",
                    params=("name",),
                    confirm=True,
                ),
            ),
        ),
    )


def build_panel() -> PanelSpec:
    return PanelSpec(
        title=_t("IT boshqaruvi", "Администрирование", "IT operations"),
        widgets=(
            _process_table(),
            _service_table(),
            *_scan_widgets(),
            *_backup_widgets(),
        ),
    )
