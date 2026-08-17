"""Repository layer - all database access goes through these classes."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Activity,
    AIGeneration,
    AppSetting,
    Attachment,
    AuditLog,
    Buyer,
    BuyerContact,
    Catalog,
    Certificate,
    Checklist,
    ChecklistTemplate,
    Company,
    Contract,
    Document,
    EmailMessage,
    EmailTemplate,
    IntegrationConfig,
    Lead,
    MarketingSource,
    Product,
    ProductCategory,
    ProductPrice,
    Quotation,
    RevenueRecord,
    Role,
    SalesAgent,
    Shipment,
    Task,
    User,
)
from app.models.sales import RFQ
from app.repositories.base import BaseRepository


class Repositories:
    """Convenience bundle of every repository bound to one session."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = BaseRepository(session, User)
        self.roles = BaseRepository(session, Role)
        self.companies = BaseRepository(session, Company)
        self.categories = BaseRepository(session, ProductCategory)
        self.products = BaseRepository(session, Product)
        self.prices = BaseRepository(session, ProductPrice)
        self.catalogs = BaseRepository(session, Catalog)
        self.buyers = BaseRepository(session, Buyer)
        self.contacts = BaseRepository(session, BuyerContact)
        self.leads = BaseRepository(session, Lead)
        self.agents = BaseRepository(session, SalesAgent)
        self.sources = BaseRepository(session, MarketingSource)
        self.rfqs = BaseRepository(session, RFQ)
        self.quotations = BaseRepository(session, Quotation)
        self.contracts = BaseRepository(session, Contract)
        self.revenues = BaseRepository(session, RevenueRecord)
        self.certificates = BaseRepository(session, Certificate)
        self.documents = BaseRepository(session, Document)
        self.attachments = BaseRepository(session, Attachment)
        self.checklists = BaseRepository(session, Checklist)
        self.checklist_templates = BaseRepository(session, ChecklistTemplate)
        self.tasks = BaseRepository(session, Task)
        self.activities = BaseRepository(session, Activity)
        self.emails = BaseRepository(session, EmailMessage)
        self.email_templates = BaseRepository(session, EmailTemplate)
        self.shipments = BaseRepository(session, Shipment)
        self.integrations = BaseRepository(session, IntegrationConfig)
        self.audit = BaseRepository(session, AuditLog)
        self.settings = BaseRepository(session, AppSetting)
        self.ai_history = BaseRepository(session, AIGeneration)


__all__ = ["BaseRepository", "Repositories"]
