# ADR-0014: Bekor qilingan server identifikatorlari — oflayn ildiz imzosi

* Holat: qabul qilingan (2026-10-25, 1-faza qo'shimcha)

## Kontekst

Kalit almashtirish (ADR-0012) joriy kalit ishonchli bo'lgandagina xavfsiz: joriy kalit **oshkor
bo'lsa**, hujumchi u bilan o'z "keyingi" kalitini tasdiqlay oladi va qurilmalar uni o'rganadi. Server
o'zi imzolagan bekor qilish xabari ham yordam bermaydi — hujumchi aynan o'sha kalitga ega.

## Qaror

1. **Oflayn ildiz kaliti** (Ed25519 + ML-DSA-65): `mpay-server root-keygen` imzolash stansiyasida
   yaratadi; serverga qo'yilmaydi. Ilovaga faqat ildiz barmoq izi joylanadi (`-Pmpay.rootFingerprint`).
2. **Ro'yxat:** `mpay-server revoke --root-key … --version N --fp …` imzolaydi. Kanonik xabar:
   `"MPAY-PQLINK-V1 revocations" ‖ version (u64 BE) ‖ count (u32 BE) ‖ fp…` (tartiblangan, takrorsiz),
   ML-DSA konteksti `mpay-pqlink-v1` — handshake va rotation yorliqlaridan ajratilgan.
3. **Tarqatish:** server `[pqlink] revocations` faylini `GET /v1/pqlink/revocations` da beradi (o'zi
   imzolay olmaydi). `root_fingerprint` berilsa — imzo ishga tushishda tekshiriladi; joriy yoki keyingi
   identifikatori ro'yxatda bo'lsa server **ishga tushmaydi**.
4. **Qurilma:** ildiz pinlangan bo'lsa ro'yxatni oladi, ildiz barmoq izi va gibrid imzoni tekshiradi,
   faqat **kattaroq versiyani** saqlaydi (orqaga qaytarib bo'lmaydi). Bekor qilingan barmoq izi pinlangan,
   o'rganilgan yoki TOFU bo'lsa ham rad etiladi; rotation ham uni qo'shmaydi.

## Oqibatlar

* Oshkor bo'lgan kalitni ilova yangilanishisiz o'chirish mumkin — qurilma haqiqiy serverdan (yoki
  boshqa kanaldan) yangi ro'yxatni bir marta olsa bas.
* Cheklov: hali yangi ro'yxatni olmagan qurilma hujumchi serveriga ulanishi mumkin (hujumchi ro'yxatni
  bermaydi). `TODO(spec):` ro'yxatni ilova build'iga ham joylash va boshqa kanal (CDN/push) orqali tarqatish.
* Ildiz kaliti — eng qimmatli sir: oflayn saqlash, zaxira va kalit marosimi (2-faza deployment).
* Tekshirilgan: Rust unit (imzo, buzish, begona ildiz), e2e `p1_revocations.rs` (tarqatish, server o'z
  bekor qilingan kaliti bilan ishga tushmaydi, noto'g'ri imzo), Kotlin `RevocationsTest`, interop
  (Rust `revoke` → Kotlin tekshiradi).

## Ko'rib chiqilgan muqobillar

* **Server imzolagan bekor qilish** — oshkor bo'lgan kalit holatida foydasiz.
* **Faqat ilova yangilanishi** — sekin; barcha foydalanuvchilar yangilanguncha himoya yo'q.
* **To'liq X.509 PKI** — PQ sertifikat profillari hali standartlashmagan (ADR-0012 bilan bir xil sabab).
