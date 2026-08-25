# Loyiha holati — halol hisobot

Bu hujjat «nima tayyor» degan savolga **o'zini maqtamasdan** javob
beradi. «Test o'tdi» va «ishlaydi» — ikki xil narsa, shuning uchun har
qator uchun **qanday tekshirilgani** ko'rsatilgan.

Sana: 2026-08-24

---

## 1. Tekshiruv darajalari

| Belgi | Ma'nosi |
|---|---|
| **A** | Haqiqiy build o'rnatilib/ishga tushirilib, natija ko'z bilan ko'rilgan |
| **B** | Avtomatik test bor va o'tadi |
| **C** | Kod yozilgan, lekin alohida test yo'q |
| **—** | Bajarilmagan |

---

## 2. Desktop

| Nima | Daraja | Izoh |
|---|---|---|
| Installer yig'iladi | **A** | 61.9 MB, Inno Setup, ogohlantirishsiz |
| O'rnatiladi va ishga tushadi | **A** | Repo tashqarisida, 1.1 s |
| 15 ta ekran ochiladi | **A+B** | GUI smoke test + ekran suratlari |
| Uch xil kirish nuqtasi | **B** | `run.py`, `-m distribos.main`, to'g'ridan-to'g'ri fayl |
| Lokal baza (WAL, FK) | **B** | PRAGMA'lar test bilan tasdiqlangan |
| Append-only trigger'lar | **B** | audit, hodisa, ombor, to'lov |
| Outbox tranzaksiyasi | **B** | §7.1 oqimi |
| 14 hisobot | **B** | Har biri GUI testida shakllantiriladi |
| PDF hujjatlar | **C** | Kod bor, GUI testida chaqirilmagan |
| Zaxira nusxa / tiklash | **B** | Shifrlash → tekshirish → tiklash |
| AI tavsiyalar | **A+B** | Ekranda 6 ta tavsiya ko'rindi |
| Kalitlar DPAPI ostida | **B** | O'rash/ochish + kontekst bog'lanishi |

## 3. Android

| Nima | Daraja | Izoh |
|---|---|---|
| Release APK / AAB yig'iladi | **A** | 26 MB / 18 MB, R8 bilan |
| DistribOS sertifikati bilan imzolangan | **A** | v2 + v3 sxema tasdiqlandi |
| Emulyatorda o'rnatiladi va ochiladi | **A** | Crash yo'q |
| 4 ta ekran | **A** | Qo'lda ochib chiqildi, suratlari bor |
| Room bazasi + trigger'lar | **C** | Kod bor, Robolectric testi yozilmagan |
| Rolga mos ekranlar | **C** | Kod bor, faqat `agent` roli sinaldi |
| Keystore | **C** | Emulyatorda ishladi, alohida test yo'q |
| Shtrix-kod skaneri | **—** | Bog'liqlik qo'shilgan, ekran yozilmagan |
| Kamera / foto | **—** | Bajarilmagan |
| WorkManager fon sinxronizatsiyasi | **—** | Hozircha faqat ekran ochiq bo'lganda |

## 4. Sinxronizatsiya va kripto

| Nima | Daraja | Izoh |
|---|---|---|
| Python ↔ Kotlin kripto mosligi | **B** | 32 test, baytma-bayt |
| Python ↔ Kotlin domen qoidalari | **B** | 159 vektor, 9 test |
| Offline buyurtma → desktop | **B** | To'liq zanjir (Python tomonida) |
| Dublikat (10×) | **B** | Replay oynasi + inbox dedup alohida |
| Tartib buzilishi | **B** | Teskari tartib + kechiktirilgan proyeksiya |
| Yo'qolgan xabar tiklanishi | **B** | Anti-entropy digest, brokersiz |
| Bir vaqtda tahrirlash | **B** | HLC, ikki qurilmada bir xil natija |
| Bekor qilingan qurilma | **B** | Hodisalari rad etiladi |
| Buzilgan/kesilgan/katta paket | **B** | Uchalasi ham rad etiladi |
| Begona tenant | **B** | Rad etiladi |
| Clock skew | **B** | 10 yillik chetlanish qabul qilinmaydi |
| Snapshot (chunk, resume, yaxlitlik) | **B** | Uzilib qolsa davom ettiriladi |
| Snapshot role-scoped | **B** | Omborchiga moliyaviy jadval tushmaydi |
| Kalit rotatsiyasi | **C** | Kod bor, offline qurilma ssenariysi sinalmagan |

