"""Ogohlantirishni foydalanuvchi o'qiydigan bildirishnoma matniga aylantiradi (uz/ru/en)."""

from .alerts import Alert

Text = dict[str, str]


def _t(uz: str, ru: str, en: str) -> Text:
    return {"uz": uz, "ru": ru, "en": en}


def _number(value: float | None) -> str:
    return "?" if value is None else f"{value:g}"


def _percent(alert: Alert) -> Text:
    now, limit = _number(alert.value), _number(alert.limit)
    return _t(
        f"Hozir {now} %, chegara {limit} %",
        f"Сейчас {now} %, порог {limit} %",
        f"Now {now} %, limit {limit} %",
    )


def _titles(key: str) -> tuple[Text, Text]:
    """(ko'tarilgandagi sarlavha, tinchlangandagi sarlavha)."""
    kind, _, subject = key.partition(":")
    if kind == "memory":
        return (
            _t("Xotira chegaradan oshdi", "Память выше порога", "Memory above the limit"),
            _t("Xotira meʼyorga qaytdi", "Память в норме", "Memory back to normal"),
        )
    if kind == "cpu":
        return (
            _t("Protsessor uzoq vaqt band", "Процессор долго загружен", "CPU busy for too long"),
            _t("Protsessor meʼyorga qaytdi", "Процессор в норме", "CPU back to normal"),
        )
    if kind == "disk":
        return (
            _t(
                f"Diskda joy kam: {subject}",
                f"Мало места на диске: {subject}",
                f"Low disk space: {subject}",
            ),
            _t(
                f"Diskda joy yetarli: {subject}",
                f"Места на диске достаточно: {subject}",
                f"Disk space is fine: {subject}",
            ),
        )
    if kind == "plugin":
        return (
            _t(
                f"Plagin ishdan chiqdi: {subject}",
                f"Плагин вышел из строя: {subject}",
                f"Plugin failed: {subject}",
            ),
            _t(
                f"Plagin tiklandi: {subject}",
                f"Плагин восстановлен: {subject}",
                f"Plugin recovered: {subject}",
            ),
        )
    return _t(f"Ogohlantirish: {key}", f"Предупреждение: {key}", f"Alert: {key}"), _t(
        f"Tinchlandi: {key}", f"Снято: {key}", f"Cleared: {key}"
    )


def _message(alert: Alert) -> Text | str:
    kind = alert.key.partition(":")[0]
    if kind in ("memory", "cpu") and alert.value is not None:
        return _percent(alert)
    if kind == "disk" and alert.value is not None:
        free, limit = _number(alert.value), _number(alert.limit)
        return _t(
            f"Boʻsh joy {free} GB, chegara {limit} GB",
            f"Свободно {free} ГБ, порог {limit} ГБ",
            f"{free} GB free, limit {limit} GB",
        )
    return alert.note


def notice(alert: Alert) -> tuple[Text, Text | str]:
    """Bildirishnoma sarlavhasi va matni."""
    raised, cleared = _titles(alert.key)
    return (raised if alert.state == "raised" else cleared), _message(alert)
