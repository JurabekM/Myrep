# Baraka Daftari Desktop — AI-dasturchi uchun yo'riqnoma

Har sessiya boshida quyidagilarni o'qi:

- `docs/SPEC.md` — 3, 4, 5, 6 va 12-bo'limlar (mahsulot cheklovlari, texnik qarorlar, arxitektura,
  xavfsizlik, qoidalar). Eslatma: SPEC 4-bo'lim mobil (Flutter) uchun ADR; desktop uchun texnik qaror
  `docs/DESKTOP_PROMPT.md` 2-bo'lim.
- `docs/DESKTOP_PROMPT.md` — 2–6, 8 va 10-bo'lim (stek, arxitektura, pul modeli, test vektorlari,
  mahsulot cheklovlari, AI qoidalari). 9-bo'lim — ish rejasi: faqat berilgan vazifa ustida ishlang.
- `docs/MVP_PLAN.md` — faqat 0-bo'lim va 6-qonun. Bu mobil (Flutter) reja; desktop uchun umumiy qoidalar
  shu yerda.

## Qat'iy qoidalar

- **2-bo'lim (ADR) ruxsatsiz o'zgarmaydi.** Yangi crate yoki npm paket qo'shishdan oldin sababini
  `docs/CHANGELOG.md` ga yozing.
- **Bitta sessiya — bitta vazifa.** Keyingi vazifaning funksiyasini «qo'shimcha» sifatida yozmang.
- **Pul hisobi faqat Rust'da** (`money`/`domain` crate'lari). Frontend pul hisoblamaydi, faqat ko'rsatadi.
  Yangi pul funksiyasi avval test vektori bilan yoziladi (DESKTOP_PROMPT.md 5-bo'lim).
- **`unwrap()` / `expect()` / `panic!` production kodda yo'q** (testlarda ruxsat). `f32`/`f64` pul uchun taqiq.
- Har yangi command uchun `build.rs` dagi ro'yxatga va `src-tauri/capabilities/default.json` ga aniq ruxsat qo'shing.
- Frontend'da `invoke('...')` qo'lda yozilmaydi — faqat `ui/src/bindings/bindings.ts` dagi `commands`.
- Kod va identifikatorlar inglizcha; izohlar, hujjatlar va UI matnlari o'zbekcha (lotin).
- Loglarda summa, ism yoki izoh bo'lmaydi.
- Noaniq joyda taxmin qilmasdan so'rang. Javobsiz savollarni `docs/OPEN_QUESTIONS.md` ga yozing.
- Har vazifa oxirida `docs/CHANGELOG.md` ni yangilang.

## Dizayn

- Qorong'i tema (Claude Code desktop uslubi). Ranglar faqat `ui/src/styles/globals.css` dagi tokenlarda.
- Ikonkalarda odam, hayvon, qush, cho'chqa (piggy bank), qimor, alkogol, bank binosi, foiz belgisi
  va qo'l tasviri ISHLATILMAYDI — `ui/src/app/icon-policy.test.ts` shuni tekshiradi.
- Har GUI o'zgarishidan keyin ilovani haqiqatan ishga tushirib, ekranni ko'rib chiqing. Testlar o'tishi
  «ko'rinishi to'g'ri» degani emas. Har bir tugma bosilib sinalsin: ishlamaydigan tugma qoldirilmasin.

## Buyruqlar

```bash
pnpm dev                       # ishlab chiqish rejimi
pnpm test                      # frontend testlari
pnpm lint && pnpm typecheck    # frontend tekshiruvi
cargo test --workspace         # Rust testlari (bindinglarni ham yangilaydi)
cargo clippy --workspace --all-targets -- -D warnings
pnpm build                     # Windows o'rnatish fayli (NSIS)
```

Windows'da `cargo` yo'llari uzun bo'lsa, `CARGO_TARGET_DIR` ni qisqa yo'lga qo'ying (README.md).
