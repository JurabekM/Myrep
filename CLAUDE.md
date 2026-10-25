# CLAUDE.md — Myrep (barcha loyihalar uchun umumiy xotira)

Bu fayl Myrep ichidagi **barcha** loyihalarga tegishli. Loyiha papkasidagi o'z `CLAUDE.md` si bo'lsa, ikkalasi ham amal qiladi.

## Foydalanuvchi afzalliklari
- Muloqot tili: o'zbekcha (lotin). Kod, identifikatorlar, commit xabarlari — inglizcha; izohlar, hujjatlar va UI matnlari — o'zbekcha.
- Yo'nalish: vibe coding va mikrokontroller elektronikasi.
- Har PR ochilgach Claude o'zi code review qiladi (Codex o'rniga, foydalanuvchi qarori 2026-10-25): haqiqiy xatolar shu PR'da tuzatiladi, qolganlari foydalanuvchiga aytiladi.

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
