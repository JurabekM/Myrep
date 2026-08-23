"""`PRODUCT_UPDATED` hodisasi qo'llanishi.

Bu sinov `ruff` topgan xatodan keyin yozildi: `_apply_product_updated`
aniqlanmagan `versions` o'zgaruvchisidan foydalanardi, ya'ni mahsulotni
tahrirlash har doim `NameError` bilan yiqilardi. Hech bir sinov
mahsulotni TAHRIRLAMAGANI uchun bu ko'rinmay qolgan.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribos.domain.ids import uuid7_str
from distribos.sync.event_store import NewEvent
from harness import shared_tenant_setup


@pytest.fixture
def nod():
    _bus, _tenant, (desktop, _phone) = shared_tenant_setup("desktop-1", "android-1")
    return desktop


def _yarat(nod) -> str:
    product_id = uuid7_str()
    with nod.database.unit_of_work() as session:
        nod.command.submit(session, NewEvent(
            "PRODUCT_CREATED", "Product", product_id,
            {"product_id": product_id, "sku": "COLA-1L", "name": "Cola 1 L",
             "unit": "dona", "wholesale_price": 1_500_000},
        ))
    return product_id


def _tahrirla(nod, product_id: str, nom: str) -> None:
    with nod.database.unit_of_work() as session:
        nod.command.submit(session, NewEvent(
            "PRODUCT_UPDATED", "Product", product_id,
            {"product_id": product_id, "changes": {"name": nom}},
        ))


def test_tahrir_qollanadi(nod):
    from distribos.persistence.models import Product

    product_id = _yarat(nod)
    _tahrirla(nod, product_id, "Cola 1 L yangi")

    with nod.database.session() as session:
        assert session.get(Product, product_id).name == "Cola 1 L yangi"


def test_maydon_tamgasi_yoziladi(nod):
    """Konflikt hal qilish uchun maydon tamg'asi saqlansin."""
    from distribos.persistence.models import Product

    product_id = _yarat(nod)
    _tahrirla(nod, product_id, "Yangi nom")

    with nod.database.session() as session:
        versions = json.loads(session.get(Product, product_id).field_versions or "{}")
    assert "name" in versions, "maydon tamg'asi yozilmadi"


def test_ketma_ket_tahrirlar_oxirgisini_qoldiradi(nod):
    from distribos.persistence.models import Product

    product_id = _yarat(nod)
    _tahrirla(nod, product_id, "Ikkinchi")
    _tahrirla(nod, product_id, "Uchinchi")

    with nod.database.session() as session:
        assert session.get(Product, product_id).name == "Uchinchi"


def test_notanish_maydon_etiborsiz_qoldiriladi(nod):
    """Begona maydon dasturni yiqitmasin."""
    from distribos.persistence.models import Product

    product_id = _yarat(nod)
    with nod.database.unit_of_work() as session:
        nod.command.submit(session, NewEvent(
            "PRODUCT_UPDATED", "Product", product_id,
            {"product_id": product_id,
             "changes": {"name": "Nom", "yoq_maydon": "qiymat"}},
        ))

    with nod.database.session() as session:
        assert session.get(Product, product_id).name == "Nom"
