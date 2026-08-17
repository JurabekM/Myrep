#!/usr/bin/env python3
"""
Enterprise ERP Platform — Main Entry Point
============================================

Single-command launcher that bootstraps the entire ERP system:

    python run.py

On first run:
    ✓ Creates data directories (db, logs, backups, exports, uploads)
    ✓ Generates config.yaml with sensible defaults
    ✓ Creates SQLite database (or connects to PostgreSQL if available)
    ✓ Runs auto-migrations
    ✓ Seeds default roles, permissions, and admin user
    ✓ Starts Flask web server on localhost:8000 (background thread)
    ✓ Launches PySide6 desktop GUI

No Docker, Node.js, npm, Redis, Nginx, or any external server required.
Only Python.

Admin credentials (first run):
    Username: admin
    Password: admin123
"""

import logging
import os
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_banner() -> None:
    """Display the application startup banner."""
    banner = r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║              ███████╗██████╗ ██████╗                         ║
    ║              ██╔════╝██╔══██╗██╔══██╗                        ║
    ║              █████╗  ██████╔╝██████╔╝                        ║
    ║              ██╔══╝  ██╔══██╗██╔═══╝                         ║
    ║              ███████╗██║  ██║██║                              ║
    ║              ╚══════╝╚═╝  ╚═╝╚═╝                             ║
    ║                                                              ║
    ║              Enterprise ERP Platform v1.0.0                   ║
    ║              Modern ERP for Small & Medium Business           ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def setup_phase(phase_name: str) -> None:
    """Print a formatted phase header during bootstrap.

    Args:
        phase_name: Description of the current setup phase.
    """
    print(f"\n  ► {phase_name}...")


def setup_complete(message: str) -> None:
    """Print a formatted success message.

    Args:
        message: Success description.
    """
    print(f"    ✓ {message}")


def setup_warning(message: str) -> None:
    """Print a formatted warning message.

    Args:
        message: Warning description.
    """
    print(f"    ⚠ {message}")


def setup_error(message: str) -> None:
    """Print a formatted error message.

    Args:
        message: Error description.
    """
    print(f"    ✗ {message}")


def bootstrap() -> dict:
    """Execute the full application bootstrap sequence.

    Returns:
        A dictionary with references to initialized components:
        ``config``, ``db_engine``, ``auth_service``, ``rbac_manager``.

    Raises:
        SystemExit: If a critical bootstrap step fails.
    """
    components = {}

    # ------------------------------------------------------------------
    # Phase 1: Directories
    # ------------------------------------------------------------------
    setup_phase("Creating data directories")
    try:
        from src.core.utils import ensure_directories
        ensure_directories()
        setup_complete("data/db, data/logs, data/backups, data/exports, data/uploads")
    except Exception as exc:
        setup_error(f"Failed to create directories: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 2: Logging
    # ------------------------------------------------------------------
    setup_phase("Configuring logging system")
    try:
        from src.config.logging_config import setup_logging
        root_logger = setup_logging()
        setup_complete("Console + rotating file handler (10MB × 5)")
    except Exception as exc:
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO)
        setup_warning(f"Using basic logging: {exc}")

    logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Phase 3: Configuration
    # ------------------------------------------------------------------
    setup_phase("Loading configuration")
    try:
        from src.core.config import ConfigManager
        config = ConfigManager()
        config.save()
        components['config'] = config
        setup_complete(f"config.yaml (port={config.get('server.port')})")
    except Exception as exc:
        setup_error(f"Configuration failed: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 4: Database
    # ------------------------------------------------------------------
    setup_phase("Initializing database")
    try:
        from src.database.engine import DatabaseEngine
        from src.database.models import Base

        db_config = config.database
        db_engine = DatabaseEngine(db_config)
        db_engine.connect()
        components['db_engine'] = db_engine

        if db_engine.is_postgresql():
            setup_complete("Connected to PostgreSQL")
        else:
            setup_complete(f"SQLite: {db_config.get('path', 'erp_database.db')}")
    except Exception as exc:
        setup_error(f"Database connection failed: {exc}")
        logger.exception("Database initialization error")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 5: Create/Migrate tables
    # ------------------------------------------------------------------
    setup_phase("Running database migrations")
    try:
        from src.database.migration import MigrationManager

        # Import all models so they register with Base.metadata
        _import_all_models()

        migration_mgr = MigrationManager(db_engine)
        migration_mgr.create_tables()

        pending = migration_mgr.check_pending_migrations()
        if pending:
            migration_mgr.apply_migrations()
            setup_complete(f"Applied {len(pending)} migration(s)")
        else:
            setup_complete("Schema up to date")
    except Exception as exc:
        setup_error(f"Migration failed: {exc}")
        logger.exception("Migration error")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 6: Seed initial data
    # ------------------------------------------------------------------
    setup_phase("Seeding initial data")
    try:
        from src.database.seed import DataSeeder

        seeder = DataSeeder(db_engine.get_session)
        if not seeder.is_seeded():
            seeder.seed_all()
            setup_complete("Roles, permissions, admin user, chart of accounts")
            print("\n    ┌─────────────────────────────────────────┐")
            print("    │  Default Admin Credentials:              │")
            print("    │  Username: admin                         │")
            print("    │  Password: admin123                      │")
            print("    │  ⚠ Change password after first login!    │")
            print("    └─────────────────────────────────────────┘")
        else:
            setup_complete("Data already seeded (skipped)")
    except Exception as exc:
        setup_warning(f"Seeding skipped: {exc}")
        logger.exception("Seeding error")

    # ------------------------------------------------------------------
    # Phase 7: Application container
    # ------------------------------------------------------------------
    setup_phase("Initializing application container")
    try:
        from src.core.app import app

        app.config = config
        app.db_engine = db_engine
        app.register_service('config', config)
        app.register_service('database', db_engine)

        # Plugin discovery
        from src.core.plugin_manager import PluginManager
        app.plugin_manager = PluginManager()
        app.plugin_manager.discover_plugins()
        plugins = app.plugin_manager.get_all_plugins()
        if plugins:
            setup_complete(f"Loaded {len(plugins)} plugin(s)")
        else:
            setup_complete("Application container ready (no plugins)")

        components['app'] = app
    except Exception as exc:
        setup_warning(f"App container: {exc}")
        logger.exception("App container error")

    # ------------------------------------------------------------------
    # Phase 8: Auth services
    # ------------------------------------------------------------------
    setup_phase("Initializing authentication system")
    try:
        from src.auth.rbac import RBACManager
        from src.auth.service import AuthService

        rbac_manager = RBACManager(db_engine.get_session)
        auth_service = AuthService(db_engine.get_session, rbac_manager)

        components['rbac_manager'] = rbac_manager
        components['auth_service'] = auth_service

        # Register in app container
        try:
            from src.core.app import app
            app.register_service('auth', auth_service)
            app.register_service('rbac', rbac_manager)
        except Exception:
            pass

        setup_complete("RBAC + Auth service ready")
    except Exception as exc:
        setup_warning(f"Auth system: {exc}")
        logger.exception("Auth initialization error")

    # ------------------------------------------------------------------
    # Phase 9: Auto-backup check
    # ------------------------------------------------------------------
    setup_phase("Checking auto-backup schedule")
    try:
        from src.database.backup import BackupManager

        backup_mgr = BackupManager(db_engine)
        components['backup_manager'] = backup_mgr

        backup_config = config.backup
        if backup_config.get('auto_backup', True):
            backup_created = backup_mgr.auto_backup_check()
            if backup_created:
                setup_complete("Auto-backup created")
            else:
                setup_complete("No backup needed yet")
        else:
            setup_complete("Auto-backup disabled")
    except Exception as exc:
        setup_warning(f"Backup check: {exc}")

    return components


def _import_all_models() -> None:
    """Import all SQLAlchemy model modules to register them with Base.metadata.

    This ensures that ``Base.metadata.create_all()`` picks up every table.
    Models are imported silently — missing modules (from unbuilt phases)
    are ignored.
    """
    model_modules = [
        'src.auth.models',
        'src.modules.sales.models',
        'src.modules.inventory.models',
        'src.modules.accounting.models',
        'src.modules.hr.models',
        'src.modules.crm.models',
    ]
    import importlib
    for module_name in model_modules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            pass
        except Exception:
            logging.getLogger(__name__).debug(
                "Could not import %s", module_name, exc_info=True
            )


def start_web_server(config: dict, components: dict) -> threading.Thread:
    """Start the Flask web server in a background daemon thread.

    Args:
        config: The configuration manager instance.
        components: Bootstrap components dict.

    Returns:
        The daemon thread running the Flask server.
    """
    def _run_flask():
        try:
            from src.api.server import create_flask_app

            flask_app = create_flask_app(components)
            host = config.get('server.host', '0.0.0.0')
            port = config.get('server.port', 8000)
            debug = config.get('server.debug', False)

            flask_app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,
                threaded=True,
            )
        except ImportError:
            logging.getLogger(__name__).info(
                "Flask API module not available yet — web server skipped"
            )
        except Exception:
            logging.getLogger(__name__).exception("Flask server error")

    thread = threading.Thread(target=_run_flask, daemon=True, name="FlaskServer")
    thread.start()
    return thread


