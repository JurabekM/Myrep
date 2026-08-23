"""Bosma hujjatlar — buyurtma, hisob, yuk xati, kvitansiya.

PDF Qt'ning o'z vositalari bilan chiqariladi (`QTextDocument` +
`QPdfWriter`) — qo'shimcha kutubxona kerak emas, ya'ni installer
kichikroq va bog'liqlik kamroq.

Shablonlar oq fonli: ular BOSILADI. Ilova dark, hujjat esa qog'ozga
tushadi — bu ikki xil kontekst.
"""

from __future__ import annotations

import datetime as dt
import html
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from distribos.domain.formatting import money as _money_fmt, quantity as _qty
from distribos.persistence.models import (
    Customer,
    Order,
    OrderLine,
    Organization,
    Payment,
    Product,
    Warehouse,
)


class DocumentError(RuntimeError):
    """Hujjat tayyorlanmadi."""


@dataclass(frozen=True, slots=True)
class DocumentResult:
    path: Path
    title: str
    page_count: int


def _money(value: int) -> str:
    return _money_fmt(int(value or 0))


def _escape(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


_STYLE = """
<style>
  body { font-family: 'Segoe UI', sans-serif; color: #111; font-size: 10pt; }
  h1 { font-size: 17pt; margin: 0 0 2pt 0; }
  .sub { color: #555; font-size: 9pt; margin-bottom: 10pt; }
  .org { font-size: 11pt; font-weight: bold; }
  .meta td { padding: 2pt 8pt 2pt 0; font-size: 9.5pt; }
  table.items { width: 100%; border-collapse: collapse; margin-top: 10pt; }
  table.items th {
      background: #f0f2f5; border: 1px solid #c8ccd4;
      padding: 5pt; text-align: left; font-size: 9pt;
  }
  table.items td { border: 1px solid #d5d9e0; padding: 5pt; font-size: 9.5pt; }
  td.num, th.num { text-align: right; }
  .total { font-size: 12pt; font-weight: bold; margin-top: 10pt; text-align: right; }
  .sign { margin-top: 28pt; font-size: 9.5pt; }
  .note { margin-top: 14pt; color: #666; font-size: 8.5pt; }
</style>
"""


def _organization(session: Session) -> Organization | None:
    return session.execute(select(Organization)).scalars().first()


def _header(session: Session, title: str, subtitle: str = "") -> str:
    organization = _organization(session)
    name = _escape(organization.name) if organization else "Korxona"
    details = []
    if organization:
        if organization.tax_id:
            details.append(f"STIR: {_escape(organization.tax_id)}")
        if organization.phone:
            details.append(f"Tel: {_escape(organization.phone)}")
        if organization.address:
            details.append(_escape(organization.address))
    return (
        f"<div class='org'>{name}</div>"
        f"<div class='sub'>{' · '.join(details)}</div>"
        f"<h1>{_escape(title)}</h1>"
        f"<div class='sub'>{_escape(subtitle)}</div>"
    )


def render_order(session: Session, order_id: str, *, title: str = "Buyurtma") -> str:
    """Buyurtma / hisob / yuk xati uchun umumiy shablon."""
    order = session.get(Order, order_id)
    if order is None:
        raise DocumentError("Buyurtma topilmadi")

    customer = session.get(Customer, order.customer_id)
    warehouse = session.get(Warehouse, order.warehouse_id) if order.warehouse_id else None

    lines = session.execute(
        select(OrderLine, Product.sku, Product.name, Product.unit)
        .join(Product, Product.id == OrderLine.product_id)
        .where(OrderLine.order_id == order_id)
    ).all()

    rows = []
    for index, (line, sku, name, unit) in enumerate(lines, start=1):
        rows.append(
            f"<tr><td class='num'>{index}</td><td>{_escape(sku)}</td>"
            f"<td>{_escape(name)}</td><td>{_escape(unit)}</td>"
            f"<td class='num'>{_qty(line.quantity)}</td>"
            f"<td class='num'>{_money(line.unit_price)}</td>"
            f"<td class='num'>{_qty(line.discount_percent)} %</td>"
            f"<td class='num'>{_money(line.line_total)}</td></tr>"
        )

    from distribos.presentation.status import order_state

    meta = (
        "<table class='meta'>"
        f"<tr><td>Hujjat raqami:</td><td><b>{_escape(order.number)}</b></td>"
        f"<td>Sana:</td><td>{order.ordered_at:%d.%m.%Y}</td></tr>"
        f"<tr><td>Mijoz:</td><td colspan='3'><b>{_escape(customer.name if customer else '—')}</b>"
        f"{(' · ' + _escape(customer.phone)) if customer and customer.phone else ''}</td></tr>"
        f"<tr><td>Holati:</td><td>{_escape(order_state(order.state))}</td>"
        f"<td>Ombor:</td><td>{_escape(warehouse.name if warehouse else '—')}</td></tr>"
        "</table>"
    )

    outstanding = order.total - order.paid_total
    totals = (
        f"<div class='total'>Jami: {_money(order.total)}</div>"
        + (f"<div class='total'>To'langan: {_money(order.paid_total)}</div>"
           if order.paid_total else "")
        + (f"<div class='total'>Qarz: {_money(outstanding)}</div>"
           if outstanding else "")
    )

    return (
        f"{_STYLE}{_header(session, title, f'Hujjat: {order.number}')}{meta}"
        "<table class='items'><tr>"
        "<th class='num'>#</th><th>SKU</th><th>Mahsulot</th><th>Birlik</th>"
        "<th class='num'>Miqdor</th><th class='num'>Narx</th>"
        "<th class='num'>Chegirma</th><th class='num'>Summa</th>"
        "</tr>" + "".join(rows) + "</table>"
        + totals
        + "<div class='sign'>Topshirdi: ____________________ &nbsp;&nbsp;&nbsp; "
          "Qabul qildi: ____________________</div>"
        + "<div class='note'>Hujjat DistribOS AI dasturida shakllantirildi. "
          "Buxgalteriya va soliq hisobotlari uchun rasmiy hujjat sifatida "
          "ishlatilishi alohida kelishilishi kerak.</div>"
    )


def render_payment_receipt(session: Session, payment_id: str) -> str:
    payment = session.get(Payment, payment_id)
    if payment is None:
        raise DocumentError("To'lov topilmadi")
    customer = session.get(Customer, payment.customer_id) if payment.customer_id else None

    direction = "Kirim (mijozdan)" if payment.direction == "IN" else "Chiqim"
    meta = (
        "<table class='meta'>"
        f"<tr><td>Kvitansiya:</td><td><b>{_escape(payment.number)}</b></td>"
        f"<td>Sana:</td><td>{payment.occurred_at:%d.%m.%Y %H:%M}</td></tr>"
        f"<tr><td>Mijoz:</td><td colspan='3'>{_escape(customer.name if customer else '—')}</td></tr>"
        f"<tr><td>Yo'nalish:</td><td>{_escape(direction)}</td>"
        f"<td>Usul:</td><td>{_escape(payment.method)}</td></tr>"
        "</table>"
    )
    reversed_note = (
        "<div class='note'><b>DIQQAT:</b> bu to'lov keyinchalik bekor "
        "qilingan (teskari yozuv mavjud).</div>"
        if payment.is_reversed else ""
    )
    return (
        f"{_STYLE}{_header(session, 'To`lov kvitansiyasi', payment.number)}{meta}"
        f"<div class='total'>Summa: {_money(payment.amount)}</div>"
        f"{reversed_note}"
        + (f"<div class='note'>Izoh: {_escape(payment.note)}</div>" if payment.note else "")
        + "<div class='sign'>Qabul qildi: ____________________</div>"
    )


def render_report(report) -> str:
    """Hisobotni bosma shaklga aylantiradi."""
    header_cells = "".join(f"<th>{_escape(column)}</th>" for column in report.columns)
    body_rows = "".join(
        "<tr>" + "".join(f"<td>{_escape(cell)}</td>" for cell in row) + "</tr>"
        for row in report.rows
    )
    footer = ""
    if report.footer:
        footer = (
            "<tr>" + "".join(f"<th>{_escape(cell)}</th>" for cell in report.footer)
            + "</tr>"
        )
    generated = report.generated_at.strftime("%d.%m.%Y %H:%M")
    return (
        f"{_STYLE}<h1>{_escape(report.title)}</h1>"
        f"<div class='sub'>{_escape(report.description)} · "
        f"tayyorlandi {generated} · {report.row_count} qator</div>"
        f"<table class='items'><tr>{header_cells}</tr>{body_rows}{footer}</table>"
    )


def write_pdf(html_body: str, destination: Path, *, title: str = "") -> DocumentResult:
    """HTML ni PDF ga chiqaradi.

    Qt kerak — bu funksiya faqat GUI o'rnatilgan muhitda ishlaydi.
    """
    from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        raise DocumentError(
            "PDF chiqarish uchun grafik muhit kerak (Qt ilovasi ishlamayapti)"
        )

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(destination))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(150)
    if title:
        writer.setTitle(title)

    document = QTextDocument()
    document.setHtml(html_body)
    document.setPageSize(writer.pageLayout().paintRectPixels(writer.resolution()).size())
    document.print_(writer)

    return DocumentResult(
        path=destination, title=title or "Hujjat", page_count=document.pageCount()
    )


def write_html(html_body: str, destination: Path, *, title: str = "") -> DocumentResult:
    """HTML fayl sifatida saqlaydi (PDF muqobili, brauzerda ochiladi)."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        f"<!doctype html><html lang='uz'><head><meta charset='utf-8'>"
        f"<title>{_escape(title)}</title></head><body>{html_body}</body></html>",
        encoding="utf-8",
    )
    return DocumentResult(path=destination, title=title or "Hujjat", page_count=1)


#: Buyurtma asosidagi hujjat turlari.
ORDER_DOCUMENTS: tuple[tuple[str, str], ...] = (
    ("order", "Buyurtma"),
    ("invoice", "Hisob-faktura"),
    ("waybill", "Yuk xati"),
    ("return", "Qaytarish hujjati"),
)


def default_document_name(kind: str, number: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d")
    safe = "".join(character for character in number if character.isalnum() or character in "-_")
    return f"{kind}-{safe}-{stamp}.pdf"
