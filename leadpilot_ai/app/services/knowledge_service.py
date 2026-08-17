"""Knowledge base management and retrieval for the AI agent."""

from __future__ import annotations

import logging
import shutil
from datetime import date
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import load_config
from app.database.engine import session_scope
from app.models.enums import KBItemType
from app.models.enums import Permission as Perm
from app.models.intelligence import KnowledgeBaseAttachment, KnowledgeBaseItem
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.dates import today

logger = logging.getLogger(__name__)


class KnowledgeError(Exception):
    """Knowledge base rule violation (``code`` is an i18n key)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def list_items(
    *,
    search: str = "",
    item_type: str = "",
    category: str = "",
    only_ai_usable: bool = False,
    include_archived: bool = False,
) -> list[KnowledgeBaseItem]:
    """Filtered knowledge base listing."""
    with session_scope() as session:
        stmt = select(KnowledgeBaseItem)
        if not include_archived:
            stmt = stmt.where(KnowledgeBaseItem.is_archived.is_(False))
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    KnowledgeBaseItem.title.ilike(pattern),
                    KnowledgeBaseItem.title_ru.ilike(pattern),
                    KnowledgeBaseItem.body.ilike(pattern),
                    KnowledgeBaseItem.body_ru.ilike(pattern),
                    KnowledgeBaseItem.keywords.ilike(pattern),
                    KnowledgeBaseItem.tags.ilike(pattern),
                )
            )
        if item_type:
            stmt = stmt.where(KnowledgeBaseItem.item_type == item_type)
        if category:
            stmt = stmt.where(KnowledgeBaseItem.category == category)
        if only_ai_usable:
            stmt = stmt.where(KnowledgeBaseItem.ai_usable.is_(True))
        stmt = stmt.order_by(KnowledgeBaseItem.priority.desc(), KnowledgeBaseItem.updated_at.desc())
        return list(session.execute(stmt).scalars().unique().all())


def get_item(item_id: int) -> KnowledgeBaseItem | None:
    """Load one knowledge base item."""
    with session_scope() as session:
        return session.get(KnowledgeBaseItem, item_id)


def save_item(
    *,
    actor: CurrentUser,
    item_id: int | None = None,
    company_id: int = 1,
    item_type: str = KBItemType.FAQ,
    category: str = "",
    title: str,
    title_ru: str = "",
    body: str = "",
    body_ru: str = "",
    keywords: str = "",
    tags: str = "",
    service_id: int | None = None,
    branch_id: int | None = None,
    price: float | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
    ai_usable: bool = True,
    priority: int = 0,
) -> KnowledgeBaseItem:
    """Create or update a knowledge base article."""
    actor.require(Perm.KB_MANAGE)
    if not title.strip():
        raise KnowledgeError("kb_title_required")
    if valid_from and valid_to and valid_to < valid_from:
        raise KnowledgeError("kb_invalid_dates")
    with session_scope() as session:
        if item_id:
            item = session.get(KnowledgeBaseItem, item_id)
            if item is None:
                raise KnowledgeError("kb_not_found")
            old = item.title
        else:
            item = KnowledgeBaseItem(company_id=company_id, title=title)
            session.add(item)
            old = ""
        item.item_type = item_type
        item.category = category.strip()
        item.title = title.strip()
        item.title_ru = title_ru.strip()
        item.body = body
        item.body_ru = body_ru
        item.keywords = keywords
        item.tags = tags
        item.service_id = service_id
        item.branch_id = branch_id
        item.price = price
        item.valid_from = valid_from
        item.valid_to = valid_to
        item.ai_usable = ai_usable
        item.priority = priority
        item.updated_by_id = actor.id
        session.flush()
        audit_service.record(
            session,
            action="kb_saved",
            entity_type="kb_item",
            entity_id=item.id,
            entity_label=item.title,
            old_value=old,
            new_value=item.title,
            user_id=actor.id,
            username=actor.username,
        )
        return item


def archive_item(item_id: int, *, actor: CurrentUser) -> None:
    """Archive a knowledge base item."""
    actor.require(Perm.KB_MANAGE)
    with session_scope() as session:
        item = session.get(KnowledgeBaseItem, item_id)
        if item is None:
            raise KnowledgeError("kb_not_found")
        item.is_archived = True
        audit_service.record(
            session,
            action="kb_archived",
            entity_type="kb_item",
            entity_id=item.id,
            entity_label=item.title,
            user_id=actor.id,
            username=actor.username,
        )


def toggle_ai_usable(item_id: int, value: bool, *, actor: CurrentUser) -> None:
    """Allow or forbid the AI to quote this item."""
    actor.require(Perm.KB_MANAGE)
    with session_scope() as session:
        item = session.get(KnowledgeBaseItem, item_id)
        if item is None:
            raise KnowledgeError("kb_not_found")
        item.ai_usable = value


def add_attachment(item_id: int, file_path: str, *, actor: CurrentUser) -> KnowledgeBaseAttachment:
    """Copy a document into the data directory and link it to the item."""
    actor.require(Perm.KB_MANAGE)
    source = Path(file_path)
    if not source.exists():
        raise KnowledgeError("file_not_found")
    target_dir = load_config().attachments_dir / "kb"
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / f"kb{item_id}_{source.name}"
    shutil.copy2(source, destination)
    text = _extract_text(destination)
    with session_scope() as session:
        item = session.get(KnowledgeBaseItem, item_id)
        if item is None:
            raise KnowledgeError("kb_not_found")
        attachment = KnowledgeBaseAttachment(
            item_id=item_id,
            file_name=source.name,
            file_path=str(destination),
            size_bytes=destination.stat().st_size,
            extracted_text=text[:20000],
        )
        session.add(attachment)
        session.flush()
        return attachment


def _extract_text(path: Path) -> str:
    """Best-effort plain text extraction from TXT / PDF / DOCX."""
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".csv"}:
            return path.read_text(encoding="utf-8", errors="replace")
        if suffix == ".pdf":
            from pypdf import PdfReader  # type: ignore[import-not-found]

            reader = PdfReader(str(path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if suffix == ".docx":
            import xml.etree.ElementTree as ET
            import zipfile

            with zipfile.ZipFile(path) as archive:
                xml_bytes = archive.read("word/document.xml")
            root = ET.fromstring(xml_bytes)
            namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            return " ".join(node.text or "" for node in root.iter(f"{namespace}t"))
    except Exception as exc:  # pragma: no cover - optional dependency / broken file
        logger.info("KB text extraction skipped for %s: %s", path.name, type(exc).__name__)
    return ""


# --------------------------------------------------------------------------- #
# Retrieval for the AI agent
# --------------------------------------------------------------------------- #
def retrieve(
    session: Session,
    keywords: list[str],
    *,
    language: str = "uz",
    limit: int = 6,
    reference_day: date | None = None,
) -> list[str]:
    """Return approved, currently valid knowledge snippets ranked by relevance."""
    day = reference_day or today()
    stmt = select(KnowledgeBaseItem).where(
        KnowledgeBaseItem.is_archived.is_(False), KnowledgeBaseItem.ai_usable.is_(True)
    )
    items = list(session.execute(stmt).scalars().unique().all())
    scored: list[tuple[int, str]] = []
    for item in items:
        if not item.is_valid_on(day):
            continue
        haystack = " ".join(
            [item.title, item.title_ru, item.body, item.body_ru, item.keywords, item.tags]
        ).lower()
        hits = sum(1 for word in keywords if word and word in haystack)
        hits += item.priority
        if hits <= 0:
            continue
        body = item.body_ru if language == "ru" and item.body_ru else item.body
        title = item.title_ru if language == "ru" and item.title_ru else item.title
        scored.append((hits, f"{title}: {body}".strip()))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [text for _, text in scored[:limit]]


def active_promos(
    session: Session, language: str = "uz", reference_day: date | None = None
) -> list[str]:
    """Currently valid promotions the AI may mention."""
    day = reference_day or today()
    stmt = select(KnowledgeBaseItem).where(
        KnowledgeBaseItem.is_archived.is_(False),
        KnowledgeBaseItem.ai_usable.is_(True),
        KnowledgeBaseItem.item_type == KBItemType.PROMO,
    )
    result: list[str] = []
    for item in session.execute(stmt).scalars().unique().all():
        if not item.is_valid_on(day):
            continue
        title = item.title_ru if language == "ru" and item.title_ru else item.title
        body = item.body_ru if language == "ru" and item.body_ru else item.body
        result.append(f"{title} — {body}".strip(" —"))
    return result


def categories() -> list[str]:
    """Distinct categories used by the filter combo."""
    with session_scope() as session:
        rows = session.execute(
            select(KnowledgeBaseItem.category)
            .where(KnowledgeBaseItem.category != "")
            .distinct()
            .order_by(KnowledgeBaseItem.category)
        ).all()
        return [row[0] for row in rows]
