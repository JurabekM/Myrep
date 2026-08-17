# -*- coding: utf-8 -*-
"""
parsers/extractor.py
====================
Universal HTML ekstraktori. Berilgan HTML kontentdan barcha turdagi
ma'lumotlarni ajratib oladi:

    - Matnlar: title, headings, paragraphs, article
    - Linklar: internal / external
    - Media: image, video, audio
    - Fayllar: pdf, doc(x), xls(x), csv, zip
    - Meta: description, keywords, author, published date
    - Structured data: JSON-LD, Schema.org (microdata), OpenGraph
    - Jadvallar: HTML tables

Shuningdek CSS selector, XPath va Regex orqali maxsus ajratib olishni
qo'llab-quvvatlaydi.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from lxml import html as lxml_html

from logs.logger import get_logger

log = get_logger(__name__)

# Yuklab olinadigan fayl kengaytmalari
_FILE_EXTS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".zip",
              ".ppt", ".pptx", ".txt", ".rar", ".7z")


class Extractor:
    """HTML kontentdan ma'lumot ajratib oluvchi asosiy klass."""

    def __init__(self, html_content: str, base_url: str = "") -> None:
        self.html = html_content or ""
        self.base_url = base_url
        self.soup = BeautifulSoup(self.html, "lxml")
        self._base_domain = urlparse(base_url).netloc if base_url else ""

    # =================================================================
    # MATNLAR
    # =================================================================
    def get_title(self) -> str:
        """Sahifa sarlavhasi (<title>)."""
        if self.soup.title and self.soup.title.string:
            return self.soup.title.string.strip()
        return ""

    def get_headings(self) -> dict[str, list[str]]:
        """Barcha sarlavhalar (h1-h6)."""
        result: dict[str, list[str]] = {}
        for level in range(1, 7):
            tag = f"h{level}"
            texts = [h.get_text(strip=True) for h in self.soup.find_all(tag)]
            texts = [t for t in texts if t]
            if texts:
                result[tag] = texts
        return result

    def get_paragraphs(self) -> list[str]:
        """Barcha paragraflar (<p>)."""
        return [p.get_text(strip=True) for p in self.soup.find_all("p")
                if p.get_text(strip=True)]

    def get_article_text(self) -> str:
        """Asosiy maqola matni (article/main/eng katta matnli blok)."""
        for selector in ("article", "main", '[role="main"]'):
            node = self.soup.select_one(selector)
            if node:
                text = node.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text
        # Zaxira: eng ko'p <p> ga ega konteynerni topamiz
        candidates = self.soup.find_all(["div", "section"])
        best, best_len = "", 0
        for c in candidates:
            text = c.get_text(separator="\n", strip=True)
            if len(text) > best_len:
                best, best_len = text, len(text)
        return best

    # =================================================================
    # LINKLAR
    # =================================================================
    def get_links(self) -> dict[str, list[str]]:
        """Internal va external linklarni ajratadi."""
        internal: set[str] = set()
        external: set[str] = set()
        for a in self.soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full = urljoin(self.base_url, href) if self.base_url else href
            domain = urlparse(full).netloc
            if self._base_domain and domain == self._base_domain:
                internal.add(full)
            elif domain:
                external.add(full)
            else:
                internal.add(full)
        return {"internal": sorted(internal), "external": sorted(external)}

    # =================================================================
    # MEDIA
    # =================================================================
    def get_media(self) -> dict[str, list[str]]:
        """Rasm, video va audio manzillari."""
        def _abs(url: str) -> str:
            return urljoin(self.base_url, url) if self.base_url else url

        images = []
        for img in self.soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if src:
                images.append(_abs(src.strip()))

        videos = []
        for v in self.soup.find_all(["video", "source"]):
            src = v.get("src") or ""
            if src:
                videos.append(_abs(src.strip()))

        audios = []
        for a in self.soup.find_all("audio"):
            src = a.get("src") or ""
            if src:
                audios.append(_abs(src.strip()))

        return {
            "images": sorted(set(images)),
            "videos": sorted(set(videos)),
            "audios": sorted(set(audios)),
        }

    # =================================================================
    # FAYLLAR
    # =================================================================
    def get_files(self) -> list[str]:
        """Yuklab olinadigan fayl linklarini (pdf, docx, xlsx...) qaytaradi."""
        files: set[str] = set()
        for a in self.soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().endswith(_FILE_EXTS):
                files.add(urljoin(self.base_url, href) if self.base_url else href)
        return sorted(files)

    # =================================================================
    # META MA'LUMOTLAR
    # =================================================================
    def get_meta(self) -> dict[str, str]:
        """description, keywords, author, published date."""
        meta: dict[str, str] = {}

        def _meta_content(name: str, attr: str = "name") -> str:
            tag = self.soup.find("meta", attrs={attr: name})
            return tag.get("content", "").strip() if tag else ""

        meta["description"] = _meta_content("description") or _meta_content("og:description", "property")
        meta["keywords"] = _meta_content("keywords")
        meta["author"] = _meta_content("author") or _meta_content("article:author", "property")
        meta["published_date"] = (
            _meta_content("article:published_time", "property")
            or _meta_content("date")
            or _meta_content("pubdate")
        )
        return {k: v for k, v in meta.items() if v}

    # =================================================================
    # STRUCTURED DATA
    # =================================================================
    def get_json_ld(self) -> list[dict[str, Any]]:
        """JSON-LD (Schema.org) ma'lumotlarini ajratadi."""
        results: list[dict[str, Any]] = []
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    results.extend(d for d in data if isinstance(d, dict))
                elif isinstance(data, dict):
                    results.append(data)
            except (json.JSONDecodeError, TypeError):
                continue
        return results

    def get_opengraph(self) -> dict[str, str]:
        """OpenGraph (og:*) meta teglarini ajratadi."""
        og: dict[str, str] = {}
        for tag in self.soup.find_all("meta"):
            prop = tag.get("property", "")
            if prop.startswith("og:"):
                og[prop] = tag.get("content", "").strip()
        return og

    def get_microdata(self) -> list[dict[str, Any]]:
        """Schema.org microdata (itemscope/itemprop) ajratadi."""
        items: list[dict[str, Any]] = []
        for scope in self.soup.find_all(attrs={"itemscope": True}):
            item: dict[str, Any] = {"_type": scope.get("itemtype", "")}
            for prop in scope.find_all(attrs={"itemprop": True}):
                name = prop.get("itemprop")
                value = (prop.get("content") or prop.get("href")
                         or prop.get("src") or prop.get_text(strip=True))
                if name:
                    item[name] = value
            if len(item) > 1:
                items.append(item)
        return items

    # =================================================================
    # JADVALLAR
    # =================================================================
    def get_tables(self) -> list[list[list[str]]]:
        """Barcha HTML jadvallarni [jadval][qator][katak] ko'rinishida qaytaradi."""
        tables: list[list[list[str]]] = []
        for table in self.soup.find_all("table"):
            rows: list[list[str]] = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables

    # =================================================================
    # MAXSUS SELEKTORLAR (CSS / XPath / Regex)
    # =================================================================
    def select_css(self, selector: str, attr: str | None = None) -> list[str]:
        """CSS selector orqali ma'lumot ajratadi."""
        try:
            nodes = self.soup.select(selector)
        except Exception as exc:  # noqa: BLE001 - noto'g'ri selector
            log.error("Noto'g'ri CSS selector '{}': {}", selector, exc)
            return []
        if attr:
            return [n.get(attr, "").strip() for n in nodes if n.get(attr)]
        return [n.get_text(strip=True) for n in nodes if n.get_text(strip=True)]

    def select_xpath(self, xpath: str) -> list[str]:
        """XPath orqali ma'lumot ajratadi (lxml)."""
        try:
            tree = lxml_html.fromstring(self.html)
            results = tree.xpath(xpath)
        except Exception as exc:  # noqa: BLE001
            log.error("Noto'g'ri XPath '{}': {}", xpath, exc)
            return []
        output: list[str] = []
        for r in results:
            if isinstance(r, str):
                output.append(r.strip())
            elif hasattr(r, "text_content"):
                output.append(r.text_content().strip())
            else:
                output.append(str(r).strip())
        return [o for o in output if o]

    def select_regex(self, pattern: str) -> list[str]:
        """Regex orqali sahifa matnidan ma'lumot ajratadi."""
        try:
            return re.findall(pattern, self.html)
        except re.error as exc:
            log.error("Noto'g'ri regex '{}': {}", pattern, exc)
            return []

    # =================================================================
    # HAMMASINI YIG'ISH
    # =================================================================
    def extract_all(self) -> dict[str, Any]:
        """Barcha standart ma'lumotlarni bitta lug'atda qaytaradi."""
        return {
            "title": self.get_title(),
            "headings": self.get_headings(),
            "paragraphs": self.get_paragraphs(),
            "meta": self.get_meta(),
            "links": self.get_links(),
            "media": self.get_media(),
            "files": self.get_files(),
            "tables": self.get_tables(),
            "json_ld": self.get_json_ld(),
            "opengraph": self.get_opengraph(),
            "microdata": self.get_microdata(),
        }
