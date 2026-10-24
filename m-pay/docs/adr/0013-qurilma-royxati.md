# ADR-0013: Qurilmani ro'yxatdan o'tkazish — attestatsiya challenge'i = server nonce'i

* Holat: qabul qilingan (2026-10-24, 1-faza P1.7)

## Kontekst

Android Key Attestation qurilma holatini (bootloader qulfi, verified boot, OS/patch darajasi) kalit
**yaratilgan paytdagi** holatda yozadi. 0-fazada qurilma kaliti doimiy challenge (`mpay-enroll`) bilan
yaratilardi: qurilma toza paytda yaratilgan kalit, keyinroq root qilinsa ham, "toza" attestatsiyani
ko'rsataverardi; attestatsiya yangiligini server tekshira olmasdi.

## Qaror

1. `POST /v1/pqlink/enroll` — bir martalik 32 baytli nonce (TTL standart 300 s, xotirada,
   IP chegarasi handshake bilan umumiy).
2. Yangi qurilma kalitini `attestationChallenge = nonce` bilan yaratadi va PQ Link handshake qiladi.
3. Server (`EnrollmentGate`, attestatsiya va qurilma imzosidan keyin): qurilma `pqlink_devices`
   reyestrida bo'lsa — ruxsat; bo'lmasa challenge haqiqiy, ishlatilmagan va muddati o'tmagan nonce
   bo'lishi shart — u iste'mol qilinadi va qurilma ro'yxatga olinadi. Aks holda `403 PQLINK_ENROLLMENT`.
4. Ro'yxatdagi qurilma keyingi ulanishlarda nonce'siz ulanadi (StrongBox'da kalitni har safar qayta
   yaratish sekin va qurilma identifikatori — tokenlar bog'langan kalit — o'zgarardi).
5. Hamyon `PQLINK_ENROLLMENT` olsa (masalan reyestr tozalangan) kalitni bir marta yangi nonce bilan
   qayta yaratadi; eski tokenlar yangi qurilmaga o'tmaydi.
6. `[pqlink] enrollment = "required"` (standart) | `"off"` — faqat sandbox (konfiguratsiya tekshiruvi).

## Oqibatlar

* Yangi qurilma attestatsiyasi yangi ekani isbotlanadi; nonce qayta ishlatilmaydi.
* Ro'yxatdagi qurilmaning **keyingi** holat o'zgarishi (root) faqat qayta ro'yxatdan o'tishda ko'rinadi.
  `TODO(spec):` davriy qayta attestatsiya (masalan, N kunda bir) va Play Integrity (2-faza).
* Nonce'lar xotirada — ko'p instansiyada umumiy saqlash kerak (2-faza, ADR-0006 sessiyalari bilan birga).
* Tekshirilgan: Rust e2e `p1_enrollment.rs` (rad, ro'yxat, reyestr, bir martalik, muddat, qayta ishga
  tushish, `off` faqat sandbox), Kotlin interop, emulyatorda haqiqiy Android Keystore (yangi ro'yxat,
  nonce'siz qayta ulanish, reyestr tozalangach avtomatik qayta ro'yxat).

## Ko'rib chiqilgan muqobillar

* **Har sessiyada yangi nonce va yangi kalit** — reyestrsiz, lekin sekin va qurilma identifikatori
  har safar o'zgaradi (tokenlar qurilmaga bog'langan).
* **Doimiy challenge** (0-faza) — attestatsiya yangiligi isbotlanmaydi.
