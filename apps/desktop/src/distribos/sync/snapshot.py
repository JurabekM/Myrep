"""Snapshot va bootstrap — yangi qurilmani tez ishga tushirish.

Yangi telefon butun hodisa tarixini boshidan yuklamasligi kerak (bir yillik
savdoda bu yuz minglab hodisa). Buning o'rniga u ma'lum bir checkpoint'ga
bog'langan **snapshot** oladi va undan keyingi hodisalarni oddiy yo'l bilan
qabul qiladi.

Qat'iy qoidalar (topshiriq §11):

* snapshot brokerda DOIMIY saqlanmaydi — uni tirik, vakolatli peer beradi;
* role-scoped: agentga butun moliyaviy baza yuborilmaydi;
* qismlarga bo'linadi va uzilib qolsa **davom ettiriladi** (resume);
* yaxlitligi tekshiriladi;
* muddati o'tadi;
* bekor qilingan qurilma uni ocholmaydi (DES-1 muhri buni ta'minlaydi).
"""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass, field
from typing import Any

import cbor2
from sqlalchemy import select
from sqlalchemy.orm import Session

from distribos.application.permissions import should_replicate
from distribos.persistence.models import (
    Customer,
    EventLog,
    Order,
    OrderLine,
    Payment,
    Product,
    StockSnapshot,
    Warehouse,
    utcnow,
)

#: Bitta chunk hajmi. MQTT xabar chegarasidan (256 KiB) xavfsiz pastda:
#: DES-1 ustamasi 3.4 KB va CBOR qo'shimchasi ham sig'ishi kerak.
CHUNK_BYTES = 128 * 1024

#: Snapshot shu muddatdan keyin yaroqsiz.
SNAPSHOT_TTL = dt.timedelta(hours=24)


class SnapshotError(RuntimeError):
    """Snapshot yaratib yoki tiklab bo'lmadi."""


@dataclass(slots=True)
class SnapshotManifest:
    """Snapshot tavsifi — chunk'lardan oldin yuboriladi."""

    snapshot_id: str
    #: Qaysi nuqtagacha: `{device_id_hex: last_sequence}`.
    checkpoint: dict[str, int]
    role: str
    schema_version: int
    total_chunks: int
    total_bytes: int
    #: Butun snapshot'ning SHA3-256 hash'i — yaxlitlik tekshiruvi.
    digest: str
    created_at: str
    expires_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "checkpoint": self.checkpoint,
            "role": self.role,
            "schema_version": self.schema_version,
            "total_chunks": self.total_chunks,
            "total_bytes": self.total_bytes,
            "digest": self.digest,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SnapshotManifest:
        return cls(
            snapshot_id=data["snapshot_id"],
            checkpoint=dict(data["checkpoint"]),
            role=data["role"],
            schema_version=int(data["schema_version"]),
            total_chunks=int(data["total_chunks"]),
            total_bytes=int(data["total_bytes"]),
            digest=data["digest"],
            created_at=data["created_at"],
            expires_at=data["expires_at"],
        )

    @property
    def is_expired(self) -> bool:
        expiry = dt.datetime.fromisoformat(self.expires_at)
        return utcnow() > expiry


@dataclass(slots=True)
class SnapshotChunk:
    snapshot_id: str
    index: int
    data: bytes

    def to_dict(self) -> dict[str, Any]:
        return {"snapshot_id": self.snapshot_id, "index": self.index, "data": self.data}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SnapshotChunk:
        return cls(data["snapshot_id"], int(data["index"]), bytes(data["data"]))


#: Qaysi jadval qaysi aggregate turiga tegishli — role-scope shunga qarab.
_TABLE_AGGREGATES: tuple[tuple[str, str, Any], ...] = (
    ("products", "Product", Product),
    ("customers", "Customer", Customer),
    ("warehouses", "Inventory", Warehouse),
    ("stock", "Inventory", StockSnapshot),
    ("orders", "Order", Order),
    ("order_lines", "Order", OrderLine),
    ("payments", "Payment", Payment),
)


def _row_to_dict(row: Any) -> dict[str, Any]:
    """ORM qatorini oddiy dict'ga aylantiradi (CBOR uchun)."""
    result: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, dt.datetime) or isinstance(value, dt.date):
            value = value.isoformat()
        elif isinstance(value, bytes):
            value = value.hex()
        elif hasattr(value, "quantize"):        # Decimal
            value = str(value)
        result[column.name] = value
    return result


def build_snapshot(
    session: Session, *, role: str, snapshot_id: str, schema_version: int = 1
) -> tuple[SnapshotManifest, list[SnapshotChunk]]:
    """Rolga mos snapshot yaratadi va qismlarga bo'ladi.

    Agent roliga moliyaviy jadval TUSHMAYDI — bu `should_replicate` orqali
    hal qilinadi, ya'ni qoida bitta joyda yoziladi.
    """
    tables: dict[str, list[dict[str, Any]]] = {}
    for name, aggregate_type, model in _TABLE_AGGREGATES:
        if not should_replicate(role, aggregate_type):
            continue
        rows = session.execute(select(model)).scalars().all()
        tables[name] = [_row_to_dict(row) for row in rows]

    checkpoint = {
        device_id.hex(): int(highest)
        for device_id, highest in session.execute(
            select(EventLog.device_id, __import__("sqlalchemy").func.max(
                EventLog.device_sequence
            )).group_by(EventLog.device_id)
        ).all()
    }

    body = cbor2.dumps({"tables": tables, "schema_version": schema_version})
    digest = hashlib.sha3_256(body).hexdigest()

    chunks = [
        SnapshotChunk(snapshot_id, index, body[offset:offset + CHUNK_BYTES])
        for index, offset in enumerate(range(0, len(body), CHUNK_BYTES))
    ]
    if not chunks:
        chunks = [SnapshotChunk(snapshot_id, 0, b"")]

    created = utcnow()
    manifest = SnapshotManifest(
        snapshot_id=snapshot_id,
        checkpoint=checkpoint,
        role=role,
        schema_version=schema_version,
        total_chunks=len(chunks),
        total_bytes=len(body),
        digest=digest,
        created_at=created.isoformat(),
        expires_at=(created + SNAPSHOT_TTL).isoformat(),
    )
    return manifest, chunks


