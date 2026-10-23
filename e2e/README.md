# Yakuniy E2E (Windows, `tauri-driver`)

DESKTOP_PROMPT.md D15: Oila ssenariysi boshidan oxirigacha haqiqiy o'rnatilgan ilovada. Bu papka ssenariy
skriptini (`asosiy.e2e.ts`) va ishga tushirish tartibini beradi. **Hozircha CI'da ishlamaydi** — `tauri-driver`
va Edge WebDriver mahalliy mashinada o'rnatilishi kerak.

## Tayyorgarlik

1. `cargo install tauri-driver --locked`
2. Microsoft Edge WebDriver (WebView2 versiyasiga mos): https://developer.microsoft.com/microsoft-edge/tools/webdriver/
   — `msedgedriver.exe` PATH'da bo'lsin.
3. Ilovani yig'ing: `pnpm build` (NSIS) yoki `cargo build --release` — `baraka-dastur.exe` yo'li `wdio.conf.ts`
   dagi `application` maydoniga yoziladi.
4. Toza profil: `%APPDATA%\uz.barakadaftari.desktop` papkasini zaxiralab bo'shating (ssenariy PIN o'rnatishdan boshlanadi).
5. `pnpm add -D @wdio/cli @wdio/local-runner @wdio/mocha-framework @wdio/spec-reporter` (faqat shu papkada,
   ADR 2-bo'limga qo'shimcha dev-dependency — CHANGELOG'da sabab) va `npx wdio run e2e/wdio.conf.ts`.

## Ssenariy (asosiy.e2e.ts)

1. PIN o'rnatish → bosh sahifa (onboarding 5 qadam o'tkazib yuboriladi).
2. Daromad 3 000 000 → «Kelajagim» ulushi.
3. Xarajatlar → oy auditi → havas chegarasi (rozilik PIN bilan).
4. Byudjet → obuna qo'shish → bekor qilish.
5. Qarzlar → qarz olish (to'xta va o'yla) → 70/20/10 → payoff rejalashtiruvchisi → to'lovlar → qarz yopilishi.
6. Kelajagim → zaxira 6 oyga yetadi → darvoza ochiladi (Sheriklik kartasida «darvoza ochiq»).
7. Sheriklik → Jasur bilan musharaka: 9/9 savol, imzolar (canvas) → SIGNED.
8. Kelishuv ustasi → vazifa hodisasi → oylik ko'rik sessiyasi → bayonnoma PDF.
9. Kassa daftari → kirim/xarajat → davrni yopish → taqsimot (1 400 000 Jasurga).
10. Sozlamalar → `.baraka` eksport → fayl mavjud.

Har qadam `expect` bilan tekshiriladi; summalar matn sifatida (`soʻm`), hisob Rustda.

## Sovuq start

`Measure-Command { Start-Process "...\baraka-dastur.exe" -Wait:$false; while (-not (Get-Process baraka-daftari -ErrorAction SilentlyContinue).MainWindowHandle) { Start-Sleep -Milliseconds 50 } }`
— maqsad < 1,5 s (release build, SSD). Natija `docs/RELEASE_CHECKLIST.md` ga yoziladi.
