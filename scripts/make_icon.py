"""«Baraka Dastur» desktop ikonkalarini yaratadi (Pillow). Chizma — `scripts/baraka_logo.py` (mobil bilan bir xil).

Ishga tushirish (repo ildizidan):
    python scripts/make_icon.py

Natija: src-tauri/icons/ papkasida PNG (32, 128, 256, 512), icon.ico (16–256) va icon.icns; ilova ichidagi
belgi `ui/src/app/components/brand-mark.png` (yon panel va qulf ekrani, 32–40 px da ko'rsatiladi).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from baraka_logo import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "src-tauri" / "icons"
UI_MARK = ROOT / "ui" / "src" / "app" / "components" / "brand-mark.png"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for size, name in ((32, "32x32.png"), (128, "128x128.png"), (256, "128x128@2x.png"), (512, "icon.png")):
        render(size).save(OUT_DIR / name, format="PNG")

    frames = [render(size) for size in ICO_SIZES]
    # Pillow qoidasi: asosiy rasm eng katta bo'lishi kerak. Qolgan o'lchamlar append_images orqali
    # o'z chizmasi bilan yoziladi; aks holda ular kattaroq rasmdan kichraytirilib, detallar yo'qoladi.
    frames[-1].save(
        OUT_DIR / "icon.ico",
        format="ICO",
        sizes=[(size, size) for size in ICO_SIZES],
        append_images=frames[:-1],
    )

    render(1024).save(OUT_DIR / "icon.icns", format="ICNS")
    # 32–40 px da (2× DPI gacha) ko'rinadi: soddalashtirilgan boshoq aniqroq.
    render(96, simple=True).save(UI_MARK, format="PNG", optimize=True)
    print(f"Ikonkalar yozildi: {OUT_DIR}")


if __name__ == "__main__":
    main()
