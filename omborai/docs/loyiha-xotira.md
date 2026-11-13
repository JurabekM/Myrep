# OmborAI — loyiha xotirasi

Tekshirilgan holat: 2026-10-11. Git ildizi: `/home/user/Myrep` (ko'p loyihali repo). OmborAI `omborai/` papkasida. Ish branch: `claude/wonderful-dirac-gdu5x2`, HEAD `f422fbe`, PR #6 (bazasi `master`).

Tekshiruv izohi: sonlar, konstantalar, sxemalar, route ro'yxati, git holati, PR metama'lumoti va MQTT test vektori shu tekshiruvda buyruq yoki fayl o'qish bilan tasdiqlangan. Tasdiqlanmagan yoki bu muhitda ishga tushirilmagan narsalar `UNVERIFIED` deb belgilangan. Hujjatda parol, token, kalit yoki `.env` qiymatlari yo'q; ular faqat nomi bilan keltirilgan.

## 1. Qisqa xulosa

- **Nima yasalgan:** kichik do'konlar uchun ombor, kassa (POS), qarz daftari va hisobotlar tizimi. Desktop kassa (Python 3.12 + PySide6), Android mobil ilova (Flutter + native Kotlin shtrix-kod skaneri), FastAPI + PostgreSQL backend va Docker Compose/Caddy infratuzilmasi yasalgan.
- **Hozirgi arxitektura:** serversiz. Login, do'kon, tovar, savdo, smena va foydalanuvchilar har bir qurilmadagi shifrlangan lokal bazada. Qurilmalar faqat MQTT orqali (`broker.hivemq.com`, AES-256-GCM) sinxronlanadi. Backend klientlar tomonidan ishlatilmaydi.
- **Holat:** `origin/master` ustida 21 ta commit, PR #6 ochiq (`mergeable_state: clean`). Ruff va mypy tekshiruvlari o'tgan. To'liq test to'plami va qurilmada sinov tasdiqlanmagan.
- **Ma'lum jiddiy nuqsonlar:** (1) yangi qurilma snapshot'ni qabul qilmay qolishi mumkin (bootstrap race) va qayta so'ramaydi; (2) chek sotuv tarixisiz snapshot bilan ulangan qurilmada qaytarish qoldiqni tiklamaydi (divergensiya). Ikkalasi ham takrorlangan, avtomatik testi yo'q.
- **Qolgan asosiy ishlar:** mobil ilovada login'dan keyin bosh ekranga o'tish yo'qligi, qaytarishni rol bo'yicha cheklash, fiskal/OFD talablarini aniqlash, tovar kirimi UI, to'lovni bo'lish, hisobot va qarz daftari, ommaviy broker xavfsizligi bo'yicha qaror.
- **Platforma qarorlari:** iOS rejadan chiqarilgan; mobil ilova faqat Android uchun.

## 2. Loyiha va maqsad

- **Mahsulot:** kichik do'konlar uchun ombor (tovar, shtrix-kod, qoldiq), kassa (savdo, smena, to'lov, qaytarish), qarz daftari va hisobotlar. Qarz daftari va hisobotlar hozir faqat reja (`docs/reja.md`) va dizayn eskizida (`design/dashboard.html`) bor; klient kodida yo'q.
- **Foydalanuvchilar:** do'kon egasi (`owner`) va kassir (`cashier`). Klientlar faqat shu ikki rolni ishlatadi. Backend'da `ROLES = ("owner", "manager", "cashier", "warehouse", "viewer")` bor — klient roli bilan mos emas (ochiq ish, 15-bo'lim).
- **Egasi huquqlari:** faqat do'kon egasi kassir qo'sha oladi, faollashtiradi yoki o'chiradi (desktop va mobil). Egasini o'chirib bo'lmaydi.
- **Bozor:** O'zbekiston. Pilot: barcha do'konlar uchun universal; aniq soha tanlanmagan.
- **Til:** o'zbek (lotin) va rus — foydalanuvchi tasdiqlagan (`docs/reja.md` Qarorlar). Ilova UI matnlari hozir asosan o'zbekcha lotin; ruscha tarjima UI'da to'liq emas (UNVERIFIED: to'liq qidiruv qilinmagan). Dizayn eskizlarida UZ/RU almashtirish bor (`design/assets/app.js`).
- **Platforma:** desktop — Windows uchun mo'ljallangan (`pyproject.toml` tavsifida Windows/Linux/macOS). Mobil — faqat Android (`minSdk` 26). iOS rejadan chiqarilgan.
- **Fiskal kassa / OFD:** MVP'ga kiradi deb belgilangan, lekin provayder, chek formati va API talablari aniqlanmagan. Ilovalarda "Fiskal chek: ishlab chiqish jarayonida" yozuvi ko'rsatiladi (`desktop/omborai_desktop/ui/main_window.py:177`, `desktop/omborai_desktop/receipt.py:61`, `mobile/lib/src/screens/sale_screen.dart:219`).

## 3. Qarorlar tarixi

### 3.1 Doimiy qoidalar (sanasiz, foydalanuvchi qarori)

- Ish uslubi: uzun sessiyalarda to'xtamasdan ishlash.
- PR faqat so'ralganda ochiladi.
- Ish branch'i: `claude/wonderful-dirac-gdu5x2`; PR bazasi: `master`.
- Commit xabarlarida model nomi yozilmaydi; faqat `Claude-Session` trailer. Tekshirildi: 21 ta commitning 21 tasida `Claude-Session` bor, `Co-Authored-By` yo'q. Ziddiyat: 16-bo'limga qarang.
- Pilot: barcha do'konlar uchun universal; aniq soha yo'q.
- Jamoa: foydalanuvchi va Claude (AI yordamchi).

### 3.2 Xronologiya (2026-10-10, commit vaqti UTC)

| Vaqt | Commit | Qaror yoki o'zgarish |
|---|---|---|
| 03:57 | `5915618` | Faza 0: loyiha rejasi (`docs/reja.md`) va dizayn eskizlari. |
| 04:02–04:19 | `a61ebd4`, `8134543`, `d11d584`, `a644cad`, `8919e72`, `3abcb9c`, `6db98f5` | Faza 1–4: backend (FastAPI, PostgreSQL RLS), tovar/qoldiq, smena/savdo, desktop PySide6 kassa, REST sinxronizatsiya (`/v1/sync/push`, `/v1/sync/pull`). Bu yo'nalish keyin bekor qilindi. |
| 04:48–04:49 | `1121b3b`, `891dac3`, `607283b` | Faza 5: mobil ilova (Flutter + Kotlin skaner), CI (`.github/workflows`), README. |
| 06:12 | `cbc227b` | Foydalanuvchi qarorlari (reja oxiri): mobil faqat Android (iOS olib tashlandi); fiskal/OFD MVP'ga kiradi (talablar noma'lum); hosting — javob berilmagan; pilot soha — tanlanmagan; jamoa — foydalanuvchi va Claude. |
| 06:25 | `001cf54` | Lokal ma'lumot shifrlangan saqlanadi: desktop SQLCipher, mobil `sqflite_sqlcipher`. Kalitlar OS xavfsiz xotirasida. |
| 06:37 | `ddc0f37` | MQTT sinxronizatsiya protokoli va xavfsizlik modeli (`docs/sync-mqtt.md`): AES-256-GCM, mavzu nomi HKDF orqali. |
| 06:40 | `b5b6db4` | Savdo MQTT orqali (`broker.hivemq.com`). Fiskal — "ishlab chiqilmoqda". |
| 06:52 | `e652983` | Desktop: savdo, smena, qaytarish va katalog faqat MQTT orqali. |
| 07:06 | `90c570a` | Mobil ilova faqat MQTT orqali; tovar formasi. |
| 07:33 | `7fc1ec1` | Telefon sinovi uchun lokal server qo'llanmasi. Keyin serversiz rejim bilan bekor qilindi. |
| 07:38 | `8710860` | Sinov qo'llanmasi: emulyator manzili. Keyin bekor qilindi. |
| 14:04 | `9257970` | **Oxirgi qaror (1) — serversiz rejim.** Login, do'kon va foydalanuvchilar lokal bazada. Parol PBKDF2-HMAC-SHA256 bilan xeshlanadi. Do'kon juftlash kodi `store_id:kalit` bilan qo'shiladi. Foydalanuvchi operatsiyalari (`store`, `user`) MQTT'da sinxronlanadi. Backend klientlar tomonidan ishlatilmaydi. |
| 14:27 | `f422fbe` | **Oxirgi qaror (2) — kassirlarni boshqarish.** Kassirni faqat do'kon egasi qo'shadi, faollashtiradi yoki o'chiradi (desktop va mobil). Egasini o'chirib bo'lmaydi. |

Izoh: `cbc227b` dagi "hosting javobsiz" qarori va `9257970` dagi "backend ishlatilmaydi" natijasi o'rtasida ziddiyat yo'q, lekin hosting masalasi hali yopilmagan (3.3, 2-band).

### 3.3 Ochiq savollar

1. **Fiskal kassa / OFD / soliq:** provayder, chek formati va API aniqlanmagan (`docs/reja.md:202`, `:216`, `:238`). MVP'ga kiradi deb belgilangan, lekin `docs/reja.md:194` da "to'liq fiskal integratsiya" MVP'dan tashqarida deyilgan — ichki ziddiyat.
2. **Hosting va broker:** javob berilmagan. Ommaviy `broker.hivemq.com` autentifikatsiyasiz; `docs/reja.md:239` savdo ma'lumoti uchun mos emasligini qayd etadi, lekin ishlab chiqarish default'i shu host (`desktop/omborai_desktop/config.py:12`, `mobile/lib/src/sync/mqtt_sync.dart:21`). Xususiy broker uchun `MqttSync` da login/parol parametri yo'q.
3. **Serversiz xavfsizlik narxi:** parol xeshi do'kon kaliti bilan shifrlangan holda tarqaladi; kalit tarqalsa xeshdan parol taxmin qilinishi mumkin (`docs/sync-mqtt.md`). Bu qabul qilinganmi, tasdiqlanmagan.
4. **Pilot soha:** tanlanmagan (`docs/reja.md` Q5: oziq-ovqat, ulgurji, qurilish mollari yoki kiyim).
5. **Rus tili:** hal qilingan — o'zbek va rus tillari yetarli (foydalanuvchi javobi). Ilovalarda ruscha tarjimani to'liq qilish kerak (ochiq ish).
6. **Commit trailer siyosati:** foydalanuvchi qarori — faqat `Claude-Session`; bu sessiyaning tizim ko'rsatmasi esa `Co-Authored-By` qo'shishni talab qilgan. Keyingi sessiyada qaysi qoida ustun ekanini tasdiqlang.
7. **Tarif narxlari va obuna:** javobsiz (`docs/reja.md` Q9); kodda obuna moduli yo'q.
8. **Ma'lumot joylashuvi talabi** (`docs/reja.md` Q4) va **SMS provayder** (Q7): serversiz rejimda markaziy server va SMS yo'q; bu savollar yopilganmi, aniq emas.
9. **Kassir roli bilan qaytarish:** desktop va mobilda qaytarish hamma rol uchun ochiq (10.2-4). Qoida (faqat egasi/menejer) qabul qilinadimi — tasdiqlanmagan.

## 4. Repo tuzilishi

Git ildizi: `/home/user/Myrep`. Root'da `.gitignore`, `run_python.bat`, `.github/workflows/` (ikki fayl: `omborai-backend.yml`, `omborai-clients.yml`) va boshqa loyihalar bor. CI yo'llari `omborai/...` ga qaratilgan.

`omborai/` papkasi:

| Yo'l | Nima bor |
|---|---|
| `README.md` | Faza holati jadvali, papkalar, backend lokal ishga tushirish. Eskirgan qismlar bor (14-bo'lim). |
| `.gitignore` | `__pycache__/`, `.venv/`, `.env`, `infra/.env`, `desktop/build/`, `desktop/dist/`, `mobile/build/`, `mobile/.dart_tool/`, `*.egg-info/` va h.k. |
| `backend/` | FastAPI backend. `app/` (asosiy kod), `migrations/` (Alembic, 4 ta versiya), `tests/` (6 test fayl), `scripts/export_openapi.py`, `Dockerfile`, `pyproject.toml`, `alembic.ini`, `.env.example`. |
| `backend/app/` | `main.py` (create_app), `config.py`, `db.py` (RLS kontekst), `deps.py` (Principal, `require_roles`), `errors.py` (RFC 7807), `security.py` (argon2, JWT, refresh), `models.py` (17 jadval), `schemas.py`, `api/` (11 fayl: auth, catalog, health, me, purchases, sales, shifts, stock, stores, sync), `services/` (stock.py, sales.py). |
| `backend/migrations/versions/` | `0001_init`, `0002_catalog_stock`, `0003_sales`, `0004_sync` (chiziqli zanjir, head = `0004_sync`). |
| `backend/omborai_backend.egg-info/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Generatsiya qilingan, gitignore'da. |
| `desktop/` | Python 3.12 + PySide6 kassa. `omborai_desktop/` paketi (24 `.py` fayl), `tests/` (8 test fayl + `conftest.py`), `pyproject.toml`, `README.md`. |
| `desktop/omborai_desktop/` | `__main__.py`, `config.py`, `security.py`, `auth.py`, `users.py`, `cart.py`, `money.py`, `receipt.py`, `escpos.py`; `offline/store.py` (LocalStore); `sync/` (crypto.py, ops.py, mqtt_sync.py); `ui/` (main_window.py, login.py, dialogs.py, products_dialog.py, users_dialog.py, tasks.py, theme.py). |
| `desktop/omborai_desktop.egg-info/` | Generatsiya qilingan, gitignore'da. `SOURCES.txt` eskirgan: `users.py`, `ui/users_dialog.py`, `tests/conftest.py`, `tests/test_auth.py`, `tests/test_users.py` ro'yxatda yo'q. |
| `mobile/` | Flutter loyiha (faqat Android). `lib/` (18 Dart fayl, 3355 qator), `test/` (8 fayl), `android/` (Gradle, native Kotlin), `pubspec.yaml`, `pubspec.lock`, `analysis_options.yaml`, `README.md` (eskirgan). `ios/` papkasi yo'q. |
| `mobile/lib/` | `main.dart`; `src/app_session.dart`, `src/auth.dart`, `src/money.dart`; `src/domain/cart.dart`; `src/offline/local_db.dart`; `src/sync/` (crypto.dart, mqtt_sync.dart, ops.dart); `src/screens/` (9 ekran). |
| `mobile/android/app/src/main/kotlin/uz/omborai/omborai_mobile/` | `MainActivity.kt`; `scanner/` (BarcodeScannerPlugin.kt, BarcodeScannerViewFactory.kt, BarcodeScannerView.kt). |
| `mobile/build/` | Build natijalari (gitignore'da). Ichida APK fayllar bor (6-bo'lim). |
| `shared/openapi.json` | OpenAPI 3.1.0 shartnoma: 23 path, 32 operatsiya. `backend/scripts/export_openapi.py` yaratadi; CI farqni tekshiradi. |
| `infra/` | `docker-compose.yml` (postgres, redis, migrate, api, caddy), `.env.example`, `caddy/Caddyfile`, `postgres/init/01-app-role.sh`. |
| `design/` | `dashboard.html` ("Bosh sahifa (eskiz)"), `inventory.html` ("Tovarlar (eskiz)"), `pos.html` ("Kassa (eskiz)"), `assets/app.js`, `assets/styles.css`. |
| `docs/` | `reja.md` (241 qator, to'liq reja va qarorlar), `sync-mqtt.md` (MQTT protokoli va xavfsizlik), `sinov-telefon.md` (telefon va kompyuter bilan qo'lda sinov), `loyiha-xotira.md` (shu fayl). |

Kod hajmi (tekshirildi): backend `app/` — 2470 qator Python; desktop `omborai_desktop/` — 2885 qator Python; mobil `lib/` — 3355 qator Dart.

## 5. Desktop ilova

### 5.1 Arxitektura

- **UI:** PySide6 (`ui/`). Oynalar: `PosWindow` (kassa), login oqimi, mahsulotlar, foydalanuvchilar. API chaqiruvi yo'q; fon ishlari `ui/tasks.py` (QThreadPool).
- **Ma'lumot:** `offline/store.py` — `LocalStore`. SQLCipher bazasi (kalit berilsa, `PRAGMA key = "x'<64 hex>'"`); kalit berilmasa oddiy `sqlite3` (testlar uchun). Jadvallar 9 ta (9-bo'lim). Operatsiyalar `apply_op()` orqali bir tranzaksiyada qo'llanadi va `applied_ops` bilan dedupe qilinadi.
- **Sinxronizatsiya:** `sync/mqtt_sync.py` — `MqttSync` (paho-mqtt 2.x, `CallbackAPIVersion.VERSION2`, `clean_session=False`, QoS 1). Shifrlash `sync/crypto.py`da (8-bo'lim). Operatsiya tuzilishi va `op_id` qoidalari `sync/ops.py`da.
- **Domen:** `cart.py` (Qt'siz savat, `to_sale_payload()`), `money.py` (`round_som` ROUND_HALF_UP, `format_som`, `format_qty`), `receipt.py` (kenglikka mos matnli chek), `escpos.py` (ESC/POS baytlari, CP866, kesish; tarmoq printeri TCP 9100), `auth.py` (PBKDF2, login normallashtirish, juftlash kodi), `users.py` (kassir qo'shish va faollashtirish/o'chirish operatsiyalari).
- **Xavfsizlik:** `security.py` — OS keyring (ro'yxat 5.5 da).

### 5.2 Modullar qisqacha

| Fayl | Vazifa |
|---|---|
| `__init__.py` | `__version__ = "0.1.0"`. |
| `__main__.py` | `main()`: QApplication, tema, konfiguratsiya, lokal baza, login, MQTT, `PosWindow`. |
| `config.py` | `DesktopConfig` (frozen dataclass), `from_env()`. |
| `security.py` | Keyring: lokal baza kaliti va do'kon kaliti. |
| `auth.py` | `hash_password`, `verify_password` (PBKDF2), `normalize_login`, `make_pairing_code`, `parse_pairing_code`. |
| `users.py` | `add_cashier`, `set_active` — `user` operatsiyasini yasaydi (rol tekshiruvi UI'da). |
| `offline/store.py` | `LocalStore`: sxema, outbox (`enqueue`, `pending_ops`), `apply_op` va handler'lar, so'rovlar, `snapshot_payload`. |
| `sync/crypto.py` | `generate_store_key`, `topic_for`, `seal`, `open_envelope`, `DecryptionError`. |
| `sync/ops.py` | Tur konstantalari, `new_op()`, `refund_op_id()` (`refund:<sale_id>`). |
| `sync/mqtt_sync.py` | `MqttSync`: `start`, `stop`, `send` (10 s publish kutadi), callback'lar. |
| `ui/main_window.py` | `PosWindow`: qidiruv (F2), savat, smena, qaytarish, katalog, foydalanuvchilar, sinxron holati, snapshot so'rovi. |
| `ui/login.py` | Birinchi ishga tushirish: `StartDialog`, `CreateStoreDialog`, `JoinDialog` (`LoginDialog` `ui/dialogs.py` dan import qilinadi); `run_login`, `create_store`, `join_store`, `pairing_code`. |
| `ui/dialogs.py` | `LoginDialog`, `OpenShiftDialog`, `CloseShiftDialog`, `PaymentDialog`, `ReceiptDialog`, `RefundDialog`, `parse_som`. |
| `ui/products_dialog.py` | `ProductsDialog`, `ProductFormDialog`, `parse_barcodes`; `UNITS = ["dona", "kg", "litr", "metr", "quti", "paket"]`. |
| `ui/users_dialog.py` | `UsersDialog` (faqat egasi), `AddCashierDialog`. |
| `ui/tasks.py` | `BackgroundRunner` (QThreadPool), `SyncRunner` (testlar uchun sinxron). |
| `ui/theme.py` | `apply_theme()`: Fusion uslubi, minimal 11 pt shrift. |

### 5.3 Ishga tushirish

Ishga tushirish oqimi (`__main__.main`): QApplication → `apply_theme` → `DesktopConfig.from_env()` → lokal baza papkasini yaratish → `LocalStore(path, key=get_or_create_db_key())` → `run_login(local)` (bekor qilinsa chiqadi) → `MqttSync(get_or_create_store_key(), device_id=local.device_id(), ...)` → `PosWindow(...)`, `show()`, `start()` → `app.exec()` → `mqtt.stop()`, `local.close()`.

Linux (bash), `desktop/README.md` va CI bo'yicha:

```
cd omborai/desktop
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export OMBORAI_PRINTER_HOST=192.168.1.50   # ixtiyoriy
python -m omborai_desktop
```

Konsol skripti: `omborai-desktop` (`pyproject.toml` `[project.scripts]`).

Windows (PowerShell): `py -3.12 -m venv .venv`, `.venv\Scripts\activate`, `pip install -e ".[dev]"`, `$env:OMBORAI_PRINTER_HOST = "..."`, `python -m omborai_desktop`. UNVERIFIED: Windows'da hech qanday buyruq ishga tushirilmagan.

`desktop/README.md` dagi `export OMBORAI_API_URL=...` qatori kodda hech narsa o'qimaydi — o'chirib tashlash kerak (14-bo'lim).

### 5.4 Env o'zgaruvchilari

| Nom | Standart | Qayerda | Izoh |
|---|---|---|---|
| `OMBORAI_PRINTER_HOST` | yo'q (None) | `config.py` | Bo'sh qiymat yo'q hisoblanadi. Berilmasa "Chop etish" tugmasi ko'rinmaydi. ESC/POS, TCP 9100. |
| `OMBORAI_RECEIPT_WIDTH` | `32` | `config.py` | Butun son. Noto'g'ri qiymatda ishga tushirish xato beradi. |
| `OMBORAI_LOCAL_DB` | `~/.omborai/local.db` | `config.py` | Shifrlangan lokal baza yo'li. |
| `OMBORAI_MQTT_HOST` | `broker.hivemq.com` | `config.py` | MQTT broker. |
| `OMBORAI_MQTT_PORT` | `8883` | `config.py` | Butun son. |
| `OMBORAI_MQTT_TLS` | `"1"` | `config.py` | TLS faqat qiymat aniq `"1"` bo'lsa yoqiladi. `"true"` yozilsa TLS jim o'chadi. |
| `OMBORAI_STORE_KEY` | yo'q | `security.py` | 32 baytli do'kon kaliti (hex). Berilsa keyring o'rniga shu ishlatiladi. Sir hisoblanadi. |
| `QT_QPA_PLATFORM` | `offscreen` | `tests/conftest.py` (`setdefault`) | Testlar uchun. |

Kodda o'qilmaydi: `OMBORAI_API_URL` (faqat `desktop/README.md` da).

### 5.5 Keyring (OS xavfsiz xotirasi)

- Xizmat nomi: `omborai-desktop`.
- Hisob `local-db-key`: SQLCipher kaliti, tasodifiy 256 bit, 64 hex belgi. Birinchi ishga tushirishda yaratiladi.
- Hisob `mqtt-store-key`: do'kon kaliti, 32 bayt, hex. `OMBORAI_STORE_KEY` berilsa u ustun.
- Qiymatlar hujjatda yo'q.
- Linux'da keyring Secret Service talab qiladi (UNVERIFIED: sinalmagan).

### 5.6 Testlar

Fayllar va test funksiyalari soni (tekshirildi):

| Fayl | Soni | Tavsif |
|---|---|---|
| `test_auth.py` | 6 | Parol xeshi (round-trip, tuz), juftlash kodi, LWW user, nofaol user, snapshot orqali do'kon bootstrap. |
| `test_encryption.py` | 6 | SQLCipher diskda shifrlangan, noto'g'ri kalit rad etiladi, kalit formati, kalit bir marta yaratiladi. |
| `test_money_cart.py` | 8 | Pul formati va yaxlitlash, savat jami, chegirma, sotuv payload. |
| `test_mqtt_sync.py` | 7 | Envelope round-trip, noto'g'ri kalit/mavzu/buzish rad etiladi, mavzu deterministik, kalit uzunligi. 3 ta broker testi (ikki qurilma, boshqa kalit, snapshot bootstrap) faqat `mosquitto` PATH'da bo'lsa ishlaydi. |
| `test_pos_ui.py` | 9 | `PosWindow` oqimlari (qtbot, soxta MQTT): savdo, smena, qaytarish, katalog, snapshot. |
| `test_receipt_escpos.py` | 4 | Chek kengligi, o'rash, ESC/POS baytlari, miqdor formati. |
| `test_store_ops.py` | 9 | Operatsiyalarni qo'llash, qaytarish bir marta, smena, tovar LWW, snapshot, outbox. |
| `test_users.py` | 4 | Kassir qo'shish, dublikat login, faollashtirish/o'chirish, egasini himoya qilish. |
| **Jami** | **53** | `def test_` bo'yicha statik hisob. |

Buyruqlar (CI bilan bir xil): `pytest -q`, `ruff check .`, `mypy omborai_desktop --ignore-missing-imports`. `pyproject.toml`: `testpaths = ["tests"]`, `qt_api = "pyside6"`; ruff `line-length = 110`, `target-version = "py312"`, tanlov `E, F, I, B, UP, S`.

Natija: 13-bo'lim.

### 5.7 Cheklovlar (kodda yo'q)

- Tovar kirimi yoki qoldiq tuzatish UI'si yo'q. `movement` operatsiyasi `apply` qilinadi (`store.py`), lekin hech bir ekran uni yaratmaydi. Yangi tovarga boshlang'ich qoldiq kiritib bo'lmaydi.
- Juftlash kodini ko'rsatish ekrani yo'q. `ui/login.py` dagi `pairing_code()` ni hech kim chaqirmaydi (desktop'dan yangi qurilma uchun kod chiqarilmaydi).
- Fiskal chek yo'q (placeholder bor).
- Bo'lib to'lash yo'q: `Cart.to_sale_payload` ro'yxatni qabul qiladi, lekin `PaymentDialog` bitta usul taklif qiladi (`cash`, `card`, `click`, `payme`).
- Savdolar jurnali, hisobotlar, cheklarni qayta chop etish, smena tarixi yo'q.
- Kam qoldiq ogohlantirishi yo'q: `min_stock` saqlanadi va ko'rsatiladi, lekin qoldiq bilan solishtirilmaydi.
- Menyu paneli, chiqish (logout), parolni o'zgartirish, foydalanuvchini tahrirlash, rol o'zgartirish yo'q (`user` operatsiyasi protokolda bor, UI yo'q).
- Chop etish faqat tarmoq printeri orqali; USB, Bluetooth, kassa yashigi yo'q.
- Oflayn navbat: `outbox` jadvali va `pending_count` bor; "Sinxron" holati ko'rsatiladi.

## 6. Mobil ilova

### 6.1 Arxitektura

- **Qatlamlar:** `AppSession` (`lib/src/app_session.dart`, `ChangeNotifier`) — barcha yozish operatsiyalari, sessiya, smena, MQTT va outbox holati shu yerda. `LocalDb` (`lib/src/offline/local_db.dart`) — SQLCipher jadvallari va op qo'llash. `MqttSync` (`lib/src/sync/mqtt_sync.dart`) — `mqtt_client` o'rami.
- **Ma'lumot kaliti:** `DbPasswordStore` — `FlutterSecureStorage` kaliti `db_password` (birinchi ishga tushirishda 32 tasodifiy bayt, base64url). Baza fayli: `omborai_local.db` (`getDatabasesPath()` ostida), `main.dart` da ochiladi.
- **Do'kon kaliti:** `StoreKeyStore` — `store_key` (hex). Birinchi qurilma yaratadi; boshqalari juftlash kodi bilan kiritadi.
- **Tema:** Material 3; `colorSchemeSeed` yorug' `0xFF0F766E`, tungi `0xFF2DD4BF`; `ThemeMode.system`.
- **Sinxron davri:** `syncInterval = 15 s` (`app_session.dart:85`), `Timer.periodic` (`:265`). Ilova ochiq bo'lsa ishlaydi; fon rejimi (WorkManager) yo'q.
- **Native Kotlin skaner:** `MainActivity.kt` `BarcodeScannerPlugin` ni ulaydi. Platform view `uz.omborai/scanner`; hodisalar kanali `uz.omborai/scanner/events/<viewId>`. CameraX (orqa kamera, `ImageAnalysis` `KEEP_ONLY_LATEST`) va ML Kit: EAN-13, EAN-8, UPC-A, UPC-E, CODE-128, CODE-39, QR. Bir xil kod 2000 ms ichida qayta yuborilmaydi. Loyihaning o'z MethodChannel'i yo'q.

### 6.2 Ekranlar va navigatsiya

| Ekran (fayl) | Vazifa | Qayerdan ochiladi |
|---|---|---|
| `LoginScreen` (`login_screen.dart`) | Birinchi ishga tushirish: do'kon yaratish yoki juftlash kodi; keyin login/parol. | `main.dart` (`_Bootstrap`, `restore()` false bo'lsa). |
| `HomeScreen` (`home_screen.dart`) | Bosh menyu: smena ochish/yopish, sinxron holati, navigatsiya, chiqish. | `main.dart` (`restore()` true bo'lsa), chiqishda `pushAndRemoveUntil`. |
| `PairingScreen` (`pairing_screen.dart`) | Do'kon juftlash kodini ko'rsatish va nusxalash; kodni kiritib qo'shilish. | Bosh menyu, kalit ikonkasi (`home_screen.dart:105`). |
| `SaleScreen` (`sale_screen.dart`) | Kassa: qidiruv, skaner, savat, to'lov usuli, `submitSale`. | Bosh menyu "Kassa" (faqat do'kon bor va smena ochiq). |
| `ScannerScreen` (`scanner_screen.dart`) | Shtrix-kod skaneri (platform view) va qo'lda kiritish. Kod bilan `pop`. | `SaleScreen` (`sale_screen.dart:68-70`). |
| `ProductsScreen` (`products_screen.dart`) | Tovarlar ro'yxati, qidiruv. | Bosh menyu "Tovarlar" (do'kon bor bo'lsa). |
| `ProductFormScreen` (`product_form_screen.dart`) | Tovar qo'shish, tahrirlash, o'chirish (`product` operatsiyasi). | `ProductsScreen` (FAB va element bosilganda). |
| `RefundsScreen` (`refunds_screen.dart`) | Oxirgi cheklar, qaytarish tugmasi va tasdiqlash dialogi. | Bosh menyu "Qaytarish" (do'kon bor bo'lsa). |
| `UsersScreen` (`users_screen.dart`) | Foydalanuvchilar ro'yxati, kassir qo'shish (`_AddCashierDialog`), faollashtirish/o'chirish. | Bosh menyu, faqat egasi (`session.isOwner`). |

Muhim: login, do'kon yaratish yoki juftlash muvaffaqiyatli bo'lgandan keyin hech qanday marshrut ochilmaydi. `login_screen.dart` da `Navigator` yo'q; `_run` faqat `busy` holatini boshqaradi. `main.dart` dagi `_Bootstrap` esa faqat bir marta, ilova ishga tushganda `restore()` ni tekshiradi. Natija: yangi kirgan foydalanuvchi ilovani qayta ochmaguncha `LoginScreen` da qoladi. Kod o'qish bilan aniqlangan; qurilmada tekshirilmagan (UNVERIFIED).

Ko'rinish qoidalari (`home_screen.dart`): "Kassa" faqat `session.hasStore && session.shiftOpen` bo'lsa yoqiladi (`:166`); "Foydalanuvchilar" faqat `isOwner` (`:186`); "Qaytarish" va "Tovarlar" — `hasStore` (`:177`, `:199`). Qaytarish ekranida rol tekshiruvi yo'q (14-bo'lim).

### 6.3 Ma'lumot modeli

9-bo'limga qarang (lokal jadvallar). Desktop va mobil sxemasi bir xil.

### 6.4 Build

- **Flutter SDK:** `/opt/flutter` da Flutter 3.47.7 (stable), Dart 3.13.5 (tekshirildi: `/opt/flutter/bin/cache/flutter.version.json`, `/opt/flutter/bin/cache/dart-sdk/version`). `flutter` PATH'da yo'q.
- **Lock talablari:** `pubspec.yaml` — `environment.sdk: ^3.13.5`; `pubspec.lock` — Dart `>=3.13.5 <4.0.0`, Flutter `>=3.38.4`.
- **Versiya:** `0.1.0+1` (`pubspec.yaml`). `local.properties` da `flutter.versionName=0.1.0`, `flutter.versionCode=1`.
- **Android:** `namespace` va `applicationId` = `uz.omborai.omborai_mobile`; `minSdk = 26`; `targetSdk = flutter.targetSdkVersion`; `compileSdk = flutter.compileSdkVersion` (Flutter default, 36 — manifest'da ko'rinmaydi, UNVERIFIED); `ndkVersion = flutter.ndkVersion` (28.2.13676358); Java/Kotlin 17 (`app/build.gradle.kts`).
- **Gradle:** AGP `com.android.application` 9.1.0, Kotlin `org.jetbrains.kotlin.android` 2.4.0, Gradle 9.3.1 (`gradle-wrapper.properties`). `gradlew` va `gradle-wrapper.jar` git'da; `gradlew.bat` git'da yo'q (`mobile/android/.gitignore`).
- **Release imzosi:** `buildTypes.release.signingConfig = signingConfigs.getByName("debug")` (`app/build.gradle.kts:37`). Release debug kalit bilan imzolanadi. TODO: release imzo konfiguratsiyasi kerak.
- **Manifest ruxsatlari:** `CAMERA`, `INTERNET`; `android.hardware.camera` `required="false"`. Debug overlay (`src/debug/AndroidManifest.xml`): `usesCleartextTraffic="true"` — faqat debug, izohi LAN HTTP sinovi uchun deydi, lekin ilova hozir HTTP ishlatmaydi (eskirgan).
- **Native kutubxonalar:** CameraX 1.4.2 (core, camera2, lifecycle, view), `androidx.lifecycle-runtime` 2.8.7, ML Kit barcode-scanning 17.3.0 (`app/build.gradle.kts` bo'yicha scout; UNVERIFIED: shu tekshiruvda o'qilmagan).
- **Android SDK (shu muhitda):** `/opt/android-sdk/platforms` da `android-34`, `android-35`, `android-36`, `android-37.0`; `/opt/android-sdk/ndk/28.2.13676358`.
- **Build natijalari (`mobile/build/app/outputs/flutter-apk/`, gitignore'da):** `app-release.apk` (82 390 135 bayt, 2026-10-10 14:04), `app-debug.apk` (222 558 564 bayt, 07:33), `app-arm64-v8a-release.apk` (29 894 636), `app-armeabi-v7a-release.apk` (23 995 018), `app-x86_64-release.apk` (32 909 363) — har biri `.sha1` bilan. Fayllar mavjudligi tekshirildi; qanday buyruq bilan yig'ilgani UNVERIFIED (ehtimol `flutter build apk --release`, `--debug`, `--release --split-per-abi`).
- **Build buyruqlari (CI):** `flutter pub get`, `flutter build apk --debug`.
- **Lokal fayllar (gitignore'da, yangi muhitda qayta yaratiladi):** `mobile/android/local.properties` (`flutter.sdk`, `sdk.dir`, `flutter.buildMode`, `flutter.versionName`, `flutter.versionCode` kalitlari), `mobile/.dart_tool/`, `mobile/build/`, `mobile/android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java` (Flutter generatsiya qiladi), `omborai_mobile.iml`, `.idea/`.

### 6.5 Testlar

`mobile/test/` (tekshirildi):

| Fayl | `test()` | `testWidgets()` | `group()` | Izoh |
|---|---|---|---|---|
| `auth_test.dart` | 4 | 0 | 0 | PBKDF2 — Python `hashlib` bilan bir xil natija (vektor: 8.4-bo'lim). |
| `cashier_test.dart` | 5 | 0 | 0 | Kassir oqimi. |
| `crypto_test.dart` | 4 | 0 | 0 | Desktop bilan kross-platforma test vektori (8-bo'lim). |
| `local_db_test.dart` | 6 | 0 | 0 | Lokal baza. |
| `login_screen_test.dart` | 0 | 2 | 0 | Bo'sh do'konda taklif; do'kon bor, bo'sh login xatosi. |
| `money_cart_test.dart` | 6 | 0 | 0 | Pul va savat. |
| `mqtt_sync_test.dart` | 1 | 0 | 0 | Haqiqiy broker integratsiyasi; `OMBORAI_TEST_MQTT_PORT` berilmasa o'tkazib yuboriladi (`:94`). |
| `users_db_test.dart` | 4 | 0 | 1 | Foydalanuvchilar bazasi. |
| **Jami** | **30** | **2** | **1** | 32 ta deklaratsiya. |

`mocktail` `dev_dependencies` da, lekin `test/` va `lib/` da hech qayerda import qilinmagan. Testlar host'da `sqflite_common_ffi` orqali ishlaydi (qurilma kerak emas).

Buyruqlar: `flutter analyze`, `flutter test`. Natija 13-bo'limda.

### 6.6 Cheklovlar

- iOS yo'q (rejadan chiqarilgan).
- Skaner faqat Android (iOS uchun alohida native plugin kerak — `mobile/README.md`).
- Sinxron faqat ilova ochiq paytida; WorkManager yo'q.
- Login'dan keyin navigatsiya yo'q (6.2).
- Qaytarish ekranida rol cheklovi yo'q.
- Eskirgan hujjat: `mobile/README.md` `lib/src/api/` (HTTP klient), `OMBORAI_API_URL`, "Android SDK platform 35" va API testlarini tasvirlaydi — bularning hech biri joriy kodda yo'q (`lib/src/api/` papkasi yo'q).
- Kotlin skaner haqiqiy qurilmada tekshirilmagan (UNVERIFIED).

## 7. Backend va infra

### 7.1 Holati

- **Backend:** FastAPI (`app/main.py`, `create_app()`), SQLAlchemy 2.0 async + asyncpg, Alembic, PostgreSQL 16 (RLS bilan tenant izolyatsiyasi), argon2 parollar, JWT (HS256).
- **Klientlar ishlatmaydi:** desktop `pyproject.toml` (PySide6, sqlcipher3-binary, keyring, paho-mqtt, cryptography) va mobil `pubspec.yaml` (cryptography, decimal, flutter_secure_storage, mqtt_client, path, permission_handler, sqflite_sqlcipher, uuid) da HTTP klient kutubxonasi yo'q. Klient manba kodida `/v1/` yo'llari topilmadi (eski `.pyc` va `mobile/build` ichidagi qoldiqlardan tashqari, UNVERIFIED).
- **Tizimda:** `backend/app/api/sync.py` (REST sinxron, `op_id` va `sync_ops` jadvali) — klient unga ulanmaydi.
- **Hujjatlardagi eski REST sinxron tavsifi** (`README.md:78`, `docs/reja.md:66-67`: `idempotency_key`, `change_seq`) — kod bilan mos emas.

### 7.2 Endpointlar (32 operatsiya: 2 ildiz + 30 `/v1`)

OpenAPI (`shared/openapi.json`) bilan mos (23 path, 32 operatsiya — tekshirildi). Rollar — kod o'qish bilan (ishga tushirilmagan).

- Ildiz: `GET /healthz` (liveness), `GET /readyz` (`SELECT 1`, DB xato bo'lsa 503).
- Auth: `POST /v1/auth/register` (tenant, do'kon va egasini yaratadi), `POST /v1/auth/login`, `POST /v1/auth/refresh` (rotatsiya).
- Me va do'konlar: `GET /v1/me`; `GET /v1/stores`; `POST /v1/stores` (owner, manager).
- Katalog: `GET|POST /v1/categories`; `GET|POST /v1/suppliers`; `GET|POST /v1/products` (POST: owner, manager, warehouse); `GET /v1/products/by-barcode/{code}`; `GET|PATCH|DELETE /v1/products/{product_id}` (DELETE — yumshoq o'chirish, owner, manager).
- Qoldiq: `GET|POST /v1/stock/movements` (POST: faqat `adjustment`, `writeoff`; owner, manager, warehouse); `GET /v1/stock/balances`.
- Kirim: `GET|POST /v1/purchases` (POST: owner, manager, warehouse).
- Smena: `POST /v1/shifts` (owner, manager, cashier; ochiq smena bo'lsa 409); `GET /v1/shifts/current`; `POST /v1/shifts/{shift_id}/close`.
- Savdo: `GET|POST /v1/sales` (POST: owner, manager, cashier; idempotent — bir xil id qayta yuborilsa 200); `GET /v1/sales/{sale_id}`; `POST /v1/sales/{sale_id}/refund` (owner, manager).
- Sinxron: `POST /v1/sync/push` (operatsiyalar, max 100 ta); `GET /v1/sync/pull` (keyset kursorlar, `limit` default 200, max 500, 3 soniyalik `HORIZON`).

Kodda yo'q, lekin rejada bor: `/customers`, `/debts`, `/reports`, `/subscriptions`, `/webhooks/click`, `/webhooks/payme`.

### 7.3 Ma'lumot modeli (PostgreSQL, 17 jadval)

`tenants`, `users`, `stores`, `memberships`, `refresh_tokens`, `categories`, `products`, `product_barcodes`, `suppliers`, `purchases`, `purchase_items`, `stock_movements` (append-only: `omborai_app` roli UPDATE/DELETE huquqiga ega emas), `shifts` (`uq_open_shift_per_store` qisman unikal indeks), `sales`, `sale_items`, `payments`, `sync_ops`. RLS 14 ta jadvalda yoqilgan; `tenants`, `users`, `refresh_tokens` da yo'q.

Migratsiyalar: `0001_init` (tenant, user, store, membership, refresh token, `omborai_app` roli), `0002_catalog_stock`, `0003_sales` (`sale_number_seq` START 1000), `0004_sync` (`sales.updated_at`, `sync_ops`, indekslar). Zanjir chiziqli, head = `0004_sync`. Haqiqiy PostgreSQL'da `alembic upgrade head` ishga tushirilmagan (UNVERIFIED).

### 7.4 Qayta ishlatish imkoniyati

- Qayta ishlatish mumkin: tenant va RLS modeli (`db.py`, `deps.py`), JWT va refresh rotatsiya (`security.py`, `api/auth.py`), tovar va qoldiq ledger (`services/stock.py`, `FOR UPDATE` qulfi, manfiy qoldiq himoyasi), savdo narxini serverda hisoblash (`services/sales.py`), smena yopish hisoboti, OpenAPI shartnomasi.
- Hozircha foydalanilmaydi. Serversiz qarordan keyin backend klientlar tomonidan chaqirilmaydi.
- Kelajakda kerak bo'lishi mumkin: hisobotlar, qarz daftari, Click/Payme, fiskal integratsiya (markaziy hakam, nazorat), ko'p qurilma konflikt tekshiruvi. Bu modullar hali yozilmagan.
- Eslatma: backend'dagi `sync` modeli (`op_id`, per-table `updated_at` kursor) MQTT modeli bilan bir xil emas.

### 7.5 Ishga tushirish

Lokal (`README.md`, kod bilan mos; UNVERIFIED: sinalmagan):

```
cd omborai/backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export OMBORAI_MIGRATION_URL=postgresql+asyncpg://<superuser>:<parol>@localhost:5432/omborai
export OMBORAI_DATABASE_URL=postgresql+asyncpg://<app_role>:<parol>@localhost:5432/omborai
alembic upgrade head
uvicorn app.main:app --reload
```

Hujjatlar: `http://127.0.0.1:8000/docs` va `/openapi.json` faqat `OMBORAI_ENV` `prod` bo'lmaganda yoqiladi (standart: `dev`).

Docker (`infra/`): `cp .env.example .env`, qiymatlarni almashtirish, `docker compose up -d --build`. Xizmatlar: `postgres` (16-alpine, host portsiz), `redis` (7-alpine, `--requirepass`, host portsiz), `migrate` (`alembic upgrade head`, bir martalik), `api` (`expose: 8000`, faqat ichki), `caddy` (80/443). Majburiy o'zgaruvchilar (nomi bilan): `POSTGRES_PASSWORD`, `OMBORAI_APP_PASSWORD`, `REDIS_PASSWORD`, `OMBORAI_JWT_SECRET`. Ixtiyoriy: `OMBORAI_ENV` (standart `prod`), `OMBORAI_DOMAIN` (standart `localhost`). UNVERIFIED: `docker compose` va `docker build` bu muhitda ishga tushirilmagan.

Caddy: `{$OMBORAI_DOMAIN:localhost}` manzili, avtomatik HTTPS, `reverse_proxy api:8000` (`X-Forwarded-Proto`), xavfsizlik sarlavhalari (HSTS, nosniff, DENY, no-referrer), JSON access log. ACME va TLS xulq-atvori UNVERIFIED.

Postgres init: `infra/postgres/init/01-app-role.sh` — `omborai_app` roli (LOGIN, NOSUPERUSER, NOBYPASSRLS) birinchi ishga tushirishda yaratiladi. Oddiy `CREATE ROLE` (IF NOT EXISTS yo'q), shuning uchun u migratsiyadan oldin bo'lishi kerak.

Dockerfile: `python:3.12-slim`, `pip install .` (dev extras yo'q), `USER omborai` (uid 10001), healthcheck `/healthz`, CMD `uvicorn app.main:app ... --proxy-headers`. `FORWARDED_ALLOW_IPS` berilmagan; uvicorn'ning standart ishonchli proxy qiymati Caddy konteyneri uchun yetarli emasligi mumkin (UNVERIFIED: image'dagi uvicorn versiyasi tekshirilmagan).

Redis: `OMBORAI_REDIS_URL` `config.py:18` da e'lon qilingan, lekin hech qayerda o'qilmaydi; compose uni `api` ga uzatadi. Redis kodda ishlatilmaydi.

### 7.6 Testlar

`backend/tests/` — 47 test funksiyasi (tekshirildi): `test_health.py` 2, `test_auth.py` 9, `test_catalog_stock.py` 10, `test_sales.py` 12, `test_sync.py` 10, `test_tenant_isolation.py` 4. Yordamchilar: `conftest.py`, `helpers.py`, `__init__.py`.

`conftest.py` haqiqiy PostgreSQL'da ishlaydi (mock emas): sessiya boshida `omborai_test` bazasini qayta yaratadi (superuser URL kerak — env nomi `OMBORAI_TEST_ADMIN_URL`), `alembic upgrade head` ishga tushiradi, `omborai_app` ga LOGIN beradi. Har testdan keyin jadvallar tozalanadi. `pytest-asyncio` `asyncio_mode=auto`. Natija 13-bo'limda.

## 8. MQTT protokoli va shifrlash

Manba: `docs/sync-mqtt.md` va kod (`desktop/omborai_desktop/sync/crypto.py`, `mobile/lib/src/sync/crypto.dart`).

### 8.1 Kalit va mavzu

- `K` — do'kon kaliti, 32 bayt tasodifiy. Qurilmalar o'rtasida juftlash kodi orqali o'tadi.
- Mavzu: `topic = "omborai/v1/" + hex(HKDF-SHA256(K, salt, info=b"topic", L=16)) + "/ops"`. Desktop: `salt=None` (RFC 5869 bo'yicha 32 nol bayt). Mobil: salt sifatida 32 nol bayt. Ikkalasi bir xil natija beradi (tasdiqlangan test vektori).
- Mavzu uzunligi: `omborai/v1/` + 32 hex + `/ops`.

### 8.2 Xabar formati (broker ko'radigan bayt)

Envelope (JSON, UTF-8):

```json
{"v": 1, "n": "<base64, 12 bayt nonce>", "c": "<base64, shifrlangan matn || 16 bayt GCM tegi>"}
```

- Shifr: AES-256-GCM, kalit `K`, nonce tasodifiy 12 bayt, AAD = mavzu nomining UTF-8 baytlari.
- Ochiq matn (shifrdan keyin, JSON):

```json
{"op_id": "<uuid>", "type": "<tur>", "device": "<uuid>", "ts": "<ISO 8601>", "store_id": "<uuid>", "payload": {}}
```

- QoS 1 (desktop: `publish(qos=1)`, `wait_for_publish` 10 s; mobil: `MqttQos.atLeastOnce`). Desktop `clean_session=False`. Mobil: `keepAlivePeriod = 30`, `autoReconnect = true`, client id `omborai-<deviceId>`.

### 8.3 Qabul qilish qoidalari

1. Envelope'ni ochish. `v != 1` yoki istalgan dekodlash/tekshiruv xatosi — xabar jim tashlanadi (desktop: `DecryptionError`, log; mobil: `DecryptionException`).
2. `device == o'z deviceId` bo'lsa tashlanadi.
3. `type == "snapshot_request"` — `on_request` (desktop) / `onRequest` (mobil). Qo'llanmaydi, dedupe yozilmaydi.
4. Qolgan hammasi `apply_op` ga beriladi. Dedupe `applied_ops` jadvali orqali, qo'llash bilan bir tranzaksiyada.

### 8.4 Test vektori (kross-platforma)

Faqat test uchun kalit (ishlab chiqarishda ishlatilmaydi):

- `K` = bayt `0x00` … `0x1f` (hex `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f`).
- Kutilgan mavzu: `omborai/v1/b562beb66f2a7f7fe4d0830bfd2f84c4/ops`.
- Desktop tomonidan shifrlangan envelope (mobil testi ochishi kerak):

```json
{"v": 1, "n": "VHd/YGJnKvfXuNkC", "c": "hqgeCKIhB8Rzp8FnaqbdoVtEueF1vJaZ9AaAjm5GCWPB5/notg3B"}
```

- Ochilgan ochiq matn: `{"hello":"dunyo","n":1}` (23 bayt). `c` 39 bayt (23 + 16 teg). Nonce 12 bayt.
- Shu sessiyada qayta hisoblandi (Python `cryptography` 50.0.1): mavzu mos, ochiq matn mos, AAD noto'g'ri bo'lsa `InvalidTag`.
- Manzil: `mobile/test/crypto_test.dart` (4 test: mavzu, vektorni ochish, round-trip va noto'g'ri kalit/AAD rad etish, kalit uzunligi). Desktop'da bu vektorga teng test yo'q — faqat round-trip (`test_mqtt_sync.py`).
- Parol xeshi vektori: `mobile/test/auth_test.dart` da (tuz 16 nol bayt, PBKDF2-HMAC-SHA256, 100 000 iteratsiya, 32 bayt natija; Python `hashlib` bilan solishtirilgan). Qiymat va parol matni bu hujjatda keltirilmagan. Desktop `test_auth.py` da belgilangan vektor yo'q (faqat round-trip). `docs/sync-mqtt.md` ikkala testda ham vektor bor deydi — bu noto'g'ri.

### 8.5 Operatsiya turlari

`op_id` qoidasi: deterministik `op_id` qayta yuborishda dublikatni to'xtatadi.

| `type` | `op_id` | `payload` | Qo'llash ta'siri |
|---|---|---|---|
| `sale` | `payload.id` (sotuv UUID) | `{id, store_id, number, shift_id, items: [{product_id, qty, product_name, unit, unit_price, line_total}], discount, subtotal, total, payments: [{method, amount}], created_at}` | Har item uchun `movements` yozuvi `<op_id>:<product_id>`, `qty` manfiy, `kind = "sale"`. `sales` ga `INSERT OR IGNORE`, status `completed`. Qo'llashda qoldiq tekshirilmaydi (klient yuborishdan oldin tekshiradi). |
| `refund` | `refund:<sale_id>` | `{sale_id}` | Sotuv bor va `completed` bo'lsa: `refund:<sale_id>:<product_id>` yozuvlari, `qty` musbat, `kind = "sale_return"`; sotuv `refunded`. Aks holda hech narsa qilinmaydi, lekin `op_id` baribir yoziladi. |
| `shift_open` | smena UUID | `{shift_id, opening_cash}` | Do'konda ochiq smena bo'lsa e'tiborsiz. Aks holda `opened_at = op.ts`. |
| `shift_close` | operatsiya UUID | `{shift_id, closing_cash, summary}` | `closed_at = op.ts`, `closing_cash`, `summary` JSON; faqat `closed_at IS NULL` bo'lsa. |
| `movement` | operatsiya UUID | `{product_id, qty, kind}` | `movements` yozuvi, `id = op_id`, `kind` payload'dan. Backend konstantasi: `receipt`, `sale`, `sale_return`, `adjustment`, `writeoff`. UI bu operatsiyani yaratmaydi. |
| `product` | operatsiya UUID | tovar obyekti: `{id, name, unit, sale_price, cost_price, min_stock, barcodes, deleted}` | LWW: saqlangan `updated_ts >= op.ts` bo'lsa e'tiborsiz; aks holda upsert, `updated_ts = op.ts`. O'chirish yumshoq (`deleted: true`). |
| `user` | operatsiya UUID | `{id, login, name, role, salt, pw_hash, active}` | Qo'shish va faollashtirish/o'chirish. LWW (desktop `store.py:460-481`, mobil `local_db.dart:473-500`). |
| `store` | operatsiya UUID | `{name}` | `store_info` ga LWW (`updated_ts >= ts` bo'lsa e'tiborsiz). |
| `snapshot` | yangi UUID | 8.6 ga qarang | Faqat `applied_ops` soni 0 bo'lgan qurilmada qo'llanadi. |
| `snapshot_request` | yangi UUID | `{}` | Hech qachon qo'llanmaydi va `applied_ops` ga yozilmaydi. Outbox'ga emas, to'g'ridan-to'g'ri yuboriladi. |

Mavzu bo'yicha qoidalar: `sale` va `refund` uchun deterministik op_id hamma qurilmada bir xil, shuning uchun ikki qurilmadan qaytarish qoldiqni ikki marta tiklamaydi. Qo'llash qoidasi: qurilma o'z operatsiyasini avval o'zida qo'llaydi, keyin nashr qiladi.

### 8.6 Snapshot shakli

`payload`:

- `store`: `{name, updated_ts}` yoki `null`.
- `users`: `users` jadvali qatorlari (`id, store_id, login, name, role, salt, pw_hash, active, updated_ts`). Parol xeshi va tuz shu yerda, faqat shifrlangan holda uzatiladi.
- `products`: `{id, name, unit, sale_price, cost_price, min_stock, barcodes, deleted, updated_ts}`. O'chirilganlar ham kiradi.
- `balances`: `{product_id: qty}` (qator yig'indisi; noldan farqli, UNVERIFIED: to'liq filtr kodi o'qilmagan).
- `open_shift`: `shifts` qatori yoki `null`.
- Sotuv tarixi kiritilmaydi.

Qo'llash: `store`, `users`, `products` — o'z `updated_ts` bo'yicha LWW; har bir balans `snapshot:<op_id>:<product_id>` `kind = "snapshot"` yozuvi bo'ladi; ochiq smena `INSERT OR IGNORE`.

### 8.7 So'rov va javob oqimi

- Yangi qurilma (`applied_ops` = 0) ulanganda va har 15 soniyalik tekshiruvda `snapshot_request` yuboradi. Desktop: `refresh_interval_ms = 15000`, 60 soniyalik cheklov (`main_window.py:54`, `:581`, `:615`). Mobil: `syncInterval = 15 s`, 60 soniyalik bayroq (`app_session.dart:338`).
- Javob beradi: `applied_ops` > 0 bo'lgan har bir qurilma (`main_window.py:623`). Javob outbox'ga emas, to'g'ridan-to'g'ri yuboriladi; yuborish xatolari e'tiborsiz qoldiriladi.
- Bir nechta snapshot kelishi mumkin; birinchisi qo'llanadi, keyin qurilmada `applied_ops` > 0 bo'ladi va qolganlari rad etiladi.
- Ulanish muammosi: snapshot bitta xabar sifatida; bo'lak-bo'lak uzatish yo'q.

### 8.8 Outbox va ishonchlilik

- Har operatsiya avval lokal qo'llanadi, keyin yuboriladi yoki navbatga qo'yiladi (`main_window.py:218-222`, `app_session.dart:284-286`).
- Desktop navbat: `pending_ops(limit=50)`, `created_at, op_id` tartibida.
- Mobil `flushOutbox` yuborilgan qatorni PUBACK kutmasdan o'chiradi (kod o'qish; UNVERIFIED: qurilmada tekshirilmagan). Desktop `send` broker tasdig'ini 10 soniya kutadi.
- Sotuvdan oldin qoldiq tekshiruvi klientda (desktop `main_window.py:480-488`, mobil `app_session.dart:403-410`; kod o'qish).
- Broker darajasida yetkazish kafolati yo'q (ommaviy broker, saqlash yo'q). Qayta yuborish va dedupe bilan qisman qoplanadi.

### 8.9 Ma'lum protokol kamchiliklari

- `ts` formati ikki platformada har xil: desktop `datetime.now(UTC).isoformat()` → `...+00:00` (mikrosekund); mobil `DateTime.now().toUtc().toIso8601String()` → `...Z`. LWW xom satr bilan solishtiradi (`store.py:452`, `local_db.dart:462`, `:486`).
- LWW tengligi: `ts` teng bo'lsa saqlangan qator g'olib (`>=`). Qaysi qurilma birinchi kelganiga bog'liq; `device` bo'yicha tie-break yo'q.
- Vaqt manbai qurilmaniki (server vaqti yo'q). Soat noto'g'ri bo'lsa LWW noto'g'ri g'olib chiqaradi.
- Do'kon kaliti sizib chiqsa, hamma shifrlangan xabar ochiladi va parol xeshlari taxmin qilinishi mumkin.

## 9. Lokal ma'lumot modeli

Desktop (`offline/store.py`, `SCHEMA`) va mobil (`lib/src/offline/local_db.dart`, v2) jadvallari bir xil ustunlarga ega. Desktop'da versiya pragma yo'q; mobil sqflite `version: 2`, `onUpgrade` faqat `from < 2` uchun `_schemaV2` ni qo'llaydi (yangi versiya uchun yangi shart kerak).

| Jadval | Ustunlar (tur, standart) | Izoh |
|---|---|---|
| `products` | `id` PK TEXT; `name` TEXT; `unit` TEXT; `sale_price` INTEGER (so'm); `cost_price` INTEGER = 0; `min_stock` TEXT = '0'; `barcodes` TEXT = '[]' (JSON); `deleted` INTEGER = 0; `updated_ts` TEXT = '' | Do'konga bog'lanmagan (`store_id` yo'q). Qurilmada bir vaqtda bitta do'kon deb taxmin qilinadi. |
| `movements` | `id` PK; `store_id`; `product_id`; `qty` TEXT (decimal); `kind` TEXT | Indeks `movements_store_product (store_id, product_id)`. Qoldiq = yig'indi. |
| `sales` | `id` PK; `store_id`; `shift_id` (NULL bo'lishi mumkin); `number` TEXT; `status` TEXT; `total` INTEGER; `payload` TEXT (JSON); `created_at` TEXT | Status: `completed`, `refunded`. |
| `shifts` | `id` PK; `store_id`; `opened_at` TEXT; `opening_cash` INTEGER; `closed_at` (NULL); `closing_cash` (NULL); `summary` (NULL, JSON) | Ochiq smena: `closed_at IS NULL`. |
| `outbox` | `op_id` PK; `store_id`; `op` TEXT (JSON); `created_at` TEXT | Yuborilmagan operatsiyalar. |
| `applied_ops` | `op_id` PK | Dedupe jadvali. |
| `sync_state` | `name` PK; `value` TEXT NOT NULL | Kalit-qiymat: `device_id`, `store_id`, `store_name`, `session_user`, `receipt_seq` (kalit nomlari kod bo'yicha; `receipt_seq` desktop `store.py:151` da ham). |
| `store_info` | `store_id` PK; `name`; `updated_ts` = '' | Faqat v2 (mobil) va desktop'da bor. |
| `users` | `id` PK; `store_id`; `login`; `name`; `role`; `salt`; `pw_hash`; `active` INTEGER = 1; `updated_ts` = '' | Indeks `users_store_login (store_id, login)`. Login kichik harfga normallashtiriladi. |

Mobil faqat v1 jadvallarni `_schema` da, v2 jadvallarni `_schemaV2` da yaratadi (`CREATE TABLE IF NOT EXISTS`); v1 jadvallarida `IF NOT EXISTS` yo'q.

Joylashuv: desktop — `OMBORAI_LOCAL_DB` (standart `~/.omborai/local.db`), shifrlangan, kalit keyring'da. Mobil — `omborai_local.db` (`getDatabasesPath()`), kalit `db_password` secure storage'da.

Backend PostgreSQL sxemasi (7.3) bu lokal sxemadan alohida; sinxron qilinmaydi.

## 10. Xavfsizlik modeli va ma'lum zaifliklar

### 10.1 Model

- **Lokal:** baza SQLCipher bilan shifrlangan; kalitlar OS xavfsiz xotirasida (desktop keyring, mobil Android Keystore orqali `FlutterSecureStorage`). Kalitlar fayl yoki repo'da saqlanmaydi.
- **Parollar:** PBKDF2-HMAC-SHA256, 100 000 iteratsiya, 16 bayt tuz, 32 bayt natija (desktop `auth.py`, mobil `auth.dart`). Parol matni saqlanmaydi va yuborilmaydi.
- **Do'kon kaliti (`K`):** qurilmalar orasida qo'lda juftlanadi. Juftlash kodi `store_id:kalit_hex` — kodning o'zi kalit (sir sifatida ishlatilishi kerak; ko'rsatish ekrani hozir faqat mobilda).
- **MQTT:** har xabar AES-256-GCM bilan shifrlanadi, mavzu `K` dan olinadi. Broker mavzu nomini, xabar hajmini va vaqtni ko'radi (metama'lumot).
- **Backend (ishlatilmaydi):** RLS (fail-closed: `app.tenant_id` bo'lmasa hech qator qaytmaydi), `omborai_app` roli (NOSUPERUSER, NOBYPASSRLS), JWT access 15 daqiqa, refresh 30 kun, refresh token'lar SHA-256 xeshi sifatida saqlanadi, qayta ishlatilsa oila bekor qilinadi.

### 10.2 Takrorlangan (tekshirilgan) nuqsonlar

1. **Snapshot poygasi (jiddiy):** qurilma snapshot'dan oldin bitta jonli operatsiya qo'llasa (masalan `store`, `user`, `sale`), `apply_op` keyingi snapshot'ni rad etadi (`store.py:355-356`). Qurilma so'rovni faqat `applied_count() == 0` bo'lganda yuboradi (`main_window.py:581`); bitta jonli op qo'llangach so'rov to'xtaydi. Natija: tovarlar va foydalanuvchilar yo'q, login imkonsiz. Tasdiqlandi (2026-10-11, lokal in-memory `LocalStore`, brokersiz): jonli `store` op qo'llandi (True), keyin snapshot (False), `get_product` = None, `list_users` = [].
2. **Qaytarish divergensiyasi:** qurilma sotuv tarixi yo'q holda snapshot bilan ulansa, keyin `refund` kelsa, `_apply_refund` sotuvni topmaydi va jim qaytadi (`store.py:398-402`), lekin `op_id` yoziladi. Takrorlandi: A sotuvdan keyin 7, qaytargandan keyin 10; D (snapshot sotuvdan keyin olgan) 7 da qoladi, `refund` op `True` qaytaradi, sotuv qatori `None`.
3. **Mobilda login'dan keyin navigatsiya yo'q** (6.2). Kod o'qish; qurilmada UNVERIFIED.
4. **Qaytarish rol bo'yicha cheklanmagan:** desktop `RefundDialog` / `refund_sale` (`main_window.py:105-106, 121, 516-530`) da rol tekshiruvi yo'q (faqat `btn_users` egasi uchun yashiriladi). Mobil `RefundsScreen` (`home_screen.dart:199`) ham egasi tekshiruvisiz. Har qanday kassir istalgan `completed` chekni qaytara oladi.
5. **Narx ishonchi:** sotuv payload'idagi `unit_price`, `line_total`, `total` qurilma tomonidan hisoblanadi; serverda tekshiruv yo'q (`cart.py:92` izohi). Do'kon kaliti bo'lgan istalgan qurilma istalgan narx yuborishi mumkin. Qo'llashda ham tekshiruv yo'q (`_apply_sale`).
6. **Juftlash kodi sir:** `store_id:kalit_hex` ni kim o'qisa, do'konga ulanadi. Ko'rsatish ekrani hozir faqat mobilda; desktop'da chiqaruvchi funksiya chaqirilmaydi.
7. **Desktop: qabul qilishda ishlov berilmagan xatolar:** `open_envelope` faqat `ValueError, KeyError, TypeError, InvalidTag` ni ushlaydi; JSON ildizi ob'ekt bo'lmasa (`envelope.get` `AttributeError`) yoki ochilgan matn JSON bo'lmasa, `_on_message` ushlamaydi (kod o'qish).
8. **Desktop mahsulot formasi:** `unit` `UNITS` ro'yxatida bo'lmasa, tahrirlashda "dona" tanlanadi va "dona" saqlanadi (`products_dialog.py:51-52, 109`). Kod o'qish.
9. **Backend: GET endpointlar do'kon bo'yicha cheklanmagan:** `GET /v1/sales?store_id=`, `GET /v1/stock/balances`, `GET /v1/stock/movements` faqat autentifikatsiya va tenant tekshiradi; a'zolik yoki do'kon scope yo'q (`api/sales.py:91-99`, `api/stock.py:41-65`).
10. **Backend: rol tenant bo'yicha:** `require_roles` foydalanuvchining barcha `memberships` rollarini oladi va `store_id` ni e'tiborsiz qoldiradi (`deps.py`).
11. **Backend: login/refresh tekshiruvi:** `login` birinchi membership'ni `LIMIT 1` bilan tanlaydi, `ORDER BY` yo'q. `refresh` `users.deleted_at` ni tekshirmaydi (`api/auth.py:74-125`). Access token muddati tugaguncha `tid` ishonchli.
12. **Backend RLS:** `ENABLE ROW LEVEL SECURITY` bor, `FORCE ROW LEVEL SECURITY` yo'q — jadval egasi (migratsiya roli) RLS'ni chetlab o'tadi. Ilova `omborai_app` bilan ulanadi (tekshirildi: migratsiyalarda `FORCE` yo'q).
13. **Mobil release imzosi debug kalit bilan:** `app/build.gradle.kts:37`.
14. **Desktop TLS:** `OMBORAI_MQTT_TLS` faqat `"1"` ni qabul qiladi; boshqa qiymat TLS'ni jim o'chiradi (`config.py`).
15. **Public broker:** autentifikatsiya yo'q, metama'lumot ko'rinadi; `MqttSync` da login/parol sozlamasi yo'q (qayta sozlash protokolni o'zgartirmaydi, lekin kod o'zgartiradi).
16. **Backend `--proxy-headers`:** `FORWARDED_ALLOW_IPS` berilmagan (UNVERIFIED ta'siri).

### 10.3 Yaxshi qilingan narsalar

- SQL/PRAGMA: desktop `PRAGMA key` kaliti faqat 64 hex belgi bo'lsa qabul qilinadi (`store.py` `HEX_KEY`).
- Mobil `openEnvelope` har qanday xatoni `DecryptionException` ga aylantiradi.
- Desktop `send` broker tasdig'ini kutadi.
- Backend: `stock_movements` append-only (UPDATE/DELETE huquqi olib tashlangan), qoldiq qulfi (`FOR UPDATE`), `sync_ops` dedupe.

## 11. Git holati va PR

- Git ildizi: `/home/user/Myrep`. `origin` = `https://github.com/JurabekM/Myrep` (fetch va push). Credential'lar URL'da yo'q.
- Joriy branch: `claude/wonderful-dirac-gdu5x2`.
- HEAD: `f422fbe77590a9945cffdfc6754ce810e6796488`. Ish daraxti commit oldidan toza edi; keyin faqat `docs/loyiha-xotira.md` qo'shildi.
- `origin/master`: `20aebd301f32833239f2343772aafab148ef0732`. Branch `master` dan 21 commit oldinda; `git diff --stat origin/master..HEAD`: 152 fayl, +18717 / -0.
- **PR #6** (GitHub REST, tekshirildi): holat `open`, draft emas, birlashtirilmagan, `mergeable_state: clean`. Sarlavha: "OmborAI: serversiz desktop va mobil (MQTT), kassirlar, Faza 0–5". Head `claude/wonderful-dirac-gdu5x2` @ `f422fbe`; base `master` @ `20aebd3`; 21 commit; 152 fayl; +18717 / -0. CI natijasi (check runs) tekshirilmagan (UNVERIFIED).
- `gh pr view` GraphQL orqali ishlamadi (403); REST ishladi — `gh api repos/JurabekM/Myrep/pulls/6`.

Commitlar (eskidan yangiga, `origin/master..HEAD`):

1. `5915618` Faza 0 — loyiha rejasi va dizayn eskizlari
2. `a61ebd4` Faza 1 — fondament (backend skeleti, auth, tenant izolyatsiyasi, CI)
3. `8134543` Faza 2 — tovar, shtrix-kod, kirim va qoldiq ledger'i
4. `d11d584` Faza 3 (backend) — kassa smenasi, savdo, to'lov va qaytarish
5. `a644cad` Faza 3 (desktop) — Python/PySide6 kassa ilovasi
6. `8919e72` Faza 4 (backend) — offline sinxronizatsiya
7. `3abcb9c` sync pull tipini mypy uchun aniqlashtirish
8. `6db98f5` Faza 4 (desktop) — offline rejim va sinxronizatsiya
9. `1121b3b` Faza 5 — mobil ilova (Flutter + native Kotlin skaner)
10. `891dac3` desktop va mobil uchun CI (lint, tip tekshiruvi, testlar, APK)
11. `607283b` README — fazalar holati va papkalar
12. `ddc0f37` MQTT sinxronizatsiya protokoli va xavfsizlik modeli
13. `001cf54` lokal ma'lumotlar shifrlangan holda saqlanadi
14. `cbc227b` reja — foydalanuvchi qarorlari
15. `90c570a` mobil ilova faqat MQTT orqali; tovar formasi
16. `e652983` desktop — savdo, smena, qaytarish va katalog faqat MQTT orqali
17. `b5b6db4` savdo MQTT orqali (broker.hivemq.com), shifrlangan protokol; fiskal — ishlab chiqilmoqda
18. `7fc1ec1` telefon sinovi uchun lokal server qo'llanmasi
19. `8710860` sinov qo'llanmasi — emulyator manzili
20. `9257970` serversiz rejim — login, do'kon va foydalanuvchilar lokal, MQTT orqali sinxron
21. `f422fbe` kassir qo'shish, faollashtirish/o'chirish (faqat egasi)

2–8 raqamli commitlar backend va REST sinxronizatsiya yo'nalishiga tegishli (keyin MQTT bilan almashtirildi); 18–19 — bekor qilingan lokal server va emulyator qo'llanmalari.

Eslatma: `master` (`20aebd3`) ichida `Dehqon Ko'makchi` va boshqa loyihalar bor; OmborAI ning barcha o'zgarishi shu PR'da.

## 12. Lokal muhitda davom ettirish

### 12.1 Talablar

- **Git.**
- **Python 3.12+** (desktop va backend; `requires-python >= 3.12`). Bu muhitda `/usr/bin/python3.12` bor. Windows'da `py -3.12`.
- **Flutter SDK** — stable, Dart >= 3.13.5, Flutter >= 3.38.4 (`pubspec.lock`). Shu muhitda Flutter 3.47.7 `/opt/flutter` da.
- **Android SDK:** platform 36 (compile/target), NDK `28.2.13676358`, build-tools. Shu muhitda `/opt/android-sdk` da platforms 34, 35, 36, 37.0 va NDK 28.2.13676358 bor.
- **JDK 17** (Java/Kotlin 17; CI `temurin 17`). Shu muhitda `/usr/bin/java` bor, versiyasi UNVERIFIED.
- **PostgreSQL 16** (backend va backend testlari uchun).
- **Docker + Compose** (ixtiyoriy; infra uchun).
- **Mosquitto** (MQTT broker testlari uchun). Shu muhitda `/usr/sbin/mosquitto` bor, PATH'da (desktop testi `shutil.which("mosquitto")` ishlatadi).
- **Windows uchun:** PySide6 va `sqlcipher3-binary` wheel'larining mavjudligi UNVERIFIED.

### 12.2 Qadamlar

1. **Clone va branch:**

```
git clone https://github.com/JurabekM/Myrep.git
cd Myrep
git checkout claude/wonderful-dirac-gdu5x2
cd omborai
```

Eslatma: `master` da OmborAI yo'q. Repo katta; faqat `omborai/` kerak bo'lsa sparse checkout ham mumkin (UNVERIFIED: sinalmagan).

2. **Desktop venv:**

```
cd omborai/desktop
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m omborai_desktop
```

Linux'da keyring uchun Secret Service kerak (UNVERIFIED). Desktop'ni ikkinchi qurilma sifatida ishga tushirish uchun birinchi qurilmadan juftlash kodi kerak (12.5).

3. **Mobil:**

```
cd omborai/mobile
flutter pub get
```

`android/local.properties` ni qo'lda yarating (gitignore'da): `flutter.sdk=<Flutter SDK yo'li>`, `sdk.dir=<Android SDK yo'li>`. Keyin: `flutter analyze`, `flutter test`, qurilma ulanib `flutter run` (UNVERIFIED: qurilmada sinalmagan).

4. **APK:**

```
flutter build apk --debug        # CI shu buyruqni ishlatadi
flutter build apk --release      # chiqish: build/app/outputs/flutter-apk/app-release.apk
```

Eslatma: APK fayllar git'da yo'q (root `.gitignore` da `*.apk` va `mobile/.gitignore` da `/build/`). Release debug kalit bilan imzolanadi (10.2-13). Telefonga o'rnatish: `docs/sinov-telefon.md`.

5. **Backend:** 7.5 dagi buyruqlar. Migratsiya oldidan `omborai_app` roli bo'lishi kerak (Docker'da `infra/postgres/init` bajariladi; lokal'da qo'lda yarating).

6. **Testlar:**

```
# desktop (venv ichida)
cd omborai/desktop && pytest -q && ruff check . && mypy omborai_desktop --ignore-missing-imports

# mobil
cd omborai/mobile && flutter analyze && flutter test

# backend (PostgreSQL 16 kerak; OMBORAI_TEST_ADMIN_URL — superuser URL)
cd omborai/backend && pytest -q && ruff check . && ruff format --check . && mypy app
```

7. **MQTT broker testlari:**
   - Desktop: 3 ta broker testi `mosquitto` PATH'da bo'lsa o'zi ishga tushiradi (tasodifiy port, `allow_anonymous true`, `persistence false`, faqat `127.0.0.1`). `mosquitto` yo'q bo'lsa o'tkazib yuboriladi. CI desktop jobida `mosquitto` apt orqali o'rnatiladi.
   - Mobil: `mosquitto` ni `listener <PORT> 127.0.0.1` va `allow_anonymous true` bilan qo'lda ishga tushiring, keyin `OMBORAI_TEST_MQTT_PORT=<PORT> flutter test test/mqtt_sync_test.dart`. Port berilmasa test o'tkazib yuboriladi (HiveMQ'ga ulanmaydi).

### 12.3 Lokal ma'lumot eslatmalari

- Shifrlangan lokal baza (`~/.omborai/local.db` yoki mobil `omborai_local.db`) repo'da yo'q. Kalitlar qurilma va OS foydalanuvchisiga bog'langan — boshqa mashinaga ko'chirib bo'lmaydi.
- Yangi mashinada do'kon uchun: birinchi qurilma (do'kon yaratuvchi) bo'lsangiz, yangi do'kon yarating; mavjud do'konga qo'shilsangiz, boshqa qurilmadan juftlash kodini oling (`<store_id>:<kalit>`).
- `OMBORAI_STORE_KEY` ni fayl yoki repo'ga yozmang; muhit o'zgaruvchisi sifatida bering (qiymat hujjatda yo'q).

### 12.4 Gitignore'da bo'lgan, qayta yaratiladigan fayllar

`*.egg-info/` (desktop, backend), `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `__pycache__/`, `mobile/build/`, `mobile/.dart_tool/`, `mobile/android/.gradle/`, `mobile/android/local.properties`, `mobile/android/gradlew.bat`, `mobile/android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java` (Flutter generatsiyasi), `mobile/omborai_mobile.iml`, `mobile/.idea/`.

### 12.5 Juftlash (ikki qurilma)

1. Birinchi qurilmada: do'kon yaratish (nom, egasi login, parol kamida 8 belgi).
2. Shu qurilmada "Juftlash" ekranini oching (mobil: `PairingScreen`) va kodni nusxalang. Desktop'da bunday ekran yo'q (5.7).
3. Ikkinchi qurilmada "Do'konga qo'shilish" → kodni kiriting. Snapshot kelguncha kuting (10.2-1 ga qarang: agar ikkinchi qurilmada oldin biror amal qilingan bo'lsa, snapshot qabul qilinmaydi).
4. Egasi login/parol bilan kiradi.

## 13. Sinov natijalari

Bu sessiyada bajarilgan tekshiruvlar va natijalari:

| Buyruq yoki tekshiruv | Joy | Natija |
|---|---|---|
| `ruff check . --no-cache` | `omborai/desktop` | All checks passed! |
| `ruff check . --no-cache` | `omborai/backend` | All checks passed! |
| `mypy omborai_desktop --ignore-missing-imports --cache-dir=/dev/null` | `omborai/desktop` | Success: no issues found in 24 source files. Izoh: PySide6, paho-mqtt, keyring o'rnatilmagan, ularning importlari e'tiborga olinmagan — tip tekshiruvi zaif. |
| `pytest -q` (venv: PySide6, sqlcipher3-binary, keyring, paho-mqtt, cryptography, pytest, pytest-qt; `QT_QPA_PLATFORM=offscreen`) | `omborai/desktop` | 53 passed (oxirgi tasdiqlangan yugurish, 2026-10-10). Bog'liqliklar yoki `PYTHONPATH` yetishmasa 4 modul import xatosi beradi (PySide6, sqlcipher3, cryptography). |
| In-memory `LocalStore` takrorlash (brokersiz, `/usr/bin/python3 -B -I`) | `omborai/desktop` (kod) | Bootstrap race takrorlandi. Refund divergensiya takrorlandi (10.2, 1–2). Fayl yaratilmadi (`-B`). |
| MQTT test vektorini qayta hisoblash (`cryptography` 50.0.1) | `/usr/bin/python3` | Mavzu, ochiq matn (`{"hello":"dunyo","n":1}`), AAD tekshiruvi — mos. |
| Backend OpenAPI sanoq | `shared/openapi.json` | 23 path, 32 operatsiya, OpenAPI 3.1.0. |
| Backend route dekoratorlari va `include_router` | `backend/app` | 22 ta `@router.get/post` dekorator va `products` uchun PATCH/DELETE; `v1` ga 11 ta `include_router` (`main.py:21-31`). To'liq OpenAPI moslik UNVERIFIED. |
| Desktop test funksiyalari statik sanoq | `omborai/desktop/tests` | 53. |
| Mobil test deklaratsiyalari statik sanoq | `omborai/mobile/test` | `test()` 30, `testWidgets()` 2, `group()` 1. |
| Backend test funksiyalari statik sanoq | `omborai/backend/tests` | 47. |
| `backend/.pytest_cache/v/cache/lastfailed` | `omborai/backend` | `{}` — oxirgi saqlangan ishga tushirishda xato yozilmagan. Bu o'tganini isbotlamaydi. |

Oldin bajarilgan (scout hisoboti), bu sessiyada qayta ishlatilmagan:

- `flutter analyze --no-pub` (`/opt/flutter/bin`): "No issues found! (ran in 19.5s)", exit 0. UNVERIFIED (bu sessiyada qayta tekshirilmagan).
- `flutter build apk` — hech qachon bu muhitda tasdiqlanmagan; APK fayllar mavjud (6-bo'lim).

Ishga tushirilmagan (UNVERIFIED):

- Desktop `pytest -q` to'liq bog'liqliklar bilan (kutilgan: 53 test; PySide6, sqlcipher3, paho, keyring, cryptography o'rnatish kerak).
- Mobil `flutter test` (kutilgan: 30 `test()` + 2 `testWidgets()`), `flutter build apk`, `flutter run` (qurilmada).
- Kotlin skanerni qurilmada ishlatish.
- Backend `pytest -q` (PostgreSQL 16 va bog'liqliklar kerak; kutilgan: 47), `mypy app`, `alembic upgrade head` haqiqiy PostgreSQL'da, `ruff format --check`.
- `scripts/export_openapi.py` (fayl yozadi; CI `shared/openapi.json` farqini tekshiradi).
- `docker compose up`, `docker build`, Caddy TLS va ACME.
- Desktop broker testlari (3) va mobil broker testi (1) haqiqiy Mosquitto bilan.
- `broker.hivemq.com:8883` ga ulanish va xabar almashish.
- Ikki qurilmali haqiqiy sinxron, snapshot oqimi (qurilmada).
- Argon2 default hash turi (`PasswordHasher()`; paket bu muhitda yo'q).
- Windows'da desktop ishga tushirish.
- Thermal printer bilan chop etish (ESC/POS, CP866).

## 14. Ma'lum muammolar va texnik saboqlar

### 14.1 Ma'lum muammolar (kodda)

- **Snapshot poygasi** (10.2-1): jonli op birinchi bo'lsa qurilma bootstrap bo'la olmaydi. Yechim yo'nalishi: snapshot'ni `applied_ops` soniga emas, mahalliy katalog bo'shligiga qarab qabul qilish; yoki `applied_ops` > 0 bo'lsa ham `products`/`users` bo'sh bo'lsa qayta so'rash. Testi yo'q.
- **Qaytarish divergensiyasi** (10.2-2): snapshot sotuv tarixini o'z ichiga olmaydi. Yechim yo'nalishi: `refund` operatsiyasiga sotuv qatorlarini (items) ham qo'shish, yoki snapshot'ga `sales` ro'yxatini qo'shish. Testi yo'q.
- **Mobil login'dan keyin navigatsiya yo'q** (6.2).
- **Qaytarish rol bo'yicha ochiq** (10.2-4).
- **Desktop mahsulot formasi unit**: noma'lum birlik "dona" ga aylanadi (10.2-8).
- **Desktop `open_envelope` xato ushlashi** (10.2-7).
- **LWW tengligi va `ts` formati** (8.9).
- **Mobil `flushOutbox` PUBACK kutmaydi** (8.8; UNVERIFIED).
- **`products` jadvalida `store_id` yo'q:** bir qurilmada ikki do'kon qo'llab-quvvatlanmaydi.
- **Ikki qurilma bir vaqtda bir xil login qo'shsa:** ikkalasi ham saqlanadi, LWW bilan eng so'nggisi ishlaydi; markaziy tekshiruv yo'q (`f422fbe` xabari, ma'lum cheklov).
- **Fiskal chek:** placeholder (2-bo'lim).
- **Mobil `lib/src/api/` va `OMBORAI_API_URL`** eskirgan hujjatda bor, kodda yo'q.

### 14.2 Hujjat ziddiyatlari (kod bilan farq)

- `docs/sync-mqtt.md`: "product LWW (ts, keyin device)" — kodda device tie-break yo'q. "Eng birinchi javob beruvchi" — aslida barcha qurilmalar javob beradi, faqat birinchisi qo'llanadi. Parol vektori ikkala testda deyilgan — faqat mobilda.
- `docs/sync-mqtt.md`: "snapshot poygasi kichik oynada qoldiq farqi" — aslida tovar va foydalanuvchilar umuman yo'qolishi mumkin (10.2-1).
- `docs/sync-mqtt.md`: "negativ qoldiq hisobotda belgilanadi" — bunday belgilash kodda yo'q.
- `docs/sync-mqtt.md`: "xususiy brokerda faqat manzil va autentifikatsiya sozlamasi o'zgaradi" — `MqttSync` da autentifikatsiya parametri yo'q.
- `docs/sync-mqtt.md`: "parol o'zgarishi `user` operatsiyasi orqali" — protokol qo'llaydi, lekin hech bir klientda parol o'zgartirish yo'q.
- `docs/sinov-telefon.md`: "Shu qurilmada **Juftlash** ekranini oching" — juftlash ekrani faqat mobilda; desktop'da kodni ko'rsatadigan ekran yo'q.
- `docs/sinov-telefon.md`: desktop uchun `pip install -e ".[dev]"` qadami yo'q.
- `docs/reja.md` (241 qator): Riverpod, go_router, Drift, dio, Celery, Redis, FTS5, SQLAlchemy/httpx (desktop), python-escpos, UUID v7, SMS (Eskiz), WorkManager, testcontainers, integration_test, REST sync `change_seq`, `/customers`, `/debts`, `/reports` — hech biri joriy kod bilan mos emas (bu so'zlar `reja.md` da bor; kodda yo'q: `pubspec.yaml`, `pyproject.toml`, `openapi.json` bilan tekshirildi). `docs/reja.md:194` va `:238` ziddiyatli (fiskal).
- `README.md`: "backend/README bo'limlari" — `backend/README` yo'q. Faza 2–4 "keyingi" deb yozilgan, holat jadvalida esa "tayyor". Sinxron "REST `/v1/sync/push`" deyilgan, klientlar MQTT ishlatadi.
- `desktop/README.md`: `omborai_desktop/api.py` yo'q; `OMBORAI_API_URL` kodda o'qilmaydi; "Offline rejim — Faza 4 da" deyilgan, lekin `offline/store.py` allaqachon bor.
- `mobile/README.md`: `lib/src/api/`, `OMBORAI_API_URL`, "Android SDK platform 35", API klient testlari — eskirgan.
- `docs/` dagi `reja.md:239` ("broker.hivemq.com savdo uchun mos emas") va production default — ziddiyat (3.3-2).
- `design/` eskizlari: qarz daftari, foyda ko'rsatkichi, kirim/tuzatish tugmalari, Click/Payme oqimlari eskiz darajasida; kodda yo'q.
- `mobile/android/app/build.gradle.kts:18` dagi TODO izohi (applicationId) qolgan, lekin qiymat allaqachon o'rnatilgan. `:35` dagi TODO (release imzo) hali haqiqiy.

### 14.3 Texnik saboqlar (gotchas)

- **Snapshot faqat bo'sh qurilmada.** Har qanday jonli operatsiyadan keyin bootstrap yo'li yopiladi. Yangi qurilmani ulashdan oldin uni bo'sh qoldiring.
- **`apply_op` refund'ni "qo'llangan" deb qaytaradi**, lekin sotuv yo'q bo'lsa hech narsa o'zgarmaydi. Qo'llash natijasini ishonchsiz deb hisoblang.
- **`OMBORAI_MQTT_TLS`** faqat `"1"`. `"true"` yoki `"yes"` TLS'ni jim o'chiradi.
- **`OMBORAI_STORE_KEY`** keyring'dan ustun, hex noto'g'ri bo'lsa `bytes.fromhex` ValueError beradi (ishga tushirish paytida).
- **Desktop testlari** `QT_QPA_PLATFORM=offscreen` ni `conftest.py` da `setdefault` bilan qo'yadi; CI'da ham shu.
- **Desktop mosquitto testlari** `shutil.which("mosquitto")` ga bog'liq. `/usr/sbin` PATH'da bo'lmasa testlar o'tkazib yuboriladi (sukut bo'yicha `skip`, xato emas).
- **pytest interpretatori:** `pytest` boshqa Python muhitida bo'lsa (uv tool), `pip install -e` qilingan venv'dagi bog'liqliklar ko'rinmaydi. Har doim venv'ning `python -m pytest` ini ishlating.
- **Mobil DB migratsiyasi:** `onUpgrade` faqat `from < 2`. Keyingi versiya uchun yangi shart kerak; `onUpgrade` ning `to` parametri ishlatilmaydi.
- **Mobil v1 jadvallari `IF NOT EXISTS`siz** — `onCreate` faqat yangi bazada ishlaydi; `_schema` ni o'zgartirish mavjud bazaga ta'sir qilmaydi; o'zgarish kerak bo'lsa yangi `onUpgrade` shartini yozing.
- **Mobil `_Bootstrap`** — `FutureBuilder` faqat bir marta; login'dan keyin holatni qayta tekshirmaydi (14.1).
- **Backend RLS:** `set_config(..., is_local=true)` commit'dan keyin tozalanadi; `db.py` dagi `after_begin` hook har tranzaksiyada qayta qo'yadi. Yangi sessiya ochganda kontekstni o'zingiz qo'ying.
- **Backend'da jadval egasi RLS'ni chetlab o'tadi** (`FORCE` yo'q). Ilova `omborai_app` bilan ulanishi shart.
- **Backend `memberships` RLS:** WITH CHECK faqat tenant; `user_id` bo'yicha o'qish OR shartida.
- **`memberships` UNIQUE (tenant_id, user_id, store_id)** — `store_id IS NULL` dublikatlarini to'smaydi (PostgreSQL NULL'larni teng deb hisoblamaydi).
- **Migratsiya oldidan `omborai_app` roli kerak** (Docker init skripti bu yerda muhim).
- **Caddy `{$OMBORAI_DOMAIN:localhost}`** — `localhost` uchun Caddy lokal CA sertifikati beradi; HTTP ishlatilmaydi.
- **Gitignore:** `*.apk` va `build/` root'da — release APK git'ga tushmaydi; `*.egg-info/` ham shunday.
- **`egg-info/SOURCES.txt` eskirgan** — `pip install -e` qayta yaratadi, uni tahrirlamang.
- **ESC/POS** matnini `cp866` ga kodlash (`escpos.py`); boshqa kodlashda printer belgilari buziladi.
- **Mobil kamera ruxsati** ilova ishga tushganda so'raladi (`CAMERA`, `required="false"`).
- **Mobil `mocktail`** `dev_dependencies` da, ishlatilmaydi — olib tashlash mumkin.
- **Mobil `flutter analyze`** `analysis_options.yaml` (`flutter_lints`) bilan.

## 15. Ochiq ishlar va ustuvorlik

Ustuvorlik: P0 — ishlab chiqarishga chiqishdan oldin; P1 — MVP uchun; P2 — keyingi bosqich.

**P0**

1. Snapshot poygasini tuzatish (bootstrap'ni bo'sh katalog bo'yicha aniqlash) va regressiya testi (desktop `test_store_ops.py`, `test_pos_ui.py`; mobil `users_db_test.dart`).
2. Qaytarish divergensiyasini tuzatish (refund operatsiyasiga items; yoki snapshot'ga sotuvlar) va testi.
3. Mobil: login/do'kon yaratish/juftlashdan keyin bosh ekranga o'tish; `login_screen_test.dart` ga bu holat qo'shiladi.
4. Qaytarishni rol bo'yicha cheklash (desktop `refund_sale` va mobil `RefundsScreen`), egasi/menejer (qaror kerak: kassir qaytara oladimi).
5. Hosting va broker qarori: ommaviy `broker.hivemq.com` qoladimi; xususiy broker uchun `MqttSync` da autentifikatsiya qo'shiladimi (3.3-2).
6. Fiskal/OFD talablarini aniqlash: provayder, chek formati, API (3.3-1). Reja xavf jadvalida fiskal bo'yicha xavf darajasi "Yuqori" (`docs/reja.md`).

**P1**

7. Desktop: juftlash kodini ko'rsatish oynasi (`login.pairing_code()` ga chaqiruvchi), ogohlantirish bilan (kod = kalit).
8. Tovar kirimi va qoldiq tuzatish UI (`movement` operatsiyasi allaqachon qo'llanadi).
9. Mahsulot formasi: noma'lum birlikni saqlash (desktop, 10.2-8); mobil bilan tekshirish.
10. Desktop `open_envelope` va `_on_message` da xatolarni to'liq ushlash (10.2-7).
11. Narx ishonchi: qo'llashda sotuv summasini payload ichida tekshirish (`subtotal`, `total` = items yig'indisi) — hech bo'lmasa qayd etish.
12. `ts` formatini bir xillashtirish (UTC, bir xil ko'rinish) va LWW tengligi uchun `device` tie-break (8.9).
13. Desktop va mobil testlar: to'liq bog'liqliklar bilan `pytest -q` va `flutter test` ishga tushirish; mobil broker testi CI'ga qo'shish (desktop jobida mosquitto bor, mobil jobida yo'q).
14. Eski hujjatlarni yangilash: `README.md`, `desktop/README.md`, `mobile/README.md`, `docs/sync-mqtt.md`, `docs/sinov-telefon.md`, `docs/reja.md` (14.2).
15. Mobil release imzo konfiguratsiyasi (`signingConfigs.release`) va `build.gradle.kts` dagi eskirgan TODO'lar.
16. Savdo jurnali, cheklarni qayta chop etish, smena tarixi, kam qoldiq ogohlantirishi (`min_stock` bilan solishtirish), bo'lib to'lash (`Cart.to_sale_payload` allaqachon ro'yxat qabul qiladi).
17. Desktop/mobil: chiqish, parol o'zgartirish, foydalanuvchini tahrirlash, rol o'zgartirish (`user` operatsiyasi protokolda bor).
18. Backend RLS: `FORCE ROW LEVEL SECURITY` va ilova/owner rollarini ajratish (agar backend qayta ishga tushirilsa); GET endpointlarga do'kon a'zolik tekshiruvi.
19. Backend `require_roles` ni do'kon bo'yicha qilish; `login` ga `ORDER BY`; `refresh` da `users.deleted_at` tekshiruvi.
20. Backend `--proxy-headers` uchun `FORWARDED_ALLOW_IPS` ni aniqlashtirish; `OMBORAI_REDIS_URL` ni olib tashlash yoki ishlatish.

**P2**

21. Fon sinxronizatsiyasi (Android WorkManager) — hozir faqat ilova ochiq paytida.
22. Qarz daftari va hisobotlar (dizayn eskizi bor, kod yo'q).
23. Click/Payme integratsiyasi (backend'da webhook yo'llari rejada, kodda yo'q).
24. Ko'p filial, AI prognoz (reja, "Keyin").
25. Desktop Linux/macOS (pyproject tavsifida, sinalmagan).
26. Ruscha interfeys (agar kerak bo'lsa).

## 16. Foydalanuvchi bilan ishlash uslubi

- Foydalanuvchi o'zbek tilida yozadi (lotin). Hujjatlar va UI matnlari o'zbek lotinida.
- Uzun sessiyalarda to'xtamasdan ishlashni xohlaydi; qaror kerak bo'lganda aniq savol beriladi.
- Qarorlar yozib boriladi (reja fayli oxiridagi "Qarorlar" bo'limi va 3-bo'lim jurnali). Ochiq savollar alohida ko'rsatilsin.
- PR faqat so'ralganda ochiladi. Ish branch'i: `claude/wonderful-dirac-gdu5x2`; PR bazasi `master`.
- Commit xabarlari: model nomi yo'q; `Claude-Session` trailer. Bu sessiyada tizim ko'rsatmasi `Co-Authored-By` qo'shishni talab qilgan — keyingi commit'dan oldin foydalanuvchi bilan tasdiqlang (3.3-6).
- Lokal sinov tanlangan (serverga bog'liq hosting javobsiz); foydalanuvchi loyihani to'liq yuklab olib lokal muhitda davom ettirmoqchi.
- Jamoa: foydalanuvchi va Claude. Pilot: universal.
- Sirlar (parol, token, kalit, `.env`) hujjatlarga va commit'ga yozilmasin; faqat nomi bilan ko'rsatilsin.
