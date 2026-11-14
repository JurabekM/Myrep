"""Tarmoq xavf signallari uchun bildirishnoma matni (uz/ru/en)."""

from collections.abc import Mapping
from typing import Any

Localized = dict[str, str]

_TITLES: dict[str, Localized] = {
    "port_scan": {
        "uz": "Port skanerlash aniqlandi",
        "ru": "Обнаружено сканирование портов",
        "en": "Port scan detected",
    },
    "null_scan": {
        "uz": "NULL skan aniqlandi",
        "ru": "Обнаружено NULL-сканирование",
        "en": "NULL scan detected",
    },
    "fin_scan": {
        "uz": "FIN skan aniqlandi",
        "ru": "Обнаружено FIN-сканирование",
        "en": "FIN scan detected",
    },
    "xmas_scan": {
        "uz": "Xmas skan aniqlandi",
        "ru": "Обнаружено Xmas-сканирование",
        "en": "Xmas scan detected",
    },
    "port": {
        "uz": "Shubhali portga murojaat",
        "ru": "Обращение к подозрительному порту",
        "en": "Suspicious port contacted",
    },
    "secret": {
        "uz": "Sir ochiq matnda uzatildi",
        "ru": "Секрет передан открытым текстом",
        "en": "Secret sent in clear text",
    },
}
_UNKNOWN: Localized = {
    "uz": "Tarmoq signali",
    "ru": "Сетевое предупреждение",
    "en": "Network alert",
}

STOPPED_TITLE: Localized = {
    "uz": "Tarmoq kuzatuvi toʻxtab qoldi",
    "ru": "Наблюдение за сетью остановилось",
    "en": "Network capture stopped",
}


def net_notice(alert: Mapping[str, Any]) -> tuple[Localized, str]:
    """Sarlavha (tilga qarab) va barcha tilda bir xil qisqa matn: `manba → manzil (izoh)`."""
    title = _TITLES.get(str(alert.get("kind", "")), _UNKNOWN)
    message = f"{alert.get('src', '')} → {alert.get('dst', '')}"
    note = str(alert.get("note", ""))
    return title, f"{message} ({note})" if note else message
