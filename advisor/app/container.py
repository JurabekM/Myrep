"""Kompozitsiya ildizi (Composition Root) — barcha bog'liqliklarni yig'adi.

Bitta joyda repozitoriylar, AI router, RAG va servislar tuziladi va ular
o'zaro bog'lanadi (Dependency Injection). UI va main.py faqat shu konteynerni
oladi.
"""

from __future__ import annotations

from app.ai.router import ModelRouter, build_providers
from app.core.config import AppConfig
from app.data.database import Database
from app.data.repositories.conversation_repo import ConversationRepository, MessageRepository
from app.data.repositories.document_repo import DocumentRepository
from app.data.repositories.kb_repo import KBRepository, UsageRepository
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.services.chat_service import ChatService
from app.services.consultant_service import ConsultantService
from app.services.dashboard_service import DashboardService
from app.services.document_service import DocumentService
from app.services.finance_service import FinanceService
from app.services.legal_service import LegalService
from app.services.lex_scraper import LexScraper
from app.services.marketing_service import MarketingService
from app.services.tax_service import TaxService
from app.services.voice_service import VoiceService
from app.workers.task_manager import TaskManager


class Container:
    def __init__(self, config: AppConfig, database: Database):
        self.config = config
        self.db = database

        # --- Repozitoriylar ---
        self.conversations = ConversationRepository(database)
        self.messages = MessageRepository(database)
        self.documents = DocumentRepository(database)
        self.kb = KBRepository(database)
        self.usage = UsageRepository(database)

        # --- RAG ---
        self.vector_store = VectorStore(self.kb)
        self.retriever = Retriever(self.vector_store)

        # --- AI ---
        self.router = ModelRouter(
            build_providers(config), config.ai.provider_order, self.usage
        )

        # --- Fon vazifalari ---
        self.tasks = TaskManager()

        # --- Servislar ---
        profile = config.profile
        self.chat_service = ChatService(
            self.conversations, self.messages, self.router, self.retriever, profile
        )
        self.consultant_service = ConsultantService(self.router, profile)
        self.legal_service = LegalService(self.router, self.retriever, profile)
        self.tax_service = TaxService(self.router, profile)
        self.finance_service = FinanceService()
        self.marketing_service = MarketingService(self.router, profile)
        self.document_service = DocumentService(self.documents, self.router, profile)
        self.dashboard_service = DashboardService(self.usage, profile)
        self.voice_service = VoiceService()
        self.lex_scraper = LexScraper(self.kb, self.vector_store)

    def shutdown(self) -> None:
        self.tasks.shutdown()
        self.db.close_all()
