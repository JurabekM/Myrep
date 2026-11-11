#!/usr/bin/env python3
"""Google Play grafikasi: sarlavhali skrinshotlar, feature graphic (1024×500) va ikonka (512×512).

Kirish: build/store/raw/*.png (screenshots_test.dart). Chiqish: docs/store/.
Ranglar — Myrep dizayn tokenlari (CLAUDE.md), shrift — ilovadagi NotoSans, logotip — android/.../ic_logo.xml.

    cd havoradar && python3 tool/store/compose.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "build", "store", "raw")
OUT = os.path.join(ROOT, "docs", "store")
FONT_BOLD = os.path.join(ROOT, "assets", "fonts", "NotoSans-Bold.ttf")
FONT_REG = os.path.join(ROOT, "assets", "fonts", "NotoSans-Regular.ttf")

PAPER = (0x26, 0x26, 0x24)
SIDEBAR = (0x1F, 0x1E, 0x1D)
LINE = (0x4A, 0x49, 0x45)
INK = (0xFA, 0xF9, 0xF5)
INK_MUTED = (0xA6, 0xA3, 0x9A)
ACCENT = (0xD9, 0x77, 0x57)

# Skrinshot → sarlavha (do'kon sahifasidagi tartibda).
CAPTIONS = [
    ("01_radar", "Bugungi issiqlik va havo xavfi — bir qarashda"),
    ("02_today", "Issiqlik, havo sifati va UV: JSST va NWS mezonlari bo'yicha"),
    ("03_reasons", "«Nega bu daraja?» — har bir ball tushuntiriladi"),
    ("04_forecast", "7 kunlik prognoz va 48 soatlik grafik"),
    ("05_first_aid", "Issiq urishida birinchi yordam — internetsiz"),
    ("06_profile", "Keksalar, bolalar, yurak va o'pka kasallari uchun ertaroq ogohlantirish"),
    ("07_onboarding", "GPS kerak emas, shaxsiy ma'lumot yig'ilmaydi"),
]


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def rounded(im, radius):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], radius, fill=255)
    return mask


def framed(raw_path, caption, out_path):
    W, H = 1080, 2160
    canvas = Image.new("RGB", (W, H), SIDEBAR)
    d = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT_BOLD, 64)
    lines = wrap(d, caption, font, 940)
    y = 120 if len(lines) <= 2 else 80
    for line in lines:
        w = d.textlength(line, font=font)
        d.text(((W - w) / 2, y), line, font=font, fill=INK)
        y += 84
    d.rounded_rectangle([W / 2 - 60, y + 22, W / 2 + 60, y + 30], 4, fill=ACCENT)

    shot = Image.open(raw_path).convert("RGB")
    scale = 0.78
    sw, sh = int(shot.width * scale), int(shot.height * scale)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    x0, y0 = (W - sw) // 2, H - sh - 40
    border = 4
    d.rounded_rectangle([x0 - border, y0 - border, x0 + sw + border, y0 + sh + border], 48, fill=LINE)
    canvas.paste(shot, (x0, y0), rounded(shot, 44))
    canvas.save(out_path, optimize=True)


def bezier(p0, p1, p2, p3, n=60):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return pts


def wave(x, y, h, step):
    """ic_logo.xml dagi «c step/3·…, s …» to'lqini: ikki kubik egri chiziq."""
    first = bezier((x, y), (x + step / 3, y - h), (x + 2 * step / 3, y - h), (x + step, y))
    second = bezier((x + step, y), (x + 4 * step / 3, y + h), (x + 5 * step / 3, y + h), (x + 2 * step, y))
    return first + second[1:]


def logo(draw, ox, oy, size, ink=INK):
    """Android vektor ikonkasini (108×108 viewport, markazda 0,8 masshtab) PIL bilan chizish."""
    k = size / 108

    def p(x, y):
        x, y = 54 + (x - 54) * 0.8, 54 + (y - 54) * 0.8
        return ox + x * k, oy + y * k

    def stroke(points, width, color):
        # Qalin chiziq — zich nuqtalar bo'ylab doira «muhri»: yumaloq uchlar, qirrasiz.
        pts = [p(*q) for q in points]
        r = width * 0.8 * k / 2
        dense = []
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = max(1, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 / (r / 4)))
            dense += [(x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n) for i in range(n)]
        dense.append(pts[-1])
        for x, y in dense:
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

    # Kulrang to'lqin quyosh orqasida (ic_logo.xml bilan bir xil tartib).
    faded = tuple(int(c * 0.6 + bg * 0.4) for c, bg in zip(ink, PAPER))
    stroke(wave(58, 52, 4, 15), 4, faded)
    cx, cy = p(46, 44)
    r = 14 * 0.8 * k
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)
    for a, b in [((46, 20), (46, 24)), ((46, 64), (46, 68)), ((22, 44), (26, 44)), ((66, 44), (70, 44)),
                 ((29, 27), (32, 30)), ((60, 58), (63, 61)), ((29, 61), (32, 58)), ((60, 30), (63, 27))]:
        stroke([a, b], 4, ACCENT)
    stroke(wave(40, 72, 5, 18), 4, ink)
    stroke(wave(34, 82, 5, 18), 4, ink)


def icon(out_path, size=512):
    big = size * 4
    im = Image.new("RGB", (big, big), PAPER)
    logo(ImageDraw.Draw(im), 0, 0, big)
    im.resize((size, size), Image.LANCZOS).save(out_path, optimize=True)


def feature(out_path):
    W, H, S = 1024, 500, 3
    im = Image.new("RGB", (W * S, H * S), PAPER)
    d = ImageDraw.Draw(im)
    logo(d, 40 * S, 50 * S, 400 * S)
    title = ImageFont.truetype(FONT_BOLD, 92 * S)
    sub = ImageFont.truetype(FONT_REG, 38 * S)
    x = 470 * S
    d.text((x, 120 * S), "HavoRadar", font=title, fill=INK)
    d.rounded_rectangle([x, 252 * S, x + 110 * S, 260 * S], 4 * S, fill=ACCENT)
    y = 290 * S
    for line in wrap(d, "Kuchli issiqlik va havo ifloslanishidan oldindan ogohlantirish", sub, 520 * S):
        d.text((x, y), line, font=sub, fill=INK_MUTED)
        y += 52 * S
    im.resize((W, H), Image.LANCZOS).save(out_path, optimize=True)


def main():
    if not os.path.isdir(RAW):
        sys.exit(f"{RAW} yo'q — avval: TZ=Asia/Tashkent flutter test tool/store/screenshots_test.dart")
    phone = os.path.join(OUT, "phone")
    plain = os.path.join(OUT, "phone-plain")
    os.makedirs(phone, exist_ok=True)
    os.makedirs(plain, exist_ok=True)
    for name, caption in CAPTIONS:
        src = os.path.join(RAW, name + ".png")
        framed(src, caption, os.path.join(phone, name + ".png"))
        # Sarlavhasiz variant (24-bit PNG, alfa kanalsiz — Play talabi).
        Image.open(src).convert("RGB").save(os.path.join(plain, name + ".png"), optimize=True)
        print("phone:", name)
    feature(os.path.join(OUT, "feature-graphic.png"))
    icon(os.path.join(OUT, "icon-512.png"))
    print("feature-graphic.png, icon-512.png")


if __name__ == "__main__":
    main()
