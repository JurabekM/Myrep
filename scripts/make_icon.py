"""Baraka Daftari ikonkasini yaratadi (Pillow). Tashqi rasm fayli talab qilinmaydi.

Ishga tushirish (repo ildizidan):
    python scripts/make_icon.py

Natija: src-tauri/icons/ papkasida PNG (32, 128, 256, 512), icon.ico (16–256) va icon.icns.

Dizayn: qorong'i fon (Claude Code dark uslubi), krem rangli «daftar» sahifasi va geometrik
sakkiz burchakli yulduz (islomiy naqsh). Jonzot, cho'chqa (piggy bank), qimor, alkogol, bank binosi
va foiz belgilari ishlatilmaydi. Kichik o'lchamlar (48 px dan kichik) uchun detallar tashlanadi:
ingichka chiziqlar 16–32 px da yo'qoladi, shuning uchun har o'lcham alohida chiziladi.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "src-tauri" / "icons"

# Ranglar src/styles/globals.css dagi dizayn tokenlari bilan bir xil.
BG_TOP = (44, 43, 40, 255)  # #2c2b28
BG_BOTTOM = (31, 30, 29, 255)  # #1f1e1d
PAGE = (240, 238, 230, 255)  # #f0eee6
CLAY = (217, 119, 87, 255)  # #d97757
RULE = (201, 196, 180, 255)  # #c9c4b4

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
DETAIL_MIN_SIZE = 48  # shundan kichik o'lchamda detallar chizilmaydi


def star_points(cx: float, cy: float, r_outer: float, r_inner: float) -> list[tuple[float, float]]:
    """Sakkiz burchakli yulduzning 16 ta nuqtasi (yuqori cho'qqidan boshlanadi)."""
    points: list[tuple[float, float]] = []
    for k in range(16):
        radius = r_outer if k % 2 == 0 else r_inner
        angle = math.radians(-90 + k * 22.5)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def background(n: int) -> Image.Image:
    """Yuqoridan pastga gradiyentli, burchaklari yumaloq fon."""
    gradient = Image.new("RGBA", (n, n))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(n):
        t = y / (n - 1)
        color = tuple(round(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(4))
        grad_draw.line([(0, y), (n - 1, y)], fill=color)

    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, n - 1, n - 1], radius=round(n * 0.2225), fill=255
    )

    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    img.paste(gradient, (0, 0), mask)
    return img


def render(size: int) -> Image.Image:
    """Bitta o'lcham uchun alohida chizadi: avval katta, keyin silliq kichraytiriladi."""
    supersample = 4 if size <= 256 else 2
    n = size * supersample

    def u(value: float) -> float:
        """Birlik koordinatasini (0..1) piksel koordinatasiga o'tkazadi."""
        return value * n

    img = background(n)
    draw = ImageDraw.Draw(img)
    detailed = size >= DETAIL_MIN_SIZE

    # Daftar sahifasi
    draw.rounded_rectangle([u(0.25), u(0.21), u(0.75), u(0.83)], radius=u(0.045), fill=PAGE)

    # Geometrik yulduz — asosiy belgi, barcha o'lchamlarda ko'rinadi
    radius = 0.19 if detailed else 0.23
    draw.polygon(star_points(u(0.5), u(0.47), u(radius), u(radius * 0.625)), fill=CLAY)

    if detailed:
        # Daftar halqalari (yuqori chekka)
        for x in (0.37, 0.50, 0.63):
            draw.rounded_rectangle(
                [u(x - 0.035), u(0.175), u(x + 0.035), u(0.245)], radius=u(0.035), fill=CLAY
            )
        # Yozuv chiziqlari (pastki qism)
        for y in (0.72, 0.78):
            draw.line(
                [(u(0.36), u(y)), (u(0.64), u(y))], fill=RULE, width=max(1, round(u(0.018)))
            )

    return img.resize((size, size), Image.Resampling.LANCZOS)


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
    print(f"Ikonkalar yozildi: {OUT_DIR}")


if __name__ == "__main__":
    main()
