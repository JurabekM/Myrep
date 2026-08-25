"""Boshqa kompaniyaning ma'lumot faylini ochish RAD ETILADI.

Bu sinov haqiqiy nosozlikdan keyin yozildi: eski `data` papkasi saqlanib,
kalitlar yangilanganda dastur tushunarsiz `IntegrityError` bilan yiqilardi.
Endi u aniq xabar beradi va faylga TEGMAYDI.
"""

from __future__ import annotations

import os

import pytest
from distribos.app_context import ForeignDatabaseError, _guard_tenant
from distribos.persistence.base import Database
from distribos.persistence.models.sync import EpochKeyRecord


def _database(tmp_path):
    database = Database.open(tmp_path / "distribos.sqlite3")
    database.create_all()
    return database


def _seed_tenant(database: Database, tenant_id: bytes) -> None:
    with database.unit_of_work() as session:
        session.add(EpochKeyRecord(
            epoch=1, key_id=1, tenant_id=tenant_id,
            root_secret_wrapped=b"x" * 32, profile_id=1, is_current=True,
        ))


def test_bosh_baza_ochiladi(tmp_path):
    """Yangi (bo'sh) fayl — hech qanday to'siq yo'q."""
    database = _database(tmp_path)
    _guard_tenant(database, os.urandom(16))   # xato bo'lmasligi kerak


def test_oz_bazasi_ochiladi(tmp_path):
    tenant = os.urandom(16)
    database = _database(tmp_path)
    _seed_tenant(database, tenant)
    _guard_tenant(database, tenant)


def test_begona_baza_rad_etiladi(tmp_path):
    database = _database(tmp_path)
    _seed_tenant(database, os.urandom(16))

    with pytest.raises(ForeignDatabaseError) as caught:
        _guard_tenant(database, os.urandom(16))

    xabar = str(caught.value)
    assert "boshqa kompaniyaga tegishli" in xabar
    # Foydalanuvchiga texnik atama emas, YECHIM ko'rsatilsin.
    assert "Yechim" in xabar
    assert "tenant" not in xabar.lower()


def test_begona_baza_ozgartirilmaydi(tmp_path):
    """Rad etish faylga yozmasligi kerak — ma'lumot buzilmasin."""
    tenant = os.urandom(16)
    database = _database(tmp_path)
    _seed_tenant(database, tenant)

    with pytest.raises(ForeignDatabaseError):
        _guard_tenant(database, os.urandom(16))

    with database.session() as session:
        rows = session.query(EpochKeyRecord).all()
    assert len(rows) == 1
    assert bytes(rows[0].tenant_id) == tenant
