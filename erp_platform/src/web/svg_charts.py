# -*- coding: utf-8 -*-
"""
SVG grafiklar — 100% Python'da chiziladi (JavaScript kutubxonalarisiz).

Line/Area, Bar, Donut (pie) va Heatmap generatorlari. Har biri tayyor
``<svg>`` matnini qaytaradi; ranglar dark theme bilan uyg'un.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Sequence

PALETTE = ["#4f8cff", "#34d399", "#fbbf24", "#f87171", "#a78bfa",
           "#22d3ee", "#fb923c", "#e879f9"]
_GRID = "#283044"
_MUTED = "#8d99ae"


def _f(value) -> float:
    """Decimal/None ni float ga xavfsiz o'giradi."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _nice_max(value: float) -> float:
    """O'q uchun 'chiroyli' maksimal qiymat tanlaydi."""
    if value <= 0:
        return 1.0
    magnitude = 10 ** (len(str(int(value))) - 1)
    for mult in (1, 2, 2.5, 5, 10):
        if value <= magnitude * mult:
            return magnitude * mult
    return value


def _short(value: float) -> str:
    """Katta sonlarni qisqartiradi: 1.2M, 340K."""
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if abs(value) >= divisor:
            short = value / divisor
            return (f"{short:.1f}".rstrip("0").rstrip(".")) + suffix
    return f"{value:.0f}"


# ---------------------------------------------------------------------- #
#  Line / Area chart
# ---------------------------------------------------------------------- #

def line_chart(labels: Sequence[str], series: list[dict],
               width: int = 720, height: int = 260) -> str:
    """
    Chiziqli grafik (area to'ldirish bilan).

    ``series``: ``[{"name": "Daromad", "values": [...], "color": "#..."}]``
    """
    pad_l, pad_r, pad_t, pad_b = 56, 12, 14, 34
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    n = max(len(labels), 1)
    max_v = _nice_max(max((max((_f(v) for v in s["values"]), default=0)
                           for s in series), default=0))

    def x(i: int) -> float:
        return pad_l + (plot_w * i / max(n - 1, 1))

    def y(v: float) -> float:
        return pad_t + plot_h * (1 - v / max_v)

    parts = [f'<svg viewBox="0 0 {width} {height}" '
             f'xmlns="http://www.w3.org/2000/svg" role="img">']

    # Gorizontal to'r va Y yorliqlari
    for step in range(5):
        gy = pad_t + plot_h * step / 4
        val = max_v * (1 - step / 4)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                     f'y2="{gy:.1f}" stroke="{_GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" fill="{_MUTED}" '
                     f'font-size="10" text-anchor="end">{_short(val)}</text>')

    # X yorliqlari (siqilishda har n-chisini ko'rsatamiz)
    label_step = max(1, n // 12)
    for i, label in enumerate(labels):
        if i % label_step:
            continue
        parts.append(f'<text x="{x(i):.1f}" y="{height - 12}" fill="{_MUTED}" '
                     f'font-size="10" text-anchor="middle">{label}</text>')

    for idx, serie in enumerate(series):
        color = serie.get("color") or PALETTE[idx % len(PALETTE)]
        pts = [(x(i), y(_f(v))) for i, v in enumerate(serie["values"])]
        if not pts:
            continue
        path = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        area = (path + f" L {pts[-1][0]:.1f} {pad_t + plot_h} "
                       f"L {pts[0][0]:.1f} {pad_t + plot_h} Z")
        parts.append(f'<path d="{area}" fill="{color}" opacity="0.09"/>')
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" '
                     f'stroke-width="2.2" stroke-linejoin="round"/>')
        for px, py in pts:
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" '
                         f'fill="{color}"/>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------- #
#  Bar chart
# ---------------------------------------------------------------------- #

