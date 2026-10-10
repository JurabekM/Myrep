import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DesktopConfig:
    api_base_url: str = "http://127.0.0.1:8000"
    store_name_fallback: str = "OmborAI"
    printer_host: str | None = None  # bo'sh bo'lsa chek faqat ekranda ko'rsatiladi
    receipt_width: int = 32
    local_db_path: str = str(Path.home() / ".omborai" / "local.db")
    mqtt_host: str = "broker.hivemq.com"
    mqtt_port: int = 8883
    mqtt_tls: bool = True

    @classmethod
    def from_env(cls) -> "DesktopConfig":
        return cls(
            api_base_url=os.environ.get("OMBORAI_API_URL", cls.api_base_url),
            printer_host=os.environ.get("OMBORAI_PRINTER_HOST") or None,
            receipt_width=int(os.environ.get("OMBORAI_RECEIPT_WIDTH", "32")),
            local_db_path=os.environ.get("OMBORAI_LOCAL_DB", cls.local_db_path),
            mqtt_host=os.environ.get("OMBORAI_MQTT_HOST", cls.mqtt_host),
            mqtt_port=int(os.environ.get("OMBORAI_MQTT_PORT", str(cls.mqtt_port))),
            mqtt_tls=os.environ.get("OMBORAI_MQTT_TLS", "1") == "1",
        )
