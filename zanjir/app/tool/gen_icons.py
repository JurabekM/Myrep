"""Ilova ikonkasi (12-faza): ikki zanjir halqasi, Myrep dark ranglari. Bitta geometriya → adaptive vector (Android 8+),
eski PNG'lar (Android 7) va Play Store uchun 512 px.

    python3 -I app/tool/gen_icons.py          # yozish
    python3 -I app/tool/gen_icons.py --check  # CI: fayllar geometriyaga mosmi

Talab: Pillow. Anthropic brend belgilari ishlatilmaydi (CLAUDE.md) — faqat rang tokenlari.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw

APP = Path(__file__).resolve().parents[1]
RES = APP / "android/app/src/main/res"
STORE = APP.parent / "docs/store"
PAPER, ACCENT, INK = "#262624", "#D97757", "#FAF9F5"
# 108 dp adaptive canvas; xavfsiz zona — markazdagi 66 dp doira.
CANVAS, W, H, STROKE, OFFSET, ROTATION = 108, 34, 18, 6, 13, -45
LEGACY = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}


def stadium(cx: float, cy: float) -> str:
    r = H / 2
    x0, x1, y0, y1 = cx - W / 2 + r, cx + W / 2 - r, cy - H / 2, cy + H / 2
    return f"M{x0:g},{y0:g} H{x1:g} A{r:g},{r:g} 0 0 1 {x1:g},{y1:g} H{x0:g} A{r:g},{r:g} 0 0 1 {x0:g},{y0:g} Z"


def foreground_xml() -> str:
    c = CANVAS / 2
    paths = "\n".join(
        f'        <path android:pathData="{stadium(c + dx, c)}" android:strokeColor="{color}"\n'
        f'            android:strokeWidth="{STROKE}" android:fillColor="#00000000" />'
        for dx, color in ((-OFFSET, ACCENT), (OFFSET, INK))
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generatsiya: app/tool/gen_icons.py — qo'lda tahrirlanmaydi. -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="{CANVAS}dp" android:height="{CANVAS}dp"
    android:viewportWidth="{CANVAS}" android:viewportHeight="{CANVAS}">
    <group android:rotation="{ROTATION}" android:pivotX="{c:g}" android:pivotY="{c:g}">
{paths}
    </group>
</vector>
"""


ADAPTIVE = """<?xml version="1.0" encoding="utf-8"?>
<!-- Generatsiya: app/tool/gen_icons.py — qo'lda tahrirlanmaydi. -->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/zanjir_paper" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
    <monochrome android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
"""


def raster(size: int, *, full_bleed: bool) -> bytes:
    """`full_bleed` — Play Store (kvadrat, Play o'zi yumaloqlaydi); aks holda — yumaloq burchakli eski ikonka."""
    k = 8  # supersampling
    big = size * k
    scale = big / (84 if full_bleed else 92)  # Play va eski ikonkada halqalar yuzaning katta qismini egallaydi
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if full_bleed:
        d.rectangle((0, 0, big, big), fill=PAPER)
    else:
        d.rounded_rectangle((0, 0, big - 1, big - 1), radius=big * 0.18, fill=PAPER)
    links = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ld = ImageDraw.Draw(links)
    c = big / 2
    for dx, color in ((-OFFSET, ACCENT), (OFFSET, INK)):
        cx = c + dx * scale
        box = (cx - W / 2 * scale, c - H / 2 * scale, cx + W / 2 * scale, c + H / 2 * scale)
        ld.rounded_rectangle(box, radius=H / 2 * scale, outline=color, width=round(STROKE * scale))
    img.alpha_composite(links.rotate(-ROTATION, resample=Image.Resampling.BICUBIC, center=(c, c)))
    out = io.BytesIO()
    img.resize((size, size), Image.Resampling.LANCZOS).save(out, format="PNG", optimize=True)
    return out.getvalue()


def outputs() -> dict[Path, bytes]:
    files: dict[Path, bytes] = {
        RES / "drawable/ic_launcher_foreground.xml": foreground_xml().encode(),
        RES / "mipmap-anydpi-v26/ic_launcher.xml": ADAPTIVE.encode(),
        STORE / "icon-512.png": raster(512, full_bleed=True),
    }
    for dpi, px in LEGACY.items():
        files[RES / f"mipmap-{dpi}/ic_launcher.png"] = raster(px, full_bleed=False)
    return files


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for path, data in outputs().items():
        if check:
            # PNG baytlari Pillow versiyasiga bog'liq — o'lcham tekshiriladi; XML — aynan.
            ok = path.exists() and (
                Image.open(path).size == Image.open(io.BytesIO(data)).size
                if path.suffix == ".png"
                else path.read_bytes() == data
            )
            if not ok:
                stale.append(str(path.relative_to(APP.parent)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if stale:
        print("eskirgan ikonkalar: " + ", ".join(stale) + " — gen_icons.py ni qayta ishga tushiring", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
