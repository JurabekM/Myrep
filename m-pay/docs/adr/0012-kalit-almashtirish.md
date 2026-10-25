# ADR-0012: PQ Link server kalitini almashtirish (rotation)

* Holat: qabul qilingan (2026-10-24, 1-faza P1.6)

## Kontekst

Qurilmalar PQ Link server identifikatorini (Ed25519 + ML-DSA-65 ochiq kalitlari, barmoq izi
`SHA-256(ed25519 ‖ mldsa65)`) pinlaydi (P1.5). Kalit muddati tugasa, HSM almashtirilsa yoki kalit
oshkor bo'lishidan xavotir bo'lsa, server yangi identifikatorga o'tishi kerak — barcha ilovalarni
qayta chiqarmasdan va qurilmalarni uzib qo'ymasdan.

## Qaror

1. **E'lon:** `mpay-server identity-next --version N` yangi Ed25519 kalitini KeyStore'da
   (`mpay.srv-ed25519.vN`) va KEK bilan o'ralgan ML-DSA-65 blob'ini (`pqlink-mldsa65.vN.blob`)
   yaratadi. Operator `[pqlink.next]` ni yoqadi.
2. **Tasdiq (endorsement):** server ishga tushganda joriy identifikator keyingisining barmoq izini
   gibrid imzolaydi: `ROTATION_LABEL ‖ next_fp`, `ROTATION_LABEL = "MPAY-PQLINK-V1 identity-rotation"`
   (handshake yorlig'idan farqli — domen ajratish), ML-DSA konteksti `mpay-pqlink-v1`.
   `GET /v1/pqlink/identity` javobida `next` (kalitlar, barmoq izi, ikki imzo).
3. **Qurilma (roll-forward):** joriy identifikator pin bo'yicha qabul qilingandan keyingina, tasdiqi
   to'g'ri bo'lgan keyingi barmoq izi o'rganilgan pinlarga qo'shiladi (`ServerPinPolicy.rollForward`).
4. **O'tish:** e'londan keyin yetarli vaqt o'tgach (faol qurilmalar ulanib bo'lgach) `[pqlink]`
   `mldsa_blob`/`ed25519_label` yangilariga almashtiriladi, `[pqlink.next]` o'chiriladi.
   Eski pinli, o'rganmagan qurilmalar rad etiladi — ular uchun ilova yangilanishi (yangi build pini).

## Oqibatlar

* Pin to'plami (P1.5) bir nechta identifikatorni qabul qiladi; build pinlariga ham joriy + keyingi
  qo'yish mumkin.
* Tasdiq faqat joriy kalitlar ishonchli bo'lsa ma'noli: joriy kalit **oshkor bo'lgan** holatda hujumchi
  o'z "keyingi" kalitini tasdiqlashi mumkin — bunday holatda roll-forward emas, ilova yangilanishi
  (build pinlarini almashtirish) kerak — yoki oflayn ildiz imzolagan bekor qilish ro'yxati (ADR-0014).
* Tekshirilgan: Rust e2e (`p1_rotation.rs` — e'lon, tasdiq, soxta barmoq izi rad, o'tish, eski pin rad),
  Kotlin `RotationTest`, tillararo interop (Rust `identity-next` → Kotlin tasdiqni tekshiradi).

## Ko'rib chiqilgan muqobillar

* **Faqat ilova yangilanishi** — har almashtirishda barcha qurilmalar majburan yangilanadi.
* **X.509 PKI (CA zanjiri)** — qurilmaga CA pinlanadi; PQ (ML-DSA) sertifikat profillari hali
  standartlashib ulgurmagan, gibrid zanjir murakkab. 2-fazada bank PKI'si bilan qayta ko'riladi.
