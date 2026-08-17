"""HTML report generator — combines the profile, charts and ML results in one file."""
from __future__ import annotations

import datetime as _dt
import html
from pathlib import Path
from typing import Any

import pandas as pd
from matplotlib.figure import Figure

from ..config import APP_NAME, PALETTE, VERSION
from .charting import figure_to_base64

CSS = f"""
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 32px 28px 64px;
  background: {PALETTE['bg']}; color: {PALETTE['text']};
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  line-height: 1.55;
}}
.wrap {{ max-width: 1180px; margin: 0 auto; }}
h1 {{ font-size: 30px; margin: 0 0 4px; letter-spacing: -.4px; }}
h2 {{ font-size: 20px; margin: 40px 0 14px; padding-bottom: 8px;
      border-bottom: 1px solid {PALETTE['border']}; }}
h3 {{ font-size: 15px; margin: 22px 0 8px; color: {PALETTE['accent2']}; }}
.sub {{ color: {PALETTE['muted']}; font-size: 13px; margin-bottom: 26px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
          gap: 12px; margin: 18px 0 8px; }}
.card {{ background: {PALETTE['surface']}; border: 1px solid {PALETTE['border']};
         border-radius: 12px; padding: 14px 16px; }}
.card .k {{ color: {PALETTE['muted']}; font-size: 11px; text-transform: uppercase;
            letter-spacing: .6px; }}
.card .v {{ font-size: 23px; font-weight: 650; margin-top: 4px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12.5px;
         background: {PALETTE['surface']}; border-radius: 10px; overflow: hidden;
         margin: 10px 0 6px; }}
th, td {{ padding: 8px 11px; text-align: left;
          border-bottom: 1px solid {PALETTE['border']}; }}
th {{ background: {PALETTE['surface2']}; color: {PALETTE['muted']};
      font-weight: 600; text-transform: uppercase; font-size: 11px;
      letter-spacing: .4px; position: sticky; top: 0; }}
tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: {PALETTE['surface2']}; }}
.scroll {{ max-height: 460px; overflow: auto; border: 1px solid {PALETTE['border']};
           border-radius: 10px; }}
.fig {{ background: {PALETTE['surface']}; border: 1px solid {PALETTE['border']};
        border-radius: 12px; padding: 12px; margin: 14px 0; text-align: center; }}
.fig img {{ max-width: 100%; border-radius: 8px; }}
.issue {{ border-left: 3px solid {PALETTE['warning']}; background: {PALETTE['surface']};
          border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 8px 0; font-size: 13px; }}
.issue.high {{ border-left-color: {PALETTE['danger']}; }}
.issue.low {{ border-left-color: {PALETTE['faint']}; }}
.issue b {{ color: {PALETTE['text']}; }}
.issue span {{ color: {PALETTE['muted']}; }}
pre {{ background: {PALETTE['surface']}; border: 1px solid {PALETTE['border']};
       border-radius: 10px; padding: 14px; overflow-x: auto; font-size: 12.5px;
       color: {PALETTE['text']}; }}
.badge {{ display: inline-block; padding: 3px 9px; border-radius: 20px;
          font-size: 11px; background: {PALETTE['surface3']}; color: {PALETTE['accent2']};
          margin-right: 6px; }}
footer {{ margin-top: 48px; padding-top: 16px; border-top: 1px solid {PALETTE['border']};
          color: {PALETTE['faint']}; font-size: 12px; }}
"""


def _table(df: pd.DataFrame, max_rows: int = 200) -> str:
    if df is None or df.empty:
        return f"<p style='color:{PALETTE['muted']}'>No data</p>"
    shown = df.head(max_rows)
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in shown.columns)
    body = []
    for _, row in shown.iterrows():
        cells = "".join(f"<td>{html.escape(_fmt(v))}</td>" for v in row)
        body.append(f"<tr>{cells}</tr>")
    more = (f"<p style='color:{PALETTE['muted']};font-size:12px'>"
            f"… showing {max_rows} of {len(df):,} rows</p>"
            if len(df) > max_rows else "")
    return (f"<div class='scroll'><table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table></div>{more}")


def _fmt(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:,.2e}"
    return str(v)


def _card(key: str, value: Any) -> str:
    return f"<div class='card'><div class='k'>{html.escape(key)}</div>" \
           f"<div class='v'>{html.escape(str(value))}</div></div>"


