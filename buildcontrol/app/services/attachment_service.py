"""Document attachments for any entity."""

from __future__ import annotations

from app.database.session import session_scope
from app.models.entities import User
from app.repositories import Repositories
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.utils.files import store_file


def list_attachments(entity_type: str, entity_id: int) -> list[dict]:
    """Return attachments linked to an entity."""
    with session_scope() as session:
        return [
            {
                "id": a.id,
                "title": a.title or "",
                "file_path": a.file_path,
                "created_at": a.created_at,
                "user": a.user.label if a.user else "",
            }
            for a in Repositories(session).attachments.for_entity(entity_type, entity_id)
        ]


def attach(
    entity_type: str,
    entity_id: int,
    source_path: str,
    actor: CurrentUser,
    title: str = "",
    copy: bool = True,
    project_id: int | None = None,
) -> int:
    """Attach a file, copying it into the managed storage by default."""
    stored = store_file(source_path, entity_type) if copy else source_path
    with session_scope() as session:
        repos = Repositories(session)
        attachment = repos.attachments.create(
            entity_type=entity_type,
            entity_id=entity_id,
            title=title or stored.rsplit("\\", 1)[-1],
            file_path=stored,
            user_id=actor.id,
        )
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.CREATE,
            entity_type="Attachment",
            entity_id=attachment.id,
            project_id=project_id,
            description=f"{entity_type}#{entity_id}: {attachment.title}",
        )
        return attachment.id


def remove(attachment_id: int, actor: CurrentUser) -> None:
    """Detach a file (the stored copy stays on disk)."""
    with session_scope() as session:
        repos = Repositories(session)
        attachment = repos.attachments.get_or_raise(attachment_id)
        title = attachment.title
        repos.attachments.delete(attachment)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.DELETE,
            entity_type="Attachment",
            entity_id=attachment_id,
            description=title,
        )
