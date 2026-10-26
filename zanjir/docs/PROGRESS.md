# ZANJIR — PROGRESS

**Joriy holat:** Rejalashtirish — foydalanuvchi tasdig'i kutilmoqda (`docs/PROMPT.md` 11-bo'lim, 3-qadam).
**Oxirgi yangilanish:** 2026-10-26

## Fazalar

| # | Faza | Holat | Sana | Commit |
|---|---|---|---|---|
| — | Reja va boshlang'ich hujjatlar (`PROMPT.md`, `CLAUDE.md`, `PROGRESS.md`) | ✅ Tayyor, tasdiq kutilmoqda | 2026-10-26 | — |
| 0 | Skelet: monorepo, docs, CI | ⏳ Kutilmoqda | | |
| 1 | `zanjir_core`: modellar, normalar, `evaluate()` | ⏳ | | |
| 2 | Ajratish solveri | ⏳ | | |
| 3 | Kanonik JSON + hash-zanjir + imzo (Dart + Python) | ⏳ | | |
| 4 | Ilova ma'lumot qatlami (Drift) | ⏳ | | |
| 5 | Ilova UI, l10n uz/ru | ⏳ | | |
| 6 | Deterministik PDF, QR, imzolash | ⏳ | | |
| 7 | Server: auth, RBAC, RLS, sync, `/v/{qr_token}` | ⏳ | | |
| 8 | Sinxronlash integratsiyasi (E2E) | ⏳ | | |
| 9 | Ajratish rejasi UI, tasdiqlash, STALE | ⏳ | | |
| 10 | Mustahkamlash: xavfsizlik, audit, accessibility | ⏳ | | |
| 11 | Deploy (staging + prod) | ⏳ | | |
| 12 | Release (AAB, Play internal) | ⏳ | | |

## 🛑 Inson darvozalari

| # | Qachon | Nima kerak | Holat |
|---|---|---|---|
| R | Boshlashdan oldin | Reja va `zanjir_core` tuzilmasini tasdiqlash; quyidagi ochiq savollarga javob | ⏳ Kutilmoqda |
| 1 | 1-fazadan keyin | Litsenziyali muhandis `docs/NORMS_REVIEW.md` ni tekshirib imzolaydi | ⏳ |
| 2 | 11-fazadan oldin | Domen, O'zbekistondagi server (IP, SSH user), SMTP/SMS — faqat `.env` orqali | ⏳ |
| 3 | 12-fazadan oldin | Release keystore (foydalanuvchi yaratadi), Play Console yuklash | ⏳ |
| 4 | Pilotdan keyin | Fikr-mulohazalar asosida keyingi reja | ⏳ |

## Ochiq savollar

Elektr xavfsizligi / baholash semantikasi (1-faza shularga bog'liq):

- **S1. Oxirgi va taqsimlovchi zanjir** (LOOP-TN-FINAL vs LOOP-TN-DIST): tugun qaysi biri ekanini qanday aniqlaymiz? Taklif: `node.attrs.circuit_role: "final" | "distribution"` majburiy maydon; bo'lmasa → NEEDS_REVIEW.
- **S2. Sirtmoq formulasi va vaqt normasi:** 0,4 s / 5 s normasi `Zs_max = k_corr·U0/Ia` (Ia = 5/10/20·In — elektromagnit ajratgich zonasi) bilan tekshiriladi. Ya'ni Ia ni har doim "oniy" zona deb olamiz, 5 s uchun ham (konservativ). To'g'rimi? 5/10/20 koeffitsientlari ham YAML'ga (`trip_multipliers`) chiqariladi (4-qoida).
- **S3. Sirtmoq natijalari:** Zs ≤ Zs_max → PASS; Zs > Zs_max va yuqorida UZO yo'q → FAIL; yuqorida UZO bor → NEEDS_REVIEW. Shu to'g'rimi?
- **S4. UZO `tripped=false`:** 0,5·IΔn sinovida o'chmaslik — to'g'ri natija. Taklif: `multiplier < 1` uchun norma yo'q → NEEDS_REVIEW; `tripped=false → FAIL` faqat `multiplier ≥ 1` da. Rozimisiz?
- **S5. Selektiv UZO 5·IΔn** (va 2·IΔn) normalari jadvalda yo'q. `needs_verification` holatida `RCD-5X-S` (50–150 ms), `RCD-2X` (≤150 ms), `RCD-2X-S` (60–200 ms) qo'shaymi yoki bu multiplikatorlar NEEDS_REVIEW bo'lib qolsinmi?
- **S6. Yerga ulash normasini tanlash:** EARTH-NEUTRAL / EARTH-REPEAT / EARTH-TT qaysi biri qo'llanishi uchun `EARTH_ELECTRODE.attrs.role: "neutral" | "repeat" | "tt"` maydoni; EARTH-REPEAT uchun o'lchov "jami" yoki "alohida" ekanini `values.scope: "total" | "single"` bilan beramiz. Rozimisiz?
- **S7. EARTH-TT (Ra·Ia ≤ 50 V):** Ia — yuqoridagi UZO'ning IΔn (graf orqali), UZO bo'lmasa → NEEDS_REVIEW. Yangi qoida turi `max_product` (`min`/`max`/`range`/`max_time_ms` ga qo'shimcha). To'g'rimi?

Ish tartibi:

- **S8. Joylashuv:** ZANJIR Myrep monorepo ichida `zanjir/` papkasida, CI esa `.github/workflows/zanjir.yml` (faqat `zanjir/**` o'zgarganda). Alohida repo kerakmi?
- **S9. PR:** sessiya bitta branch'ga bog'langan (`claude/new-session-2w6wwo`). Har faza — alohida commit(lar) + PR tavsifi `docs/` da; GitHub PR'ni har fazada ochaymi yoki faqat siz so'raganda?
- **S10. Android `applicationId`** (masalan `uz.zanjir.app`) va ilova nomi — 4-fazagacha kerak.
