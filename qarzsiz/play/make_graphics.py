#!/usr/bin/env python3
"""Google Play grafikasi: ikona (512×512), feature graphic (1024×500) va telefon skrinshotlari.

    cd qarzsiz/android && ./gradlew :app:testDebugUnitTest --tests '*StoreScreenshotsTest'
    python3 -I qarzsiz/play/make_graphics.py

Ikona `app/src/main/res/drawable/ic_launcher_foreground.xml` dagi yo'llarning o'zi (viewport 108),
4× katta chizilib kichraytiriladi (silliq chiziq). Kerak: Pillow.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONTS = ROOT / "android/app/src/main/res/font"
SHOTS = ROOT / "android/app/build/outputs/play"

PAPER = (0x26, 0x26, 0x24)
SIDEBAR = (0x1F, 0x1E, 0x1D)
INK = (0xFA, 0xF9, 0xF5)
INK_MUTED = (0xA6, 0xA3, 0x9A)
ACCENT = (0xD9, 0x77, 0x57)
ACCENT_TEXT = (0xE8, 0x95, 0x7A)

# ic_launcher_foreground.xml: (rang, [segmentlar]); segment — nuqtalar ro'yxati (L) yoki bezye (C).
PATHS = [
    (INK, [("M", (48, 40)), ("L", (40, 40)), ("C", (33, 40), (28, 46), (28, 54)),
           ("C", (28, 62), (33, 68), (40, 68)), ("L", (46, 68))]),
    (ACCENT, [("M", (62, 40)), ("L", (68, 40)), ("C", (75, 40), (80, 46), (80, 54)),
              ("C", (80, 62), (75, 68), (68, 68)), ("L", (60, 68))]),
    (ACCENT, [("M", (54, 62)), ("L", (54, 32))]),
    (ACCENT, [("M", (45, 41)), ("L", (54, 32)), ("L", (63, 41))]),
]
STROKE = 5.0


def _polyline(segs):
    pts = []
    cur = None
    for seg in segs:
        kind = seg[0]
        if kind == "M":
            cur = seg[1]
            pts.append(cur)
        elif kind == "L":
            cur = seg[1]
            pts.append(cur)
        else:
            p0, (c1, c2, p3) = cur, seg[1:]
            for i in range(1, 25):
                t = i / 24
                x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t ** 2 * c2[0] + t ** 3 * p3[0]
                y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t ** 2 * c2[1] + t ** 3 * p3[1]
                pts.append((x, y))
            cur = p3
    return pts


def draw_mark(img: Image.Image, cx: float, cy: float, scale: float) -> None:
    """Belgini (markazi viewport'da (54, 50)) `img` ga (cx, cy) markazda chizadi.

    Chiziq yumaloq «mo'yqalam» bilan: yo'l bo'ylab har ~1 pikselda doira — bo'g'imlarda tikan qolmaydi,
    uchlari yumaloq (strokeLineCap="round" kabi).
    """
    d = ImageDraw.Draw(img)
    r = STROKE * scale / 2
    for color, segs in PATHS:
        pts = [((x - 54) * scale + cx, (y - 50) * scale + cy) for x, y in _polyline(segs)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            steps = max(1, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5))
            for i in range(steps + 1):
                x = x0 + (x1 - x0) * i / steps
                y = y0 + (y1 - y0) * i / steps
                d.ellipse((x - r, y - r, x + r, y + r), fill=color)


def icon(path: Path) -> None:
    ss = 4
    big = Image.new("RGB", (512 * ss, 512 * ss), SIDEBAR)
    draw_mark(big, 256 * ss, 256 * ss, 512 / 84 * ss)
    big.resize((512, 512), Image.LANCZOS).save(path, optimize=True)


def feature(path: Path) -> None:
    ss = 2
    W, H = 1024 * ss, 500 * ss
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # Chapda — ikona kartochkasi
    box = (96 * ss, 110 * ss, 376 * ss, 390 * ss)
    d.rounded_rectangle(box, radius=56 * ss, fill=SIDEBAR)
    draw_mark(img, 236 * ss, 250 * ss, 280 / 72 * ss)
    bold = ImageFont.truetype(str(FONTS / "noto_sans_bold.ttf"), 92 * ss)
    sub = ImageFont.truetype(str(FONTS / "noto_sans_bold.ttf"), 38 * ss)
    small = ImageFont.truetype(str(FONTS / "noto_sans_regular.ttf"), 27 * ss)
    x = 430 * ss
    d.text((x, 118 * ss), "Qarzsiz", font=bold, fill=INK)
    d.text((x, 250 * ss), "Qarzdan reja bilan chiqing", font=sub, fill=ACCENT_TEXT)
    d.text((x, 318 * ss), "Offlayn · shifrlangan · lotin va kirill", font=small, fill=INK_MUTED)
    img.resize((1024, 500), Image.LANCZOS).save(path, optimize=True)


def main() -> int:
    out = HERE / "graphics"
    phone = out / "phone"
    phone.mkdir(parents=True, exist_ok=True)
    icon(out / "icon-512.png")
    feature(out / "feature-graphic-1024x500.png")
    shots = sorted(SHOTS.glob("*.png"))
    if not shots:
        print(f"Skrinshot yo'q: {SHOTS} — avval StoreScreenshotsTest'ni ishga tushiring.")
    for f in phone.glob("*.png"):
        f.unlink()
    for f in shots:
        shutil.copyfile(f, phone / f.name)
    for f in sorted(out.rglob("*.png")):
        with Image.open(f) as im:
            print(f"{f.relative_to(HERE)}  {im.size[0]}×{im.size[1]}  {f.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
