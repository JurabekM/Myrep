"""Zaxira nusxa va tiklash.

Server yo'q — shuning uchun backup **majburiy biznes funksiyasi**, qulaylik
emas. Agar barcha qurilmalar yo'qolsa va tashqi nusxa bo'lmasa, ochiq MQTT
broker ma'lumotni tiklash manbai HISOBLANMAYDI (ADR-0003).

Nusxa shifrlanadi: unda butun korxonaning mijozlari, narxlari va moliyaviy
tarixi bor. Kalit foydalanuvchi parolidan chiqariladi (scrypt), ya'ni
nusxani boshqa kompyuterda ham ochish mumkin — DPAPI'ga bog'lab qo'yilsa,
kompyuter buzilganda nusxa ham yaroqsiz bo'lardi.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from distribos.persistence.base import Database

MAGIC = b"DBOSBAK1"
#: scrypt parametrlari — interaktiv foydalanish uchun (~100 ms).
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**15, 8, 1


class BackupError(RuntimeError):
    """Nusxa yaratib yoki tiklab bo'lmadi."""


@dataclass(frozen=True, slots=True)
class BackupInfo:
    path: Path
    created_at: dt.datetime
    size_bytes: int
    database_sha256: str
    app_version: str
    schema_version: int

    @property
    def human_size(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


def _derive_key(password: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    kdf = Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return kdf.derive(password.encode("utf-8"))


def create_backup(
    database: Database, destination: Path, password: str, *, app_version: str = "0.1.0"
) -> BackupInfo:
    """Shifrlangan zaxira nusxa yaratadi.

    SQLite `backup` API ishlatiladi — ilova ishlab turganda ham
    **izchil** (consistent) nusxa oladi. Faylni oddiy `copy` qilish WAL
    tufayli yarim tranzaksiyani ushlab qolishi mumkin.
    """
    if len(password) < 8:
        raise BackupError("Parol kamida 8 belgidan iborat bo'lishi kerak")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # WAL ni asosiy faylga yozamiz, keyin izchil nusxa olamiz.
    database.checkpoint_wal()

    with tempfile.TemporaryDirectory() as workdir:
        staging = Path(workdir) / "snapshot.sqlite3"
        source_path = database.engine.url.database
        if not source_path or source_path == ":memory:":
            raise BackupError("Xotiradagi bazadan zaxira nusxa olinmaydi")

        source = sqlite3.connect(source_path)
        target = sqlite3.connect(staging)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        plaintext = staging.read_bytes()

    digest = hashlib.sha256(plaintext).hexdigest()
    created = dt.datetime.now(dt.UTC)
    metadata = {
        "created_at": created.isoformat(),
        "app_version": app_version,
        "schema_version": 1,
        "database_sha256": digest,
        "aether_protocol": "5.1",
    }
    header = json.dumps(metadata, ensure_ascii=False).encode("utf-8")

    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(password, salt)
    # Metama'lumot AAD sifatida autentifikatsiyalanadi — uni o'zgartirib
    # bo'lmaydi.
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext, header)

    with destination.open("wb") as handle:
        handle.write(MAGIC)
        handle.write(len(header).to_bytes(4, "big"))
        handle.write(header)
        handle.write(salt)
        handle.write(nonce)
        handle.write(ciphertext)

    return BackupInfo(
        path=destination, created_at=created, size_bytes=destination.stat().st_size,
        database_sha256=digest, app_version=app_version, schema_version=1,
    )


def read_backup_metadata(path: Path) -> dict:
    """Nusxa metama'lumotini parolsiz o'qiydi (ro'yxat ko'rsatish uchun)."""
    path = Path(path)
    with path.open("rb") as handle:
        if handle.read(len(MAGIC)) != MAGIC:
            raise BackupError("Bu DistribOS zaxira nusxasi emas")
        header_length = int.from_bytes(handle.read(4), "big")
        if not 0 < header_length < 65536:
            raise BackupError("Zaxira nusxa sarlavhasi buzilgan")
        return json.loads(handle.read(header_length).decode("utf-8"))


def verify_backup(path: Path, password: str) -> BackupInfo:
    """Nusxani ochib, yaxlitligini TEKSHIRADI (tiklamasdan).

    «Nusxa bor» degani «nusxa ishlaydi» degani emas — shuning uchun bu
    funksiya alohida turadi va UI uni muntazam taklif qiladi.
    """
    plaintext, metadata = _decrypt(Path(path), password)

    if hashlib.sha256(plaintext).hexdigest() != metadata["database_sha256"]:
        raise BackupError("Zaxira nusxa buzilgan (nazorat yig'indisi mos emas)")

    # Bazani ochib, SQLite darajasida ham tekshiramiz.
    with tempfile.TemporaryDirectory() as workdir:
        staging = Path(workdir) / "verify.sqlite3"
        staging.write_bytes(plaintext)
        connection = sqlite3.connect(staging)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise BackupError(f"Baza yaxlitligi buzilgan: {result}")
            tables = connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            if tables < 10:
                raise BackupError(f"Bazada kutilganidan kam jadval bor ({tables})")
        finally:
            connection.close()

    return BackupInfo(
        path=Path(path),
        created_at=dt.datetime.fromisoformat(metadata["created_at"]),
        size_bytes=Path(path).stat().st_size,
        database_sha256=metadata["database_sha256"],
        app_version=metadata.get("app_version", "?"),
        schema_version=int(metadata.get("schema_version", 1)),
    )


def restore_backup(path: Path, password: str, target_database_path: Path) -> BackupInfo:
    """Nusxani tiklaydi.

    Mavjud baza ustidan yozilmaydi — avval `.replaced-<vaqt>` nomi bilan
    chetga olinadi. Tiklash noto'g'ri ketsa, eski holatga qaytish mumkin
    bo'lishi kerak.
    """
    info = verify_backup(path, password)
    plaintext, _ = _decrypt(Path(path), password)

    target = Path(target_database_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
        target.rename(target.with_suffix(f".replaced-{stamp}"))
    # WAL/SHM qoldiqlari yangi baza bilan aralashmasin.
    for suffix in ("-wal", "-shm"):
        stale = Path(str(target) + suffix)
        if stale.exists():
            stale.unlink()

    target.write_bytes(plaintext)
    return info


def _decrypt(path: Path, password: str) -> tuple[bytes, dict]:
    with path.open("rb") as handle:
        if handle.read(len(MAGIC)) != MAGIC:
            raise BackupError("Bu DistribOS zaxira nusxasi emas")
        header_length = int.from_bytes(handle.read(4), "big")
        header = handle.read(header_length)
        salt = handle.read(16)
        nonce = handle.read(12)
        ciphertext = handle.read()

    if len(salt) != 16 or len(nonce) != 12 or not ciphertext:
        raise BackupError("Zaxira nusxa to'liq emas")

    key = _derive_key(password, salt)
    try:
        plaintext = ChaCha20Poly1305(key).decrypt(nonce, ciphertext, header)
    except Exception as exc:
        raise BackupError(
            "Nusxa ochilmadi. Parol noto'g'ri yoki fayl buzilgan."
        ) from exc

    return plaintext, json.loads(header.decode("utf-8"))


def list_backups(directory: Path) -> list[BackupInfo]:
    """Papkadagi nusxalar ro'yxati (parolsiz, metama'lumot bo'yicha)."""
    directory = Path(directory)
    if not directory.exists():
        return []

    results: list[BackupInfo] = []
    for path in sorted(directory.glob("*.dbak"), reverse=True):
        try:
            metadata = read_backup_metadata(path)
            results.append(BackupInfo(
                path=path,
                created_at=dt.datetime.fromisoformat(metadata["created_at"]),
                size_bytes=path.stat().st_size,
                database_sha256=metadata["database_sha256"],
                app_version=metadata.get("app_version", "?"),
                schema_version=int(metadata.get("schema_version", 1)),
            ))
        except (BackupError, KeyError, ValueError, OSError):
            continue   # buzuq fayl ro'yxatni yiqitmasin
    return results


def prune_backups(directory: Path, keep: int = 10) -> int:
    """Eski nusxalarni tozalaydi. Necha tasi o'chirilgani qaytariladi."""
    backups = list_backups(directory)
    removed = 0
    for info in backups[keep:]:
        try:
            info.path.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def default_backup_name(prefix: str = "distribos") -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}.dbak"
