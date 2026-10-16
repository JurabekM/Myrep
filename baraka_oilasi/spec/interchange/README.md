# `.baraka` almashish formati

Telefon ↔ desktop sinxronlash, zaxira nusxa va yangi qurilmani ulash uchun yagona format
(`docs/BARAKA_OILASI.md` 8.3–8.5). Rust (`core/crates/interchange`) va Android (Dart) shu
papkadagi fayllarga bayt-bayt mos kelishi shart.

| Fayl | Nima |
|---|---|
| `export-format.schema.json` | JSON Schema: sarlavha, `meta` va `row` qatorlari; `x-baraka-tables` — sinxronlanadigan jadvallar (import tartibi, `MUTABLE` / `APPEND_ONLY`, BLOB ustunlar) |
| `oracle.py` | Mustaqil Python implementatsiya (HChaCha20 shu yerda, Argon2id va ChaCha20-Poly1305 — `cryptography`) |
| `vectors.json` | KAT vektorlari: konteyner baytlari, kanonik JSON va yozuv xeshi, birlashtirish qarorlari |

## Fayl tuzilishi
```text
BARAKA-EXPORT\n
{"formatVersion":1,"aead":"xchacha20poly1305","kdf":{"alg":"argon2id","mKib":65536,"tCost":3,"pCost":1},"salt":"<32 hex>","nonce":"<48 hex>"}\n
<shifrlangan JSON Lines + 16 bayt Poly1305 tegi>
```
- Kalit: `Argon2id(NFC(parol), salt, kdf)`, 32 bayt. Parol kamida 8 belgi.
- AAD: birinchi ikki qator (`\n` lari bilan). Sarlavha o'zgartirilsa — fayl ochilmaydi.
- Noto'g'ri parol yoki o'zgartirilgan fayl: `INTERCHANGE_BAD_PASSWORD`.
- Sarlavhadagi KDF chegaralari: `mKib ≤ 262144`, `tCost ≤ 10`, `pCost ≤ 4` (begona fayl qurilmani
  «qotirib» qo'ymasin).

## Tarkib
Har qator — kanonik JSON (kalitlar saralangan, bo'shliqsiz, UTF-8, sonlar faqat butun):
1. `{"kind":"meta", ...}` — xonadon, manba qurilma, `exportId`, `ackExportId`, rejim
   (`FULL | INCREMENTAL | PAIRING`), sxema versiyasi, yozuvlar soni.
2. `{"kind":"row","table":"incomes","data":{...}}` — jadval yozuvi aynan bazadagidek
   (BLOB: `{"b64":"..."}`).

## Birlashtirish (8.4)
Har bir yozuv uchun `base` — shu ikki qurilma oxirgi kelishgan holatning xeshi. Eksportda
yuborilgan yozuvlar «kutilmoqda» bo'ladi va qabul qiluvchining keyingi faylidagi `ackExportId`
bilan tasdiqlanadi. Qaror jadvali (`merge-*` vektorlari):

| Mahalliy | Kelgan | Natija |
|---|---|---|
| yo'q | bor | qo'shiladi |
| = kelgan | | o'zgarishsiz |
| = base | ≠ base | kelgani qabul qilinadi |
| ≠ base | = base | mahalliy qoladi |
| ≠ base | ≠ base | **ziddiyat** — foydalanuvchi tanlaydi (LWW yo'q) |
| `APPEND_ONLY` va farq qiladi | | rad etiladi (yopilgan yozuv o'zgarmaydi) |

Kelishuv jurnali qo'shimcha ravishda zanjir bo'yicha tekshiriladi: kelgan xeshlar qayta
hisoblanadi; mahalliy nusxadan ayrilgan bo'lsa (fork) — import to'xtaydi.

```bash
python3 -I spec/interchange/oracle.py --selftest
python3 -I spec/interchange/oracle.py --check spec/interchange/vectors.json
```
