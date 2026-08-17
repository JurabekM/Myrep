"""Business logic layer.

Every rule that matters (pricing validity, quotation approval, checklist
automation, shipment transitions, follow-up rules) lives here - never in the UI.
"""

__all__ = [
    "ai_content_service",
    "audit_service",
    "auth_service",
    "buyer_service",
    "catalog_service",
    "checklist_service",
    "company_service",
    "contract_service",
    "document_service",
    "email_service",
    "import_service",
    "integration_service",
    "lead_service",
    "logistics_service",
    "permissions",
    "product_service",
    "quotation_service",
    "report_service",
    "task_service",
]
