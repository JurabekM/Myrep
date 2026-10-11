import sys
from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from .config import DesktopConfig
from .offline.store import LocalStore
from .security import get_or_create_db_key, get_or_create_device_seed, get_or_create_store_key
from .sync.identity import DeviceIdentity
from .sync.mqtt_sync import MqttSync
from .ui.bootstrap import wait_for_store
from .ui.login import run_login
from .ui.main_window import PosWindow
from .ui.theme import apply_theme

EXIT_WAIT_MS = 10_000  # paho connect_timeout (5 s) dan katta: chiqishdan oldin ulanish urinishi tugaydi


def _make_sync(local: LocalStore, config: DesktopConfig) -> MqttSync:
    return MqttSync(
        get_or_create_store_key(),
        device_id=local.device_id(),
        apply_op=local.apply_op,
        host=config.mqtt_host,
        port=config.mqtt_port,
        tls=config.mqtt_tls,
    )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OmborAI")
    apply_theme(app)

    config = DesktopConfig.from_env()
    Path(config.local_db_path).parent.mkdir(parents=True, exist_ok=True)
    identity = DeviceIdentity(get_or_create_device_seed())
    local = LocalStore(config.local_db_path, key=get_or_create_db_key(), identity=identity)
    mqtt: MqttSync | None = None

    def bootstrap() -> bool:
        # Juftlangan qurilma: do'kon ma'lumoti (snapshot) kelguncha login oynasi ochilmaydi
        nonlocal mqtt
        mqtt = _make_sync(local, config)
        return wait_for_store(local, mqtt)

    user = run_login(local, bootstrap=bootstrap)
    if user is None:
        # Ulanish urinishi hali davom etayotgan bo'lsa, tugashini kutamiz: aks holda stop() bilan poyga
        QThreadPool.globalInstance().waitForDone(EXIT_WAIT_MS)
        if mqtt is not None:
            mqtt.stop()
        local.close()
        return 0

    if mqtt is None:
        mqtt = _make_sync(local, config)
    window = PosWindow(config, local=local, mqtt=mqtt, user=user)
    window.show()
    window.start()
    code = app.exec()
    mqtt.stop()
    local.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
