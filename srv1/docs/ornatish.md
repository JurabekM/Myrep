# O'rnatish va Windows xizmati (texnik tafsilot)

Foydalanuvchi uchun qadamlar — [qollanma.md](qollanma.md). Bu yerda skriptlar
nima qilishi va nima sinalgani.

| Skript | Huquq | Vazifa |
|--------|-------|--------|
| `install/install.ps1` | oddiy | `uv sync --no-dev`, `tools/` tekshiruvi, ma'lumotlar papkasi, yorliqlar |
| `install/service.ps1` | `install/remove/start/stop/restart` — administrator; `plan/status` — oddiy | NSSM xizmati |
| `install/uninstall.ps1` | oddiy | yorliqlarni o'chiradi; ma'lumotlarga tegmaydi |
| `install/stop-core.ps1` | oddiy (token faylini o'qiy oladigan hisob) | xizmat bo'lmagan, ishlab turgan yadroni API orqali tartibli to'xtatadi va jarayoni tugaguncha kutadi; o'rnatuvchi yangilash va olib tashlashdan oldin chaqiradi. Portni `config.toml` dan oladi. Kod 0 — yadro yo'q yoki to'xtadi, 1 — hali ishlayapti |
| `install/common.ps1` | — | umumiy funksiyalar |

Skriptlar faqat ASCII: Windows PowerShell 5.1 BOM'siz UTF-8 faylni ANSI deb
o'qiydi (test buni qo'riqlaydi).

## `install.ps1`

- `-DataDir <yo'l>` — standart `%PROGRAMDATA%\SRV_1` o'rniga. Bunda skript
  `SRV1_DATA_DIR` ni qanday o'rnatishni ko'rsatadi (o'zi o'rnatmaydi).
- `-ShortcutDir <papka,...>`, `-NoShortcut`, `-Dev` (pytest/ruff/pyright ham),
  `-SkipSync`.
- **Ma'lumotlar papkasi ruxsatlari.** `ProgramData` ichida yaratilgan papkani
  odatda barcha foydalanuvchilar o'qiy oladi. Skript yangi papkada merosni
  uzadi va faqat uch yozuv qoldiradi: joriy foydalanuvchi, `SYSTEM` (S-1-5-18),
  administratorlar (S-1-5-32-544). SID ishlatiladi — guruh nomlari Windows
  tiliga qarab farq qiladi. **Mavjud papkaning ruxsatlariga tegilmaydi.**
- Tashqi dasturlarni skript **yuklab olmaydi** — faqat bor-yo'qligini ko'rsatadi
  ([tools/README.md](../tools/README.md)).
- Yorliq: `.venv\Scripts\pythonw.exe -m srv1_shell`, belgi —
  `shell/srv1_shell/srv1.ico` (kodda chizilgan: `python -m srv1_shell.icon`).

## `service.ps1` — NSSM sozlamalari

`-Action plan` aniq buyruqlarni chiqaradi. Asosiylari:

| Sozlama | Qiymat | Nega |
|---------|--------|------|
| dastur | `.venv\Scripts\python.exe -m srv1_core` | |
| `AppEnvironmentExtra` | `SRV1_DATA_DIR=...`, `PYTHONUNBUFFERED=1` | |
| `Start` | `SERVICE_DELAYED_AUTO_START` | 4 GB mashinada Windows yuklanishiga xalaqit bermasin |
| `ObjectName` | sizning hisobingiz (parol `Get-Credential` bilan so'raladi) | token, COM portlar va fayllar shell bilan bir egada |
| `AppStdout`/`AppStderr` | `<ma'lumotlar>\logs\service.log`, 1 MB da aylanadi | |
| `AppExit Default` | `Restart`, 5 s kechikish | yiqilsa qayta ko'tariladi |
| `AppExit 2` | `Exit` | sozlama xatosida cheksiz qayta urinmaydi |
| `AppStopMethodConsole` | 20000 ms | Ctrl+C — yadro plagin va loyihalarni o'zi yopadi |

20 s da yopilmasa, NSSM butun jarayon daraxtini o'ldiradi. NSSM 2.24 da bu doimiy
xatti-harakat; `AppKillProcessTree` parametri faqat 2.25 sinov yig'ilishlarida bor va
2.24 uni rad etadi, shuning uchun skript uni qo'ymaydi (2026-11-13 dagi birinchi haqiqiy
o'rnatish aynan shu parametrda yiqilgan).

Sozlash yarim yo'lda yiqilsa, skript xizmatni olib tashlaydi — `LocalSystem` nomidan
avtostartli yarim xizmat qolmaydi.

Nega `LocalSystem` emas: yadro `auth.token` ni faqat o'z egasiga ochadi;
xizmat `SYSTEM` bo'lsa, oddiy foydalanuvchining shell'i tokenni o'qiy olmaydi.

Parol NSSM'ga buyruq satri orqali beriladi (NSSM hisobga «xizmat sifatida
kirish» huquqini ham shu yerda beradi), ya'ni o'rnatish paytida bir lahza
jarayon argumentlarida ko'rinadi. Keyin uni Windows (LSA) saqlaydi; skript
hech qayerga yozmaydi.

