"""Tekshirish sahifasi matnlari (uz — standart, ru)."""

from __future__ import annotations

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "title": "Protokolni tekshirish",
        "number": "Protokol raqami",
        "status": "Holat",
        "active": "Amalda",
        "revoked": "Bekor qilingan",
        "lab": "Laboratoriya",
        "signer": "Imzolagan",
        "signed_at": "Imzolangan vaqt (UTC)",
        "payload_hash": "Ma'lumotlar hash'i (SHA-256)",
        "pdf_hash": "PDF hash'i (SHA-256)",
        "signature": "Elektron imzo",
        "signature_ok": "Imzo va hash'lar to'g'ri",
        "signature_bad": "Imzo tekshiruvidan o'tmadi",
        "download": "PDF ni yuklab olish",
        "check_file": "Qo'lingizdagi PDF faylni tekshirish",
        "check_hint": "Fayl qurilmangizda tekshiriladi, serverga yuborilmaydi.",
        "match": "Fayl imzolangan protokol bilan bir xil",
        "mismatch": "Fayl imzolangan protokoldan farq qiladi",
        "not_found": "Protokol topilmadi. QR kod yoki havolani tekshiring.",
        "disclaimer": "Ilova faqat tavsiya beradi. Ishga ruxsat va xavfsizlik uchun javobgarlik naryad beruvchi va "
        "ish rahbari zimmasida.",
        "language": "Русский",
    },
    "ru": {
        "title": "Проверка протокола",
        "number": "Номер протокола",
        "status": "Статус",
        "active": "Действует",
        "revoked": "Отозван",
        "lab": "Лаборатория",
        "signer": "Подписал",
        "signed_at": "Время подписи (UTC)",
        "payload_hash": "Хеш данных (SHA-256)",
        "pdf_hash": "Хеш PDF (SHA-256)",
        "signature": "Электронная подпись",
        "signature_ok": "Подпись и хеши верны",
        "signature_bad": "Подпись не прошла проверку",
        "download": "Скачать PDF",
        "check_file": "Проверить имеющийся PDF-файл",
        "check_hint": "Файл проверяется на вашем устройстве и не отправляется на сервер.",
        "match": "Файл совпадает с подписанным протоколом",
        "mismatch": "Файл отличается от подписанного протокола",
        "not_found": "Протокол не найден. Проверьте QR-код или ссылку.",
        "disclaimer": "Приложение даёт только рекомендации. Ответственность за допуск к работе и безопасность несут "
        "выдающий наряд и руководитель работ.",
        "language": "O'zbekcha",
    },
}
