"""Lokal baza (SQLCipher, shifrlangan). Barcha ma'lumot imzolangan MQTT operatsiyalaridan quriladi.

Protokol v2: docs/sync-mqtt.md. Har bir kiruvchi operatsiya apply_op() orqali o'tadi:
imzo -> muallif faolligi -> tur bo'yicha ruxsat -> tekshiruv -> qo'llash.
Natija: APPLIED, DUPLICATE, REJECTED,
PENDING (kutiladi), SKIPPED (qo'llanmadi, xato emas).
"""

import base64
import json
import logging
import re
import threading
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from ..money import round_som
from ..sync import crypto
from ..sync import ops as o

log = logging.getLogger(__name__)

HEX_KEY = re.compile(r"^[0-9a-f]{64}$")
MAX_DEFERRED = 5000

APPLIED = "applied"
DUPLICATE = "duplicate"
REJECTED = "rejected"
PENDING = "pending"
SKIPPED = "skipped"

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    sale_price INTEGER NOT NULL,
    cost_price INTEGER NOT NULL DEFAULT 0,
    min_stock TEXT NOT NULL DEFAULT '0',
    barcodes TEXT NOT NULL DEFAULT '[]',
    deleted INTEGER NOT NULL DEFAULT 0,
    updated_ts TEXT NOT NULL DEFAULT '',
    updated_op TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS product_prices (
    product_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    op_id TEXT NOT NULL,
    sale_price INTEGER NOT NULL,
    PRIMARY KEY (product_id, ts, op_id)
);
CREATE TABLE IF NOT EXISTS movements (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    qty TEXT NOT NULL,
    kind TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS movements_store_product ON movements (store_id, product_id);
CREATE TABLE IF NOT EXISTS sales (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    shift_id TEXT,
    number TEXT NOT NULL,
    status TEXT NOT NULL,
    total INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS refunded_sales (
    sale_id TEXT PRIMARY KEY,
    op_id TEXT NOT NULL,
    ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shifts (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    device TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    opening_cash INTEGER NOT NULL,
    closed_at TEXT,
    closing_cash INTEGER,
    summary TEXT
);
CREATE INDEX IF NOT EXISTS shifts_device ON shifts (device, closed_at);
CREATE TABLE IF NOT EXISTS outbox (
    op_id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    op TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS deferred (
    op_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    op TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS applied_ops (op_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    public_key TEXT NOT NULL,
    role TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    updated_ts TEXT NOT NULL DEFAULT '',
    updated_op TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS store_info (
    store_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    updated_ts TEXT NOT NULL DEFAULT '',
    updated_op TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    login TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    salt TEXT NOT NULL,
    pw_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    updated_ts TEXT NOT NULL DEFAULT '',
    updated_op TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS users_store_login ON users (store_id, login);
CREATE TABLE IF NOT EXISTS sync_state (name TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class _Invalid(Exception):
    """Operatsiya shakli yoki qiymati noto'g'ri: rad etiladi."""


def _dict_row(cursor, row):  # type: ignore[no-untyped-def]
    """sqlite3 va sqlcipher3 uchun bir xil qator shakli (lug'at)."""
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def _open_encrypted(path: str, key: str):  # type: ignore[no-untyped-def]
    """SQLCipher ochiladi. key: 64 belgili hex (32 bayt). Faqat shu shakl qabul qilinadi."""
    import sqlcipher3

    if not HEX_KEY.match(key):
        raise ValueError("Baza kaliti 64 belgili hex bo'lishi kerak")
    db = sqlcipher3.connect(path, check_same_thread=False)
    db.execute(f"PRAGMA key = \"x'{key}'\"")
    db.execute("SELECT count(*) FROM sqlite_master").fetchone()  # noto'g'ri kalitda shu yerda xato beradi
    return db


def _well_formed(op: Any) -> bool:
    if not isinstance(op, dict):
        return False
    if not all(key in op for key in ("op_id", "type", "device", "ts", "store_id", "payload", "sig")):
        return False
    text_fields = ("op_id", "type", "device", "ts", "store_id", "sig")
    return (
        all(isinstance(op[key], str) for key in text_fields)
        and isinstance(op["payload"], dict)
        and len(op["ts"]) == o.TS_LENGTH
    )


def _str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise _Invalid(key)
    return value


def _int(data: dict[str, Any], key: str, default: int | None = None) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _Invalid(key)
    return value


def _dec(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise _Invalid("qty")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _Invalid("qty") from exc


def _items(raw: Any) -> list[tuple[str, Decimal]]:
    if not isinstance(raw, list) or not raw:
        raise _Invalid("items")
    result: list[tuple[str, Decimal]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise _Invalid("items")
        qty = _dec(item.get("qty"))
        if qty <= 0:
            raise _Invalid("qty")
        result.append((_str(item, "product_id"), qty))
    return result


class LocalStore:
    def __init__(self, path: str = ":memory:", *, key: str | None = None, identity: Any = None) -> None:
        if key is not None:
            self._db = _open_encrypted(path, key)
        else:
            import sqlite3

            self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = _dict_row
        self._lock = threading.RLock()
        self._identity = identity
        with self._lock:
            self._db.executescript(SCHEMA)
            self._db.commit()
        self.device_id()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # --- holat -------------------------------------------------------------

    def get_state(self, name: str) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT value FROM sync_state WHERE name = ?", (name,)).fetchone()
        return None if row is None else str(row["value"])

    def set_state(self, name: str, value: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO sync_state (name, value) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET value = "
                "excluded.value",
                (name, value),
            )
            self._db.commit()

    def device_id(self) -> str:
        """Qurilmaning doimiy id'si (birinchi ishga tushirishda yaratiladi)."""
        existing = self.get_state("device_id")
        if existing:
            return existing
        value = str(uuid.uuid4())
        self.set_state("device_id", value)
        return value

    def public_key_hex(self) -> str:
        if self._identity is None:
            raise RuntimeError("Qurilma kaliti yuklanmagan")
        return str(self._identity.public_key_hex)

    def is_bootstrapped(self) -> bool:
        """Do'kon holati to'liq: egasi (yoki snapshot) orqali. Bo'lmasa, qurilma kutadi."""
        return self.get_state("bootstrapped") == "1"

    def _bootstrap_ts(self) -> str:
        return self.get_state("bootstrap_ts") or ""

    def next_receipt_number(self) -> str:
        """Chek raqami: qurilma qisqa id + ketma-ket son (ikki qurilmada bir xil raqam bo'lmasligi uchun)."""
        with self._lock:
            row = self._db.execute("SELECT value FROM sync_state WHERE name = 'receipt_seq'").fetchone()
            seq = int(row["value"]) + 1 if row else 1
            self._db.execute(
                "INSERT INTO sync_state (name, value) VALUES ('receipt_seq', ?) "
                "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                (str(seq),),
            )
            self._db.commit()
        return f"{self.device_id()[:4]}-{seq}"

    # --- imzolangan operatsiya yaratish --------------------------------------

    def new_op(
        self,
        op_type: str,
        payload: dict[str, Any],
        *,
        store_id: str | None = None,
        op_id: str | None = None,
    ) -> dict[str, Any]:
        """Shu qurilma nomidan imzolangan operatsiya (docs/sync-mqtt.md, 5-bo'lim)."""
        if self._identity is None:
            raise RuntimeError("Qurilma kaliti yuklanmagan")
        store = store_id or self.get_state("store_id")
        if not store:
            raise RuntimeError("Do'kon tanlanmagan")
        op = o.new_op(op_type, store, payload, device_id=self.device_id(), op_id=op_id)
        op["sig"] = base64.b64encode(self._identity.sign(crypto.canonical_bytes(op))).decode("ascii")
        return op

    def join_request(self, label: str) -> dict[str, Any]:
        """Yangi qurilmaning egasiga so'rovi: o'z kaliti bilan imzolangan (tasdiq uchun)."""
        payload = {"device_id": self.device_id(), "public_key": self.public_key_hex(), "label": label}
        return self.new_op(o.JOIN_REQUEST, payload)

    # --- do'kon bootstrap'i ------------------------------------------------------

    def init_owner(self, store_id: str, label: str) -> None:
        """Do'konni shu qurilma yaratadi: o'zi egasi, bootstrap shart emas."""
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO devices (device_id, store_id, public_key, role, label, active, "
                "updated_ts, updated_op) VALUES (?, ?, ?, ?, ?, 1, '', '')",
                (self.device_id(), store_id, self.public_key_hex(), o.ROLE_OWNER, label),
            )
            self._db.execute(
                "INSERT INTO sync_state (name, value) VALUES ('store_id', ?) "
                "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                (store_id,),
            )
            self._set_state_locked("bootstrapped", "1")
            self._set_state_locked("bootstrap_ts", "")
            self._db.commit()

    def set_pairing(self, store_id: str, owner_device_id: str, owner_public_key: str) -> None:
        """Juftlash kodi: egasi qurilmasi ishonch ildizi. Do'kon ma'lumoti snapshot orqali keladi."""
        if not HEX_KEY.match(owner_public_key):
            raise ValueError("Egasi kaliti noto'g'ri")
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO devices (device_id, store_id, public_key, role, label, active, "
                "updated_ts, updated_op) VALUES (?, ?, ?, ?, 'egasi', 1, '', '')",
                (owner_device_id, store_id, owner_public_key, o.ROLE_OWNER),
            )
            self._set_state_locked("store_id", store_id)
            self._set_state_locked("bootstrapped", "0")
            self._set_state_locked("bootstrap_ts", "")
            self._db.commit()

    def _set_state_locked(self, name: str, value: str) -> None:
        self._db.execute(
            "INSERT INTO sync_state (name, value) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET value = "
            "excluded.value",
            (name, value),
        )

    # --- navbat (yuborilmagan, mahalliy operatsiyalar) ---------------------------

    def enqueue(self, op: dict[str, Any]) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO outbox (op_id, store_id, op, created_at) VALUES (?, ?, ?, ?)",
                (op["op_id"], op["store_id"], json.dumps(op, ensure_ascii=False), op["ts"]),
            )
            self._db.commit()

    def pending_ops(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT op FROM outbox ORDER BY created_at, op_id LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(r["op"]) for r in rows]

    def pending_count(self) -> int:
        with self._lock:
            row = self._db.execute("SELECT COUNT(*) AS n FROM outbox").fetchone()
        return int(row["n"])

    def drop_outbox(self, op_id: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM outbox WHERE op_id = ?", (op_id,))
            self._db.commit()

    def deferred_count(self) -> int:
        with self._lock:
            row = self._db.execute("SELECT COUNT(*) AS n FROM deferred").fetchone()
        return int(row["n"])

    # --- o'qish: katalog, qoldiq, savdo -------------------------------------------

    def balance(self, store_id: str, product_id: str) -> Decimal:
        with self._lock:
            rows = self._db.execute(
                "SELECT qty FROM movements WHERE store_id = ? AND product_id = ?", (store_id, product_id)
            ).fetchall()
        return sum((Decimal(r["qty"]) for r in rows), Decimal(0))

    def _product_dict(self, row: dict[str, Any], store_id: str) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "unit": row["unit"],
            "sale_price": row["sale_price"],
            "cost_price": row["cost_price"],
            "min_stock": row["min_stock"],
            "barcodes": json.loads(row["barcodes"]),
            "stock_qty": str(self.balance(store_id, row["id"])),
        }

    def get_product(self, product_id: str, store_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM products WHERE id = ? AND deleted = 0", (product_id,)
            ).fetchone()
        return None if row is None else self._product_dict(row, store_id)

    def product_by_barcode(self, code: str, store_id: str) -> dict[str, Any] | None:
        with self._lock:
            rows = self._db.execute("SELECT * FROM products WHERE deleted = 0").fetchall()
        for row in rows:
            if code in json.loads(row["barcodes"]):
                return self._product_dict(row, store_id)
        return None

    def search_products(self, query: str, store_id: str, limit: int = 30) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        with self._lock:
            rows = self._db.execute("SELECT * FROM products WHERE deleted = 0 ORDER BY name").fetchall()
        found = [self._product_dict(r, store_id) for r in rows if needle in r["name"].lower()]
        return found[:limit]

    def all_products(self) -> list[dict[str, Any]]:
        """Katalog (o'chirilganlarsiz), ism bo'yicha."""
        with self._lock:
            rows = self._db.execute("SELECT * FROM products WHERE deleted = 0 ORDER BY name").fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "unit": r["unit"],
                "sale_price": r["sale_price"],
                "cost_price": r["cost_price"],
                "min_stock": r["min_stock"],
                "barcodes": json.loads(r["barcodes"]),
            }
            for r in rows
        ]

    def open_shift_for_device(self, device_id: str) -> dict[str, Any] | None:
        """Shu qurilmaning ochiq smenasi (har bir qurilmaning o'z smenasi bor)."""
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM shifts WHERE device = ? AND closed_at IS NULL", (device_id,)
            ).fetchone()
        return None if row is None else dict(row)

    def get_shift(self, shift_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        return None if row is None else dict(row)

    def sales(self, store_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM sales WHERE store_id = ? ORDER BY created_at DESC LIMIT ?", (store_id, limit)
            ).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def get_sale(self, sale_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
        return None if row is None else {**dict(row), "payload": json.loads(row["payload"])}

    def shift_summary(self, shift_id: str) -> dict[str, Any]:
        """Smena yopilganda hisobot: savdolar, qaytarishlar, to'lov turlari bo'yicha summa."""
        with self._lock:
            rows = self._db.execute("SELECT * FROM sales WHERE shift_id = ?", (shift_id,)).fetchall()
        summary: dict[str, Any] = {
            "sales_count": 0,
            "total_sales": 0,
            "refunds_count": 0,
            "total_refunds": 0,
            "by_method": {},
        }
        for row in rows:
            payload = json.loads(row["payload"])
            if row["status"] == "refunded":
                summary["refunds_count"] += 1
                summary["total_refunds"] += int(row["total"])
                continue
            summary["sales_count"] += 1
            summary["total_sales"] += int(row["total"])
            for payment in payload["payments"]:
                method = payment["method"]
                summary["by_method"][method] = summary["by_method"].get(method, 0) + int(payment["amount"])
        return summary

    # --- roster (qurilmalar) va foydalanuvchilar ----------------------------------

    def device_row(self, device_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if row is None:
            return None
        return {**dict(row), "active": bool(row["active"])}

    def list_devices(self, store_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM devices WHERE store_id = ? ORDER BY label, device_id", (store_id,)
            ).fetchall()
        return [{**dict(r), "active": bool(r["active"])} for r in rows]

    def is_owner_device(self, device_id: str) -> bool:
        row = self.device_row(device_id)
        return row is not None and row["active"] and row["role"] == o.ROLE_OWNER

    def verify_join_request(self, op: dict[str, Any]) -> bool:
        """So'rov o'z kaliti bilan imzolanganmi, do'kon shu do'konmi, qurilma hali qo'shilmaganmi."""
        if op.get("type") != o.JOIN_REQUEST or not _well_formed(op):
            return False
        payload = op["payload"]
        public_key = payload.get("public_key")
        if payload.get("device_id") != op["device"] or not isinstance(public_key, str):
            return False
        if op["store_id"] != self.get_state("store_id") or not HEX_KEY.match(public_key):
            return False
        existing = self.device_row(op["device"])
        if existing is not None and existing["active"]:
            return False
        return crypto.verify_op(op, public_key)

    def is_active_device_op(self, op: dict[str, Any]) -> bool:
        """Operatsiya muallifi faol roster qurilmasimi va imzosi to'g'rimi (snapshot_request uchun)."""
        row = self.device_row(op.get("device", ""))
        return row is not None and row["active"] and crypto.verify_op(op, row["public_key"])

    def list_users(self, store_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id, login, name, role, active FROM users WHERE store_id = ? ORDER BY name",
                (store_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def find_user(self, store_id: str, login: str) -> dict[str, Any] | None:
        """Faol foydalanuvchini login bo'yicha topadi (xesh bilan). Login katta-kichik harfga bog'liq emas."""
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM users WHERE store_id = ? AND login = ? AND active = 1 "
                "ORDER BY updated_ts DESC LIMIT 1",
                (store_id, login.strip().lower()),
            ).fetchone()
        return None if row is None else dict(row)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return None if row is None else dict(row)

    def login_exists(self, store_id: str, login: str) -> bool:
        """Login band bo'lsa True (nofaol foydalanuvchilar ham hisobga olinadi)."""
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) AS n FROM users WHERE store_id = ? AND login = ?",
                (store_id, login.strip().lower()),
            ).fetchone()
        return int(row["n"]) > 0

    def store_name(self, store_id: str) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT name FROM store_info WHERE store_id = ?", (store_id,)).fetchone()
        return None if row is None else str(row["name"])

    def snapshot_payload(self, store_id: str) -> dict[str, Any]:
        """Egasi qurilmasi yuboradigan to'liq holat (docs/sync-mqtt.md, 9-bo'lim)."""
        with self._lock:
            info = self._db.execute("SELECT * FROM store_info WHERE store_id = ?", (store_id,)).fetchone()
            devices = self._db.execute("SELECT * FROM devices WHERE store_id = ?", (store_id,)).fetchall()
            users = self._db.execute("SELECT * FROM users WHERE store_id = ?", (store_id,)).fetchall()
            products = self._db.execute("SELECT * FROM products").fetchall()
            balances = self._db.execute(
                "SELECT product_id, qty FROM movements WHERE store_id = ?", (store_id,)
            ).fetchall()
            shifts = self._db.execute(
                "SELECT * FROM shifts WHERE store_id = ? AND closed_at IS NULL", (store_id,)
            ).fetchall()
        totals: dict[str, Decimal] = {}
        for row in balances:
            totals[row["product_id"]] = totals.get(row["product_id"], Decimal(0)) + Decimal(row["qty"])
        return {
            "store": {"name": info["name"], "updated_ts": info["updated_ts"]} if info else None,
            "devices": [
                {
                    "device_id": d["device_id"],
                    "public_key": d["public_key"],
                    "role": d["role"],
                    "label": d["label"],
                    "active": bool(d["active"]),
                    "updated_ts": d["updated_ts"],
                }
                for d in devices
            ],
            "users": [
                {
                    "id": u["id"],
                    "login": u["login"],
                    "name": u["name"],
                    "role": u["role"],
                    "salt": u["salt"],
                    "pw_hash": u["pw_hash"],
                    "active": bool(u["active"]),
                    "updated_ts": u["updated_ts"],
                }
                for u in users
            ],
            "products": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "unit": p["unit"],
                    "sale_price": p["sale_price"],
                    "cost_price": p["cost_price"],
                    "min_stock": p["min_stock"],
                    "barcodes": json.loads(p["barcodes"]),
                    "deleted": bool(p["deleted"]),
                    "updated_ts": p["updated_ts"],
                }
                for p in products
            ],
            "balances": {pid: str(qty) for pid, qty in totals.items() if qty != 0},
            "open_shifts": [
                {
                    "id": s["id"],
                    "device": s["device"],
                    "opening_cash": s["opening_cash"],
                    "opened_at": s["opened_at"],
                }
                for s in shifts
            ],
        }

    # --- qabul qilish: apply_op --------------------------------------------------

    def apply_op(self, op: dict[str, Any]) -> str:
        """Operatsiyani tekshiradi va qo'llaydi. Natija: APPLIED, DUPLICATE, REJECTED, PENDING, SKIPPED."""
        with self._lock:
            result = self._guarded(op)
            self._db.commit()
            return result

    def _guarded(self, op: Any) -> str:
        """Bitta operatsiya SAVEPOINT ichida: xato bo'lsa faqat shu operatsiya bekor qilinadi."""
        self._db.execute("SAVEPOINT op_guard")
        try:
            result = self._process(op)
        except _Invalid as exc:
            self._db.execute("ROLLBACK TO op_guard")
            self._db.execute("RELEASE op_guard")
            log.info("Operatsiya rad etildi (%s): %s", exc, op.get("op_id") if isinstance(op, dict) else "?")
            return REJECTED
        except Exception:
            self._db.execute("ROLLBACK TO op_guard")
            self._db.execute("RELEASE op_guard")
            log.exception("Operatsiya qo'llanmadi")
            return REJECTED
        self._db.execute("RELEASE op_guard")
        return result

    def _process(self, op: Any) -> str:
        if not _well_formed(op) or op["type"] not in o.KNOWN_TYPES:
            return REJECTED
        kind = op["type"]
        if kind in (o.SNAPSHOT_REQUEST, o.JOIN_REQUEST):
            return SKIPPED  # so'rovlar qo'llanmaydi, javobni boshqa qurilma beradi
        if self._applied(op["op_id"]):
            return DUPLICATE
        if op["store_id"] != self.get_state("store_id"):
            return REJECTED
        if not self.is_bootstrapped():
            return self._process_bootstrapping(op)
        if kind not in (o.DEVICE, o.SNAPSHOT) and op["ts"] <= self._bootstrap_ts():
            return SKIPPED  # snapshot ichida (K5): bootstrap vaqtidan oldingi operatsiya
        signer = self.device_row(op["device"])
        if signer is None:
            return self._defer(op)  # muallif hali roster'da yo'q: keyinroq
        if not signer["active"] or not crypto.verify_op(op, signer["public_key"]):
            return REJECTED
        if kind in o.OWNER_ONLY and signer["role"] != o.ROLE_OWNER:
            return REJECTED
        return self._apply(op, signer)

    def _process_bootstrapping(self, op: dict[str, Any]) -> str:
        """Bootstrap oldin: faqat egasi imzosidagi qurilma va snapshot qo'llanadi, qolgani kutadi."""
        kind = op["type"]
        signer = self.device_row(op["device"])
        if (
            signer is not None
            and kind in (o.DEVICE, o.SNAPSHOT)
            and signer["active"]
            and signer["role"] == o.ROLE_OWNER
            and crypto.verify_op(op, signer["public_key"])
        ):
            return self._apply(op, signer)
        return self._defer(op)

    def _apply(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        handlers = {
            o.DEVICE: self._apply_device,
            o.STORE: self._apply_store,
            o.USER: self._apply_user,
            o.PRODUCT: self._apply_product,
            o.MOVEMENT: self._apply_movement,
            o.SALE: self._apply_sale,
            o.REFUND: self._apply_refund,
            o.SHIFT_OPEN: self._apply_shift_open,
            o.SHIFT_CLOSE: self._apply_shift_close,
            o.SNAPSHOT: self._apply_snapshot,
        }
        result = handlers[op["type"]](op, signer)
        if result in (APPLIED, SKIPPED):
            self._mark_applied(op["op_id"])
        if result == PENDING:
            return self._defer(op)
        return result

    # --- dedupe va kutish buferi -------------------------------------------------

    def _applied(self, op_id: str) -> bool:
        return self._db.execute("SELECT 1 FROM applied_ops WHERE op_id = ?", (op_id,)).fetchone() is not None

    def _mark_applied(self, op_id: str) -> None:
        self._db.execute("INSERT OR IGNORE INTO applied_ops (op_id) VALUES (?)", (op_id,))

    def _defer(self, op: dict[str, Any]) -> str:
        count = self._db.execute("SELECT COUNT(*) AS n FROM deferred").fetchone()["n"]
        if count >= MAX_DEFERRED:
            return REJECTED
        self._db.execute(
            "INSERT OR IGNORE INTO deferred (op_id, ts, op) VALUES (?, ?, ?)",
            (op["op_id"], op["ts"], json.dumps(op, ensure_ascii=False)),
        )
        return PENDING

    def _sweep(self) -> None:
        """Kutilayotgan operatsiyalarni qayta tekshiradi (roster yoki katalog o'zgargach)."""
        rows = self._db.execute("SELECT op_id, op FROM deferred ORDER BY ts, op_id").fetchall()
        for row in rows:
            self._db.execute("DELETE FROM deferred WHERE op_id = ?", (row["op_id"],))
            self._guarded(json.loads(row["op"]))

    # --- ko'rinishlar: qo'llash ------------------------------------------------------

    def _apply_device(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        if signer["role"] != o.ROLE_OWNER:
            return REJECTED
        changed = self._put_device(op["store_id"], op["payload"], op["ts"], op["op_id"])
        if self.is_bootstrapped():
            self._sweep()
        return APPLIED if changed else SKIPPED

    def _put_device(self, store_id: str, data: dict[str, Any], ts: str, op_id: str) -> bool:
        device_id = _str(data, "device_id")
        public_key = _str(data, "public_key").lower()
        role = data.get("role")
        active = data.get("active", True)
        label = str(data.get("label", ""))
        if not HEX_KEY.match(public_key) or role not in o.ROLES or not isinstance(active, bool):
            raise _Invalid("device")
        existing = self.device_row(device_id)
        if existing is not None:
            if existing["public_key"] != public_key:
                raise _Invalid("device key")
            if existing["role"] == o.ROLE_OWNER and (role != o.ROLE_OWNER or not active):
                raise _Invalid("owner immutable")
            if (existing["updated_ts"], existing["updated_op"]) >= (ts, op_id):
                return False
        elif role == o.ROLE_OWNER and not active:
            raise _Invalid("owner inactive")
        self._db.execute(
            "INSERT OR REPLACE INTO devices (device_id, store_id, public_key, role, label, active, "
            "updated_ts, updated_op) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (device_id, store_id, public_key, role, label, 1 if active else 0, ts, op_id),
        )
        return True

    def _apply_store(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        return (
            APPLIED
            if self._put_store(op["store_id"], _str(op["payload"], "name"), op["ts"], op["op_id"])
            else SKIPPED
        )

    def _put_store(self, store_id: str, name: str, ts: str, op_id: str) -> bool:
        row = self._db.execute(
            "SELECT updated_ts, updated_op FROM store_info WHERE store_id = ?", (store_id,)
        ).fetchone()
        if row is not None and (row["updated_ts"], row["updated_op"]) >= (ts, op_id):
            return False
        self._db.execute(
            "INSERT INTO store_info (store_id, name, updated_ts, updated_op) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(store_id) DO UPDATE SET name=excluded.name, updated_ts=excluded.updated_ts, "
            "updated_op=excluded.updated_op",
            (store_id, name, ts, op_id),
        )
        return True

    def _apply_user(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        return APPLIED if self._put_user(op["store_id"], op["payload"], op["ts"], op["op_id"]) else SKIPPED

    def _put_user(self, store_id: str, data: dict[str, Any], ts: str, op_id: str) -> bool:
        user_id = _str(data, "id")
        role = data.get("role")
        active = data.get("active", True)
        if role not in o.ROLES or not isinstance(active, bool):
            raise _Invalid("user")
        row = self._db.execute("SELECT updated_ts, updated_op FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is not None and (row["updated_ts"], row["updated_op"]) >= (ts, op_id):
            return False
        self._db.execute(
            "INSERT INTO users (id, store_id, login, name, role, salt, pw_hash, active, "
            "updated_ts, updated_op) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET login=excluded.login, "
            "name=excluded.name, role=excluded.role, salt=excluded.salt, pw_hash=excluded.pw_hash, "
            "active=excluded.active, updated_ts=excluded.updated_ts, updated_op=excluded.updated_op",
            (
                user_id,
                store_id,
                _str(data, "login").strip().lower(),
                _str(data, "name"),
                role,
                _str(data, "salt"),
                _str(data, "pw_hash"),
                1 if active else 0,
                ts,
                op_id,
            ),
        )
        return True

    def _apply_product(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        self._put_product(op["payload"], op["ts"], op["op_id"])
        if self.is_bootstrapped():
            self._sweep()
        return APPLIED

    def _put_product(self, data: dict[str, Any], ts: str, op_id: str) -> bool:
        product_id = _str(data, "id")
        sale_price = _int(data, "sale_price")
        cost_price = _int(data, "cost_price", 0)
        if sale_price < 0 or cost_price < 0:
            raise _Invalid("price")
        min_stock = str(_dec(data.get("min_stock", "0")))
        barcodes = data.get("barcodes", [])
        deleted = data.get("deleted", False)
        if not isinstance(barcodes, list) or not all(isinstance(b, str) for b in barcodes):
            raise _Invalid("barcodes")
        if not isinstance(deleted, bool):
            raise _Invalid("deleted")
        # Narx tarixi: har o'zgarish saqlanadi, sotuv tekshiruvi `ts` vaqtidagi narxni oladi
        self._db.execute(
            "INSERT OR IGNORE INTO product_prices (product_id, ts, op_id, sale_price) VALUES (?, ?, ?, ?)",
            (product_id, ts, op_id, sale_price),
        )
        row = self._db.execute(
            "SELECT updated_ts, updated_op FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if row is not None and (row["updated_ts"], row["updated_op"]) >= (ts, op_id):
            return False
        self._db.execute(
            "INSERT INTO products (id, name, unit, sale_price, cost_price, min_stock, barcodes, deleted, "
            "updated_ts, updated_op) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name, unit=excluded.unit, sale_price=excluded.sale_price, "
            "cost_price=excluded.cost_price, min_stock=excluded.min_stock, barcodes=excluded.barcodes, "
            "deleted=excluded.deleted, updated_ts=excluded.updated_ts, updated_op=excluded.updated_op",
            (
                product_id,
                _str(data, "name"),
                _str(data, "unit"),
                sale_price,
                cost_price,
                min_stock,
                json.dumps(barcodes, ensure_ascii=False),
                1 if deleted else 0,
                ts,
                op_id,
            ),
        )
        return True

    def _apply_movement(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        payload = op["payload"]
        if payload.get("kind") not in o.MOVEMENT_KINDS:
            return REJECTED
        qty = _dec(payload.get("qty"))
        if qty == 0:
            return REJECTED
        self._insert_movement(op["op_id"], op["store_id"], _str(payload, "product_id"), qty, payload["kind"])
        return APPLIED

    def _price_at(self, product_id: str, ts: str) -> int | None:
        row = self._db.execute(
            "SELECT sale_price FROM product_prices WHERE product_id = ? AND ts <= ? "
            "ORDER BY ts DESC, op_id DESC LIMIT 1",
            (product_id, ts),
        ).fetchone()
        return None if row is None else int(row["sale_price"])

    def _check_sale(self, payload: dict[str, Any], ts: str) -> str:
        """Sotuv narxlari katalogga mos (6.1-bo'lim). Katalog kutilsa PENDING, mos bo'lmasa _Invalid."""
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise _Invalid("items")
        subtotal = 0
        for item in items:
            if not isinstance(item, dict):
                raise _Invalid("item")
            product_id = _str(item, "product_id")
            qty = _dec(item.get("qty"))
            if qty <= 0:
                raise _Invalid("qty")
            unit_price = _int(item, "unit_price")
            line_total = _int(item, "line_total")
            price = self._price_at(product_id, ts)
            if price is None:
                return PENDING
            if unit_price != price or line_total != round_som(qty * price):
                raise _Invalid("price mismatch")
            subtotal += line_total
        discount = _int(payload, "discount", 0)
        if _int(payload, "subtotal") != subtotal or not 0 <= discount <= subtotal:
            raise _Invalid("subtotal")
        if _int(payload, "total") != subtotal - discount:
            raise _Invalid("total")
        payments = payload.get("payments", [])
        if not isinstance(payments, list):
            raise _Invalid("payments")
        paid = sum(_int(p, "amount") for p in payments if isinstance(p, dict))
        if paid < subtotal - discount:
            raise _Invalid("payments short")
        return APPLIED

    def _apply_sale(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        payload = op["payload"]
        sale_id = _str(payload, "id")
        if sale_id != op["op_id"]:
            raise _Invalid("sale id")
        verdict = self._check_sale(payload, op["ts"])
        if verdict == PENDING:
            return PENDING
        if self.get_sale(sale_id) is not None:
            return REJECTED
        for item in payload["items"]:
            self._insert_movement(
                f"{op['op_id']}:{item['product_id']}",
                op["store_id"],
                item["product_id"],
                -_dec(item["qty"]),
                "sale",
            )
        status = "refunded" if self._refunded(sale_id) else "completed"
        self._db.execute(
            "INSERT INTO sales (id, store_id, shift_id, number, status, total, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sale_id,
                op["store_id"],
                payload.get("shift_id"),
                str(payload.get("number", "")),
                status,
                int(payload["total"]),
                json.dumps(payload, ensure_ascii=False),
                payload.get("created_at", op["ts"]),
            ),
        )
        return APPLIED

    def _refunded(self, sale_id: str) -> bool:
        return (
            self._db.execute("SELECT 1 FROM refunded_sales WHERE sale_id = ?", (sale_id,)).fetchone()
            is not None
        )

    def _apply_refund(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        sale_id = _str(op["payload"], "sale_id")
        if op["op_id"] != o.refund_op_id(sale_id):
            raise _Invalid("refund id")
        items = _items(op["payload"].get("items"))
        if self._refunded(sale_id):
            return REJECTED
        sale = self.get_sale(sale_id)
        if sale is not None:
            if sale["status"] != "completed":
                return REJECTED
            expected = sorted((str(i["product_id"]), _dec(i["qty"])) for i in sale["payload"]["items"])
            if expected != sorted(items):
                return REJECTED
        for product_id, qty in items:
            self._insert_movement(
                f"refund:{sale_id}:{product_id}", op["store_id"], product_id, qty, "sale_return"
            )
        self._db.execute(
            "INSERT INTO refunded_sales (sale_id, op_id, ts) VALUES (?, ?, ?)",
            (sale_id, op["op_id"], op["ts"]),
        )
        if sale is not None:
            self._db.execute("UPDATE sales SET status = 'refunded' WHERE id = ?", (sale_id,))
        return APPLIED

    def _apply_shift_open(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        payload = op["payload"]
        shift_id = _str(payload, "shift_id")
        if shift_id != op["op_id"]:
            raise _Invalid("shift id")
        opening_cash = _int(payload, "opening_cash")
        if opening_cash < 0:
            raise _Invalid("opening_cash")
        if self.open_shift_for_device(op["device"]) is not None or self.get_shift(shift_id) is not None:
            return REJECTED
        self._db.execute(
            "INSERT INTO shifts (id, store_id, device, opened_at, opening_cash) VALUES (?, ?, ?, ?, ?)",
            (shift_id, op["store_id"], op["device"], op["ts"], opening_cash),
        )
        return APPLIED

    def _apply_shift_close(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        payload = op["payload"]
        shift_id = _str(payload, "shift_id")
        closing_cash = _int(payload, "closing_cash")
        row = self.get_shift(shift_id)
        if row is None:
            return PENDING  # smena ochilishi hali kelmagan
        if row["closed_at"] is not None:
            return REJECTED
        if row["device"] != op["device"] and signer["role"] != o.ROLE_OWNER:
            return REJECTED
        summary = payload.get("summary", {})
        if not isinstance(summary, dict):
            raise _Invalid("summary")
        self._db.execute(
            "UPDATE shifts SET closed_at = ?, closing_cash = ?, summary = ? WHERE id = ?",
            (op["ts"], closing_cash, json.dumps(summary, ensure_ascii=False), shift_id),
        )
        return APPLIED

    def _insert_movement(
        self, movement_id: str, store_id: str, product_id: str, qty: Decimal, kind: str
    ) -> None:
        self._db.execute(
            "INSERT OR IGNORE INTO movements (id, store_id, product_id, qty, kind) VALUES (?, ?, ?, ?, ?)",
            (movement_id, store_id, product_id, str(qty), kind),
        )

    def _apply_snapshot(self, op: dict[str, Any], signer: dict[str, Any]) -> str:
        """Bootstrap: egasi snapshot'i. Faqat bootstrap bo'lmagan qurilmada (K5: jonli op rad ettirmaydi)."""
        if self.is_bootstrapped():
            return REJECTED
        payload = op["payload"]
        store_id = op["store_id"]
        op_id = op["op_id"]
        info = payload.get("store")
        if isinstance(info, dict):
            self._put_store(store_id, _str(info, "name"), str(info.get("updated_ts", "")), op_id)
        for device in payload.get("devices", []):
            self._put_device(store_id, device, str(device.get("updated_ts", "")), op_id)
        for user in payload.get("users", []):
            self._put_user(store_id, user, str(user.get("updated_ts", "")), op_id)
        for product in payload.get("products", []):
            self._put_product(product, str(product.get("updated_ts", "")), op_id)
        for product_id, qty in payload.get("balances", {}).items():
            amount = _dec(qty)
            if amount != 0:
                self._insert_movement(
                    f"snapshot:{op_id}:{product_id}", store_id, product_id, amount, "snapshot"
                )
        for shift in payload.get("open_shifts", []):
            self._db.execute(
                "INSERT OR IGNORE INTO shifts (id, store_id, device, opened_at, opening_cash) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    _str(shift, "id"),
                    store_id,
                    _str(shift, "device"),
                    _str(shift, "opened_at"),
                    _int(shift, "opening_cash"),
                ),
            )
        # commit'siz: operatsiya SAVEPOINT ichida (set_state commit qilardi)
        self._set_state_locked("bootstrapped", "1")
        self._set_state_locked("bootstrap_ts", op["ts"])
        self._sweep()  # bootstrap'dan oldingi kutilayotgan operatsiyalar: ts > T bo'lganlari qo'llanadi
        return APPLIED
