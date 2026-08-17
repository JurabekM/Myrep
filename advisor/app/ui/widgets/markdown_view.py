"""Markdown ko'rsatuvchi — AI javoblarini HTML sifatida render qiladi.

Tashqi bog'liqliksiz yengil Markdown→HTML konvertori (sarlavhalar, ro'yxatlar,
kod bloklari, qalin/kursiv, jadval). Ultra Dark uslubga mos inline stil bilan
QTextBrowser'da ko'rsatiladi.
"""

from __future__ import annotations

import html
import re

from PyQt6.QtWidgets import QTextBrowser

from app.ui.theme.palette import Colors as C


def _render_inline(text: str) -> str:
    text = html.escape(text)
    # Inline kod
    text = re.sub(r"`([^`]+)`", rf'<code style="background:{C.BG_BASE};'
                  rf'padding:1px 4px;border-radius:4px;">\1</code>', text)
    # Qalin
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # Kursiv
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    # Havola
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                  rf'<a href="\2" style="color:{C.ACCENT};">\1</a>', text)
    return text


def markdown_to_html(md: str) -> str:
    lines = md.split("\n")
    html_parts: list[str] = []
    in_code = False
    code_buffer: list[str] = []
    in_list = False
    table_buffer: list[str] = []

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    def flush_table() -> None:
        if not table_buffer:
            return
        rows = [r for r in table_buffer if r.strip()]
        table_buffer.clear()
        if len(rows) < 2:
            return
        cells = [_split_row(r) for r in rows]
        # Ikkinchi qator ajratkich (---) bo'lsa uni tashlaymiz.
        header = cells[0]
        body = cells[2:] if len(cells) > 1 and set("-: |") >= set("".join(cells[1])) else cells[1:]
        out = [f'<table cellspacing="0" cellpadding="6" '
               f'style="border-collapse:collapse;margin:8px 0;">']
        out.append("<tr>" + "".join(
            f'<th style="border:1px solid {C.BORDER};text-align:left;'
            f'color:{C.TEXT_SECONDARY};">{_render_inline(c)}</th>' for c in header
        ) + "</tr>")
        for row in body:
            out.append("<tr>" + "".join(
                f'<td style="border:1px solid {C.BORDER};">{_render_inline(c)}</td>'
                for c in row
            ) + "</tr>")
        out.append("</table>")
        html_parts.append("".join(out))

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                html_parts.append(
                    f'<pre style="background:{C.BG_BASE};border:1px solid {C.BORDER};'
                    f'border-radius:8px;padding:10px;overflow-x:auto;">'
                    f'<code>{html.escape(chr(10).join(code_buffer))}</code></pre>'
                )
                code_buffer = []
            in_code = not in_code
            continue
        if in_code:
            code_buffer.append(line)
            continue

        if "|" in line and line.strip().startswith("|"):
            table_buffer.append(line)
            continue
        flush_table()

        heading = re.match(r"^(#{1,4})\s+(.*)", line)
        if heading:
            flush_list()
            level = len(heading.group(1))
            size = {1: 20, 2: 17, 3: 15, 4: 14}[level]
            html_parts.append(
                f'<div style="font-size:{size}px;font-weight:700;'
                f'margin:10px 0 4px 0;color:{C.TEXT_PRIMARY};">'
                f'{_render_inline(heading.group(2))}</div>'
            )
            continue

        list_item = re.match(r"^\s*[-*]\s+(.*)", line)
        if list_item:
            if not in_list:
                html_parts.append('<ul style="margin:4px 0 4px 18px;">')
                in_list = True
            html_parts.append(f"<li>{_render_inline(list_item.group(1))}</li>")
            continue

        num_item = re.match(r"^\s*\d+\.\s+(.*)", line)
        if num_item:
            if not in_list:
                html_parts.append('<ul style="margin:4px 0 4px 18px;">')
                in_list = True
            html_parts.append(f"<li>{_render_inline(num_item.group(1))}</li>")
            continue

        flush_list()
        if line.strip():
            html_parts.append(f'<div style="margin:3px 0;">{_render_inline(line)}</div>')
        else:
            html_parts.append('<div style="height:6px;"></div>')

    flush_list()
    flush_table()
    return f'<div style="color:{C.TEXT_PRIMARY};line-height:1.5;">' + "".join(html_parts) + "</div>"


def _split_row(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


class MarkdownView(QTextBrowser):
    def __init__(self, parent=None):  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; }}"
        )

    def set_markdown(self, md: str) -> None:
        self.setHtml(markdown_to_html(md))
