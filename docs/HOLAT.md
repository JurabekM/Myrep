# Loyiha holati — halol hisobot

Bu hujjat «nima tayyor» degan savolga **o'zini maqtamasdan** javob
beradi. «Test o'tdi» va «ishlaydi» — ikki xil narsa, shuning uchun har
qator uchun **qanday tekshirilgani** ko'rsatilgan.

Sana: 2026-08-23

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

### 5.2. Unumdorlik

Topshiriqdagi mezonlar (100 000 mahsulot, 1 million hodisa, 50 000
mahsulotli mobil katalog) **o'lchanmagan**. Indekslar qo'yilgan, lekin
benchmark yo'q. Desktop ishga tushishi o'lchandi: 1.1 s.

### 5.3. Haqiqiy qurilma

Faqat emulyator (Medium_Phone_API_36) sinaldi — lekin **haqiqiy ochiq
broker orqali**, soxta transport bilan emas. Haqiqiy telefonda —
xususan zaif qurilmada va yomon tarmoqda — sinalmagan.

### 5.4. Lokal konteynerli MQTT broker

Integratsion testlar uchun Mosquitto/HiveMQ CE konteyneri **sozlanmagan**.
Hozircha sinxronizatsiya mantiqi soxta transport ustida sinaladi.

### 5.5. Boshqalar

* Alembic migratsiyalari yozilmagan (hozircha `create_all`);
* ovozli buyurtma (speech-to-text) — yo'q;
* tashqi AI provayder abstraksiyasi — faqat lokal maslahatchi bor;
* uz-Kirill va rus tillari — kalitlar tayyor, tarjimalar yo'q;
* CI (GitHub Actions) — sozlanmagan;
* soak test — bajarilmagan.

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

Ustuvorlik tartibida:

1. QR provisioning oqimini ikkala tomonda tugatish — hozir bu yagona
   uzilgan halqa.
2. Lokal konteynerli broker bilan integratsion test.
3. Unumdorlik o'lchovi (100k mahsulot, 1M hodisa).
4. Alembic migratsiyalari — sxema o'zgarishi ma'lumotni yo'qotmasin.
5. DES-1 uchun mustaqil kriptografik ko'rib chiqish.
