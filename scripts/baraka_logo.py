"""«Baraka Dastur» logotipi — desktop va Android uchun bitta manba (Pillow, tashqi rasm yoki shrift kerak emas).

Belgi: yashil fonda krem rangli geometrik «B» harfi va oltin sakkiz burchakli yulduz («baraka»). Harf
shriftsiz, to'rtburchak va yumaloq shakllardan quriladi — shrift litsenziyasiga bog'liq emas. Jonzot, qo'l,
cho'chqa (piggy bank), qimor, alkogol, bank binosi va foiz belgilari ishlatilmaydi.

Kichik o'lchamlarda (< 48 px) yulduz chizilmaydi va harf biroz qalinlashadi: aks holda detal 16–32 px da
loyqa dog'ga aylanadi. Har o'lcham 4× katta chizilib, keyin kichraytiriladi (silliq qirralar).

Bu fayl modul sifatida ishlatiladi: `scripts/make_icon.py` (desktop) va mobil `tools/make_icon.py` shu yerdagi
`render()` ni chaqiradi.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

GREEN_TOP = (52, 120, 88, 255)  # #347858
GREEN_BOTTOM = (28, 74, 54, 255)  # #1c4a36
CREAM = (248, 243, 230, 255)  # #f8f3e6
GOLD = (222, 177, 72, 255)  # #deb148

SS = 4  # supersampling
DETAIL_MIN = 48  # shundan kichik o'lchamda yulduz chizilmaydi


def star_points(cx: float, cy: float, r_outer: float, r_inner: float) -> list[tuple[float, float]]:
    """Sakkiz burchakli yulduzning 16 nuqtasi (yuqori cho'qqidan)."""
    pts: list[tuple[float, float]] = []
    for k in range(16):
        radius = r_outer if k % 2 == 0 else r_inner
        angle = math.radians(-90 + k * 22.5)
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return pts


def letter_mask(n: int, x0: float, y0: float, s: float, bold: bool) -> Image.Image:
    """`s` o'lchamli kvadrat ichida (x0, y0 dan) «B» harfi niqobi (L rejim, 255 — harf)."""
    mask = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mask)

    def box(a: float, b: float, c: float, e: float) -> tuple[float, float, float, float]:
        return (x0 + a * s, y0 + b * s, x0 + c * s, y0 + e * s)

    stroke = 0.14 if bold else 0.11
    top, bottom, left = 0.17, 0.83, 0.27
    middle = 0.475
    up_right, low_right = 0.66, 0.71
    up_h = middle + stroke / 2 - top
    low_h = bottom - (middle - stroke / 2)
    # Yuqori va pastki «qorin»: o'ng tomoni to'liq yumaloq (radius = balandlikning yarmi).
    d.rounded_rectangle(box(left, top, up_right, middle + stroke / 2), radius=up_h / 2 * s, fill=255)
    d.rounded_rectangle(box(left, middle - stroke / 2, low_right, bottom), radius=low_h / 2 * s, fill=255)
    # Ichki bo'shliqlar (counter).
    d.rounded_rectangle(
        box(left + stroke, top + stroke, up_right - stroke, middle - stroke / 2),
        radius=(up_h / 2 - stroke) * s,
        fill=0,
    )
    d.rounded_rectangle(
        box(left + stroke, middle + stroke / 2, low_right - stroke, bottom - stroke),
        radius=(low_h / 2 - stroke) * s,
        fill=0,
    )
    # Vertikal ustun: chap qirra to'g'ri, burchaklari to'g'ri.
    d.rectangle(box(left, top, left + stroke, bottom), fill=255)
    return mask


def render(size: int, *, background: bool = True, scale: float = 1.0, rounded: bool = True) -> Image.Image:
    """`size` px logotip. `background=False` — faqat belgi (Android adaptive foreground uchun).

    `scale` — belgining kvadratdagi ulushi (adaptive ikonka xavfsiz zonasi uchun kichraytiriladi).
    """
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    if background:
        grad = Image.new("RGBA", (n, n))
        gd = ImageDraw.Draw(grad)
        for y in range(n):
            t = y / max(n - 1, 1)
            gd.line(
                [(0, y), (n - 1, y)],
                fill=tuple(round(GREEN_TOP[i] + (GREEN_BOTTOM[i] - GREEN_TOP[i]) * t) for i in range(4)),
            )
        shape = Image.new("L", (n, n), 0)
        if rounded:
            ImageDraw.Draw(shape).rounded_rectangle([0, 0, n - 1, n - 1], radius=round(n * 0.2225), fill=255)
        else:
            shape.paste(255, (0, 0, n, n))
        img.paste(grad, (0, 0), shape)

    detailed = size >= DETAIL_MIN
    s = n * scale
    x0 = (n - s) / 2
    y0 = (n - s) / 2
    # Yulduz bo'lsa, harf biroz chapga suriladi — kompozitsiya muvozanati.
    letter_x = x0 - (0.04 * s if detailed else -0.02 * s)
    mask = letter_mask(n, letter_x, y0, s, bold=not detailed)
    cream = Image.new("RGBA", (n, n), CREAM)
    img.paste(cream, (0, 0), mask)
    if detailed:
        ImageDraw.Draw(img).polygon(
            star_points(x0 + 0.79 * s, y0 + 0.25 * s, 0.10 * s, 0.05 * s), fill=GOLD
        )
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    from pathlib import Path

    preview = Image.new("RGBA", (1100, 300), (30, 30, 30, 255))
    x = 20
    for px in (256, 128, 64, 48, 32, 24, 16):
        preview.paste(render(px), (x, 20), render(px))
        x += px + 20
    out = Path(__file__).resolve().parent / "logo_preview.png"
    preview.save(out)
    print(out)
