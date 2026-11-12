"""`iot` plagini paneli (uch tilda)."""

from srv1_sdk.panel import (
    FormField,
    FormWidget,
    LogWidget,
    PanelSpec,
    RowAction,
    TableColumn,
    TableWidget,
    ValueWidget,
)


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


_TOPIC = FormField(name="topic", label=_t("Mavzu", "Тема", "Topic"))
_PORT = FormField(name="port", label=_t("Port", "Порт", "Port"))


def _mqtt_widgets() -> tuple[FormWidget | TableWidget | LogWidget, ...]:
    return (
        FormWidget(
            label=_t("MQTT: xabar nashr qilish", "MQTT: опубликовать", "MQTT: publish"),
            path="/mqtt/publish",
            fields=(
                _TOPIC,
                FormField(
                    name="payload", label=_t("Xabar", "Сообщение", "Payload"), required=False
                ),
            ),
        ),
        TableWidget(
            label=_t("MQTT obunalari", "Подписки MQTT", "MQTT subscriptions"),
            source="/mqtt/subscriptions",
            refresh_s=10,
            columns=(TableColumn(key="topic", title=_t("Mavzu", "Тема", "Topic")),),
            row_actions=(
                RowAction(
                    label=_t("Obunani bekor qilish", "Отписаться", "Unsubscribe"),
                    path="/mqtt/unsubscribe",
                    params=("topic",),
                ),
            ),
        ),
        FormWidget(
            label=_t("MQTT: obuna boʻlish", "MQTT: подписаться", "MQTT: subscribe"),
            path="/mqtt/subscribe",
            fields=(_TOPIC,),
        ),
        LogWidget(
            label=_t("MQTT xabarlari", "Сообщения MQTT", "MQTT messages"),
            source="/mqtt/log",
            refresh_s=2,
        ),
    )


def _serial_widgets() -> tuple[FormWidget | TableWidget | LogWidget, ...]:
    return (
        TableWidget(
            label=_t("Serial portlar", "Последовательные порты", "Serial ports"),
            source="/serial/ports",
            refresh_s=5,
            columns=(
                TableColumn(key="port", title=_t("Port", "Порт", "Port")),
                TableColumn(key="allowed", title=_t("Ruxsat", "Разрешён", "Allowed")),
                TableColumn(key="open", title=_t("Ochiq", "Открыт", "Open")),
                TableColumn(key="baudrate", title=_t("Tezlik", "Скорость", "Baud rate")),
                TableColumn(key="description", title=_t("Tavsif", "Описание", "Description")),
            ),
            row_actions=(
                RowAction(
                    label=_t("Yopish", "Закрыть", "Close"), path="/serial/close", params=("port",)
                ),
            ),
        ),
        FormWidget(
            label=_t("Serial portni ochish", "Открыть порт", "Open serial port"),
            path="/serial/open",
            fields=(
                _PORT,
                FormField(
                    name="baudrate",
                    label=_t("Tezlik", "Скорость", "Baud rate"),
                    kind="number",
                    required=False,
                ),
            ),
        ),
        FormWidget(
            label=_t("Serial portga yozish", "Записать в порт", "Write to serial port"),
            path="/serial/write",
            fields=(_PORT, FormField(name="text", label=_t("Matn", "Текст", "Text"))),
        ),
        LogWidget(
            label=_t("Serial monitor", "Монитор порта", "Serial monitor"),
            source="/serial/lines",
            refresh_s=1,
            filters=(_PORT,),
        ),
    )


def build_panel() -> PanelSpec:
    return PanelSpec(
        title="IoT",
        widgets=(
            ValueWidget(label="MQTT", source="/status", field="mqtt_state", refresh_s=3),
            ValueWidget(label=_t("Broker", "Брокер", "Broker"), source="/status", field="broker"),
            ValueWidget(
                label=_t("Yozuvlar", "Записей", "Samples"), source="/status", field="samples"
            ),
            ValueWidget(
                label=_t("Modbus (ishlayapti)", "Modbus (на связи)", "Modbus (online)"),
                source="/status",
                field="modbus_ok",
            ),
            TableWidget(
                label=_t("Oxirgi qiymatlar", "Последние значения", "Latest values"),
                source="/telemetry/latest",
                refresh_s=2,
                filters=(
                    FormField(
                        name="source",
                        label=_t("Manba (boshi)", "Источник (начало)", "Source (prefix)"),
                        required=False,
                    ),
                ),
                columns=(
                    TableColumn(key="source", title=_t("Manba", "Источник", "Source")),
                    TableColumn(key="key", title=_t("Kalit", "Ключ", "Key")),
                    TableColumn(key="value", title=_t("Qiymat", "Значение", "Value")),
                    TableColumn(key="ts", title=_t("Vaqt", "Время", "Time"), format="datetime"),
                ),
            ),
            FormWidget(
                label=_t("Qiymatni qoʻlda yozish", "Записать значение вручную", "Record a value"),
                path="/telemetry/record",
                fields=(
                    FormField(name="source", label=_t("Manba", "Источник", "Source")),
                    FormField(name="key", label=_t("Kalit", "Ключ", "Key")),
                    FormField(name="value", label=_t("Qiymat", "Значение", "Value"), kind="number"),
                ),
            ),
            *_mqtt_widgets(),
            TableWidget(
                label=_t("Modbus qurilmalari", "Устройства Modbus", "Modbus devices"),
                source="/modbus",
                refresh_s=3,
                columns=(
                    TableColumn(key="name", title=_t("Nom", "Имя", "Name")),
                    TableColumn(key="address", title=_t("Manzil", "Адрес", "Address")),
                    TableColumn(key="ok", title=_t("Aloqa", "Связь", "Online")),
                    TableColumn(
                        key="last_poll",
                        title=_t("Oxirgi soʻrov", "Опрос", "Last poll"),
                        format="datetime",
                    ),
                    TableColumn(key="error", title=_t("Xato", "Ошибка", "Error")),
                ),
                row_actions=(
                    RowAction(
                        label=_t("Hozir soʻrash", "Опросить", "Poll now"),
                        path="/modbus/poll",
                        params=("name",),
                    ),
                    RowAction(
                        label=_t("Olib tashlash", "Удалить", "Remove"),
                        path="/modbus/remove",
                        params=("name",),
                        confirm=True,
                    ),
                ),
            ),
            *_serial_widgets(),
        ),
    )