---

## 5. BAJARILMAGAN yoki tekshirilmagan

Bular ochiq va ular haqida da'vo qilinmaydi.

### 5.1. Android tomonidagi ulash ekrani — BAJARILDI

Ulash oqimi endi **haqiqiy brokerda, haqiqiy telefonda (emulyator)
uchidan-uchiga sinaldi** — daraja **A**.

Sinov ketma-ketligi (`tools/join_host.py` + emulyator):

1. Kompyuter `broker.hivemq.com:8883` ga ulanadi va bir martalik taklif
   yaratadi (426 belgili kod yoki QR);
2. telefon kodni o'qiydi, JOIN_REQUEST yuboradi;
3. kompyuter javob beradi, telefon epoch kalitini o'rnatadi;
4. egasi qurilmani tasdiqlaydi (`INVITED` -> `ACTIVE`);
5. telefonning 4 ta hodisasi (3 buyurtma + 1 to'lov) kompyuterga yetadi;
6. kompyuterda **ulanishdan oldin** yaratilgan mahsulot (`SINOV-1`)
   telefonga yetadi.

6-band muhim: u hodisa broker tarixidan emas, **anti-entropiya orqali**
tiklanganini ko'rsatadi — telefon o'sha paytda hali obuna ham emas edi.

Yakuniy o'lchov (toza emulyator, debug build):

```
kompyuter -> telefon : SINOV-1 yetdi (inbox 1)
telefon -> kompyuter : 4 hodisa, hammasi PEER_APPLIED
rad etilgan xabarlar : 0
```

**Reliz (minifikatsiyalangan) APK ham xuddi shu yo'l bilan sinaldi** va
u ham ulandi, kalitni oldi, «Hammasi sinxronlangan» holatida 0 rad
etilgan xabar bilan turdi. Bu alohida sinov: R8 aynan shu yerda xato
chiqargan edi (§6.2).

Bu sinovlar to'qqizta xatoni ochdi, ular tuzatildi (§6.1, §6.2).

### 5.2. Unumdorlik — O'LCHANDI

`docs/BENCHMARK.md` — 100 000 mahsulot, 1 000 000 hodisa, 50 000
buyurtmada o'lchandi (`python tools/benchmark.py`). Ko'p mezon
maqsadga (≤300 ms) sig'adi; bitta ochiq savol bor (buyurtmalar
ro'yxati stend ichida 410 ms, stend tashqarisida xuddi shu so'rov 6 ms
— sabab hujjatda halol yozilgan, "tuzatilmagan"). Desktop ishga
tushishi: 1.1 s.

### 5.3. Haqiqiy qurilma

Faqat emulyator (Medium_Phone_API_36) sinaldi — lekin **haqiqiy ochiq
broker orqali**, soxta transport bilan emas. Haqiqiy telefonda —
xususan zaif qurilmada va yomon tarmoqda — sinalmagan.

### 5.4. Lokal konteynerli MQTT broker — BAJARILDI

`tests/integration/broker.py` — Docker'da TLS yoqilgan Mosquitto
(`eclipse-mosquitto:2`), o'z-o'zini imzolagan sertifikat bilan. Uchta
sinov (`tests/integration/test_live_broker_sync.py`, `pytest -m
integration`) **haqiqiy soket** ustida ishlaydi — `LoopbackBus` emas:

