# Zarbxona v3 — AI coder uchun topshiriq

Senga `zarbxona_v3_spec/` to'plami berildi: `SPEC.md` (to'liq spetsifikatsiya),
`kat/zarbxona_kat_v1.json` (namunaviy vektorlar), `tools/kat_tekshir.py`
(standart kutubxonalar bilan ishlaydigan namuna tekshiruvchi).
AETHER-Q loyihasining boshqa kodi senda yo'q va kerak emas.

**Vazifa:** SPEC.md bo'yicha AETHER-Q Zarbxona v3 ni yoz — Python 3.12+, PySide6
dark UI, `cryptography>=47`, `paho-mqtt`. Asosiy xususiyat: pul **sekin, protsessorni
kam band qilib, jonli monitor ostida** zarb qilinadi (§14), katta buyurtma kichik
partiyalarga bo'linadi va uzilishdan keyin davom etadi (§15).

**Tartib:**
1. `python tools/kat_tekshir.py kat/zarbxona_kat_v1.json` → `HAMMASI MOS` ekanini ko'r.
2. `core/` ni yoz (§17) va KAT testidan o'tkaz (T1–T2). Bayt-ma-bayt mos kelmaguncha
   keyingi qadamga o'tma.
3. Sur'at, buyurtma, tiklash, tekshiruvchi, protokol (soxta sessiya bilan), keyin GUI.
4. §18.1 dagi hamma test o'tsin. §18.2 ni README'ga foydalanuvchi uchun buyruqlar
   bilan yoz.

**Eng ko'p xato qilinadigan joylar (§19):**
- AQ-KMAC256 standart emas: pycryptodome/OpenSSL KMAC boshqa natija beradi (§2.2).
- LE u64 va BE u32 prefikslar aralashtirilmaydi (§2.6).
- Summa u128, toq Merkle tugun nusxalanmaydi, barg ≠ sarlavha xeshi.
- AETHER-Q sessiyasini o'zing yozma, faqat adapter (§13.3).
- Partiya kaliti va master diskka yozilmaydi.

Hujjat va interfeys o'zbek tilida. Taxminiy raqamni o'lchangan deb, «tekshirilmadi»ni
«toza» deb ko'rsatma. Oxirida nima qilinganini, nima sinalganini va nima sinalmaganini
(ayniqsa §18.2) halol yoz.
