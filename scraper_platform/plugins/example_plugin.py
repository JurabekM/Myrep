# -*- coding: utf-8 -*-
"""
plugins/example_plugin.py
=========================
Namuna plugin. Bu faylni nusxalab, o'z parseringizni yozishingiz mumkin.

Bu plugin e-commerce sahifalaridan mahsulot nomi va narxini ajratib
olishga harakat qiladi (JSON-LD Product yoki umumiy narx patternlari).
"""

from __future__ import annotations

import re
from typing import Any

from plugins.plugin_manager import BasePlugin
from parsers.extractor import Extractor


class ProductPlugin(BasePlugin):
    """E-commerce mahsulot sahifalari uchun namuna parser."""

    name = "product_extractor"

    def matches(self, url: str, html: str) -> bool:
        """JSON-LD ichida Product bo'lsa yoki narx belgilari bo'lsa mos keladi."""
        low = html.lower()
        return ('"@type": "product"' in low.replace(" ", "")
                or "add to cart" in low
                or "savatga" in low)

    def parse(self, url: str, html: str) -> list[dict[str, Any]]:
        """Mahsulot nomi va narxini ajratadi."""
        ext = Extractor(html, base_url=url)
        results: list[dict[str, Any]] = []

        # 1) JSON-LD Product'lardan
        for ld in ext.get_json_ld():
            if str(ld.get("@type", "")).lower() == "product":
                offers = ld.get("offers", {})
                price = ""
                if isinstance(offers, dict):
                    price = offers.get("price", "")
                elif isinstance(offers, list) and offers:
                    price = offers[0].get("price", "")
                results.append({
                    "product_name": ld.get("name", ""),
                    "price": price,
                    "currency": (offers.get("priceCurrency", "")
                                 if isinstance(offers, dict) else ""),
                    "source_url": url,
                })

        # 2) JSON-LD topilmasa, umumiy narx patternini qidiramiz
        if not results:
            price_match = re.search(r"[\$€£₽]\s?\d[\d\s.,]*", html)
            if price_match:
                results.append({
                    "product_name": ext.get_title(),
                    "price": price_match.group().strip(),
                    "source_url": url,
                })

        return results
