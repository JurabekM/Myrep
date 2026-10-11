# Kod imzolash va avtomatik yangilash (Windows)

> **Holat (halol):** bu sessiyada sertifikat, imzolash kaliti va yangilash serveri **yo'q**. Quyida tayyor shablon va
> qadamlar bor; ularsiz **imzolangan installer va imzolangan updater manifesti yaratilmagan**. «SmartScreen
> ogohlantirishisiz o'rnatiladi» mezoni sertifikat olingach tekshiriladi (RELEASE_CHECKLIST).

## 1. Kod imzolash (Authenticode)
- Sertifikat: OV yoki EV (EV SmartScreen obro'sini darhol beradi; OV — vaqt o'tib). Hal qilinishi kerak (DESKTOP_PROMPT 12).
- Kalit saqlash: sertifikat/PFX repoga **kiritilmaydi**; CI maxfiy omborida yoki HSM/bulut imzolash (masalan, Azure Trusted Signing) orqali.
- Sozlash: `src-tauri/tauri.release.conf.template.json` → `tauri.release.conf.json` (`certificateThumbprint`, `timestampUrl`); bulut imzolashda `bundle.windows.signCommand`.
- Build: `cargo tauri build --config src-tauri/tauri.release.conf.json` (NSIS installer, `installMode: currentUser` — administratorsiz).
- Tekshiruv: `signtool verify /pa /v Baraka*.exe`; toza Windows 11 da SmartScreen/Defender sinovi.

## 2. Imzolangan yangilash manifesti (Tauri updater)
Updater kodda **hali ulanmagan** (kalitsiz foydasiz va ishlamaydigan sozlama xavfli). Kalitlar tayyor bo'lgach:
1. Kalit juftligi: `cargo tauri signer generate -w ~/.tauri/baraka.key` — **maxfiy kalit** (parol bilan) CI maxfiy omboriga; **ochiq kalit** shablondagi `pubkey` ga.
2. `Cargo.toml` ga `tauri-plugin-updater` (sabab: rasmiy Tauri 2 updater, imzoni ochiq kalit bilan tekshiradi), `lib.rs` da `.plugin(tauri_plugin_updater::Builder::new().build())`.
3. Capability (`capabilities/main.json`) ga aniq ruxsat: `"updater:default"`. CSP `connect-src` ga yangilash hosti qo'shiladi (hozir faqat `'self'` va IPC — ADR: tarmoq chaqiruvlari yo'q).
4. Build muhitida: `TAURI_SIGNING_PRIVATE_KEY`, `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. Build `*.nsis.zip` va `*.sig` yaratadi.
5. `latest.json` (HTTPS serverda):
   ```json
   {
     "version": "0.2.0",
     "notes": "…",
     "pub_date": "2026-11-01T00:00:00Z",
     "platforms": {
       "windows-x86_64": { "signature": "<.sig fayl mazmuni>", "url": "https://<HOST>/baraka-daftari/Baraka_0.2.0_x64-setup.nsis.zip" }
     }
   }
   ```
6. UI: «Yangilanish bor» xabari foydalanuvchi roziligi bilan; **avtomatik o'rnatish yo'q**; ma'lumotlar bazasi migratsiyasi yangilashdan keyin birinchi ochilishda (zaxira nusxa oldindan: `.baraka` eksport tavsiya etiladi).
7. Maxfiylik: yangilanish so'rovi faqat versiya raqamini yuboradi; foydalanuvchi/moliyaviy ma'lumot yo'q.

## 3. Reliz qoidalari
- Versiya: `tauri.conf.json` va `Cargo.toml` bir xil; `docs/CHANGELOG.md` yangilangan.
- Maxfiy kalit yo'qolsa mavjud o'rnatmalar yangilanmaydi — kalitni zaxiralash tartibi alohida hujjatlanadi.
