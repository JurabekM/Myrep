# ADR-0021: Play Integrity — provisioning'da ilova va qurilma yaxlitligi

* Holat: qabul qilingan (2026-10-26, 2-faza P2.6)

## Kontekst

Android Key Attestation (ADR-0013/0015) qurilma **kaliti** apparatda ekanini va yuklash holatini
isbotlaydi, lekin quyidagilarni ko'rsatmaydi:

* ilova o'zgartirilmaganmi (qayta imzolangan / Play'dan tashqari o'rnatilgan klon);
* tizim buzilmaganmi (root, kalit apparat bo'lsa ham OS nazoratda bo'lishi mumkin);
* qurilmada masofaviy boshqaruv yoki ekranni yozuvchi noma'lum ilova bormi (keng tarqalgan
  firibgarlik sxemasi: "bank xodimi" qurbonga masofaviy kirish ilovasini o'rnattiradi va uning
  telefonida kartani tokenlashtiradi).

Tahdid modeli S2 da bu "Play Integrity (stub)" edi. Haqiqiy Google Play Integrity API Google Cloud
loyihasi va Play Console'dagi ilovani talab qiladi — sandbox'da ular yo'q.

## Qaror

1. **Qayerda:** provisioning (`POST /v1/tokens`) — karta qurilmaga bog'lanadigan va pul xavfi
   boshlanadigan nuqta. Har avtorizatsiyada emas (kvota va kechikish; avtorizatsiyani CDCVM va
   Shield qoplaydi). Ro'yxatdan o'tish va rekey'ga kengaytirish — keyin, kerak bo'lsa.
2. **Bog'lanish:** standart so'rov `requestHash = base64url(SHA-256("MPAY-PI-V1" ‖ 0x00 ‖ "provision"
   ‖ 0x00 ‖ PQ Link sessiya ID))`. Token boshqa sessiyada qayta ishlatilmaydi, server nonce uchun
   qo'shimcha aylanma yo'q. PAN xeshga **kirmaydi**: `requestHash` Google'ga ketadi, PAN esa
   xeshdan tiklanadi (BIN ichida ~10⁹ variant).
3. **Ikki qatlam:**
   * *Haqiqiylik va bog'lanish* — serverda, qat'iy: imzo (mock) yoki Google dekodlashi, paket nomi,
     ruxsat etilgan ilova imzo sertifikati, `requestHash`, yangilik (`max_age_secs`, standart 120 s,
     soat farqi 30 s). Buzilsa — `403 INTEGRITY_INVALID` (sabab faqat logda). Token yo'q va
     `required = true` — `403 INTEGRITY_REQUIRED`. Google javob bermasa — `503 INTEGRITY_UNAVAILABLE`
     (fail-closed; mijoz qayta urinadi).
   * *Verdict sifati* — Shield ID&V qoidalarida, soddalashtirilgan `IntegritySignals` (`app`,
     `device`, `licensed`, `env_risk`) orqali; Shield roliga ham shu belgilar ketadi (token emas):
     | Qoida | Shart | Natija |
     |---|---|---|
     | `IDV_INTEGRITY_APP_UNRECOGNIZED` | ilova tanilmagan / baholanmagan | RED |
     | `IDV_INTEGRITY_DEVICE_NONE` | qurilma yaxlitligi yo'q | RED |
     | `IDV_INTEGRITY_ENV_HIGH_RISK` | Play Protect `HIGH_RISK` yoki ekranni noma'lum ilova boshqaradi | RED |
     | `IDV_INTEGRITY_BASIC_ONLY` | faqat basic (yoki virtual) | YELLOW (step-up OTP) |
     | `IDV_INTEGRITY_ENV_RISK` | Play Protect `MEDIUM_RISK` yoki ekran yozuvchi noma'lum ilova | YELLOW |
     | `IDV_INTEGRITY_UNLICENSED` | litsenziyasiz | +300 ball |
     Chegaralar konfiguratsiyadagi qoidalar faylida — bank o'zi o'zgartiradi.
