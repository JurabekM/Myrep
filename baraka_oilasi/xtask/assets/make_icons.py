"""Baraka ilova ikonkasi (Claude Code dark theme uslubi): to'q fon, daftar chiziqlari va sarg'ish xatcho'p.
Faqat standart kutubxona (zlib, struct). Ishlatish: python3 -I make_icons.py <chiqish_papkasi>"""
import os, struct, sys, zlib

PAPER = (48, 48, 46, 255)      # #30302E
INK = (31, 30, 29, 255)        # #1F1E1D — muqova
LINE = (166, 163, 154, 255)    # #A6A39A
GREEN = (217, 119, 87, 255)    # #D97757 — xatcho'p (nomi tarixiy)
CLEAR = (0, 0, 0, 0)

def pixel(x, y, n):
    u, v = x / n, y / n
    r = 0.18
    # yumaloq burchakli kvadrat
    cx = min(max(u, r), 1 - r); cy = min(max(v, r), 1 - r)
    if (u - cx) ** 2 + (v - cy) ** 2 > r * r:
        return CLEAR
    if 0.70 < u < 0.80 and v < 0.55 and not (v > 0.45 and abs(u - 0.75) < (v - 0.45)):
        return GREEN
    if u < 0.16:
        return INK
    for k in range(4):
        if abs(v - (0.34 + k * 0.14)) < 0.012 and 0.24 < u < 0.86:
            return LINE
    return PAPER

def png(n):
    rows = b"".join(b"\x00" + bytes(c for x in range(n) for c in pixel(x + 0.5, y + 0.5, n)) for y in range(n))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")

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
print("ok")
