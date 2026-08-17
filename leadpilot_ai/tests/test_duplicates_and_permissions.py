"""Duplicate detection, lead merging and role-based access control."""

from __future__ import annotations

import pytest

from app.models.enums import Permission as Perm
from app.models.enums import RoleName
from app.services import lead_service
from app.services.auth_service import PermissionDenied
from app.utils.formatting import normalize_phone


# --------------------------------------------------------------------------- #
# Phone normalisation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+998901234567", "+998901234567"),
        ("998901234567", "+998901234567"),
        ("901234567", "+998901234567"),
        ("90 123 45 67", "+998901234567"),
        ("+998 (90) 123-45-67", "+998901234567"),
        ("00998901234567", "+998901234567"),
        ("", None),
        (None, None),
    ],
)
def test_phone_normalisation(raw, expected) -> None:
    """Different notations collapse to one canonical form."""
    assert normalize_phone(raw) == expected


# --------------------------------------------------------------------------- #
# Duplicates
# --------------------------------------------------------------------------- #
def test_duplicate_is_found_by_phone(admin) -> None:
    """Two leads with the same number are reported as duplicates."""
    first = lead_service.create_lead(actor=admin, full_name="Dup One", phone="+998905550001")
    second = lead_service.create_lead(actor=admin, full_name="Dup Two", phone="90 555 00 01")
    duplicates = lead_service.find_duplicates(second.id)
    assert first.id in [lead.id for lead in duplicates]


def test_duplicate_is_found_by_telegram_username(admin) -> None:
    """Telegram usernames are matched case-insensitively."""
    first = lead_service.create_lead(
        actor=admin, full_name="TG One", telegram_username="Sample_User"
    )
    second = lead_service.create_lead(
        actor=admin, full_name="TG Two", telegram_username="sample_user"
    )
    duplicates = lead_service.find_duplicates(second.id)
    assert first.id in [lead.id for lead in duplicates]


def test_merge_moves_history_and_archives_the_duplicate(admin) -> None:
    """Merging keeps the primary lead and archives the duplicate reversibly."""
    primary = lead_service.create_lead(
        actor=admin, full_name="Merge Primary", phone="+998905550002"
    )
    duplicate = lead_service.create_lead(
        actor=admin, full_name="", phone="+998905550002", email="dup@example.com"
    )
    merged = lead_service.merge_leads(primary.id, duplicate.id, actor=admin)
    assert merged.email == "dup@example.com"

    archived = lead_service.get_lead(duplicate.id)
    assert archived.is_archived is True
    assert archived.merged_into_id == primary.id


def test_merge_is_reversible(admin) -> None:
    """An administrator can undo a merge."""
    primary = lead_service.create_lead(actor=admin, full_name="Unmerge A", phone="+998905550003")
    duplicate = lead_service.create_lead(actor=admin, full_name="Unmerge B", phone="+998905550003")
    lead_service.merge_leads(primary.id, duplicate.id, actor=admin)
    restored = lead_service.unmerge_lead(duplicate.id, actor=admin)
    assert restored.is_archived is False
    assert restored.merged_into_id is None


def test_merging_a_lead_with_itself_is_refused(admin) -> None:
    """Self-merge is a programming error and is rejected."""
    lead = lead_service.create_lead(actor=admin, full_name="Self Merge")
    with pytest.raises(lead_service.LeadError) as exc:
        lead_service.merge_leads(lead.id, lead.id, actor=admin)
    assert exc.value.code == "merge_same_lead"


# --------------------------------------------------------------------------- #
# Permissions
# --------------------------------------------------------------------------- #
def test_admin_has_every_permission(admin) -> None:
    """The administrator role is unrestricted."""
    assert admin.role == RoleName.ADMIN
    assert admin.can(Perm.SETTINGS_MANAGE)
    assert admin.can(Perm.USER_MANAGE)
    assert admin.can(Perm.LEAD_MERGE)


def test_operator_cannot_manage_settings(operator) -> None:
    """Operators are limited to their daily work."""
    assert operator.can(Perm.CONVERSATION_REPLY)
    assert not operator.can(Perm.SETTINGS_MANAGE)
    assert not operator.can(Perm.USER_MANAGE)
    assert not operator.can(Perm.LEAD_VIEW_ALL)
    with pytest.raises(PermissionDenied):
        operator.require(Perm.SETTINGS_MANAGE)


def test_viewer_is_read_only(viewer) -> None:
    """The viewer role may not reply or edit."""
    assert viewer.can(Perm.CONVERSATION_VIEW)
    assert not viewer.can(Perm.CONVERSATION_REPLY)
    assert not viewer.can(Perm.LEAD_EDIT)


def test_operator_cannot_edit_another_operators_lead(admin, operator, second_operator) -> None:
    """Ownership is enforced on lead updates."""
    lead = lead_service.create_lead(
        actor=admin, full_name="Owned Lead", owner_id=second_operator.id
    )
    with pytest.raises(lead_service.LeadError) as exc:
        lead_service.update_lead(lead.id, actor=operator, full_name="Hacked")
    assert exc.value.code == "no_permission_other_lead"


def test_operator_can_edit_their_own_lead(admin, operator) -> None:
    """An operator may edit the leads assigned to them."""
    lead = lead_service.create_lead(actor=admin, full_name="Own Lead", owner_id=operator.id)
    updated = lead_service.update_lead(lead.id, actor=operator, interest="Stomatologiya")
    assert updated.interest == "Stomatologiya"


def test_operator_scope_hides_other_leads(admin, operator, second_operator) -> None:
    """A restricted operator only sees the leads assigned to them."""
    from app.repositories.lead_repository import LeadFilter

    lead_service.create_lead(actor=admin, full_name="Scope Mine", owner_id=operator.id)
    lead_service.create_lead(actor=admin, full_name="Scope Other", owner_id=second_operator.id)
    leads, _total = lead_service.search_leads(LeadFilter(), actor=operator, limit=500)
    assert all(lead.owner_id == operator.id for lead in leads)
