"""Email composition, sending through the active provider and follow-up lists."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.email.providers import OutgoingEmail
from app.models import Buyer, EmailMessage, EmailTemplate, Quotation
from app.services import audit_service, company_service, integration_service, task_service
from app.services.auth_service import CurrentUser
from app.utils.errors import NotFoundError, ValidationError
from app.utils.formatting import now, today


def list_templates(session: Session, language: str | None = None) -> list[dict]:
    """Available email templates."""
    stmt = select(EmailTemplate).where(EmailTemplate.is_archived.is_(False))
    if language:
        stmt = stmt.where(EmailTemplate.language == language)
    return [
        {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "language": row.language,
            "subject": row.subject,
            "body": row.body,
            "purpose": row.purpose,
        }
        for row in session.scalars(stmt.order_by(EmailTemplate.name)).unique().all()
    ]


def save_template(session: Session, actor: CurrentUser, values: dict) -> EmailTemplate:
    """Create or update an email template."""
    actor.require("settings.edit")
    template_id = values.get("id")
    if template_id:
        template = session.get(EmailTemplate, template_id)
        if template is None:
            raise NotFoundError("Template not found")
    else:
        code = (values.get("code") or "").strip()
        if not code:
            raise ValidationError("Template code is required", key="error.code_required")
        template = EmailTemplate(code=code, name=values.get("name") or code)
        session.add(template)
    for key in ("code", "name", "language", "subject", "body", "purpose"):
        if key in values:
            setattr(template, key, values[key])
    session.flush()
    return template


def render_template(session: Session, template_id: int, context: dict) -> dict:
    """Substitute ``{placeholders}`` in a template's subject and body."""
    template = session.get(EmailTemplate, template_id)
    if template is None:
        raise NotFoundError("Template not found")

    def _fill(text: str) -> str:
        result = text
        for key, value in context.items():
            result = result.replace("{" + key + "}", "" if value is None else str(value))
        return result

    return {"subject": _fill(template.subject), "body": _fill(template.body)}


def template_context(
    session: Session, buyer_id: int | None, quotation_id: int | None, sender: str
) -> dict:
    """Build the placeholder context available to templates."""
    company = company_service.company_dict(session)
    context = {
        "company": company.get("name", ""),
        "company_phone": company.get("phone", ""),
        "company_email": company.get("email", ""),
        "company_website": company.get("website", ""),
        "sender": sender,
        "date": today().strftime("%d.%m.%Y"),
        "buyer": "",
        "contact": "",
        "country": "",
        "quotation_number": "",
        "quotation_total": "",
        "valid_until": "",
    }
    if buyer_id:
        buyer = session.get(Buyer, buyer_id)
        if buyer is not None:
            context.update(
                {
                    "buyer": buyer.company_name,
                    "contact": buyer.contact_person or "Sir/Madam",
                    "country": buyer.country,
                }
            )
    if quotation_id:
        quotation = session.get(Quotation, quotation_id)
        if quotation is not None:
            context.update(
                {
                    "quotation_number": quotation.number,
                    "quotation_total": f"{quotation.grand_total:,.2f} {quotation.currency}",
                    "valid_until": (
                        quotation.valid_until.strftime("%d.%m.%Y") if quotation.valid_until else ""
                    ),
                }
            )
    return context


def save_draft(session: Session, actor: CurrentUser, values: dict) -> EmailMessage:
    """Store an email draft."""
    actor.require("email.send")
    message_id = values.get("id")
    if message_id:
        message = session.get(EmailMessage, message_id)
        if message is None:
            raise NotFoundError("Message not found")
    else:
        message = EmailMessage(user_id=actor.id)
        session.add(message)
    for key in (
        "subject",
        "body",
        "to_address",
        "cc_address",
        "buyer_id",
        "lead_id",
        "quotation_id",
        "template_id",
        "attachment_path",
    ):
        if key in values:
            setattr(message, key, values[key])
    message.status = "draft"
    session.flush()
    return message


