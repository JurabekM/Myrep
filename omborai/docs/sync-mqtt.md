# Sinxronizatsiya: faqat MQTT (broker.hivemq.com)

Qaror (foydalanuvchi tomonidan tasdiqlangan): ilovalar ma'lumot almashinuvi uchun faqat MQTT broker
`broker.hivemq.com` dan foydalanadi. Ma'lumot almashinuvi (savdo, qaytarish, smena, tovar, qoldiq) faqat
shu protokol orqali o'tadi. REST faqat autentifikatsiya va do'konlar ro'yxati uchun qoldi (`/v1/auth/*`,
`/v1/stores`); `/v1/sync/*` va savdo/smena endpointlari klientlar tomonidan ishlatilmaydi.

## Xavfsizlik modeli

- Broker ommaviy: autentifikatsiya yo'q, har kim mavzuni kuzatishi mumkin. Shuning uchun **barcha xabarlar
  ilova ichida shifrlanadi** (AES-256-GCM). Broker faqat shifrlangan baytlarni ko'radi.
- Do'kon kaliti (32 bayt) qurilmalar o'rtasida qo'lda juftlanadi (QR yoki matn). Kalit ilovada xavfsiz
  xotirada saqlanadi (desktop: OS keyring, mobil: Android Keystore). Kalit hech qayerga yuborilmaydi.
- Mavzu nomi kalitdan HKDF orqali olinadi: `omborai/v1/<hex>/ops`. Kalitsiz mavzuni topib bo'lmaydi.
- Metama'lumot (vaqt, xabar hajmi, mavzu band bo'lishi) broker tomonidan ko'rinadi. Bu qabul qilingan xavf.

## Kalit va mavzu

- `K` — do'kon kaliti, 32 bayt tasodifiy.
- `topic = "omborai/v1/" + hex(HKDF-SHA256(K, info="topic", len=16)) + "/ops"`
- Shifrlash: `AES-256-GCM(K)`, nonce 12 bayt (tasodifiy), AAD = `topic` baytlari.

## Xabar formati (JSON, QoS 1)

```json
{"v": 1, "n": "<base64 nonce>", "c": "<base64 ciphertext+tag>"}
```

Ochiq matn (shifrdan keyin) — operatsiya:

```json
{"op_id": "<uuid>", "type": "<tur>",
 "device": "<uuid>", "ts": "<ISO 8601>", "store_id": "<uuid>", "payload": {...}}
```

Operatsiya turlari:

| `type`             | `op_id`                     | Mazmuni                                                          |
|--------------------|-----------------------------|------------------------------------------------------------------|
| `sale`             | sotuv UUID                  | Chek: items (product_id, qty), payments, total; qoldiq kamayadi  |
| `refund`           | `refund:<sale_id>`          | Qaytarish: qoldiq tiklanadi, chek `refunded`. Bir chek bir marta |
| `shift_open`       | smena UUID                  | Smena ochish. Ochiq smena bor bo'lsa e'tiborsiz                  |
| `shift_close`      | operatsiya UUID             | Smena yopish, hisobot (summary) bilan                            |
| `movement`         | operatsiya UUID             | Kirim / tuzatish (qoldiq o'zgarishi)                             |
| `product`          | operatsiya UUID             | Tovar qo'shish / tahrirlash / o'chirish (LWW, `ts` bo'yicha)     |
| `snapshot`         | operatsiya UUID             | Yangi qurilmaga to'liq holat: tovarlar, qoldiqlar, ochiq smena  |
| `snapshot_request` | operatsiya UUID             | Yangi qurilma so'raydi; boshqa qurilma `snapshot` yuboradi       |

## Semantika

- Har bir operatsiya `op_id` (UUID) bilan noyob. Qabul qiluvchi `applied_ops` jadvalida dublikatni rad etadi
  (QoS 1 "kamida bir marta" kafolatlaydi, dedupe esa "bir marta" ta'sirini beradi).
- Qurilma o'z operatsiyasini avval o'zida qo'llaydi, keyin nashr qiladi. Boshqa qurilmalar xuddi shu
  operatsiyani qo'llaydi. Natijada hamma qurilmada qoldiq bir xil bo'ladi (hodisalar ketma-ketligi).
- Tovar (`product`) o'zgarishlari: oxirgi yozgan g'olib (`ts`, keyin `device`). Qoldiq: append-only
  (`movements` jadvali; sotuv manfiy, qaytarish musbat yozuv).
- Qaytarish: `refund:<sale_id>` op_id hamma qurilmada bir xil, shuning uchun bir chekni ikki qurilmadan
  qaytarish ham qoldiqni ikki marta tiklamaydi. Chek allaqachon `refunded` bo'lsa e'tiborsiz.
- Yangi qurilma (bo'sh bazasi bilan) ulanganda `snapshot_request` yuboradi. Boshqa qurilma (eng birinchi
  javob beruvchi) `snapshot` bilan javob beradi: tovarlar, qoldiqlar, ochiq smena. `snapshot` faqat
  `applied_ops` bo'sh qurilmada qo'llanadi. Qurilmada allaqachon ma'lumot bo'lsa u e'tiborsiz qoldiriladi.
- Qurilma o'zining xabarini (`device == o'zim`) qayta qo'llamaydi.

## Ma'lum cheklovlar (muhim)

- **Markaziy hakam yo'q.** Ikki oflayn qurilma bir vaqtda oxirgi donani sotsa, qoldiq manfiyga tushishi
  mumkin. Bunday holat aniqlanadi va hisobotda belgilanadi, lekin oldindan to'xtatib bo'lmaydi.
- **Yetkazib berish kafolati broker darajasida.** Ommaviy brokerda uzoq muddatli xabar saqlash va uptime
  kafolati yo'q. Uzilish paytida yuborilgan xabar yo'qolishi mumkin. Qurilma o'z outbox'ini saqlaydi va
  ulanganda qayta nashr qiladi (dedupe himoya qiladi).
- **Snapshot poygasi.** Snapshot va shu paytda kelgan jonli operatsiyalar tartibi kafolatlanmaydi. Snapshot
  tugallangach, tashqarida qolgan yozuvlar qo'lda tekshirilishi kerak (kichik oynada qoldiq farqi bo'lishi
  mumkin). Hozircha hal qilinmagan.
- **Chek va qaytarish tarixi** faqat qurilmalarda saqlanadi (server bazasi yo'q). Hisobotlar qurilma
  ichida hisoblanadi.
- Xususiy broker (Mosquitto, TLS + login) bilan ishlash uchun faqat manzil va autentifikatsiya sozlamasi
  o'zgaradi, protokol o'zgarmaydi.

## Fiskal kassa / OFD

Hozirda ishlab chiqish jarayonida. Ilovalarda "Fiskal chek: ishlab chiqish jarayonida" deb ko'rsatiladi.
