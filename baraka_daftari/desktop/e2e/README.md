# Windows E2E (tauri-driver)

**Holat: yozilgan, lekin hali ishga tushirilmagan.** Bu sessiyalar Linux konteynerda ishladi (Windows va WebView2 yo'q).
Qabul mezoni «E2E yashil» faqat Windows mashinada shu spetsifikatsiyalar yashil bo'lgandan keyin bajarilgan hisoblanadi.

## Tayyorgarlik (Windows)
1. `cargo install tauri-driver --locked`
2. Microsoft Edge WebDriver (`msedgedriver.exe`), o'rnatilgan Edge/WebView2 versiyasiga mos, `PATH` da.
3. Reliz build: `cd desktop && cargo tauri build --no-bundle` (yoki `cargo build --release -p baraka-desktop` + `pnpm --dir ui build`).
4. `cd desktop/e2e && pnpm install && pnpm test`.

## Qamrov
- `specs/anvar.e2e.ts`: PIN o'rnatish → onboarding → `Ctrl+N` daromad → bo'limlar → disklеymer → `Ctrl+L` qulf.
- `specs/musharaka.e2e.ts` (D15): Anvar × Dilshod — shartnoma ustasi (progress, önizleme), tomonlar tasdig'i,
  faollashtirish, vazifa hodisasi, oylik ko'rik va bayonnoma, «katta foyda» tasdig'i bilan davrni yopish, eksport.
- Pul hisobi va to'liq «Anvar» zanjiri: `crates/services/tests/anvar.rs` (har `cargo test --workspace` da ishlaydi).
  Kelishuv, jurnal, ko'rik va import zanjiri: `crates/services/tests/ventures.rs`, `interchange.rs`, `agreements.rs`.
- OS fayl dialoglari (PDF/.baraka saqlash) WebDriver bilan boshqarilmaydi — qo'lda tekshiriladi (RELEASE_CHECKLIST).
