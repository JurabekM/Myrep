"""Work stages, automatic delay detection and the daily site log."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.database.session import session_scope
from app.models.entities import User, WorkStage
from app.models.enums import StageStatus
from app.repositories import Repositories
from app.services import audit_service
from app.services.auth_service import CurrentUser
from app.services.permissions import Perm, require

#: Statuses that are never overwritten by the delay detector.
_TERMINAL = (StageStatus.DONE.value, StageStatus.BLOCKED.value)


def refresh_delays(session: Session, project_id: int, today: date | None = None) -> int:
    """Mark stages whose planned finish has passed while progress is below 100%.

    Returns the number of stages whose status changed.
    """
    today = today or date.today()
    changed = 0
    for stage in Repositories(session).stages.for_project(project_id):
        if stage.status in _TERMINAL:
            continue
        overdue = bool(stage.plan_end and stage.plan_end < today)
        incomplete = (stage.progress_percent or 0.0) < 100.0
        if overdue and incomplete and stage.status != StageStatus.DELAYED.value:
            stage.status = StageStatus.DELAYED.value
            changed += 1
        elif not overdue and stage.status == StageStatus.DELAYED.value:
            stage.status = (
                StageStatus.IN_PROGRESS.value
                if (stage.progress_percent or 0.0) > 0
                else StageStatus.NOT_STARTED.value
            )
            changed += 1
    session.flush()
    return changed


def list_stages(project_id: int, status: str = "", text: str = "") -> list[dict]:
    """Return the work stages of a project (delays refreshed first)."""
    with session_scope() as session:
        refresh_delays(session, project_id)
        repos = Repositories(session)
        rows = []
        for stage in repos.stages.for_project(project_id):
            if status and stage.status != status:
                continue
            if text and text.lower() not in stage.name.lower():
                continue
            rows.append(
                {
                    "id": stage.id,
                    "name": stage.name,
                    "section_id": stage.section_id,
                    "section": _section_name(session, stage.section_id),
                    "plan_start": stage.plan_start,
                    "plan_end": stage.plan_end,
                    "actual_start": stage.actual_start,
                    "actual_end": stage.actual_end,
                    "progress_percent": stage.progress_percent or 0.0,
                    "responsible": stage.responsible.label if stage.responsible else "",
                    "responsible_id": stage.responsible_id,
                    "status": stage.status,
                    "dependencies": stage.dependencies or "",
                    "note": stage.note or "",
                    "order_index": stage.order_index or 0,
                }
            )
        return rows


def _section_name(session: Session, section_id: int | None) -> str:
    if not section_id:
        return ""
    section = Repositories(session).sections.get(section_id)
    return section.name if section else ""


def stage_choices(project_id: int) -> list[tuple[int | str, str]]:
    """Return ``[(id, name)]`` pairs for stage pickers."""
    with session_scope() as session:
        rows = [(s.id, s.name) for s in Repositories(session).stages.for_project(project_id)]
    return [("", "—")] + rows


def save_stage(data: dict, actor: CurrentUser, stage_id: int | None = None) -> int:
    """Create or update a work stage."""
    require(actor.role_code, Perm.STAGE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        if stage_id:
            stage = repos.stages.get_or_raise(stage_id)
            before = f"{stage.status}/{stage.progress_percent}"
            repos.stages.update(stage, **data)
            action = audit_service.Action.UPDATE
        else:
            data.setdefault(
                "order_index",
                repos.stages.count(filters=[WorkStage.project_id == data["project_id"]]),
            )
            stage = repos.stages.create(**data)
            before = ""
            action = audit_service.Action.CREATE
        refresh_delays(session, stage.project_id)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=action,
            entity_type="WorkStage",
            entity_id=stage.id,
            project_id=stage.project_id,
            description=stage.name,
            old_value=before,
            new_value=f"{stage.status}/{stage.progress_percent}",
        )
        return stage.id


def delete_stage(stage_id: int, actor: CurrentUser) -> None:
    """Archive a work stage (soft delete)."""
    require(actor.role_code, Perm.STAGE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        stage = repos.stages.get_or_raise(stage_id)
        repos.stages.archive(stage, True)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.ARCHIVE,
            entity_type="WorkStage",
            entity_id=stage_id,
            project_id=stage.project_id,
            description=stage.name,
        )


def move_stage(stage_id: int, direction: int, actor: CurrentUser) -> None:
    """Reorder a stage in the timeline."""
    require(actor.role_code, Perm.STAGE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        stage = repos.stages.get_or_raise(stage_id)
        stages = repos.stages.for_project(stage.project_id)
        index = next((i for i, s in enumerate(stages) if s.id == stage_id), None)
        if index is None:
            return
        new_index = max(0, min(index + direction, len(stages) - 1))
        stages.insert(new_index, stages.pop(index))
        for position, item in enumerate(stages):
            item.order_index = position
        session.flush()


# --------------------------------------------------------------------------- #
# Daily site log
# --------------------------------------------------------------------------- #


def list_logs(project_id: int, stage_id: int | None = None) -> list[dict]:
    """Return daily site log entries."""
    with session_scope() as session:
        repos = Repositories(session)
        rows = []
        for entry in repos.logs.for_project(project_id):
            if stage_id and entry.stage_id != stage_id:
                continue
            rows.append(
                {
                    "id": entry.id,
                    "log_date": entry.log_date,
                    "stage_id": entry.stage_id,
                    "stage": entry.stage.name if entry.stage else "",
                    "work_done": entry.work_done or "",
                    "progress_percent": entry.progress_percent or 0.0,
                    "workers_count": entry.workers_count or 0,
                    "issue": entry.issue or "",
                    "photo_path": entry.photo_path or "",
                    "author": entry.author.label if entry.author else "",
                }
            )
        return rows


def save_log(data: dict, actor: CurrentUser, log_id: int | None = None) -> int:
    """Create or update a site log entry; propagates progress to the stage."""
    require(actor.role_code, Perm.STAGE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        if log_id:
            entry = repos.logs.get_or_raise(log_id)
            repos.logs.update(entry, **data)
        else:
            entry = repos.logs.create(author_id=actor.id, **data)
        if entry.stage_id:
            stage = repos.stages.get(entry.stage_id)
            if stage is not None and (entry.progress_percent or 0) > (stage.progress_percent or 0):
                stage.progress_percent = entry.progress_percent
                if stage.progress_percent >= 100:
                    stage.status = StageStatus.DONE.value
                    stage.actual_end = stage.actual_end or entry.log_date
                elif stage.status == StageStatus.NOT_STARTED.value:
                    stage.status = StageStatus.IN_PROGRESS.value
                    stage.actual_start = stage.actual_start or entry.log_date
        refresh_delays(session, entry.project_id)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.UPDATE if log_id else audit_service.Action.CREATE,
            entity_type="DailySiteLog",
            entity_id=entry.id,
            project_id=entry.project_id,
            description=(entry.work_done or "")[:80],
        )
        return entry.id


def delete_log(log_id: int, actor: CurrentUser) -> None:
    """Remove a site log entry."""
    require(actor.role_code, Perm.STAGE_EDIT)
    with session_scope() as session:
        repos = Repositories(session)
        entry = repos.logs.get_or_raise(log_id)
        project_id = entry.project_id
        repos.logs.delete(entry)
        audit_service.log(
            session,
            user=session.get(User, actor.id),
            action=audit_service.Action.DELETE,
            entity_type="DailySiteLog",
            entity_id=log_id,
            project_id=project_id,
            description="site log removed",
        )


def delayed_stages(project_id: int | None = None) -> list[dict]:
    """Return every delayed stage, optionally limited to one project."""
    with session_scope() as session:
        repos = Repositories(session)
        projects = (
            [repos.projects.get_or_raise(project_id)] if project_id else repos.projects.list()
        )
        rows = []
        for project in projects:
            refresh_delays(session, project.id)
            for stage in repos.stages.for_project(project.id):
                if stage.status != StageStatus.DELAYED.value:
                    continue
                overdue = (date.today() - stage.plan_end).days if stage.plan_end else 0
                rows.append(
                    {
                        "id": stage.id,
                        "project": project.name,
                        "project_id": project.id,
                        "name": stage.name,
                        "plan_end": stage.plan_end,
                        "progress_percent": stage.progress_percent or 0.0,
                        "overdue_days": overdue,
                        "responsible": stage.responsible.label if stage.responsible else "",
                    }
                )
        return rows


def stage_gantt_rows(project_id: int) -> list[dict]:
    """Return the minimal payload used by the Gantt widget."""
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "start": row["plan_start"],
            "end": row["plan_end"],
            "actual_start": row["actual_start"],
            "actual_end": row["actual_end"],
            "progress": row["progress_percent"],
            "status": row["status"],
        }
        for row in list_stages(project_id)
    ]
