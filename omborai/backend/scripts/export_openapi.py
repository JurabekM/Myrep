"""OpenAPI shartnomasini ../shared/openapi.json ga yozadi (desktop va mobil klientlar shundan foydalanadi)."""

import json
import os
from pathlib import Path

# Eksport uchun sozlamalar muhim emas, lekin modul import qilinganda tekshiriladi
os.environ.setdefault("OMBORAI_ENV", "dev")

from app.main import create_app  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "shared" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"yozildi: {OUT}")


if __name__ == "__main__":
    main()