def bar_chart(labels: Sequence[str], series: list[dict],
              width: int = 720, height: int = 260) -> str:
    """Guruhlangan ustunli grafik (bir nechta seriya yonma-yon)."""
    pad_l, pad_r, pad_t, pad_b = 56, 12, 14, 34
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    n = max(len(labels), 1)
    n_series = max(len(series), 1)
    max_v = _nice_max(max((max((_f(v) for v in s["values"]), default=0)
                           for s in series), default=0))
    group_w = plot_w / n
    bar_w = max(group_w * 0.7 / n_series, 2)

    parts = [f'<svg viewBox="0 0 {width} {height}" '
             f'xmlns="http://www.w3.org/2000/svg" role="img">']
    for step in range(5):
        gy = pad_t + plot_h * step / 4
        val = max_v * (1 - step / 4)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                     f'y2="{gy:.1f}" stroke="{_GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" fill="{_MUTED}" '
                     f'font-size="10" text-anchor="end">{_short(val)}</text>')

    label_step = max(1, n // 12)
    for i, label in enumerate(labels):
        cx = pad_l + group_w * i + group_w / 2
        if i % label_step == 0:
            parts.append(f'<text x="{cx:.1f}" y="{height - 12}" fill="{_MUTED}" '
                         f'font-size="10" text-anchor="middle">{label}</text>')
        for s_idx, serie in enumerate(series):
            color = serie.get("color") or PALETTE[s_idx % len(PALETTE)]
            value = _f(serie["values"][i]) if i < len(serie["values"]) else 0
            bar_h = plot_h * value / max_v
            bx = cx - (bar_w * n_series) / 2 + s_idx * bar_w
            by = pad_t + plot_h - bar_h
            parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" '
                         f'height="{bar_h:.1f}" rx="2" fill="{color}" '
                         f'opacity="0.9"/>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------- #
#  Donut (pie)
# ---------------------------------------------------------------------- #

def donut_chart(items: list[dict], size: int = 210) -> str:
    """
    Halqa diagramma. ``items``: ``[{"label": ..., "value": ...}]``.

    Markazida jami qiymat ko'rsatiladi.
    """
    import math

    total = sum(_f(item["value"]) for item in items)
    cx = cy = size / 2
    radius, stroke = size / 2 - 16, 26
    parts = [f'<svg viewBox="0 0 {size} {size}" '
             f'xmlns="http://www.w3.org/2000/svg" role="img">']

    if total <= 0:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
                     f'stroke="{_GRID}" stroke-width="{stroke}"/>')
    else:
        angle = -90.0
        for idx, item in enumerate(items):
            fraction = _f(item["value"]) / total
            sweep = fraction * 360
            if sweep <= 0:
                continue
            color = PALETTE[idx % len(PALETTE)]
            # to'liq doira uchun alohida holat
            if sweep >= 359.99:
                parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" '
                             f'fill="none" stroke="{color}" '
                             f'stroke-width="{stroke}"/>')
                break
            a1, a2 = math.radians(angle), math.radians(angle + sweep)
            x1, y1 = cx + radius * math.cos(a1), cy + radius * math.sin(a1)
            x2, y2 = cx + radius * math.cos(a2), cy + radius * math.sin(a2)
            large = 1 if sweep > 180 else 0
            parts.append(
                f'<path d="M {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large} 1 '
                f'{x2:.2f} {y2:.2f}" fill="none" stroke="{color}" '
                f'stroke-width="{stroke}" stroke-linecap="butt"/>')
            angle += sweep

    parts.append(f'<text x="{cx}" y="{cy - 2}" fill="#e4e9f2" font-size="15" '
                 f'font-weight="700" text-anchor="middle">{_short(total)}</text>')
    parts.append(f'<text x="{cx}" y="{cy + 15}" fill="{_MUTED}" font-size="9" '
                 f'text-anchor="middle">JAMI</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------- #
#  Heatmap
# ---------------------------------------------------------------------- #

def heatmap(row_labels: Sequence[str], col_labels: Sequence[str],
            values: list[list[float]], width: int = 720,
            height: int = 240) -> str:
    """
    Issiqlik xaritasi (masalan, hafta kuni x soat kesimida savdolar).

    ``values[row][col]`` — katakcha qiymati; rang intensivligi qiymatga
    proporsional (accent ko'k gradienti).
    """
    pad_l, pad_t, pad_b = 64, 8, 26
    rows, cols = max(len(row_labels), 1), max(len(col_labels), 1)
    cell_w = (width - pad_l - 8) / cols
    cell_h = (height - pad_t - pad_b) / rows
    max_v = max((max((_f(v) for v in row), default=0) for row in values),
                default=0) or 1

    parts = [f'<svg viewBox="0 0 {width} {height}" '
             f'xmlns="http://www.w3.org/2000/svg" role="img">']
    for r, row_label in enumerate(row_labels):
        cy = pad_t + r * cell_h
        parts.append(f'<text x="{pad_l - 8}" y="{cy + cell_h / 2 + 3:.1f}" '
                     f'fill="{_MUTED}" font-size="10" text-anchor="end">'
                     f'{row_label}</text>')
        for c in range(cols):
            value = _f(values[r][c]) if c < len(values[r]) else 0
            opacity = 0.06 + 0.94 * (value / max_v) if value > 0 else 0.05
            parts.append(
                f'<rect x="{pad_l + c * cell_w:.1f}" y="{cy:.1f}" '
                f'width="{cell_w - 2:.1f}" height="{cell_h - 2:.1f}" rx="3" '
                f'fill="#4f8cff" opacity="{opacity:.2f}"/>')
    col_step = max(1, cols // 16)
    for c, col_label in enumerate(col_labels):
        if c % col_step:
            continue
        parts.append(f'<text x="{pad_l + c * cell_w + cell_w / 2:.1f}" '
                     f'y="{height - 8}" fill="{_MUTED}" font-size="9" '
                     f'text-anchor="middle">{col_label}</text>')
    parts.append("</svg>")
    return "".join(parts)


def legend_html(names: Sequence[str]) -> str:
    """Grafik ostidagi legend (rang + nom)."""
    spans = []
    for idx, name in enumerate(names):
        color = PALETTE[idx % len(PALETTE)]
        spans.append(f'<span><span class="dot" '
                     f'style="background:{color}"></span>{name}</span>')
    return f'<div class="legend">{"".join(spans)}</div>'
