# Myrep — bir repoda ikki loyiha

Bu repoda ikkita mustaqil loyiha bor. Ishni boshlashdan oldin qaysi loyihada ishlayotganingni aniqla va faqat o'sha bo'lim qoidalariga amal qil.

| Loyiha | Papkalar |
| --- | --- |
| SRV_1 (Windows server, Python) | `core/`, `sdk/`, `shell/`, `plugins/`, `install/`, `tests/`, `pyproject.toml`, `uv.lock`, `docs/*.md` va `docs/img/`, `tools/README.md` |
| ROSTOR-2 (Android antifraud, Flutter + Kotlin) | `app/`, `registry/`, `tools/` dagi skriptlar (`*.py`, `*.ps1`, `rostor_db/`, `rostor_report/`, `store/`, `testapks/`), `docs/play/`, `docs/icon-preview.png`, `README.md` |

---

# SRV_1 — umumiy loyiha prompti

## Rol
Sen SRV_1 loyihasining bosh muhandisisan. Barcha tushuntirish, izoh, hujjat va
commit xabarlarini o'zbek tilida yoz. Kod, identifikatorlar va buyruqlar
ingliz tilida qoladi.

## Maqsad
SRV_1 — Windows 10 da ishlaydigan universal modulli server:
kichik yadro + plaginlar + alohida GUI shell. Vazifalari: fayllar bilan ishlash,
ma'lumotlarni tahlil qilish, IoT, elektronika/mikrokontrollerlar, IT
administrlash va sayt/loyihalarni joylash (hosting).

## Qat'iy cheklovlar (buzilmaydi)
- Mashina: Windows 10 x64, 4 GB RAM. Butun tizim bo'sh holatda 350 MB dan
  oshmasin (yadro + Caddy + shell).
- TAQIQLANGAN: Docker, WSL, VM, pandas, QtWebEngine, Celery, RQ, PostgreSQL,
  Redis, Electron, `shell=True`, `0.0.0.0` ga standart bog'lanish.
- GUI ichida biznes-mantiq bo'lmaydi: shell faqat yadro API'si orqali ishlaydi.
- Ro'yxatda yo'q kutubxonani qo'shishdan oldin mendan so'ra.
- Event loop: Windows Proactor (subprocess uchun kerak). Shu sabab `aiomqtt`
  ishlatilmaydi, MQTT uchun `paho-mqtt` o'z oqimida (`loop_start()`).

## Texnologik stek
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

## Arxitektura
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

## Repozitoriy tuzilmasi
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

## Bosqichlar
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

## Ish qoidalari
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

## Joriy holat
Qaysi bosqich tugagani va navbatdagisi `docs/bosqichlar.md` da yuritiladi.
Ishni boshlashdan oldin o'sha faylni o'qi. Buyruqlar: `docs/ishlab-chiqish.md`.

---

# ROSTOR-2 — loyiha qoidalari

Foydalanuvchi bilan o'zbek tilida (lotin). Kod, buyruqlar va identifikatorlar inglizcha.

## O'zgarmas talablar (foydalanuvchi 2026-11-01)
- Ilova **to'liq offlayn**: reliz manifestida `INTERNET` yo'q (`src/release/AndroidManifest.xml` uni majburan olib tashlaydi). Yangilanishlarni faqat developer yangi versiya sifatida chiqaradi.
- Texnologiya: Flutter (UI + qoidalar) + Kotlin (Android API). Uchinchi tomon Flutter plaginlari qo'shilmaydi — ular `INTERNET` olib kirishi mumkin; kerakli narsa MethodChannel orqali Kotlin'da yoziladi.
- `MANAGE_EXTERNAL_STORAGE`, Accessibility va SMS ruxsatlari so'ralmaydi. Yangi ruxsat qo'shilsa, `tools/check_release.py` dagi `ALLOWED` ataylab yangilanadi.
- `registry/registry.json` ga faqat manbasi tekshirilgan yozuv kiradi (`validate_registry`). Taxmin bilan domen, paket yoki telefon qo'shilmaydi.

## Joriy holat
- F0 + F1 tayyor (2026-11-01): APK Qalqon, qurilma auditi, Havola Qalqoni, xabar tekshiruvi, "haqiqiymi?", ta'lim ekrani.
- F2 tayyor (2026-11-01): Qo'ng'iroq Qalqoni — `call/PhoneRules.kt` (qoidalar), `CallShield.kt` (indeks, sozlamalar, tarix, bildirishnoma), `ShieldScreeningService`; Flutter `ui/call_screen.dart`; matndagi raqamlar `core/phone.dart` + `text_rules._phoneFindings`.
- F3 tayyor (2026-11-01): imzolangan firibgarlik hisoboti — Kotlin `report/` (ReportCodec, ReporterKeys, ReportFileProvider), Flutter `core/report_draft.dart`, `ui/report_screen.dart`, `ui/quiz_screen.dart`; developer vositasi `tools/rostor_report/` (verify, aggregate, kat). O'zbekcha Material matnlari (`flutter_localizations`, SDK ichida), to'q splash.
- Testlar: `flutter test` 49/49, Kotlin `testDebugUnitTest` 23/23, `tools/rostor_report/test_rostor_report.py` 6/6 (Python va ROSTOR-1 KAT; raqamlar uchun `app/test/fixtures/phone_kat.json`; hisobot uchun `report-kat.json` — Python imzolagani Kotlin'da, Kotlin imzolagani Python'da tekshiriladi).
- Emulyatorda (BTQ_V02, API 36) debug va release yig'ilishi har ekranda sinalgan. Sinovda topilgan 2 xato regressiya testi bilan qulflangan.
- Reliz APK hozircha debug kaliti bilan imzolangan (`release/*-SINOV.apk`).
- F4 tayyor (2026-11-01): versiya 1.0.0+1; `build.gradle.kts` imzosi `ROSTOR2_SIGNING_PROPERTIES`/`-PsigningProperties` dan (yo'q bo'lsa debug), `BuildConfig.EXPECTED_SIGNATURE_SHA256` "haqiqiymi?" ekraniga; `tools/create_upload_key.ps1`, `tools/build_release.ps1` (natija `release/<versiya>/`), `check_release.py` APK+AAB imzo tekshiruvi; `docs/play/*`, `tools/store/*` (grafika, 6 ta uz skrinshot 1080×1920, `check_listing.py`); `test/design/icon_policy_test.dart`.
- Upload kaliti yaratildi (2026-11-02, `C:\keys\rostor2\upload`, SHA-256 `5625D80E…1A1AF10B`). Imzolangan reliz `release/1.0.0+1/` (3 APK + AAB), `check_release` va apksigner/jarsigner bilan tasdiqlangan; x86_64 APK emulyatorda sinalgan (bosh ekran, "haqiqiymi?" izi = upload kaliti, audit, xabar, qo'ng'iroq, hisobot imzosi).
- Kutilmoqda (foydalanuvchi): maxfiylik siyosatini ommaviy joyga qo'yish (`<ALOQA_EMAIL>` va boshqalar), Play Console, birinchi yuklashdan keyin app signing SHA-256 ni README'ga yozish.

