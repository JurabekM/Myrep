"""Domain enumerations shared across models, services and UI.

Values are stable machine keys; the human readable Uzbek/Russian labels live in
``app.ui.i18n`` so the database never depends on the interface language.
"""

from __future__ import annotations

from enum import StrEnum


class RoleName(StrEnum):
    """Built-in roles."""

    ADMIN = "admin"
    SALES_MANAGER = "sales_manager"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(StrEnum):
    """Fine grained permissions checked by :mod:`app.services.auth_service`."""

    LEAD_VIEW_ALL = "lead.view_all"
    LEAD_VIEW_ASSIGNED = "lead.view_assigned"
    LEAD_EDIT = "lead.edit"
    LEAD_ASSIGN = "lead.assign"
    LEAD_DELETE = "lead.delete"
    LEAD_MERGE = "lead.merge"
    CONVERSATION_REPLY = "conversation.reply"
    CONVERSATION_VIEW = "conversation.view"
    BOOKING_MANAGE = "booking.manage"
    CALL_MANAGE = "call.manage"
    TASK_MANAGE = "task.manage"
    KB_MANAGE = "kb.manage"
    AI_CONFIGURE = "ai.configure"
    AI_REVIEW = "ai.review"
    MARKETING_VIEW = "marketing.view"
    MARKETING_EDIT = "marketing.edit"
    OPERATOR_REVIEW = "operator.review"
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"
    SETTINGS_MANAGE = "settings.manage"
    USER_MANAGE = "user.manage"
    INTEGRATION_MANAGE = "integration.manage"
    AUDIT_VIEW = "audit.view"


ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleName.ADMIN: {p.value for p in Permission},
    RoleName.SALES_MANAGER: {
        Permission.LEAD_VIEW_ALL,
        Permission.LEAD_EDIT,
        Permission.LEAD_ASSIGN,
        Permission.LEAD_MERGE,
        Permission.CONVERSATION_VIEW,
        Permission.CONVERSATION_REPLY,
        Permission.BOOKING_MANAGE,
        Permission.CALL_MANAGE,
        Permission.TASK_MANAGE,
        Permission.KB_MANAGE,
        Permission.AI_REVIEW,
        Permission.AI_CONFIGURE,
        Permission.MARKETING_VIEW,
        Permission.MARKETING_EDIT,
        Permission.OPERATOR_REVIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.AUDIT_VIEW,
    },
    RoleName.OPERATOR: {
        Permission.LEAD_VIEW_ASSIGNED,
        Permission.LEAD_EDIT,
        Permission.CONVERSATION_VIEW,
        Permission.CONVERSATION_REPLY,
        Permission.BOOKING_MANAGE,
        Permission.CALL_MANAGE,
        Permission.TASK_MANAGE,
        Permission.REPORT_VIEW,
    },
    RoleName.ANALYST: {
        Permission.LEAD_VIEW_ALL,
        Permission.CONVERSATION_VIEW,
        Permission.MARKETING_VIEW,
        Permission.OPERATOR_REVIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.AI_REVIEW,
    },
    RoleName.VIEWER: {
        Permission.LEAD_VIEW_ASSIGNED,
        Permission.CONVERSATION_VIEW,
        Permission.REPORT_VIEW,
    },
}