**NSSM tuzog'i:** `nssm.exe` konsolsiz yoki huquqsiz chaqirilsa, xabar oynasi
ochadi va chaqiruvchini kutdirib qo'yadi. Shu sabab skript administratorlikni
va faylni NSSM'dan **oldin** tekshiradi, testlar esa NSSM'ni umuman chaqirmaydi.

## Sinalgan va sinalmagan

**Sinalgan** (`tests/test_install_scripts.py`, `tests/test_service_stop.py`):

- besh skript ham xatosiz tahlil qilinadi (PowerShell parser);
- `stop-core.ps1` haqiqiy yadroni to'xtatadi (`tests/test_server_control.py`): yadro yo'q
  bo'lsa kod 0; token noto'g'ri bo'lsa kod 1 va yadro ishlayveradi; to'g'ri token bilan
  kod 0 va skript qaytganda yadro jarayoni tugagan;
- `install.ps1` haqiqatan yuguradi (vaqtinchalik papkada): papkalar, uch
  yozuvli ruxsat ro'yxati, yorliq nishoni va belgisi; qayta yugurganda mavjud
  fayl va ruxsatlarga tegmaydi; `uninstall.ps1` yorliqni o'chiradi;
- `service.ps1 plan` — kutilgan NSSM buyruqlari, parol yo'q, hech narsa
  yaratilmaydi; `status`; administratorsiz o'zgartiruvchi amallar rad etiladi
  (NSSM chaqirilmasdan);
- **to'xtash mexanizmi**: yadro o'z konsolida ishga tushadi, tashqi jarayon
  NSSM kabi (`AttachConsole` + `GenerateConsoleCtrlEvent`) Ctrl+C yuboradi —
  yadro 20 s ichida kod 0 bilan chiqadi, Caddy va loyiha jarayoni qolmaydi.

**Haqiqiy o'rnatish (2026-11-13, foydalanuvchi administrator oynasida yugurdi):**

- xizmat foydalanuvchi hisobidan o'rnatildi va ishga tushdi; yadro `127.0.0.1:8710`
  da javob beradi, oddiy foydalanuvchi tokenni o'qiy oladi, Caddy ko'tarildi;
- `remove` ishlayotgan xizmatni toza to'xtatdi: NSSM STOP dan 1 s o'tib yadro
  `core_stopped` yozdi, chiqish kodi 0;
- xizmat daraxti (nssm + python + caddy + 2 conhost) private xotirasi: 151,7 MB
  (shell'siz, ishga tushgandan bir necha daqiqa o'tib, bir marta o'lchangan);
- ikki xato topildi va tuzatildi: `AppKillProcessTree` (yuqorida) va `nssm start`
  ning yolg'on xatosi. NSSM dastur `AppThrottle` (10 s) ishlagandan keyingina
  `running` deydi, `nssm start` esa undan oldin «Unexpected status
  SERVICE_START_PENDING» bilan 1 kod qaytaradi — xizmat esa ishga tushgan bo'ladi.
  Skript endi chiqish kodiga emas, 40 s ichida `running` holatiga qaraydi.
  **Tuzatilgan skriptning o'zi hali administrator bilan qayta yugurilmagan.**

**Sinalmagan:**

- qayta yuklashdan keyingi avtostart, yiqilgandan keyin qayta ko'tarilish,
  `start`/`stop`/`restart` amallari;
- `uv sync --no-dev` bilan toza mashinada o'rnatish (ishlab chiqish mashinasida
  muhit allaqachon bor edi; `-SkipSync` bilan sinalgan);
- standart `%PROGRAMDATA%\SRV_1` papkasini yaratish (test vaqtinchalik papkada);
- xizmat nomidan ishlaganda `PATH` (masalan `node` topilishi) va COM portlar.
