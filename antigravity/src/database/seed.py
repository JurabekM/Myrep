"""
Data Seeder Module
==================

Populates the database with essential initial data required for the
Enterprise ERP platform to function on first launch.

Seeders:
    * **Roles** — creates default roles from the :class:`Roles` enum.
    * **Permissions** — creates permission entries from ``PERMISSION_MATRIX``.
    * **Admin user** — creates a default administrator account.
    * **Chart of Accounts** — provisions a basic Uzbekistan-standard chart.

The seeder is idempotent: calling :meth:`DataSeeder.seed_all` multiple
times will not create duplicate records.

Classes:
    DataSeeder: Orchestrates all seeding operations.

Usage::

    seeder = DataSeeder(engine.get_session)
    if not seeder.is_seeded():
        seeder.seed_all()
"""

from __future__ import annotations

import datetime
import hashlib
import logging
from typing import Any, Callable

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.core.constants import (
    Roles,
    Permissions,
    PERMISSION_MATRIX,
)
from src.core.exceptions import DatabaseError
from src.core.utils import generate_uuid

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Fallback password hashing (used if src.auth is not available yet)
# ------------------------------------------------------------------


def _fallback_hash_password(password: str) -> str:
    """Hash a password using SHA-256 as a minimal fallback.

    This is used **only** when ``src.auth.security.hash_password`` is not
    importable (e.g. during early bootstrapping before the auth module is
    built).  Production environments should always use bcrypt via the
    auth module.

    Args:
        password: The plaintext password.

    Returns:
        A hexadecimal SHA-256 hash string.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------
# Safe imports — these modules may not exist yet during early phases.
# ------------------------------------------------------------------

try:
    from src.auth.security import hash_password as _hash_password
except ImportError:
    _hash_password = _fallback_hash_password
    logger.debug(
        "src.auth.security not available; using fallback password hashing."
    )

try:
    from src.auth.models import User, Role, Permission
    _HAS_AUTH_MODELS = True
except ImportError:
    User = None  # type: ignore[assignment, misc]
    Role = None  # type: ignore[assignment, misc]
    Permission = None  # type: ignore[assignment, misc]
    _HAS_AUTH_MODELS = False
    logger.debug(
        "src.auth.models not available; role/user/permission seeding "
        "will be deferred."
    )

try:
    from src.accounting.models import Account  # type: ignore[import-untyped]
    _HAS_ACCOUNTING_MODELS = True
except ImportError:
    Account = None  # type: ignore[assignment, misc]
    _HAS_ACCOUNTING_MODELS = False
    logger.debug(
        "src.accounting.models not available; chart-of-accounts seeding "
        "will be deferred."
    )


class DataSeeder:
    """Orchestrates initial data population for the ERP database.

    All seeder methods are **idempotent** — they check for existing data
    before inserting and safely skip when records already exist.

    Attributes:
        session_factory: A callable returning a context-managed SQLAlchemy
            ``Session`` (e.g. ``DatabaseEngine.get_session``).
    """

    def __init__(self, session_factory: Callable[..., Any]) -> None:
        """Initialise the data seeder.

        Args:
            session_factory: A callable returning a context-managed
                :class:`~sqlalchemy.orm.Session`.
        """
        self.session_factory = session_factory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def seed_all(self) -> None:
        """Execute all seeders in the correct dependency order.

        Order:
            1. Roles
            2. Permissions
            3. Admin user (depends on roles)
            4. Chart of accounts

        Raises:
            DatabaseError: If any seeder fails critically.
        """
        logger.info("Starting database seeding …")

        try:
            self.seed_roles()
            self.seed_permissions()
            self.seed_admin_user()
            self.seed_chart_of_accounts()
            logger.info("Database seeding completed successfully.")
        except Exception as exc:
            raise DatabaseError(f"Database seeding failed: {exc}") from exc

    def is_seeded(self) -> bool:
        """Check whether the database has already been seeded.

        The check is based on the presence of at least one Role record.

        Returns:
            ``True`` if seed data is detected.
        """
        if not _HAS_AUTH_MODELS or Role is None:
            return False

        try:
            with self.session_factory() as session:
                count = session.execute(
                    select(func.count()).select_from(Role)
                ).scalar() or 0
                return count > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Individual seeders
    # ------------------------------------------------------------------

    def seed_roles(self) -> None:
        """Create default roles from the :class:`Roles` enum.

        Each role is created with a display-friendly name derived from
        the enum member name.

        Raises:
            DatabaseError: If the insert fails.
        """
        if not _HAS_AUTH_MODELS or Role is None:
            logger.warning("Auth models unavailable — skipping role seeding.")
            return

        try:
            with self.session_factory() as session:
                existing = {
                    r.name
                    for r in session.execute(select(Role)).scalars().all()
                }

                for role_enum in Roles:
                    if role_enum.value not in existing:
                        role = Role(
                            id=generate_uuid(),
                            name=role_enum.value,
                            display_name=role_enum.value.replace("_", " ").title(),
                            description=f"Default {role_enum.value} role",
                            is_system=True,
                        )
                        session.add(role)

                session.flush()
                logger.info("Roles seeded (%d enum members).", len(Roles))
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Failed to seed roles: {exc}") from exc

    def seed_permissions(self) -> None:
        """Create permission records from ``PERMISSION_MATRIX``.

        The matrix maps role names to lists of permission codenames.
        Each unique permission is created once, then linked to the
        appropriate roles.

        Raises:
            DatabaseError: If the insert fails.
        """
        if not _HAS_AUTH_MODELS or Permission is None or Role is None:
            logger.warning(
                "Auth models unavailable — skipping permission seeding."
            )
            return

        try:
            with self.session_factory() as session:
                # Collect all unique permissions from the matrix.
                all_permissions: set[str] = set()
                for perms in PERMISSION_MATRIX.values():
                    if isinstance(perms, (list, tuple, set)):
                        all_permissions.update(perms)

                existing_perms = {
                    p.codename
                    for p in session.execute(select(Permission)).scalars().all()
                }

                # Create missing permissions.
                perm_objects: dict[str, Any] = {}
                for codename in all_permissions:
                    if codename not in existing_perms:
                        perm = Permission(
                            id=generate_uuid(),
                            codename=codename,
                            name=codename.replace("_", " ").title(),
                            description=f"Permission: {codename}",
                        )
                        session.add(perm)
                        perm_objects[codename] = perm

                session.flush()

                # Build a full lookup (existing + newly created).
                all_perm_lookup: dict[str, Any] = {}
                for p in session.execute(select(Permission)).scalars().all():
                    all_perm_lookup[p.codename] = p

                # Link permissions to roles.
                for role_name, perms in PERMISSION_MATRIX.items():
                    role = session.execute(
                        select(Role).where(Role.name == role_name)
                    ).scalar_one_or_none()

                    if role is None:
                        continue

                    if not isinstance(perms, (list, tuple, set)):
                        continue

                    for codename in perms:
                        perm_obj = all_perm_lookup.get(codename)
                        if perm_obj and perm_obj not in role.permissions:
                            role.permissions.append(perm_obj)

                session.flush()
                logger.info(
                    "Permissions seeded (%d unique permissions).",
                    len(all_permissions),
                )
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Failed to seed permissions: {exc}") from exc

    def seed_admin_user(self) -> None:
        """Create the default administrator account.

        Credentials:
            * **Login**: ``admin``
            * **Password**: ``admin123`` (hashed)

        The admin user is associated with the ``ADMINISTRATOR`` role.

        Raises:
            DatabaseError: If the insert fails.
        """
        if not _HAS_AUTH_MODELS or User is None or Role is None:
            logger.warning(
                "Auth models unavailable — skipping admin user seeding."
            )
            return

        try:
            with self.session_factory() as session:
                existing = session.execute(
                    select(User).where(User.username == "admin")
                ).scalar_one_or_none()

                if existing is not None:
                    logger.info("Admin user already exists — skipping.")
                    return

                # Look up the administrator role.
                admin_role = session.execute(
                    select(Role).where(Role.name == Roles.ADMINISTRATOR.value)
                ).scalar_one_or_none()

                admin = User(
                    id=generate_uuid(),
                    username="admin",
                    email="admin@erp.local",
                    password_hash=_hash_password("admin123"),
                    first_name="System",
                    last_name="Administrator",
                    is_active=True,
                    is_superuser=True,
                )

                if admin_role is not None:
                    admin.role_id = admin_role.id

                session.add(admin)
                session.flush()
                logger.info("Default admin user created (login: admin).")
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Failed to seed admin user: {exc}") from exc

    def seed_chart_of_accounts(self) -> None:
        """Create a basic Uzbekistan-standard chart of accounts.

        The chart follows the National Accounting Standards of Uzbekistan
        (NAS) with account groups for assets, liabilities, equity,
        revenue, and expenses.

        Raises:
            DatabaseError: If the insert fails.
        """
        if not _HAS_ACCOUNTING_MODELS or Account is None:
            logger.warning(
                "Accounting models unavailable — skipping chart-of-accounts "
                "seeding."
            )
            return

        accounts = self._get_uzbekistan_chart_of_accounts()

        try:
            with self.session_factory() as session:
                existing_codes = {
                    a.code
                    for a in session.execute(select(Account)).scalars().all()
                }

                for acct_data in accounts:
                    if acct_data["code"] not in existing_codes:
                        account = Account(
                            id=generate_uuid(),
                            **acct_data,
                        )
                        session.add(account)

                session.flush()
                logger.info(
                    "Chart of accounts seeded (%d accounts).", len(accounts)
                )
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(
                f"Failed to seed chart of accounts: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Static data
    # ------------------------------------------------------------------

    @staticmethod
    def _get_uzbekistan_chart_of_accounts() -> list[dict[str, Any]]:
        """Return the default Uzbekistan NAS chart of accounts.

        Returns:
            A list of dictionaries with keys ``code``, ``name``,
            ``account_type``, ``parent_code`` (nullable), and
            ``is_system``.
        """
        return [
            # ── Assets (0100–0999) ─────────────────────────────────
            {
                "code": "0100",
                "name": "Asosiy vositalar (Основные средства)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "0200",
                "name": "Nomoddiy aktivlar (Нематериальные активы)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "0300",
                "name": "Uzoq muddatli investitsiyalar (Долгосрочные инвестиции)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "0400",
                "name": "Kapital qo'yilmalar (Капитальные вложения)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            # ── Inventories (1000–2999) ────────────────────────────
            {
                "code": "1000",
                "name": "Materiallar (Материалы)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "1500",
                "name": "Xom ashyo (Сырье и материалы)",
                "account_type": "asset",
                "parent_code": "1000",
                "is_system": True,
            },
            {
                "code": "2000",
                "name": "Asosiy ishlab chiqarish (Основное производство)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "2800",
                "name": "Tayyor mahsulot (Готовая продукция)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "2900",
                "name": "Tovarlar (Товары)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            # ── Cash & Receivables (3000–4999) ─────────────────────
            {
                "code": "3000",
                "name": "Pul mablag'lari (Денежные средства)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "3100",
                "name": "Hisob-kitob schyoti (Расчетный счет)",
                "account_type": "asset",
                "parent_code": "3000",
                "is_system": True,
            },
            {
                "code": "3200",
                "name": "Valyuta schyoti (Валютный счет)",
                "account_type": "asset",
                "parent_code": "3000",
                "is_system": True,
            },
            {
                "code": "5000",
                "name": "Kassa (Касса)",
                "account_type": "asset",
                "parent_code": "3000",
                "is_system": True,
            },
            {
                "code": "4000",
                "name": "Oluvchilar va buyurtmachilar (Дебиторская задолженность)",
                "account_type": "asset",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "4300",
                "name": "Xodimlarga berilgan avanslar (Авансы выданные)",
                "account_type": "asset",
                "parent_code": "4000",
                "is_system": True,
            },
            # ── Liabilities (6000–6999) ────────────────────────────
            {
                "code": "6000",
                "name": "Yetkazuvchi va pudratchilar (Кредиторская задолженность)",
                "account_type": "liability",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "6300",
                "name": "Soliqlar bo'yicha qarz (Задолженность по налогам)",
                "account_type": "liability",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "6400",
                "name": "Byudjetga to'lovlar (Платежи в бюджет)",
                "account_type": "liability",
                "parent_code": "6300",
                "is_system": True,
            },
            {
                "code": "6500",
                "name": "Sug'urta bo'yicha to'lovlar (Страховые платежи)",
                "account_type": "liability",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "6700",
                "name": "Mehnat haqi bo'yicha hisob-kitoblar (Расчеты по оплате труда)",
                "account_type": "liability",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "6800",
                "name": "Qisqa muddatli kreditlar (Краткосрочные кредиты)",
                "account_type": "liability",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "7000",
                "name": "Uzoq muddatli kreditlar (Долгосрочные кредиты)",
                "account_type": "liability",
                "parent_code": None,
                "is_system": True,
            },
            # ── Equity (8000–8499) ─────────────────────────────────
            {
                "code": "8000",
                "name": "Ustav kapitali (Уставный капитал)",
                "account_type": "equity",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "8100",
                "name": "Qo'shimcha kapital (Добавленный капитал)",
                "account_type": "equity",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "8200",
                "name": "Rezerv kapitali (Резервный капитал)",
                "account_type": "equity",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "8300",
                "name": "Taqsimlanmagan foyda (Нераспределенная прибыль)",
                "account_type": "equity",
                "parent_code": None,
                "is_system": True,
            },
            # ── Revenue (9000–9199) ────────────────────────────────
            {
                "code": "9000",
                "name": "Asosiy faoliyat daromadlari (Доходы от основной деятельности)",
                "account_type": "revenue",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9100",
                "name": "Mahsulot sotishdan tushum (Выручка от продаж)",
                "account_type": "revenue",
                "parent_code": "9000",
                "is_system": True,
            },
            {
                "code": "9200",
                "name": "Boshqa operatsion daromadlar (Прочие операционные доходы)",
                "account_type": "revenue",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9300",
                "name": "Moliyaviy faoliyat daromadlari (Финансовые доходы)",
                "account_type": "revenue",
                "parent_code": None,
                "is_system": True,
            },
            # ── Expenses (9400–9999) ───────────────────────────────
            {
                "code": "9400",
                "name": "Sotilgan mahsulot tannarxi (Себестоимость реализации)",
                "account_type": "expense",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9410",
                "name": "Sotish xarajatlari (Расходы на реализацию)",
                "account_type": "expense",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9420",
                "name": "Ma'muriy xarajatlar (Административные расходы)",
                "account_type": "expense",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9430",
                "name": "Boshqa operatsion xarajatlar (Прочие операционные расходы)",
                "account_type": "expense",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9500",
                "name": "Foyda solig'i xarajatlari (Расходы по налогу на прибыль)",
                "account_type": "expense",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9600",
                "name": "Moliyaviy xarajatlar (Финансовые расходы)",
                "account_type": "expense",
                "parent_code": None,
                "is_system": True,
            },
            {
                "code": "9900",
                "name": "Yakuniy moliyaviy natija (Итоговый финансовый результат)",
                "account_type": "equity",
                "parent_code": None,
                "is_system": True,
            },
        ]
