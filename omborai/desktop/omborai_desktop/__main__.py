import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .api import ApiClient
from .config import DesktopConfig
from .offline.store import LocalStore
from .security import get_or_create_db_key
from .ui.login import run_login
from .ui.main_window import PosWindow
from .ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OmborAI")
    apply_theme(app)

    config = DesktopConfig.from_env()
    api = ApiClient(config.api_base_url)
    if not run_login(api):
        return 0

    Path(config.local_db_path).parent.mkdir(parents=True, exist_ok=True)
    local = LocalStore(config.local_db_path, key=get_or_create_db_key())
    window = PosWindow(api, config, local=local)
    window.show()
    window.start()
    code = app.exec()
    local.close()
    api.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
