#!/usr/bin/env python3
"""
AETHER-Q Sidecar Studio ikonkasi (Pillow, tashqi rasm faylisiz).

G'oya: ikki tugun (klient va server) post-kvant tunel bilan bog'langan, ustida qulf. Ranglar GUI temasidan
(teal #4FD1C5 urg'u, to'q navy fon) — boshqa AETHER-Q dasturlaridan bir qarashda farq qiladi (ular qalqon,
tanga yoki terminal belgisini ishlatadi).

Har o'lcham ALOHIDA chiziladi (4x supersampling + LANCZOS); <=24 px uchun soddalashtirilgan variant
(chiziqchalar va kalit teshigi yo'q, qulf va tunel qalinroq). ICO'ga yozishda append_images SHART.

    python scripts/make_icon.py
Natija: crates/aq-studio/assets/icon.ico, icon-256.png, preview.png (16/24/32/48/256 yonma-yon, kattalashtirilgan)
"""

import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "crates" / "aq-studio" / "assets"

NAVY_TOP = (14, 36, 64)
NAVY_BOT = (9, 22, 41)
BORDER = (40, 82, 120)
TEAL = (79, 209, 197)
TEAL_DARK = (25, 104, 99)
WHITE = (230, 238, 247)
HOLE = (14, 36, 64)
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def draw(size: int) -> Image.Image:
    s = size * 4  # supersampling
    small = size <= 24
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(s * (0.20 if not small else 0.16))
    # Fon: vertikal gradient (maska bilan yumaloq kvadrat).
    grad = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(grad)
    for y in range(s):
        t = y / (s - 1)
        c = tuple(int(NAVY_TOP[i] * (1 - t) + NAVY_BOT[i] * t) for i in range(3)) + (255,)
        gd.line([(0, y), (s, y)], fill=c)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=255)
    img.paste(grad, (0, 0), mask)
    if not small:
        d.rounded_rectangle([1, 1, s - 2, s - 2], radius=r, outline=BORDER, width=max(2, s // 64))

    # Tunel: qalin teal chiziq, uchlarida tugunlar.
    cy = s * (0.66 if not small else 0.68)
    x0, x1 = s * 0.20, s * 0.80
    bar = s * (0.085 if not small else 0.13)
    d.rounded_rectangle([x0, cy - bar / 2, x1, cy + bar / 2], radius=bar / 2, fill=TEAL_DARK if not small else TEAL)
    if not small:
        # shifrlangan oqim: chiziqchalar
        dash, gap = s * 0.06, s * 0.035
        x = x0 + s * 0.12
        while x + dash < x1 - s * 0.12:
            d.rounded_rectangle([x, cy - bar * 0.18, x + dash, cy + bar * 0.18], radius=bar * 0.18, fill=TEAL)
            x += dash + gap
    node = s * (0.115 if not small else 0.15)
    for cx in (x0, x1):
        d.ellipse([cx - node, cy - node, cx + node, cy + node], fill=TEAL)
        if not small:
            d.ellipse([cx - node * 0.42, cy - node * 0.42, cx + node * 0.42, cy + node * 0.42], fill=NAVY_BOT)

    # Qulf: tunel ustida, markazda.
    lw = s * (0.30 if not small else 0.42)
    lh = s * (0.22 if not small else 0.28)
    lx, ly = s / 2 - lw / 2, s * (0.34 if not small else 0.30)
    shackle_w = lw * 0.62
    sw = max(2, int(s * (0.045 if not small else 0.075)))
    d.arc(
        [s / 2 - shackle_w / 2, ly - shackle_w * 0.62, s / 2 + shackle_w / 2, ly + shackle_w * 0.38],
        start=180,
        end=360,
        fill=WHITE,
        width=sw,
    )
    d.line([s / 2 - shackle_w / 2 + sw / 2 - 1, ly - shackle_w * 0.12, s / 2 - shackle_w / 2 + sw / 2 - 1, ly + 2], fill=WHITE, width=sw)
    d.line([s / 2 + shackle_w / 2 - sw / 2, ly - shackle_w * 0.12, s / 2 + shackle_w / 2 - sw / 2, ly + 2], fill=WHITE, width=sw)
    d.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=s * 0.03, fill=WHITE)
    if not small:
        kx, ky = s / 2, ly + lh * 0.45
        kr = lw * 0.09
        d.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=HOLE)
        d.rectangle([kx - kr * 0.45, ky, kx + kr * 0.45, ky + lh * 0.30], fill=HOLE)
    return img.resize((size, size), Image.LANCZOS)


def wizard_images(dest: pathlib.Path):
    """Inno Setup sehrgari rasmlari (100% va 125% masshtab): chap panel va o'ng yuqori kichik belgi."""
    dest.mkdir(parents=True, exist_ok=True)
    for (w, h), name in (((164, 314), "wizard.bmp"), ((205, 392), "wizard-125.bmp")):
        s = 4
        img = Image.new("RGB", (w * s, h * s))
        d = ImageDraw.Draw(img)
        for y in range(h * s):
            t = y / (h * s - 1)
            d.line([(0, y), (w * s, y)], fill=tuple(int(NAVY_TOP[i] * (1 - t) + NAVY_BOT[i] * t) for i in range(3)))
        # Pastda nozik tunel chizig'i (bezak).
        cy = int(h * s * 0.82)
        d.line([(int(w * s * 0.1), cy), (int(w * s * 0.9), cy)], fill=TEAL_DARK, width=6 * s // 4)
        for cx in (int(w * s * 0.1), int(w * s * 0.9)):
            r = 7 * s
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=TEAL)
        img = img.resize((w, h), Image.LANCZOS)
        icon = draw(int(w * 0.62))
        img.paste(icon, ((w - icon.width) // 2, int(h * 0.22)), icon)
        img.save(dest / name)
    for n, name in ((55, "wizard-small.bmp"), (69, "wizard-small-125.bmp")):
        bg = Image.new("RGB", (n, n), (255, 255, 255))
        ic = draw(n)
        bg.paste(ic, (0, 0), ic)
        bg.save(dest / name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wizard_images(ROOT / "installer")
    imgs = [draw(n) for n in SIZES]
    big = imgs[-1]
    big.save(OUT / "icon-256.png")
    big.save(OUT / "icon.ico", sizes=[(n, n) for n in SIZES], append_images=imgs[:-1])
    # Tekshirish uchun: kichik o'lchamlar 8x kattalashtirilgan (piksel aniq).
    shown = [16, 24, 32, 48]
    tiles = [imgs[SIZES.index(n)].resize((n * 8, n * 8), Image.NEAREST) for n in shown] + [big]
    w = sum(t.width for t in tiles) + 20 * (len(tiles) + 1)
    h = max(t.height for t in tiles) + 40
    prev = Image.new("RGBA", (w, h), (24, 28, 36, 255))
    x = 20
    for t in tiles:
        prev.paste(t, (x, 20), t)
        x += t.width + 20
    prev.save(OUT / "preview.png")
    ico = Image.open(OUT / "icon.ico")
    print("ico o'lchamlari:", sorted(ico.info.get("sizes", [])))
    print("yozildi:", OUT / "icon.ico", OUT / "icon-256.png", OUT / "preview.png")


if __name__ == "__main__":
    main()