* hodisa haqiqiy broker orqali boshqa tugunga yetadi;
* o'z aks-sadosi (broker xabarni yuboruvchiga ham qaytaradi) hech qanday
  behuda `dead_letter` yozuvi qoldirmaydi;
* ikki yo'nalishli sinxronizatsiya ishlaydi.

Sinov Docker mavjud bo'lmasa JIMGINA o'tkazib yuboriladi (CI muhitida
odatda bor). Bu haqiqiy `broker.hivemq.com`ga BOG'LIQ EMAS (ADR-0002).

**Muhim topilma:** birinchi urinishda ikki tugun `Database.in_memory()`
(StaticPool — bitta ulanish barcha oqimlar orasida) bilan qurilganda
`StaleDataError` chiqdi. Sabab MQTT'ning FON OQIMI (paho `loop_start()`)
bilan asosiy oqim BIR XIL ulanishga bir vaqtda yozishga urinishi edi.
Bu production xatosi EMAS — production fayl-asosli baza (WAL, alohida
ulanishlar) ishlatadi. Sinov shunga moslashtirildi va daraja **A**.

### 5.5. Alembic migratsiyalari — BAJARILDI

`alembic/versions/0001_boshlangich_sxema.py` — joriy modeldan
avtogeneratsiya qilingan boshlang'ich migratsiya.
`distribos.persistence.migrations.ensure_schema()` uchta holatni
farqlaydi:

1. bo'sh baza — Alembic barcha migratsiyalarni qo'llaydi;
2. `create_all()` bilan yaratilgan ESKI baza (Alembic tarixisiz, lekin
   jadvallar bor) — qayta yaratilmaydi, faqat "head" deb belgilanadi
   (`stamp`), aks holda `CREATE TABLE` "jadval allaqachon bor" xatosi
   bilan yiqilardi;
3. allaqachon migratsiyalangan baza — oddiy `upgrade`.

**Real yangilash stsenariysi sinaldi** (daraja A): PyInstaller bilan
yig'ilgan `.exe` eski (`create_all()` bilan yaratilgan, ichida haqiqiy
mahsulot yozuvi bor) bazaga ko'rsatildi — mahsulot saqlanib qoldi,
`alembic_version` to'g'ri "0001" ga stamp qilindi, `CREATE TABLE` xatosi
chiqmadi.

Bu yo'lda ikkita xato topildi va tuzatildi:

* `alembic` `pyproject.toml`da e'lon qilingan edi, lekin muhitda
  **o'rnatilmagan** edi;
