# `.baraka` almashish formati (v1)

Telefon va desktop ilovalari uchun **umumiy** format (DESKTOP_PROMPT 6.3). Mobil ilova ham shu faylni o'qiy va yoza olishi shart.

## 1. Konteyner (shifrlash)

Fayl bayt tuzilmasi (hammasi big-endian):

| Offset | Uzunlik | Maydon |
|---|---|---|
| 0 | 8 | `magic` = ASCII `BARAKA1\n` |
| 8 | 4 | Argon2id `m_kib` (xotira, KiB) |
| 12 | 4 | Argon2id `t` (o'tishlar) |
| 16 | 4 | Argon2id `p` (parallellik) |
| 20 | 16 | `salt` (tasodifiy) |
| 36 | 24 | `nonce` (tasodifiy) |
| 60 | … | `ciphertext ‖ tag` (XChaCha20-Poly1305, 16 bayt tag) |

- Kalit: `Argon2id(parol UTF-8, salt, m_kib, t, p) → 32 bayt` (versiya 0x13).
- AEAD: XChaCha20-Poly1305, `AAD` = 0..60-baytlar (butun sarlavha), ochiq matn = UTF-8 JSON (2-bo'lim).
- Ishlab chiqarish parametrlari: `m_kib = 65536`, `t = 3`, `p = 1`. O'qishda DoS'dan himoya: `8 ≤ m_kib ≤ 1048576`, `1 ≤ t ≤ 10`, `1 ≤ p ≤ 8`.
- Parol kamida 8 ta belgi. AEAD noto'g'ri parolni buzilgan shifrlangan qismdan farqlay olmaydi: tegi mos kelmasa «parol noto'g'ri yoki fayl buzilgan» deb ko'rsatiladi; `magic`/uzunlik/KDF chegaralari buzilgan bo'lsa «bu .baraka fayli emas».

## 2. Hujjat

JSON Schema: [`export-format.schema.json`](export-format.schema.json); minimal misol: [`example-export.json`](example-export.json).

- `tables[]` — ota jadvallar oldin. Har bir yozuv — jadval ustunlari → qiymat.
- Qiymat turlari: `null`, **butun son**, matn, yoki `{"$blob": "<kichik harfli hex>"}`. **Kasr son yo'q** (pul — eng kichik birlikdagi butun son, masalan tiyin).
- Sana-vaqt — RFC 3339 UTC; kalendar sana — `YYYY-MM-DD`.
- Eksport qilinmaydi: `member_credentials` (PIN xeshlari qurilmaga xos) va `settings` (qurilma sozlamalari).
- `since` — inkremental eksport (`updated_at > since`; tombstone'lar ham kiradi); to'liq eksportda `null`.
- `schema_version` — eksport qilgan ilovaning baza sxemasi. Import qiluvchi **yangiroq** `format_version` yoki `schema_version`ni rad etadi («ilovani yangilang»); eskisini qabul qiladi.

## 3. Import va birlashtirish qoidalari

1. Yozuvlar `id` bo'yicha moslashadi. Lokal yo'q → qo'shiladi.
2. Bir xil `id`: **`version` kattasi yutadi; teng bo'lsa `updated_at` kechrog'i; ikkalasi teng bo'lsa lokal qoladi.**
3. `deleted_at` (tombstone) oddiy yangilanish sifatida qo'llanadi (qattiq o'chirish yo'q).
4. Bir xil `version`, turlicha tarkib — **ziddiyat**: foydalanuvchiga ro'yxat ko'rsatiladi (g'olib: `updated_at` bo'yicha).
5. **Yopilgan davrlar** (`venture_periods.status = CLOSED`, ularning `venture_entries`, `venture_attachments`) va `venture_distributions`, shuningdek **imzolangan shartnoma** jadvallari (`partnership_versions`, `partnership_signatures`) import orqali o'zgartirilmaydi. Farq bo'lsa lokal qoladi va ogohlantirish (ziddiyat) chiqadi. Davr faqat ochiqdan yopiqqa o'tishi mumkin (yozuvlari va taqsimoti bilan birga).
6. **Standart (seed) yozuvlar** qurilmalarda turli `id` bilan yaratiladi; dublikat bo'lmasligi uchun ular tabiiy kalit bo'yicha lokalga ulanadi: `categories(name)`, `members(display_name, role)`, `assets(asset_type=VAULT, name, vault_type)`, `allocation_rules(kind, currency)`. Hujjatdagi `id` lokal `id`ga almashtiriladi (FK'lar ham).
7. Xonadon: lokal xonadon bor bo'lsa hujjatdagi `household_id` lokalga almashtiriladi; lokal xonadon bo'lmasa (yangi qurilma) hujjatdagisi qabul qilinadi.
8. Bazaga sig'maydigan yozuv (unikal cheklov, ota yozuv yo'q) o'tkazib yuboriladi va ziddiyat ro'yxatida `REJECTED` bo'lib ko'rinadi.
9. Qo'llash — yagona tranzaksiya; avval «oldindan ko'rish» (hech narsa saqlanmaydi) xuddi shu hisobotni beradi.

Ziddiyat turlari: `DIVERGED`, `CLOSED_PERIOD`, `SIGNED_CONTRACT`, `REJECTED`; yechim: `KEPT_LOCAL`, `TOOK_INCOMING`, `SKIPPED`.
