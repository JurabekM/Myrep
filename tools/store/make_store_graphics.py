"""Google Play grafikasi: 512×512 ikonka va 1024×500 "feature graphic".

  py tools/store/make_store_graphics.py

Ikonka belgisi tools/make_icon.py dagi bilan bir xil (firuza qalqon, "R2", kesilgan signal).
Grafikada jonzot, bank binosi, qimor va boshqa taqiqlangan ramzlar yo'q — faqat geometriya va matn.
Rasmiy tashkilotlar logotiplari ishlatilmaydi (Play impersonation siyosati).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from make_icon import ACCENT, BG, SS, WHITE, draw_mark, font  # noqa: E402

DIM = (157, 177, 204, 255)      # RColors.textDim
SURFACE = (18, 41, 74, 255)     # RColors.surface


def play_icon(path: Path) -> None:
    n = 512 * SS
    im = Image.new("RGBA", (n, n), BG)
    draw_mark(ImageDraw.Draw(im), n / 2, n / 2, n * 0.66, small=False)
    im.resize((512, 512), Image.LANCZOS).save(path)


def pill(d: ImageDraw.ImageDraw, x: float, y: float, text: str, f) -> float:
    b = d.textbbox((0, 0), text, font=f)
    w, h = b[2] - b[0], b[3] - b[1]
    pad_x, pad_y = 18 * SS, 11 * SS
    d.rounded_rectangle((x, y, x + w + 2 * pad_x, y + h + 2 * pad_y), radius=(h + 2 * pad_y) / 2,
                        fill=SURFACE, outline=ACCENT, width=2 * SS)
    d.text((x + pad_x - b[0], y + pad_y - b[1]), text, font=f, fill=WHITE)
    return x + w + 2 * pad_x + 14 * SS


def feature_graphic(path: Path) -> None:
    W, H = 1024 * SS, 500 * SS
    im = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(im)
    # Yengil geometrik fon: o'ng tomonda konsentrik yoylar (signal emas — qalqon to'lqini).
    for i, r in enumerate(range(260, 900, 90)):
        c = (79, 209, 197, max(10, 38 - i * 5))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse((W * 0.22 - r * SS, H / 2 - r * SS, W * 0.22 + r * SS, H / 2 + r * SS),
                                      outline=c, width=3 * SS)
        im.alpha_composite(layer)
    d = ImageDraw.Draw(im)
    draw_mark(d, W * 0.22, H / 2, H * 0.62, small=False)
    x = W * 0.40
    d.text((x, H * 0.17), "ROSTOR-2", font=font(96 * SS), fill=WHITE)
    d.text((x, H * 0.40), "Firibgarlikdan himoya —", font=font(40 * SS), fill=ACCENT)
    d.text((x, H * 0.50), "to'liq internetsiz", font=font(40 * SS), fill=ACCENT)
    f = font(22 * SS)
    px = x
    for t in ("APK imzosi", "Qo'ng'iroq", "SMS va havola"):
        px = pill(d, px, H * 0.70, t, f)
    assert px < W - 24 * SS, "yorliqlar o'ng chetga tegib qoldi"
    im.convert("RGB").resize((1024, 500), Image.LANCZOS).save(path)


if __name__ == "__main__":
    play_icon(HERE / "play_icon_512.png")
    feature_graphic(HERE / "feature_graphic_1024x500.png")
    print("yozildi:", HERE / "play_icon_512.png", HERE / "feature_graphic_1024x500.png")
