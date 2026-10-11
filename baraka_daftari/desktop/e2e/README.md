# Windows E2E (tauri-driver)

**Holat: yozilgan, lekin hali ishga tushirilmagan.** Bu sessiya Linux konteynerda ishladi (Windows va WebView2 yo'q).
Qabul mezoni «E2E yashil» faqat Windows mashinada shu spetsifikatsiya yashil bo'lgandan keyin bajarilgan hisoblanadi.

## Tayyorgarlik (Windows)
1. `cargo install tauri-driver --locked`
2. Microsoft Edge WebDriver (`msedgedriver.exe`), o'rnatilgan Edge/WebView2 versiyasiga mos, `PATH` da.
3. Reliz build: `cd desktop && cargo tauri build --no-bundle` (yoki `cargo build --release -p baraka-desktop` + `pnpm --dir ui build`).
4. `cd desktop/e2e && pnpm install && pnpm test`.

## Qamrov
- `specs/anvar.e2e.ts`: PIN o'rnatish → onboarding → `Ctrl+N` daromad → bo'limlar → disklеymer → `Ctrl+L` qulf.
- Pul hisobi va to'liq «Anvar» zanjiri (audit → havas → obuna → qarz → 70/20/10 → payoff → darvoza → sheriklik → taqsimot → eksport):
  `crates/services/tests/anvar.rs` (har `cargo test --workspace` da ishlaydi).
- OS fayl dialoglari (PDF/.baraka saqlash) WebDriver bilan boshqarilmaydi — qo'lda tekshiriladi (RELEASE_CHECKLIST).
