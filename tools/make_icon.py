"""«Baraka Dastur» logotipi va launcher ikonkalarini yaratadi (Pillow, tashqi
rasm kerak emas; shrift — assets/fonts/NotoSans-Bold.ttf).

Belgi: yashil fonda krem rangli «B» monogrammasi va tilla rang bug'doy
boshog'i — to'kinlik, ya'ni barakaning an'anaviy ramzi. Jonzot tasviri,
tanga-quti yoki foiz belgisi yo'q (docs/DESIGN_GUIDELINES.md).

Ishga tushirish:  python tools/make_icon.py
Natija:
  android/app/src/main/res/mipmap-*/ic_launcher*.png va adaptive XML;
  assets/branding/logo.png (ilova ichidagi nishon: qulf va xush kelibsiz);
  tools/store/play_icon_512.png, tools/store/feature_graphic_1024x500.png
  (Google Play sahifasi uchun); tools/icon_preview.png (ko'z bilan tekshirish).
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "android" / "app" / "src" / "main" / "res"
FONT = ROOT / "assets" / "fonts" / "NotoSans-Bold.ttf"
FONT_REGULAR = ROOT / "assets" / "fonts" / "NotoSans-Regular.ttf"

# Ranglar lib/app/theme/app_theme.dart dagi DaftarColors bilan bir oila.
GREEN_TOP = (58, 128, 95, 255)
GREEN = (47, 107, 79, 255)  # accent
GREEN_DEEP = (31, 77, 56, 255)
CREAM = (248, 243, 230, 255)  # paper
GOLD = (226, 182, 78, 255)
GOLD_DEEP = (184, 138, 44, 255)

SS = 4  # supersampling

LEGACY = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
ADAPTIVE = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}


def _gradient(size: tuple[int, int], top, bottom) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4)))
    return img


def _grain(length: float, width: float, angle_deg: float, color, outline=None) -> Image.Image:
    """Bitta don: uchli bargsimon shakl, [angle_deg] ga burilgan."""
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


def _wheat(base: Image.Image, x0: float, y0: float, s: float, simple: bool) -> None:
    """Bug'doy boshog'i: pastdan yuqoriga biroz egilgan poya va donlar."""
    d = ImageDraw.Draw(base)
    bottom = (x0 + 0.71 * s, y0 + 0.86 * s)
    top = (x0 + 0.77 * s, y0 + 0.26 * s)
    stem_w = max(2, int((0.034 if simple else 0.026) * s))
    # Poya — kvadratik egri chiziq.
    ctrl = (x0 + 0.80 * s, y0 + 0.58 * s)
    pts = []
    for i in range(41):
        t = i / 40
        x = (1 - t) ** 2 * bottom[0] + 2 * (1 - t) * t * ctrl[0] + t**2 * top[0]
        y = (1 - t) ** 2 * bottom[1] + 2 * (1 - t) * t * ctrl[1] + t**2 * top[1]
        pts.append((x, y))
    d.line(pts, fill=GOLD_DEEP, width=stem_w, joint="curve")

    def at(t: float) -> tuple[float, float, float]:
        x = (1 - t) ** 2 * bottom[0] + 2 * (1 - t) * t * ctrl[0] + t**2 * top[0]
        y = (1 - t) ** 2 * bottom[1] + 2 * (1 - t) * t * ctrl[1] + t**2 * top[1]
        dx = 2 * (1 - t) * (ctrl[0] - bottom[0]) + 2 * t * (top[0] - ctrl[0])
        dy = 2 * (1 - t) * (ctrl[1] - bottom[1]) + 2 * t * (top[1] - ctrl[1])
        return x, y, math.degrees(math.atan2(dx, -dy))

    pairs = 3 if simple else 4
    length = (0.17 if simple else 0.125) * s
    width = (0.085 if simple else 0.060) * s
    outline = None if simple else GOLD_DEEP
    for i in range(pairs):
        t = 0.36 + i * (0.56 / pairs)
        x, y, ang = at(t)
        for side in (-1, 1):
            g = _grain(length, width, ang + side * 32, GOLD, outline)
            off = width * 0.62
            rad = math.radians(ang + side * 90)
            _paste_center(base, g, x + math.sin(rad) * off, y - math.cos(rad) * off)
    # Uchidagi don — tik.
    x, y, ang = at(1.0)
    _paste_center(base, _grain(length, width, ang, GOLD, outline), x, y - length * 0.28)


def _letter(base: Image.Image, x0: float, y0: float, s: float) -> None:
    """Krem rangli «B» — chap tomonda, boshoq uchun joy qoldiriladi."""
    font = ImageFont.truetype(str(FONT), int(0.80 * s))
    d = ImageDraw.Draw(base)
    l, t, r, b = d.textbbox((0, 0), "B", font=font)
    w, h = r - l, b - t
    cx, cy = x0 + 0.38 * s, y0 + 0.53 * s
    d.text((cx - w / 2 - l, cy - h / 2 - t), "B", font=font, fill=CREAM)


def mark(size: int, *, simple: bool | None = None) -> Image.Image:
    """Shaffof fonli belgi (B + boshoq), [size] px kvadrat."""
    if simple is None:
        simple = size <= 48
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    _letter(img, 0, 0, big)
    _wheat(img, 0, 0, big, simple)
    return img.resize((size, size), Image.LANCZOS)


def tile(size: int, *, rounded: bool = True, scale: float = 0.80) -> Image.Image:
    """Yashil gradient fon + belgi (legacy launcher, Play ikonkasi)."""
    big = size * SS
    bg = _gradient((big, big), GREEN_TOP, GREEN_DEEP)
    if rounded:
        m = Image.new("L", (big, big), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, big - 1, big - 1), radius=big * 0.22, fill=255)
        bg.putalpha(m)
    inner = int(big * scale)
    bg.alpha_composite(_mark_big(inner, size <= 48), ((big - inner) // 2, (big - inner) // 2))
    return bg.resize((size, size), Image.LANCZOS)


def _mark_big(px: int, simple: bool) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    _letter(img, 0, 0, px)
    _wheat(img, 0, 0, px, simple)
    return img


def feature_graphic() -> Image.Image:
    w, h = 1024, 500
    img = _gradient((w * 2, h * 2), GREEN_TOP, GREEN_DEEP)
    m = _mark_big(560, simple=False)
    img.alpha_composite(m, (150, (h * 2 - 560) // 2))
    d = ImageDraw.Draw(img)
    title = ImageFont.truetype(str(FONT), 140)
    sub = ImageFont.truetype(str(FONT_REGULAR), 62)
    d.text((800, 345), "Baraka Dastur", font=title, fill=CREAM)
    d.text((806, 550), "Ribosiz shaxsiy moliya", font=sub, fill=GOLD)
    return img.resize((w, h), Image.LANCZOS)


def main() -> None:
    for density, px in LEGACY.items():
        out = RES / f"mipmap-{density}"
        out.mkdir(parents=True, exist_ok=True)
        tile(px, scale=0.86).save(out / "ic_launcher.png")
    for density, px in ADAPTIVE.items():
        # Adaptive foreground shaffof; xavfsiz zona — markazdagi 66 %.
        fg = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        inner = int(px * 0.62)
        fg.alpha_composite(mark(inner), ((px - inner) // 2, (px - inner) // 2))
        fg.save(RES / f"mipmap-{density}" / "ic_launcher_foreground.png")
    anydpi = RES / "mipmap-anydpi-v26"
    anydpi.mkdir(exist_ok=True)
    (anydpi / "ic_launcher.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background"/>\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
        '    <monochrome android:drawable="@mipmap/ic_launcher_foreground"/>\n'
        '</adaptive-icon>\n',
        encoding="utf-8",
    )
    (RES / "values" / "ic_launcher_background.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        '    <color name="ic_launcher_background">#2F6B4F</color>\n</resources>\n',
        encoding="utf-8",
    )
    branding = ROOT / "assets" / "branding"
    branding.mkdir(parents=True, exist_ok=True)
    # Ilova ichida krem sahifada ham ko'rinishi uchun — yashil nishon.
    tile(384, scale=0.86).save(branding / "logo.png")
    store = ROOT / "tools" / "store"
    store.mkdir(parents=True, exist_ok=True)
    tile(512, rounded=False, scale=0.80).convert("RGB").save(store / "play_icon_512.png")
    feature_graphic().convert("RGB").save(store / "feature_graphic_1024x500.png")
    # Ko'z bilan tekshirish uchun prevyu: legacy o'lchamlar + adaptive doira.
    sizes = (16, 24, 48, 96, 192)
    preview = Image.new("RGBA", (sum(sizes) + 10 * len(sizes) + 220, 210), (255, 255, 255, 255))
    x = 10
    for px in sizes:
        preview.alpha_composite(tile(px, scale=0.86), (x, 6))
        x += px + 10
    circle = Image.new("RGBA", (192, 192), GREEN)
    circle.alpha_composite(Image.open(RES / "mipmap-xxxhdpi" / "ic_launcher_foreground.png").resize((192, 192), Image.LANCZOS))
    cm = Image.new("L", (192, 192), 0)
    ImageDraw.Draw(cm).ellipse((0, 0, 191, 191), fill=255)
    circle.putalpha(cm)
    preview.alpha_composite(circle, (x, 6))
    preview.save(ROOT / "tools" / "icon_preview.png")
    print("ikonkalar yozildi:", RES)


if __name__ == "__main__":
    main()
