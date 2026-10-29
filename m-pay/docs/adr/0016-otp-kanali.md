# ADR-0016: OTP yetkazish kanali — emitentdagi telefonga SMS (webhook)

* Holat: qabul qilingan (2026-10-25, 2-faza P2.1)

## Kontekst

YELLOW ID&V (masalan, mavjud kartani yangi qurilmaga qo'shish) bir martalik kod talab qiladi. 0–1-fazada
kod faqat sandbox endpointi (`GET /v1/sandbox/otp/{id}`, operator kaliti) orqali olinardi — haqiqiy
foydalanuvchiga yetkazish yo'q edi. Pilot bank hali tanlanmagan, uning SMS shlyuzi spetsifikatsiyasi
noma'lum, shuning uchun kanal virtual muhitda sinaladi.

Asosiy xavf — hisobni egallash (ATO): hujumchi o'g'irlangan karta ma'lumoti bilan o'z telefoniga
token oladi. Kod hujumchi kiritgan raqamga emas, **karta egasining emitentda ro'yxatdan o'tgan**
raqamiga yuborilishi kerak.

## Qaror

1. Telefon raqami faqat emitentda saqlanadi (`issuer_accounts.phone`, E.164). Server uni
   `Issuer::contact_phone(FPAN)` bilan oladi; qurilma raqam yubormaydi va to'liq raqamni ko'rmaydi.
2. Kanal `[otp] channel`: `sandbox` (default — yuborilmaydi) yoki `webhook`:
   `POST url` `{"to","text","reference"}`, `Authorization: Bearer <token>`. Token faqat muhit
   o'zgaruvchisida (`token_env`), TLS — tizim ildizlari + ixtiyoriy `ca_file`.
3. Provisioning `PENDING_IDV` qaytarganda server telefon va kodni oladi, SMS'ni **fonda** yuboradi;
   javobda `otp_sent_to` — maskalangan raqam (`+998*******01`). Sekin yoki osilgan shlyuz javobni
   ushlab turmaydi (aks holda mijoz `challenge_id` ni olmay, token "yetim" qolardi).
4. `POST /v1/tokens/{id}/idv/resend` (sealed, qurilma tekshiruvi): o'sha kodni qayta yuboradi. Faqat
   token `PENDING_IDV` da va challenge bloklanmagan bo'lsa (3 noto'g'ri koddan keyin `423 OTP_LOCKED` —
   ishlatib bo'lmaydigan kod uchun SMS yuborilmaydi). Chegara — 3 marta (`429 OTP_RESEND_LIMIT`).
   SMS **aniq ketmagan** urinish (emitentda raqam yo'q, ulanib bo'lmadi, shlyuz 4xx/5xx) hisoblagichni
   qaytaradi; natija noma'lum bo'lsa (javob kutish vaqti tugadi) — hisoblanadi.
5. Shlyuzga yuborish: 5xx yoki tarmoq xatosida bitta qayta urinish, 4xx da qayta urinilmaydi.
   Ulanish vaqti alohida chegaralanadi (`timeout_ms / 2`, ≤ 2 s). `reference = challenge_id` —
   shlyuz tomonida idempotentlik uchun. `http://` faqat loopback yoki `insecure_http = true` bilan.
   Token muhit o'zgaruvchisida; CLI buyruqlari (`identity`, `audit-verify`) OTP kanalisiz yig'iladi.
6. Logga OTP va SMS matni yozilmaydi; telefon faqat maskalangan holda. Mamlakat kodi faqat ma'lum
   ro'yxatda (`+998`) ochiq qoladi — boshqa kodlarda `+` va oxirgi 2 raqam.
7. Sinov uchun virtual shlyuz `mpay-smsgw` (alohida test vositasi, server binariga kirmaydi).

## Oqibatlar

* Hujumchi qurilmasi kodni olmaydi — kod karta egasiga boradi; maskalangan raqam foydalanuvchiga
  qayerga kod kelishini ko'rsatadi.
* Emitentda raqami yo'q karta uchun YELLOW oqimini yakunlab bo'lmaydi (`409 NO_CONTACT`).
  `TODO(spec):` pilot bank bilan muqobil kanal (bank ilovasiga push, call-center).
* `TODO(spec):` haqiqiy shlyuz formati (SMPP/HTTP), SMS matni, yuboruvchi nomi, qayta yuborish chegarasi
  va narx — pilot bank bilan kelishiladi; webhook adapteri shu nuqtada almashtiriladi.
* SIM-swap hujumi bu qarorda yopilmaydi. `TODO(spec):` emitent/operator SIM-swap belgisi Shield'ga.
* Tekshirilgan: e2e `p2_otp.rs` (4 test: yetkazish, qayta yuborish, chegara, boshqa qurilma rad,
  telefonsiz hisob, operator nosozligi va hisoblagich qaytishi, shlyuz o'chgan, bloklangan kodga SMS
  yo'q, sandbox kanali, loglarda OTP/telefon yo'q),
  Kotlin interop (haqiqiy `mpay-server` + `mpay-smsgw`, kod SMS'dan o'qiladi).

## Ko'rib chiqilgan muqobillar

* **Qurilma kiritgan raqamga SMS** — ATO'dan himoya qilmaydi.
* **Kodni bank ilovasiga push** — bankning mobil ilovasi bilan integratsiya talab qiladi; pilotda keyin.
* **Har qayta yuborishda yangi kod** — tekshirish urinishlari chegarasini aylanib o'tish yo'lini ochadi;
  o'sha kod va bitta urinishlar hisoblagichi soddaroq va xavfsizroq.
