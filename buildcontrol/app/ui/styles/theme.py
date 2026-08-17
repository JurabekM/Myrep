"""Design tokens: colors, radii, spacing and typography."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Dark palette used across the whole application."""

    # surfaces
    bg: str = "#111827"
    bg_alt: str = "#151B26"
    sidebar: str = "#0D131F"
    surface: str = "#1E293B"
    surface_alt: str = "#243044"
    surface_hover: str = "#2B384E"
    elevated: str = "#243247"
    border: str = "#2C3A50"
    border_strong: str = "#3A4A63"

    # text
    text: str = "#E6EDF6"
    text_muted: str = "#93A2B7"
    text_faint: str = "#64748B"
    text_inverse: str = "#0B1220"

    # accents
    accent: str = "#3B82F6"
    accent_hover: str = "#2F76EC"
    accent_pressed: str = "#2563EB"
    accent_soft: str = "#1D3557"

    success: str = "#22C55E"
    success_soft: str = "#14311F"
    warning: str = "#F5B342"
    warning_soft: str = "#3A2E12"
    danger: str = "#EF4444"
    danger_soft: str = "#3A1A1C"
    info: str = "#38BDF8"
    info_soft: str = "#12303D"
    neutral_soft: str = "#25324A"

    # chart / gantt
    bar_plan: str = "#3B82F6"
    bar_actual: str = "#22C55E"
    bar_delay: str = "#EF4444"
    grid: str = "#22304A"


COLORS = Palette()

FONT_FAMILY = '"Segoe UI", "Inter", "Noto Sans", sans-serif'
FONT_SIZE = 13
FONT_SIZE_SMALL = 12
FONT_SIZE_TITLE = 18

RADIUS = 10
RADIUS_SM = 8
RADIUS_LG = 12

SPACING = 12
SPACING_SM = 8
SPACING_LG = 20

SIDEBAR_WIDTH = 236
SIDEBAR_WIDTH_COLLAPSED = 64
TITLEBAR_HEIGHT = 44
ROW_HEIGHT = 34


def status_colors(kind: str) -> tuple[str, str]:
    """Return ``(text_color, background_color)`` for a semantic badge kind."""
    mapping = {
        "success": (COLORS.success, COLORS.success_soft),
        "warning": (COLORS.warning, COLORS.warning_soft),
        "danger": (COLORS.danger, COLORS.danger_soft),
        "info": (COLORS.info, COLORS.info_soft),
        "accent": (COLORS.accent, COLORS.accent_soft),
        "neutral": (COLORS.text_muted, COLORS.neutral_soft),
    }
    return mapping.get(kind, mapping["neutral"])