def _fig(fig: Figure, caption: str = "") -> str:
    b64 = figure_to_base64(fig)
    cap = (f"<div style='color:{PALETTE['muted']};font-size:12px;margin-top:6px'>"
           f"{html.escape(caption)}</div>" if caption else "")
    return f"<div class='fig'><img src='data:image/png;base64,{b64}'/>{cap}</div>"


def build_report(
    df: pd.DataFrame,
    *,
    title: str = "Data analysis report",
    dataset_name: str = "dataset",
    profile: Any = None,
    figures: list[tuple[Figure, str]] | None = None,
    ml_result: Any = None,
    extra_tables: list[tuple[str, pd.DataFrame]] | None = None,
    history: list[str] | None = None,
) -> str:
    """Build the full HTML report as a string."""
    from .profile import correlation, profile_dataframe, top_correlations

    prof = profile or profile_dataframe(df)
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    parts: list[str] = []

    parts.append(f"<h1>{html.escape(title)}</h1>")
    parts.append(
        f"<div class='sub'>Source: <b>{html.escape(dataset_name)}</b> · "
        f"Generated: {now} · {APP_NAME} v{VERSION}</div>"
    )

    # Overview metrics
    parts.append("<div class='cards'>")
    parts.append(_card("Rows", f"{prof.rows:,}"))
    parts.append(_card("Columns", f"{prof.cols:,}"))
    parts.append(_card("Memory", f"{prof.memory_mb:.2f} MB"))
    parts.append(_card("Missing", f"{prof.missing_pct:.2f}%"))
    parts.append(_card("Duplicates", f"{prof.duplicates:,}"))
    parts.append(_card("Quality score", f"{prof.quality_score}/100"))
    parts.append("</div>")

    # Column profile
    parts.append("<h2>Column profile</h2>")
    parts.append(_table(prof.to_frame(), 300))

    # Quality issues
    if prof.issues:
        parts.append("<h2>Data quality warnings</h2>")
        for iss in prof.issues[:60]:
            parts.append(
                f"<div class='issue {html.escape(iss.get('level', 'low'))}'>"
                f"<b>{html.escape(iss['title'])}</b> · "
                f"<span>{html.escape(iss.get('column', '—'))}</span><br>"
                f"<span>{html.escape(iss['detail'])}</span></div>"
            )

    # Correlation
    corr = correlation(df)
    if not corr.empty:
        top = top_correlations(corr, threshold=0.4)
        if not top.empty:
            parts.append("<h2>Strong relationships</h2>")
            parts.append(_table(top, 40))

    # Charts
    if figures:
        parts.append("<h2>Charts</h2>")
        for fig, cap in figures:
            parts.append(_fig(fig, cap))

    # ML results
    if ml_result is not None:
        parts.append("<h2>Machine Learning results</h2>")
        parts.append(
            f"<p><span class='badge'>{html.escape(ml_result.task)}</span>"
            f"<span class='badge'>target: {html.escape(ml_result.target)}</span>"
            f"<span class='badge'>best: {html.escape(ml_result.best_name)}</span></p>"
        )
        parts.append("<div class='cards'>")
        for k, v in list(ml_result.metrics.items())[:6]:
            parts.append(_card(k, f"{v:.4f}" if isinstance(v, float) else v))
        parts.append("</div>")
        parts.append("<h3>Model leaderboard</h3>")
        parts.append(_table(ml_result.leaderboard, 30))
        if ml_result.importance is not None and not ml_result.importance.empty:
            parts.append("<h3>Feature importance</h3>")
            parts.append(_table(ml_result.importance.head(25), 25))
        if ml_result.confusion is not None:
            parts.append("<h3>Confusion matrix</h3>")
            parts.append(_table(ml_result.confusion.reset_index(), 30))

    # Extra tables
    for name, tbl in (extra_tables or []):
        parts.append(f"<h2>{html.escape(name)}</h2>")
        parts.append(_table(tbl, 200))

    # Edit history
    if history:
        parts.append("<h2>Applied operations</h2>")
        parts.append("<pre>" + html.escape("\n".join(
            f"{i + 1:2d}. {h}" for i, h in enumerate(history))) + "</pre>")

    # Data sample
    parts.append("<h2>Data sample</h2>")
    parts.append(_table(df.head(50), 50))

    parts.append(f"<footer>Generated by {APP_NAME} v{VERSION} · {now}</footer>")

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body><div class='wrap'>{''.join(parts)}</div></body></html>"
    )


def save_report(html_text: str, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_text, encoding="utf-8")
    return str(p)
