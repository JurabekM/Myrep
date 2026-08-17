"""Telephony adapters (Twilio, generic SIP provider, demo)."""

from __future__ import annotations

import logging
import random
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx

from app.integrations.base import AdapterCredentials, AdapterResult, BaseAdapter
from app.models.enums import CallDirection, CallOutcome
from app.utils.dates import now

logger = logging.getLogger(__name__)
TIMEOUT = 20.0


@dataclass
class CallResult:
    """Normalised description of a placed or received call."""

    external_id: str
    direction: str
    phone: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int = 0
    outcome: str = CallOutcome.NO_ANSWER
    recording_path: str = ""
    transcript_text: str = ""
    extra: dict[str, str] = field(default_factory=dict)


class TelephonyAdapter(BaseAdapter):
    """Place calls and retrieve their recordings."""

    @abstractmethod
    def place_call(self, phone: str, operator_caller_id: str = "") -> AdapterResult:
        """Start an outbound call."""

    @abstractmethod
    def fetch_recent_calls(self, since: datetime | None = None) -> list[CallResult]:
        """Return calls completed since ``since``."""


#: Scripted demo transcripts (Uzbek and Russian) covering typical outcomes.
DEMO_TRANSCRIPTS: list[tuple[str, str, str]] = [
    (
        "uz",
        CallOutcome.BOOKED,
        "Operator: Assalomu alaykum, MedLine Clinic. Mijoz: Salom, dermatolog qabuliga "
        "yozilmoqchiman. Operator: Albatta, ertaga soat 15:00 bo'sh. Mijoz: Menga to'g'ri "
        "keladi. Operator: Ismingiz va raqamingizni ayting. Mijoz: Nodira, 90 123 45 67. "
        "Operator: Yozdim, ertaga kutamiz.",
    ),
    (
        "ru",
        CallOutcome.TOO_EXPENSIVE,
        "Оператор: Здравствуйте, клиника MedLine. Клиент: Сколько стоит лазерная эпиляция? "
        "Оператор: От 350 тысяч сум. Клиент: Дороговато, я подумаю. Оператор: Хорошо, у нас "
        "бывают акции. Клиент: Спасибо, до свидания.",
    ),
    (
        "uz",
        CallOutcome.NO_ANSWER,
        "Qo'ng'iroq javobsiz qoldi.",
    ),
    (
        "ru",
        CallOutcome.REFUSED,
        "Оператор: Добрый день! Клиент: Я уже был у вас, мне не понравилось обслуживание, "
        "больше не звоните. Оператор: Извините за неудобство.",
    ),
    (
        "uz",
        CallOutcome.CALLBACK,
        "Operator: Salom, sizga qo'ng'iroq qilyapman. Mijoz: Hozir bandman, keyinroq "
        "qo'ng'iroq qiling iltimos. Operator: Albatta, ertaga aloqaga chiqaman.",
    ),
]


class DemoTelephonyAdapter(TelephonyAdapter):
    """Offline telephony simulator producing scripted calls and transcripts."""

    provider = "demo_telephony"
    title = "Demo telefoniya"
    is_demo = True

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()
        self._random = random.Random(seed)
        self._calls: list[CallResult] = []

    def test_connection(self) -> AdapterResult:
        """Always available."""
        self.last_sync_at = now()
        return AdapterResult.success("Demo telefoniya faol")

    def place_call(self, phone: str, operator_caller_id: str = "") -> AdapterResult:
        """Simulate an outbound call with a random but plausible outcome."""
        language, outcome, transcript = self._random.choice(DEMO_TRANSCRIPTS)
        duration = 0 if outcome == CallOutcome.NO_ANSWER else self._random.randint(45, 320)
        started = now()
        result = CallResult(
            external_id=f"demo-call-{self._random.randint(100000, 999999)}",
            direction=CallDirection.OUTBOUND,
            phone=phone,
            started_at=started,
            ended_at=started + timedelta(seconds=duration),
            duration_seconds=duration,
            outcome=outcome,
            transcript_text=transcript,
            extra={"language": language},
        )
        self._calls.append(result)
        return AdapterResult.success(
            "Demo qo'ng'iroq bajarildi", external_id=result.external_id, call=result
        )

    def fetch_recent_calls(self, since: datetime | None = None) -> list[CallResult]:
        """Return simulated calls."""
        if since is None:
            return list(self._calls)
        return [c for c in self._calls if c.started_at >= since]


