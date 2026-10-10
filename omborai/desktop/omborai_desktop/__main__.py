import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .config import DesktopConfig
from .offline.store import LocalStore
from .security import get_or_create_db_key, get_or_create_store_key
from .sync.mqtt_sync import MqttSync
from .ui.login import run_login
from .ui.main_window import PosWindow
from .ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OmborAI")
    apply_theme(app)

    config = DesktopConfig.from_env()
    Path(config.local_db_path).parent.mkdir(parents=True, exist_ok=True)
    local = LocalStore(config.local_db_path, key=get_or_create_db_key())
    user = run_login(local)
    if user is None:
        local.close()
        return 0

    mqtt = MqttSync(
        get_or_create_store_key(),
        device_id=local.device_id(),
        apply_op=local.apply_op,
        host=config.mqtt_host,
        port=config.mqtt_port,
        tls=config.mqtt_tls,
    )
    window = PosWindow(config, local=local, mqtt=mqtt)
    window.show()
    window.start()
    code = app.exec()
    mqtt.stop()
    local.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
