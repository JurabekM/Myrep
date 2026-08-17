# -*- coding: utf-8 -*-
"""
Bootstrap — dasturning avtomatik ishga tushish jarayoni.

Bitta ``initialize()`` chaqiruvi quyidagilarni kafolatlaydi:
  1. papkalar yaratilgan (data/, logs/, backups/, exports/, plugins/)
  2. config.yaml mavjud (bo'lmasa generatsiya qilinadi)
  3. logging sozlangan
  4. database yaratilgan, migratsiyalar qo'llangan, boshlang'ich
     ma'lumotlar yozilgan
  5. admin foydalanuvchi mavjud
  6. barcha servislar DI konteynerga ro'yxatdan o'tgan

Foydalanuvchi hech narsani qo'lda sozlamaydi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.core.audit import AuditTrail
from src.core.cache import TTLCache
from src.core.config import Config
from src.core.container import ServiceContainer
from src.core.events import EventBus
from src.core.logger import get_logger, setup_logging
from src.core.security import CSRFProtect, RateLimiter, SignedTokenFactory
from src.database.connection import create_database
from src.database.migrations import MigrationRunner

#: Avtomatik yaratiladigan papkalar
REQUIRED_DIRS = ("data", "logs", "backups", "exports", "plugins")


@dataclass
class AppContext:
    """Ilovaning umumiy konteksti — barcha qatlamlarga uzatiladi."""

    base_dir: Path
    config: Config
    db: object
    bus: EventBus
    cache: TTLCache
    audit: AuditTrail
    services: ServiceContainer
    admin_password: str | None = None
    flags: dict = field(default_factory=dict)

    def close(self) -> None:
        """Resurslarni tartibli yopadi."""
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            pass


def ensure_directories(base_dir: Path) -> None:
    """Kerakli papkalarni yaratadi (mavjud bo'lsa jim o'tadi)."""
    for name in REQUIRED_DIRS:
        (base_dir / name).mkdir(parents=True, exist_ok=True)


def initialize(base_dir: Path | None = None, flags: dict | None = None) -> AppContext:
    """
    To'liq bootstrap. Qaytarilgan :class:`AppContext` orqali barcha
    servislarga kirish mumkin: ``ctx.services.get("auth")`` va h.k.
    """
    base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
    flags = flags or {}

    # 1. Papkalar
    ensure_directories(base_dir)

    # 2. Konfiguratsiya
    config = Config.ensure(base_dir / "config.yaml")
    if flags.get("port"):
        config.set("server.port", int(flags["port"]))

    # 3. Logging
    setup_logging(base_dir / "logs", str(config.get("logging.level", "INFO")))
    log = get_logger("bootstrap")
    log.info("UzERP ishga tushmoqda... (base_dir=%s)", base_dir)

    # 4. Database + migratsiyalar
    db = create_database(config, base_dir)
    MigrationRunner(db).run()

    # 5. Yadro servislari
    bus = EventBus()
    cache = TTLCache(maxsize=2048, ttl=120.0)
    audit = AuditTrail(db)

    # 6. Admin foydalanuvchi
    from src.auth.service import AuthService  # aylanma importni oldini olish

    auth = AuthService(db, config, audit)
    admin_password = auth.ensure_admin(base_dir / "data")

    # 7. DI konteyner
    services = ServiceContainer()
    services.register_instance("base_dir", base_dir)
    services.register_instance("config", config)
    services.register_instance("db", db)
    services.register_instance("bus", bus)
    services.register_instance("cache", cache)
    services.register_instance("audit", audit)
    services.register_instance("auth", auth)

    secret = str(config.get("app.secret_key"))
    services.register_instance("tokens", SignedTokenFactory(secret))
    services.register_instance("csrf", CSRFProtect(secret))
    services.register_instance(
        "rate_limiter",
        RateLimiter(
            max_requests=int(config.get("security.rate_limit_per_minute", 120)),
            window_seconds=60.0,
        ),
    )

    _register_business_services(services)

    ctx = AppContext(
        base_dir=base_dir, config=config, db=db, bus=bus, cache=cache,
        audit=audit, services=services, admin_password=admin_password,
        flags=flags,
    )
    audit.log("system.start", category="system",
              details=f"engine={db.engine}")
    log.info("Bootstrap tugadi: db=%s, jadval=%d ta",
             db.engine, len(db.table_names()))
    return ctx


def _register_business_services(services: ServiceContainer) -> None:
    """
    Biznes-modullar servislarini ro'yxatdan o'tkazadi (lazy).

    Modul hali yaratilmagan bo'lsa jim o'tadi — bosqichma-bosqich qurish
    jarayonida tizim doim ishga tushaveradi.
    """
    registry: list[tuple[str, str, str]] = [
        # (servis nomi, modul yo'li, klass nomi)
        ("products", "src.modules.inventory.products", "ProductService"),
        ("inventory", "src.modules.inventory.stock", "InventoryService"),
        ("purchases", "src.modules.inventory.purchases", "PurchaseService"),
        ("sales", "src.modules.sales.service", "SalesService"),
        ("customers", "src.modules.sales.customers", "CustomerService"),
        ("suppliers", "src.modules.inventory.suppliers", "SupplierService"),
        ("crm", "src.modules.crm.service", "CrmService"),
        ("accounting", "src.modules.accounting.service", "AccountingService"),
        ("payments", "src.modules.accounting.payments", "PaymentService"),
        ("assets", "src.modules.accounting.assets", "AssetService"),
        ("hr", "src.modules.hr.service", "HrService"),
        ("payroll", "src.modules.hr.payroll", "PayrollService"),
        ("reports", "src.modules.reports.service", "ReportService"),
        ("analytics", "src.modules.analytics.service", "AnalyticsService"),
        ("exporter", "src.services.export_service", "ExportService"),
        ("importer", "src.services.import_service", "ImportService"),
        ("backup", "src.services.backup_service", "BackupService"),
        ("search", "src.services.search_service", "SearchService"),
        ("plugins", "src.services.plugin_service", "PluginService"),
        ("integrations", "src.services.integration_service", "IntegrationService"),
    ]
    log = get_logger("bootstrap")
    for name, module_path, class_name in registry:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
        except (ImportError, AttributeError):
            continue  # modul keyingi bosqichda qo'shiladi
        services.register(name, _make_factory(cls))
        log.debug("Servis ro'yxatdan o'tdi: %s", name)

    # AccountingService hodisalarga (sale.confirmed, purchase.received)
    # obuna bo'lishi uchun darhol yaratilishi shart — aks holda avtomatik
    # buxgalteriya o'tkazmalari yozilmay qoladi.
    if services.has("accounting"):
        services.get("accounting")

    # Pluginlar ham hodisalarga obuna bo'lishi mumkin — startda yuklanadi.
    # Plugin xatosi tizimni to'xtatmaydi.
    if services.has("plugins"):
        try:
            services.get("plugins").load_all()
        except Exception:  # noqa: BLE001
            log.exception("Pluginlarni yuklashda xato")


def _make_factory(cls):
    """Servis klassi uchun standart factory (konteynerni qabul qiladi)."""

    def factory(container: ServiceContainer):
        return cls(container)

    return factory