class Channel(StrEnum):
    """Communication channels a lead can arrive from."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    WEBSITE = "website"
    PHONE = "phone"
    MANUAL = "manual"
    DEMO = "demo"


class LeadStatus(StrEnum):
    """Lead pipeline statuses."""

    NEW = "new"
    AI_CONVERSATION = "ai_conversation"
    WAITING_OPERATOR = "waiting_operator"
    OPERATOR_WORKING = "operator_working"
    BOOKED = "booked"
    ARRIVED = "arrived"
    WON = "won"
    LOST = "lost"
    CALLBACK = "callback"
    SPAM = "spam"


#: Allowed pipeline transitions. ``SPAM`` and ``LOST`` are reachable from anywhere.
LEAD_STATUS_TRANSITIONS: dict[str, set[str]] = {
    LeadStatus.NEW: {
        LeadStatus.AI_CONVERSATION,
        LeadStatus.WAITING_OPERATOR,
        LeadStatus.OPERATOR_WORKING,
        LeadStatus.CALLBACK,
    },
    LeadStatus.AI_CONVERSATION: {
        LeadStatus.WAITING_OPERATOR,
        LeadStatus.OPERATOR_WORKING,
        LeadStatus.BOOKED,
        LeadStatus.CALLBACK,
    },
    LeadStatus.WAITING_OPERATOR: {
        LeadStatus.OPERATOR_WORKING,
        LeadStatus.AI_CONVERSATION,
        LeadStatus.BOOKED,
        LeadStatus.CALLBACK,
    },
    LeadStatus.OPERATOR_WORKING: {
        LeadStatus.BOOKED,
        LeadStatus.CALLBACK,
        LeadStatus.WON,
        LeadStatus.WAITING_OPERATOR,
    },
    LeadStatus.BOOKED: {
        LeadStatus.ARRIVED,
        LeadStatus.CALLBACK,
        LeadStatus.OPERATOR_WORKING,
        LeadStatus.WON,
    },
    LeadStatus.ARRIVED: {LeadStatus.WON, LeadStatus.CALLBACK},
    LeadStatus.CALLBACK: {
        LeadStatus.OPERATOR_WORKING,
        LeadStatus.AI_CONVERSATION,
        LeadStatus.BOOKED,
        LeadStatus.WON,
    },
    LeadStatus.WON: set(),
    LeadStatus.LOST: {LeadStatus.CALLBACK},
    LeadStatus.SPAM: set(),
}

#: Statuses that may be reached from any other status.
UNIVERSAL_STATUSES: set[str] = {LeadStatus.LOST, LeadStatus.SPAM}

#: Statuses that mark the lead as no longer active in the pipeline.
CLOSED_STATUSES: set[str] = {LeadStatus.WON, LeadStatus.LOST, LeadStatus.SPAM}


class IntentLevel(StrEnum):
    """Qualitative buying intent derived from the lead score."""

    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class MessageDirection(StrEnum):
    """Direction of a conversation message."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class MessageSender(StrEnum):
    """Who produced a message."""

    CUSTOMER = "customer"
    AI = "ai"
    OPERATOR = "operator"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    """Delivery state of an outbound message."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ConversationStatus(StrEnum):
    """Conversation lifecycle."""

    OPEN = "open"
    AI_HANDLING = "ai_handling"
    WAITING_OPERATOR = "waiting_operator"
    OPERATOR_HANDLING = "operator_handling"
    CLOSED = "closed"


class AIState(StrEnum):
    """Finite state machine of the AI sales agent."""

    NEW_LEAD = "new_lead"
    GREETING = "greeting"
    NEED_DISCOVERY = "need_discovery"
    QUALIFICATION = "qualification"
    OFFER_PRESENTATION = "offer_presentation"
    OBJECTION_HANDLING = "objection_handling"
    BOOKING_ATTEMPT = "booking_attempt"
    FOLLOW_UP = "follow_up"
    HUMAN_HANDOFF = "human_handoff"
    WON = "won"
    LOST = "lost"


class AIInteractionStatus(StrEnum):
    """Outcome of a generated AI reply (used by the quality review module)."""

    SUGGESTED = "suggested"
    SENT = "sent"
    EDITED = "edited"
    REJECTED = "rejected"
    POSITIVE_REPLY = "positive_reply"
    ESCALATED = "escalated"


class AIErrorCategory(StrEnum):
    """Reason a manager marked an AI answer as wrong."""

    WRONG_INFO = "wrong_info"
    WRONG_TONE = "wrong_tone"
    VAGUE = "vague"
    LATE_ESCALATION = "late_escalation"
    OTHER = "other"


class BookingStatus(StrEnum):
    """Booking lifecycle."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    NOT_CONFIRMED = "not_confirmed"
    CANCELLED = "cancelled"
    ARRIVED = "arrived"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class BookingPurpose(StrEnum):
    """Business meaning of a booking slot."""

    CLINIC_APPOINTMENT = "clinic_appointment"
    TRIAL_LESSON = "trial_lesson"
    TEST_DRIVE = "test_drive"
    PROPERTY_VIEWING = "property_viewing"
    TOUR_CONSULTATION = "tour_consultation"
    ISP_INSTALLATION = "isp_installation"
    GENERAL_MEETING = "general_meeting"


class TaskType(StrEnum):
    """Follow-up task categories."""

    WRITE_BACK = "write_back"
    CALL_BACK = "call_back"
    CONFIRM_BOOKING = "confirm_booking"
    NO_SHOW_FOLLOWUP = "no_show_followup"
    SEND_DOCUMENT = "send_document"
    MANAGER_APPROVAL = "manager_approval"
    OTHER = "other"


class TaskStatus(StrEnum):
    """Task lifecycle."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class TaskPriority(StrEnum):
    """Task urgency."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationLevel(StrEnum):
    """Severity of a notification centre entry."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


class CallDirection(StrEnum):
    """Inbound / outbound call."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallOutcome(StrEnum):
    """Result of a phone call."""

    NO_ANSWER = "no_answer"
    CALLBACK = "callback"
    INTERESTED = "interested"
    BOOKED = "booked"
    TOO_EXPENSIVE = "too_expensive"
    WRONG_NUMBER = "wrong_number"
    SOLD = "sold"
    REFUSED = "refused"


class Sentiment(StrEnum):
    """Sentiment classification for calls and conversations."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class IntegrationKind(StrEnum):
    """Type of an integration configuration row."""

    CHANNEL = "channel"
    TELEPHONY = "telephony"
    LLM = "llm"
    STT = "stt"
    CRM = "crm"


class IntegrationStatus(StrEnum):
    """Connection state shown in the top bar."""

    NOT_CONFIGURED = "not_configured"
    DEMO = "demo"
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"


class LanguageCode(StrEnum):
    """Languages the AI agent can detect and answer in."""

    UZ = "uz"
    RU = "ru"
    UNKNOWN = "unknown"


class ToneOfVoice(StrEnum):
    """AI writing style."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    PREMIUM = "premium"
    CONCISE = "concise"


class KBItemType(StrEnum):
    """Knowledge base item categories."""

    SERVICE = "service"
    PRICE = "price"
    PROMO = "promo"
    BRANCH = "branch"
    FAQ = "faq"
    POLICY = "policy"
    INSTRUCTION = "instruction"
    DOCUMENT = "document"


class LossReason(StrEnum):
    """Why a lead was lost (mandatory when moving to LOST)."""

    PRICE = "price"
    NO_ANSWER = "no_answer"
    COMPETITOR = "competitor"
    NOT_RELEVANT = "not_relevant"
    POSTPONED = "postponed"
    BAD_SERVICE = "bad_service"
    OTHER = "other"


class MarketingSourceType(StrEnum):
    """Advertising source families used for ROI attribution."""

    META_ADS = "meta_ads"
    GOOGLE_ADS = "google_ads"
    TELEGRAM_CHANNEL = "telegram_channel"
    INSTAGRAM_ORGANIC = "instagram_organic"
    REFERRAL = "referral"
    OFFLINE = "offline"
    OTHER = "other"
