import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DesktopConfig:
    api_base_url: str = "http://127.0.0.1:8000"
    store_name_fallback: str = "OmborAI"
    printer_host: str | None = None  # bo'sh bo'lsa chek faqat ekranda ko'rsatiladi
    receipt_width: int = 32

    @classmethod
    def from_env(cls) -> "DesktopConfig":
        return cls(
            api_base_url=os.environ.get("OMBORAI_API_URL", cls.api_base_url),
            printer_host=os.environ.get("OMBORAI_PRINTER_HOST") or None,
            receipt_width=int(os.environ.get("OMBORAI_RECEIPT_WIDTH", "32")),
        )
