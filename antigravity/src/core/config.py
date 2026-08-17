"""YAML-based configuration management for the Enterprise ERP platform.

Provides a centralised :class:`ConfigManager` that loads, validates, and
persists application settings.  Configuration values are stored in a YAML
file and exposed through both dot-notation ``get``/``set`` methods and
typed property accessors for common sections.

Features:
    - Automatic fallback to sensible defaults when no YAML file exists.
    - Dot-notation key access (e.g. ``config.get('database.type')``).
    - Typed section properties (``database``, ``server``, ``security``, etc.).
    - Auto-generated secret key in default configuration.
    - Graceful degradation when PyYAML is not installed.

Example::

    from src.core.config import ConfigManager

    cfg = ConfigManager('config.yaml')
    db_type = cfg.get('database.type', 'sqlite')
    cfg.set('server.port', 9000)
    cfg.save()
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from .constants import (
    APP_NAME,
    APP_VERSION,
    CURRENCY,
    DEFAULT_DB,
    DEFAULT_PORT,
    VAT_RATE,
)
from .utils import get_data_dir, get_project_root


logger = logging.getLogger(__name__)


class ConfigManager:
    """Centralised configuration management with YAML persistence.

    On instantiation the manager attempts to load settings from a YAML
    file.  If the file does not exist or PyYAML is unavailable, sensible
    defaults are generated automatically.

    Attributes:
        _config_path: Resolved path to the YAML configuration file.
        _config: The in-memory configuration dictionary.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialise the configuration manager.

        Args:
            config_path: Path to the YAML config file.  Defaults to
                ``<project_root>/config.yaml`` when ``None``.
        """
        self._logger = logging.getLogger(__name__)
        if config_path is None:
            self._config_path = Path(get_project_root()) / 'config.yaml'
        else:
            self._config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> Dict[str, Any]:
        """Load configuration from the YAML file.

        Falls back to :meth:`generate_default_config` when the file is
        missing or PyYAML is not installed.

        Returns:
            The loaded (or default) configuration dictionary.
        """
        if self._config_path.exists() and yaml is not None:
            try:
                with open(self._config_path, 'r', encoding='utf-8') as fh:
                    loaded = yaml.safe_load(fh)
                    self._config = loaded if isinstance(loaded, dict) else {}
                self._logger.info(
                    'Configuration loaded from %s', self._config_path,
                )
            except Exception:
                self._logger.exception(
                    'Failed to load config from %s — using defaults',
                    self._config_path,
                )
                self._config = self.generate_default_config()
        else:
            self._config = self.generate_default_config()
            self._logger.info('Using default configuration')
        return self._config

    def save(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Persist the current (or supplied) configuration to YAML.

        Args:
            config: If provided, replaces the in-memory config before
                saving.  When ``None`` the existing in-memory config is
                written.
        """
        if config is not None:
            self._config = config
        if yaml is None:
            self._logger.warning(
                'PyYAML is not installed — cannot save configuration',
            )
            return
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, 'w', encoding='utf-8') as fh:
            yaml.dump(
                self._config,
                fh,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        self._logger.info('Configuration saved to %s', self._config_path)

    # ------------------------------------------------------------------
    # Dot-notation access
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value using dot-notation.

        Args:
            key: Dot-separated key path (e.g. ``'database.type'``).
            default: Value returned when the key does not exist.

        Returns:
            The configuration value, or *default* if not found.
        """
        keys = key.split('.')
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot-notation.

        Intermediate dictionaries are created automatically when they do
        not yet exist.

        Args:
            key: Dot-separated key path (e.g. ``'server.port'``).
            value: The value to store.
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    # ------------------------------------------------------------------
    # Default configuration
    # ------------------------------------------------------------------

    def generate_default_config(self) -> Dict[str, Any]:
        """Generate a complete default configuration dictionary.

        Includes sensible defaults for all subsystems: database, server,
        security, company info, backup policy, and logging.

        Returns:
            A fully-populated configuration dictionary.
        """
        data_dir = str(get_data_dir())
        return {
            'app': {
                'name': APP_NAME,
                'version': APP_VERSION,
            },
            'database': {
                'type': 'sqlite',
                'path': os.path.join(data_dir, 'db', DEFAULT_DB),
                'postgresql': {
                    'host': 'localhost',
                    'port': 5432,
                    'name': 'erp_database',
                    'user': 'erp_user',
                    'password': '',
                },
            },
            'server': {
                'host': '0.0.0.0',
                'port': DEFAULT_PORT,
                'debug': False,
            },
            'security': {
                'secret_key': uuid.uuid4().hex + uuid.uuid4().hex,
                'session_timeout': 3600,
                'max_login_attempts': 5,
                'password_min_length': 8,
            },
            'company': {
                'name': 'My Company',
                'currency': CURRENCY,
                'vat_rate': VAT_RATE,
                'language': 'uz',
            },
            'backup': {
                'auto_backup': True,
                'interval_hours': 24,
                'max_backups': 30,
                'path': os.path.join(data_dir, 'backups'),
            },
            'logging': {
                'level': 'INFO',
                'file': os.path.join(data_dir, 'logs', 'erp.log'),
            },
        }

    # ------------------------------------------------------------------
    # Typed section properties
    # ------------------------------------------------------------------

    @property
    def database(self) -> Dict[str, Any]:
        """Return the ``database`` configuration section.

        Returns:
            Dictionary with database connection settings.
        """
        return self._config.get('database', {})

    @property
    def server(self) -> Dict[str, Any]:
        """Return the ``server`` configuration section.

        Returns:
            Dictionary with HTTP server settings.
        """
        return self._config.get('server', {})

    @property
    def security(self) -> Dict[str, Any]:
        """Return the ``security`` configuration section.

        Returns:
            Dictionary with security and authentication settings.
        """
        return self._config.get('security', {})

    @property
    def company(self) -> Dict[str, Any]:
        """Return the ``company`` configuration section.

        Returns:
            Dictionary with company information and localisation.
        """
        return self._config.get('company', {})

    @property
    def backup(self) -> Dict[str, Any]:
        """Return the ``backup`` configuration section.

        Returns:
            Dictionary with backup policy settings.
        """
        return self._config.get('backup', {})

    @property
    def logging_config(self) -> Dict[str, Any]:
        """Return the ``logging`` configuration section.

        Returns:
            Dictionary with logging level and file path settings.
        """
        return self._config.get('logging', {})

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        return f'ConfigManager(path={self._config_path})'

    def __contains__(self, key: str) -> bool:
        """Support ``'key' in config_manager`` syntax.

        Args:
            key: Dot-separated key path to check.

        Returns:
            ``True`` if the key resolves to a non-``None`` value.
        """
        return self.get(key) is not None
