import sys

from PySide6.QtWidgets import QApplication

from .api import ApiClient
from .config import DesktopConfig
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

    window = PosWindow(api, config)
    window.show()
    window.start()
    code = app.exec()
    api.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
