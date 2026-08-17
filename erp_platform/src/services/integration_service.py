# -*- coding: utf-8 -*-
"""
Integratsiya adapterlari — kelajakdagi tashqi ulanishlar uchun tayyor
interfeyslar (Adapter + Strategy pattern).

MUHIM: API kalitlari IXTIYORIY. Kalit sozlanmagan adapter "sozlanmagan"
holatda bo'ladi: so'rov strukturasini TAYYORLAYDI, lekin tashqi serverga
YUBORMAYDI. Bu ERP ni internet va kalitlarsiz to'liq ishlatish imkonini
beradi, integratsiya esa keyin faqat config.yaml ni to'ldirish bilan yoqiladi.

Adapterlar: Click, Payme, Uzum Bank (to'lov), Telegram, Email, SMS
(xabarnoma), Soliq (hisobot), 1C (import).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from src.core.errors import UzERPError
from src.core.utils import D
from src.modules.base import BaseService


class BaseAdapter:
    """Barcha integratsiya adapterlarining asosi."""

    #: Texnik nom (config kaliti bilan mos)
    name: str = "base"
    #: Ko'rinadigan nom
    title: str = "Adapter"

    def __init__(self, config, log) -> None:
        self.config = config
        self.log = log

    def _cfg(self, key: str, default: Any = "") -> Any:
        """Adapterning config qiymatini o'qiydi."""
        return self.config.get(f"integrations.{self.name}.{key}", default)

    def is_configured(self) -> bool:
        """Adapter ishlashga tayyorligini bildiradi (kalitlar bor-yo'qligi)."""
        return False

    def status(self) -> dict:
        """UI uchun holat ma'lumoti."""
        return {"name": self.name, "title": self.title,
                "configured": self.is_configured()}


# ---------------------------------------------------------------------- #
#  To'lov shlyuzlari
# ---------------------------------------------------------------------- #

class ClickAdapter(BaseAdapter):
    """Click to'lov tizimi adapteri (https://docs.click.uz)."""

    name, title = "click", "Click"

    def is_configured(self) -> bool:
        return bool(self._cfg("merchant_id") and self._cfg("secret_key"))

    def create_invoice(self, amount, order_id: str) -> dict:
        """Click to'lov havolasi uchun so'rov strukturasini tayyorlaydi."""
        payload = {
            "service_id": self._cfg("service_id"),
            "merchant_id": self._cfg("merchant_id"),
            "amount": str(D(amount)),
            "transaction_param": str(order_id),
            "url": "https://my.click.uz/services/pay",
        }
        return {"prepared": True, "sent": False, "gateway": self.name,
                "payload": payload,
                "note": ("Sozlanmagan — config.yaml da integrations.click "
                         "to'ldirilsa yuborishga tayyor."
                         if not self.is_configured() else "Tayyor.")}

    def verify_callback(self, data: dict) -> bool:
        """Click callback imzosini tekshiradi (MD5 zanjiri)."""
        secret = str(self._cfg("secret_key"))
        if not secret:
            return False
        sign_string = "".join(str(data.get(k, "")) for k in (
            "click_trans_id", "service_id", "merchant_trans_id",
            "amount", "action", "sign_time"))
        expected = hashlib.md5((sign_string + secret).encode()).hexdigest()
        return expected == str(data.get("sign_string", ""))


class PaymeAdapter(BaseAdapter):
    """Payme (Paycom) to'lov tizimi adapteri."""

    name, title = "payme", "Payme"

    def is_configured(self) -> bool:
        return bool(self._cfg("merchant_id") and self._cfg("key"))

    def create_invoice(self, amount, order_id: str) -> dict:
        """Payme checkout parametrlarini tayyorlaydi (summalar tiyinda)."""
        payload = {
            "merchant": self._cfg("merchant_id"),
            "amount": int(D(amount) * 100),  # tiyin
            "account": {"order_id": str(order_id)},
            "url": "https://checkout.paycom.uz",
        }
        return {"prepared": True, "sent": False, "gateway": self.name,
                "payload": payload,
                "note": ("Sozlanmagan." if not self.is_configured()
                         else "Tayyor.")}


