# Sinxronizatsiya protokoli v2: imzolangan operatsiyalar (MQTT)

Holat: amalga oshirilmoqda (2026-10-11). Desktop (Python) va mobil (Dart) bir xil shartnomaga amal qiladi.
Versiya `v: 2`. v1 bilan mos emas: eski qurilmalar qayta o'rnatiladi.

## 1. Tahdid modeli

- **Kassir qurilmasi ishonchsiz.** U do'kon kalitini biladi, lekin egasi nomidan operatsiya yubora olmaydi, narxni
  o'zgartira olmaydi, egani nofaol qila olmaydi, yangi qurilma qo'sha olmaydi.
- Har bir operatsiya muallif qurilmasining Ed25519 kaliti bilan **imzolanadi**. Qabul qiluvchi imzoni, muallifning
  faolligini va turiga mos ruxsatni tekshiradi.
- Broker ommaviy (`broker.hivemq.com`). Mavzu va xabar `K` (do'kon kaliti) bilan shifrlanadi.
- **Ochiq qolgan xavf:** `K` kassirda ham bor, shuning uchun kassir shifrlangan ma'lumotni (jumladan parol xeshlarini)
  o'qiy oladi. Bu imzolash bilan hal bo'lmaydi; alohida bosqichda hal qilinadi (10-bo'lim).

## 2. Kalitlar

| Kalit | Kim yaratadi | Qayerda saqlanadi | Vazifasi |
|---|---|---|---|
| `K` (32 bayt) | do'konni yaratgan qurilma | OS keyring / Android Keystore | xabarni shifrlash, mavzu nomi |
| Qurilma kaliti (Ed25519, 32 baytlik seed) | har qurilma o'zi | OS keyring / Android Keystore | operatsiyani imzolash |

Mavzu: `omborai/v2/` + `hex(HKDF-SHA256(K, salt=None, info="topic", L=16))` + `/ops`.

## 3. Juftlash kodi

`<store_id>:<owner_device_id>:<owner_public_key_hex>:<store_key_hex>`

- Egasi qurilmasi (role `owner`) ko'rsatadi. Boshqa rollarga bu ekran ko'rinmaydi.
- Kod sir: `K` va egasining ochiq kaliti shu yerda. Ishonch ildizi shu kod.

## 4. Konvert (broker ko'radigan bayt)

```json
{"v": 2, "n": "<base64, 12 bayt>", "c": "<base64, shifrlangan matn || 16 bayt GCM tegi>"}
```

AES-256-GCM, kalit `K`, nonce tasodifiy, AAD = mavzu nomining UTF-8 baytlari.

## 5. Operatsiya (shifrlangan JSON)

```json
{"op_id": "<uuid>", "type": "<tur>", "device": "<device_id>", "ts": "<ts>",
 "store_id": "<uuid>", "payload": {...}, "sig": "<base64, 64 bayt>"}
```

- `ts`: UTC, **aniq shu format**: `YYYY-MM-DDTHH:MM:SS.ffffffZ` (6 ta kasr raqam). Solishtirish satr bo'yicha.
- **Imzo:** `Ed25519_sign(qurilma_kaliti, canonical(op))`, bunda `op` da `sig` maydoni yo'q.
- **Canonical JSON:** kalitlar Unicode tartibida saralangan (rekursiv), bo'shliqsiz (`,` `:`), `ensure_ascii=false`,
  faqat butun sonlar (float yo'q), UTF-8 baytlar. Boshqaruv belgilari (U+0000–U+001F) qiymatlarda ishlatilmaydi.
- Qabul qiluvchi `device` maydoni orqali muallifni roster'dan topadi va imzoni shu kalit bilan tekshiradi.

## 6. Operatsiya turlari va ruxsatlar

| `type` | Imzolovchi | Payload | Qo'llash |
|---|---|---|---|
| `device` | owner | `{device_id, public_key, role, label, active}` | Qurilma qo'shish, rol, bloklash. `public_key` o'zgarmaydi. LWW |
| `join_request` | o'zi (imzo `payload.public_key` bilan) | `{device_id, public_key, label}` | Yangi qurilma so'rovi. Egasi tasdiqlaydi. Qo'llanmaydi |
| `store` | owner | `{name}` | LWW |
| `user` | owner | `{id, login, name, role, salt, pw_hash, active}` | LWW |
| `product` | owner | `{id, name, unit, sale_price, cost_price, min_stock, barcodes, deleted}` | LWW; narx tarixi saqlanadi |
| `movement` | owner | `{product_id, qty, kind}`, kind: `receipt`, `adjustment`, `writeoff` | Qoldiq |
| `sale` | owner yoki kassir qurilmasi | chek (5.1) | Narxlar katalogga mos bo'lishi shart |
| `shift_open` | faol qurilma | `{shift_id, opening_cash}` | Qurilmada bitta ochiq smena |
| `shift_close` | smena ochgan qurilma yoki owner | `{shift_id, closing_cash, summary}` | Faqat ochiq smenani yopadi |
| `refund` | owner | `{sale_id, items: [{product_id, qty}]}` | Qaytarish o'z mahsulotlarini olib yuradi; bir chek bir marta |
| `snapshot` | owner | 5.2 | Yangi qurilmaga to'liq holat. Faqat bootstrap bo'lmagan qurilma qabul qiladi |
| `snapshot_request` | faol qurilma | `{}` | Qo'llanmaydi. Owner javob beradi |

`op_id` qoidalari: `sale` = sotuv UUID; `refund` = `refund:<sale_id>`; `shift_open` = smena UUID; qolganlari UUID.
Bir xil `op_id` ikki marta qo'llanmaydi (`applied_ops`).

### 6.1. Sotuv tekshiruvi (hamma qurilmada bir xil)

- Har `items[i]`: `qty > 0`, `unit_price` = `ts` vaqtidagi katalog narxi (narx tarixidan, `ts` dan oldingi oxirgi yozuv),
  `line_total = round_half_up(qty * unit_price)`.
- `subtotal = sum(line_total)`, `0 <= discount <= subtotal`, `total = subtotal - discount`.
- Katalog narxi hali kelmagan bo'lsa — operatsiya **kutiladi** (pending). Narx mos kelmasa — **rad etiladi**.

### 6.2. Qaytarish

- `refund` egasi tomonidan imzolanadi. `items` o'z-o'zidan to'liq: sotuv qatori bo'lmasa ham qoldiq tiklanadi.
- Qoldiq yozuvi `refund:<sale_id>:<product_id>`, `kind = sale_return`. Chek allaqachon qaytarilgan bo'lsa — rad.
- Sotuv qatori bor bo'lsa, `status = refunded`. Qaytarish sotuvdan oldin kelsa, `refunded_sales` da yoziladi;
  sotuv keyin kelganda shu yerdan `refunded` bo'ladi. Qoldiq natijasi tartibga bog'liq emas.

### 6.3. Smena

- Har bir qurilmaning o'z smenasi bor (kassa yashigi qurilmada). `shift_open` qurilma ochiq smenasi bo'lsa rad.
- `opened_at = op.ts`. Smena UI'si shu qurilmaning smenasini ko'rsatadi.

## 7. Qurilma qo'shish (juftlash va tasdiqlash)

1. **Yangi qurilma** kodni kiritadi: `store_id`, egasi `device_id` va ochiq kalit, `K` saqlanadi. Roster'da faqat egasi.
   Yangi qurilma o'z kalitini yaratadi (agar bo'lmasa).
2. Yangi qurilma `join_request` yuboradi (o'z kaliti bilan imzolangan), har 15 soniyada, tasdiq kelguncha.
3. **Egasi** qurilmasi so'rovni ko'radi (imzo tekshiriladi) va so'raydi: kassir / egasi sifatida qo'shilsinmi yoki rad.
   Tasdiqlansa `device` operatsiyasini yuboradi (egasi imzosi bilan).
4. Yangi qurilma o'z `device` yozuvini egasi imzosi bilan oladi (bootstrap oldin ham qabul qilinadi) va
   `snapshot_request` yuboradi.
5. Egasi `snapshot` yuboradi. Yangi qurilma uni qabul qiladi, bootstrap bo'ladi, login ochiladi.

Egasi qurilmasi o'chiq bo'lsa, yangi qurilma kutadi va "egasi qurilmasini tekshiring" xabarini ko'rsatadi.

## 8. Qabul qilish tartibi

1. Konvertni oching (`v == 2`, GCM tegi). Xato — tashlanadi.
2. JSON va majburiy maydonlarni tekshiring. Xato — tashlanadi.
3. `snapshot_request` / `join_request` — 7-bo'limga qarang, operatsiya sifatida qo'llanmaydi.
4. **Bootstrap bo'lmagan qurilma** (`bootstrapped = 0`):
   - Owner imzosidagi `device` va owner imzosidagi `snapshot` qo'llanadi.
   - Qolgan hamma operatsiya **bufer**ga (pending) yoziladi. Holat o'zgarmaydi.
5. **Bootstrap bo'lgan qurilma:**
   - `op.ts <= bootstrap_ts` (`device` va `snapshot` bundan mustasno) — snapshot ichida, tashlanadi.
   - Muallif (`device`) roster'da bo'lmasa — pending.
   - Imzo noto'g'ri yoki muallif faol emas — tashlanadi.
   - Tur bo'yicha ruxsat (6-jadval) va 6.1–6.3 tekshiruvi. Rad — tashlanadi; kutish — pending.
   - Qo'llash (bitta tranzaksiyada, `applied_ops` bilan birga).
6. `device`, `product` yoki `snapshot` qo'llanganidan keyin pending ro'yxati qayta ko'rib chiqiladi.

LWW (`store`, `user`, `product`, `device`): kalit `(ts, op_id)`. Yangisi g'olib. Teng bo'lsa `op_id` katta bo'lgani.

## 9. Snapshot va bootstrap

`snapshot` payload (owner imzosi bilan):

```json
{"store": {"name": "...", "updated_ts": "..."},
 "devices": [{"device_id", "public_key", "role", "label", "active", "updated_ts"}],
 "users": [{"id", "login", "name", "role", "salt", "pw_hash", "active", "updated_ts"}],
 "products": [{"id", "name", "unit", "sale_price", "cost_price", "min_stock", "barcodes", "deleted", "updated_ts"}],
 "balances": {"<product_id>": "<qty>"},
 "open_shifts": [{"id", "device", "opening_cash", "opened_at"}]}
```

- Snapshot `ts = T`. Qabul qilinganda: `bootstrapped = 1`, `bootstrap_ts = T`.
- Bootstrap oldin kelgan jonli operatsiyalar bufer'da. Bootstrapdan keyin: `ts > T` bo'lganlari qo'llanadi, `ts <= T` bo'lganlari tashlanadi
  (ular snapshot ichida). Shunday qilib jonli operatsiya snapshot'ni rad ettirmaydi (K5).
- Ma'lum cheklov: `ts <= T` bo'lgan, lekin egaga `T` gacha yetib bormagan operatsiya yo'qoladi. Vaqt xatosi (soat siljishi) ham
  shu oynani o'zgartiradi. Qisqa oyna, hujjatlangan.
- Sotuv tarixi snapshot'ga kirmaydi. Qaytarish o'z-o'zidan to'liq bo'lgani uchun buning ta'siri yo'q.

## 10. Cheklovlar (ochiq)

- **Maxfiylik:** `K` kassirda bor, u shifrlangan ma'lumotni o'qiydi (parol xeshlari ham). Keyingi bosqich: xabarlarni
  qurilmaga alohida shifrlash yoki parol xeshlarini egasiga cheklash.
- Qoldiq: ikki qurilma bir vaqtda oxirgi donani sotsa, qoldiq manfiy bo'lishi mumkin (qabul qilingan).
- Broker kafolati yo'q: outbox + dedupe. Mobil ulanish `clean session` bilan emas (persistent), PUBACK kelgandan keyin navbat o'chadi.
- Vaqt manbai — qurilma soati (NTP tavsiya etiladi).

## 11. Test vektorlari

Kross-platforma (desktop va mobil bir xil natija berishi shart):
- `K` = bayt `0x00..0x1f`. Mavzu: `omborai/v2/<hex>/ops` — testlarda hisoblanadi (`tests/test_vectors.py`, `test/vectors_test.dart`).
- Qurilma kaliti seed `0x01..0x20` bo'lsa, imzo va public key qiymatlari testda qayd etiladi.
- Canonical JSON va imzo qiymatlari ikki tilda ham bir xil bo'lishi shart.
