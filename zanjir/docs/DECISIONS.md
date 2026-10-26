# ZANJIR — Arxitektura qarorlari (ADR)

Format: kontekst → qaror → oqibat. Qabul qilingan ADR o'zgartirilmaydi; o'rniga yangi ADR yoziladi.

---

## ADR-0001: Myrep monorepo ichida `zanjir/` papkasi

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (foydalanuvchi, S8)
- **Kontekst:** Prompt bo'sh repozitoriyni nazarda tutadi, lekin foydalanuvchining loyihalari `Myrep` monorepo'sida yashaydi.
- **Qaror:** Barcha ZANJIR fayllari `zanjir/` ostida; promptdagi yo'llar (`app/`, `server/`, …) `zanjir/` ga nisbatan. CI — `.github/workflows/zanjir.yml`, faqat `zanjir/**` o'zgarganda ishlaydi. Release teglari: `zanjir-v*`.
- **Oqibat:** Boshqa loyihalar CI'si ZANJIR'ga ta'sir qilmaydi. Keyinchalik alohida repoga ko'chirish `git subtree split` bilan mumkin.

## ADR-0002: Baholash semantikasini aniqlashtirish (S1–S7)

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (foydalanuvchi tasdig'i). Normalar muhandis tekshiruvigacha `needs_verification`.
- **Kontekst:** Promptdagi baholash qoidalarida bir nechta noaniqlik bor edi (6-bo'lim, 10-qoida).
- **Qaror:**
  1. **S1.** Sirtmoq uchun `node.attrs.circuit_role: final | distribution` (tugunda yoki yuqoridagi apparatda). Yo'q bo'lsa → NEEDS_REVIEW.
  2. **S2.** Zs_max uchun Ia har doim elektromagnit ajratgich zonasi: `Ia = trip_multiplier[curve] · In`. Koeffitsientlar (B=5, C=10, D=20) `norms/*.yaml` da (`trip_multipliers`), kodda emas. 5 s normasi uchun ham shu (konservativ).
  3. **S3.** Zs ≤ Zs_max → PASS; Zs > Zs_max va yuqorida UZO/RCBO yo'q → FAIL; bor → NEEDS_REVIEW.
  4. **S4.** UZO: `multiplier < 1` → norma yo'q → NEEDS_REVIEW. `tripped = false` → FAIL faqat `multiplier ≥ 1` da.
  5. **S5.** Qo'shimcha normalar `needs_verification` bilan: `RCD-2X` (≤ 150 ms), `RCD-2X-S` (60–200 ms), `RCD-5X-S` (50–150 ms), manba — ГОСТ IEC 61008-1.
  6. **S6.** `EARTH_ELECTRODE.attrs.role: neutral | repeat | tt`; EARTH-REPEAT uchun `values.scope: total | single` (jami ≤ 10 Ω, alohida ≤ 30 Ω). Yo'q bo'lsa → NEEDS_REVIEW.
  7. **S7.** EARTH-TT: `Ra · Ia ≤ 50 V`, Ia = yuqoridagi UZO'ning IΔn (graf orqali); UZO topilmasa → NEEDS_REVIEW. Yangi qoida turi `max_product`.
- **Oqibat:** `norms/schema.json` `min | max | range | max_time_ms | max_product` qoidalarini va `trip_multipliers` blokini qo'llab-quvvatlaydi. Tugun atributlari UI'da majburiy maydon sifatida ko'rsatiladi.

## ADR-0003: Asboblar versiyalari

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan
- **Kontekst:** Takrorlanadigan build'lar kerak (lokal ↔ CI).
- **Qaror:** Flutter 3.47.8 (stable, Dart 3.13.7) — CI'da `subosito/flutter-action` bilan aynan shu versiya; `zanjir_core` ham shu Dart bilan tekshiriladi. Python 3.12, bog'liqliklar `uv` bilan (`server/uv.lock`, `tools/norms/uv.lock`).
- **Oqibat:** Flutter yangilanishi — alohida commit va CHANGELOG yozuvi.

## ADR-0004: Normalarni tekshirish va release darvozasi

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan
- **Kontekst:** Normalar JSON Schema bo'yicha tekshirilishi va tekshirilmagan normalar bilan release chiqmasligi kerak (prompt 5.1).
- **Qaror:** `tools/norms/check_norms.py` — schema validatsiyasi, ID takrorlanmasligi, `--release` rejimida `reviewed_by` / `reviewed_at` bo'shligi va `needs_verification` normalar uchun xato. CI'da har push'da oddiy rejim, `zanjir-v*` teglarida `--release`. Ilova ichida `zanjir_core` normalarni yuklashda ham tekshiradi (ikkinchi himoya qatlami).
- **Oqibat:** Muhandis imzosisiz release build'i yiqiladi; Claude `reviewed_by` ni hech qachon to'ldirmaydi.