class UzumBankAdapter(BaseAdapter):
    """Uzum Bank (Apelsin) to'lov adapteri."""

    name, title = "uzum", "Uzum Bank"

    def is_configured(self) -> bool:
        return bool(self._cfg("merchant_id") and self._cfg("secret_key"))

    def create_invoice(self, amount, order_id: str) -> dict:
        """Uzum to'lov so'rovi strukturasini tayyorlaydi."""
        payload = {
            "merchantId": self._cfg("merchant_id"),
            "amount": int(D(amount) * 100),
            "orderId": str(order_id),
            "currency": "UZS",
        }
        return {"prepared": True, "sent": False, "gateway": self.name,
                "payload": payload,
                "note": ("Sozlanmagan." if not self.is_configured()
                         else "Tayyor.")}


# ---------------------------------------------------------------------- #
#  Xabarnomalar
# ---------------------------------------------------------------------- #

class TelegramAdapter(BaseAdapter):
    """Telegram bot xabarnomalari (stdlib urllib bilan, kalit bo'lsa)."""

    name, title = "telegram", "Telegram"

    def is_configured(self) -> bool:
        return bool(self._cfg("token") and self._cfg("chat_id"))

    def send_message(self, text: str, chat_id: str | None = None) -> dict:
        """
        Xabar yuboradi (sozlangan bo'lsa); aks holda tayyor payload qaytaradi.
        """
        chat = chat_id or str(self._cfg("chat_id"))
        payload = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
        if not self.is_configured():
            return {"prepared": True, "sent": False, "payload": payload,
                    "note": "Token sozlanmagan (integrations.telegram)."}
        try:
            import urllib.parse
            import urllib.request

            url = (f"https://api.telegram.org/bot{self._cfg('token')}"
                   f"/sendMessage")
            data = urllib.parse.urlencode(payload).encode()
            with urllib.request.urlopen(url, data=data, timeout=10) as resp:
                ok = resp.status == 200
            return {"prepared": True, "sent": ok, "payload": payload}
        except Exception as exc:  # noqa: BLE001
            self.log.warning("Telegram yuborish xatosi: %s", exc)
            return {"prepared": True, "sent": False, "payload": payload,
                    "note": f"Yuborishda xato: {exc}"}


class EmailAdapter(BaseAdapter):
    """Email xabarnomalari (stdlib smtplib, sozlangan bo'lsa)."""

    name, title = "email", "Email"

    def is_configured(self) -> bool:
        return bool(self._cfg("smtp_host") and self._cfg("sender"))

    def send_message(self, to: str, subject: str, body: str) -> dict:
        """Xat yuboradi (sozlangan bo'lsa); aks holda payload tayyorlaydi."""
        payload = {"to": to, "subject": subject, "body": body,
                   "from": str(self._cfg("sender"))}
        if not self.is_configured():
            return {"prepared": True, "sent": False, "payload": payload,
                    "note": "SMTP sozlanmagan (integrations.email)."}
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = payload["from"]
            msg["To"] = to
            with smtplib.SMTP(str(self._cfg("smtp_host")),
                              int(self._cfg("smtp_port", 587)),
                              timeout=15) as smtp:
                smtp.starttls()
                if self._cfg("username"):
                    smtp.login(str(self._cfg("username")),
                               str(self._cfg("password")))
                smtp.send_message(msg)
            return {"prepared": True, "sent": True, "payload": payload}
        except Exception as exc:  # noqa: BLE001
            self.log.warning("Email yuborish xatosi: %s", exc)
            return {"prepared": True, "sent": False, "payload": payload,
                    "note": f"Yuborishda xato: {exc}"}


