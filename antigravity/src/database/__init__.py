"""
Database Package
================

Provides database engine management, ORM base models, generic repository pattern,
migration system, backup/restore functionality, and initial data seeding for the
Enterprise ERP platform.

Exports:
    - DatabaseEngine: Connection management with SQLite/PostgreSQL auto-detection.
    - Base, BaseModel: SQLAlchemy declarative base and abstract model with mixins.
    - TimestampMixin, SoftDeleteMixin, AuditMixin: Reusable model mixins.
    - BaseRepository: Generic CRUD repository with filtering, pagination, and search.
    - MigrationManager: Schema versioning and auto-migration support.
    - BackupManager: Database backup, restore, and retention management.
    - DataSeeder: Initial data population for roles, permissions, and accounts.
"""

from src.database.engine import DatabaseEngine
from src.database.models import (
    Base,
    BaseModel,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
)
from src.database.repository import BaseRepository
from src.database.migration import MigrationManager
from src.database.backup import BackupManager
from src.database.seed import DataSeeder

__all__ = [
    "DatabaseEngine",
    "Base",
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "BaseRepository",
    "MigrationManager",
    "BackupManager",
    "DataSeeder",
]
