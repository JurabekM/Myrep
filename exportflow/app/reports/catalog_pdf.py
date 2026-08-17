"""Multilingual product catalog PDF generation."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, Spacer, Table, TableStyle

from app.reports.pdf_base import (
    BRAND,
    BRAND_LIGHT,
    MUTED,
    footer_factory,
    logo_flowable,
    make_document,
    styles,
    table_style,
)

_TEXT = {
    "en": {
        "catalog": "PRODUCT CATALOG",
        "about": "About the company",
        "certificates": "Certificates",
        "contacts": "Contacts",
        "products": "Products",
        "sku": "SKU",
        "hs": "HS code",
        "moq": "MOQ",
        "unit": "Unit",
        "lead_time": "Lead time",
        "packaging": "Packaging",
        "origin": "Origin",
        "specs": "Specification",
        "price": "Price",
        "days": "days",
        "no_photo": "No photo",
        "cert_note": "Certification documents are available on request.",
        "request": "Request a quote",
    },
    "ru": {
        "catalog": "КАТАЛОГ ПРОДУКЦИИ",
        "about": "О компании",
        "certificates": "Сертификаты",
        "contacts": "Контакты",
        "products": "Продукция",
        "sku": "Артикул",
        "hs": "ТН ВЭД",
        "moq": "МОЗ",
        "unit": "Ед.",
        "lead_time": "Срок",
        "packaging": "Упаковка",
        "origin": "Происхождение",
        "specs": "Характеристики",
        "price": "Цена",
        "days": "дней",
        "no_photo": "Нет фото",
        "cert_note": "Документы о сертификации предоставляются по запросу.",
        "request": "Запросить предложение",
    },
    "uz": {
        "catalog": "MAHSULOTLAR KATALOGI",
        "about": "Kompaniya haqida",
        "certificates": "Sertifikatlar",
        "contacts": "Aloqa",
        "products": "Mahsulotlar",
        "sku": "SKU",
        "hs": "HS kodi",
        "moq": "MOQ",
        "unit": "Birlik",
        "lead_time": "Muddat",
        "packaging": "Qadoqlash",
        "origin": "Kelib chiqishi",
        "specs": "Tavsif",
        "price": "Narx",
        "days": "kun",
        "no_photo": "Rasm yo'q",
        "cert_note": "Sertifikatlash hujjatlari so'rov asosida taqdim etiladi.",
        "request": "Taklif so'rash",
    },
}


def _product_image(path: str | None, width: float = 52 * mm, height: float = 40 * mm):
    """Scaled product photo flowable, or ``None`` when unavailable."""
    if not path or not Path(path).exists():
        return None
    try:
        from reportlab.lib.utils import ImageReader

        reader = ImageReader(path)
        img_w, img_h = reader.getSize()
        scale = min(width / img_w, height / img_h)
        return Image(path, width=img_w * scale, height=img_h * scale)
    except Exception:  # pragma: no cover
        return None


def build_catalog_pdf(path: str | Path, catalog: dict, company: dict) -> str:
    """Render the catalog to PDF and return the output path."""
    lang = catalog.get("language") or "en"
    text = _TEXT.get(lang, _TEXT["en"])
    st = styles()
    doc = make_document(path, catalog.get("title", "Catalog"))
    story: list = []

    # ------------------------------------------------------------ cover page
    logo = logo_flowable(company.get("logo_path"), 70 * mm, 32 * mm)
    if logo:
        story.append(logo)
    story.append(Spacer(1, 22 * mm))
    story.append(Paragraph(catalog.get("title") or text["catalog"], st["title"]))
    if catalog.get("subtitle"):
        story.append(Paragraph(catalog["subtitle"], st["subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            f"<b>{company.get('name', '')}</b><br/>{company.get('address') or ''}",
            st["body"],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            " | ".join(
                part
                for part in (company.get("phone"), company.get("email"), company.get("website"))
                if part
            ),
            st["small"],
        )
    )
    if catalog.get("cover_note"):
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph(catalog["cover_note"].replace("\n", "<br/>"), st["body"]))
    story.append(
        Spacer(1, 6 * mm),
    )
    story.append(Paragraph(f"Version {catalog.get('version', '1.0')}", st["small"]))
    story.append(PageBreak())

    # ------------------------------------------------------------ about page
    about = (
        catalog.get("about_text") or company.get(f"about_{lang}") or company.get("about_en") or ""
    )
    if about:
        story.append(Paragraph(text["about"], st["h1"]))
        story.append(Paragraph(about.replace("\n", "<br/>"), st["body"]))
        story.append(Spacer(1, 6 * mm))

    # --------------------------------------------------------- certificates
    certificates = catalog.get("certificates") or []
    if catalog.get("include_certificates"):
        story.append(Paragraph(text["certificates"], st["h1"]))
        if certificates:
            rows = [["#", "Certificate", "Issuer", "Valid until"]]
            for index, cert in enumerate(certificates, 1):
                rows.append(
                    [
                        str(index),
                        cert.get("name", ""),
                        cert.get("issuer") or "-",
                        cert.get("expiry_date") or "-",
                    ]
                )
            table = Table(rows, colWidths=[10 * mm, None, 45 * mm, 30 * mm], repeatRows=1)
            table.setStyle(table_style())
            story.append(table)
        else:
            story.append(Paragraph(text["cert_note"], st["body"]))
        story.append(PageBreak())

    # ------------------------------------------------------------- products
    story.append(Paragraph(text["products"], st["h1"]))
    for product in catalog.get("products", []):
        block: list = []
        block.append(Paragraph(product.get("name", ""), st["h2"]))
        photo = _product_image(product.get("photo"))
        spec_rows = [
            (text["sku"], product.get("sku", "")),
            (text["hs"], product.get("hs_code") or "-"),
            (text["origin"], product.get("origin_country") or "-"),
            (
                text["moq"],
                f"{product['moq']:g} {product.get('unit', '')}" if product.get("moq") else "-",
            ),
            (
                text["lead_time"],
                (
                    f"{product['lead_time_days']} {text['days']}"
                    if product.get("lead_time_days")
                    else "-"
                ),
            ),
            (text["packaging"], product.get("packaging_type") or "-"),
        ]
        if catalog.get("include_prices") and product.get("price_text"):
            spec_rows.append((text["price"], product["price_text"]))

        info = Table(
            [[key, value] for key, value in spec_rows],
            colWidths=[26 * mm, None],
        )
        info.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        description = product.get("description") or ""
        right_cells = [
            Paragraph(description.replace("\n", "<br/>"), st["body"]),
            Spacer(1, 2 * mm),
            info,
        ]
        layout = Table(
            [[photo or Paragraph(text["no_photo"], st["small"]), right_cells]],
            colWidths=[56 * mm, None],
        )
        layout.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("BACKGROUND", (0, 0), (0, 0), colors.white),
                ]
            )
        )
        block.append(layout)

        specs = product.get("specifications") or []
        if specs:
            rows = [[text["specs"], ""]]
            rows += [[spec["name"], spec["value"]] for spec in specs]
            spec_table = Table(rows, colWidths=[55 * mm, None])
            spec_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), BRAND_LIGHT),
                        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("SPAN", (0, 0), (-1, 0)),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            block.append(Spacer(1, 3 * mm))
            block.append(spec_table)
        if product.get("certificates"):
            block.append(Spacer(1, 2 * mm))
            block.append(
                Paragraph(
                    f"<b>{text['certificates']}:</b> {', '.join(product['certificates'])}",
                    st["small"],
                )
            )
        block.append(Spacer(1, 8 * mm))
        story.extend(block)

    # ------------------------------------------------------------- contacts
    story.append(PageBreak())
    story.append(Paragraph(text["contacts"], st["h1"]))
    contact_text = catalog.get("contact_text") or ""
    if contact_text:
        story.append(Paragraph(contact_text.replace("\n", "<br/>"), st["body"]))
        story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            f"<b>{company.get('name', '')}</b><br/>"
            f"{company.get('address') or ''}<br/>"
            f"{company.get('export_contact_name') or ''}<br/>"
            f"{company.get('export_contact_phone') or company.get('phone') or ''}<br/>"
            f"{company.get('export_contact_email') or company.get('email') or ''}<br/>"
            f"{company.get('website') or ''}",
            st["body"],
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            f"<b>{text['request']}:</b> {company.get('export_contact_email') or company.get('email') or ''}",
            st["body"],
        )
    )

    footer = footer_factory(company.get("name", ""), f"| {catalog.get('title', '')}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(path)
