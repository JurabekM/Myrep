"""«Kuzatuv» panelining «Tarmoq» bo'limi (vidjetlar ro'yxati)."""

from srv1_sdk.panel import (
    ButtonWidget,
    ChartWidget,
    FormField,
    FormWidget,
    LabelWidget,
    RowAction,
    TableColumn,
    TableWidget,
    ValueWidget,
    Widget,
)

Text = dict[str, str]


def _t(uz: str, ru: str, en: str) -> Text:
    return {"uz": uz, "ru": ru, "en": en}


def _value(label: Text, field: str) -> ValueWidget:
    return ValueWidget(label=label, source="/net/status", field=field, refresh_s=2.0)


def _column(key: str, title: Text) -> TableColumn:
    return TableColumn(key=key, title=title)


def _optional(name: str, label: Text, kind: str = "text") -> FormField:
    if kind == "switch":
        return FormField(
            name=name, label=label, kind="choice", choices=("", "on", "off"), required=False
        )
    return FormField(
        name=name, label=label, kind="number" if kind == "number" else "text", required=False
    )


_INTRO = _t(
    "Tarmoq kuzatuvi. Tanlangan interfeysdagi paketlar ushlanadi, tahlil qilinadi va xavf "
    "belgilari tekshiriladi: port skanerlash, NULL/FIN/Xmas skan, shubhali portlar, ochiq "
    "matnda uzatilgan parol va tokenlar. Ushlash alohida jarayonda ishlaydi va faqat siz "
    "boshlaganda yoqiladi. Npcap drayveri oʻrnatilgan boʻlishi kerak. Faqat oʻz "
    "tarmogʻingizda yoki ruxsat bilan ishlating.",
    "Наблюдение за сетью. Пакеты выбранного интерфейса перехватываются, разбираются и "
    "проверяются на признаки угроз: сканирование портов, NULL/FIN/Xmas, подозрительные "
    "порты, пароли и токены открытым текстом. Перехват идёт в отдельном процессе и только "
    "когда вы его запустили. Нужен драйвер Npcap. Используйте только в своей сети или с "
    "разрешения.",
    "Network monitoring. Packets on the chosen interface are captured, parsed and checked "
    "for threats: port scans, NULL/FIN/Xmas scans, suspicious ports, passwords and tokens "
    "sent in clear text. Capture runs in a separate process and only when you start it. "
    "The Npcap driver is required. Use only on your own network or with permission.",
)

_SETTINGS_NOTE = _t(
    "Sozlamalar: boʻsh maydon oʻzgarmaydi. Paket matni standart holatda saqlanmaydi — "
    "yoqilsa, har paketning dastlabki 256 belgisi bazaga yoziladi (ichida parol boʻlishi "
    "mumkin). Geolokatsiya tashqi IP manzillarni ip-api.com ga shifrlanmagan soʻrov bilan "
    "yuboradi. Shubhali portlar — vergul bilan; «-» roʻyxatni boʻshatadi.",
    "Настройки: пустое поле не меняется. Содержимое пакетов по умолчанию не сохраняется — "
    "если включить, первые 256 символов каждого пакета пишутся в базу (там может быть "
    "пароль). Геолокация отправляет внешние IP-адреса на ip-api.com незашифрованным "
    "запросом. Подозрительные порты — через запятую; «-» очищает список.",
    "Settings: an empty field is kept. Packet contents are not stored by default — when "
    "enabled, the first 256 characters of every packet go to the database (they may contain "
    "a password). Geolocation sends external IP addresses to ip-api.com over plain HTTP. "
    "Suspicious ports are comma separated; “-” empties the list.",
)