class TwilioAdapter(TelephonyAdapter):
    """Twilio Programmable Voice adapter."""

    provider = "twilio"
    title = "Twilio Voice"

    def is_configured(self) -> bool:
        """Requires account SID, auth token and a caller id."""
        return self.credentials.has("account_sid", "auth_token", "from_number")

    def _auth(self) -> tuple[str, str]:
        """HTTP basic auth pair."""
        return self.credentials.get("account_sid"), self.credentials.get("auth_token")

    def test_connection(self) -> AdapterResult:
        """Read the account resource."""
        if not self.is_configured():
            return AdapterResult.failure("Twilio credentials kiritilmagan", "not_configured")
        sid = self.credentials.get("account_sid")
        try:
            response = httpx.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                auth=self._auth(),
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        if response.status_code >= 400:
            self.last_error = str(payload.get("message", "auth error"))
            return AdapterResult.failure(self.last_error, "api")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success(f"{payload.get('friendly_name', 'Twilio')} ulandi")

    def place_call(self, phone: str, operator_caller_id: str = "") -> AdapterResult:
        """Create an outbound call resource."""
        if not self.is_configured():
            return AdapterResult.failure("Twilio sozlanmagan", "not_configured")
        sid = self.credentials.get("account_sid")
        twiml_url = self.credentials.get("twiml_url", "http://demo.twilio.com/docs/voice.xml")
        try:
            response = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json",
                auth=self._auth(),
                data={
                    "To": phone,
                    "From": operator_caller_id or self.credentials.get("from_number"),
                    "Url": twiml_url,
                    "Record": "true",
                },
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Qo'ng'iroq bo'lmadi: {type(exc).__name__}", "network")
        if response.status_code >= 400:
            self.last_error = str(payload.get("message", ""))
            return AdapterResult.failure(self.last_error, "api")
        return AdapterResult.success("Qo'ng'iroq boshlandi", external_id=payload.get("sid", ""))

    def fetch_recent_calls(self, since: datetime | None = None) -> list[CallResult]:
        """List recent calls from the Twilio API."""
        if not self.is_configured():
            return []
        sid = self.credentials.get("account_sid")
        params: dict[str, str] = {"PageSize": "50"}
        if since:
            params["StartTime>"] = since.strftime("%Y-%m-%d")
        try:
            response = httpx.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json",
                auth=self._auth(),
                params=params,
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return []
        results: list[CallResult] = []
        for call in payload.get("calls", []):
            duration = int(call.get("duration") or 0)
            started = now()
            results.append(
                CallResult(
                    external_id=call.get("sid", ""),
                    direction=(
                        CallDirection.INBOUND
                        if call.get("direction", "").startswith("inbound")
                        else CallDirection.OUTBOUND
                    ),
                    phone=call.get("to", ""),
                    started_at=started - timedelta(seconds=duration),
                    ended_at=started,
                    duration_seconds=duration,
                    outcome=(
                        CallOutcome.NO_ANSWER
                        if call.get("status") in {"no-answer", "busy", "failed"}
                        else CallOutcome.INTERESTED
                    ),
                )
            )
        self.last_sync_at = now()
        return results


class SIPProviderAdapter(TelephonyAdapter):
    """Generic REST bridge for a local SIP/PBX provider (Asterisk, OnlinePBX...)."""

    provider = "sip"
    title = "SIP / PBX provider"

    def is_configured(self) -> bool:
        """Requires the PBX base URL and an API key."""
        return self.credentials.has("base_url", "api_key")

    def _headers(self) -> dict[str, str]:
        """Authorization header for the PBX API."""
        return {"Authorization": f"Bearer {self.credentials.get('api_key')}"}

    def test_connection(self) -> AdapterResult:
        """GET ``/status`` on the PBX bridge."""
        if not self.is_configured():
            return AdapterResult.failure("PBX URL va API key kerak", "not_configured")
        try:
            response = httpx.get(
                f"{self.credentials.get('base_url').rstrip('/')}/status",
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Ulanib bo'lmadi: {type(exc).__name__}", "network")
        self.last_error = ""
        self.last_sync_at = now()
        return AdapterResult.success("PBX ulandi")

    def place_call(self, phone: str, operator_caller_id: str = "") -> AdapterResult:
        """Ask the PBX to originate a call."""
        if not self.is_configured():
            return AdapterResult.failure("PBX sozlanmagan", "not_configured")
        try:
            response = httpx.post(
                f"{self.credentials.get('base_url').rstrip('/')}/calls",
                headers=self._headers(),
                json={"to": phone, "from": operator_caller_id or self.credentials.get("extension")},
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return AdapterResult.failure(f"Qo'ng'iroq bo'lmadi: {type(exc).__name__}", "network")
        return AdapterResult.success("Qo'ng'iroq boshlandi", external_id=str(payload.get("id", "")))

    def fetch_recent_calls(self, since: datetime | None = None) -> list[CallResult]:
        """Read the PBX call log."""
        if not self.is_configured():
            return []
        try:
            response = httpx.get(
                f"{self.credentials.get('base_url').rstrip('/')}/calls",
                headers=self._headers(),
                params={"since": since.isoformat()} if since else None,
                timeout=TIMEOUT,
            )
            payload = response.json()
        except Exception as exc:
            self.last_error = type(exc).__name__
            return []
        results: list[CallResult] = []
        for call in payload if isinstance(payload, list) else payload.get("calls", []):
            results.append(
                CallResult(
                    external_id=str(call.get("id", "")),
                    direction=call.get("direction", CallDirection.OUTBOUND),
                    phone=str(call.get("phone", "")),
                    started_at=now(),
                    duration_seconds=int(call.get("duration") or 0),
                    outcome=call.get("outcome", CallOutcome.NO_ANSWER),
                    recording_path=str(call.get("recording_url", "")),
                )
            )
        self.last_sync_at = now()
        return results


__all__ = [
    "AdapterCredentials",
    "TelephonyAdapter",
    "CallResult",
    "DemoTelephonyAdapter",
    "TwilioAdapter",
    "SIPProviderAdapter",
]
