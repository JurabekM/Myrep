"""Static HTML catalog export (no backend required) and ZIP packaging."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import PATHS
from app.utils.formatting import fmt_datetime, now, slugify

_TEXT = {
    "en": {
        "request": "Request a quote",
        "request_subject": "Quotation request",
        "request_body": "Please send your best price, MOQ and lead time for SKU",
        "products": "Products",
        "about": "About the company",
        "certificates": "Certificates",
        "certificate": "Certificate",
        "issuer": "Issuer",
        "valid_until": "Valid until",
        "contacts": "Contacts",
        "details": "View details",
        "no_photo": "No photo",
        "sku": "SKU",
        "hs": "HS code",
        "origin": "Country of origin",
        "moq": "MOQ",
        "lead_time": "Lead time",
        "capacity": "Monthly capacity",
        "packaging": "Packaging",
        "net_weight": "Net weight",
        "gross_weight": "Gross weight",
        "shelf_life": "Shelf life",
        "storage": "Storage condition",
        "price": "Price",
        "specs": "Specification",
        "days": "days",
        "month": "month",
        "cert_note": "Certification documents are available on request.",
        "footer_note": "This catalog is a static export. Prices and terms are confirmed in writing per enquiry.",
    },
    "ru": {
        "request": "Запросить предложение",
        "request_subject": "Запрос коммерческого предложения",
        "request_body": "Просим направить цену, МОЗ и срок поставки по артикулу",
        "products": "Продукция",
        "about": "О компании",
        "certificates": "Сертификаты",
        "certificate": "Сертификат",
        "issuer": "Кем выдан",
        "valid_until": "Действителен до",
        "contacts": "Контакты",
        "details": "Подробнее",
        "no_photo": "Нет фото",
        "sku": "Артикул",
        "hs": "Код ТН ВЭД",
        "origin": "Страна происхождения",
        "moq": "Минимальный заказ",
        "lead_time": "Срок производства",
        "capacity": "Мощность в месяц",
        "packaging": "Упаковка",
        "net_weight": "Вес нетто",
        "gross_weight": "Вес брутто",
        "shelf_life": "Срок годности",
        "storage": "Условия хранения",
        "price": "Цена",
        "specs": "Характеристики",
        "days": "дней",
        "month": "месяц",
        "cert_note": "Документы о сертификации предоставляются по запросу.",
        "footer_note": "Каталог является статической выгрузкой. Цены и условия подтверждаются письменно по запросу.",
    },
    "uz": {
        "request": "Taklif so'rash",
        "request_subject": "Tijorat taklifi so'rovi",
        "request_body": "Quyidagi SKU bo'yicha narx, MOQ va yetkazish muddatini yuboring",
        "products": "Mahsulotlar",
        "about": "Kompaniya haqida",
        "certificates": "Sertifikatlar",
        "certificate": "Sertifikat",
        "issuer": "Bergan tashkilot",
        "valid_until": "Amal qiladi",
        "contacts": "Aloqa",
        "details": "Batafsil",
        "no_photo": "Rasm yo'q",
        "sku": "SKU",
        "hs": "HS kodi",
        "origin": "Kelib chiqish mamlakati",
        "moq": "Minimal buyurtma",
        "lead_time": "Ishlab chiqarish muddati",
        "capacity": "Oylik quvvat",
        "packaging": "Qadoqlash",
        "net_weight": "Sof vazn",
        "gross_weight": "Umumiy vazn",
        "shelf_life": "Yaroqlilik muddati",
        "storage": "Saqlash sharti",
        "price": "Narx",
        "specs": "Texnik tavsif",
        "days": "kun",
        "month": "oy",
        "cert_note": "Sertifikatlash hujjatlari so'rov asosida taqdim etiladi.",
        "footer_note": "Ushbu katalog statik eksport. Narx va shartlar so'rov asosida yozma tasdiqlanadi.",
    },
}


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(PATHS.templates_dir / "catalog")),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["urlencode"] = lambda value: quote(str(value))
    return env


def _copy_asset(source: str | None, assets_dir: Path, prefix: str) -> str | None:
    """Copy an image into the export's ``assets`` folder, returning its name."""
    if not source:
        return None
    path = Path(source)
    if not path.exists():
        return None
    target_name = f"{prefix}{path.suffix.lower()}"
    shutil.copy2(path, assets_dir / target_name)
    return target_name


def build_html_catalog(output_dir: str | Path, catalog: dict, company: dict) -> str:
    """Write a fully self-contained static catalog and return its directory."""
    output = Path(output_dir)
    if output.exists():
        shutil.rmtree(output)
    assets = output / "assets"
    products_dir = output / "products"
    assets.mkdir(parents=True, exist_ok=True)
    products_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(PATHS.templates_dir / "catalog" / "base.css", assets / "style.css")
    logo_file = _copy_asset(company.get("logo_path"), assets, "logo")

    lang = catalog.get("language") or "en"
    text = _TEXT.get(lang, _TEXT["en"])
    env = _environment()
    contact_email = company.get("export_contact_email") or company.get("email") or ""
    contact_phone = company.get("export_contact_phone") or company.get("phone") or ""
    generated_at = fmt_datetime(now())

    products = []
    for index, product in enumerate(catalog.get("products", []), 1):
        slug = slugify(f"{product.get('sku', '')}-{product.get('name', '')}", f"product-{index}")
        photo_files = []
        for photo_index, photo in enumerate(product.get("photos") or [], 1):
            name = _copy_asset(photo, assets, f"{slug}-{photo_index}")
            if name:
                photo_files.append(name)
        entry = dict(product)
        entry["slug"] = slug
        entry["photo_files"] = photo_files
        entry["photo_file"] = photo_files[0] if photo_files else None
        products.append(entry)

    context = {
        "catalog": catalog,
        "company": company,
        "products": products,
        "certificates": catalog.get("certificates") or [],
        "about_text": catalog.get("about_text")
        or company.get(f"about_{lang}")
        or company.get("about_en")
        or "",
        "lang": lang,
        "t": text,
        "logo_file": logo_file,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "generated_at": generated_at,
    }

    index_html = env.get_template("index.html.j2").render(**context)
    (output / "index.html").write_text(index_html, encoding="utf-8")

    product_template = env.get_template("product.html.j2")
    for product in products:
        html = product_template.render(**{**context, "product": product})
        (products_dir / f"{product['slug']}.html").write_text(html, encoding="utf-8")

    return str(output)


def zip_catalog(source_dir: str | Path, zip_path: str | Path) -> str:
    """Package an exported catalog folder into a ZIP archive."""
    source = Path(source_dir)
    target = Path(zip_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in source.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(source))
    return str(target)
