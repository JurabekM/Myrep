#!/usr/bin/env python3
"""docs/PLAY_STORE.md dagi do'kon matnlari Google Play cheklovlariga sig'ishini tekshiradi."""
import os
import re
import sys

LIMITS = {"title": 30, "short": 80, "full": 4000, "whatsnew": 500}
path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "PLAY_STORE.md")
text = open(path, encoding="utf-8").read()
blocks = re.findall(r"<!-- listing:(\w+):(\w+) -->\n(.*?)\n<!-- /listing -->", text, re.S)
bad = 0
for lang, kind, body in blocks:
    n, limit = len(body.strip()), LIMITS[kind]
    ok = n <= limit
    bad += not ok
    print(f"{'OK ' if ok else 'XATO'} {lang:2} {kind:8} {n:5}/{limit}")
if len(blocks) != 2 * len(LIMITS):
    sys.exit(f"Kutilgan {2 * len(LIMITS)} ta blok, topildi {len(blocks)}")
sys.exit(1 if bad else 0)
