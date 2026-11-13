# Kripto test vektorlari (ADR-0007)

Dart (`packages/zanjir_core/test/crypto/vectors_test.dart`) va Python (`server/tests/crypto/test_vectors.py`)
testlari **aynan shu fayllarni** o'qiydi. Ikki implementatsiya bir-birini nazorat qiladi.

| Fayl | Mazmuni |
|---|---|
| `canonical_json.json` | Kanonik JSON (RFC 8785): RFC misollari, sonlar, Unicode, xato holatlari, vaqt formati |
| `ed25519.json` | RFC 8032 rasmiy vektorlari + rad etilishi shart bo'lgan imzolar (S + L, noto'g'ri kalitlar) |
| `hash_chain.json` | 5 ta hodisali audit zanjiri, anchor bilan davom ettirish, 12 ta buzish holati |
| `protocol_signature.json` | Protokol payload'i, PDF baytlari, `payload_sha256 ‖ pdf_sha256` imzosi |

Yaratish (Python implementatsiyasi avval RFC rasmiy natijalari bilan tekshiriladi):

```
cd server
uv run python -I ../tools/vectors/generate.py          # yozish
uv run python -I ../tools/vectors/generate.py --check  # CI: eskirmaganmi
```

Vektorlarni qo'lda tahrirlamang. Formatni o'zgartirish — yangi ADR va ikkala tomonda bir vaqtda.
Test kaliti (`device_seed`) — RFC 8032 TEST 1 ning ochiq maxfiy kaliti, haqiqiy qurilmada ishlatilmaydi.
