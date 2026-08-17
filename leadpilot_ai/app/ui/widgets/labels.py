"""Enum → localized label helpers shared by tables, filters and dialogs."""

from __future__ import annotations

from app.models.enums import (
    AIInteractionStatus,
    BookingPurpose,
    BookingStatus,
    CallOutcome,
    Channel,
    IntegrationStatus,
    IntentLevel,
    KBItemType,
    LeadStatus,
    LossReason,
    RoleName,
    Sentiment,
    TaskPriority,
    TaskStatus,
    TaskType,
    ToneOfVoice,
)
from app.ui.i18n import tr
from app.ui.styles import theme


def status_label(status: str) -> str:
    """Localized lead status."""
    return tr(f"status.{status}")


def channel_label(channel: str) -> str:
    """Localized channel name."""
    return tr(f"channel.{channel}")


def intent_label(intent: str) -> str:
    """Localized intent level."""
    return tr(f"intent.{intent}")


def booking_status_label(status: str) -> str:
    """Localized booking status."""
    return tr(f"bstatus.{status}")


def purpose_label(purpose: str) -> str:
    """Localized booking purpose."""
    return tr(f"purpose.{purpose}")


def outcome_label(outcome: str) -> str:
    """Localized call outcome."""
    return tr(f"outcome.{outcome}")


def sentiment_label(value: str) -> str:
    """Localized sentiment."""
    return tr(f"sentiment.{value}")


def task_type_label(value: str) -> str:
    """Localized task type."""
    return tr(f"ttype.{value}")


def task_status_label(value: str) -> str:
    """Localized task status."""
    return tr(f"tstatus.{value}")


def priority_label(value: str) -> str:
    """Localized task priority."""
    return tr(f"prio.{value}")


def kb_type_label(value: str) -> str:
    """Localized knowledge base item type."""
    return tr(f"kbtype.{value}")


def role_label(value: str) -> str:
    """Localized role name."""
    return tr(f"role.{value}")


def loss_label(value: str) -> str:
    """Localized loss reason."""
    return tr(f"loss.{value}") if value else "—"


def integration_status_label(value: str) -> str:
    """Localized integration status."""
    return tr(f"istatus.{value}")


def ai_status_label(value: str) -> str:
    """Localized AI interaction status."""
    return tr(f"ai.{value}")


def tone_label(value: str) -> str:
    """Localized tone of voice."""
    return tr(f"tone.{value}")


def language_label(value: str) -> str:
    """Localized language name."""
    return tr(f"lang.{value}") if value in ("uz", "ru") else tr("lang.unknown")


# --------------------------------------------------------------------------- #
# Combo box item builders
# --------------------------------------------------------------------------- #
def status_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for lead statuses."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(status_label(s.value), s.value) for s in LeadStatus]


def channel_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for channels."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(channel_label(c.value), c.value) for c in Channel]


def intent_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for intent levels."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(intent_label(i.value), i.value) for i in IntentLevel]


def booking_status_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for booking statuses."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(booking_status_label(s.value), s.value) for s in BookingStatus]


def purpose_items() -> list[tuple[str, str]]:
    """``(label, value)`` pairs for booking purposes."""
    return [(purpose_label(p.value), p.value) for p in BookingPurpose]


def outcome_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for call outcomes."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(outcome_label(o.value), o.value) for o in CallOutcome]


def sentiment_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for sentiments."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(sentiment_label(s.value), s.value) for s in Sentiment]


def task_type_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for task types."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(task_type_label(t.value), t.value) for t in TaskType]


def task_status_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for task statuses."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(task_status_label(s.value), s.value) for s in TaskStatus]


def priority_items() -> list[tuple[str, str]]:
    """``(label, value)`` pairs for priorities."""
    return [(priority_label(p.value), p.value) for p in TaskPriority]


def kb_type_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for knowledge base types."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(kb_type_label(t.value), t.value) for t in KBItemType]


def role_items() -> list[tuple[str, str]]:
    """``(label, value)`` pairs for roles."""
    return [(role_label(r.value), r.value) for r in RoleName]


def loss_items() -> list[tuple[str, str]]:
    """``(label, value)`` pairs for loss reasons."""
    return [(loss_label(r.value), r.value) for r in LossReason]


def tone_items() -> list[tuple[str, str]]:
    """``(label, value)`` pairs for tone of voice."""
    return [(tone_label(t.value), t.value) for t in ToneOfVoice]


def language_items(include_unknown: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for languages."""
    items = [(tr("lang.uz"), "uz"), (tr("lang.ru"), "ru")]
    if include_unknown:
        items.append((tr("lang.unknown"), "unknown"))
    return items


def ai_status_items(include_all: bool = True) -> list[tuple[str, str]]:
    """``(label, value)`` pairs for AI interaction statuses."""
    items = [(tr("common.all"), "")] if include_all else []
    return items + [(ai_status_label(s.value), s.value) for s in AIInteractionStatus]


def integration_status_items() -> list[tuple[str, str]]:
    """``(label, value)`` pairs for integration statuses."""
    return [(integration_status_label(s.value), s.value) for s in IntegrationStatus]


# --------------------------------------------------------------------------- #
# Colours
# --------------------------------------------------------------------------- #
def status_color(status: str) -> str:
    """Colour for a lead status."""
    return theme.STATUS_COLORS.get(status, theme.TEXT_MUTED)


def intent_color(intent: str) -> str:
    """Colour for an intent level."""
    return theme.INTENT_COLORS.get(intent, theme.TEXT_MUTED)


def channel_color(channel: str) -> str:
    """Colour for a channel."""
    return theme.CHANNEL_COLORS.get(channel, theme.TEXT_MUTED)


def booking_color(status: str) -> str:
    """Colour for a booking status."""
    return theme.BOOKING_COLORS.get(status, theme.TEXT_MUTED)


def priority_color(priority: str) -> str:
    """Colour for a task priority."""
    return theme.PRIORITY_COLORS.get(priority, theme.TEXT_MUTED)


def integration_color(status: str) -> str:
    """Colour for an integration status."""
    return theme.INTEGRATION_COLORS.get(status, theme.TEXT_MUTED)


def sentiment_color(value: str) -> str:
    """Colour for a sentiment value."""
    return {
        Sentiment.POSITIVE: theme.SUCCESS,
        Sentiment.NEUTRAL: theme.TEXT_MUTED,
        Sentiment.NEGATIVE: theme.DANGER,
    }.get(value, theme.TEXT_MUTED)


def score_color(score: int) -> str:
    """Colour for a numeric lead score."""
    if score >= 70:
        return theme.DANGER
    if score >= 40:
        return theme.WARNING
    return theme.INFO


CHANNEL_ICONS: dict[str, str] = {
    Channel.TELEGRAM: "fa6b.telegram",
    Channel.WHATSAPP: "fa6b.whatsapp",
    Channel.INSTAGRAM: "fa6b.instagram",
    Channel.WEBSITE: "fa6s.globe",
    Channel.PHONE: "fa6s.phone",
    Channel.MANUAL: "fa6s.pen",
    Channel.DEMO: "fa6s.flask",
}


def channel_icon_name(channel: str) -> str:
    """Qtawesome icon name for a channel."""
    return CHANNEL_ICONS.get(channel, "fa6s.comment")
