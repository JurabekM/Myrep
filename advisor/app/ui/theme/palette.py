"""Ultra Dark rang palitrasi — barcha UI ranglari shu yerdan olinadi (DRY)."""

from __future__ import annotations


class Colors:
    # Fon qatlamlari (eng quyuqdan yorug'roqqa)
    BG_BASE = "#0a0c10"        # asosiy oyna foni
    BG_SURFACE = "#111419"     # panellar, sidebar
    BG_ELEVATED = "#181c23"    # kartalar, inputlar
    BG_HOVER = "#1f242c"       # hover holati
    BG_ACTIVE = "#262c36"      # bosilgan/tanlangan

    # Matn
    TEXT_PRIMARY = "#e6e9ef"   # asosiy matn (yuqori kontrast)
    TEXT_SECONDARY = "#9aa3b2" # ikkilamchi matn
    TEXT_MUTED = "#5c6675"     # xira matn (placeholder)

    # Chegara
    BORDER = "#232830"
    BORDER_STRONG = "#2e3540"

    # Urg'u (accent) — ko'k
    ACCENT = "#3b82f6"
    ACCENT_HOVER = "#2f6fe0"
    ACCENT_MUTED = "#1e3a5f"

    # Holat ranglari
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    INFO = "#38bdf8"

    # Chat pufakchalari
    BUBBLE_USER = "#1e3a5f"
    BUBBLE_ASSISTANT = "#181c23"

    # Grafiklar uchun (matplotlib)
    CHART_SERIES = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#38bdf8"]
    CHART_GRID = "#232830"
