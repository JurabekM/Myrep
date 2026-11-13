"""`electronics` plagini paneli (uch tilda)."""

from srv1_sdk.panel import (
    ButtonWidget,
    FormField,
    FormWidget,
    LogWidget,
    PanelSpec,
    RowAction,
    TableColumn,
    TableWidget,
    ValueWidget,
)

from .models import BOARDS


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


_PORT = FormField(name="port", label=_t("Port", "Порт", "Port"))
_BAUD = FormField(
    name="baudrate", label=_t("Tezlik", "Скорость", "Baud rate"), kind="number", required=False
)


def _flash_widgets() -> tuple[FormWidget | LogWidget | ButtonWidget | TableWidget, ...]:
    return (
        FormWidget(
            label=_t("Proshivka yozish", "Записать прошивку", "Flash firmware"),
            path="/flash",
            confirm=True,
            fields=(
                _PORT,
                FormField(
                    name="board",
                    label=_t("Plata", "Плата", "Board"),
                    kind="choice",
                    choices=tuple(BOARDS),
                ),
                FormField(name="file", label=_t("Fayl", "Файл", "File")),
                FormField(
                    name="offset",
                    label=_t("Manzil (faqat ESP)", "Адрес (только ESP)", "Offset (ESP only)"),
                    required=False,
                ),
                FormField(
                    name="backup",
                    label=_t(
                        "Avval eski proshivkani saqlash (ESP)",
                        "Сначала сохранить старую прошивку (ESP)",
                        "Back up current firmware first (ESP)",
                    ),
                    kind="bool",
                ),
            ),
        ),
        LogWidget(
            label=_t("Proshivka jurnali", "Журнал прошивки", "Flash log"),
            source="/flash/log",
            refresh_s=1,
        ),
        ButtonWidget(
            label=_t("Yozishni toʻxtatish", "Прервать запись", "Cancel flashing"),
            path="/flash/cancel",
            confirm=True,
        ),
        TableWidget(
            label=_t("Proshivka fayllari", "Файлы прошивок", "Firmware files"),
            source="/firmware",
            refresh_s=10,
            columns=(
                TableColumn(key="name", title=_t("Fayl", "Файл", "File")),
                TableColumn(key="size", title=_t("Hajm", "Размер", "Size"), format="size"),
                TableColumn(
                    key="modified", title=_t("Oʻzgargan", "Изменён", "Modified"), format="datetime"
                ),
            ),
        ),
        TableWidget(
            label=_t("Oxirgi urinishlar", "Последние попытки", "Recent attempts"),
            source="/flash/history",
            refresh_s=3,
            columns=(
                TableColumn(key="started", title=_t("Vaqt", "Время", "Time"), format="datetime"),
                TableColumn(key="port", title=_t("Port", "Порт", "Port")),
                TableColumn(key="board", title=_t("Plata", "Плата", "Board")),
                TableColumn(key="file", title=_t("Fayl", "Файл", "File")),
                TableColumn(key="state", title=_t("Natija", "Результат", "Result")),
                TableColumn(key="seconds", title=_t("Soniya", "Секунд", "Seconds")),
                TableColumn(key="error", title=_t("Xato", "Ошибка", "Error")),
            ),
        ),
    )


def _monitor_widgets() -> tuple[FormWidget | LogWidget, ...]:
    return (
        FormWidget(
            label=_t("Monitorni ochish", "Открыть монитор", "Open monitor"),
            path="/monitor/open",
            fields=(_PORT, _BAUD),
        ),
        FormWidget(
            label=_t("Portga yozish", "Записать в порт", "Write to port"),
            path="/monitor/write",
            fields=(_PORT, FormField(name="text", label=_t("Matn", "Текст", "Text"))),
        ),
        LogWidget(
            label=_t("Serial monitor", "Монитор порта", "Serial monitor"),
            source="/monitor/lines",
            refresh_s=1,
            filters=(_PORT,),
        ),
    )


def build_panel() -> PanelSpec:
    return PanelSpec(
        title=_t("Elektronika", "Электроника", "Electronics"),
        widgets=(
            ValueWidget(label="esptool", source="/status", field="esptool", refresh_s=3),
            ValueWidget(label="avrdude", source="/status", field="avrdude"),
            ValueWidget(
                label=_t("Proshivka holati", "Состояние прошивки", "Flash state"),
                source="/status",
                field="flash_state",
            ),
            TableWidget(
                label=_t("Portlar va platalar", "Порты и платы", "Ports and boards"),
                source="/ports",
                refresh_s=3,
                columns=(
                    TableColumn(key="port", title=_t("Port", "Порт", "Port")),
                    TableColumn(key="chip", title=_t("Qurilma", "Устройство", "Device")),
                    TableColumn(
                        key="board", title=_t("Taxminiy plata", "Вероятная плата", "Likely board")
                    ),
                    TableColumn(key="usb", title="USB"),
                    TableColumn(key="allowed", title=_t("Ruxsat", "Разрешён", "Allowed")),
                    TableColumn(key="monitor", title=_t("Monitor", "Монитор", "Monitor")),
                    TableColumn(key="description", title=_t("Tavsif", "Описание", "Description")),
                ),
                row_actions=(
                    RowAction(
                        label=_t("Monitorni ochish", "Открыть монитор", "Open monitor"),
                        path="/monitor/open",
                        params=("port",),
                    ),
                    RowAction(
                        label=_t("Monitorni yopish", "Закрыть монитор", "Close monitor"),
                        path="/monitor/close",
                        params=("port",),
                    ),
                ),
            ),
            *_flash_widgets(),
            *_monitor_widgets(),
        ),
    )
