"""Texnik holatni foydalanuvchi tiliga tarjima qiladi.

Topshiriq §19: foydalanuvchiga «aggregate», «checkpoint», «projector»,
«outbox» kabi atamalar KO'RSATILMAYDI. Sotuvchi «PEER_APPLIED» ni emas,
«boshqa qurilmalarga yetkazildi» ni ko'radi.

Bu tarjima bitta joyda turadi — UI'ning har burchagida takrorlanmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass

from distribos.aether_q.provider import RejectReason
# Formatlash `domain.formatting` da — UI, hisobot va hujjat bir xil ko'rinsin.
from distribos.domain.formatting import money, quantity
from distribos.persistence.models import DeliveryState, OrderState

__all__ = [
    "StatusLabel", "connection_status", "delivery_status", "device_platform",
    "money", "order_state", "order_state_tone", "quantity", "rejection_status",
    "role_name",
]


@dataclass(frozen=True, slots=True)
class StatusLabel:
    text: str
    #: `ok` | `progress` | `warning` | `error`
    tone: str
    hint: str = ""


_DELIVERY: dict[str, StatusLabel] = {
    DeliveryState.LOCAL_COMMITTED: StatusLabel(
        "Qurilmada saqlandi", "progress",
        "Ma'lumot shu kompyuterda saqlandi. Internet paydo bo'lishi bilan "
        "boshqa qurilmalarga yuboriladi.",
    ),
    DeliveryState.SEALED: StatusLabel("Yuborishga tayyor", "progress"),
    DeliveryState.QUEUED: StatusLabel("Navbatda", "progress"),
    DeliveryState.MQTT_PUBLISHED: StatusLabel(
        "Yuborilmoqda", "progress",
        "Yuborildi, boshqa qurilma qabul qilganini kutmoqdamiz.",
    ),
    DeliveryState.MQTT_ACKNOWLEDGED: StatusLabel("Yuborildi", "progress"),
    DeliveryState.PEER_RECEIVED: StatusLabel("Boshqa qurilmaga yetkazildi", "progress"),
    DeliveryState.PEER_APPLIED: StatusLabel(
        "Sinxronlandi", "ok", "Barcha qurilmalarda hisobga olindi.",
    ),
    DeliveryState.PEER_REJECTED: StatusLabel(
        "Tekshiruv talab qiladi", "warning",
        "Boshqa qurilma bu yozuvni qabul qilmadi. Sinxronizatsiya "
        "bo'limidan sababni ko'ring.",
    ),
    DeliveryState.CONFLICT: StatusLabel(
        "Tekshiruv talab qiladi", "warning",
        "Ikki qurilmada bir-biriga zid o'zgarish bo'lgan. Qaysi biri "
        "to'g'ri ekanini siz tanlashingiz kerak.",
    ),
    DeliveryState.DEAD_LETTER: StatusLabel(
        "Xatolik yuz berdi", "error",
        "Bir necha marta urinildi, lekin yuborilmadi. Sinxronizatsiya "
        "bo'limidan qayta urinib ko'ring.",
    ),
}


def delivery_status(state: str) -> StatusLabel:
    return _DELIVERY.get(state, StatusLabel("Noma'lum holat", "warning"))


_ORDER_STATES: dict[str, str] = {
    OrderState.DRAFT: "Qoralama",
    OrderState.CONFIRMED: "Tasdiqlangan",
    OrderState.APPROVED: "Ma'qullangan",
    OrderState.ALLOCATED: "Ajratilgan",
    OrderState.PICKED: "Yig'ilgan",
    OrderState.SHIPPED: "Jo'natilgan",
    OrderState.DELIVERED: "Yetkazilgan",
    OrderState.PARTIALLY_RETURNED: "Qisman qaytarilgan",
    OrderState.RETURNED: "Qaytarilgan",
    OrderState.CANCELLED: "Bekor qilingan",
}


def order_state(state: str) -> str:
    return _ORDER_STATES.get(state, state)


def order_state_tone(state: str) -> str:
    if state in (OrderState.DELIVERED,):
        return "ok"
    if state in (OrderState.CANCELLED, OrderState.RETURNED):
        return "error"
    if state in (OrderState.PARTIALLY_RETURNED,):
        return "warning"
    return "progress"


#: Rad etish sabablari. Foydalanuvchiga NIMA QILISH kerakligi aytiladi.
_REJECTIONS: dict[RejectReason, StatusLabel] = {
    RejectReason.MALFORMED: StatusLabel(
        "Buzilgan xabar", "error", "Xabar yo'lda buzilgan. Qayta yuboriladi.",
    ),
    RejectReason.UNKNOWN_VERSION: StatusLabel(
        "Eski yoki yangi dastur", "warning",
        "Boshqa qurilmada dasturning boshqa versiyasi. Ikkalasini ham "
        "yangilang.",
    ),
    RejectReason.UNSUPPORTED_PROFILE: StatusLabel(
        "Mos kelmaydigan xavfsizlik sozlamasi", "error",
    ),
    RejectReason.UNKNOWN_EPOCH: StatusLabel(
        "Eskirgan xavfsizlik kaliti", "warning",
        "Bu qurilma kalit yangilanishidan oldingi xabarni yubordi.",
    ),
    RejectReason.UNKNOWN_KEY: StatusLabel(
        "Kalit topilmadi", "warning",
        "Qurilmani qayta ulash kerak bo'lishi mumkin.",
    ),
    RejectReason.FOREIGN_TENANT: StatusLabel(
        "Begona korxona xabari", "error",
        "Bu xabar boshqa korxonaga tegishli va rad etildi.",
    ),
    RejectReason.UNKNOWN_SENDER: StatusLabel(
        "Notanish qurilma", "warning",
        "Qurilma ro'yxatdan o'tmagan. Sozlamalar > Qurilmalar bo'limida "
        "qo'shing.",
    ),
    RejectReason.REVOKED_SENDER: StatusLabel(
        "Bekor qilingan qurilma", "error",
        "Bu qurilma ro'yxatdan chiqarilgan, uning ma'lumotlari qabul "
        "qilinmaydi.",
    ),
    RejectReason.BAD_SIGNATURE: StatusLabel(
        "Imzo to'g'ri kelmadi", "error",
        "Xabar haqiqiyligi tasdiqlanmadi va rad etildi.",
    ),
    RejectReason.REPLAY: StatusLabel(
        "Takroriy xabar", "ok", "Bu xabar allaqachon qabul qilingan edi.",
    ),
    RejectReason.AEAD_FAILURE: StatusLabel(
        "Xabar ochilmadi", "error", "Xabar buzilgan yoki o'zgartirilgan.",
    ),
    RejectReason.SCHEMA_INVALID: StatusLabel(
        "Tanib bo'lmaydigan ma'lumot", "warning",
        "Ehtimol boshqa qurilmada dasturning yangiroq versiyasi.",
    ),
    RejectReason.TOO_LARGE: StatusLabel(
        "Xabar juda katta", "warning",
    ),
    RejectReason.STALE: StatusLabel("Eskirgan xabar", "warning"),
}


def rejection_status(reason: RejectReason | str) -> StatusLabel:
    if isinstance(reason, str):
        try:
            reason = RejectReason[reason]
        except KeyError:
            return StatusLabel("Noma'lum sabab", "warning")
    return _REJECTIONS.get(reason, StatusLabel("Rad etildi", "warning"))


def connection_status(connected: bool, queued: int) -> StatusLabel:
    """Yuqoridagi holat chizig'i uchun."""
    if connected and queued == 0:
        return StatusLabel("Hammasi sinxronlangan", "ok")
    if connected and queued:
        return StatusLabel(f"Yuborilmoqda ({queued})", "progress")
    if queued:
        return StatusLabel(
            f"Ulanish yo'q — {queued} ta yozuv navbatda", "warning",
            "Ishlashda davom eting. Internet paydo bo'lishi bilan hammasi "
            "avtomatik yuboriladi.",
        )
    return StatusLabel(
        "Ulanish yo'q", "warning",
        "Dastur ulanishsiz ham to'liq ishlaydi.",
    )


def device_platform(platform: str) -> str:
    return {"desktop": "Kompyuter", "android": "Telefon"}.get(platform, platform)


def role_name(role: str) -> str:
    return {
        "owner": "Egasi",
        "manager": "Rahbar",
        "agent": "Savdo agenti",
        "warehouse": "Omborchi",
        "cashier": "Kassir",
        "viewer": "Kuzatuvchi",
    }.get(role, role)