4. **Almashtiriladigan tekshiruvchi** (`mpay-integrity`, `IntegrityVerifier`):
   * `mock` — sandbox: ES256 JWS, mazmuni Play Integrity verdict tuzilmasida; kalit `init` da
     (`sandbox-integrity-mock.key.pem`). Faqat `sandbox = true` bilan. Emulyatordagi demo ilova va
     `mpay-tsim` tokenni `POST /v1/sandbox/integrity-token` (operator kaliti) dan, soft-hamyon va yuk
     generatori — kalitdan oladi. 7 ta stsenariy (`strong`, `device`, `basic`, `no_integrity`,
     `unrecognized`, `play_protect_risk`, `remote_control`).
   * `google` — `decodeIntegrityToken` (OAuth2 access token fayl/muhitdan).
   Production'da `mock` taqiqlangan va `certificate_sha256` majburiy (`validate`).
5. **Hamyon:** Kotlin `Integrity.requestHash` (Rust bilan umumiy test vektori), `MpayClient.provision(…,
   integrityToken)`, wallet-sdk `IntegrityTokenProvider` (production — Play Integrity standart
   so'rovi; sandbox — server mock'i). Rust soft-hamyonda `IntegrityProvider`.

## Oqibatlar

* Root, qayta imzolangan ilova va masofaviy boshqaruv ostidagi qurilmaga karta qo'shilmaydi; basic
  qurilma step-up OTP oladi. Token boshqa sessiya yoki ilovadan o'g'irlab ishlatilmaydi.
* Google mavjud bo'lmasa provisioning to'xtaydi (fail-closed) — to'lovlar (avtorizatsiya) ta'sirlanmaydi.
* Metrika: `mpay_integrity_checks_total{result}` (`ok`, `missing`, `invalid`, `unavailable`, `absent`).
* Tekshirilgan: unit (bog'lanish, verdict xaritasi, JWS buzish, `alg: none`, Google emulyatori), e2e
  `p2_integrity` (4), Kotlin ↔ Rust interop (tokensiz → `INTEGRITY_REQUIRED`, boshqa sessiya tokeni →
  `INTEGRITY_INVALID`, TLS+mTLS orqali), smoke (haqiqiy binarlar, 10 provisioning — 10 verdict),
  emulyatorda demo ilova (`docs/android-testing.md` §7).
* `TODO(spec):`
  * Google bilan haqiqiy integratsiya: Cloud loyiha raqami, Play Console, xizmat akkaunti → access
    token oqimi, Android'da `com.google.android.play:integrity` va `StandardIntegrityManager`.
    Verdict maydonlari Google'ning ochiq hujjatiga muvofiq; integratsiyada joriy hujjat bilan
    qayta solishtiriladi.
  * Kvota va keshlash siyosati (standart so'rov provayderini oldindan tayyorlash).
  * `MEETS_VIRTUAL_INTEGRITY` hozir basic bilan teng — bank siyosatiga ko'ra o'zgartirilishi mumkin.

## Ko'rib chiqilgan muqobillar

* **Klassik so'rov, server nonce'i:** qo'shimcha aylanma va server holati; standart so'rov +
  sessiyaga bog'langan `requestHash` xuddi shu kafolatni beradi (sessiya o'zi server bilan handshake).
* **Faqat qat'iy rad (Shield'siz):** basic qurilmalar (ko'p arzon telefonlar) butunlay chetda qolardi;
  step-up OTP o'rtacha yo'l.
* **Har avtorizatsiyada:** kvota, kechikish (p99 SLA) va oflayn-ga yaqin tap oqimini buzadi.
* **requestHash'ga PAN xeshi:** provisioning'ga qattiqroq bog'lanadi, lekin PAN'ni Google'ga oshkor
  qiladi — rad etildi.
