"""«Baraka Dastur» logotipi — desktop uchun chizma (Pillow). Mobil `tools/make_icon.py` dagi belgi bilan aynan bir xil.

Belgi: yashil gradient fonda krem rangli «B» va tilla rang bug'doy boshog'i — to'kinlik, ya'ni barakaning
an'anaviy ramzi. Jonzot, qo'l, cho'chqa (piggy bank), qimor, alkogol, bank binosi va foiz belgisi ishlatilmaydi.

Ranglar, shrift (`scripts/fonts/NotoSans-Bold.ttf`, OFL — mobil `assets/fonts` dagi fayl bilan bayt-bir xil)
va geometriya mobil ilova bilan bir xil. Belgi o'zgarsa, ikkala faylni birga yangilang.

Kichik o'lchamlarda (≤ 48 px) boshoq soddalashadi: donlar kamroq va yo'g'onroq, chegarasiz. Har o'lcham 4× katta
chizilib, keyin kichraytiriladi (silliq qirralar).
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = Path(__file__).resolve().parent / "fonts" / "NotoSans-Bold.ttf"

GREEN_TOP = (58, 128, 95, 255)  # #3a805f
GREEN = (47, 107, 79, 255)  # #2f6b4f
GREEN_DEEP = (31, 77, 56, 255)  # #1f4d38
CREAM = (248, 243, 230, 255)  # #f8f3e6
GOLD = (226, 182, 78, 255)  # #e2b64e
GOLD_DEEP = (184, 138, 44, 255)  # #b88a2c

SS = 4  # supersampling
SIMPLE_MAX = 48  # shu o'lchamgacha boshoq soddalashtiriladi


def _gradient(size: tuple[int, int], top, bottom) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4)))
    return img


def _grain(length: float, width: float, angle_deg: float, color, outline=None) -> Image.Image:
    """Bitta don: uchli bargsimon shakl, `angle_deg` ga burilgan."""
    w, h = int(width * 2) + 4, int(length * 2) + 4
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = w / 2, h / 2
    pts = []
    for i in range(64):
        a = 2 * math.pi * i / 64
        # Ellips, uchlari biroz o'tkirlashtirilgan.
        x = math.sin(a) * width / 2 * (abs(math.sin(a)) ** 0.15)
        y = -math.cos(a) * length / 2
        pts.append((cx + x, cy + y))
    d.polygon(pts, fill=color, outline=outline, width=max(1, int(width * 0.09)) if outline else 1)
    return img.rotate(-angle_deg, resample=Image.BICUBIC, expand=True)


def _paste_center(base: Image.Image, img: Image.Image, cx: float, cy: float) -> None:
    base.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def _wheat(base: Image.Image, s: float, simple: bool) -> None:
    """Bug'doy boshog'i: pastdan yuqoriga biroz egilgan poya va donlar."""
    d = ImageDraw.Draw(base)
    bottom = (0.71 * s, 0.86 * s)
    top = (0.77 * s, 0.26 * s)
    ctrl = (0.80 * s, 0.58 * s)
    stem_w = max(2, int((0.034 if simple else 0.026) * s))

    def at(t: float) -> tuple[float, float, float]:
        x = (1 - t) ** 2 * bottom[0] + 2 * (1 - t) * t * ctrl[0] + t**2 * top[0]
        y = (1 - t) ** 2 * bottom[1] + 2 * (1 - t) * t * ctrl[1] + t**2 * top[1]
        dx = 2 * (1 - t) * (ctrl[0] - bottom[0]) + 2 * t * (top[0] - ctrl[0])
        dy = 2 * (1 - t) * (ctrl[1] - bottom[1]) + 2 * t * (top[1] - ctrl[1])
        return x, y, math.degrees(math.atan2(dx, -dy))

    d.line([at(i / 40)[:2] for i in range(41)], fill=GOLD_DEEP, width=stem_w, joint="curve")

    pairs = 3 if simple else 4
    length = (0.17 if simple else 0.125) * s
    width = (0.085 if simple else 0.060) * s
    outline = None if simple else GOLD_DEEP
    for i in range(pairs):
        x, y, ang = at(0.36 + i * (0.56 / pairs))
        for side in (-1, 1):
            grain = _grain(length, width, ang + side * 32, GOLD, outline)
            off = width * 0.62
            rad = math.radians(ang + side * 90)
            _paste_center(base, grain, x + math.sin(rad) * off, y - math.cos(rad) * off)
    # Uchidagi don — tik.
    x, y, ang = at(1.0)
    _paste_center(base, _grain(length, width, ang, GOLD, outline), x, y - length * 0.28)


def _letter(base: Image.Image, s: float) -> None:
    """Krem rangli «B» — chap tomonda, boshoq uchun joy qoldiriladi."""
    font = ImageFont.truetype(str(FONT), int(0.80 * s))
    d = ImageDraw.Draw(base)
    l, t, r, b = d.textbbox((0, 0), "B", font=font)
    cx, cy = 0.38 * s, 0.53 * s
    d.text((cx - (r - l) / 2 - l, cy - (b - t) / 2 - t), "B", font=font, fill=CREAM)


def _mark(px: int, simple: bool) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    _letter(img, px)
    _wheat(img, px, simple)
    return img


def render(size: int, *, rounded: bool = True, scale: float = 0.86, simple: bool | None = None) -> Image.Image:
    """`size` px ikonka: yashil gradient fon + belgi (mobil `tile()` bilan bir xil).

    `simple=None` — o'lchamga qarab (≤ 48 px soddalashtirilgan boshoq).
    """
    if simple is None:
        simple = size <= SIMPLE_MAX
    big = size * SS
    bg = _gradient((big, big), GREEN_TOP, GREEN_DEEP)
    if rounded:
        m = Image.new("L", (big, big), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, big - 1, big - 1), radius=big * 0.22, fill=255)
        bg.putalpha(m)
    inner = int(big * scale)
    bg.alpha_composite(_mark(inner, simple), ((big - inner) // 2, (big - inner) // 2))
    return bg.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    sizes = (256, 128, 64, 48, 32, 24, 16)
    preview = Image.new("RGBA", (sum(sizes) + 20 * (len(sizes) + 1), 300), (30, 30, 30, 255))
    x = 20
    for px in sizes:
        preview.alpha_composite(render(px), (x, 20))
        x += px + 20
    out = Path(__file__).resolve().parent / "logo_preview.png"
    preview.save(out)
    print(out)
