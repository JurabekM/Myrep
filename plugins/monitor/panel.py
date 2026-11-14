"""`monitor` paneli tavsifi (shell shu bo'yicha chizadi)."""

from srv1_sdk.panel import (
    ButtonWidget,
    ChartWidget,
    FormField,
    FormWidget,
    LabelWidget,
    PanelSpec,
    TableColumn,
    TableWidget,
    ValueWidget,
)

from .netcap.panel import net_widgets

# 240 nuqta: standart 15 soniyalik oraliqda bir soat.
CHART_WINDOW = 240


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


def _value(label: dict[str, str], field: str) -> ValueWidget:
    return ValueWidget(label=label, source="/status", field=field, refresh_s=5.0)


def _chart(label: dict[str, str], field: str) -> ChartWidget:
    return ChartWidget(
        label=label,
        topic="sample",
        field=field,
        window=CHART_WINDOW,
        history="/history",
        y_min=0,
        y_max=100,
    )


def _number(name: str, label: dict[str, str]) -> FormField:
    return FormField(name=name, label=label, kind="number", required=False)


def build_panel() -> PanelSpec:
    return PanelSpec(
        title=_t("Kuzatuv", "Наблюдение", "Monitoring"),
        widgets=(
            LabelWidget(
                text=_t(
                    "CPU, RAM va disk holati davriy oʻlchanib, tarixga yoziladi. "
                    "Chegaradan oshsa, quyidagi jadvalga ogohlantirish tushadi.",
                    "Загрузка ЦП, память и диски периодически измеряются и записываются "
                    "в историю. При превышении порога в таблице ниже появляется предупреждение.",
                    "CPU, memory and disks are measured periodically and stored. "
                    "When a limit is crossed, an alert appears in the table below.",
                )
            ),
            _value(_t("CPU, %", "ЦП, %", "CPU, %"), "cpu_percent"),
            _value(_t("RAM, %", "Память, %", "Memory, %"), "memory_percent"),
            _value(
                _t("Diskda boʻsh, GB", "Свободно на диске, ГБ", "Disk free, GB"), "disk_free_gb"
            ),
            _value(_t("SRV_1, MB", "SRV_1, МБ", "SRV_1, MB"), "srv1_mb"),
            _value(
                _t("Faol ogohlantirishlar", "Активные предупреждения", "Active alerts"),
                "active_alerts",
            ),
            _chart(_t("CPU, %", "ЦП, %", "CPU, %"), "cpu"),
            _chart(_t("RAM, %", "Память, %", "Memory, %"), "memory"),
            ButtonWidget(
                label=_t("Hozir oʻlchash", "Измерить сейчас", "Measure now"), path="/sample"
            ),
            ButtonWidget(
                label=_t("Tarixni tozalash", "Очистить историю", "Clear history"),
                method="DELETE",
                path="/history",
                confirm=True,
            ),
            TableWidget(
                label=_t("Qoidalar", "Правила", "Rules"),
                source="/rules",
                refresh_s=5.0,
                columns=(
                    TableColumn(key="key", title=_t("Qoida", "Правило", "Rule")),
                    TableColumn(key="now", title=_t("Hozir", "Сейчас", "Now")),
                    TableColumn(key="limit", title=_t("Chegara", "Порог", "Limit")),
                    TableColumn(key="state", title=_t("Holat", "Состояние", "State")),
                ),
            ),
            LabelWidget(
                text=_t(
                    "Chegaralar: boʻsh qoldirilgan maydon oʻzgarmaydi, 0 — qoidani oʻchiradi.",
                    "Пороги: пустое поле не меняется, 0 — отключает правило.",
                    "Limits: an empty field is kept, 0 turns the rule off.",
                )
            ),
            FormWidget(
                label=_t("Chegaralarni oʻzgartirish", "Изменить пороги", "Change limits"),
                path="/thresholds",
                fields=(
                    _number("memory_percent", _t("RAM, %", "Память, %", "Memory, %")),
                    _number("cpu_percent", _t("CPU, %", "ЦП, %", "CPU, %")),
                    _number(
                        "cpu_minutes",
                        _t("CPU: necha daqiqa", "ЦП: сколько минут", "CPU: for how many minutes"),
                    ),
                    _number(
                        "disk_free_gb",
                        _t("Diskda boʻsh joy, GB", "Свободно на диске, ГБ", "Disk free space, GB"),
                    ),
                ),
            ),
            TableWidget(
                label=_t("Disklar", "Диски", "Disks"),
                source="/disks",
                refresh_s=15.0,
                columns=(
                    TableColumn(key="mount", title=_t("Disk", "Диск", "Disk")),
                    TableColumn(key="free", title=_t("Boʻsh", "Свободно", "Free"), format="size"),
                    TableColumn(key="total", title=_t("Jami", "Всего", "Total"), format="size"),
                    TableColumn(key="used_percent", title=_t("Band, %", "Занято, %", "Used, %")),
                ),
            ),
            TableWidget(
                label=_t("Ogohlantirishlar", "Предупреждения", "Alerts"),
                source="/alerts",
                refresh_s=5.0,
                columns=(
                    TableColumn(key="ts", title=_t("Vaqt", "Время", "Time"), format="datetime"),
                    TableColumn(key="key", title=_t("Qoida", "Правило", "Rule")),
                    TableColumn(key="state", title=_t("Holat", "Состояние", "State")),
                    TableColumn(key="value", title=_t("Qiymat", "Значение", "Value")),
                    TableColumn(key="limit", title=_t("Chegara", "Порог", "Limit")),
                    TableColumn(key="note", title=_t("Izoh", "Примечание", "Note")),
                ),
            ),
            *net_widgets(),
        ),
    )