* `alembic/env.py` PyInstaller'ning statik import skaneridan tashqarida
  qoladi (u `--add-data` bilan ko'chiriladi va `exec` orqali yuklanadi),
  shuning uchun `logging.config` moduli paketlangan build'da
  `ModuleNotFoundError` bilan yiqilardi — bu FAQAT reliz paketida
  ko'rinardi, manba daraxtida yoki avvalgi smoke testda emas.

4 sinov (`tests/contract/test_migrations.py`) uchta holatni ham qamrab
oladi, jumladan `create_all()` va Alembic orasida jadval to'plami
drift qilmasligini tekshiruvchi sinov.

### 5.6. CI (GitHub Actions) — BAJARILDI

`.github/workflows/ci.yml` — to'rt ish: `python` (ruff + pytest),
`python-integration` (§5.4 dagi lokal broker sinovi), `kotlin-pure`
(crypto/domain/core — Android SDK'siz), `kotlin-android`
(sync/data/app — Android SDK bilan). **Haqiqiy GitHub Actions
runner'ida sinaldi** (daraja A) — birinchi push uchta xatoni ochdi:

* `apps/android/gradlew` Git'da bajarilmaydigan (100644) rejimda
  saqlangan edi — Windows'da sezilmaydi, Linux runner'da "Permission
  denied";
* `gradle/actions/setup-gradle@v4` da `build-root-directory` degan
  parametr YO'Q edi — noto'g'ri taxmin qilingan;
* GUI smoke sinovi Linux runner'da `libEGL.so.1` yo'qligi bilan
  yiqilardi — `tlambert03/setup-qt-libs` va `xvfb-run` bilan tuzatildi.

Bundan tashqari: `pyproject.toml` dagi `ruff>=0.8` ochiq versiya
diapazoni tufayli CI HAR DOIM eng yangi `ruff`ni oladi. Lokal muhitda
keshlangan eski versiya (0.8.4) 34 ta yangi qoidani (`RUF059`, `UP042`)
ko'rmagan edi — bularning barchasi oldingi kod edi, tuzatildi.

### 5.7. Boshqalar

* ovozli buyurtma (speech-to-text) — yo'q;
* tashqi AI provayder abstraksiyasi — faqat lokal maslahatchi bor;
* uz-Kirill va rus tillari — kalitlar tayyor, tarjimalar yo'q;
* soak test — bajarilmagan;
* mypy strict rejimda `presentation/` qatlami **TOZALANDI** (0/47,
  daraja B — GUI smoke test to'liq to'plami o'zgarishlardan keyin ham
  o'tadi). Bu yo'lda ikkita HAQIQIY xato topildi (faqat tur izohi emas):
  `operations.py`da ikkita turli xil `for` sikli bitta `row` nomini
  qayta ishlatgani — `PaymentRow`ni `CustomerRow.over_limit`
  deb chaqirishga olib kelardi (runtime'da ishlagan, lekin nozik va
  keyingi tahrirda buzilishi mumkin edi); `reports/builders.py`da
  `AVAILABLE_REPORTS` uchinchi elementi `object` deb yozilgani hisobot
  qurish funksiyalarini mypy'dan butunlay yashirgan edi. Qolgan 67 xato
  `presentation/` TASHQARISIDA (`reports/`, `application/`, `mqtt/`,
  `domain/rules.py` va h.k.) — bu sessiya doirasiga kirmagan.

---

## 6. Ma'lum xatarlar

| Xatar | Ta'siri | Yumshatish |
|---|---|---|
| DES-1 auditdan o'tmagan | Noma'lum zaiflik bo'lishi mumkin | Mustaqil ko'rib chiqish kerak |
| Ochiq broker | Uzilish, ban, metama'lumot | `PRIVATE_PRODUCTION` profiliga o'tish |
| ML-DSA imzosi 3309 bayt | Trafik va batareya | Batch (50 hodisagacha) |
| Qoldiq to'liq qayta hisoblanadi | Ko'p harakatda sekinlashadi | Hozircha o'lchanmagan |
| Android `agent` rolidan boshqasi sinalmagan | Ekranlar noto'g'ri bo'lishi mumkin | Qo'lda sinash kerak |

### 6.1. Jonli sinov ochgan xatolar (tuzatilgan)

Quyidagi xatolar **avtomatik testlarning hammasi o'tib turgan holda**
mavjud edi. Ularni faqat haqiqiy broker ustidagi sinov ochdi.

| Xato | Nima bo'lardi | Tuzatish |
|---|---|---|
| Telefon JOIN_REQUEST ni **o'zining** vaqtinchalik manziliga yuborardi | Ulash hech qachon ishlamasdi; telefon abadiy «javob kutilmoqda» da qolardi, ikkala tomonda ham xato ko'rinmasdi | `Topics.Space.fromTopicId()` |
| Telefon kompyuterning kompaniyasini **qabul qilmasdi** | Ulangandan keyin ham butun sinxronizatsiya noto'g'ri manzilda ketardi | `onTenantAdopted` |
| O'z aks-sadosi peer tasdig'i o'rniga o'tardi | Hech kim olmagan hodisa `PEER_APPLIED` bo'lardi — dastur **yetkazilmagan ma'lumotni yetkazilgan deb ko'rsatardi** | Muhrni ochishdan OLDIN va ochgandan KEYIN — ikki to'siq |
| Anti-entropiya ishlayotgan ilovada **hech qachon chaqirilmasdi** | Ulanishdan yoki oflayn davrdan oldingi hodisalar hech qachon yetib bormasdi | `run_sync_cycle` da 30 soniyada bir marta digest |
| Bir xil topikka **ikki marta obuna** | Har xabar ikki nusxada kelardi, ikkinchisi «takror hujum» deb qayd etilardi: 3 daqiqada 42 ta soxta xavfsizlik ogohlantirishi | Obuna idempotent qilindi |
| JOIN_REQUEST **obuna tasdiqlanmasdan** yuborilardi | Javob biz obuna bo'lgunimizcha kelib yo'qolardi — ulash goh ishlab, goh ishlamasdi | Javob SUBACK dan keyin yuboriladi |
| `PRODUCT_UPDATED` aniqlanmagan o'zgaruvchidan foydalanardi | Mahsulotni tahrirlash HAR DOIM `NameError` bilan yiqilardi | `versions` o'qiladi (+4 sinov) |
| Boshqa kompaniyaning bazasi jimgina aralashardi | Ikki kompaniya yozuvi bir faylga tushardi va ajratib bo'lmasdi | Fayl RAD ETILADI (+4 sinov) |
| «Yuborilmagan» yorlig'i rad etilgan xabarlarni ko'rsatardi | Ikki butunlay boshqa muammo chalkashardi va diagnostika noto'g'ri yo'nalishga borardi | «Qabul qilinmagan» |

Bularning ustiga — **sinovlarning o'zidagi xato**, va u qolganlarini
yashirgan asosiy sabab: `tests/harness.py` dagi soxta broker xabarni
yuboruvchiga **qaytarmasdi** (`device != sender`). Haqiqiy MQTT esa
qaytaradi. Ya'ni stend haqiqatdan kechirimliroq edi. Endi u aks-sadoni
ham yetkazadi va bu xulq test bilan qulflangan
(`tests/end-to-end/test_self_echo.py`).

Xulosa: **soxta transport ustidagi «B» darajasi hech qachon «A» o'rnini
bosolmaydi.**

### 6.2. Faqat reliz build'ida chiqqan xato

R8 (minifikatsiya) RxJava/JCTools navbat sinflarining maydonlarini
qayta nomlagan. Bu sinflar maydonni `Unsafe` orqali **nomi bo'yicha**
qidiradi, shuning uchun ishga tushishda:

```
java.lang.NoSuchFieldException: No field consumerIndex
```

Natija: reliz APK'sida MQTT klienti **umuman ulanmasdi** — foydalanuvchi
«Internet yo'q» ko'rardi. Debug build'da minifikatsiya yo'q, shuning
uchun u benuqson ishlardi.

Tuzatish: `app/proguard-rules.pro` ga saqlash qoidalari.

Xulosa: **debug build'ning ishlashi reliz build haqida hech narsa
isbotlamaydi.** Endi reliz APK ham jonli brokerda sinaladi.

Shu xato yana bir kamchilikni ochdi: ulanish xatosi `runCatching` bilan
JIMGINA yutilardi. Endi sabab logga yoziladi.

---

## 7. Keyingi qadam uchun tavsiya

Bajarildi: QR provisioning oqimi (§5.1), lokal konteynerli broker bilan
integratsion test (§5.4), unumdorlik o'lchovi (§5.2, `docs/BENCHMARK.md`),
Alembic migratsiyalari (§5.5), CI workflow yozildi (§5.6), `presentation/`
qatlamida mypy strict tozalandi (§5.7).

Qolgan, ustuvorlik tartibida:

1. DES-1 uchun mustaqil kriptografik ko'rib chiqish (loyihadan tashqari
   auditor kerak).
2. Haqiqiy telefonda (emulyator emas) sinov.
3. uz-Lotin/rus lokalizatsiyasi qolgan ekranlarga yoyilishi.
4. mypy strict xatolarini `presentation/` tashqarisida ham tuzatish
   (67 ta qoldi) — CI'ga mypy qo'shishni imkonli qiladi.
