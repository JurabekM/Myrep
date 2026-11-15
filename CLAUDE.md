# CLAUDE.md — Myrep (barcha loyihalar uchun umumiy xotira)

Bu fayl Myrep ichidagi **barcha** loyihalarga tegishli. Loyiha papkasidagi o'z `CLAUDE.md` si bo'lsa, ikkalasi ham amal qiladi.

## Foydalanuvchi afzalliklari
- Muloqot tili: o'zbekcha (lotin). Kod, identifikatorlar, commit xabarlari — inglizcha; izohlar, hujjatlar va UI matnlari — o'zbekcha.
- Yo'nalish: vibe coding va mikrokontroller elektronikasi.
- Har PR ochilgach Claude o'zi code review qiladi: haqiqiy xatolar shu PR'da tuzatiladi, qolganlari foydalanuvchiga aytiladi.

## Topshirishdan oldin to'liq sinov — QAT'IY QOIDA (foydalanuvchi qarori, 2026-11-15)
Har bir loyiha (yoki reliz) "tayyor" deyilishidan oldin **maqsadli muhitning o'zida** to'liq sinaladi:
emulyator, virtual mashina yoki haqiqiy qurilma/OS — sessiya lokal yoki bulutda ekanidan qat'i nazar.
- Faqat unit testlar va boshqa OS'dagi sinov yetarli emas: dastur foydalanuvchi ishlatadigan yo'l bilan
  (o'rnatish → ishga tushirish → asosiy vazifa → chiqish) oxirigacha yuritib ko'riladi.
  Android — emulyatorda; Windows exe — Windows'da haqiqiy drayver/xizmatlar bilan; proshivka — simulyator yoki platada.
- Maqsadli muhit qo'l ostida bo'lmasa, uni topish ishning bir qismi (CI runner, emulyator, VM, o'rnini bosuvchi
  drayver). "Sinalmagan" deb yozib topshirish mumkin emas: yo'l topilmasa, topshirishdan **oldin** to'xtab,
  foydalanuvchidan muhit yoki ruxsat so'raladi.
- Hisobotda nima, qayerda va qanday sinalgani aniq yoziladi.
- Sabab: NetMonitor 4.0.0 Windows'da Npcap bilan jonli ushlash sinalmasdan topshirildi; nosozlik gumoni
  paydo bo'lganda uni tasdiqlaydigan ham, rad etadigan ham sinov yo'q edi.

## Codex ishlatilmaydi — QAT'IY QOIDA (foydalanuvchi qarori, 2026-10-25, 2026-10-27 da kuchaytirildi)
Bu repoda Codex (OpenAI Codex, `chatgpt-codex-connector[bot]` va boshqa OpenAI agentlari) **umuman kerak emas**.
Barcha ishni — kod, code review, CI tuzatish, hujjat — **Claude o'zi bajaradi**.
- Hech qachon `@codex`, `@codex review`, `@codex security review` yozmang; Codex'ga vazifa bermang, uni taklif qilmang.
- Codex natijasini kutmang va unga tayanmang: PR tayyorligi faqat CI, Claude'ning o'z review'i va foydalanuvchi qaroriga bog'liq.
- Codex bot izohlari (review summary, "usage limits", "couldn't complete this review" va h.k.) e'tiborsiz qoldiriladi:
  javob yozilmaydi, ular asosida ish qilinmaydi va foydalanuvchiga alohida xabar qilinmaydi.
- Codex review qiladigan joyda (PR ochilganda) Claude o'zi review qiladi — bu qoida yuqoridagi self-review bandini almashtirmaydi, uni majburiy qiladi.

## UI dizayn qoidasi (foydalanuvchi qarori, 2026-10-15) — har bir yangi ilova uchun
Barcha ilovalar (desktop, mobil, web, dashboard) **standart holda Claude Code dark theme uslubida** bo'ladi.
Light mavzu faqat ixtiyoriy variant sifatida qo'shiladi; standart doim dark.

| Token | Rang | Ishlatilishi |
|---|---|---|
| `paper` (fon) | `#262624` | asosiy ish maydoni |
| `sidebar` | `#1F1E1D` | yon panellar, navigatsiya |
| `surface` | `#30302E` | kartalar, maydonlar, dialoglar |
| `line` | `#4A4945` | chegaralar |
| `ink` | `#FAF9F5` | asosiy matn |
| `inkMuted` | `#A6A39A` | ikkinchi darajali matn |
| `accent` | `#D97757` | asosiy tugma foni, katta KPI raqamlari, fokus halqasi |
| `accentInk` | `#1F1E1D` | `accent` ustidagi matn (oq emas: oq 3.1:1, AA dan o'tmaydi) |
| `accentText` | `#E8957A` | kichik sarg'ish matnlar (≥ 4.5:1) |
| `warn` / `danger` | `#E0A458` / `#E5786D` | ogohlantirish / xato |

- Kontrast WCAG AA dan past bo'lmasin (matn ≥ 4.5:1, katta matn ≥ 3:1). Yangi rang qo'shsangiz, kontrastni hisoblang.
- Dialog overlay: `bg-black/60`. Oyna oq bo'lib "chaqnamasligi" uchun HTML/oyna fonini darhol `#262624` qiling (`color-scheme: dark`; Tauri: `theme: "Dark"`, `backgroundColor`).
- Shriftlar ilova ichida (`Noto Sans`); Anthropic'ning brend shriftlari va logotiplari ishlatilmaydi — faqat rang uslubi.
- Namuna: `baraka_oilasi/shared/design-tokens/tokens.json` (`defaultTheme: "dark"`) va `cargo xtask tokens`.
