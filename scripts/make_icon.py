"""TAMGA ikonkasini chizadi (A varianti — "Muhr"): tamga belgisi muhr halqasi ichida.

Ranglar studio/src/theme/tokens.css dan: fon --bg-app, urg'u --accent, matn --text-primary.
Har o'lcham alohida 4x supersampling bilan chiziladi; <=24 px uchun soddalashtirilgan variant
(ichki punktir halqa va nuqta tashlanadi, chiziqlar qalinlashadi).

Ishga tushirish:  py -3.14 scripts/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

BG = (0x15, 0x15, 0x15, 255)
ACCENT = (0xD9, 0x77, 0x57, 255)
TEXT = (0xF0, 0xEF, 0xEC, 255)
SS = 4

OUT = Path(__file__).resolve().parent.parent / "studio" / "src-tauri" / "icons"


def quad_points(p0, p1, p2, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        pts.append((x, y))
    return pts


def round_line(d: ImageDraw.ImageDraw, pts, w, fill):
    d.line(pts, fill=fill, width=round(w), joint="curve")
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def draw(size: int) -> Image.Image:
    s = size * SS
    small = size <= 24
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = s / 100  # 100 birlikli koordinata tizimi

    # Fon: yumaloq kvadrat (Claude Code dark foni).
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=22 * u, fill=BG)

    # Muhr halqasi.
    ring_w = (9 if small else 6) * u
    r = (40 if small else 38) * u
    c = 50 * u
    d.ellipse((c - r, c - r, c + r, c + r), outline=ACCENT, width=round(ring_w))
    if not small:
        ri = 30 * u
        for k in range(36):  # punktir ichki halqa
            if k % 2:
                continue
            a0, a1 = k * 10, k * 10 + 6
            d.arc((c - ri, c - ri, c + ri, c + ri), a0, a1, fill=ACCENT, width=round(1.4 * u))

    # Tamga belgisi: ustun, egilgan yelka va taglik.
    gw = (11 if small else 7.5) * u
    round_line(d, [(c, 31 * u), (c, 69 * u)], gw, ACCENT)
    round_line(d, quad_points((32 * u, 36 * u), (c, 52 * u), (68 * u, 36 * u)), gw, ACCENT)
    round_line(d, [(41 * u, 69 * u), (59 * u, 69 * u)], gw, ACCENT)
    if not small:
        rr = 3.6 * u
        d.ellipse((c - rr, 27 * u - rr, c + rr, 27 * u + rr), fill=TEXT)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [draw(n) for n in ico_sizes]
    frames[-1].save(OUT / "icon.ico", sizes=[(n, n) for n in ico_sizes], append_images=frames[:-1])
    draw(32).save(OUT / "32x32.png")
    draw(128).save(OUT / "128x128.png")
    draw(256).save(OUT / "128x128@2x.png")
    draw(512).save(OUT / "icon.png")
    # Ko'z bilan tekshirish uchun: kichik o'lchamlarni 4x kattalashtirilgan varaq.
    sheet = Image.new("RGBA", (sum(n * 4 for n in ico_sizes[:4]) + 50, 48 * 4 + 20), (40, 40, 40, 255))
    x = 10
    for n in ico_sizes[:4]:
        big = draw(n).resize((n * 4, n * 4), Image.NEAREST)
        sheet.paste(big, (x, 10), big)
        x += n * 4 + 10
    sheet.save(OUT.parent.parent.parent / "scripts" / "icon_preview.png")
    print("ikonkalar:", OUT)


if __name__ == "__main__":
    main()
