"""docs/play/PLAY_LISTING.md uzunlik chegaralarini tekshiradi (Google Play Console talablari).

  py tools/store/check_listing.py
"""
import re
import sys
from pathlib import Path

LISTING = Path(__file__).resolve().parents[2] / "docs" / "play" / "PLAY_LISTING.md"
LIMITS = {"title": 30, "short": 80, "full": 4000, "whatsnew": 500}
LANGS = ("uz", "ru", "en")
FORBIDDEN = [r"\brasmiy ilova\b", r"№\s*1", r"\beng yaxshi\b", r"\bлучш", r"\bbest\b"]
# "100%" faqat inkor gapda ruxsat ("hech bir dastur 100% himoya bermaydi").
NEGATIONS = ("bermaydi", "не даёт", "no software")


def absolute_claims(value: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", value) if "100%" in s and not any(n in s.lower() for n in NEGATIONS)]


def main() -> None:
    text = LISTING.read_text(encoding="utf-8")
    bad = 0
    for lang in LANGS:
        for field, limit in LIMITS.items():
            m = re.search(rf"<!-- {lang}:{field} -->\n(.*?)\n<!-- /{lang}:{field} -->", text, re.S)
            if not m:
                print(f"YO'Q  {lang}:{field}")
                bad += 1
                continue
            value = m.group(1).strip()
            n = len(value)
            ok = 0 < n <= limit
            for pat in FORBIDDEN:
                if re.search(pat, value, re.I):
                    print(f"TAQIQ {lang}:{field}: /{pat}/")
                    ok = False
            for s in absolute_claims(value):
                print(f"TAQIQ {lang}:{field}: mutlaq va'da: {s[:80]}")
                ok = False
            bad += not ok
            print(f"{'OK  ' if ok else 'XATO'}  {lang}:{field:8} {n:5}/{limit}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