def start_desktop_gui(components: dict) -> None:
    """Launch the PySide6 desktop GUI application.

    This blocks until the GUI window is closed.

    Args:
        components: Bootstrap components dict with config, db_engine, etc.
    """
    try:
        from src.ui.app import run_desktop_app
        run_desktop_app(components)
    except ImportError as exc:
        logging.getLogger(__name__).info(
            "Desktop GUI module not available yet: %s", exc
        )
        print("\n  ℹ Desktop GUI not available yet.")
        print("    The web interface is running at:")
        config = components.get('config')
        port = config.get('server.port', 8000) if config else 8000
        print(f"    → http://localhost:{port}")
        print("\n  Press Ctrl+C to stop the server.\n")

        # Keep the main thread alive for the web server
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Shutting down...")


def main() -> None:
    """Main entry point for the Enterprise ERP platform.

    Orchestrates the full startup sequence:
    1. Print banner
    2. Bootstrap all subsystems
    3. Start Flask web server (background)
    4. Launch Desktop GUI (foreground)
    """
    print_banner()
    print("  Starting Enterprise ERP Platform...")
    print("  " + "=" * 50)

    # Bootstrap
    components = bootstrap()

    print("\n  " + "=" * 50)
    print("  ✓ Bootstrap complete!\n")

    # Start web server
    config = components.get('config')
    if config:
        port = config.get('server.port', 8000)
        print(f"  ► Starting web server on http://localhost:{port}")
        web_thread = start_web_server(config, components)
        time.sleep(0.5)  # Give Flask a moment to bind
        setup_complete(f"Web server running at http://localhost:{port}")
    else:
        print("  ⚠ Config not available — web server skipped")

    # Launch desktop GUI
    print("\n  ► Launching Desktop GUI...")
    start_desktop_gui(components)

    # Cleanup
    print("\n  Shutting down Enterprise ERP Platform...")
    try:
        from src.core.app import app
        app.shutdown()
    except Exception:
        pass

    db_engine = components.get('db_engine')
    if db_engine:
        try:
            db_engine.close()
        except Exception:
            pass

    print("  ✓ Goodbye!\n")


if __name__ == '__main__':
    main()
