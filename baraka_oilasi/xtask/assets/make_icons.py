"""«Baraka Dastur» ilova ikonkasi (Claude Code dark theme uslubi): to'q fon, krem rangli «B» harfi va
undan o'sib chiqqan sarg'ish barg (baraka — o'sish). Manba dizayn: `logo.svg` (1024 birlik, shu fayldagi
geometriya bilan bir xil). Faqat standart kutubxona (zlib, struct); chetlar 4×4 supersampling bilan silliq.
Ishlatish: python3 -I make_icons.py <desktop_icons_papkasi> [android_res_papkasi]"""
import os, struct, sys, zlib

PAPER = (38, 38, 36)       # #262624 — fon
INK = (250, 249, 245)      # #FAF9F5 — «B»
ACCENT = (217, 119, 87)    # #D97757 — barg
SS = 4                     # supersampling (har o'qda)

# Geometriya — logo.svg dagi koordinatalar (translate(-26 -14) qo'llangan holda).
DX, DY = -26, -14
HALF = 46                  # «B» chizig'i yarim qalinligi (92 / 2)
RX = 228                   # fon burchagi radiusi


def _p(x, y):
    return (x + DX, y + DY)


SEGMENTS = [
    (_p(360, 330), _p(360, 760)),  # ustun
    (_p(360, 760), _p(585, 760)),  # past
    (_p(585, 530), _p(360, 530)),  # o'rta
    (_p(360, 330), _p(555, 330)),  # tepa
]
ARCS = [  # o'ng yarim aylanalar: markaz, radius
    (_p(585, 645), 115),
    (_p(555, 430), 100),
]


def _bezier(p0, p1, p2, p3, n=48):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


LEAF = _bezier(_p(640, 330), _p(650, 230), _p(720, 170), _p(830, 160)) + _bezier(
    _p(830, 160), _p(826, 270), _p(760, 330), _p(640, 330)
)[1:]
VEIN = _bezier(_p(650, 320), _p(700, 270), _p(750, 220), _p(800, 190), 24)
VEIN_HALF = 6
LEAF_BOX = (min(x for x, _ in LEAF), min(y for _, y in LEAF), max(x for x, _ in LEAF), max(y for _, y in LEAF))


def _seg_dist2(px, py, a, b):
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
    dx, dy = px - (ax + t * vx), py - (ay + t * vy)
    return dx * dx + dy * dy


def _in_b(x, y):
    h2 = HALF * HALF
    for a, b in SEGMENTS:
        if _seg_dist2(x, y, a, b) <= h2:
            return True
    for (cx, cy), r in ARCS:
        if x >= cx and abs(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 - r) <= HALF:
            return True
    return False


def _in_poly(x, y, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _in_vein(x, y):
    h2 = VEIN_HALF * VEIN_HALF
    return any(_seg_dist2(x, y, VEIN[i], VEIN[i + 1]) <= h2 for i in range(len(VEIN) - 1))


def _in_bg(x, y):
    cx = min(max(x, RX), 1024 - RX)
    cy = min(max(y, RX), 1024 - RX)
    return (x - cx) ** 2 + (y - cy) ** 2 <= RX * RX


def sample(x, y):
    """1024 birlikdagi nuqta rangi (RGB) yoki None (shaffof)."""
    if not _in_bg(x, y):
        return None
    if _in_b(x, y):
        return INK
    x0, y0, x1, y1 = LEAF_BOX
    if x0 <= x <= x1 and y0 <= y <= y1 and _in_poly(x, y, LEAF):
        return PAPER if _in_vein(x, y) else ACCENT
    return PAPER


def png(n):
    """n×n RGBA PNG: yumaloq burchakli kvadrat, tashqarisi shaffof."""
    rows = bytearray()
    k = 1024 / n
    for py in range(n):
        rows.append(0)
        for px in range(n):
            r = g = b = a = 0
            for sy in range(SS):
                for sx in range(SS):
                    c = sample((px + (sx + 0.5) / SS) * k, (py + (sy + 0.5) / SS) * k)
                    if c is not None:
                        r += c[0]; g += c[1]; b += c[2]; a += 1
            if a:
                rows += bytes((r // a, g // a, b // a, a * 255 // (SS * SS)))
            else:
                rows += b"\x00\x00\x00\x00"

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)) + chunk(
        b"IDAT", zlib.compress(bytes(rows), 9)
    ) + chunk(b"IEND", b"")


def ico(sizes):
    imgs = [png(s) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(imgs))
    off = 6 + 16 * len(imgs)
    dirs = b""
    for s, data in zip(sizes, imgs):
        dirs += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), off)
        off += len(data)
    return head + dirs + b"".join(imgs)


out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for name, n in (("32x32.png", 32), ("128x128.png", 128), ("128x128@2x.png", 256), ("icon.png", 512)):
    open(os.path.join(out, name), "wb").write(png(n))
open(os.path.join(out, "icon.ico"), "wb").write(ico([16, 32, 48, 256]))

# Android: minSdk 26 — adaptiv ikonka (vektor) asosiy; bular faqat zaxira.
if len(sys.argv) > 2:
    for dpi, n in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)):
        d = os.path.join(sys.argv[2], f"mipmap-{dpi}")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "ic_launcher.png"), "wb").write(png(n))
print("ok")
