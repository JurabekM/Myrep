"""ORM model package - importing it registers every table on ``Base.metadata``."""

from app.models.auth import Permission, Role, User, role_permission
from app.models.base import ArchiveMixin, Base, IdMixin, TimestampMixin
from app.models.catalog import Catalog, CatalogItem
from app.models.company import Company
from app.models.crm import (
    Buyer,
    BuyerContact,
    Lead,
    LeadSource,
    MarketingSource,
    SalesAgent,
)
from app.models.docs import (
    Activity,
    AIGeneration,
    Attachment,
    Certificate,
    Checklist,
    ChecklistItem,
    ChecklistTemplate,
    ChecklistTemplateItem,
    Document,
    EmailMessage,
    EmailTemplate,
    Task,
)
from app.models.logistics import FreightQuote, Shipment, ShipmentItem
from app.models.product import (
    Product,
    ProductCategory,
    ProductMedia,
    ProductPrice,
    ProductSpecification,
    ProductVariant,
)
from app.models.sales import (
    RFQ,
    Contract,
    Quotation,
    QuotationItem,
    QuotationVersion,
    RevenueRecord,
    RFQItem,
)
from app.models.system import AppSetting, AuditLog, IntegrationConfig

__all__ = [
    "AIGeneration",
    "Activity",
    "AppSetting",
    "ArchiveMixin",
    "Attachment",
    "AuditLog",
    "Base",
    "Buyer",
    "BuyerContact",
    "Catalog",
    "CatalogItem",
    "Certificate",
    "Checklist",
    "ChecklistItem",
    "ChecklistTemplate",
    "ChecklistTemplateItem",
    "Company",
    "Contract",
    "Document",
    "EmailMessage",
    "EmailTemplate",
    "FreightQuote",
    "IdMixin",
    "IntegrationConfig",
    "Lead",
    "LeadSource",
    "MarketingSource",
    "Permission",
    "Product",
    "ProductCategory",
    "ProductMedia",
    "ProductPrice",
    "ProductSpecification",
    "ProductVariant",
    "Quotation",
    "QuotationItem",
    "QuotationVersion",
    "RFQ",
    "RFQItem",
    "RevenueRecord",
    "Role",
    "SalesAgent",
    "Shipment",
    "ShipmentItem",
    "Task",
    "TimestampMixin",
    "User",
    "role_permission",
]
