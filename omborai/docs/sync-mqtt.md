# Sinxronizatsiya: faqat MQTT (broker.hivemq.com)

Qaror (foydalanuvchi tomonidan tasdiqlangan): ilovalar ma'lumot almashinuvi uchun faqat MQTT broker
`broker.hivemq.com` dan foydalanadi. REST sinxronizatsiya (`/v1/sync/*`) o'rniga shu protokol ishlatiladi.

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
{"op_id": "<uuid>", "type": "sale|refund|movement|product",
 "device": "<uuid>", "ts": "<ISO 8601>", "store_id": "<uuid>", "payload": {...}}
```

## Semantika

- Har bir operatsiya `op_id` (UUID) bilan noyob. Qabul qiluvchi `applied_ops` jadvalida dublikatni rad etadi
  (QoS 1 "kamida bir marta" kafolatlaydi, dedupe esa "bir marta" ta'sirini beradi).
- Qurilma o'z operatsiyasini avval o'zida qo'llaydi, keyin nashr qiladi. Boshqa qurilmalar xuddi shu
  operatsiyani qo'llaydi. Natijada hamma qurilmada qoldiq bir xil bo'ladi (hodisalar ketma-ketligi).
- Tovar (`product`) o'zgarishlari: oxirgi yozgan g'olib (`ts`, keyin `device`). Qoldiq: append-only.

## Ma'lum cheklovlar (muhim)

- **Markaziy hakam yo'q.** Ikki oflayn qurilma bir vaqtda oxirgi donani sotsa, qoldiq manfiyga tushishi
  mumkin. Bunday holat aniqlanadi va hisobotda belgilanadi, lekin oldindan to'xtatib bo'lmaydi.
- **Yetkazib berish kafolati broker darajasida.** Ommaviy brokerda uzoq muddatli xabar saqlash va uptime
  kafolati yo'q. Uzilish paytida yuborilgan xabar yo'qolishi mumkin. Qurilma o'z outbox'ini saqlaydi va
  ulanganda qayta nashr qiladi (dedupe himoya qiladi).
- **Chek va qaytarish tarixi** faqat qurilmalarda saqlanadi (server bazasi yo'q). Hisobotlar qurilma
  ichida hisoblanadi.
- Xususiy broker (Mosquitto, TLS + login) bilan ishlash uchun faqat manzil va autentifikatsiya sozlamasi
  o'zgaradi, protokol o'zgarmaydi.

## Fiskal kassa / OFD

Hozirda ishlab chiqish jarayonida. Ilovalarda "Fiskal chek: ishlab chiqish jarayonida" deb ko'rsatiladi.
