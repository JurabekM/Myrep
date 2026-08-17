"""Plugin architecture for the Enterprise ERP platform.

Provides a two-class system for extensibility:

- :class:`PluginBase` — abstract base class that all plugins must subclass.
- :class:`PluginManager` — discovers, loads, and manages plugin lifecycles.

Plugins are discovered from a ``plugins/`` directory at the project root.
Each plugin must be a Python package (directory with ``__init__.py``) that
contains at least one class inheriting from :class:`PluginBase`.

Plugin lifecycle::

    discover_plugins()  →  load_plugin()  →  activate_plugin()
                                                      │
                                              deactivate_plugin()

Example plugin structure::

    plugins/
    └── my_plugin/
        ├── __init__.py   # contains class MyPlugin(PluginBase): ...
        └── views.py
"""

import importlib.util
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import PluginError
from .utils import get_project_root


class PluginBase(ABC):
    """Abstract base class for ERP plugins.

    All plugins must inherit from this class and implement the required
    :meth:`activate` and :meth:`deactivate` methods.  Optional hooks
    allow plugins to contribute menu items and API routes.

    Attributes:
        name: Human-readable plugin name.
        version: Semantic version string.
        description: Short description of the plugin's purpose.
        author: Plugin author or organisation name.
    """

    name: str = 'Unnamed Plugin'
    version: str = '0.1.0'
    description: str = ''
    author: str = ''

    @abstractmethod
    def activate(self, app: Any) -> None:
        """Activate the plugin within the application context.

        Called when the plugin is enabled.  The *app* reference provides
        access to the service registry, event bus, and configuration.

        Args:
            app: The :class:`~src.core.app.Application` instance.
        """

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the plugin and release all acquired resources.

        Called when the plugin is disabled or during application shutdown.
        """

    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Return menu items to register in the application UI.

        Each dictionary should contain at minimum:
        ``{'label': str, 'icon': str, 'route': str}``.

        Returns:
            A list of menu item definition dictionaries, or an empty list.
        """
        return []

    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Return API route definitions contributed by this plugin.

        Each dictionary should contain at minimum:
        ``{'path': str, 'method': str, 'handler': Callable}``.

        Returns:
            A list of route definition dictionaries, or an empty list.
        """
        return []

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        return f'Plugin({self.name} v{self.version})'


class PluginManager:
    """Manages plugin discovery, loading, activation, and deactivation.

    Maintains two registries: one for all discovered/loaded plugins and
    one for currently active plugins.

    Attributes:
        _plugins: All discovered plugins keyed by name.
        _active: Currently active plugins keyed by name.
    """

    def __init__(self) -> None:
        """Initialise the plugin manager with empty registries."""
        self._plugins: Dict[str, PluginBase] = {}
        self._active: Dict[str, PluginBase] = {}
        self._logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Discovery and loading
    # ------------------------------------------------------------------

    def discover_plugins(
        self, plugins_dir: Optional[str] = None,
    ) -> List[str]:
        """Scan a directory for plugin packages and load them.

        Each immediate sub-directory containing an ``__init__.py`` is
        treated as a candidate plugin.

        Args:
            plugins_dir: Absolute or relative path to the plugins directory.
                Defaults to ``<project_root>/plugins``.

        Returns:
            Names of successfully discovered plugins.
        """
        if plugins_dir is None:
            plugins_path = Path(get_project_root()) / 'plugins'
        else:
            plugins_path = Path(plugins_dir)

        discovered: List[str] = []
        if not plugins_path.exists():
            self._logger.info(
                'Plugins directory not found: %s', plugins_path,
            )
            return discovered

        for item in sorted(plugins_path.iterdir()):
            if item.is_dir() and (item / '__init__.py').exists():
                try:
                    self.load_plugin(str(item))
                    discovered.append(item.name)
                except PluginError as exc:
                    self._logger.error(
                        'Failed to load plugin %s: %s', item.name, exc,
                    )

        self._logger.info('Discovered %d plugin(s)', len(discovered))
        return discovered

    def load_plugin(self, plugin_path: str) -> None:
        """Load a single plugin from the given directory path.

        The directory must contain an ``__init__.py`` with at least one
        class that inherits from :class:`PluginBase`.

        Args:
            plugin_path: Absolute path to the plugin package directory.

        Raises:
            PluginError: If the path is invalid, the module cannot be
                imported, or no :class:`PluginBase` subclass is found.
        """
        path = Path(plugin_path)
        if not path.exists():
            raise PluginError(f'Plugin path does not exist: {plugin_path}')

        init_file = path / '__init__.py'
        if not init_file.exists():
            raise PluginError(
                f'Plugin missing __init__.py: {plugin_path}',
            )

        try:
            module_name = f'plugins.{path.name}'
            spec = importlib.util.spec_from_file_location(
                module_name, str(init_file),
            )
            if spec is None or spec.loader is None:
                raise PluginError(
                    f'Cannot create module spec for {path.name}',
                )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]

            # Locate the first PluginBase subclass
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                raise PluginError(
                    f'No PluginBase subclass found in {path.name}',
                )

            instance = plugin_class()
            self._plugins[instance.name] = instance
            self._logger.info(
                'Loaded plugin: %s v%s', instance.name, instance.version,
            )

        except PluginError:
            raise
        except Exception as exc:
            raise PluginError(
                f'Error loading plugin {path.name}: {exc}',
            ) from exc

    # ------------------------------------------------------------------
    # Activation / deactivation
    # ------------------------------------------------------------------

    def activate_plugin(self, name: str, app: Any = None) -> None:
        """Activate a previously loaded plugin.

        Args:
            name: The plugin's registered name.
            app: The :class:`~src.core.app.Application` instance passed
                to :meth:`PluginBase.activate`.

        Raises:
            PluginError: If the plugin is unknown or activation fails.
        """
        if name not in self._plugins:
            raise PluginError(f'Plugin not found: {name}')
        if name in self._active:
            self._logger.warning('Plugin already active: %s', name)
            return

        plugin = self._plugins[name]
        try:
            plugin.activate(app)
            self._active[name] = plugin
            self._logger.info('Activated plugin: %s', name)
        except Exception as exc:
            raise PluginError(
                f'Failed to activate plugin {name}: {exc}',
            ) from exc

    def deactivate_plugin(self, name: str) -> None:
        """Deactivate a currently active plugin.

        Args:
            name: The plugin's registered name.

        Raises:
            PluginError: If the plugin is not currently active or
                deactivation fails.
        """
        if name not in self._active:
            raise PluginError(f'Plugin not active: {name}')

        plugin = self._active[name]
        try:
            plugin.deactivate()
            del self._active[name]
            self._logger.info('Deactivated plugin: %s', name)
        except Exception as exc:
            raise PluginError(
                f'Error deactivating plugin {name}: {exc}',
            ) from exc

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_active_plugins(self) -> List[PluginBase]:
        """Return all currently active plugins.

        Returns:
            A list of :class:`PluginBase` instances.
        """
        return list(self._active.values())

    def get_all_plugins(self) -> List[PluginBase]:
        """Return all discovered plugins (active and inactive).

        Returns:
            A list of :class:`PluginBase` instances.
        """
        return list(self._plugins.values())

    def is_active(self, name: str) -> bool:
        """Check whether a plugin is currently active.

        Args:
            name: The plugin's registered name.

        Returns:
            ``True`` if the plugin is active, ``False`` otherwise.
        """
        return name in self._active

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        return (
            f'PluginManager(loaded={len(self._plugins)}, '
            f'active={len(self._active)})'
        )
