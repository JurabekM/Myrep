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
from distribos.i18n import tr
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


def _delivery_labels() -> dict[str, StatusLabel]:
    # Funksiya sifatida: `tr()` HAR CHAQIRISHDA joriy tilni o'qishi
    # kerak — modul darajasidagi doimiy bo'lsa import vaqtidagi
    # (til o'rnatilishidan OLDINGI) tilda muzlab qolardi.
    return {
        DeliveryState.LOCAL_COMMITTED: StatusLabel(
            tr("Qurilmada saqlandi"), "progress",
            tr(
                "Ma'lumot shu kompyuterda saqlandi. Internet paydo bo'lishi "
                "bilan boshqa qurilmalarga yuboriladi."
            ),
        ),
        DeliveryState.SEALED: StatusLabel(tr("Yuborishga tayyor"), "progress"),
        DeliveryState.QUEUED: StatusLabel(tr("Navbatda"), "progress"),
        DeliveryState.MQTT_PUBLISHED: StatusLabel(
            tr("Yuborilmoqda"), "progress",
            tr("Yuborildi, boshqa qurilma qabul qilganini kutmoqdamiz."),
        ),
        DeliveryState.MQTT_ACKNOWLEDGED: StatusLabel(tr("Yuborildi"), "progress"),
        DeliveryState.PEER_RECEIVED: StatusLabel(
            tr("Boshqa qurilmaga yetkazildi"), "progress"
        ),
        DeliveryState.PEER_APPLIED: StatusLabel(
            tr("Sinxronlandi"), "ok", tr("Barcha qurilmalarda hisobga olindi."),
        ),
        DeliveryState.PEER_REJECTED: StatusLabel(
            tr("Tekshiruv talab qiladi"), "warning",
            tr(
                "Boshqa qurilma bu yozuvni qabul qilmadi. Sinxronizatsiya "
                "bo'limidan sababni ko'ring."
            ),
        ),
        DeliveryState.CONFLICT: StatusLabel(
            tr("Tekshiruv talab qiladi"), "warning",
            tr(
                "Ikki qurilmada bir-biriga zid o'zgarish bo'lgan. Qaysi biri "
                "to'g'ri ekanini siz tanlashingiz kerak."
            ),
        ),
        DeliveryState.DEAD_LETTER: StatusLabel(
            tr("Xatolik yuz berdi"), "error",
            tr(
                "Bir necha marta urinildi, lekin yuborilmadi. Sinxronizatsiya "
                "bo'limidan qayta urinib ko'ring."
            ),
        ),
    }


def delivery_status(state: str) -> StatusLabel:
    return _delivery_labels().get(state, StatusLabel(tr("Noma'lum holat"), "warning"))


def order_state(state: str) -> str:
    labels: dict[str, str] = {
        OrderState.DRAFT: tr("Qoralama"),
        OrderState.CONFIRMED: tr("Tasdiqlangan"),
        OrderState.APPROVED: tr("Ma'qullangan"),
        OrderState.ALLOCATED: tr("Ajratilgan"),
        OrderState.PICKED: tr("Yig'ilgan"),
        OrderState.SHIPPED: tr("Jo'natilgan"),
        OrderState.DELIVERED: tr("Yetkazilgan"),
        OrderState.PARTIALLY_RETURNED: tr("Qisman qaytarilgan"),
        OrderState.RETURNED: tr("Qaytarilgan"),
        OrderState.CANCELLED: tr("Bekor qilingan"),
    }
    return labels.get(state, state)


def order_state_tone(state: str) -> str:
    if state in (OrderState.DELIVERED,):
        return "ok"
    if state in (OrderState.CANCELLED, OrderState.RETURNED):
        return "error"
    if state in (OrderState.PARTIALLY_RETURNED,):
        return "warning"
    return "progress"


