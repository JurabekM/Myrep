"""Application bootstrap and dependency-injection container.

Provides the central :class:`Application` object that ties together all
subsystems — configuration, events, plugins, database, and authentication
— into a single cohesive runtime context.

The module exposes a global :data:`app` singleton that serves as the
entry point for the entire ERP platform.  Subsystems that are built by
other agents (database, auth) are represented as placeholder attributes
that get populated during the full bootstrap sequence in ``run.py``.

Usage::

    from src.core.app import app

    app.initialize()
    db = app.get_service('database')
    app.shutdown()
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from .config import ConfigManager
from .events import EventBus, event_bus
from .exceptions import ERPException
from .plugin_manager import PluginManager
from .utils import ensure_directories

if TYPE_CHECKING:
    pass  # Future: from src.database.engine import DatabaseEngine


logger = logging.getLogger(__name__)


class Application:
    """Central application container and service registry.

    Acts as a lightweight dependency-injection container, holding
    references to every major subsystem.  Services can be registered
    and retrieved by name, enabling loose coupling between modules.

    Attributes:
        config: The configuration manager (populated on :meth:`initialize`).
        event_bus: The global event bus instance.
        plugin_manager: The plugin lifecycle manager.
        db_engine: Database engine (set externally during bootstrap).
        auth_manager: Authentication manager (set externally during bootstrap).
    """

    def __init__(self) -> None:
        """Initialise the application with default subsystems."""
        self._logger = logging.getLogger(__name__)
        self._initialized: bool = False

        # Core subsystems
        self.config: Optional[ConfigManager] = None
        self.event_bus: EventBus = event_bus
        self.plugin_manager: PluginManager = PluginManager()

        # Placeholder subsystems — set by external bootstrap code
        self.db_engine: Any = None
        self.auth_manager: Any = None

        # Service registry
        self._services: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Service registry
    # ------------------------------------------------------------------

    def register_service(self, name: str, service: Any) -> None:
        """Register a service in the dependency-injection container.

        If a service with the same name already exists it is overwritten
        and a warning is logged.

        Args:
            name: Unique identifier for the service.
            service: The service instance to register.
        """
        if name in self._services:
            self._logger.warning('Overwriting existing service: %s', name)
        self._services[name] = service
        self._logger.debug('Service registered: %s', name)

    def get_service(self, name: str) -> Any:
        """Retrieve a previously registered service.

        Args:
            name: The service identifier.

        Returns:
            The registered service instance.

        Raises:
            ERPException: If no service is registered under *name*.
        """
        service = self._services.get(name)
        if service is None:
            raise ERPException(
                f'Service not found: {name}', error_code='SVC_001',
            )
        return service

    def has_service(self, name: str) -> bool:
        """Check whether a service is registered.

        Args:
            name: The service identifier.

        Returns:
            ``True`` if the service exists, ``False`` otherwise.
        """
        return name in self._services

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config_path: Optional[str] = None) -> None:
        """Bootstrap the application.

        Performs the following steps in order:

        1. Load configuration from YAML (or defaults).
        2. Create the standard data directory tree.
        3. Discover available plugins.

        Database and authentication setup are handled externally by
        ``run.py`` after this method returns.

        Args:
            config_path: Optional path to a YAML config file.  When
                ``None`` the default location is used.
        """
        if self._initialized:
            self._logger.warning('Application already initialized')
            return

        self._logger.info('Initializing Enterprise ERP application...')

        # 1. Configuration
        self.config = ConfigManager(config_path)

        # 2. Data directories
        ensure_directories()

        # 3. Plugin discovery
        self.plugin_manager.discover_plugins()

        self._initialized = True
        self._logger.info('Application initialized successfully')

    def shutdown(self) -> None:
        """Gracefully shut down the application.

        Deactivates all active plugins, clears the event bus, and
        empties the service registry.
        """
        self._logger.info('Shutting down application...')

        # Deactivate plugins
        for plugin in list(self.plugin_manager.get_active_plugins()):
            try:
                self.plugin_manager.deactivate_plugin(plugin.name)
            except Exception:
                self._logger.exception(
                    'Error deactivating plugin %s', plugin.name,
                )

        # Clear event subscriptions
        self.event_bus.clear()

        # Clear service registry
        self._services.clear()

        self._initialized = False
        self._logger.info('Application shutdown complete')

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """Whether :meth:`initialize` has been called successfully.

        Returns:
            ``True`` after successful initialisation.
        """
        return self._initialized

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        status = 'initialized' if self._initialized else 'not initialized'
        return f'Application({status}, services={len(self._services)})'


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

app: Application = Application()
"""Global application singleton.

Import this instance rather than creating new :class:`Application` objects
to ensure all modules share the same container.
"""
