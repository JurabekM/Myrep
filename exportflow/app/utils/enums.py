"""Domain vocabularies.

Values are stored in the database as plain strings; the ``I18N_KEY`` maps are
used by the UI layer to display them in the active interface language.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- roles
ROLE_ADMIN = "administrator"
ROLE_EXPORT_MANAGER = "export_manager"
ROLE_SALES_MANAGER = "sales_manager"
ROLE_LOGISTICS = "logistics_specialist"
ROLE_CATALOG_MANAGER = "catalog_manager"
ROLE_VIEWER = "viewer"

ALL_ROLES = (
    ROLE_ADMIN,
    ROLE_EXPORT_MANAGER,
    ROLE_SALES_MANAGER,
    ROLE_LOGISTICS,
    ROLE_CATALOG_MANAGER,
    ROLE_VIEWER,
)

# --------------------------------------------------------------------------- product
PRODUCT_STATUSES = ("draft", "active", "archived")

UNITS = ("pcs", "set", "kg", "ton", "m", "m2", "m3", "litre", "carton", "pallet")

# --------------------------------------------------------------------------- incoterms
INCOTERMS = ("EXW", "FCA", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP")
PORT_REQUIRED_INCOTERMS = ("FOB", "CFR", "CIF", "FCA", "CPT", "CIP")

PRICE_STATUSES = ("draft", "approved", "expired")

PAYMENT_TERMS = (
    "100% T/T in advance",
    "30% advance, 70% against B/L copy",
    "Irrevocable L/C at sight",
    "Irrevocable L/C 30 days",
    "50% advance, 50% before shipment",
    "D/P at sight",
    "Open account 30 days",
)

# --------------------------------------------------------------------------- CRM
BUYER_TYPES = (
    "importer",
    "distributor",
    "retailer",
    "wholesaler",
    "agent",
    "manufacturer",
)

RISK_LEVELS = ("low", "medium", "high")

LEAD_SOURCES = (
    "alibaba",
    "linkedin",
    "email",
    "website_inquiry",
    "trade_fair",
    "sales_agent",
    "referral",
    "manual",
    "other",
)

LEAD_STATUSES = (
    "new",
    "in_review",
    "replied",
    "qualified",
    "rfq_received",
    "quotation_sent",
    "sample_sent",
    "negotiation",
    "contract_preparation",
    "contract_signed",
    "shipment_in_progress",
    "closed_won",
    "closed_lost",
    "follow_up",
    "spam",
)

#: Ordered kanban columns of the pipeline workspace.
PIPELINE_STAGES = (
    "new",
    "in_review",
    "qualified",
    "rfq_received",
    "quotation_sent",
    "sample_sent",
    "negotiation",
    "contract_preparation",
    "contract_signed",
    "closed_won",
    "closed_lost",
)

LEAD_TEMPERATURES = ("cold", "warm", "hot")

# --------------------------------------------------------------------------- sales
RFQ_STATUSES = ("new", "in_review", "quoted", "declined", "closed")

QUOTATION_STATUSES = (
    "draft",
    "review_required",
    "approved",
    "sent",
    "viewed",
    "buyer_replied",
    "under_negotiation",
    "accepted",
    "rejected",
    "expired",
    "cancelled",
)

#: Statuses that mean the quotation already left the company.
QUOTATION_SENT_STATUSES = (
    "sent",
    "viewed",
    "buyer_replied",
    "under_negotiation",
    "accepted",
    "rejected",
)

CONTRACT_STATUSES = ("draft", "signed", "in_execution", "completed", "cancelled")

# --------------------------------------------------------------------------- documents
CERTIFICATE_TYPES = (
    "certificate_of_origin",
    "iso",
    "halal",
    "organic",
    "haccp",
    "phytosanitary",
    "veterinary",
    "quality_certificate",
    "lab_test_report",
    "other",
)

CERTIFICATE_STATUSES = ("valid", "expiring", "expired", "revoked")
VERIFICATION_STATUSES = ("unverified", "verified", "rejected")

DOCUMENT_TYPES = (
    "commercial_invoice",
    "packing_list",
    "bill_of_lading",
    "certificate_of_origin",
    "contract",
    "proforma_invoice",
    "customs_declaration",
    "insurance_policy",
    "other",
)

# --------------------------------------------------------------------------- checklist
CHECKLIST_CATEGORIES = (
    "product_readiness",
    "certificates",
    "packaging",
    "pricing",
    "incoterms",
    "payment_terms",
    "customs_documents",
    "logistics",
    "sample",
    "contract",
    "shipment",
)

CHECKLIST_SCOPES = ("product", "buyer", "lead", "shipment")

PRIORITIES = ("low", "normal", "high", "critical")
TASK_STATUSES = ("open", "in_progress", "done", "cancelled")

# --------------------------------------------------------------------------- logistics
SHIPMENT_STATUSES = (
    "planning",
    "booking_requested",
    "booked",
    "ready_to_ship",
    "in_customs",
    "in_transit",
    "arrived",
    "delivered",
    "delayed",
    "cancelled",
)

#: Allowed forward transitions; ``cancelled``/``delayed`` are reachable from any
#: non-final state and handled separately in the service layer.
SHIPMENT_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "planning": ("booking_requested", "cancelled"),
    "booking_requested": ("booked", "planning", "cancelled"),
    "booked": ("ready_to_ship", "cancelled", "delayed"),
    "ready_to_ship": ("in_customs", "in_transit", "cancelled", "delayed"),
    "in_customs": ("in_transit", "delayed", "cancelled"),
    "in_transit": ("arrived", "delayed", "cancelled"),
    "arrived": ("delivered", "delayed"),
    "delivered": (),
    "delayed": ("in_customs", "in_transit", "arrived", "delivered", "cancelled"),
    "cancelled": (),
}

CONTAINER_TYPES = ("20DV", "40DV", "40HC", "20RF", "40RF", "LCL", "Truck", "Air", "Rail")

CUSTOMS_STATUSES = ("not_started", "declaration_submitted", "cleared", "held", "rejected")

# --------------------------------------------------------------------------- email
EMAIL_STATUSES = ("draft", "queued", "sent", "failed", "received")

# --------------------------------------------------------------------------- AI
AI_CONTENT_TYPES = (
    "product_description_short",
    "product_description_full",
    "b2b_product_description",
    "alibaba_listing",
    "seo_title",
    "buyer_email",
    "commercial_offer",
    "follow_up_email",
    "quotation_intro",
    "objection_response",
    "linkedin_outreach",
    "certificate_explanation",
    "negotiation_talking_points",
)

AI_TONES = ("professional", "friendly", "concise", "persuasive", "formal")

# --------------------------------------------------------------------------- integrations
INTEGRATION_KINDS = ("llm", "email", "lead_import", "crm", "webhook")

LOST_REASONS = (
    "price_too_high",
    "no_certificate",
    "moq_mismatch",
    "long_lead_time",
    "logistics_cost",
    "payment_terms",
    "competitor_won",
    "buyer_silent",
    "other",
)


def i18n_key(group: str, value: str) -> str:
    """Build the translation key for an enum value (``enum.lead_status.new``)."""
    return f"enum.{group}.{value}"
