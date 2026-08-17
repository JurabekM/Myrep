"""Quotation and shipping-document PDF generation."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from app.reports.pdf_base import (
    BRAND,
    LINE,
    footer_factory,
    kv_table,
    logo_flowable,
    make_document,
    styles,
    table_style,
)
from app.utils.formatting import fmt_date

_TEXT = {
    "en": {
        "quotation": "QUOTATION",
        "to": "To",
        "from": "From",
        "no": "No",
        "date": "Date",
        "valid": "Valid until",
        "incoterm": "Delivery terms",
        "port": "Port / place of loading",
        "destination": "Destination",
        "payment": "Payment terms",
        "lead_time": "Lead time",
        "currency": "Currency",
        "item": "Item",
        "hs": "HS code",
        "qty": "Qty",
        "unit": "Unit",
        "price": "Unit price",
        "total": "Amount",
        "subtotal": "Subtotal",
        "freight": "Freight",
        "insurance": "Insurance",
        "discount": "Discount",
        "grand": "GRAND TOTAL",
        "packaging": "Packaging",
        "certificates": "Certificates",
        "remarks": "Remarks",
        "bank": "Bank details",
        "signature": "Authorised signature",
        "days": "days",
    },
    "ru": {
        "quotation": "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ",
        "to": "Кому",
        "from": "От",
        "no": "№",
        "date": "Дата",
        "valid": "Действительно до",
        "incoterm": "Условия поставки",
        "port": "Порт / место отгрузки",
        "destination": "Пункт назначения",
        "payment": "Условия оплаты",
        "lead_time": "Срок изготовления",
        "currency": "Валюта",
        "item": "Наименование",
        "hs": "ТН ВЭД",
        "qty": "Кол-во",
        "unit": "Ед.",
        "price": "Цена",
        "total": "Сумма",
        "subtotal": "Итого",
        "freight": "Фрахт",
        "insurance": "Страхование",
        "discount": "Скидка",
        "grand": "ВСЕГО К ОПЛАТЕ",
        "packaging": "Упаковка",
        "certificates": "Сертификаты",
        "remarks": "Примечания",
        "bank": "Банковские реквизиты",
        "signature": "Подпись уполномоченного лица",
        "days": "дней",
    },
    "uz": {
        "quotation": "TIJORAT TAKLIFI",
        "to": "Kimga",
        "from": "Kimdan",
        "no": "Raqam",
        "date": "Sana",
        "valid": "Amal qiladi",
        "incoterm": "Yetkazib berish sharti",
        "port": "Yuklash porti / joyi",
        "destination": "Manzil",
        "payment": "To'lov sharti",
        "lead_time": "Ishlab chiqarish muddati",
        "currency": "Valyuta",
        "item": "Mahsulot",
        "hs": "HS kodi",
        "qty": "Miqdor",
        "unit": "Birlik",
        "price": "Narx",
        "total": "Summa",
        "subtotal": "Jami",
        "freight": "Fraxt",
        "insurance": "Sug'urta",
        "discount": "Chegirma",
        "grand": "UMUMIY SUMMA",
        "packaging": "Qadoqlash",
        "certificates": "Sertifikatlar",
        "remarks": "Izohlar",
        "bank": "Bank rekvizitlari",
        "signature": "Vakolatli imzo",
        "days": "kun",
    },
}


def build_quotation_pdf(path: str | Path, quotation: dict, company: dict) -> str:
    """Render a quotation to a professional PDF and return the file path."""
    lang = quotation.get("language") or "en"
    text = _TEXT.get(lang, _TEXT["en"])
    st = styles()
    doc = make_document(path, f"{text['quotation']} {quotation['number']}")
    currency = quotation.get("currency") or "USD"
    story: list = []

    logo = logo_flowable(company.get("logo_path"))
    header_left = [
        Paragraph(f"<b>{company.get('name', '')}</b>", st["body"]),
        Paragraph(company.get("address") or "", st["small"]),
        Paragraph(
            " | ".join(
                part
                for part in (company.get("phone"), company.get("email"), company.get("website"))
                if part
            ),
            st["small"],
        ),
    ]
    header = Table(
        [[logo or Paragraph("", st["body"]), header_left]],
        colWidths=[48 * mm, None],
    )
    header.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])
    )
    story.append(header)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(text["quotation"], st["title"]))
    story.append(
        Paragraph(
            f"{text['no']}: <b>{quotation['number']}</b> "
            f"(rev. {quotation.get('revision', 1)}) &nbsp;&nbsp; "
            f"{text['date']}: <b>{fmt_date(quotation.get('issue_date'))}</b>",
            st["subtitle"],
        )
    )

    left_rows = [
        (f"{text['to']}:", quotation.get("buyer", "")),
        ("", quotation.get("buyer_contact") or ""),
        ("", quotation.get("buyer_country") or ""),
        ("", quotation.get("buyer_email") or ""),
    ]
    right_rows = [
        (f"{text['valid']}:", fmt_date(quotation.get("valid_until"))),
        (f"{text['incoterm']}:", quotation.get("incoterm") or ""),
        (f"{text['port']}:", quotation.get("loading_port") or ""),
        (f"{text['destination']}:", quotation.get("destination") or ""),
        (f"{text['payment']}:", quotation.get("payment_terms") or ""),
        (
            f"{text['lead_time']}:",
            (
                f"{quotation.get('lead_time_days')} {text['days']}"
                if quotation.get("lead_time_days")
                else ""
            ),
        ),
        (f"{text['currency']}:", currency),
    ]
    info = Table(
        [[kv_table(left_rows, 80 * mm), kv_table(right_rows, 88 * mm)]],
        colWidths=[84 * mm, None],
    )
    info.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])
    )
    story.append(info)
    story.append(Spacer(1, 5 * mm))

    if quotation.get("intro_text"):
        story.append(Paragraph(quotation["intro_text"].replace("\n", "<br/>"), st["body"]))
        story.append(Spacer(1, 4 * mm))

    head = [
        "#",
        text["item"],
        text["hs"],
        text["qty"],
        text["unit"],
        f"{text['price']}, {currency}",
        f"{text['total']}, {currency}",
    ]
    rows = [head]
    for index, item in enumerate(quotation.get("items", []), 1):
        rows.append(
            [
                str(index),
                Paragraph(item.get("description", ""), st["cell"]),
                item.get("hs_code") or "",
                f"{item.get('quantity', 0):g}",
                item.get("unit") or "",
                f"{item.get('unit_price', 0):,.2f}",
                f"{item.get('line_total', 0):,.2f}",
            ]
        )
    items_table = Table(
        rows, colWidths=[10 * mm, None, 20 * mm, 20 * mm, 15 * mm, 26 * mm, 28 * mm], repeatRows=1
    )
    style = table_style()
    style.add("ALIGN", (3, 1), (-1, -1), "RIGHT")
    items_table.setStyle(style)
    story.append(items_table)
    story.append(Spacer(1, 3 * mm))

    total_rows = [[text["subtotal"], f"{quotation.get('subtotal', 0):,.2f} {currency}"]]
    if quotation.get("freight_cost"):
        total_rows.append([text["freight"], f"{quotation['freight_cost']:,.2f} {currency}"])
    if quotation.get("insurance_cost"):
        total_rows.append([text["insurance"], f"{quotation['insurance_cost']:,.2f} {currency}"])
    if quotation.get("discount"):
        total_rows.append([text["discount"], f"-{quotation['discount']:,.2f} {currency}"])
    total_rows.append([text["grand"], f"{quotation.get('grand_total', 0):,.2f} {currency}"])

    totals = Table(total_rows, colWidths=[50 * mm, 40 * mm], hAlign="RIGHT")
    totals.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, BRAND),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, -1), (-1, -1), BRAND),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(totals)
    story.append(Spacer(1, 5 * mm))

    detail_blocks = []
    if quotation.get("packaging"):
        detail_blocks.append(f"<b>{text['packaging']}:</b> {quotation['packaging']}")
    if quotation.get("certificate_refs"):
        detail_blocks.append(f"<b>{text['certificates']}:</b> {quotation['certificate_refs']}")
    if quotation.get("remarks"):
        detail_blocks.append(f"<b>{text['remarks']}:</b> {quotation['remarks']}")
    for block in detail_blocks:
        story.append(Paragraph(block.replace("\n", "<br/>"), st["body"]))
        story.append(Spacer(1, 2 * mm))

    bank_rows = [
        (company.get("bank_name") or "", company.get("bank_account") or ""),
    ]
    if company.get("bank_swift"):
        story.append(Spacer(1, 3 * mm))
        story.append(
            KeepTogether(
                [
                    Paragraph(f"<b>{text['bank']}</b>", st["h2"]),
                    Paragraph(
                        f"{company.get('bank_name', '')}<br/>"
                        f"Account: {company.get('bank_account', '')}<br/>"
                        f"SWIFT: {company.get('bank_swift', '')}",
                        st["small"],
                    ),
                ]
            )
        )
    _ = bank_rows

    story.append(Spacer(1, 10 * mm))
    signature = Table(
        [[Paragraph(f"{text['signature']}: _______________________", st["small"])]],
        colWidths=[None],
    )
    signature.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(signature)

    footer = footer_factory(company.get("name", ""), f"| {quotation['number']}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(path)


def build_shipping_document(
    path: str | Path, shipment: dict, company: dict, kind: str = "commercial_invoice"
) -> str:
    """Render a commercial invoice or packing list draft."""
    st = styles()
    is_invoice = kind == "commercial_invoice"
    title = "COMMERCIAL INVOICE" if is_invoice else "PACKING LIST"
    doc = make_document(path, f"{title} {shipment['number']}")
    currency = shipment.get("currency") or "USD"
    story: list = []

    logo = logo_flowable(company.get("logo_path"))
    if logo:
        story.append(logo)
        story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(title, st["title"]))
    story.append(Paragraph(f"No: <b>{shipment['number']}</b>", st["subtitle"]))

    left = kv_table(
        [
            ("Shipper:", company.get("name", "")),
            ("", company.get("address") or ""),
            ("Tax ID:", company.get("tax_id") or ""),
        ],
        80 * mm,
    )
    right = kv_table(
        [
            ("Consignee:", shipment.get("buyer", "")),
            ("", shipment.get("buyer_address") or ""),
            ("Country:", shipment.get("buyer_country") or ""),
            ("Incoterm:", shipment.get("incoterm") or ""),
            ("Port of loading:", shipment.get("loading_port") or ""),
            ("Destination:", shipment.get("destination") or ""),
            ("ETD / ETA:", f"{fmt_date(shipment.get('etd'))} / {fmt_date(shipment.get('eta'))}"),
        ],
        88 * mm,
    )
    info = Table([[left, right]], colWidths=[84 * mm, None])
    info.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])
    )
    story.append(info)
    story.append(Spacer(1, 5 * mm))

    if is_invoice:
        head = [
            "#",
            "Description",
            "HS code",
            "Qty",
            "Unit",
            f"Price, {currency}",
            f"Amount, {currency}",
        ]
        widths = [10 * mm, None, 20 * mm, 20 * mm, 15 * mm, 26 * mm, 28 * mm]
    else:
        head = ["#", "Description", "HS code", "Qty", "Unit", "Packages", "Net, kg", "Gross, kg"]
        widths = [10 * mm, None, 20 * mm, 18 * mm, 14 * mm, 20 * mm, 20 * mm, 20 * mm]

    rows = [head]
    for index, item in enumerate(shipment.get("items", []), 1):
        if is_invoice:
            rows.append(
                [
                    str(index),
                    Paragraph(item.get("description", ""), st["cell"]),
                    item.get("hs_code") or "",
                    f"{item.get('quantity', 0):g}",
                    item.get("unit") or "",
                    f"{item.get('unit_price', 0):,.2f}",
                    f"{item.get('amount', 0):,.2f}",
                ]
            )
        else:
            rows.append(
                [
                    str(index),
                    Paragraph(item.get("description", ""), st["cell"]),
                    item.get("hs_code") or "",
                    f"{item.get('quantity', 0):g}",
                    item.get("unit") or "",
                    f"{item.get('packages', 0):g}",
                    f"{item.get('net_weight', 0):,.2f}",
                    f"{item.get('gross_weight', 0):,.2f}",
                ]
            )
    table = Table(rows, colWidths=widths, repeatRows=1)
    style = table_style()
    style.add("ALIGN", (3, 1), (-1, -1), "RIGHT")
    table.setStyle(style)
    story.append(table)
    story.append(Spacer(1, 4 * mm))

    if is_invoice:
        total = sum(item.get("amount", 0) for item in shipment.get("items", []))
        summary = [["TOTAL", f"{total:,.2f} {currency}"]]
    else:
        summary = [
            ["Total packages", f"{shipment.get('package_count', 0):g}"],
            ["Net weight, kg", f"{shipment.get('net_weight', 0):,.2f}"],
            ["Gross weight, kg", f"{shipment.get('gross_weight', 0):,.2f}"],
            ["Container", shipment.get("container_type") or "-"],
        ]
    summary_table = Table(summary, colWidths=[50 * mm, 40 * mm], hAlign="RIGHT")
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, LINE),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Authorised signature: _______________________", st["small"]))
    story.append(Paragraph("Draft generated by ExportFlow", st["small"]))

    footer = footer_factory(company.get("name", ""), f"| {shipment['number']}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(path)
