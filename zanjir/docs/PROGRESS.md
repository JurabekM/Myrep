# ZANJIR — PROGRESS

**Joriy holat:** 4-faza tayyor. 🛑 1-inson darvozasi (`docs/NORMS_REVIEW.md`) va S11–S14 hali ochiq. Keyingi — 5-faza (ilova UI, l10n).
**Oxirgi yangilanish:** 2026-10-26

## Fazalar

| # | Faza | Holat | Sana | Commit |
|---|---|---|---|---|
| — | Reja va boshlang'ich hujjatlar (`PROMPT.md`, `CLAUDE.md`, `PROGRESS.md`) | ✅ Tasdiqlangan | 2026-10-26 | e342364 |
| 0 | Skelet: monorepo, docs, CI | ✅ Tayyor | 2026-10-26 | d7fefe8 |
| 1 | `zanjir_core`: modellar, normalar, `evaluate()` | ✅ Tayyor (golden: 147, evaluator coverage 100% qator/branch) | 2026-10-26 | ba44045 |
| 2 | Ajratish solveri | ✅ Tayyor (7 stsenariy, 1000 tasodifiy graf brute force bilan, 2000 tugun ~22 ms) | 2026-10-26 | cd2b24d |
| 3 | Kanonik JSON + hash-zanjir + imzo (Dart + Python) | ✅ Tayyor (umumiy vektorlar, RFC 8785/8032, har bir bayt/bit buzilishi aniqlanadi) | 2026-10-26 | 63bf546 |
| 4 | Ilova ma'lumot qatlami (Drift) | ✅ Tayyor (`packages/zanjir_data`: migratsiya, repozitoriy, append-only, tashkilot testlari) | 2026-10-26 | c515956 |
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
| R | Boshlashdan oldin | Reja va `zanjir_core` tuzilmasini tasdiqlash; ochiq savollarga javob | ✅ 2026-10-26: barcha takliflar qabul qilindi |
| 1 | 1-fazadan keyin | Litsenziyali muhandis `docs/NORMS_REVIEW.md` ni tekshirib imzolaydi (M1–M10 savollarga javob) | 🛑 Kutilmoqda |
| 2 | 11-fazadan oldin | Domen, O'zbekistondagi server (IP, SSH user), SMTP/SMS — faqat `.env` orqali | ⏳ |
| 3 | 12-fazadan oldin | Release keystore (foydalanuvchi yaratadi), Play Console yuklash | ⏳ |
| 4 | Pilotdan keyin | Fikr-mulohazalar asosida keyingi reja | ⏳ |

## Ochiq savollar

S1–S10 hal qilindi (2026-10-26, foydalanuvchi: "barcha takliflarga roziman"):
- S1–S7 → ADR-0002 (baholash semantikasi). S5: 3 ta qo'shimcha UZO normasi `needs_verification` bilan qo'shildi.
- S8 → ADR-0001 (`zanjir/` papkasi). S9 → GitHub PR faqat foydalanuvchi so'raganda. S10 → `uz.zanjir.app`, «ZANJIR».

Solver bo'yicha (ADR-0006), hozircha konservativ:
- **S11.** Zona ichida manba (UPS, generator, PV, akkumulyator ustida ish) → reja tuzilmaydi (Blocked). Bunday ishlar uchun alohida oqim kerakmi?
- **S12.** Zonadagi har bir kabelga zaryadsizlantirish ogohlantirishi (uzunlik chegarasi yo'q). Chegara (masalan, laboratoriya sozlamasi) kerakmi?
- **S13.** Kirish nuqtasi — faqat manbaga ulangan tomon. Manbasiz pastki tomonlarda (iste'molchi) ham yerga ulash qadami kerakmi?
- **S14.** Kesimda ko'rinadigan uzilish (avtomat/kontaktor emas, ajratgich) talab qilinsinmi yoki ogohlantirish yetarlimi?

Muhandis uchun: M1–M10 (`docs/NORMS_REVIEW.md`). Ular hal bo'lguncha baholash konservativ (NEEDS_REVIEW yoki qat'iyroq chegara).

## Eslatmalar
- GitHub Actions bu branch uchun hali ishga tushmadi (workflow default branch'da yo'q) — lokal tekshiruvlar yashil; PR ochilganda CI ishlaydi.
- Noto Sans shrifti ilovaga 5-fazada qo'shiladi (hozir tizim shrifti).
- 5-fazada: ilovani `zanjir_data` ga ulash (Riverpod provayderlari, bazani ochish), laboratoriya sozlamalari (`k_corr`, `margin_pct`) saqlash.
- Release darvozasi `needs_verification` holatidagi normalarni ham yiqitadi (ADR-0004) — muhandis tekshiruvidan keyin holat `source_seen` ga o'zgartiriladi.
