"""Certificates, generic export documents and file attachments."""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import PATHS
from app.models import Attachment, Certificate, Document, Product
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.errors import NotFoundError, ValidationError
from app.utils.formatting import days_until, today

#: Alert thresholds in days before a certificate expires.
EXPIRY_ALERT_DAYS = (60, 30, 7)


def certificate_status(expiry: dt.date | None) -> str:
    """Derive the lifecycle status of a certificate from its expiry date."""
    if expiry is None:
        return "valid"
    remaining = days_until(expiry)
    if remaining is None:
        return "valid"
    if remaining < 0:
        return "expired"
    if remaining <= max(EXPIRY_ALERT_DAYS):
        return "expiring"
    return "valid"


def expiry_alerts(session: Session) -> list[dict]:
    """Certificates that crossed a 60/30/7-day alert threshold or expired."""
    rows = (
        session.scalars(
            select(Certificate).where(
                Certificate.is_archived.is_(False), Certificate.expiry_date.is_not(None)
            )
        )
        .unique()
        .all()
    )
    alerts: list[dict] = []
    for cert in rows:
        remaining = days_until(cert.expiry_date)
        if remaining is None:
            continue
        if remaining < 0:
            level = "expired"
        elif remaining <= 7:
            level = "critical"
        elif remaining <= 30:
            level = "warning"
        elif remaining <= 60:
            level = "info"
        else:
            continue
        alerts.append(
            {
                "id": cert.id,
                "name": cert.name,
                "cert_type": cert.cert_type,
                "product_id": cert.product_id,
                "expiry_date": cert.expiry_date,
                "days_left": remaining,
                "level": level,
            }
        )
    return sorted(alerts, key=lambda item: item["days_left"])


def refresh_certificate_statuses(session: Session) -> int:
    """Recompute the stored status column of every certificate."""
    rows = (
        session.scalars(select(Certificate).where(Certificate.is_archived.is_(False)))
        .unique()
        .all()
    )
    changed = 0
    for cert in rows:
        new_status = certificate_status(cert.expiry_date)
        if cert.status != new_status and cert.status != "revoked":
            cert.status = new_status
            changed += 1
    session.flush()
    return changed


