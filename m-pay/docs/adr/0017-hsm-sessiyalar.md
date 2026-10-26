# ADR-0017: PKCS#11 sessiyalar pool'i va uzilishdan tiklanish

* Holat: qabul qilingan (2026-10-26, 2-faza P2.2)

## Kontekst

`Pkcs11KeyStore` (ADR-0003) bitta R/W sessiyani `Mutex` ostida ishlatardi. Shu sababli ikki muammo bor edi:

1. **O'tkazuvchanlik.** Barcha HSM operatsiyalari ketma-ket bajarilardi: LUK hosil qilish (KDF/CMAC),
   ARQC tekshiruvi, PAN/DPAN envelope (GCM), PAN indeksi (HMAC), PQ Link handshake imzosi (Ed25519).
   Tarmoq HSM'ida har operatsiya round-trip, shuning uchun bitta sessiya SLA'ni (200 TPS, p99 < 300 ms)
   cheklaydi.
2. **Uzilishdan tiklanmaslik.** HSM qayta ishga tushsa, tarmoq uzilsa yoki sessiya muddati tugasa,
   `CKR_SESSION_HANDLE_INVALID` / `CKR_USER_NOT_LOGGED_IN` paydo bo'ladi. Shundan keyin har bir
   avtorizatsiya `91` qaytarardi va bu server qayta ishga tushirilguncha davom etardi.

## Qaror

1. **Sessiyalar pool'i.** `MPAY_PKCS11_SESSIONS` ta R/W sessiya ochiladi (1–64, standart 4), har biri
   o'z `Mutex` ida. Operatsiya bo'sh sessiyani oladi (`try_lock`, navbat bilan); hammasi band bo'lsa
   navbatdagisini kutadi. Sessiyalar kerak bo'lganda ochiladi. Birinchisi darhol ochiladi, shunda
   noto'g'ri PIN ishga tushishda aniqlanadi.
2. **Tiklanish.** Quyidagi xatolar "sessiya yo'qoldi" deb hisoblanadi:
   `SESSION_HANDLE_INVALID`, `SESSION_CLOSED`, `USER_NOT_LOGGED_IN`, `DEVICE_REMOVED`,
   `TOKEN_NOT_PRESENT`, `DEVICE_ERROR`. Bunday xatoda sessiya yopiladi, yangisi ochiladi
   (`C_OpenSession` + `C_Login`) va operatsiya **bir marta** takrorlanadi.
3. **Kalit handle'lari keshi.** `yorliq → (handle, turi)`. Token obyektlari handle'i ilovaning barcha
   sessiyalarida bir xil, shuning uchun har operatsiyada `C_FindObjects`/`C_GetAttributeValue`
   chaqirilmaydi. Kesh sessiya yo'qolganda va kalit yaratilganda tozalanadi.
   `KEY_HANDLE_INVALID`/`OBJECT_HANDLE_INVALID` ham "sessiya yo'qoldi" deb hisoblanadi.
4. **Login tushib qolishi.** Login tushganda yopiq kalitlar `C_FindObjects` da ko'rinmaydi va xato
   "kalit yo'q" bo'lib keladi. Shuning uchun kalit topilmaganda sessiya holati (`C_GetSessionInfo`)
   tekshiriladi. Aks holda `ensure_key` takroriy kalit yaratardi. Bu tekshiruv faqat shu kam
   uchraydigan yo'lda ishlaydi, oddiy operatsiyaga qo'shimcha chaqiruv qo'shilmaydi.

## Oqibatlar

* HSM qisqa uzilishi faqat uzilish paytidagi so'rovlarga ta'sir qiladi. Server qayta ishga tushirilmaydi.
* Takrorlash xavfsiz: barcha operatsiyalar idempotent (MAC, imzo, shifrlash). Kalit yaratishda esa
  avval mavjudligi tekshiriladi.
* SoftHSM'da (8 oqim, CMAC): keshsiz 1 264 op/s → kesh bilan 17 941 (1 sessiya) / 32 591 op/s
  (4 sessiya). Yuk sinovida HSM qo'shimcha xarajati −21% → −3%. Keshsiz pool SoftHSM'da sekinroq edi:
  u ichida ketma-ket ishlaydi.
* `TODO(spec):` pilot bankning HSM'i bo'yicha sessiyalar soni va uzilish xatolarining aniq ro'yxati.
  Tarmoq HSM'ida pool foydasini o'lchash.
* Tekshirilgan (SoftHSM2, Docker): `pkcs11_session_pool_parallel_ops` (8 oqim, 4 sessiya, natija bir
  xil) va `pkcs11_recovers_after_logout` (login tushdi → operatsiya muvaffaqiyatli, ikki marta).
  Yuk sinovi: `docs/load-report.md` §7.

## Ko'rib chiqilgan muqobillar

* **Har operatsiyaga yangi sessiya** — har safar `C_OpenSession` bilan round-trip, tarmoq HSM'ida
  qimmat.
* **Faqat watchdog bilan qayta ishga tushirish** — uzilishda barcha so'rovlar yiqiladi va jarayon
  qayta yuklanadi (PQ Link sessiyalari xotirada yo'qoladi).