@dataclass
class SnapshotAssembler:
    """Kelgan qismlarni yig'adi. Uzilib qolsa DAVOM ETTIRADI."""

    manifest: SnapshotManifest
    received: dict[int, bytes] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return len(self.received) == self.manifest.total_chunks

    @property
    def missing_indexes(self) -> list[int]:
        """Yetishmayotgan qismlar — faqat shularni qayta so'raymiz."""
        return [i for i in range(self.manifest.total_chunks) if i not in self.received]

    @property
    def progress(self) -> float:
        if self.manifest.total_chunks == 0:
            return 1.0
        return len(self.received) / self.manifest.total_chunks

    def add(self, chunk: SnapshotChunk) -> None:
        if chunk.snapshot_id != self.manifest.snapshot_id:
            raise SnapshotError("chunk boshqa snapshot'ga tegishli")
        if not 0 <= chunk.index < self.manifest.total_chunks:
            raise SnapshotError(f"chunk indeksi chegaradan tashqarida: {chunk.index}")
        self.received[chunk.index] = chunk.data

    def finish(self) -> dict[str, Any]:
        """Yig'ilgan snapshot'ni ochadi. Yaxlitlik tekshiriladi."""
        if not self.is_complete:
            raise SnapshotError(
                f"snapshot to'liq emas: {self.missing_indexes} qismlar yetishmaydi"
            )
        if self.manifest.is_expired:
            raise SnapshotError("snapshot muddati o'tgan")

        body = b"".join(self.received[i] for i in range(self.manifest.total_chunks))
        if len(body) != self.manifest.total_bytes:
            raise SnapshotError("snapshot hajmi manifestga mos emas")
        if hashlib.sha3_256(body).hexdigest() != self.manifest.digest:
            raise SnapshotError("snapshot yaxlitligi buzilgan (hash mos emas)")

        payload = cbor2.loads(body)
        if int(payload.get("schema_version", 0)) > self.manifest.schema_version:
            raise SnapshotError("snapshot sxemasi biz biladiganidan yangi")
        return payload


#: `_TABLE_AGGREGATES` dagi nom -> model, tiklash uchun.
_RESTORE_ORDER: tuple[tuple[str, Any], ...] = (
    ("warehouses", Warehouse),
    ("products", Product),
    ("customers", Customer),
    ("orders", Order),
    ("order_lines", OrderLine),
    ("payments", Payment),
    ("stock", StockSnapshot),
)

#: Qaysi maydonlar baytga qaytarilishi kerak.
_BINARY_FIELDS = {"tenant_id", "device_id", "origin_device_id", "sender_device_id"}


def restore_snapshot(
    session: Session, payload: dict[str, Any], manifest: SnapshotManifest
) -> dict[str, int]:
    """Snapshot'ni bo'sh bazaga tiklaydi.

    Tartib muhim: ota-ona jadvallar oldin (FK). Mavjud yozuv ustidan
    yozilmaydi — snapshot faqat BOOTSTRAP uchun.
    """
    tables = payload.get("tables", {})
    restored: dict[str, int] = {}

    for name, model in _RESTORE_ORDER:
        rows = tables.get(name)
        if not rows:
            continue
        count = 0
        columns = {c.name: c for c in model.__table__.columns}
        primary = [c.name for c in model.__table__.primary_key.columns]

        for raw in rows:
            key = tuple(raw[name_] for name_ in primary)
            lookup = key[0] if len(key) == 1 else key
            if session.get(model, lookup) is not None:
                continue

            values: dict[str, Any] = {}
            for column_name, value in raw.items():
                column = columns.get(column_name)
                if column is None or value is None:
                    values[column_name] = value
                    continue
                type_name = column.type.__class__.__name__
                if type_name == "LargeBinary" and isinstance(value, str):
                    values[column_name] = bytes.fromhex(value)
                elif type_name == "DateTime" and isinstance(value, str):
                    parsed = dt.datetime.fromisoformat(value)
                    values[column_name] = (
                        parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)
                    )
                elif type_name == "Date" and isinstance(value, str):
                    values[column_name] = dt.date.fromisoformat(value)
                else:
                    values[column_name] = value

            session.add(model(**values))
            count += 1
        session.flush()
        restored[name] = count

    return restored


def checkpoint_to_ranges(
    local: dict[str, int], remote: dict[str, int]
) -> dict[str, list[int]]:
    """Snapshot checkpoint'idan keyin nima yetishmayotganini hisoblaydi."""
    wanted: dict[str, list[int]] = {}
    for device_hex, remote_highest in remote.items():
        local_highest = local.get(device_hex, 0)
        if remote_highest > local_highest:
            wanted[device_hex] = [local_highest + 1, remote_highest]
    return wanted