def list_certificates(
    session: Session,
    *,
    text: str = "",
    cert_type: str | None = None,
    product_id: int | None = None,
    status: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Filtered certificate list."""
    stmt = select(Certificate)
    if not include_archived:
        stmt = stmt.where(Certificate.is_archived.is_(False))
    if text:
        pattern = f"%{text.strip()}%"
        stmt = stmt.where(
            or_(
                Certificate.name.ilike(pattern),
                Certificate.number.ilike(pattern),
                Certificate.issuer.ilike(pattern),
                Certificate.target_market.ilike(pattern),
            )
        )
    if cert_type:
        stmt = stmt.where(Certificate.cert_type == cert_type)
    if product_id:
        stmt = stmt.where(Certificate.product_id == product_id)
    if status:
        stmt = stmt.where(Certificate.status == status)
    rows = (
        session.scalars(stmt.order_by(Certificate.expiry_date.is_(None), Certificate.expiry_date))
        .unique()
        .all()
    )
    products = {
        row.id: row.display_name("en") for row in session.scalars(select(Product)).unique().all()
    }
    return [
        {
            "id": row.id,
            "name": row.name,
            "cert_type": row.cert_type,
            "product_id": row.product_id,
            "product": products.get(row.product_id, ""),
            "issuer": row.issuer or "",
            "number": row.number or "",
            "issue_date": row.issue_date,
            "expiry_date": row.expiry_date,
            "days_left": days_until(row.expiry_date),
            "target_market": row.target_market or "",
            "file_path": row.file_path or "",
            "verification_status": row.verification_status,
            "status": row.status,
            "notes": row.notes or "",
            "is_archived": row.is_archived,
        }
        for row in rows
    ]


def save_certificate(session: Session, actor: CurrentUser, values: dict) -> Certificate:
    """Create or update a certificate record."""
    actor.require("certificate.edit")
    name = (values.get("name") or "").strip()
    if not name:
        raise ValidationError("Certificate name is required", key="error.name_required")
    cert_id = values.get("id")
    if cert_id:
        cert = session.get(Certificate, cert_id)
        if cert is None:
            raise NotFoundError("Certificate not found")
        action = "update"
    else:
        cert = Certificate(name=name)
        session.add(cert)
        action = "create"
    for key in (
        "name",
        "cert_type",
        "product_id",
        "issuer",
        "number",
        "issue_date",
        "expiry_date",
        "target_market",
        "file_path",
        "verification_status",
        "notes",
    ):
        if key in values:
            setattr(cert, key, values[key])
    if cert.issue_date and cert.expiry_date and cert.expiry_date < cert.issue_date:
        raise ValidationError("Expiry date is before issue date", key="error.date_range")
    cert.status = values.get("status") or certificate_status(cert.expiry_date)
    session.flush()
    audit_service.record(
        session,
        action=action,
        entity_type="certificate",
        entity_id=cert.id,
        summary=f"Certificate {cert.name} {action}d",
        user_id=actor.id,
        username=actor.username,
    )
    return cert


def archive_certificate(
    session: Session, actor: CurrentUser, cert_id: int, reason: str = ""
) -> None:
    """Archive a certificate and log the file removal."""
    actor.require("certificate.edit")
    cert = session.get(Certificate, cert_id)
    if cert is None:
        raise NotFoundError("Certificate not found")
    cert.is_archived = True
    cert.archive_reason = reason or None
    session.flush()
    audit_service.record(
        session,
        action="archive",
        entity_type="certificate",
        entity_id=cert.id,
        summary=f"Certificate {cert.name} archived (file: {cert.file_path or '-'})",
        user_id=actor.id,
        username=actor.username,
    )


def missing_certificates(session: Session, product_ids: list[int], required: str) -> list[str]:
    """Return required certificate names that are missing or expired.

    ``required`` is a free-form, comma separated requirement string coming from
    the RFQ or the buyer, e.g. ``"Halal, Certificate of Origin"``.
    """
    wanted = [part.strip().lower() for part in (required or "").split(",") if part.strip()]
    if not wanted:
        return []
    rows = (
        session.scalars(
            select(Certificate).where(
                Certificate.is_archived.is_(False),
                (
                    Certificate.product_id.in_(product_ids)
                    if product_ids
                    else Certificate.id.is_not(None)
                ),
            )
        )
        .unique()
        .all()
    )
    available: list[tuple[str, str]] = []
    for cert in rows:
        status = certificate_status(cert.expiry_date)
        available.append((f"{cert.name} {cert.cert_type}".lower(), status))

    missing: list[str] = []
    for want in wanted:
        matched = [status for text, status in available if want in text]
        if not matched:
            missing.append(want)
        elif all(status == "expired" for status in matched):
            missing.append(f"{want} (expired)")
    return missing


# ------------------------------------------------------------------ documents
def list_documents(
    session: Session,
    *,
    buyer_id: int | None = None,
    lead_id: int | None = None,
    shipment_id: int | None = None,
    doc_type: str | None = None,
) -> list[dict]:
    """Filtered document register."""
    stmt = select(Document).where(Document.is_archived.is_(False))
    if buyer_id:
        stmt = stmt.where(Document.buyer_id == buyer_id)
    if lead_id:
        stmt = stmt.where(Document.lead_id == lead_id)
    if shipment_id:
        stmt = stmt.where(Document.shipment_id == shipment_id)
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    rows = session.scalars(stmt.order_by(Document.id.desc())).unique().all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "doc_type": row.doc_type,
            "buyer_id": row.buyer_id,
            "lead_id": row.lead_id,
            "shipment_id": row.shipment_id,
            "doc_date": row.doc_date,
            "file_path": row.file_path or "",
            "status": row.status,
            "notes": row.notes or "",
        }
        for row in rows
    ]


def save_document(session: Session, actor: CurrentUser, values: dict) -> Document:
    """Create or update an export document entry."""
    actor.require("certificate.edit")
    doc_id = values.get("id")
    if doc_id:
        doc = session.get(Document, doc_id)
        if doc is None:
            raise NotFoundError("Document not found")
    else:
        doc = Document(title=values.get("title") or "Document")
        session.add(doc)
    for key in (
        "title",
        "doc_type",
        "buyer_id",
        "lead_id",
        "shipment_id",
        "quotation_id",
        "contract_id",
        "file_path",
        "doc_date",
        "status",
        "notes",
    ):
        if key in values:
            setattr(doc, key, values[key])
    session.flush()
    audit_service.record(
        session,
        action="update" if doc_id else "create",
        entity_type="document",
        entity_id=doc.id,
        summary=f"Document {doc.title}",
        user_id=actor.id,
        username=actor.username,
    )
    return doc


# ---------------------------------------------------------------- attachments
def store_file(source: str | Path, subfolder: str = "") -> str:
    """Copy a user-selected file into the managed attachments directory."""
    source_path = Path(source)
    if not source_path.exists():
        raise ValidationError("File not found", key="error.file_missing")
    target_dir = PATHS.attachments_dir / subfolder if subfolder else PATHS.attachments_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source_path.name
    counter = 1
    while target.exists():
        target = target_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
        counter += 1
    shutil.copy2(source_path, target)
    return str(target)


def add_attachment(
    session: Session,
    actor: CurrentUser,
    entity_type: str,
    entity_id: int,
    file_path: str | Path,
    description: str = "",
) -> Attachment:
    """Copy and register a file attached to any entity."""
    stored = store_file(file_path, subfolder=entity_type)
    path = Path(stored)
    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        file_name=path.name,
        file_path=stored,
        size_bytes=path.stat().st_size,
        description=description or None,
    )
    session.add(attachment)
    session.flush()
    audit_service.record(
        session,
        action="create",
        entity_type="attachment",
        entity_id=attachment.id,
        summary=f"File '{path.name}' attached to {entity_type} #{entity_id}",
        user_id=actor.id,
        username=actor.username,
    )
    return attachment


def list_attachments(session: Session, entity_type: str, entity_id: int) -> list[dict]:
    """Attachments of one entity."""
    rows = session.scalars(
        select(Attachment)
        .where(Attachment.entity_type == entity_type, Attachment.entity_id == entity_id)
        .order_by(Attachment.id.desc())
    ).all()
    return [
        {
            "id": row.id,
            "file_name": row.file_name,
            "file_path": row.file_path,
            "size_bytes": row.size_bytes,
            "description": row.description or "",
            "created_at": row.created_at,
        }
        for row in rows
    ]


def delete_attachment(session: Session, actor: CurrentUser, attachment_id: int) -> None:
    """Remove an attachment record and audit the deletion."""
    attachment = session.get(Attachment, attachment_id)
    if attachment is None:
        return
    audit_service.record(
        session,
        action="delete",
        entity_type="attachment",
        entity_id=attachment.id,
        summary=f"Attachment '{attachment.file_name}' deleted",
        details={"path": attachment.file_path},
        user_id=actor.id,
        username=actor.username,
    )
    session.delete(attachment)
    session.flush()


def certificate_register_rows(session: Session) -> list[dict]:
    """Rows for the certificate expiry report."""
    return [
        {
            **row,
            "alert": (
                "expired"
                if (row["days_left"] is not None and row["days_left"] < 0)
                else ("soon" if (row["days_left"] is not None and row["days_left"] <= 60) else "ok")
            ),
        }
        for row in list_certificates(session)
    ]


def today_str() -> str:
    """Small helper used by report headers."""
    return today().strftime("%d.%m.%Y")
