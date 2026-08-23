"""Deterministik proyektor — hodisalarni biznes jadvallariga qo'llaydi.

Muhim xususiyat: **deterministik**. Bir xil hodisalar to'plami, qanday
tartibda kelishidan qat'i nazar, bir xil yakuniy holatni beradi. Buni
ta'minlovchi uchta qoida:

1. Qoldiq va moliya — append-only, tartibga bog'liq emas (yig'indi).
2. Katalog va mijoz — maydon darajasidagi HLC solishtiruvi: eng kech
   tamg'a yutadi, kelish tartibi emas.
3. Buyurtma holati — holat mashinasi; noqonuniy o'tish qo'llanmaydi va
   konflikt sifatida yoziladi.

Shu sababli hodisa kech kelsa ham (bir necha kun offline qurilma) natija
buzilmaydi.
"""

from __future__ import annotations

import datetime as dt
import enum
import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from distribos.domain.contracts import ContractError, load_registry
from distribos.domain.ids import HybridTimestamp
from distribos.domain.rules import can_transition, compute_order_totals
from distribos.persistence.models import (
    AuditLog,
    ConflictRecord,
    Customer,
    EventLog,
    InventoryMovement,
    Order,
    OrderLine,
    OrderState,
    Payment,
    PaymentAllocation,
    Product,
    StockSnapshot,
    User,
    Visit,
    utcnow,
)

logger = logging.getLogger(__name__)


class ProjectionError(RuntimeError):
    """Hodisani qo'llab bo'lmadi."""


class Outcome(enum.Enum):
    """Hodisani qo'llash natijasi."""

    APPLIED = "APPLIED"
    #: Ota-ona yozuv hali kelmagan (tartib buzilishi). Hodisa
    #: YO'QOTILMAYDI — `applied_at` NULL qoladi va keyingi urinishda
    #: qayta ko'riladi. Bu MQTT ustida ishlash uchun majburiy.
    DEFERRED = "DEFERRED"
    #: Zid amal — odam ko'rishi kerak.
    CONFLICT = "CONFLICT"


#: Necha marta kechiktirilgandan keyin konflikt sifatida ko'rsatiladi.
MAX_PROJECTION_ATTEMPTS = 12


@dataclass(slots=True)
class ProjectionResult:
    applied: int = 0
    duplicates: int = 0
    conflicts: int = 0
    rejected: int = 0
    deferred: int = 0


def _parse_ts(value: Any) -> dt.datetime:
    """ISO-8601 matnni tz-aware datetime'ga aylantiradi.

    tzinfo'siz datetime bazadagi timestamptz bilan solishtirilganda
    jimgina noto'g'ri natija beradi — shuning uchun doim UTC qo'yiladi.
    """
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.UTC)
    text = str(value).replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _constraint_detail(exc: Exception) -> str:
    """Cheklov xatosidan qisqa, maxfiy ma'lumotsiz tavsif.

    To'liq SQL parametrlari mijoz nomi va summalarni o'z ichiga oladi —
    ular konflikt yozuviga TUSHMASLIGI kerak.
    """
    text = str(getattr(exc, "orig", exc))
    return text.splitlines()[0][:200] if text else "cheklov buzildi"


