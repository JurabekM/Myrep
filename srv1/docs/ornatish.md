# O'rnatish va Windows xizmati (texnik tafsilot)

Foydalanuvchi uchun qadamlar — [qollanma.md](qollanma.md). Bu yerda skriptlar
nima qilishi va nima sinalgani.

| Skript | Huquq | Vazifa |
|--------|-------|--------|
| `install/install.ps1` | oddiy | `uv sync --no-dev`, `tools/` tekshiruvi, ma'lumotlar papkasi, yorliqlar |
| `install/service.ps1` | `install/remove/start/stop/restart` — administrator; `plan/status` — oddiy | NSSM xizmati |
| `install/uninstall.ps1` | oddiy | yorliqlarni o'chiradi; ma'lumotlarga tegmaydi |
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
| `AppKillProcessTree` | 1 | 20 s da yopilmasa, butun daraxt o'ldiriladi |

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

- to'rt skript ham xatosiz tahlil qilinadi (PowerShell parser);
- `install.ps1` haqiqatan yuguradi (vaqtinchalik papkada): papkalar, uch
  yozuvli ruxsat ro'yxati, yorliq nishoni va belgisi; qayta yugurganda mavjud
  fayl va ruxsatlarga tegmaydi; `uninstall.ps1` yorliqni o'chiradi;
- `service.ps1 plan` — kutilgan NSSM buyruqlari, parol yo'q, hech narsa
  yaratilmaydi; `status`; administratorsiz o'zgartiruvchi amallar rad etiladi
  (NSSM chaqirilmasdan);
- **to'xtash mexanizmi**: yadro o'z konsolida ishga tushadi, tashqi jarayon
  NSSM kabi (`AttachConsole` + `GenerateConsoleCtrlEvent`) Ctrl+C yuboradi —
  yadro 20 s ichida kod 0 bilan chiqadi, Caddy va loyiha jarayoni qolmaydi.

**Sinalmagan:**

- **xizmatni haqiqatan o'rnatish, ishga tushirish, qayta yuklashdan keyingi
  avtostart, yiqilgandan keyin qayta ko'tarilish** — administrator huquqi yo'q.
  `service.ps1 install` biror marta ham oxirigacha yugurmagan;
- `uv sync --no-dev` bilan toza mashinada o'rnatish (ishlab chiqish mashinasida
  muhit allaqachon bor edi; `-SkipSync` bilan sinalgan);
- standart `%PROGRAMDATA%\SRV_1` papkasini yaratish (test vaqtinchalik papkada);
- xizmat nomidan ishlaganda `PATH` (masalan `node` topilishi) va COM portlar.