## Tuzoqlar
- Android 13+ "Restricted settings": sideload qilingan ilovaning Accessibility'sini `settings put` jim bekor qiladi. Sinovda avval `appops set <pkg> ACCESS_RESTRICTED_SETTINGS allow`.
- TOFU: fayldagi APK bilan bir xil imzo faqat o'rnatilgan nusxa **do'kondan** kelgan bo'lsa ishonch beradi.
- Git Bash'da `adb shell` yo'llari uchun `MSYS_NO_PATHCONV=1`.
- Raqam normallashtirish Kotlin (`PhoneNumbers`) va Dart (`normalizePhone`) da ikki marta yozilgan — o'zgartirsang, ikkalasini va `phone_kat.json` ni birga o'zgartir. `URLDecoder` ochiq "+" ni probelga aylantiradi (faqat `%` bo'lsa dekodla).
- Qo'ng'iroq qoidalari faqat Kotlin'da: xizmat Flutter dvigatelisiz ishlaydi, UI "raqamni tekshirish" ham `checkPhone` orqali shu kodni chaqiradi.
- `CALL_SCREENING` roli `POST_NOTIFICATIONS` ni avtomatik beradi (`GRANTED_BY_ROLE`). Kontaktdagi raqamlar uchun tizim xizmatni chaqirmasligi mumkin; messenjer qo'ng'iroqlari umuman kelmaydi.
- Qo'ng'iroq paytida tizimning "kiruvchi qo'ng'iroq" heads-up oynasi ustunlik qiladi: ROSTOR-2 ogohlantirishi bildirishnomalar pardasida va qo'ng'iroqdan keyin ko'rinadi (bloklanganda heads-up chiqadi).
- Emulyatorda qo'ng'iroq: `adb emu gsm call <raqam>` / `gsm cancel <raqam>`. Emulyator oynasini boot'dan keyin darhol `C:\Users\comp_2.1\tools\place_emulator.ps1` bilan joylashtir.
- `gradlew` ni to'g'ridan-to'g'ri ishlatganda `JAVA_HOME` = Android Studio JBR (tizimdagi JDK 25 Gradle'ni yiqitadi); avval `flutter pub get`.
- Hisobot: `content` baytlari faylga o'zgarishsiz joylanadi va shular imzolanadi — JSON'ni qayta kanonlashtirma. `readable` imzolanmaydi; tekshiruv faqat `content` ga tayanadi. Hisobot kaliti urug'lari prefs "rostor2_keys" da, Keystore AES-GCM bilan o'ralgan; Keystore yo'qolsa yangi qurilma ID paydo bo'ladi.
- BouncyCastle `MLDSAPrivateKeyParameters(ml_dsa_65, seed32)` Python `from_seed_bytes` bilan bir xil kalit beradi (ReportCodecTest tasdiqlaydi).
- Kategoriya nomlari Kotlin `ReportCodec.CATEGORIES` va Dart `reportCategories` da ikki marta — birga o'zgartir.
- Python skript bilan Kotlin/Dart tahrirlaganda `"\n"` haqiqiy qatorga aylanadi — Edit ishlat.
- `C:\keys\rostor2\upload\key.properties` ni HECH QACHON ochma va ko'rsatma (parol ochiq matnda). Kalitni foydalanuvchi `create_upload_key.ps1` bilan o'zi yaratadi.
- Play App Signing: Play'dan o'rnatilgan ilova izi = app signing key (upload kaliti emas). `-ExpectedSignatureSha256` AAB uchun Play xeshi bilan `-NoApk`; APK'larda bu xesh mos kelmaydi.
- `apksigner -v` chiqishi `V2 Signer: certificate DN:` — regex ikkala formatni qabul qiladi, o'qilmasa yopiq holatda yiqiladi.
- Play skrinshotlari: `wm size 1080x1920` + `wm density 380` + SystemUI demo rejimi; `adb input text` ni fokuslanmagan maydonga yuborma — oyna atrofida yashil fokus ramkasi qoladi (faqat qayta yuklash ketkazdi). Ish oxirida `wm size/density reset`, demo `exit`.
- Baza kaliti: `C:\keys\rostor2\db` (repo tashqarisida). `rostor_db.py keygen --force` eski ilovalarni yangi bazadan uzib qo'yadi.