def net_widgets() -> tuple[Widget, ...]:
    return (
        LabelWidget(text=_INTRO),
        # Kartochkalarda faqat qisqa sonlar: matn (interfeys nomi, xato) uzun bo'lishi mumkin
        # va kartochkaga sig'may kesiladi — u jadvalda ko'rsatiladi.
        _value(_t("Paketlar", "Пакеты", "Packets"), "total"),
        _value(_t("Paket/s", "Пакетов/с", "Packets/s"), "pps"),
        _value(_t("Tarmoq signallari", "Сетевые сигналы", "Network alerts"), "stored_alerts"),
        _value(
            _t("Ushlash jarayoni, MB", "Процесс перехвата, МБ", "Capture process, MB"), "worker_mb"
        ),
        TableWidget(
            label=_t("Tarmoq kuzatuvi holati", "Состояние наблюдения за сетью", "Capture state"),
            source="/net/summary",
            refresh_s=2.0,
            columns=(
                _column("state", _t("Holat", "Состояние", "State")),
                _column("interface", _t("Interfeys", "Интерфейс", "Interface")),
                _column("npcap", _t("Npcap", "Npcap", "Npcap")),
                _column("store_payload", _t("Matn saqlash", "Сохранение", "Payload")),
                _column("geo", _t("Geolokatsiya", "Геолокация", "Geolocation")),
                _column("error", _t("Oxirgi xato", "Последняя ошибка", "Last error")),
            ),
        ),
        ChartWidget(
            label=_t("Paket/s", "Пакетов/с", "Packets/s"), topic="net", field="pps", window=240
        ),
        TableWidget(
            label=_t("Interfeyslar", "Интерфейсы", "Interfaces"),
            source="/net/interfaces",
            refresh_s=10.0,
            columns=(
                _column("name", _t("Nomi", "Имя", "Name")),
                _column("address", _t("Manzil", "Адрес", "Address")),
                _column("speed_mbit", _t("Tezlik, Mbit/s", "Скорость, Мбит/с", "Speed, Mbit/s")),
                _column("capturing", _t("Ushlanmoqda", "Перехват", "Capturing")),
            ),
            row_actions=(
                RowAction(
                    label=_t("Ushlashni boshlash", "Начать перехват", "Start capture"),
                    path="/net/start",
                    params=("name",),
                ),
            ),
        ),
        ButtonWidget(label=_t("Pauza", "Пауза", "Pause"), path="/net/pause"),
        ButtonWidget(label=_t("Davom ettirish", "Продолжить", "Resume"), path="/net/resume"),
        ButtonWidget(label=_t("Toʻxtatish", "Остановить", "Stop"), path="/net/stop"),
        TableWidget(
            label=_t("Tarmoq signallari", "Сетевые сигналы", "Network alerts"),
            source="/net/alerts",
            refresh_s=3.0,
            columns=(
                TableColumn(key="ts", title=_t("Vaqt", "Время", "Time"), format="datetime"),
                _column("kind", _t("Tur", "Тип", "Kind")),
                _column("src", _t("Manba", "Источник", "Source")),
                _column("dst", _t("Manzil", "Назначение", "Destination")),
                _column("note", _t("Izoh", "Примечание", "Note")),
            ),
        ),
        TableWidget(
            label=_t("Paketlar", "Пакеты", "Packets"),
            source="/net/packets",
            refresh_s=3.0,
            filters=(
                _optional("ip", _t("IP manzil", "IP-адрес", "IP address")),
                _optional("proto", _t("Protokol", "Протокол", "Protocol")),
            ),
            columns=(
                TableColumn(key="ts", title=_t("Vaqt", "Время", "Time"), format="datetime"),
                _column("proto", _t("Protokol", "Протокол", "Protocol")),
                _column("src", _t("Manba", "Источник", "Source")),
                _column("dst", _t("Manzil", "Назначение", "Destination")),
                TableColumn(key="length", title=_t("Hajm", "Размер", "Size"), format="size"),
                _column("info", _t("Maʼlumot", "Сведения", "Info")),
                _column("mark", _t("Belgi", "Метка", "Mark")),
                _column("payload", _t("Matn", "Содержимое", "Payload")),
            ),
        ),
        TableWidget(
            label=_t("Eng faol manzillar", "Самые активные адреса", "Top hosts"),
            source="/net/hosts",
            refresh_s=5.0,
            columns=(
                _column("ip", _t("IP manzil", "IP-адрес", "IP address")),
                _column("packets", _t("Paketlar", "Пакеты", "Packets")),
                TableColumn(key="bytes", title=_t("Hajm", "Объём", "Volume"), format="size"),
                _column("where", _t("Qayerda", "Где", "Where")),
            ),
        ),
        ButtonWidget(
            label=_t(
                "Tarmoq maʼlumotini tozalash", "Очистить сетевые данные", "Clear network data"
            ),
            method="DELETE",
            path="/net/data",
            confirm=True,
        ),
        TableWidget(
            label=_t(
                "Kuzatuvdan chiqarilgan manzillar", "Исключённые адреса", "Excluded addresses"
            ),
            source="/net/excluded",
            refresh_s=10.0,
            columns=(_column("ip", _t("IP manzil", "IP-адрес", "IP address")),),
            row_actions=(
                RowAction(
                    label=_t("Kuzatuvga qaytarish", "Вернуть в наблюдение", "Watch again"),
                    path="/net/unexclude",
                    params=("ip",),
                ),
            ),
        ),
        FormWidget(
            label=_t("Manzilni kuzatuvdan chiqarish", "Исключить адрес", "Exclude an address"),
            path="/net/exclude",
            fields=(
                FormField(
                    name="ips",
                    label=_t(
                        "IP manzil(lar), vergul bilan",
                        "IP-адрес(а), через запятую",
                        "IP address(es), comma separated",
                    ),
                ),
            ),
        ),
        LabelWidget(text=_SETTINGS_NOTE),
        FormWidget(
            label=_t(
                "Tarmoq kuzatuvi sozlamalari",
                "Настройки наблюдения за сетью",
                "Network monitoring settings",
            ),
            path="/net/settings",
            fields=(
                _optional(
                    "store_payload",
                    _t("Paket matnini saqlash", "Сохранять содержимое", "Store packet contents"),
                    "switch",
                ),
                _optional("geo", _t("Geolokatsiya", "Геолокация", "Geolocation"), "switch"),
                _optional(
                    "bpf_filter",
                    _t(
                        "BPF filtr (masalan: tcp port 80)",
                        "BPF-фильтр (например: tcp port 80)",
                        "BPF filter (e.g. tcp port 80)",
                    ),
                ),
                _optional(
                    "suspicious_ports",
                    _t("Shubhali portlar", "Подозрительные порты", "Suspicious ports"),
                ),
                _optional(
                    "scan_ports",
                    _t(
                        "Port skan: nechta port",
                        "Скан портов: сколько портов",
                        "Port scan: how many ports",
                    ),
                    "number",
                ),
            ),
        ),
    )