class SmsAdapter(BaseAdapter):
    """SMS xabarnomalari (Eskiz.uz formatidagi tayyor payload)."""

    name, title = "sms", "SMS"

    def is_configured(self) -> bool:
        return bool(self._cfg("token"))

    def send_message(self, phone: str, text: str) -> dict:
        """SMS so'rovini tayyorlaydi (kalit bo'lmasa yubormaydi)."""
        payload = {
            "mobile_phone": phone.replace("+", "").replace(" ", ""),
            "message": text,
            "from": str(self._cfg("sender", "UzERP")),
        }
        return {"prepared": True, "sent": False, "payload": payload,
                "note": ("Token sozlanmagan (integrations.sms)."
                         if not self.is_configured()
                         else "Provayder ulanishi keyingi versiyada.")}


# ---------------------------------------------------------------------- #
#  Hisobot va import
# ---------------------------------------------------------------------- #

class SoliqAdapter(BaseAdapter):
    """Soliq organlari uchun hisobot ma'lumotlarini tayyorlovchi adapter."""

    name, title = "soliq", "Soliq (my.soliq.uz)"

    def __init__(self, config, log, container) -> None:
        super().__init__(config, log)
        self.container = container

    def prepare_vat_declaration(self, date_from: str, date_to: str) -> dict:
        """QQS deklaratsiyasi uchun strukturalangan ma'lumot tayyorlaydi."""
        accounting = self.container.get("accounting")
        vat = accounting.vat_report(date_from, date_to)
        return {
            "prepared": True, "sent": False,
            "declaration": {
                "type": "QQS",
                "period": {"from": date_from, "to": date_to},
                "company_tin": self.config.get("app.company_tin", ""),
                "output_vat": str(vat["output_vat"]),
                "input_vat": str(vat["input_vat"]),
                "payable": str(vat["payable"]),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            },
            "note": "my.soliq.uz ga yuklash uchun tayyor struktura.",
        }


class OneCImportAdapter(BaseAdapter):
    """1C dan eksport qilingan fayllarni UzERP formatiga o'giruvchi adapter."""

    name, title = "onec", "1C Import"

    def __init__(self, config, log, container) -> None:
        super().__init__(config, log)
        self.container = container

    def import_products_csv(self, file_path: str,
                            user: dict | None = None) -> dict:
        """
        1C nomenklatura CSV faylini import qiladi (rus ustun nomlari
        ImportService lug'ati orqali avtomatik tan olinadi).
        """
        importer = self.container.get("importer")
        return importer.import_products(file_path, user=user)


# ---------------------------------------------------------------------- #
#  Servis-registr
# ---------------------------------------------------------------------- #

class IntegrationService(BaseService):
    """Barcha integratsiya adapterlarining yagona registri."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.adapters: dict[str, BaseAdapter] = {}
        for cls in (ClickAdapter, PaymeAdapter, UzumBankAdapter,
                    TelegramAdapter, EmailAdapter, SmsAdapter):
            adapter = cls(self.config, self.log)
            self.adapters[adapter.name] = adapter
        for cls in (SoliqAdapter, OneCImportAdapter):
            adapter = cls(self.config, self.log, container)
            self.adapters[adapter.name] = adapter

    def get(self, name: str) -> BaseAdapter:
        """Adapterni nomi bo'yicha qaytaradi."""
        if name not in self.adapters:
            raise UzERPError(f"Integratsiya topilmadi: {name}")
        return self.adapters[name]

    def list_all(self) -> list[dict]:
        """Barcha adapterlar holati (sozlamalar sahifasi uchun)."""
        return [adapter.status() for adapter in self.adapters.values()]

    def notify(self, text: str) -> dict:
        """
        Umumiy xabarnoma: sozlangan birinchi kanal (Telegram -> Email)
        orqali yuboriladi.
        """
        telegram = self.adapters["telegram"]
        if telegram.is_configured():
            return telegram.send_message(text)
        email = self.adapters["email"]
        if email.is_configured():
            return email.send_message(
                str(email._cfg("sender")), "UzERP xabarnoma", text)
        return {"prepared": True, "sent": False,
                "note": "Hech qanday xabarnoma kanali sozlanmagan."}
