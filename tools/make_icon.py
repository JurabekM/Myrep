"""ROSTOR-2 ikonkasi: firuza qalqon ichida "R2" monogrammasi va qalqon ostida kesilgan
signal yoyi (ilova internetsiz ishlaydi). Ranglar ilova temasidan (lib/ui/theme.dart).

Yaratadi: Android legacy mipmap (48..192 px), adaptive foreground (108..432 px, shaffof),
fon rangi resursi va docs/icon-preview.png. Har o'lcham alohida, 4x supersampling bilan.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "app" / "android" / "app" / "src" / "main" / "res"
BG = (11, 29, 51, 255)        # RColors.bg
ACCENT = (79, 209, 197, 255)  # RColors.accent
WHITE = (230, 238, 248, 255)  # RColors.text
SS = 4


def font(px: int) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_mark(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, small: bool) -> None:
    """Qalqon (s — qalqon balandligi) va ichidagi belgi."""
    w = s * 0.84
    top = cy - s / 2
    pts = [
        (cx, top),
        (cx + w / 2, top + s * 0.14),
        (cx + w / 2, top + s * 0.50),
        (cx + w * 0.30, top + s * 0.80),
        (cx, top + s),
        (cx - w * 0.30, top + s * 0.80),
        (cx - w / 2, top + s * 0.50),
        (cx - w / 2, top + s * 0.14),
    ]
    d.polygon(pts, fill=ACCENT)
    inset = s * 0.075
    inner = [
        (cx, top + inset * 1.25),
        (cx + w / 2 - inset, top + s * 0.14 + inset * 0.55),
        (cx + w / 2 - inset, top + s * 0.50),
        (cx + w * 0.30 - inset * 0.6, top + s * 0.80 - inset * 0.55),
        (cx, top + s - inset * 1.4),
        (cx - w * 0.30 + inset * 0.6, top + s * 0.80 - inset * 0.55),
        (cx - w / 2 + inset, top + s * 0.50),
        (cx - w / 2 + inset, top + s * 0.14 + inset * 0.55),
    ]
    d.polygon(inner, fill=BG)
    f = font(int(s * (0.40 if small else 0.36)))
    text = "R2"
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ty = top + s * (0.40 if small else 0.36) - th / 2 - bbox[1]
    d.text((cx - tw / 2 - bbox[0], ty), text, font=f, fill=WHITE)
    if not small:
        # Kesilgan signal yoyi: tarmoq yo'q.
        # Wi-Fi belgisi (markazdagi nuqta ustida ikki konsentrik yoy) va uni kesgan chiziq.
        ay = top + s * 0.78
        lw = max(2, int(s * 0.032))
        for r in (s * 0.085, s * 0.155):
            d.arc([cx - r, ay - r, cx + r, ay + r], 225, 315, fill=ACCENT, width=lw)
        dot = s * 0.028
        d.ellipse([cx - dot, ay - dot, cx + dot, ay + dot], fill=ACCENT)
        d.line([cx - s * 0.13, ay + s * 0.01, cx + s * 0.13, ay - s * 0.17], fill=WHITE, width=lw)


def legacy(px: int) -> Image.Image:
    big = px * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, big - 1, big - 1], radius=big * 0.22, fill=BG)
    draw_mark(d, big / 2, big / 2, big * 0.74, small=px < 64)
    return img.resize((px, px), Image.LANCZOS)


def foreground(px: int) -> Image.Image:
    big = px * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))  # shaffof: fonni tizim chizadi
    d = ImageDraw.Draw(img)
    draw_mark(d, big / 2, big / 2, big * 0.50, small=False)  # xavfsiz zona: markazdagi 66%
    return img.resize((px, px), Image.LANCZOS)


def main() -> None:
    for dens, lpx, fpx in [("mdpi", 48, 108), ("hdpi", 72, 162), ("xhdpi", 96, 216), ("xxhdpi", 144, 324), ("xxxhdpi", 192, 432)]:
        out = RES / f"mipmap-{dens}"
        out.mkdir(parents=True, exist_ok=True)
        legacy(lpx).save(out / "ic_launcher.png")
        foreground(fpx).save(out / "ic_launcher_foreground.png")
    any_dir = RES / "mipmap-anydpi-v26"
    any_dir.mkdir(exist_ok=True)
    (any_dir / "ic_launcher.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background"/>\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
        '    <monochrome android:drawable="@mipmap/ic_launcher_foreground"/>\n'
        '</adaptive-icon>\n', encoding="utf-8", newline="\n")
    (RES / "values" / "colors.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        '    <color name="ic_launcher_background">#0B1D33</color>\n</resources>\n', encoding="utf-8", newline="\n")
    # Ko'zdan kechirish uchun: barcha o'lchamlar yonma-yon, 4x kattalashtirilgan.
    sizes = [48, 72, 96, 144, 192]
    prev = Image.new("RGBA", (sum(sizes) + 20 * len(sizes) + 20, 232), (40, 40, 48, 255))
    x = 20
    for s in sizes:
        prev.paste(legacy(s), (x, 20), legacy(s))
        x += s + 20
    (ROOT / "docs").mkdir(exist_ok=True)
    prev.save(ROOT / "docs" / "icon-preview.png")
    print("ikonkalar yozildi:", RES)


if __name__ == "__main__":
    main()
