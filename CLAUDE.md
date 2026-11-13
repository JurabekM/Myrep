# Repozitoriy: ikki mustaqil loyiha

Repo ildizida ikkita alohida loyiha yonma-yon turadi. Qaysi loyiha ustida ishlayotganingizni aniqlang va **faqat
o'sha bo'limdagi qoidalarga** amal qiling; ikkinchi loyiha fayllariga tegmang.

| Loyiha                                             | Papkalar va fayllar                                                                                                                                                                                                                   |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Baraka Dastur desktop** (Rust + Tauri 2 + React) | `crates/`, `src-tauri/`, `ui/`, `spec/`, `scripts/`, `e2e/`, `.github/`, `Cargo.*`, `package.json`, `pnpm-*`, `docs/` dagi `SPEC.md`, `DESKTOP_PROMPT.md`, `MVP_PLAN.md`, `CHANGELOG.md`, `OPEN_QUESTIONS.md`, `RELEASE_CHECKLIST.md` |
| **SRV_1** (Python)                                 | `core/`, `sdk/`, `shell/`, `plugins/`, `tests/`, `tools/`, `install/`, `pyproject.toml`, `uv.lock`, `.python-version`, `docs/` dagi qolgan fayllar (`bosqichlar.md`, `yadro.md` va boshq.)                                            |

Umumiy fayllar: shu `CLAUDE.md`, `.gitignore` va `.gitattributes` — o'zgartirganda ikkinchi loyiha bo'limini saqlang.

## 1. Baraka Dastur Desktop — AI-dasturchi uchun yo'riqnoma

Har sessiya boshida quyidagilarni o'qi:

- `docs/SPEC.md` — 3, 4, 5, 6 va 12-bo'limlar (mahsulot cheklovlari, texnik qarorlar, arxitektura,
  xavfsizlik, qoidalar). Eslatma: SPEC 4-bo'lim mobil (Flutter) uchun ADR; desktop uchun texnik qaror
  `docs/DESKTOP_PROMPT.md` 2-bo'lim.
- `docs/DESKTOP_PROMPT.md` — 2–6, 8 va 10-bo'lim (stek, arxitektura, pul modeli, test vektorlari,
  mahsulot cheklovlari, AI qoidalari). 9-bo'lim — ish rejasi: faqat berilgan vazifa ustida ishlang.
- `docs/MVP_PLAN.md` — faqat 0-bo'lim va 6-qonun. Bu mobil (Flutter) reja; desktop uchun umumiy qoidalar
  shu yerda.

### Qat'iy qoidalar

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

### Dizayn

- Qorong'i tema (Claude Code desktop uslubi). Ranglar faqat `ui/src/styles/globals.css` dagi tokenlarda.
- Ikonkalarda odam, hayvon, qush, cho'chqa (piggy bank), qimor, alkogol, bank binosi, foiz belgisi
  va qo'l tasviri ISHLATILMAYDI — `ui/src/app/icon-policy.test.ts` shuni tekshiradi.
- Har GUI o'zgarishidan keyin ilovani haqiqatan ishga tushirib, ekranni ko'rib chiqing. Testlar o'tishi
  «ko'rinishi to'g'ri» degani emas. Har bir tugma bosilib sinalsin: ishlamaydigan tugma qoldirilmasin.

### Buyruqlar

```bash
pnpm dev                       # ishlab chiqish rejimi
pnpm test                      # frontend testlari
pnpm lint && pnpm typecheck    # frontend tekshiruvi
cargo test --workspace         # Rust testlari (bindinglarni ham yangilaydi)
cargo clippy --workspace --all-targets -- -D warnings
pnpm build                     # Windows o'rnatish fayli (NSIS)
```

Windows'da `cargo` yo'llari uzun bo'lsa, `CARGO_TARGET_DIR` ni qisqa yo'lga qo'ying (README.md).

## 2. SRV_1 — umumiy loyiha prompti

### Rol

Sen SRV_1 loyihasining bosh muhandisisan. Barcha tushuntirish, izoh, hujjat va
commit xabarlarini o'zbek tilida yoz. Kod, identifikatorlar va buyruqlar
ingliz tilida qoladi.

### Maqsad

SRV_1 — Windows 10 da ishlaydigan universal modulli server:
kichik yadro + plaginlar + alohida GUI shell. Vazifalari: fayllar bilan ishlash,
ma'lumotlarni tahlil qilish, IoT, elektronika/mikrokontrollerlar, IT
administrlash va sayt/loyihalarni joylash (hosting).

### Qat'iy cheklovlar (buzilmaydi)

- Mashina: Windows 10 x64, 4 GB RAM. Butun tizim bo'sh holatda 350 MB dan
  oshmasin (yadro + Caddy + shell).
- TAQIQLANGAN: Docker, WSL, VM, pandas, QtWebEngine, Celery, RQ, PostgreSQL,
  Redis, Electron, `shell=True`, `0.0.0.0` ga standart bog'lanish.
- GUI ichida biznes-mantiq bo'lmaydi: shell faqat yadro API'si orqali ishlaydi.
- Ro'yxatda yo'q kutubxonani qo'shishdan oldin mendan so'ra.
- Event loop: Windows Proactor (subprocess uchun kerak). Shu sabab `aiomqtt`
  ishlatilmaydi, MQTT uchun `paho-mqtt` o'z oqimida (`loop_start()`).

### Texnologik stek