#: Rad etish sabablari. Foydalanuvchiga NIMA QILISH kerakligi aytiladi.
def _rejection_labels() -> dict[RejectReason, StatusLabel]:
    return {
        RejectReason.MALFORMED: StatusLabel(
            tr("Buzilgan xabar"), "error", tr("Xabar yo'lda buzilgan. Qayta yuboriladi."),
        ),
        RejectReason.UNKNOWN_VERSION: StatusLabel(
            tr("Eski yoki yangi dastur"), "warning",
            tr(
                "Boshqa qurilmada dasturning boshqa versiyasi. Ikkalasini ham "
                "yangilang."
            ),
        ),
        RejectReason.UNSUPPORTED_PROFILE: StatusLabel(
            tr("Mos kelmaydigan xavfsizlik sozlamasi"), "error",
        ),
        RejectReason.UNKNOWN_EPOCH: StatusLabel(
            tr("Eskirgan xavfsizlik kaliti"), "warning",
            tr("Bu qurilma kalit yangilanishidan oldingi xabarni yubordi."),
        ),
        RejectReason.UNKNOWN_KEY: StatusLabel(
            tr("Kalit topilmadi"), "warning",
            tr("Qurilmani qayta ulash kerak bo'lishi mumkin."),
        ),
        RejectReason.FOREIGN_TENANT: StatusLabel(
            tr("Begona korxona xabari"), "error",
            tr("Bu xabar boshqa korxonaga tegishli va rad etildi."),
        ),
        RejectReason.UNKNOWN_SENDER: StatusLabel(
            tr("Notanish qurilma"), "warning",
            tr(
                "Qurilma ro'yxatdan o'tmagan. Sozlamalar > Qurilmalar bo'limida "
                "qo'shing."
            ),
        ),
        RejectReason.REVOKED_SENDER: StatusLabel(
            tr("Bekor qilingan qurilma"), "error",
            tr(
                "Bu qurilma ro'yxatdan chiqarilgan, uning ma'lumotlari qabul "
                "qilinmaydi."
            ),
        ),
        RejectReason.BAD_SIGNATURE: StatusLabel(
            tr("Imzo to'g'ri kelmadi"), "error",
            tr("Xabar haqiqiyligi tasdiqlanmadi va rad etildi."),
        ),
        RejectReason.REPLAY: StatusLabel(
            tr("Takroriy xabar"), "ok", tr("Bu xabar allaqachon qabul qilingan edi."),
        ),
        RejectReason.AEAD_FAILURE: StatusLabel(
            tr("Xabar ochilmadi"), "error", tr("Xabar buzilgan yoki o'zgartirilgan."),
        ),
        RejectReason.SCHEMA_INVALID: StatusLabel(
            tr("Tanib bo'lmaydigan ma'lumot"), "warning",
            tr("Ehtimol boshqa qurilmada dasturning yangiroq versiyasi."),
        ),
        RejectReason.TOO_LARGE: StatusLabel(
            tr("Xabar juda katta"), "warning",
        ),
        RejectReason.STALE: StatusLabel(tr("Eskirgan xabar"), "warning"),
    }


def rejection_status(reason: RejectReason | str) -> StatusLabel:
    if isinstance(reason, str):
        try:
            reason = RejectReason[reason]
        except KeyError:
            return StatusLabel(tr("Noma'lum sabab"), "warning")
    return _rejection_labels().get(reason, StatusLabel(tr("Rad etildi"), "warning"))


def connection_status(connected: bool, queued: int) -> StatusLabel:
    """Yuqoridagi holat chizig'i uchun."""
    if connected and queued == 0:
        return StatusLabel(tr("Hammasi sinxronlangan"), "ok")
    if connected and queued:
        return StatusLabel(tr("Yuborilmoqda ({n})").format(n=queued), "progress")
    if queued:
        return StatusLabel(
            tr("Ulanish yo'q — {n} ta yozuv navbatda").format(n=queued), "warning",
            tr(
                "Ishlashda davom eting. Internet paydo bo'lishi bilan hammasi "
                "avtomatik yuboriladi."
            ),
        )
    return StatusLabel(
        tr("Ulanish yo'q"), "warning",
        tr("Dastur ulanishsiz ham to'liq ishlaydi."),
    )


def device_platform(platform: str) -> str:
    return {"desktop": tr("Kompyuter"), "android": tr("Telefon")}.get(platform, platform)


def role_name(role: str) -> str:
    return {
        "owner": tr("Egasi"),
        "manager": tr("Rahbar"),
        "agent": tr("Savdo agenti"),
        "warehouse": tr("Omborchi"),
        "cashier": tr("Kassir"),
        "viewer": tr("Kuzatuvchi"),
    }.get(role, role)
