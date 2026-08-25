"""Bazani sxemaga olib kelish — uchta holat ham xavfsiz bo'lishi kerak.

Bu Alembic ulanishi shu sabab bilan qo'shildi: `create_all()` ishlab
chiqarish bazasini boshqarish uchun YETARLI EMAS — u eski bazadagi
ustunlarni yo'qotmasdan yangilay olmaydi. Lekin Alembic o'tishning o'zi
xavfli: agar eski (Alembic'siz) baza ustida boshlang'ich migratsiya
ishga tushirilsa, u `CREATE TABLE` bilan yiqiladi, chunki jadval
allaqachon bor. Shu holat aynan shu yerda sinaladi.
"""

from __future__ import annotations

from distribos.persistence.base import Database, create_database_engine
from distribos.persistence.migrations import ensure_schema
from distribos.persistence.models import Product
from sqlalchemy import inspect, text


def test_bosh_baza_migratsiyalanadi(tmp_path):
    engine = create_database_engine(tmp_path / "distribos.sqlite3")
    ensure_schema(engine)

    inspector = inspect(engine)
    assert inspector.has_table("catalog_product")
    assert inspector.has_table("event_log")
    assert inspector.has_table("alembic_version")


def test_eski_create_all_baza_qayta_yaratilmaydi(tmp_path):
    """`create_all()` bilan yaratilgan baza — ustida `upgrade` emas,
    faqat `stamp` bajarilishi kerak, aks holda CREATE TABLE yiqiladi."""
    path = tmp_path / "distribos.sqlite3"
    database = Database.open(path)
    database.create_all()

    # Sinov ma'lumoti: bu QOLISHI kerak. `ensure_schema` uni
    # o'chirmasligini shu tekshiradi.
    with database.unit_of_work() as session:
        session.add(Product(
            id="p1", sku="SKU-1", name="Sinov mahsuloti", unit="dona",
            wholesale_price=100,
        ))

    ensure_schema(database.engine)   # yiqilmasligi kerak

    with database.session() as session:
        nomi = session.execute(
            text("SELECT name FROM catalog_product WHERE id = 'p1'")
        ).scalar_one()
    assert nomi == "Sinov mahsuloti"

    inspector = inspect(database.engine)
    assert inspector.has_table("alembic_version")


def test_migratsiyalangan_baza_qayta_ishga_tushsa_ozgarmaydi(tmp_path):
    """Ikkinchi marta ishga tushirish idempotent bo'lishi kerak."""
    engine = create_database_engine(tmp_path / "distribos.sqlite3")
    ensure_schema(engine)
    ensure_schema(engine)   # ikkinchi marta — xato bo'lmasligi kerak

    inspector = inspect(engine)
    assert inspector.has_table("catalog_product")


def test_create_all_va_migratsiya_bir_xil_jadval_toplamini_beradi(tmp_path):
    """Ikki yo'l ORQASIDA drift bo'lmasligini tekshiradi.

    Agar kimdir modelga yangi jadval qo'shib, migratsiya yozishni
    unutsa — bu sinov shuni ushlaydi.
    """
    yaratilgan = create_database_engine(tmp_path / "create_all.sqlite3")
    Database(yaratilgan).create_all()
    yaratilgan_jadvallar = {
        t for t in inspect(yaratilgan).get_table_names()
        if t != "alembic_version"
    }

    migratsiyalangan = create_database_engine(tmp_path / "migrated.sqlite3")
    ensure_schema(migratsiyalangan)
    migratsiyalangan_jadvallar = {
        t for t in inspect(migratsiyalangan).get_table_names()
        if t != "alembic_version"
    }

    assert yaratilgan_jadvallar == migratsiyalangan_jadvallar, (
        "model va migratsiya orasida farq bor — yangi jadval/ustun uchun "
        "`alembic revision --autogenerate` bilan migratsiya yozish kerak"
    )
