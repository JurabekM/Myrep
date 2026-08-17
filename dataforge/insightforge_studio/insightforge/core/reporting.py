from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from .charts import to_base64
from .profiling import Profile, profile_frame


def build_html_report(frame: pd.DataFrame, name: str, *, profile: Profile | None = None,
                      figures: list[tuple[str, Figure]] | None = None,
                      notes: str = "", audit: list[dict] | None = None) -> str:
    report = profile or profile_frame(frame)
    issues = "".join(
        f'<div class="issue {item.severity}"><b>{html.escape(item.title)}</b>'
        f'<span>{html.escape(item.column or "Dataset")}</span><p>{html.escape(item.detail)}</p></div>'
        for item in report.issues
    ) or '<p class="muted">Jiddiy sifat muammosi topilmadi.</p>'
    gallery = "".join(
        f'<section><h2>{html.escape(title)}</h2><img src="data:image/png;base64,{to_base64(fig)}"></section>'
        for title, fig in figures or []
    )
    audit_html = ""
    if audit:
        audit_frame = pd.DataFrame(audit).tail(100)
        audit_html = f"<section><h2>Audit tarixi</h2>{audit_frame.to_html(index=False, escape=True)}</section>"
    preview = frame.head(50).to_html(index=False, escape=True, classes="data")
    profile_table = report.column_stats.to_html(index=False, escape=True, classes="data")
    return f"""<!doctype html><html lang="uz"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(name)}</title>
<style>{_CSS}</style></head><body><main><header><div><span class="brand">INSIGHTFORGE</span>
<h1>{html.escape(name)}</h1><p>{datetime.now():%Y-%m-%d %H:%M} da yaratildi</p></div>
<div class="score"><strong>{report.health_score:.0f}</strong><span>Health score</span></div></header>
<div class="metrics"><article><b>{report.rows:,}</b><span>Qator</span></article>
<article><b>{report.columns}</b><span>Ustun</span></article><article><b>{report.missing_cells:,}</b><span>Bo'sh</span></article>
<article><b>{report.duplicate_rows:,}</b><span>Dublikat</span></article></div>
<section><h2>Izoh</h2><p>{html.escape(notes) if notes else 'Avtomatik analitik hisobot.'}</p></section>
<section><h2>Data quality</h2>{issues}</section><section><h2>Ustunlar profili</h2>{profile_table}</section>
{gallery}<section><h2>Ma'lumot namunasi</h2>{preview}</section>{audit_html}
<footer>InsightForge Studio · lokal hisobot</footer></main></body></html>"""


def save_html(content: str, path: str | Path) -> Path:
    p = Path(path).with_suffix(".html")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


_CSS = """
:root{color-scheme:dark;--bg:#080b12;--panel:#111827;--line:#29354d;--text:#eef3ff;--muted:#9aa8c0;--p:#7c5cfc}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px Inter,Segoe UI,sans-serif}
main{max-width:1280px;margin:auto;padding:40px}header{display:flex;justify-content:space-between;align-items:center;padding:30px;background:linear-gradient(120deg,#171e2e,#15142c);border:1px solid var(--line);border-radius:20px}
.brand{color:#9b87ff;font-weight:800;letter-spacing:2px}h1{font-size:34px;margin:8px 0}.score{width:130px;height:130px;border:8px solid var(--p);border-radius:50%;display:flex;flex-direction:column;justify-content:center;align-items:center}.score strong{font-size:38px}.score span,.muted,header p{color:var(--muted)}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}.metrics article,section{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px}.metrics b{display:block;font-size:25px}.metrics span{color:var(--muted)}section{margin:18px 0;overflow:auto}img{display:block;max-width:100%;margin:auto;border-radius:12px}.data{border-collapse:collapse;width:100%}.data th,.data td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}.data th{color:#b9aaff}.issue{padding:12px 15px;border-left:4px solid #ffcb66;background:#171e2e;margin:8px 0}.issue.danger{border-color:#ff6b86}.issue.info{border-color:#31c6ff}.issue span{margin-left:10px;color:var(--muted)}.issue p{margin:5px 0 0}footer{text-align:center;color:var(--muted);padding:25px}@media(max-width:700px){main{padding:15px}.metrics{grid-template-columns:1fr 1fr}}
"""
