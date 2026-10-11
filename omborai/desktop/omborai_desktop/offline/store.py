"""Lokal baza (SQLCipher, shifrlangan). Barcha ma'lumot MQTT operatsiyalaridan quriladi (docs/sync-mqtt.md).

Qoidalar:
- Qoldiq = movements yig'indisi. Savdo, qaytarish, tuzatish, snapshot — hammasi movements orqali.
- Tovar: eng so'nggi o'zgarish g'olib (updated_ts bo'yicha, LWW).
- Smena: do'konda bir vaqtda bitta ochiq smena; ikkinchi ochish e'tiborsiz qoldiriladi.
- Qaytarish op_id = refund:<sale_id>: bir chek faqat bir marta qaytariladi (barcha qurilmalarda).
"""

import json
import re
import threading
import uuid
from decimal import Decimal
from typing import Any

from ..sync import ops as o

HEX_KEY = re.compile(r"^[0-9a-f]{64}$")

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
    updated_ts TEXT NOT NULL DEFAULT ''
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
CREATE TABLE IF NOT EXISTS shifts (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    opening_cash INTEGER NOT NULL,
    closed_at TEXT,
    closing_cash INTEGER,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS outbox (
    op_id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    op TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS store_info (
    store_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    updated_ts TEXT NOT NULL DEFAULT ''
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
    updated_ts TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS users_store_login ON users (store_id, login);
CREATE TABLE IF NOT EXISTS applied_ops (op_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS sync_state (name TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


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


class LocalStore:
    def __init__(self, path: str = ":memory:", *, key: str | None = None) -> None:
        if key is not None:
            self._db = _open_encrypted(path, key)
        else:
            import sqlite3

            self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = _dict_row
        self._lock = threading.RLock()
        with self._lock:
            self._db.executescript(SCHEMA)
            self._db.commit()

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

    # --- navbat (ulanmagan paytda yuborilmagan operatsiyalar) ---------------

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

    # --- o'qish -------------------------------------------------------------

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

    def open_shift(self, store_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM shifts WHERE store_id = ? AND closed_at IS NULL", (store_id,)
            ).fetchone()
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

    def applied_count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) AS n FROM applied_ops").fetchone()["n"])

    def snapshot_payload(self, store_id: str) -> dict[str, Any]:
        """Yangi qurilmaga uzatiladigan holat: katalog, qoldiqlar, ochiq smena."""
        with self._lock:
            products = self._db.execute("SELECT * FROM products").fetchall()
            balances = self._db.execute(
                "SELECT product_id, qty FROM movements WHERE store_id = ?", (store_id,)
            ).fetchall()
            open_shift = self._db.execute(
                "SELECT * FROM shifts WHERE store_id = ? AND closed_at IS NULL", (store_id,)
            ).fetchone()
            info = self._db.execute("SELECT * FROM store_info WHERE store_id = ?", (store_id,)).fetchone()
            users = self._db.execute("SELECT * FROM users WHERE store_id = ?", (store_id,)).fetchall()
        totals: dict[str, Decimal] = {}
        for row in balances:
            totals[row["product_id"]] = totals.get(row["product_id"], Decimal(0)) + Decimal(row["qty"])
        return {
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
            "open_shift": dict(open_shift) if open_shift else None,
            "store": {"name": info["name"], "updated_ts": info["updated_ts"]} if info else None,
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
        }

    # --- qo'llash (barcha operatsiya turlari) -------------------------------

    def apply_op(self, op: dict[str, Any]) -> bool:
        """Operatsiyani bir marta qo'llaydi. Yangi bo'lsa True; dublikat yoki e'tiborsiz bo'lsa False.

        Dedupe va qo'llash bitta tranzaksiyada: yarim qo'llangan operatsiya bo'lmaydi.
        """
        kind = op["type"]
        if kind == o.SNAPSHOT_REQUEST:
            return False  # ma'lumot emas, javob talab qiladi
        with self._lock:
            try:
                if kind == o.SNAPSHOT and self.applied_count() > 0:
                    return False  # snapshot faqat bo'sh (yangi) qurilmaga
                inserted = self._db.execute(
                    "INSERT OR IGNORE INTO applied_ops (op_id) VALUES (?)", (op["op_id"],)
                )
                if inserted.rowcount == 0:
                    self._db.commit()
                    return False
                handler = self._handlers.get(kind)
                if handler is None:
                    raise ValueError(f"Noma'lum operatsiya turi: {kind}")
                handler(self, op)
                self._db.commit()
                return True
            except Exception:
                self._db.rollback()
                raise

    def _apply_sale(self, op: dict[str, Any]) -> None:
        payload = op["payload"]
        for item in payload["items"]:
            self._insert_movement(
                f"{op['op_id']}:{item['product_id']}",
                op["store_id"],
                item["product_id"],
                -Decimal(str(item["qty"])),
                "sale",
            )
        self._db.execute(
            "INSERT OR IGNORE INTO sales "
            "(id, store_id, shift_id, number, status, total, payload, created_at) "
            "VALUES (?, ?, ?, ?, 'completed', ?, ?, ?)",
            (
                payload["id"],
                op["store_id"],
                payload.get("shift_id"),
                str(payload["number"]),
                int(payload["total"]),
                json.dumps(payload, ensure_ascii=False),
                payload["created_at"],
            ),
        )

    def _apply_refund(self, op: dict[str, Any]) -> None:
        sale_id = op["payload"]["sale_id"]
        row = self._db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
        if row is None or row["status"] != "completed":
            return
        for item in json.loads(row["payload"])["items"]:
            self._insert_movement(
                f"refund:{sale_id}:{item['product_id']}",
                op["store_id"],
                item["product_id"],
                Decimal(str(item["qty"])),
                "sale_return",
            )
        self._db.execute("UPDATE sales SET status = 'refunded' WHERE id = ?", (sale_id,))

    def _apply_shift_open(self, op: dict[str, Any]) -> None:
        payload = op["payload"]
        if self.open_shift(op["store_id"]) is not None:
            return  # do'konda ochiq smena bor: ikkinchisi e'tiborsiz
        self._db.execute(
            "INSERT OR IGNORE INTO shifts (id, store_id, opened_at, opening_cash) VALUES (?, ?, ?, ?)",
            (payload["shift_id"], op["store_id"], op["ts"], int(payload["opening_cash"])),
        )

    def _apply_shift_close(self, op: dict[str, Any]) -> None:
        payload = op["payload"]
        self._db.execute(
            "UPDATE shifts SET closed_at = ?, closing_cash = ?, summary = ? WHERE id = ? AND closed_at IS "
            "NULL",
            (
                op["ts"],
                int(payload["closing_cash"]),
                json.dumps(payload.get("summary", {})),
                payload["shift_id"],
            ),
        )

    def _apply_movement(self, op: dict[str, Any]) -> None:
        payload = op["payload"]
        self._insert_movement(
            op["op_id"], op["store_id"], payload["product_id"], Decimal(str(payload["qty"])), payload["kind"]
        )

    def _apply_product(self, op: dict[str, Any]) -> None:
        self._upsert_product(op["payload"], op["ts"])

    def _apply_store(self, op: dict[str, Any]) -> None:
        self._upsert_store(op["store_id"], op["payload"]["name"], op["ts"])

    def _apply_user(self, op: dict[str, Any]) -> None:
        self._upsert_user(op["store_id"], op["payload"], op["ts"])

    def _upsert_store(self, store_id: str, name: str, ts: str) -> None:
        row = self._db.execute("SELECT updated_ts FROM store_info WHERE store_id = ?", (store_id,)).fetchone()
        if row is not None and row["updated_ts"] >= ts:
            return
        self._db.execute(
            "INSERT INTO store_info (store_id, name, updated_ts) VALUES (?, ?, ?) "
            "ON CONFLICT(store_id) DO UPDATE SET name=excluded.name, updated_ts=excluded.updated_ts",
            (store_id, name, ts),
        )

    def _upsert_user(self, store_id: str, user: dict[str, Any], ts: str) -> None:
        """Foydalanuvchi: eng so'nggi o'zgarish g'olib (LWW), xuddi tovar kabi."""
        row = self._db.execute("SELECT updated_ts FROM users WHERE id = ?", (user["id"],)).fetchone()
        if row is not None and row["updated_ts"] >= ts:
            return
        self._db.execute(
            "INSERT INTO users (id, store_id, login, name, role, salt, pw_hash, active, updated_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET login=excluded.login, "
            "name=excluded.name, role=excluded.role, salt=excluded.salt, pw_hash=excluded.pw_hash, "
            "active=excluded.active, updated_ts=excluded.updated_ts",
            (
                user["id"],
                store_id,
                user["login"],
                user["name"],
                user["role"],
                user["salt"],
                user["pw_hash"],
                1 if user.get("active", True) else 0,
                ts,
            ),
        )

    def store_name(self, store_id: str) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT name FROM store_info WHERE store_id = ?", (store_id,)).fetchone()
        return None if row is None else str(row["name"])

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

    def list_users(self, store_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id, login, name, role, active FROM users WHERE store_id = ? ORDER BY name",
                (store_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def _apply_snapshot(self, op: dict[str, Any]) -> None:
        payload = op["payload"]
        if payload.get("store"):
            self._upsert_store(op["store_id"], payload["store"]["name"], payload["store"]["updated_ts"])
        for user in payload.get("users", []):
            self._upsert_user(op["store_id"], user, user["updated_ts"])
        for product in payload["products"]:
            self._upsert_product(product, product["updated_ts"])
        for product_id, qty in payload["balances"].items():
            self._insert_movement(
                f"snapshot:{op['op_id']}:{product_id}", op["store_id"], product_id, Decimal(qty), "snapshot"
            )
        if payload.get("open_shift"):
            shift = payload["open_shift"]
            self._db.execute(
                "INSERT OR IGNORE INTO shifts (id, store_id, opened_at, opening_cash) VALUES (?, ?, ?, ?)",
                (shift["id"], op["store_id"], shift["opened_at"], int(shift["opening_cash"])),
            )

    def _upsert_product(self, product: dict[str, Any], ts: str) -> None:
        """Eng so'nggi o'zgarish g'olib: eski ts'li operatsiya yangisini o'chirmaydi."""
        row = self._db.execute("SELECT updated_ts FROM products WHERE id = ?", (product["id"],)).fetchone()
        if row is not None and row["updated_ts"] >= ts:
            return
        self._db.execute(
            "INSERT INTO products (id, name, unit, sale_price, cost_price, min_stock, barcodes, deleted, "
            "updated_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
            "unit=excluded.unit, sale_price=excluded.sale_price, cost_price=excluded.cost_price, "
            "min_stock=excluded.min_stock, barcodes=excluded.barcodes, deleted=excluded.deleted, "
            "updated_ts=excluded.updated_ts",
            (
                product["id"],
                product["name"],
                product["unit"],
                int(product["sale_price"]),
                int(product.get("cost_price", 0)),
                str(product.get("min_stock", "0")),
                json.dumps(product.get("barcodes", []), ensure_ascii=False),
                1 if product.get("deleted") else 0,
                ts,
            ),
        )

    def _insert_movement(
        self, movement_id: str, store_id: str, product_id: str, qty: Decimal, kind: str
    ) -> None:
        self._db.execute(
            "INSERT OR IGNORE INTO movements (id, store_id, product_id, qty, kind) VALUES (?, ?, ?, ?, ?)",
            (movement_id, store_id, product_id, str(qty), kind),
        )

    _handlers = {
        o.SALE: _apply_sale,
        o.REFUND: _apply_refund,
        o.SHIFT_OPEN: _apply_shift_open,
        o.SHIFT_CLOSE: _apply_shift_close,
        o.MOVEMENT: _apply_movement,
        o.PRODUCT: _apply_product,
        o.USER: _apply_user,
        o.STORE: _apply_store,
        o.SNAPSHOT: _apply_snapshot,
    }
