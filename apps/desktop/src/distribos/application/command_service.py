"""Buyruq xizmati — topshiriq §7.1 ning to'liq oqimi.

```
1. Buyruq validatsiyasi          -> contracts
2. Vakolatni tekshirish          -> permissions
3. Domen qoidalarini bajarish    -> domain.rules
4. Lokal biznes jadvallarini yangilash \\
5. Immutable domain event yaratish       > BIR tranzaksiya
6. Sync outbox'ga yozish               /
7. Commit
8. UI'ga natijani ko'rsatish
9. Fon worker orqali MQTT'ga yuborish
```

Muhim qaror: **lokal hodisa ham proyektor orqali o'tadi.** Ya'ni biznes
jadvalini qo'lda yangilamaymiz — hodisani yozamiz va o'sha proyektor uni
qo'llaydi. Bir kod yo'li bo'lgani uchun desktop va telefon bir xil
hodisalardan bir xil holatni hisoblaydi; «yaratuvchi qurilmada boshqacha
ko'rinadi» degan sinf xatolar umuman paydo bo'lmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from distribos.application.permissions import PermissionDenied, ensure_allowed
from distribos.application.projector import ProjectionResult, Projector
from distribos.domain.contracts import ContractError, load_registry
from distribos.persistence.models import EventLog
from distribos.sync.event_store import EventStore, NewEvent


class CommandRejected(RuntimeError):
    """Buyruq bajarilmadi. Sabab foydalanuvchiga ko'rsatiladi."""


@dataclass(slots=True)
class CommandResult:
    event: EventLog
    projection: ProjectionResult

    @property
    def applied(self) -> bool:
        return self.projection.applied > 0


class CommandService:
    """Hodisa yozish va darhol qo'llash uchun yagona kirish nuqtasi."""

    def __init__(
        self,
        store: EventStore,
        projector: Projector | None = None,
        *,
        actor_role: str = "owner",
    ) -> None:
        self._store = store
        self._projector = projector or Projector()
        self._registry = load_registry()
        self._actor_role = actor_role

    def submit(
        self,
        session: Session,
        event: NewEvent,
        *,
        actor_role: str | None = None,
    ) -> CommandResult:
        """Buyruqni bajaradi. Chaqiruvchi `unit_of_work()` ichida ishlatadi."""
        role = actor_role or self._actor_role

        # 1. Kontrakt validatsiyasi — noto'g'ri buyruq JURNALGA TUSHMAYDI.
        #    Buzuq hodisani yozib, keyin peer'larga tarqatish eng yomon
        #    variant: uni orqaga qaytarib bo'lmaydi.
        try:
            self._registry.validate(event.event_type, event.payload, event.schema_version)
        except ContractError as exc:
            raise CommandRejected(str(exc)) from exc

        # 2. Vakolat.
        try:
            ensure_allowed(role, event.event_type)
        except PermissionDenied as exc:
            raise CommandRejected(str(exc)) from exc

        # 3-6. Hodisa + outbox bitta tranzaksiyada.
        record = self._store.append(session, event)
        session.flush()

        # 4. Proyektor biznes jadvallarini yangilaydi — SHU tranzaksiyada.
        projection = self._projector.drain(session)
        return CommandResult(event=record, projection=projection)

    def replay_pending(self, session: Session) -> ProjectionResult:
        """Kechiktirilgan hodisalarni qayta ko'radi (fon vazifasi)."""
        return self._projector.drain(session)

    def rebuild_projections(self, session: Session) -> ProjectionResult:
        """Biznes jadvallarini hodisa jurnalidan QAYTA quradi.

        Biznes jadvallari kesh, jurnal esa haqiqat manbai. Kesh buzilsa
        (yoki sxema o'zgarsa) shu funksiya uni tiklaydi.
        """
        from sqlalchemy import update

        session.execute(update(EventLog).values(applied_at=None, projection_attempts=0))
        session.flush()
        return self._projector.drain(session, passes=20)


def build_payload(**fields: Any) -> dict[str, Any]:
    """`None` qiymatlarni tashlab, toza payload yasaydi.

    Kontrakt noma'lum maydonni rad etadi, `None` esa «berilmagan» degani —
    uni yubormaslik kerak.
    """
    return {key: value for key, value in fields.items() if value is not None}
