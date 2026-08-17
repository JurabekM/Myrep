"""Visual theme: brand colors and global CSS for the enterprise dashboard."""
from __future__ import annotations

PRIMARY = "#2e7d32"
SECONDARY = "#66bb6a"
ACCENT = "#f9a825"

PALETTE = ["#2e7d32", "#66bb6a", "#f9a825", "#ef6c00", "#0288d1",
           "#7b1fa2", "#c62828", "#00897b", "#5d4037", "#3949ab"]

GLOBAL_CSS = """
.kpi-card {border-radius: 14px; min-width: 170px; transition: transform .15s;}
.kpi-card:hover {transform: translateY(-3px);}
.kpi-value {font-size: 1.55rem; font-weight: 700; line-height: 1.2;}
.kpi-label {font-size: .8rem; opacity: .75;}
.nav-btn {justify-content: flex-start !important; text-transform: none !important;}
.section-title {font-size: 1.1rem; font-weight: 600; margin-top: .25rem;}
.chart-card {border-radius: 14px; width: 100%;}
.alert-error {border-left: 4px solid #c62828;}
.alert-warning {border-left: 4px solid #f9a825;}
.alert-info {border-left: 4px solid #0288d1;}
::-webkit-scrollbar {width: 9px; height: 9px;}
::-webkit-scrollbar-thumb {background: #9e9e9e66; border-radius: 5px;}
"""


def apply() -> None:
    """Apply brand colors + CSS to the current client."""
    from nicegui import ui

    ui.colors(primary=PRIMARY, secondary=SECONDARY, accent=ACCENT,
              positive="#43a047", negative="#c62828", warning="#f9a825")
    ui.add_css(GLOBAL_CSS)
