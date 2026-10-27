# ZANJIR — PROGRESS

**Joriy holat:** 8-faza tayyor. 🛑 1-inson darvozasi (`docs/NORMS_REVIEW.md`) va S11–S14 hali ochiq — 1-darvoza yopilmaguncha
protokol imzolash bloklangan (ilovada ham, serverda ham). Keyingi — 9-faza (ajratish rejasi UI, tasdiqlash, STALE).
**Oxirgi yangilanish:** 2026-10-27

## Fazalar

| # | Faza | Holat | Sana | Commit |
|---|---|---|---|---|
| — | Reja va boshlang'ich hujjatlar (`PROMPT.md`, `CLAUDE.md`, `PROGRESS.md`) | ✅ Tasdiqlangan | 2026-10-26 | e342364 |
| 0 | Skelet: monorepo, docs, CI | ✅ Tayyor | 2026-10-26 | d7fefe8 |
| 1 | `zanjir_core`: modellar, normalar, `evaluate()` | ✅ Tayyor (golden: 147, evaluator coverage 100% qator/branch) | 2026-10-26 | ba44045 |
| 2 | Ajratish solveri | ✅ Tayyor (7 stsenariy, 1000 tasodifiy graf brute force bilan, 2000 tugun ~22 ms) | 2026-10-26 | cd2b24d |
| 3 | Kanonik JSON + hash-zanjir + imzo (Dart + Python) | ✅ Tayyor (umumiy vektorlar, RFC 8785/8032, har bir bayt/bit buzilishi aniqlanadi) | 2026-10-26 | 63bf546 |
| 4 | Ilova ma'lumot qatlami (Drift) | ✅ Tayyor (`packages/zanjir_data`: migratsiya, repozitoriy, append-only, tashkilot testlari) | 2026-10-26 | c515956 |
| 5 | Ilova UI, l10n uz/ru | ✅ Tayyor (19 widget/oqim testi; emulyator jobi qo'shildi, lokal tekshirilmagan) | 2026-10-26 | 35727eb |
| 6 | Deterministik PDF, QR, imzolash | ✅ Tayyor (baytma-bayt bir xil PDF, 12 ta bloklash sharti testlangan, sxema v3) | 2026-10-27 | 9c7738b |
| 7 | Server: auth, RBAC, RLS, sync, `/v/{qr_token}` | ✅ Tayyor (194 pytest, testcontainers PG16, RBAC 22 endpoint × 5 rol, qamrov 97%) | 2026-10-27 | be7544a |
| 8 | Sinxronlash integratsiyasi (E2E) | ✅ Tayyor (E2E 6 stsenariy: Dart ↔ FastAPI + PostgreSQL; ilova 30, data 74 test) | 2026-10-27 | 7793f63 |
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
- Android build (`flutter build apk/appbundle`) va emulyator integration testi bu konteynerda tekshirilmagan — Android SDK yo'q; 12-fazagacha CI'da tekshiriladi.
- QR kodni kamera bilan skanerlash hali yo'q (kod qo'lda kiritiladi, deep link ishlaydi) — keyingi fazalarda.
- Protokol QR havolasi hozircha `zanjir://app/v/<token>` (faqat ilova o'rnatilgan telefonda ochiladi); ochiq tekshirish sahifasi
  `https://<domen>/v/<token>` — 7-faza (server) va 2-darvoza (domen), build'da `--dart-define=ZANJIR_VERIFY_BASE_URL`.
- `printing` (ulashish/chop etish) va FLAG_SECURE Android'da tekshirilmagan (SDK yo'q).
- Ilova serverga `--dart-define=ZANJIR_SERVER_URL=...` bilan ulanadi (domen — 2-darvoza); usiz faqat oflayn.
- Server testlari Docker talab qiladi: bu konteynerda `dockerd` qo'lda ishga tushirildi, image ECR ko'zgusidan
  (Docker Hub 429). Ilova ↔ server haqiqiy sinxronlash — 8-faza.
- Release darvozasi `needs_verification` holatidagi normalarni ham yiqitadi (ADR-0004) — muhandis tekshiruvidan keyin holat `source_seen` ga o'zgartiriladi.
