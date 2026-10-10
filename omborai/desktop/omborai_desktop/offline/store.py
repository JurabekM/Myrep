"""Mahalliy SQLite: tovar keshi, qoldiq harakatlari nusxasi, sinxronizatsiya holati va outbox navbati.

Qoldiq = serverdan kelgan harakatlar yig'indisi - hali yuborilmagan savdolar. Shu tariqa internet
bo'lmasa ham kassir qoldiqni ko'radi, lekin bu server bilan kelishilmagan taxminiy raqam.
"""

import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    sale_price INTEGER NOT NULL,
    barcodes TEXT NOT NULL DEFAULT '[]',
    deleted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS movements (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    qty TEXT NOT NULL,
    kind TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS movements_store_product ON movements (store_id, product_id);
CREATE TABLE IF NOT EXISTS outbox (
    op_id TEXT PRIMARY KEY,
    op_type TEXT NOT NULL,
    store_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error_title TEXT,
    error_detail TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_state (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS applied_ops (op_id TEXT PRIMARY KEY);
"""


def _dict_row(cursor, row):  # type: ignore[no-untyped-def]
    """sqlite3 va sqlcipher3 uchun bir xil qator shakli (lug'at)."""
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


HEX_KEY = re.compile(r"^[0-9a-f]{64}$")


def _open_encrypted(path: str, key: str):  # type: ignore[no-untyped-def]
    """SQLCipher ochiladi. key: 64 belgili hex (32 bayt). Faqat shu shakl qabul qilinadi."""
    import sqlcipher3

    if not HEX_KEY.match(key):
        raise ValueError("Baza kaliti 64 belgili hex bo'lishi kerak")
    db = sqlcipher3.connect(path, check_same_thread=False)
    db.execute(f"PRAGMA key = \"x'{key}'\"")
    # Noto'g'ri kalitda bu yerda DatabaseError ko'tariladi
    db.execute("SELECT count(*) FROM sqlite_master").fetchone()
    return db


@dataclass(frozen=True)
class PendingOp:
    op_id: str
    op_type: str
    store_id: str
    payload: dict[str, Any]


class LocalStore:
    def __init__(self, path: str = ":memory:", *, key: str | None = None) -> None:
        """key berilsa, baza SQLCipher (AES-256) bilan shifrlanadi. Kalitsiz fayl o'qilmaydi."""
        if key is not None:
            self._db = _open_encrypted(path, key)
        else:
            self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = _dict_row
        self._lock = threading.RLock()
        with self._lock:
            self._db.executescript(SCHEMA)
            self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # --- tovarlar keshi ----------------------------------------------------

    def upsert_products(self, products: list[dict[str, Any]]) -> None:
        with self._lock:
            self._db.executemany(
                "INSERT INTO products (id, name, unit, sale_price, barcodes, deleted) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, unit=excluded.unit, "
                "sale_price=excluded.sale_price, barcodes=excluded.barcodes, "
                "deleted=excluded.deleted",
                [
                    (
                        p["id"],
                        p["name"],
                        p["unit"],
                        int(p["sale_price"]),
                        json.dumps(p.get("barcodes", []), ensure_ascii=False),
                        1 if p.get("deleted") else 0,
                    )
                    for p in products
                ],
            )
            self._db.commit()

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

    def _product_dict(self, row: dict[str, Any], store_id: str) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "unit": row["unit"],
            "sale_price": row["sale_price"],
            "barcodes": json.loads(row["barcodes"]),
            "stock_qty": str(self.balance(store_id, row["id"])),
        }

    # --- qoldiq -------------------------------------------------------------

    def balance(self, store_id: str, product_id: str) -> Decimal:
        with self._lock:
            rows = self._db.execute(
                "SELECT qty FROM movements WHERE store_id = ? AND product_id = ?", (store_id, product_id)
            ).fetchall()
        confirmed = sum((Decimal(r["qty"]) for r in rows), Decimal(0))
        return confirmed - self._pending_sold(store_id, product_id)

    def _pending_sold(self, store_id: str, product_id: str) -> Decimal:
        """Hali serverdan qaytmagan savdolar: navbatda (pending) va serverda qo'llangan (applied)."""
        with self._lock:
            rows = self._db.execute(
                "SELECT payload FROM outbox WHERE op_type = 'sale' AND store_id = ? "
                "AND status IN ('pending', 'applied')",
                (store_id,),
            ).fetchall()
        total = Decimal(0)
        for row in rows:
            for item in json.loads(row["payload"])["items"]:
                if item["product_id"] == product_id:
                    total += Decimal(str(item["qty"]))
        return total

    # --- outbox ----------------------------------------------------------------

    def enqueue_sale(self, store_id: str, payload: dict[str, Any], created_at: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO outbox (op_id, op_type, store_id, payload, created_at) "
                "VALUES (?, 'sale', ?, ?, ?)",
                (payload["id"], store_id, json.dumps(payload, ensure_ascii=False), created_at),
            )
            self._db.commit()

    def pending_ops(self, limit: int = 100, store_id: str | None = None) -> list[PendingOp]:
        sql = "SELECT * FROM outbox WHERE status = 'pending'"
        args: list[Any] = []
        if store_id is not None:
            sql += " AND store_id = ?"
            args.append(store_id)
        sql += " ORDER BY created_at, op_id LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [PendingOp(r["op_id"], r["op_type"], r["store_id"], json.loads(r["payload"])) for r in rows]

    def pending_count(self) -> int:
        with self._lock:
            row = self._db.execute("SELECT COUNT(*) AS n FROM outbox WHERE status = 'pending'").fetchone()
            return int(row["n"])

    def rejected_ops(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM outbox WHERE status = 'rejected' ORDER BY created_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def drop_outbox(self, op_id: str) -> None:
        """MQTT orqali yuborilib, qo'llangan navbat yozuvini o'chiradi (qoldiq endi movements'da)."""
        with self._lock:
            self._db.execute("DELETE FROM outbox WHERE op_id = ?", (op_id,))
            self._db.commit()

    def device_id(self) -> str:
        """Qurilmaning doimiy id'si (birinchi ishga tushirishda yaratiladi)."""
        import uuid

        with self._lock:
            row = self._db.execute("SELECT value FROM sync_state WHERE name = 'device_id'").fetchone()
            if row:
                return str(row["value"])
            value = str(uuid.uuid4())
            self._db.execute("INSERT INTO sync_state (name, value) VALUES ('device_id', ?)", (value,))
            self._db.commit()
            return value

    def next_receipt_number(self) -> int:
        """Qurilma bo'yicha chek raqami. Atomik: bir vaqtda ikki chek bir raqam olmaydi."""
        with self._lock:
            row = self._db.execute("SELECT value FROM sync_state WHERE name = 'receipt_seq'").fetchone()
            number = int(row["value"]) + 1 if row else 1
            self._db.execute(
                "INSERT INTO sync_state (name, value) VALUES ('receipt_seq', ?) "
                "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                (str(number),),
            )
            self._db.commit()
            return number

    def acknowledge_rejected(self, op_id: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM outbox WHERE op_id = ? AND status = 'rejected'", (op_id,))
            self._db.commit()

    def apply_push_results(self, results: list[dict[str, Any]]) -> None:
        with self._lock:
            for result in results:
                if result["status"] == "applied":
                    # Qoldiq harakati pull orqali kelgandan keyin o'chiriladi (apply_pull)
                    self._db.execute(
                        "UPDATE outbox SET status = 'applied' WHERE op_id = ? AND status = 'pending'",
                        (result["op_id"],),
                    )
                else:
                    self._db.execute(
                        "UPDATE outbox SET status = 'rejected', error_title = ?, error_detail = ? "
                        "WHERE op_id = ?",
                        (result.get("error_title"), result.get("error_detail"), result["op_id"]),
                    )
            self._db.commit()

    # --- MQTT operatsiyalari (docs/sync-mqtt.md) ----------------------------

    def apply_op(self, op: dict[str, Any]) -> bool:
        """Operatsiyani bir marta qo'llaydi. Qaytaradi: yangi bo'lsa True, dublikat bo'lsa False.

        Dedupe va qo'llash bitta tranzaksiyada: yarim qo'llangan operatsiya bo'lmaydi.
        """
        op_id = op["op_id"]
        store_id = op["store_id"]
        payload = op["payload"]
        with self._lock:
            try:
                inserted = self._db.execute("INSERT OR IGNORE INTO applied_ops (op_id) VALUES (?)", (op_id,))
                if inserted.rowcount == 0:
                    self._db.commit()
                    return False
                kind = op["type"]
                if kind in ("sale", "refund"):
                    sign = -1 if kind == "sale" else 1
                    movement_kind = "sale" if kind == "sale" else "sale_return"
                    for item in payload["items"]:
                        self._insert_movement(
                            f"{op_id}:{item['product_id']}",
                            store_id,
                            item["product_id"],
                            sign * Decimal(str(item["qty"])),
                            movement_kind,
                        )
                elif kind == "movement":
                    self._insert_movement(
                        op_id, store_id, payload["product_id"], Decimal(str(payload["qty"])), payload["kind"]
                    )
                elif kind == "product":
                    self._db.execute(
                        "INSERT INTO products (id, name, unit, sale_price, barcodes, deleted) "
                        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
                        "unit=excluded.unit, sale_price=excluded.sale_price, barcodes=excluded.barcodes, "
                        "deleted=excluded.deleted",
                        (
                            payload["id"],
                            payload["name"],
                            payload["unit"],
                            int(payload["sale_price"]),
                            json.dumps(payload.get("barcodes", []), ensure_ascii=False),
                            1 if payload.get("deleted") else 0,
                        ),
                    )
                else:
                    raise ValueError(f"Noma'lum operatsiya turi: {kind}")
                self._db.commit()
                return True
            except Exception:
                self._db.rollback()
                raise

    def _insert_movement(
        self, movement_id: str, store_id: str, product_id: str, qty: Decimal, kind: str
    ) -> None:
        self._db.execute(
            "INSERT OR IGNORE INTO movements (id, store_id, product_id, qty, kind) VALUES (?, ?, ?, ?, ?)",
            (movement_id, store_id, product_id, str(qty), kind),
        )

    # --- sinxronizatsiya holati ---------------------------------------------

    def cursors(self) -> dict[str, str]:
        with self._lock:
            rows = self._db.execute("SELECT name, value FROM sync_state").fetchall()
        return {r["name"]: r["value"] for r in rows}

    def apply_pull(self, page: dict[str, Any]) -> None:
        self.upsert_products(page["products"])
        with self._lock:
            self._db.executemany(
                "INSERT OR IGNORE INTO movements (id, store_id, product_id, qty, kind) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (m["id"], m["store_id"], m["product_id"], str(m["qty"]), m["kind"])
                    for m in page["movements"]
                ],
            )
            # Serverdan qaytgan savdo harakatlari — mahalliy 'applied' yozuvlar endi keraksiz
            sale_refs = [m["reference_id"] for m in page["movements"] if m.get("reference_id")]
            self._db.executemany(
                "DELETE FROM outbox WHERE op_id = ? AND status = 'applied'",
                [(ref,) for ref in sale_refs],
            )
            self._db.executemany(
                "INSERT INTO sync_state (name, value) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                list(page["cursors"].items()),
            )
            self._db.commit()
