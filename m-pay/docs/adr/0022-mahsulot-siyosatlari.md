# ADR-0022: Mahsulot siyosatlari — REVIEW, CVM, token muddati, karta–qurilma

* Holat: qabul qilingan (2026-10-26, 2-faza P2.7). Standart qiymatlar — faraz, `TODO(spec)`: bank tasdiqlaydi.

## Kontekst

0–1-fazalarda mahsulot qoidalari qisman va tarqoq edi:

* **CVM:** CDCVM (biometriya) chegarasi faqat qurilmada (Rust `CardPolicy`, Kotlin `CardApplet`) qattiq
  yozilgan. Emitent uni tekshirmasdi — o'zgartirilgan (root'langan) hamyon biometriyasiz istalgan
  summani o'tkaza olardi. Bank chegarani markazdan o'zgartira olmasdi.
* **REVIEW:** Shield REVIEW'da faqat `approve` (standart) yoki `decline` — o'rta yo'l yo'q.
* **Token muddati:** DPAN muddati `min(karta muddati, hozir + 36 oy)` bilan beriladi, lekin
  avtorizatsiyada **tekshirilmasdi**; muddati o'tgan tokenga ham LUK berilardi, LUK muddati token
  muddatidan oshishi mumkin edi.
* **Karta–qurilma:** qurilmadagi tokenlar soni cheklangan, lekin bitta karta nechta qurilmada bo'lishi
  cheklanmagan (faqat Shield ball qo'shardi); bir karta shu qurilmaga takror qo'shilsa ikkinchi token
  yaratilardi.

## Qaror

1. **CVM chegarasi** — `[issuer] cvm_limit_minor` (standart 1 000 000,00 UZS):
   * qiymat token profilida qurilmaga beriladi (`TokenProfileDto.cvm_limit_minor`) va LUK to'ldirish
     javobida yangilanadi (`LuksResponse.cvm_limit_minor`) — bank o'zgartirsa qurilmalar keyingi
     to'ldirishda oladi; eski profilda yo'q bo'lsa qurilma standartini ishlatadi;
   * emitent tekshiradi: summa > chegara va CVR'da `CDCVM_PERFORMED` yo'q → **`Q2` `CVM_REQUIRED`**
     (CVR IAD ichida, ARQC bilan himoyalangan — LUK'siz soxtalashtirib bo'lmaydi). Javob ARPC bilan.
2. **REVIEW** — `[issuer] review_action`: `step_up` (yangi standart), `approve`, `decline`.
   `step_up`: CDCVM bajarilgan bo'lsa `00 APPROVED_AFTER_REVIEW`, aks holda **`Q2` `REVIEW_STEP_UP`** —
   terminal "Telefonda tasdiqlang" ko'rsatadi va o'sha summa bilan qayta tap kutadi. Firibgar
   o'g'irlangan (qulfi ochilgan) telefondan biometriyasiz o'tolmaydi, haqiqiy egasi esa bir harakat
   bilan to'laydi.
3. **`Q2`** — yangi javob kodi (M-Pay profilining `Q`-kodlari; ADR-0007). Haqiqiy sxema kodlari
   o'ylab topilmadi. Rust va Kotlin terminallari `Q2` ni "telefonda tasdiqlang" holatiga aylantiradi.
4. **Token muddati:**
   * avtorizatsiyada DPAN muddati tekshiriladi → **`54` `TOKEN_EXPIRED`** (ISO 8583 dagi ma'nosi
     bilan bir xil). Tekshiruv LUK holatidan **oldin**: LUK muddati token muddatidan oshmagani uchun
     aks holda mijoz tushunarsiz `Q1` ko'rardi. DPAN muddati sir emas (track2'da bor);
   * LUK `expires_at` = `min(hozir + ttl, token muddati tugashi)`; muddati o'tgan tokenga LUK
     berilmaydi (`410 TOKEN_EXPIRED`);
   * muddat oyning oxirigacha, **sxema vaqti bilan — O'zbekiston, UTC+5** (3-faza tayyorgarligida;
     avval UTC edi): `12/29` 2030-01-01 00:00 Toshkent (2029-12-31 19:00 UTC) gacha amal qiladi.
     `CardExpiry::end_unix`, `is_expired(now)`, `current(now)` — Vault, emitent va token muddatini
     hisoblash bir xil qoidada; server qaysi mintaqada ishlamasin natija o'zgarmaydi.
     `TODO(spec):` haqiqiy sxema qoidasi (M-Pay Test Scheme profilining tanlovi);
   * **yangilash** (3-faza tayyorgarligi): `POST /v1/tokens/{id}/renew` — muhrlangan, bog'langan
     qurilmadan. Oxirgi `[vault] token_renew_before_days` (standart 30) kunda yoki muddat o'tgach DPAN
     muddati `min(hozir + token_validity_months, karta muddati)` gacha uzaytiriladi; DPAN, PSN va LUK'lar
     o'zgarmaydi (LUK muddati eski chegara bilan qoladi), audit `TOKEN_RENEWED`. Hali erta yoki
     uzaytirib bo'lmasa — `renewed = false` va joriy profil (takroriy chaqiruv xavfsiz: javob yo'qolsa
     qurilma qayta so'raydi). Profilda `renew_after` (yo'q — karta muddati tugaydi). Hamyon (Kotlin
     `MpayWallet.renewIfDue`) LUK to'ldirishdan oldin tekshiradi;
   * uzaytirish chegarasi — tokenning **o'z** karta muddati (provisioning'da ID&V bilan tasdiqlangan,
     `vault_tokens.card_expiry`): PAN'ni biladigan, lekin OTP'ni o'tmagan provisioning boshqa tokenlarning
     chegarasini o'zgartira olmaydi;
   * karta qayta chiqarilsa (yangi muddat) — kartani qayta qo'shish (ID&V bilan). Muddati o'tgan
     tokenlar chegaralarda (`CARD_ALREADY_ON_DEVICE`, qurilma/karta soni) hisoblanmaydi.
     `TODO(spec):` emitentdan karta yangilanishi xabari (token yangilanishi qayta qo'shishsiz).
5. **Karta–qurilma** — `[vault]`:
   * `max_devices_per_card` (standart 3; 0 — cheklanmagan): boshqa qurilmalar soni chegaraga yetsa
     **`409 TOO_MANY_DEVICES`**; o'chirilgan (DELETED) va muddati o'tgan OTP'li PENDING tokenlar
     hisoblanmaydi;
   * shu karta shu qurilmada allaqachon bo'lsa **`409 CARD_ALREADY_ON_DEVICE`** (ikkinchi token
     ma'nosiz, LUK'lar ikkilanardi);
   * tekshiruvlar provisioning qulfi ostida qayta hisoblanadi (PostgreSQL'da parallel so'rovlar ham
     chegarani buzmaydi — ADR-0018 dagi qayta-sanash mexanizmi).

