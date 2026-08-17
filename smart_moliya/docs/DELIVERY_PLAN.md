# Yetkazib berish rejasi (11 bosqich)

Har bosqich tugagach quyidagilar beriladi: Project Tree yangilanishi, to'liq source code, README, API docs (agar tegishli bo'lsa), diagrammalar, test case'lar, o'rnatish yo'riqnomasi.

1. **Architecture** — ✅ yakunlandi (`01_ARCHITECTURE.md`, `PROJECT_TREE.md`, diagrammalar) + **buildable Android Studio skelet** (`android/` — Gradle root, Kotlin+Compose, Hilt, Room/Retrofit/WorkManager dependencylari ulangan, Dashboard placeholder ekrani ishlaydi)
2. **Database** — ✅ yakunlandi: PostgreSQL sxema (14 ta SQLAlchemy modeli, `backend/app/models/`), Alembic dastlabki migratsiya (`0001_initial_schema.py`), Room offline sxema (8 entity + DAO, `android/.../core/database/`), to'liq ER diagram (`docs/diagrams/er_diagram.mmd`)
3. **Backend** — ✅ yakunlandi: FastAPI core service — auth (register/login/refresh/me, JWT access+refresh), categories, wallets, transactions (avtomatik balans yangilanishi bilan), budgets (real vaqtda status hisoblash), goals (progress+oylik tejash bashorati), loans (penalty hisoblash), debts, sync (push/pull, offline-first). Repository Pattern + Service qatlami + `ServiceError` → HTTP status mapping. `pytest` bilan tekshirildi (health-check test o'tdi)
4. **Android UI** — ✅ yakunlandi: Dashboard (umumiy balans, oylik daromad/xarajat, so'nggi tranzaksiyalar), Wallets (CRUD), Income/Expense (qo'shish/o'chirish, kategoriya+hamyon tanlash), Reports (oyлik xarajat kategoriya bo'yicha, Canvas-based bar chart) — barchasi Bottom Navigation bilan bog'langan. Offline-first Repository qatlami (Room = UI manbai, Retrofit orqali serverga push/pull, muvaffaqiyatsiz bo'lsa `PENDING` holatda qoladi). Hilt orqali to'liq DI zanjiri (Network+Database+Repository modullari)
5. **AI Module** — ✅ yakunlandi: `ai_service/` alohida FastAPI+PyTorch mikroservis. Auto-categorization (bag-of-words + PyTorch linear classifier, uz/ru seed dataset), Forecast (PyTorch gradient-descent linear trend — kelasi 30 kun xarajat bashorati + "pul tugash" kuni), Anomaly detection (z-score statistik), Chatbot (intent-based, uz/ru/en, LLM-ga almashtirish uchun interfeys tayyor). 11 ta pytest testi — barchasi o'tdi (haqiqiy PyTorch o'qitish va inferensi tekshirildi)
6. **Authentication** — ✅ yakunlandi (Phone+parol, Biometric, PIN, device binding — Google/OTP keyingi bosqichda kengaytiriladi, quyida tafsilot)
7. **Payments** — ✅ yakunlandi: Universal Bank API Layer (`app/integrations/banks/` — `BankProvider` interfeysi, `MockBankProvider`, 8 ta bank registry'da: Asaka/NBU/Ipoteka/Kapitalbank/Hamkorbank/SQB/Agrobank/Aloqabank) + Payment Layer (`app/integrations/payments/` — Click/Payme/UzumBank mock, HMAC-SHA256 webhook imzo tekshiruvi). Yangi `payments` jadvali (Alembic `0002`), `/api/v1/payments` (create/webhook/list) va `/api/v1/banks` (list/link/sync) endpointlari. 10 ta yangi test (jami 15 backend testi o'tadi)
8. **Reports** — ✅ yakunlandi: backend `ReportService` (kategoriya bo'yicha taqsimot, kunlik cash flow), `GET /api/v1/reports/summary`, haqiqiy **PDF** (`reportlab`) va **Excel** (`openpyxl`, 3 sahifa: Xulosa/Kategoriyalar/Cash Flow) eksport endpointlari. Android Reports ekrani serverdan hisobot oladi, Canvas-based **Pie chart** ko'rsatadi, PDF/Excel'ni qurilmaga yuklab saqlaydi. Jami 20 backend testi o'tadi — shu jarayonda 3-bosqichdan qolgan **haqiqiy production xato** (naive/aware datetime taqqoslash, `budget_service.py`da ham) topilib tuzatildi
9. **Gamification** — ✅ yakunlandi: `GamificationService` (XP/level, streak, 6 ta badge katalogi — `first_transaction`, `streak_7_days`, `streak_30_days`, `first_goal_completed`, `first_budget_created`, `challenge_completed`), `ChallengeService` (SAVE_AMOUNT/NO_SPEND_DAYS turdagi haqiqiy tranzaksiya ma'lumotlaridan hisoblanadigan weekly/monthly challenge), `FamilyService` (guruh yaratish/qo'shilish, pocket money/allowance, Task Reward — vazifa yaratish→bajarish→tasdiqlash→avtomatik to'lov). Yangi 4 jadval (Alembic `0003`). XP/badge avtomatik beriladi: tranzaksiya qo'shilganda, byudjet yaratilganda, maqsad yakunlanganda. 11 ta yangi test — jami **31 backend testi o'tadi**. Bu jarayonda yana bitta nozik production xato topildi va tuzatildi (quyida)
10. **Testing** — ✅ yakunlandi: **backend** — `pytest.ini` (coverage: `--cov=app --cov-report=term-missing/html`, joriy holat **78%**), yangi security testlar (tampered/expired/wrong-secret JWT), public API endpoint testlari (401 himoyasi, validatsiya, OpenAPI sxema tekshiruvi), **41 test o'tadi**; `locustfile.py` — haqiqiy stress-test script (register→login→wallet→transaction oqimi). **AI Service** — 4 ta edge-case/robustness test qo'shildi (bo'sh input, qisqa tarix, inferensiya tezligi) — **15 test o'tadi**. **Android** — birinchi haqiqiy JVM unit testlar (`WalletMappersTest`, `TransactionMappersTest` — Entity/DTO/domain mapping va ISO sana round-trip)
11. **Deployment** — ✅ yakunlandi: `infra/` — backend/AI uchun Dockerfile'lar (slim, non-root, AI uchun CPU-only torch), `docker-compose.yml` (postgres+redis+backend+ai+nginx, healthcheck'lar, avtomatik `alembic upgrade head`; sintaksisi `docker compose config` bilan tekshirilgan), `nginx.conf` (reverse proxy, rate-limit 20 req/s). `.github/workflows/ci.yml` — 4 job: backend testlar, AI testlar, Android build (APK artifact), Docker image build+smoke test (YAML validatsiyadan o'tgan). To'liq qo'llanma: `docs/11_DEPLOYMENT.md` (compose bilan ko'tarish, Android BASE_URL sozlash, release APK/AAB imzolash, Google Play tekshiruv ro'yxati)

### 7-bosqich eslatma

Bu bosqich backend-markazli (arxitektura brifida "Kelajak uchun architecture tayyor bo'lsin... Hozircha Mock API" deb belgilangan). Android tomonida to'lov/bank ekranlari (hamyonni Click/Payme orqali to'ldirish, bank hisobini ulash) hali qo'shilmagan — bu keyingi UI-polish bosqichida (`ApiService`ga `/payments` va `/banks` endpointlarini qo'shish + mos ekranlar) amalga oshiriladi.

### 6-bosqich tafsiloti

- **Backend**: `LoginRequest`/`RefreshRequest`ga `device_id` qo'shildi, refresh token endi qurilmaga bog'lanadi (JWT claim'da `device_id`) — boshqa qurilmadan o'g'irlangan refresh token bilan yangilash urinishi 401 bilan rad etiladi. 2 ta yangi pytest testi (`tests/test_auth.py`) — jami 5 ta backend testi o'tadi.
- **Android**: to'liq auth oqimi — Login/Register ekranlari (`feature/auth/`), PIN o'rnatish/tekshirish (4 xonali, SHA-256 hash, shifrlangan saqlash), Biometric (fingerprint/face, `androidx.biometric`), Profile ekrani (logout). `TokenManager` endi `EncryptedSharedPreferences` (Android Keystore, AES-256) ishlatadi — oddiy SharedPreferences emas. `SmartMoliyaNavHost` endi sessiya holatini boshqaradi: AUTH_REQUIRED → PIN_SETUP/PIN_REQUIRED → UNLOCKED.
- **Kechiktirilgan**: Google Login va SMS OTP — bularga tashqi xizmat kalitlari (Google OAuth client ID, SMS provayder — Eskiz.uz yoki Play Mobile kabi) kerak, foydalanuvchidan alohida so'ralishi kerak. Interfeys (`AuthRepository`) shu qo'shimchalarga tayyor — `loginWithGoogle()`/`requestOtp()` metodlari kelgusida qo'shiladi.

## Muhim eslatma

Bu — production-darajali, to'liq ko'lamli FinTech monorepo (native Android Kotlin/Compose + 2 ta Python xizmat + admin panel). Har bosqich o'zi katta hajmda kod talab qiladi, shu sababli har bosqichni **alohida so'rov/xabar** bilan ketma-ket ishlab chiqamiz — shunda har bir qatlamni ko'rib chiqish va sifatni tekshirish imkoniyati bo'ladi.

### 9-bosqich eslatma

`UserProgress` (xp/level/streak) yozuvi Python obyekt sifatida yaratilganda SQLAlchemy'ning `mapped_column(default=0)` qiymati **flush qilinmaguncha `None` bo'lib qoladi** — bu `UserProgressRepository.get_or_create`da haqiqiy `TypeError`ga olib kelardi (`None + int`). Unit test yozayotganda topilib, endi obyekt yaratilishida barcha default qiymatlar aniq (`xp=0, level=1, ...`) beriladi — flush vaqtiga bog'liq bo'lmaydi. Bu ham `feedback-tz-aware-datetime` xotirasiga o'xshash umumiy saboq: **SQLAlchemy `default=`li ustunlarga har doim aniq boshlang'ich qiymat berish kerak, agar obyekt flush'dan oldin o'qilishi/o'zgartirilishi mumkin bo'lsa**.

Android tomonida gamification UI (XP progress bar, badge gallereyasi, leaderboard, challenge ekranlari, Family Mode) hali qo'shilmagan — bu keyingi UI-polish bosqichida amalga oshiriladi (Payments UI bilan birga).

### 10-bosqich eslatma

Widget (Compose UI) va instrumented (`androidTest`) testlar hali qo'shilmagan — ular haqiqiy Android qurilma/emulyator talab qiladi, bu muhitda mavjud emas. Backend integratsion testlar (haqiqiy Postgres bilan) ham keyinroq, Docker Compose environment tayyor bo'lganda (11-bosqich) qo'shiladi — hozirgi 41 test barchasi DB'siz (fake repository/pure logic) ishlaydi, shu bois ba'zi servis fayllarining coverage'i past (masalan `family_service.py` 25%) — bu haqiqiy DB integratsiyasi qo'shilgach yopiladi.

### 11-bosqich eslatma

Docker image'larning haqiqiy build'i bu muhitda tekshirilmadi (Docker daemon ishlamayapti edi) — compose sintaksisi va CI YAML validatsiyadan o'tdi. Docker Desktop ishga tushirilganda `docker compose -f infra/docker-compose.yml up --build` bilan sinash mumkin.

## Qo'shimcha: UI-polish bosqichi — ✅ yakunlandi

11 asosiy bosqichdan keyin bajarildi. Android'ga 3 ta yangi ekran to'plami qo'shildi:

- **Payments** (`feature/payments/`): hamyonni Click/Payme/Uzum orqali to'ldirish formasi (provider chip, hamyon tanlash, summa) + to'lovlar tarixi (status: To'landi/Kutilmoqda). Mock muhitda to'lov darhol `simulate` endpointi orqali yakunlanadi — buning uchun backend'ga `POST /api/v1/payments/{id}/simulate` qo'shildi (**faqat non-production**, `ENVIRONMENT=production`da 404).
- **Gamification** (`feature/gamification/`): Level + XP progress bar, joriy/eng uzun streak, "Mening challenge'larim" (progress bar, yangilash tugmasi), faol challenge'larga qo'shilish, nishonlar katalogi, peshqadamlar reytingi.
- **Family** (`feature/familymode/`): guruh yaratish/ID orqali qo'shilish, a'zolar ro'yxati, pocket money yuborish, vazifa yaratish (mukofot bilan), vazifani "bajarildi" deb belgilash va tasdiqlash (avtomatik to'lov). Backend'ga `GET /api/v1/family/tasks` qo'shildi (ro'yxat endpointi yo'q edi).
- **Navigatsiya**: bottom bar'dagi "Profil" o'rnini "Menyu" egalladi — ichida Profil, To'lovlar, Yutuqlar, Oila sahifalari.

Tekshirildi: 41 backend testi o'tadi, yangi endpointlar OpenAPI sxemasida, 76 Kotlin fayl qavs-balansdan o'tgan.

## Qo'shimcha: Google/OTP login — ✅ yakunlandi

- **OTP (SMS) login**: `POST /auth/otp/request` (6 xonali kod, SHA-256 hash bilan saqlanadi, 120s muddat, 5 urinish limiti, bir martalik) va `POST /auth/otp/verify` (kod to'g'ri bo'lsa — mavjud foydalanuvchini kiritadi yoki parolsiz yangi hisob ochadi). Dev muhitda kod `dev_code` maydonida qaytadi (`MockSmsSender`); production'da SMS provayder adapteri (`SmsSender` interfeysi, masalan Eskiz.uz) ulanadi va kod hech qachon javobda qaytmaydi. Hozircha `InMemoryOtpStore` (bir instance) — ko'p instance uchun Redis'ga ko'chirish interfeysi tayyor.
- **Google login**: `POST /auth/google` — `GoogleTokenVerifier` interfeysi: `GOOGLE_CLIENT_ID` sozlangan bo'lsa haqiqiy tekshiruv (`google-auth` kutubxonasi, lazy import), sozlanmagan dev muhitda mock (`mock-google:<email>:<ism>` token). Production'da client ID'siz Google login yopiq.
- **Android**: `OtpLoginScreen` (telefon → kod so'rash → dev-kod ko'rsatiladi → tasdiqlash), LoginScreen'da "SMS kod bilan kirish" va "Google bilan kirish" tugmalari. Google tugmasi faqat `app/build.gradle.kts`dagi `GOOGLE_SERVER_CLIENT_ID` to'ldirilganda ko'rinadi — Credential Manager (`androidx.credentials`) orqali to'liq oqim yozilgan, faqat client ID kiritish kifoya.
- Tekshirildi: backend **49 test** (8 yangi: OTP roundtrip/bir martalik/noto'g'ri kod/muddat/urinish limiti, mock Google verifier), Android `assembleDebug`+`testDebugUnitTest` → **BUILD SUCCESSFUL**.

## Qo'shimcha: Zamonaviy UI va temalar tizimi — ✅ yakunlandi

Butun ilova (ikkala flavor) zamonaviy fintech dizayniga o'tkazildi:
- **6 ta tanlanadigan tema** (`ui/theme/AppTheme.kt`, saqlash: `ThemeManager`+SharedPreferences, tanlov Profil sahifasida, darhol qo'llanadi): **Dark Modern** (standart), AMOLED qora, Okean (ko'k), Shafaq (binafsha-pushti), Yorug', Tizim rangi (Android 12+ dynamic color)
- **Umumiy komponentlar** (`ui/components/Components.kt`): gradient hero-kartalar, kategoriya ikon-doirachalari (16 ikon mapping), yagona uslubdagi tranzaksiya qatorlari (+yashil/−qizil summalar), bo'sh holatlar (emoji bilan), to'liq Material3 tipografiya shkalasi
- **Qayta dizayn qilingan ekranlar**: Dashboard (gradient balans kartasi + oylik daromad/xarajat pill'lari), Hamyonlar (har biriga o'z gradient kartasi), Tranzaksiyalar (ikonli qatorlar, sana formatlash), Hisobotlar (stat kartalar + pie chart + progress bar'li kategoriya qatorlari), Menyu (ikonli kartalar + chevron), Profil (tema tanlash paneli), PIN (dumaloq klaviatura)
- Build tasdiqlangan: **BUILD SUCCESSFUL**, ikkala flavor testlari o'tgan

## Qo'shimcha: Offline (avtonom) APK — ✅ yakunlandi (v2: to'liq funksiyalar bilan)

Gradle **product flavor** orqali bitta kod bazasidan ikkita mustaqil APK:
- `app-online-debug.apk` (`com.smartmoliya.app`) — to'liq versiya (backend bilan)
- `app-offline-debug.apk` (`com.smartmoliya.app.offline`, "Smart Moliya Offline") — **hech qanday serverga ulanmaydi**, lekin barcha funksiyalar lokal ishlaydi:
  - Login o'rniga to'g'ridan-to'g'ri PIN/biometrik; ma'lumotlar SQLCipher-shifrlangan Room'da
  - Hamyonlar, tranzaksiyalar (15 seed kategoriya), balans lokal yuritiladi
  - **Hisobotlar** lokal hisoblanadi (Pie chart) + **CSV eksport** (Excel'da ochiladi)
  - **Hamyonni to'ldirish**: naqd to'ldirish (income tranzaksiya sifatida, tarix bilan)
  - **Yutuqlar**: XP/level/streak, 4 nishon (earned/locked), 2 avto-challenge (haftalik tejash, xarajatsiz kunlar) — barchasi tranzaksiyalardan real vaqtda hisoblanadi
  - **Vazifalar va mukofotlar**: lokal vazifa yaratish → bajarish → tasdiqlashda mukofot hamyonga tushadi (Room `local_tasks` jadvali, DB v2)

**Kritik bug topilib tuzatildi (birinchi offline sinovda foydalanuvchi skrinshotlari orqali)**: barcha DAO'larda `@Insert(onConflict = REPLACE)` ishlatilgan edi — SQLite'da REPLACE = DELETE+INSERT, bu esa hamyon qatori yangilanganda `ON DELETE CASCADE` orqali **shu hamyonning barcha tranzaksiyalarini o'chirib yuborardi** (balans qolardi, ro'yxat/hisobot bo'shardi). Barcha DAO'lar Room'ning `@Upsert`iga o'tkazildi (o'chirmasdan yangilaydi) — bu xato online rejimga ham ta'sir qilardi (wallet refresh har safar lokal tranzaksiyalarni o'chirardi). Build tasdiqlangan: **BUILD SUCCESSFUL**, ikkala flavor testlari o'tgan.

## Qo'shimcha: Admin Panel — ✅ yakunlandi

`admin_panel/` — alohida FastAPI + Jinja2 xizmat (brifdagi barcha bo'limlar): **Dashboard** (statistika + so'nggi tranzaksiyalar), **Users** (bloklash/faollashtirish), **Transactions**, **Fraud Detection** (SQL bilan foydalanuvchi+kategoriya o'rtachasidan 2.5σ+ chetlangan xarajatlar), **Analytics** (DAU grafigi), **Notification Center** (bitta/barcha foydalanuvchilarga xabar — yangi `ADMIN_MESSAGE` turi, Alembic `0004`). Kirish: login/parol → imzolangan sessiya cookie (8 soat). Backend bilan bir bazaga to'g'ridan-to'g'ri SQL orqali ulanadi — servislar orasida kod bog'liqligi yo'q. Docker Compose'ga `admin_panel` servisi qo'shildi (host: `8081`), CI'ga `admin-panel-tests` job. **8/8 test o'tadi** (fake repository, auth guard/login/toggle/broadcast oqimlari).

## Qo'shimcha: SQLCipher + Certificate Pinning — ✅ yakunlandi

- **SQLCipher**: Room bazasi endi AES-256 bilan shifrlangan (`net.zetetic:sqlcipher-android:4.6.1`, `SupportOpenHelperFactory`). Kalit — birinchi ishga tushishda `SecureRandom` bilan yaratilgan 32 bayt, Android Keystore himoyasidagi `EncryptedSharedPreferences`da saqlanadi (`DatabaseKeyProvider`), kodda yozilmagan. APK'da `libsqlcipher.so` 4 ABI uchun paketlangani tasdiqlandi. Eslatma: ilgari shifrlanmagan baza bilan o'rnatilgan dev-qurilmada ilovani o'chirib qayta o'rnatish kerak.
- **Certificate pinning**: `buildCertificatePinner()` (`core/network/CertificatePinning.kt`) — `CERT_PIN_HOST`/`CERT_PIN_SHA256` BuildConfig maydonlari to'ldirilganda OkHttp'ga SPKI SHA-256 pin qo'shiladi. Pin faqat ko'rsatilgan hostga qo'llanadi — dev'dagi `10.0.2.2` ulanishlariga ta'sir qilmaydi (5 ta unit test bilan tasdiqlangan). Pin olish buyrug'i fayl kommentida va `docs/11_DEPLOYMENT.md`da.
- Qo'shimcha: `BASE_URL` endi BuildConfig'dan (`API_BASE_URL`), release build'da HTTP loglar avtomatik o'chadi (`Level.NONE`).
- Tekshirildi: `assembleDebug` + `testDebugUnitTest` → **BUILD SUCCESSFUL, 13/13 test**.

## Qo'shimcha: Build verifikatsiyasi — ✅ BUILD SUCCESSFUL

Android loyiha haqiqiy Gradle build bilan tekshirildi (JAVA_HOME = Android Studio JBR 21, SDK 35):
- `gradlew assembleDebug` → **BUILD SUCCESSFUL** (3m 52s, APK ~62MB `app/build/outputs/apk/debug/`)
- `gradlew testDebugUnitTest` → **8/8 test o'tdi**

Bu jarayonda topilib tuzatilgan haqiqiy build to'siqlari:
1. **Kotlin 2.0 + Compose plagini**: `org.jetbrains.kotlin.plugin.compose` plagini qo'shildi, eskirgan `composeOptions` olib tashlandi — usiz AGP build'ni darhol to'xtatardi.
2. **Gradle wrapper**: `gradlew`/`gradlew.bat` skriptlari yozildi, `gradle-wrapper.jar` (43.5KB) rasmiy gradle/gradle GitHub omboridan (v8.9.0 tag) yuklab olindi — endi loyiha hech qanday qo'shimcha qadamlarsiz ochiladi.
3. **Room schema export**: `room.schemaLocation` KSP argumenti qo'shildi (`app/schemas/` — migratsiya nazorati uchun).
4. **Cleartext HTTP**: `android:usesCleartextTraffic="true"` (faqat dev; Android 9+ standartda `http://`ni bloklaydi — ilova build bo'lardi, lekin lokal backendga ulanolmasdi).
5. `local.properties` (SDK yo'li) yaratildi — qurilmaga xos, gitignore'da.

## 🎉 Barcha 11 bosqich yakunlandi

Loyihaning joriy holati: 11 asosiy bosqich + barcha qo'shimcha bosqichlar (UI-polish, Google/OTP, SQLCipher/cert-pinning, Admin Panel) yakunlangan. Production'gacha qolgan ishlar `docs/11_DEPLOYMENT.md` "Keyingi ishlar"da: real SMS provayder va Google client ID kiritish, OTP'ni Redis'ga ko'chirish, CD pipeline, DB-integratsion testlar.