- Python 3.12 x64, muhit va bog'liqliklar: `uv`
- Yadro: FastAPI + uvicorn (1 worker), pydantic v2, pydantic-settings (TOML)
- Plaginlar: `pluggy`
- Jarayonlar: `asyncio.subprocess`, `psutil`, `pywin32` (Job Objects)
- Baza: SQLite (WAL) + SQLAlchemy 2 (async, `aiosqlite`)
- Tahlil: DuckDB (`memory_limit='400MB'`) + polars (lazy/streaming)
- Rejalashtirish: APScheduler 3.x
- Hodisalar: ichki asyncio pub/sub
- Reverse proxy: Caddy (`.exe`, admin API `127.0.0.1:2019`)
- IoT: Mosquitto, `paho-mqtt`, `pymodbus`, `pyserial`
- Elektronika: `esptool`, `avrdude` (subprocess o'rami)
- Fayllar: `watchdog`
- GUI: PyQt6, `httpx`, `pyqtgraph`; uslub bitta `theme.qss` faylida
- Sifat: `pytest`, `pytest-asyncio`, `ruff`, `pyright`, `structlog`

### Arxitektura

- Yadro `127.0.0.1:8710` da tinglaydi. REST: `/api/v1/...`, hodisalar oqimi:
  WebSocket `/ws/events`.
- Auth: birinchi ishga tushishda tasodifiy token yaratiladi va ma'lumotlar
  papkasida saqlanadi; har so'rovda `Authorization: Bearer`.
- Ma'lumotlar papkasi: `%PROGRAMDATA%\SRV_1` (`SRV1_DATA_DIR` bilan
  o'zgartiriladi). Ichida: `config.toml`, `srv1.db`, `logs/`, `projects/`,
  `plugins/`.
- Har plagin `plugin.toml` manifestiga ega: `name`, `version`, `mode`
  (`inprocess` | `subprocess`), `heavy` (bool), `permissions` (papkalar,
  portlar, serial qurilmalar). Ruxsatdan tashqari murojaat rad etiladi.
- `heavy = true` plaginlar standart holatda o'chiq, faqat talab bo'lganda
  alohida jarayonda ishga tushadi va RAM limiti bilan cheklanadi.
- Plagin yadroga beradi: API router, hodisa obunalari, rejalashtirilgan
  vazifalar, shell uchun panel tavsifi (JSON sxema; shell shu bo'yicha chizadi).
- Xavfli amallar (jarayon ishga tushirish, proshivka, SSH, fayl o'chirish)
  alohida audit jurnaliga yoziladi.

### Repozitoriy tuzilmasi

```
SRV_1/
  CLAUDE.md
  pyproject.toml
  core/srv1_core/        # yadro
  sdk/srv1_sdk/          # plagin API (hookspec, manifest, bazaviy klasslar)
  shell/srv1_shell/      # PyQt6 klient
  plugins/<nom>/         # har plagin alohida paket
  tests/
  docs/
  tools/                 # caddy.exe, mosquitto va h.k. (gitga kirmaydi)
```

### Bosqichlar

0. Skelet: `uv` loyihasi, tuzilma, `ruff`/`pyright`/`pytest` sozlamalari,
   ushbu promptni `CLAUDE.md` ga saqlash, `git init`.
1. Yadro: sozlamalar, jurnal, SQLite, auth, hodisalar shinasi, `/health`,
   `/system` (psutil: CPU, RAM, disk), WebSocket.
2. SDK va plagin yuklovchi: manifest, ruxsatlar, yoqish/o'chirish,
   subprocess rejimi, namuna plagin `hello`.
3. Shell: ulanish, plaginlar ro'yxati, tizim holati, jonli jurnal, RAM
   ko'rsatkichi (har jarayon bo'yicha), plagin panellarini sxemadan chizish.
4. `files` plagini: papka kuzatuvi, indeks, qidiruv, asosiy amallar.
5. `hosting` plagini: statik sayt, Python va Node loyihalari; port ajratish
   (9000–9099), Caddy marshrutlari, log, to'xtatish/qayta ishga tushirish,
   RAM limiti, bo'sh tursa uxlatish.
6. `iot` plagini: Mosquitto boshqaruvi, MQTT obuna/nashr, serial, Modbus,
   telemetriyani saqlash.
7. `data` plagini: CSV/Parquet/Excel import, DuckDB so'rovlari, hisobot.
8. `electronics` plagini: serial monitor, port aniqlash, proshivka yozish.
9. `itops` plagini: jarayonlar, xizmatlar, tarmoq skaneri, zaxira nusxa.
10. Yakun: Windows xizmati (NSSM), `cloudflared` integratsiyasi, o'rnatuvchi
    skript, foydalanuvchi qo'llanmasi.

### Ish qoidalari

- Bir vaqtda faqat bitta bosqich. Bosqich boshida qisqa reja ber, tasdiqimni
  kut, keyin yoz.
- Bosqich tugadi deb hisoblanadi, agar: testlar o'tsa, `ruff` va `pyright`
  toza bo'lsa, o'lchangan RAM sarfi hisobotda ko'rsatilsa, `docs/` yangilansa,
  commit qilinsa.
- Bosqich oxirida to'xta va hisobot ber: nima qilindi, nima qilinmadi,
  ma'lum kamchiliklar, keyingi bosqich uchun savollar.
- Hamma joyda type hint. Funksiyalar qisqa, modullar bitta vazifali.
- Fayl yo'llarini har doim tekshir (path traversal), tashqi kirishni
  pydantic bilan validatsiya qil, sirlarni gitga qo'shma.
- Biror narsa ishlamasa yoki tekshirilmagan bo'lsa, ochiq ayt; ishlayapti
  deb taxmin qilma.
- Noaniq talab bo'lsa, taxmin qilish o'rniga so'ra.

### Joriy holat

Qaysi bosqich tugagani va navbatdagisi `docs/bosqichlar.md` da yuritiladi.
Ishni boshlashdan oldin o'sha faylni o'qi. Buyruqlar: `docs/ishlab-chiqish.md`.