def send(session: Session, actor: CurrentUser, message_id: int) -> EmailMessage:
    """Send a draft through the active email provider.

    A provider failure is recorded on the message instead of raising, so the
    user always sees what happened and can retry.
    """
    actor.require("email.send")
    message = session.get(EmailMessage, message_id)
    if message is None:
        raise NotFoundError("Message not found")
    if not message.to_address:
        raise ValidationError("Recipient address is required", key="error.email_to_required")

    provider = integration_service.build_provider(session, "email")
    attachments = [message.attachment_path] if message.attachment_path else []
    result = provider.send(
        OutgoingEmail(
            to_address=message.to_address,
            subject=message.subject,
            body=message.body,
            cc_address=message.cc_address or "",
            attachments=attachments,
        )
    )
    message.provider = provider.code
    if result.ok:
        message.status = "sent"
        message.sent_at = now()
        message.error_message = None
    else:
        message.status = "failed"
        message.error_message = result.message
    session.flush()

    audit_service.record(
        session,
        action="send",
        entity_type="email",
        entity_id=message.id,
        summary=f"Email to {message.to_address}: {message.status}",
        user_id=actor.id,
        username=actor.username,
    )
    if message.buyer_id:
        audit_service.add_activity(
            session,
            entity_type="buyer",
            entity_id=message.buyer_id,
            kind="email",
            title=f"Email: {message.subject}",
            body=message.body[:2000],
            user_id=actor.id,
        )
    if message.lead_id:
        audit_service.add_activity(
            session,
            entity_type="lead",
            entity_id=message.lead_id,
            kind="email",
            title=f"Email: {message.subject}",
            user_id=actor.id,
        )
    if result.ok:
        task_service.create_task(
            session,
            title=f"Follow up: {message.subject}",
            rule_code="email.followup",
            entity_type="email",
            entity_id=message.id,
            buyer_id=message.buyer_id,
            lead_id=message.lead_id,
            assignee_id=actor.id,
            due_date=today() + dt.timedelta(days=task_service.FOLLOW_UP_AFTER_QUOTATION_DAYS),
        )
    integration_service.append_sync_log(
        session, "email", provider.code, f"{message.to_address} -> {message.status}"
    )
    return message


def list_messages(
    session: Session,
    *,
    buyer_id: int | None = None,
    lead_id: int | None = None,
    status: str | None = None,
    limit: int = 300,
) -> list[dict]:
    """Email history."""
    stmt = select(EmailMessage).where(EmailMessage.is_archived.is_(False))
    if buyer_id:
        stmt = stmt.where(EmailMessage.buyer_id == buyer_id)
    if lead_id:
        stmt = stmt.where(EmailMessage.lead_id == lead_id)
    if status:
        stmt = stmt.where(EmailMessage.status == status)
    rows = session.scalars(stmt.order_by(EmailMessage.id.desc()).limit(limit)).unique().all()
    buyers = {b.id: b.company_name for b in session.scalars(select(Buyer)).unique().all()}
    return [
        {
            "id": row.id,
            "subject": row.subject,
            "to_address": row.to_address,
            "buyer_id": row.buyer_id,
            "buyer": buyers.get(row.buyer_id, ""),
            "lead_id": row.lead_id,
            "quotation_id": row.quotation_id,
            "status": row.status,
            "provider": row.provider or "",
            "sent_at": row.sent_at,
            "reply_received_at": row.reply_received_at,
            "error_message": row.error_message or "",
            "body": row.body,
            "attachment_path": row.attachment_path or "",
        }
        for row in rows
    ]


def mark_reply_received(session: Session, actor: CurrentUser, message_id: int) -> EmailMessage:
    """Record that the buyer answered a message."""
    message = session.get(EmailMessage, message_id)
    if message is None:
        raise NotFoundError("Message not found")
    message.reply_received_at = now()
    session.flush()
    return message


def awaiting_reply(session: Session, days: int = 3) -> list[dict]:
    """Sent messages older than ``days`` that never received a reply."""
    cutoff = now() - dt.timedelta(days=days)
    rows = (
        session.scalars(
            select(EmailMessage).where(
                EmailMessage.is_archived.is_(False),
                EmailMessage.status == "sent",
                EmailMessage.reply_received_at.is_(None),
                EmailMessage.sent_at.is_not(None),
            )
        )
        .unique()
        .all()
    )
    buyers = {b.id: b.company_name for b in session.scalars(select(Buyer)).unique().all()}
    result = []
    for row in rows:
        sent_at = row.sent_at
        if sent_at is not None and sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=cutoff.tzinfo)
        if sent_at is None or sent_at > cutoff:
            continue
        result.append(
            {
                "id": row.id,
                "subject": row.subject,
                "buyer": buyers.get(row.buyer_id, ""),
                "buyer_id": row.buyer_id,
                "lead_id": row.lead_id,
                "to_address": row.to_address,
                "sent_at": row.sent_at,
                "days_waiting": (now() - sent_at).days,
            }
        )
    return sorted(result, key=lambda item: item["days_waiting"], reverse=True)
