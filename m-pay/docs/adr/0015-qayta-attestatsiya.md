# ADR-0015: Davriy qayta attestatsiya — qurilma kalitini almashtirish, tokenlar ko'chadi

* Holat: qabul qilingan (2026-10-25, 1-faza qo'shimcha)

## Kontekst

Android Key Attestation **har bir kalitga** bog'langan va kalit yaratilgan paytdagi qurilma holatini
yozadi (ADR-0013). Ro'yxatga olingan qurilma keyinroq root qilinsa, bu faqat yangi kalit bilan
ko'rinadi. Qurilma identifikatori kalitdan hosil bo'ladi va tokenlar unga bog'langan — oddiy qayta
ro'yxatdan o'tish tokenlarni yo'qotadi.

## Qaror

1. `[pqlink] reattest_after_days` (init: 90, 0 — o'chiq): attestatsiya shundan eski bo'lsa muhrlangan
   so'rovlar `403 REATTEST_REQUIRED` oladi. Javob muhrlangan — sessiya ketma-ketligi buzilmaydi.
2. `POST /v1/devices/rekey` (muhrlangan; eskirgan qurilmaga ham ruxsat): yangi kalitning attestatsiya
   zanjiri (challenge = `/v1/pqlink/enroll` nonce'i) va yangi kalit imzosi
   `"MPAY-PQLINK-V1 device-rekey" ‖ session_id ‖ eski device_id` ustidan — yangi kalit aynan shu
   sessiyaga va eski qurilmaga bog'lanadi (boshqa sessiyadan ko'chirib bo'lmaydi).
3. Server: zanjir (ildizlar, siyosat), imzo, nonce (bir martalik) tekshiriladi; yangi kalit ro'yxatda
   bo'lmasligi shart. Vault tokenlarni yangi qurilmaga ko'chiradi (audit `DEVICE_REKEY`), reyestrda
   yangi qurilma yoziladi, eskisi o'chiriladi. Eski sessiya TTL tugaguncha qoladi, lekin tokenlar endi
   unga tegishli emas.
4. Hamyon: `REATTEST_REQUIRED` da ikkinchi alias ostida nonce bilan kalit yaratadi, `rekey`, eski
   kalitni o'chiradi, qayta ulanib so'rovni bir marta takrorlaydi (aliaslar navbatma-navbat).

## Oqibatlar

* Qurilma holati kamida `reattest_after_days` da bir marta yangi attestatsiya bilan tekshiriladi,
  tokenlar saqlanadi.
* Shield qurilma–karta grafida eski qurilma qoladi. `TODO(spec):` rekey'ni Shield'ga voqea sifatida
  uzatish (grafda qurilmalarni bog'lash), aks holda kartani keyinroq qayta qo'shish YELLOW bo'lishi mumkin.
* Tekshirilgan: Rust e2e `p1_reattest.rs` (REATTEST_REQUIRED ketma-ket, nonce'siz kalit rad, token ko'chadi,
  eski kalit rad, to'lov va audit zanjiri; imzo sessiyaga bog'langan), Kotlin interop (Kotlin imzosi → Rust),
  emulyatorda haqiqiy Android Keystore bilan avtomatik qayta attestatsiya.

## Ko'rib chiqilgan muqobillar

* **Qayta ro'yxatdan o'tish (tokenlarsiz)** — foydalanuvchi kartalarni qayta qo'shishi kerak.
* **Faqat Play Integrity** — Google xizmatiga bog'liq va kalit darajasidagi attestatsiyani almashtirmaydi;
  2-fazada qo'shimcha signal sifatida.
