# BuildControl Mobile (Android)

`buildcontrol/` desktop dasturining **native Android ilovasi**. Prorab, omborchi va
loyiha rahbari uchun — obyektda, internetsiz ham ishlaydi.

Telefon o'z **lokal Room (SQLite) bazasini** yuritadi va kompyuterdagi BuildControl bilan
**bir xil sinxronizatsiya protokoli** orqali ma'lumot almashadi.

---

## 1. Nimalar bor

| Ekran | Nima qiladi |
|---|---|
| **Kirish** | desktopdagi bcrypt parollari bilan (`admin/admin123`), rollar bir xil |
| **Loyihalar** | qidiruv, budjet vs amaldagi xarajat, budjet sarfi indikatori, kechikish/tasdiq belgilari |
| **Loyiha → Holat** | budjet, amaldagi xarajat, qolgan mablag', smeta jami, ombordan chiqim, bosqichlar, bajarilish |
| **Loyiha → Smeta** | daraxtsimon bo'lim/kichik bo'lim/band, reja↔fakt, band qo'shish va tahrirlash |
| **Loyiha → Xaridlar** | talab yaratish (smeta bandi yoki "smetadan tashqari"), takliflar, eng yaxshi taklif, tasdiqlash |
| **Loyiha → Ombor** | loyiha bo'yicha kirim/chiqim |
| **Loyiha → Bosqichlar** | bosqichlar, avtomatik "kechikkan", kundalik nazorat jurnali |
| **Loyiha → Xarajatlar** | xarajat kiritish, tasdiqlash/rad etish, to'lash |
| **Ombor** | materiallar katalogi + qoldiq, minimal qoldiq ogohlantirishi, harakatlar |
| **Xarajatlar** | barcha loyihalar bo'yicha, status filtri |
| **Sozlamalar** | til (uz/en), sinxronizatsiya, holat paneli, chiqish |

Rollar va ruxsatlar desktop bilan **bir xil**: smetachi tasdiqlay olmaydi, kuzatuvchi
faqat o'qiydi, omborchi ombor harakatlarini yuritadi.

## 2. O'rnatish

Tayyor APK: `app/build/outputs/apk/release/app-release.apk`
(debug kalit bilan imzolangan — telefonga to'g'ridan-to'g'ri o'rnatiladi).

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
```

Yoki APK faylni telefonga tashlab, "Noma'lum manbalar"ga ruxsat berib o'rnating.

Talab: **Android 8.0 (API 26)** va yuqorisi.

## 3. Sinxronizatsiyani ulash

Eng oson yo'l — **MQTT broker** (bepul, ro'yxatdan o'tish kerak emas):

1. Telefonda: **Sozlamalar → Sinxronizatsiya**
   * *Ulanish turi* = `MQTT broker (bepul, ro'yxatdan o'tmasdan)`
   * *Broker* = `HiveMQ (ommaviy, TLS)` — yoki EMQX / Mosquitto
   * *Ish maydoni kaliti* va *Shifrlash paroli* — kompyuterdagi bilan **bir xil**
2. `Saqlash` → `Ulanishni tekshirish` → `Hozir sinxronlash`.
3. Endi kompyuterdagi login/parol bilan kirasiz.

Supabase ham qo'llab-quvvatlanadi: *Ulanish turi* = `Supabase (internet)`, keyin URL va
anon kalitini kompyuterdagi kabi kiriting.

> Ommaviy broker hammaga ochiq — ish maydoni kalitini uzun qiling va shifrlash parolini
> yoqing (payloadlar AES-256-GCM bilan sealed bo'ladi).

Yuqori o'ng burchakdagi ⟳ tugmasi qo'lda sinxronlaydi; yonidagi sariq raqam —
hali yuborilmagan o'zgarishlar soni. Ilova fonga chiqib qaytganda avtomatik sinxronlanadi.

## 4. Qanday ishlaydi

```
Telefon (Room/SQLite) ──push──►  umumiy jurnal  ◄──push── Kompyuter (SQLite)
                      ◄─pull──   MQTT / Supabase   ──pull──►
```

MQTT'da har bir yozuv o'z mavzusida `retain` bilan turadi (`buildcontrol/<ish-maydoni>/<Entity>/<uid>`), shuning uchun yangi telefon obuna bo'lishi bilan to'liq nusxani oladi.

* Har bir yozuvda global `uid` va `sync_ts` bor; tashqi kalitlar jurnalda `uid` orqali
  yuriladi, shuning uchun lokal `id` har qurilmada boshqacha bo'lsa ham bog'lanish buzilmaydi.
* Konflikt — **last-write-wins** (`sync_ts` bo'yicha).
* Ikki qurilma mustaqil yaratgan bir xil yozuv (`username`, `code`, `sku`) tabiiy kalit
  bo'yicha **birlashtiriladi**; har biri o'z `uid`ini saqlab qoladi va ikkinchisiniki
  `sync_uid_alias` jadvaliga yoziladi — shu sababli qarama-qarshi tomonning tashqi
  kalitlari ham to'g'ri hal bo'ladi.
* Sana/vaqt formati Python tomoni bilan aynan bir xil: `{"__dt__": "..."}` va `{"__d__": "..."}`.

## 5. Build

```powershell
$env:JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"
.\gradlew.bat :app:assembleRelease
```

Talab: **JDK 21** (Android Studio ichidagi JBR mos keladi — JDK 25 AGP'ni buzadi),
Android SDK 35, AGP 8.7.2, Kotlin 2.0.21.

## 6. Testlar

```powershell
.\gradlew.bat :app:testDebugUnitTest
```

| Test to'plami | Nimani qulflaydi |
|---|---|
| `SchemaCompatibilityTest` | Python `app.sync.registry`'dan eksport qilingan `desktop_schema.json` bilan jadval/ustun/tashqi kalitlar aynan mos |
| `WireFormatTest` | jurnal konverti, ISO vaqt formati, ruxsatlar matritsasi, pudratchi reytingi |
| `ReplicationRoundTripTest` | ikkita haqiqiy Room bazasi o'rtasida yaratish/tahrir/o'chirish, FK tiklanishi, LWW, tabiiy kalit birlashuvi, exo-tsikl yo'qligi |

## 7. Arxitektura

```
app/src/main/java/uz/buildcontrol/mobile/
  BuildControlApp.kt      # DI konteyner
  SyncManager.kt          # fon sinxronizatsiyasi va holati
  core/                   # i18n (uz/en), formatlash
  domain/                 # enum'lar, ruxsatlar, hisob formulalari
  data/
    db/                   # Room entity'lari (desktop sxemasining nusxasi), DAO
    sync/                 # spec, codec, transport (Supabase/PostgREST), engine, outbox
    repo/                 # business logic (desktop servislarining analogi)
  ui/
    theme/                # desktop palitrasi (#111827 / #3B82F6 ...)
    components/           # BcCard, Badge, MetricTile, Picker, FormSheet ...
    screens/              # login, projects, project (6 tab), warehouse, expenses, settings
```

## 8. Cheklovlar

* **Fayl biriktirmalari** sinxronlanmaydi (yozuv sinxronlanadi, faylning o'zi emas).
* PDF/Excel hisobotlar faqat desktopda.
* Smeta versiyalari va Excel import mobil ilovada yo'q — desktop ishi.
* Test bosqichida `http://10.0.2.2` va `localhost` uchun cleartext ruxsat berilgan
  (`res/xml/network_security_config.xml`); real Supabase HTTPS orqali ishlaydi.
