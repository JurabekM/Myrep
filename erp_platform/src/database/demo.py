# -*- coding: utf-8 -*-
"""
Namunaviy (demo) ma'lumotlar generatori.

``python run.py --demo`` bilan chaqiriladi. Bo'sh bazaga real biznesga
o'xshash ma'lumotlar yozadi: kategoriyalar, mahsulotlar, mijozlar,
ta'minotchilar, xaridlar, savdolar, xodimlar — dashboard va hisobotlarni
darhol "jonlantirish" uchun.

Idempotent emas: faqat mahsulotlar hali yaratilmagan bo'lsa ishlaydi
(takror chaqirilsa jim o'tadi).
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from src.core.logger import get_logger
from src.core.utils import today_str

_PRODUCTS = [
    ("Guruch Lazer 1kg", "4780001000011", 9000, 12000, "dona", 30),
    ("Un Oliy nav 1kg", "4780001000028", 5000, 7000, "dona", 40),
    ("Shakar 1kg", "4780001000035", 10000, 13000, "dona", 25),
    ("O'simlik yog'i 1L", "4780001000042", 18000, 23000, "dona", 20),
    ("Makaron 400g", "4780001000059", 4000, 6000, "dona", 50),
    ("Choy Kok 100g", "4780001000066", 8000, 12000, "dona", 30),
    ("Tuz 1kg", "4780001000073", 1500, 2500, "dona", 40),
    ("Sut 1L", "4780001000080", 7000, 9500, "dona", 15),
    ("Non buxanka", "4780001000097", 2500, 4000, "dona", 20),
    ("Tuxum 10 dona", "4780001000103", 12000, 16000, "quti", 10),
    ("Kartoshka 1kg", "4780001000110", 3000, 5000, "kg", 100),
    ("Piyoz 1kg", "4780001000127", 2500, 4000, "kg", 80),
    ("Sabzi 1kg", "4780001000134", 3000, 4500, "kg", 60),
    ("Gazli suv 1.5L", "4780001000141", 4000, 6500, "dona", 40),
    ("Pechenye 300g", "4780001000158", 9000, 13000, "dona", 25),
]

_CUSTOMERS = [
    ("Do'kon Baraka", "+998901112233", "301111111", 5),
    ("Mini Market Oila", "+998902223344", "302222222", 3),
    ("Supermarket Mega", "+998903334455", "303333333", 7),
    ("Choyxona Milliy", "+998904445566", "304444444", 0),
    ("Restoran Registon", "+998905556677", "305555555", 10),
]

_SUPPLIERS = [
    ("Optom Baza MChJ", "311111111", "+998971112233"),
    ("Agro Distribyutor", "312222222", "+998972223344"),
    ("Import Savdo LLC", "313333333", "+998973334455"),
]

_EMPLOYEES = [
    ("Aliyev Alisher Aliyevich", "Direktor", 8000000),
    ("Karimova Nilufar Karimovna", "Bosh buxgalter", 6000000),
    ("Rahimov Sardor Rahimovich", "Sotuvchi", 3500000),
    ("Yusupova Dilnoza Yusupovna", "Kassir", 3000000),
    ("Tosheva Malika Toshevna", "Omborchi", 3200000),
]


def seed_demo_data(ctx) -> None:
    """Bo'sh bazaga demo ma'lumotlarni yozadi."""
    log = get_logger("demo")
    db = ctx.db
    S = ctx.services

    if db.query_one("SELECT id FROM products LIMIT 1"):
        log.info("Demo: mahsulotlar mavjud — o'tkazib yuborildi.")
        return

    admin = db.query_one(
        "SELECT id, username, role FROM users WHERE role = 'administrator' "
        "LIMIT 1")
    user = dict(admin) if admin else {"id": 1, "username": "system"}
    rng = random.Random(42)  # takrorlanuvchi natija uchun

    products = S.get("products")
    inventory = S.get("inventory")
    purchases = S.get("purchases")
    sales = S.get("sales")
    customers = S.get("customers")
    suppliers = S.get("suppliers")
    hr = S.get("hr")
    warehouse_id = inventory.default_warehouse_id()

    # 1. Kategoriya
    cat_id = products.create_category("Oziq-ovqat", user=user)

    # 2. Mahsulotlar
    product_ids = []
    for name, barcode, cost, price, unit, min_stock in _PRODUCTS:
        pid = products.create({
            "name": name, "barcode": barcode, "cost_price": cost,
            "sale_price": price, "unit": unit, "min_stock": min_stock,
            "category_id": cat_id,
        }, user)
        product_ids.append(pid)

    # 3. Ta'minotchilar + kontragentlar
    supplier_ids = [suppliers.create(
        {"name": n, "tin": tin, "phone": ph}, user)
        for n, tin, ph in _SUPPLIERS]
    customer_ids = [customers.create(
        {"name": n, "phone": ph, "tin": tin, "discount_percent": disc}, user)
        for n, ph, tin, disc in _CUSTOMERS]

    # 4. Xaridlar (omborni to'ldirish) — oxirgi 3 oy
    for month_offset in range(3, 0, -1):
        doc_date = (date.today() - timedelta(days=month_offset * 28)).isoformat()
        items = [{"product_id": pid, "quantity": rng.randint(40, 120),
                  "price": _PRODUCTS[i][2]}
                 for i, pid in enumerate(product_ids)]
        pur_id = purchases.create(rng.choice(supplier_ids), warehouse_id,
                                  items, user=user, doc_date=doc_date)
        purchases.receive(pur_id, user)

    # 5. Savdolar — oxirgi 90 kunda tarqalgan
    for day_offset in range(90, 0, -1):
        doc_date = (date.today() - timedelta(days=day_offset)).isoformat()
        num_sales = rng.randint(1, 4)
        for _ in range(num_sales):
            n_items = rng.randint(1, 5)
            chosen = rng.sample(range(len(product_ids)), n_items)
            items = [{"product_id": product_ids[i],
                      "quantity": rng.randint(1, 8)} for i in chosen]
            try:
                doc_id = sales.create_doc(
                    "invoice", rng.choice(customer_ids), warehouse_id,
                    items, user=user, doc_date=doc_date)
                sales.confirm(doc_id, user=user)
                # ko'pchiligini to'lash
                if rng.random() < 0.8:
                    doc = sales.get_doc(doc_id)["doc"]
                    S.get("payments").receive_for_sale(
                        doc_id, doc["total"],
                        method=rng.choice(["cash", "card", "bank"]),
                        user=user)
            except Exception:  # noqa: BLE001 - qoldiq tugasa o'tkazib yuboramiz
                continue

    # 6. Xodimlar + bir oylik ish haqi
    dept_id = hr.create_department("Savdo bo'limi", user=user)
    for full_name, position, salary in _EMPLOYEES:
        hr.create_employee({
            "full_name": full_name, "position": position, "salary": salary,
            "department_id": dept_id,
        }, user)
    try:
        payroll = S.get("payroll")
        run_id = payroll.create_run(today_str()[:7], user)
        payroll.approve(run_id, user)
    except Exception:  # noqa: BLE001
        pass

    log.info("Demo ma'lumotlar yozildi: %d mahsulot, %d mijoz, %d xodim.",
             len(product_ids), len(customer_ids), len(_EMPLOYEES))
