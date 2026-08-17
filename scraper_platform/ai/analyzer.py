# -*- coding: utf-8 -*-
"""
ai/analyzer.py
==============
AI / evristik tahlil moduli. Tashqi og'ir kutubxonalarga bog'liq
bo'lmasdan (offline ishlaydi), quyidagilarni bajaradi:

    - Sahifa turini aniqlash (article, e-commerce, listing, forum, ...)
    - Kerakli asosiy ma'lumotlarni avtomatik topish (main content, narx...)
    - Muhim ma'lumotlarni ajratib olish (kalit iboralar)
    - Dublikatlarni aniqlash (matn o'xshashligi bo'yicha)
    - Kontent klassifikatsiyasi (kalit so'zlar asosida)

Izoh: Bu yerda yengil, izohli evristik yondashuv ishlatilgan. Kelajakda
haqiqiy LLM (masalan Claude API) ni ulash uchun `classify_with_llm`
metodi joy tayyorlab qo'yilgan.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

from parsers.extractor import Extractor
from logs.logger import get_logger

log = get_logger(__name__)


# Sahifa turini aniqlash uchun kalit belgilar
_PAGE_TYPE_SIGNALS: dict[str, list[str]] = {
    "e-commerce": ["add to cart", "add to basket", "price", "buy now", "in stock",
                   "savatga", "sotib olish", "narx", "checkout"],
    "article": ["published", "author", "min read", "posted on", "muallif", "e'lon qilingan"],
    "forum": ["reply", "replies", "posted by", "thread", "topic", "javob", "mavzu"],
    "listing": ["results found", "filter", "sort by", "showing", "natijalar", "saralash"],
    "profile": ["followers", "following", "joined", "obunachilar", "profil"],
}

# Klassifikatsiya kategoriyalari
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "texnologiya": ["software", "computer", "ai", "dastur", "texnologiya", "internet"],
    "biznes": ["business", "market", "finance", "biznes", "bozor", "moliya"],
    "sport": ["football", "match", "team", "sport", "musobaqa", "jamoa"],
    "yangiliklar": ["news", "report", "breaking", "yangilik", "xabar"],
    "ta'lim": ["education", "course", "learn", "ta'lim", "kurs", "o'quv"],
}

# Ingliz + o'zbek "stop words" (kalit ibora ajratishda tashlab yuboriladi)
_STOPWORDS: set[str] = {
    "the", "and", "for", "with", "this", "that", "from", "are", "was",
    "have", "has", "not", "you", "your", "our", "can", "will", "all",
    "va", "bilan", "uchun", "bu", "shu", "ham", "yoki", "lekin", "edi",
    "bo'ldi", "bor", "yo'q", "kerak", "qanday", "nima",
}


class ContentAnalyzer:
    """Sahifa kontentini tahlil qiluvchi AI/evristik klass."""

    def __init__(self, html: str, url: str = "") -> None:
        self.html = html or ""
        self.url = url
        self.extractor = Extractor(html, base_url=url)
        self._text = self._plain_text()

    def _plain_text(self) -> str:
        """HTML'dan sof matnni ajratadi."""
        text = re.sub(r"<script.*?</script>", " ", self.html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    # -----------------------------------------------------------------
    def detect_page_type(self) -> str:
        """Sahifa turini kalit belgilar chastotasi bo'yicha aniqlaydi."""
        low = self._text.lower()
        scores: dict[str, int] = {}
        for ptype, signals in _PAGE_TYPE_SIGNALS.items():
            scores[ptype] = sum(low.count(s) for s in signals)
        # JSON-LD @type ham kuchli belgi
        for ld in self.extractor.get_json_ld():
            t = str(ld.get("@type", "")).lower()
            if "product" in t:
                scores["e-commerce"] = scores.get("e-commerce", 0) + 5
            elif "article" in t or "newsarticle" in t:
                scores["article"] = scores.get("article", 0) + 5

        best = max(scores, key=scores.get) if scores else "generic"
        return best if scores.get(best, 0) > 0 else "generic"

    def classify_content(self) -> str:
        """Kontent mavzusini (kategoriya) aniqlaydi."""
        low = self._text.lower()
        scores = {
            cat: sum(low.count(kw) for kw in kws)
            for cat, kws in _CATEGORY_KEYWORDS.items()
        }
        best = max(scores, key=scores.get) if scores else "boshqa"
        return best if scores.get(best, 0) > 0 else "boshqa"

    def extract_keywords(self, top_n: int = 15) -> list[str]:
        """Eng ko'p uchraydigan muhim so'zlarni (kalit iboralar) ajratadi."""
        words = re.findall(r"[a-zA-Zа-яА-Яʼ'oO`g`sShHcCЀ-ӿ]{4,}", self._text.lower())
        words = [w for w in words if w not in _STOPWORDS]
        counter = Counter(words)
        return [w for w, _ in counter.most_common(top_n)]

    def find_main_content(self) -> str:
        """Sahifadagi asosiy (eng muhim) matn blokini topadi."""
        return self.extractor.get_article_text()

    def summary(self, sentences: int = 3) -> str:
        """
        Oddiy ekstraktiv qisqacha mazmun (so'z chastotasi asosida eng
        muhim gaplarni tanlaydi).
        """
        text = self.find_main_content() or self._text
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)
        raw_sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 30]
        if not raw_sentences:
            return ""

        # So'z chastotalari
        words = re.findall(r"[a-zA-Zа-яА-ЯЀ-ӿ]{4,}", text.lower())
        words = [w for w in words if w not in _STOPWORDS]
        freq = Counter(words)

        # Har bir gapni baholaymiz
        scored = []
        for idx, sent in enumerate(raw_sentences):
            sw = re.findall(r"[a-zA-Zа-яА-ЯЀ-ӿ]{4,}", sent.lower())
            score = sum(freq.get(w, 0) for w in sw) / (len(sw) + 1)
            scored.append((score, idx, sent))

        top = sorted(scored, reverse=True)[:sentences]
        # Asl tartibda qaytaramiz
        top_sorted = sorted(top, key=lambda x: x[1])
        return " ".join(s for _, _, s in top_sorted)

    # -----------------------------------------------------------------
    @staticmethod
    def content_fingerprint(text: str) -> str:
        """Matndan dublikat aniqlash uchun barmoq izi (fingerprint) yasaydi."""
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def analyze(self) -> dict[str, Any]:
        """Barcha tahlil natijalarini bitta lug'atda qaytaradi."""
        main = self.find_main_content()
        return {
            "page_type": self.detect_page_type(),
            "category": self.classify_content(),
            "keywords": self.extract_keywords(),
            "summary": self.summary(),
            "fingerprint": self.content_fingerprint(main),
            "text_length": len(self._text),
        }


class DuplicateDetector:
    """Ko'p yozuvlar orasidan dublikatlarni aniqlaydi."""

    def __init__(self, threshold: float = 0.85) -> None:
        # Jaccard o'xshashligi chegarasi (0-1)
        self.threshold = threshold
        self._seen_shingles: list[tuple[Any, set[str]]] = []

    @staticmethod
    def _shingles(text: str, k: int = 3) -> set[str]:
        """Matndan k-so'zli shingle'lar to'plamini yasaydi."""
        words = re.findall(r"\w+", text.lower())
        return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}

    def is_duplicate(self, identifier: Any, text: str) -> bool:
        """
        Berilgan matn avval ko'rilganlarga o'xshash (dublikat) ekanligini
        aniqlaydi. Yangi bo'lsa xotiraga qo'shadi.
        """
        shingles = self._shingles(text)
        if not shingles:
            return False
        for _id, prev in self._seen_shingles:
            inter = len(shingles & prev)
            union = len(shingles | prev)
            similarity = inter / union if union else 0.0
            if similarity >= self.threshold:
                return True
        self._seen_shingles.append((identifier, shingles))
        return False