class Projector:
    """Hodisalarni biznes jadvallariga qo'llaydi."""

    def __init__(self) -> None:
        self._registry = load_registry()
        self._handlers = {
            "PRODUCT_CREATED": self._apply_product_created,
            "PRODUCT_UPDATED": self._apply_product_updated,
            "PRODUCT_PRICE_CHANGED": self._apply_price_changed,
            "CUSTOMER_CREATED": self._apply_customer_created,
            "CUSTOMER_UPDATED": self._apply_customer_updated,
            "ORDER_CREATED": self._apply_order_created,
            "ORDER_STATE_CHANGED": self._apply_order_state_changed,
            "INVENTORY_MOVED": self._apply_inventory_moved,
            "PAYMENT_RECORDED": self._apply_payment_recorded,
            "PAYMENT_REVERSED": self._apply_payment_reversed,
            "VISIT_RECORDED": self._apply_visit_recorded,
            "USER_CREATED": self._apply_user_created,
            "DEVICE_REVOKED": self._apply_device_revoked,
        }

    # --- kirish nuqtasi ---------------------------------------------------

    def apply(self, session: Session, record: EventLog) -> ProjectionResult:
        """Bitta hodisani qo'llaydi. Idempotent: qayta chaqirilsa o'tkazadi."""
        result = ProjectionResult()

        if record.applied_at is not None:
            result.duplicates = 1
            return result

        import cbor2

        payload = cbor2.loads(record.payload)

        try:
            self._registry.validate(record.event_type, payload, record.schema_version)
        except ContractError as exc:
            # Kontraktga mos kelmagan hodisa QO'LLANMAYDI, lekin jurnaldan
            # o'chirilmaydi — u imzolangan tarix. Konflikt sifatida
            # ko'rsatiladi va odam qaraydi.
            self._record_conflict(
                session, record, strategy="CONTRACT", detail=str(exc)
            )
            record.applied_at = utcnow()
            result.rejected = 1
            result.conflicts = 1
            return result

        handler = self._handlers.get(record.event_type)
        if handler is None:
            self._record_conflict(
                session, record, strategy="UNKNOWN_TYPE",
                detail=f"Qo'llovchi yo'q: {record.event_type}",
            )
            record.applied_at = utcnow()
            result.rejected = 1
            return result

        # Handler'ni SAVEPOINT ichida chaqiramiz. Sabab: bitta hodisa
        # baza cheklovini buzsa (masalan ikki qurilma offline'da bir xil
        # buyurtma raqamini bergan), butun batch yiqilmasligi kerak —
        # qolgan hodisalar qo'llanaveradi, buzuq bittasi konflikt bo'ladi.
        from sqlalchemy.exc import IntegrityError

        savepoint = session.begin_nested()
        try:
            outcome = handler(session, record, payload)
            session.flush()
            savepoint.commit()
        except IntegrityError as exc:
            savepoint.rollback()
            self._record_conflict(
                session, record, strategy="UNIQUE_CONSTRAINT",
                detail=_constraint_detail(exc),
            )
            record.applied_at = utcnow()
            result.conflicts = 1
            return result

        if outcome is Outcome.DEFERRED:
            record.projection_attempts = (record.projection_attempts or 0) + 1
            if record.projection_attempts >= MAX_PROJECTION_ATTEMPTS:
                # Ota-ona yozuv juda uzoq kelmadi — endi bu konflikt,
                # jimgina yo'qolgan hodisa emas.
                self._record_conflict(
                    session, record, strategy="MISSING_PARENT",
                    detail=(
                        f"{record.projection_attempts} urinishdan keyin ham "
                        "bog'liq yozuv topilmadi"
                    ),
                )
                record.applied_at = utcnow()
                result.conflicts = 1
            else:
                result.deferred = 1
            return result

        record.applied_at = utcnow()
        if outcome is Outcome.CONFLICT:
            result.conflicts = 1
        else:
            result.applied = 1
        self._audit(session, record, payload)
        return result

    def apply_many(self, session: Session, records: list[EventLog]) -> ProjectionResult:
        total = ProjectionResult()
        for record in records:
            single = self.apply(session, record)
            total.applied += single.applied
            total.duplicates += single.duplicates
            total.conflicts += single.conflicts
            total.rejected += single.rejected
            total.deferred += single.deferred
        return total

    def drain(self, session: Session, *, limit: int = 500, passes: int = 6) -> ProjectionResult:
        """Qo'llanmagan hodisalarni qayta-qayta ko'radi.

        Har o'tishda kamida bitta hodisa qo'llansa, keyingi o'tishda unga
        bog'liq kechiktirilganlar ham qo'llanishi mumkin. Hech narsa
        o'zgarmasa to'xtaymiz — cheksiz aylanish yo'q.
        """
        from sqlalchemy import select as _select

        total = ProjectionResult()
        for _ in range(passes):
            pending = list(session.execute(
                _select(EventLog)
                .where(EventLog.applied_at.is_(None))
                .order_by(EventLog.device_id, EventLog.device_sequence)
                .limit(limit)
            ).scalars())
            if not pending:
                break
            result = self.apply_many(session, pending)
            total.applied += result.applied
            total.duplicates += result.duplicates
            total.conflicts += result.conflicts
            total.rejected += result.rejected
            total.deferred += result.deferred
            if result.applied == 0 and result.conflicts == 0:
                break
        return total

    # --- maydon darajasidagi konflikt -------------------------------------

    @staticmethod
    def _field_versions(raw: str) -> dict[str, str]:
        try:
            data = json.loads(raw or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _accept_field(
        self, versions: dict[str, str], field: str, stamp: str
    ) -> bool:
        """Bu maydon uchun kelgan tamg'a mavjuddan kechroqmi.

        Solishtirish HLC bo'yicha — devor soati emas. Ikki qurilma soati
        farq qilsa ham natija deterministik va ikkala tomonda BIR XIL.
        """
        existing = versions.get(field)
        if existing is None:
            return Outcome.APPLIED
        try:
            return HybridTimestamp.decode(stamp) > HybridTimestamp.decode(existing)
        except (ValueError, AttributeError):
            return Outcome.APPLIED

    # --- katalog ----------------------------------------------------------

    def _apply_product_created(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        product = session.get(Product, payload["product_id"])
        if product is None:
            product = Product(id=payload["product_id"], sku=payload["sku"],
                              name=payload["name"], unit=payload["unit"])
            session.add(product)

        versions = self._field_versions(product.field_versions)
        for field in ("name", "sku", "barcode", "brand", "category_id", "unit"):
            if field in payload and self._accept_field(versions, field, record.logical_timestamp):
                setattr(product, field, payload[field])
                versions[field] = record.logical_timestamp
        for field in ("purchase_price", "retail_price", "wholesale_price", "agent_price"):
            if field in payload and self._accept_field(versions, field, record.logical_timestamp):
                setattr(product, field, int(payload[field]))
                versions[field] = record.logical_timestamp
        if "pack_size" in payload:
            product.pack_size = _decimal(payload["pack_size"])
        if "min_stock" in payload:
            product.min_stock = _decimal(payload["min_stock"])

        product.field_versions = json.dumps(versions)
        product.updated_at = record.occurred_at
        return Outcome.APPLIED

    def _apply_product_updated(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        product = session.get(Product, payload["product_id"])
        if product is None:
            return Outcome.DEFERRED   # PRODUCT_CREATED hali kelmagan

        for field, value in payload["changes"].items():
            if not hasattr(product, field):
                continue
            if self._accept_field(versions, field, record.logical_timestamp):
                setattr(product, field, value)
                versions[field] = record.logical_timestamp
            # Aks holda kechroq tamg'a allaqachon bor: kelgan o'zgarish
            # eskiroq. Bu KONFLIKT EMAS — HLC deterministik yutdi va
            # ikkala qurilmada ham bir xil natija chiqadi.

        product.field_versions = json.dumps(versions)
        product.updated_at = record.occurred_at
        return Outcome.APPLIED

    def _apply_price_changed(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        product = session.get(Product, payload["product_id"])
        if product is None:
            return Outcome.DEFERRED
        field = payload["field"]
        if field not in ("retail_price", "wholesale_price", "agent_price", "purchase_price"):
            return Outcome.CONFLICT

        versions = self._field_versions(product.field_versions)
        if not self._accept_field(versions, field, record.logical_timestamp):
            return Outcome.APPLIED  # eskiroq narx — e'tiborsiz, deterministik
        setattr(product, field, int(payload["new_price"]))
        versions[field] = record.logical_timestamp
        product.field_versions = json.dumps(versions)
        product.updated_at = record.occurred_at
        return Outcome.APPLIED

    # --- mijozlar ---------------------------------------------------------

    def _apply_customer_created(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        customer = session.get(Customer, payload["customer_id"])
        if customer is None:
            customer = Customer(id=payload["customer_id"], code=payload["code"],
                                name=payload["name"], kind=payload["kind"])
            session.add(customer)

        versions = self._field_versions(customer.field_versions)
        for field in ("name", "code", "kind", "phone", "address", "territory_id",
                      "assigned_agent_id", "price_tier", "notes"):
            if field in payload and self._accept_field(versions, field, record.logical_timestamp):
                setattr(customer, field, payload[field])
                versions[field] = record.logical_timestamp
        if "credit_limit" in payload:
            customer.credit_limit = int(payload["credit_limit"])
        if "payment_term_days" in payload:
            customer.payment_term_days = int(payload["payment_term_days"])
        for field in ("latitude", "longitude"):
            if field in payload:
                setattr(customer, field, _decimal(payload[field]))

        customer.field_versions = json.dumps(versions)
        customer.updated_at = record.occurred_at
        return Outcome.APPLIED

    def _apply_customer_updated(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        customer = session.get(Customer, payload["customer_id"])
        if customer is None:
            return Outcome.DEFERRED
        versions = self._field_versions(customer.field_versions)
        for field, value in payload["changes"].items():
            if hasattr(customer, field) and self._accept_field(
                versions, field, record.logical_timestamp
            ):
                setattr(customer, field, value)
                versions[field] = record.logical_timestamp
        customer.field_versions = json.dumps(versions)
        customer.updated_at = record.occurred_at
        return Outcome.APPLIED

    # --- buyurtmalar ------------------------------------------------------

    def _apply_order_created(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        if session.get(Order, payload["order_id"]) is not None:
            return Outcome.APPLIED  # takror — idempotent

        # Bog'liq yozuvlar hali kelmagan bo'lishi mumkin (tartib buzilishi).
        # FK xatosi bilan yiqilish o'rniga kechiktiramiz — hodisa
        # yo'qolmaydi va keyingi urinishda qo'llanadi.
        if session.get(Customer, payload["customer_id"]) is None:
            return Outcome.DEFERRED
        for line in payload["lines"]:
            if session.get(Product, line["product_id"]) is None:
                return Outcome.DEFERRED

        totals = compute_order_totals(payload["lines"])
        order = Order(
            id=payload["order_id"],
            number=payload["number"],
            customer_id=payload["customer_id"],
            warehouse_id=payload.get("warehouse_id"),
            agent_id=payload.get("agent_id"),
            state=OrderState.DRAFT,
            ordered_at=_parse_ts(payload["ordered_at"]),
            subtotal=totals.subtotal,
            discount_total=totals.discount_total,
            total=totals.total,
            currency=payload.get("currency", "UZS"),
            note=payload.get("note"),
            origin_device_id=record.device_id,
            created_at=record.occurred_at,
            updated_at=record.occurred_at,
        )
        session.add(order)
        session.flush()

        from distribos.domain.rules import line_total as compute_line_total

        for line in payload["lines"]:
            session.add(OrderLine(
                id=line["line_id"],
                order_id=order.id,
                product_id=line["product_id"],
                quantity=_decimal(line["quantity"]),
                unit_price=int(line["unit_price"]),
                discount_percent=_decimal(line.get("discount_percent", 0)),
                line_total=compute_line_total(
                    line["quantity"], int(line["unit_price"]),
                    line.get("discount_percent", 0),
                ),
            ))
        return Outcome.APPLIED

    def _apply_order_state_changed(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        order = session.get(Order, payload["order_id"])
        if order is None:
            return Outcome.DEFERRED   # ORDER_CREATED hali kelmagan

        current = OrderState(order.state)
        target = OrderState(payload["to_state"])

        if current == target:
            return Outcome.APPLIED  # takror hodisa — idempotent

        if not can_transition(current, target):
            # Noqonuniy o'tish JIMGINA qabul qilinmaydi. Ikki qurilma zid
            # amal qilgan bo'lishi mumkin — odam ko'rishi kerak.
            self._record_conflict(
                session, record, strategy="STATE_MACHINE",
                detail=f"{current.value} -> {target.value} mumkin emas",
                aggregate_id=order.id, local_value=current.value,
                remote_value=target.value,
            )
            return Outcome.CONFLICT

        order.state = target
        order.updated_at = record.occurred_at
        return Outcome.APPLIED

    # --- ombor ------------------------------------------------------------

    def _apply_inventory_moved(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        if session.get(InventoryMovement, payload["movement_id"]) is not None:
            return Outcome.APPLIED  # takror

        from distribos.persistence.models import Warehouse

        if session.get(Warehouse, payload["warehouse_id"]) is None:
            return Outcome.DEFERRED
        if session.get(Product, payload["product_id"]) is None:
            return Outcome.DEFERRED

        session.add(InventoryMovement(
            id=payload["movement_id"],
            warehouse_id=payload["warehouse_id"],
            product_id=payload["product_id"],
            batch_id=payload.get("batch_id"),
            movement_type=payload["movement_type"],
            quantity=_decimal(payload["quantity"]),
            unit_cost=int(payload.get("unit_cost", 0)),
            reference_type=payload.get("reference_type"),
            reference_id=payload.get("reference_id"),
            occurred_at=_parse_ts(payload["occurred_at"]),
            source_event_id=record.event_id,
            actor_id=record.actor_id,
            note=payload.get("note"),
        ))
        session.flush()
        self._refresh_stock(session, payload["warehouse_id"], payload["product_id"])
        return Outcome.APPLIED

    def _refresh_stock(self, session: Session, warehouse_id: str, product_id: str) -> None:
        """Qoldiq keshini harakatlardan QAYTA hisoblaydi.

        Inkremental qo'shish emas, to'liq qayta hisob: kech kelgan hodisa
        ham to'g'ri hisobga olinadi. Bu sekinroq, lekin **to'g'ri** —
        ma'lumot to'g'riligi tezlikdan ustun (topshiriq ustuvorligi).
        """
        from distribos.domain.rules import compute_stock

        movements = session.execute(
            select(InventoryMovement.movement_type, InventoryMovement.quantity)
            .where(
                InventoryMovement.warehouse_id == warehouse_id,
                InventoryMovement.product_id == product_id,
            )
            .order_by(InventoryMovement.occurred_at)
        ).all()

        on_hand, reserved = compute_stock([(m, q) for m, q in movements])

        snapshot = session.get(StockSnapshot, (warehouse_id, product_id))
        if snapshot is None:
            snapshot = StockSnapshot(warehouse_id=warehouse_id, product_id=product_id)
            session.add(snapshot)
        snapshot.quantity = on_hand
        snapshot.reserved = reserved
        snapshot.updated_at = utcnow()

    # --- moliya -----------------------------------------------------------

    def _apply_payment_recorded(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        if session.get(Payment, payload["payment_id"]) is not None:
            return Outcome.APPLIED

        customer_id = payload.get("customer_id")
        if customer_id and session.get(Customer, customer_id) is None:
            return Outcome.DEFERRED
        for allocation in payload.get("allocations", []):
            if session.get(Order, allocation["order_id"]) is None:
                return Outcome.DEFERRED

        session.add(Payment(
            id=payload["payment_id"],
            number=payload["number"],
            direction=payload["direction"],
            customer_id=payload.get("customer_id"),
            cash_register_id=payload.get("cash_register_id"),
            amount=int(payload["amount"]),
            currency=payload.get("currency", "UZS"),
            exchange_rate=_decimal(payload.get("exchange_rate", 1)),
            method=payload.get("method", "cash"),
            occurred_at=_parse_ts(payload["occurred_at"]),
            source_event_id=record.event_id,
            actor_id=record.actor_id,
            note=payload.get("note"),
        ))
        session.flush()

        for allocation in payload.get("allocations", []):
            session.add(PaymentAllocation(
                id=allocation["allocation_id"],
                payment_id=payload["payment_id"],
                order_id=allocation["order_id"],
                amount=int(allocation["amount"]),
            ))
            order = session.get(Order, allocation["order_id"])
            if order is not None:
                order.paid_total += int(allocation["amount"])
        return Outcome.APPLIED

    def _apply_payment_reversed(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        original = session.get(Payment, payload["reverses_payment_id"])
        if original is None:
            return Outcome.DEFERRED
        if session.get(Payment, payload["payment_id"]) is not None:
            return Outcome.APPLIED

        # To'lov O'CHIRILMAYDI — teskari yozuv qo'shiladi (§13).
        session.add(Payment(
            id=payload["payment_id"],
            number=payload["number"],
            direction="OUT" if original.direction == "IN" else "IN",
            customer_id=original.customer_id,
            cash_register_id=original.cash_register_id,
            amount=int(payload["amount"]),
            currency=original.currency,
            method=original.method,
            occurred_at=_parse_ts(payload["occurred_at"]),
            reverses_payment_id=original.id,
            source_event_id=record.event_id,
            actor_id=record.actor_id,
            note=payload.get("reason"),
        ))
        original.is_reversed = True
        return Outcome.APPLIED

    # --- boshqalar --------------------------------------------------------

    def _apply_visit_recorded(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        if session.get(Customer, payload["customer_id"]) is None:
            return Outcome.DEFERRED

        visit = session.get(Visit, payload["visit_id"])
        if visit is None:
            visit = Visit(id=payload["visit_id"], customer_id=payload["customer_id"],
                          agent_id=payload["agent_id"])
            session.add(visit)
        visit.route_id = payload.get("route_id", visit.route_id)
        if "started_at" in payload:
            visit.started_at = _parse_ts(payload["started_at"])
        if "finished_at" in payload:
            visit.finished_at = _parse_ts(payload["finished_at"])
        visit.outcome = payload.get("outcome", visit.outcome)
        visit.note = payload.get("note", visit.note)
        for field in ("latitude", "longitude"):
            if field in payload:
                setattr(visit, field, _decimal(payload[field]))
        return Outcome.APPLIED

    def _apply_user_created(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        if session.get(User, payload["user_id"]) is not None:
            return Outcome.APPLIED
        session.add(User(
            id=payload["user_id"], username=payload["username"],
            full_name=payload["full_name"], role=payload["role"],
            phone=payload.get("phone"), territory_id=payload.get("territory_id"),
            password_hash="",   # parol alohida, hodisa orqali uzatilmaydi
        ))
        return Outcome.APPLIED

    def _apply_device_revoked(self, session: Session, record: EventLog, payload: dict) -> Outcome:
        from distribos.persistence.models import DeviceState, PeerDevice

        device_id = bytes.fromhex(payload["device_id"])
        peer = session.get(PeerDevice, device_id)
        if peer is None:
            return Outcome.DEFERRED
        peer.state = DeviceState.REVOKED
        peer.revoked_at = _parse_ts(payload["revoked_at"])
        peer.revoked_reason = payload["reason"]
        return Outcome.APPLIED

    # --- yordamchilar -----------------------------------------------------

    def _record_conflict(
        self, session: Session, record: EventLog, *, strategy: str, detail: str,
        aggregate_id: str | None = None, local_value: str | None = None,
        remote_value: str | None = None,
    ) -> None:
        session.add(ConflictRecord(
            aggregate_type=record.aggregate_type,
            aggregate_id=aggregate_id or record.aggregate_id,
            remote_event_id=record.event_id,
            strategy=strategy,
            status="NEEDS_REVIEW",
            resolution=detail,
            local_value=local_value,
            remote_value=remote_value,
        ))
        logger.warning("Konflikt: %s %s — %s", record.event_type, strategy, detail)

    def _audit(self, session: Session, record: EventLog, payload: dict) -> None:
        """Audit yozuvi. Payload BU YERGA YOZILMAYDI — faqat qisqa tavsif."""
        session.add(AuditLog(
            occurred_at=record.occurred_at,
            actor_id=record.actor_id,
            device_id=record.device_id,
            action=record.event_type,
            entity_type=record.aggregate_type,
            entity_id=record.aggregate_id,
            summary=f"{record.event_type} qo'llandi ({record.aggregate_type})",
            source_event_id=record.event_id,
        ))
