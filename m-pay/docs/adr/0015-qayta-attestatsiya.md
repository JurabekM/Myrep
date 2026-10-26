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
* Shield'ga hodisa (3-faza tayyorgarligida bajarildi): tokenlar ko'chgach Vault
  `IdvDecider::device_rekeyed(old, new)` chaqiradi. Shield grafida yangi ID eski qurilma tuguniga
  **taxallus** bo'ladi (zanjir bo'ylab asl tugunga): kartalar soni, `card_device_count`, qurilma yoshi va
  oynalari saqlanadi. Busiz kartani o'chirib qayta qo'shish `IDV_NEW_DEVICE_EXISTING_CARD` → YELLOW
  bo'lardi (e2e'da tuzatishsiz aynan shu bilan yiqilishi tekshirilgan).
  * Yomon tarix ham meros bo'ladi — rekey qurilma obro'sini "tozalash" yo'li emas. Bog'lash faqat
    attestatsiya, bir martalik nonce va eski kalit imzosidan keyin.
  * `new` Shield'da allaqachon o'z tarixiga ega bo'lsa — bog'lanmaydi (`linked = false`).
  * Shield roli: `POST /internal/shield/rekey`; API instansiyasining mahalliy zaxira dvigateli ham
    bog'lanadi. Hodisa yetkazilmasa — faqat ogohlantirish va `mpay_shield_degraded_total`: tokenlar
    allaqachon ko'chgan, oqibat xavfsiz tomonga (ortiqcha step-up).
* Tekshirilgan: e2e `p2_shield_role` — `rekeyed_device_keeps_shield_history_locally` (mahalliy dvigatel)
  va `rekey_event_reaches_shield_role` (Shield roli: 2 qurilma, 3 graf tuguni, kalitsiz 401): qayta
  qo'shish GREEN, nazorat (haqiqatan boshqa qurilma) `IDV_NEW_DEVICE_EXISTING_CARD`; graf unit testi
  (zanjir, takror, o'z tarixi bor ID rad).
* Tekshirilgan: Rust e2e `p1_reattest.rs` (REATTEST_REQUIRED ketma-ket, nonce'siz kalit rad, token ko'chadi,
  eski kalit rad, to'lov va audit zanjiri; imzo sessiyaga bog'langan), Kotlin interop (Kotlin imzosi → Rust),
  emulyatorda haqiqiy Android Keystore bilan avtomatik qayta attestatsiya.

## Ko'rib chiqilgan muqobillar

* **Qayta ro'yxatdan o'tish (tokenlarsiz)** — foydalanuvchi kartalarni qayta qo'shishi kerak.
* **Faqat Play Integrity** — Google xizmatiga bog'liq va kalit darajasidagi attestatsiyani almashtirmaydi;
  2-fazada qo'shimcha signal sifatida.