## Oqibatlar

* Bank siyosatni konfiguratsiyada boshqaradi: `[issuer] review_action`, `cvm_limit_minor`,
  `[vault] max_devices_per_card`, `token_validity_months`, `max_tokens_per_device`.
* `step_up` standart bo'lgani uchun REVIEW'dagi biometriyasiz to'lovlar endi `Q2` oladi (avval
  tasdiqlanardi). Demo va e2e testlar yangilandi.
* Tekshirilgan (muddat va yangilash): `pan` unit (UTC+5 chegarasi: 18:59:59 UTC amal qiladi, 19:00 —
  tugadi), vault `token_renewal_window_and_card_cap` va `expired_token_frees_card_and_device_uzbekistan_time`,
  e2e `token_renewal_over_http` (muddati o'tgan token `54`/`410` → renew → to'lov `00`, LUK), Kotlin ↔ Rust
  interop (`renew` javobi), SQLite va PostgreSQL.
* Tekshirilgan: emitent (`iso_flow`: `Q2` chegara va REVIEW, `54` LUK'dan oldin, `approve`/`decline`),
  vault (qurilmalar chegarasi, takroriy karta, o'chirilgandan keyin joy bo'shashi, LUK muddati
  chegarasi, muddati o'tgan tokenga LUK yo'q), e2e `p2_policy` (profil va LUK javobida chegara,
  o'zgartirilgan hamyon → `Q2`, CDCVM bilan `00`, HTTP 409 kodlari), Kotlin applet (profil chegarasi),
  emulyator (terminal `Q2` ekrani → biometriya → `00 APPROVED_AFTER_REVIEW`).
* `TODO(spec):` ketma-ket CVM'siz kichik to'lovlar soni/summasi chegarasi (kontaktsiz amaliyotdagi
  "cumulative" limit), valyutalar bo'yicha chegara (hozir faqat UZS).

## Ko'rib chiqilgan muqobillar

* **Chegarani faqat qurilmada qoldirish:** o'zgartirilgan hamyonga qarshi himoya yo'q — rad etildi.
* **REVIEW'da OTP/push:** to'lov paytida terminal oldida qo'shimcha kanal kutish noqulay; CDCVM
  allaqachon qurilmada mavjud va kriptogrammaga bog'langan.
* **`05` bilan rad etish (REVIEW'da):** mijoz nima qilishni bilmaydi; `Q2` aniq harakat beradi.
* **Takroriy kartada mavjud tokenni qaytarish:** LUK'lar va token holatini boshqa qurilma nusxasiga
  oshkor qilish xavfi; aniq xato soddaroq.
