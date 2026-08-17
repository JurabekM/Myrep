# BuildControl

Qurilish va ta'mirlash loyihalari uchun **smeta, xarid, ombor, pudratchi, ish bosqichlari va
real xarajat nazorati** dasturi. Yagona, to'liq dark-tema PySide6 desktop ilovasi.

Har bir kompyuterda **o'z lokal bazasi** bo'ladi va internetsiz to'liq ishlaydi; xodimlar
o'rtasidagi ma'lumot almashinuvi umumiy jurnal orqali **sinxronlanadi** (§4).

*A single-window PySide6 desktop application for construction estimating, purchasing,
warehouse and cost control. Offline-first with multi-device synchronisation, dark theme,
Uzbek/English interface.*

---

## 1. Imkoniyatlar

| Modul | Nima qiladi |
|---|---|
| **Kirish va xavfsizlik** | bcrypt bilan hash qilingan parollar, 5 ta rol, "esda saqlash", audit jurnali |
| **Loyihalar** | pasport, budjet, status, arxivlash, qidiruv/filtrlar, 10 tabli ishchi maydon |
| **Smeta** | daraxtsimon struktura, avtomatik hisob, drag-and-drop, versiyalar, tasdiqlash oqimi, Excel import/eksport, PDF |
| **Xaridlar** | smeta bandiga bog'langan talablar, yetkazib beruvchi takliflari, umumiy qiymat bo'yicha eng yaxshi taklif, PDF buyurtma |
| **Ombor** | materiallar katalogi, kirim/chiqim/qaytarish/inventarizatsiya/yo'qotish, minimal qoldiq ogohlantirishi |
| **Ish bosqichlari** | Gantt timeline, avtomatik "kechikkan" statusi, kundalik nazorat jurnali |
| **Kontragentlar** | pudratchi/yetkazib beruvchi kartochkalari, avtomatik reyting |
| **Xarajatlar** | tasdiqlash oqimi, qisman to'lovlar, budjetdan oshish ogohlantirishi |
| **Hisobotlar** | 11 ta hisobot, har biri PDF va Excel'ga eksport qilinadi |
| **Sinxronizatsiya** | har bir kompyuterda lokal baza + umumiy jurnal orqali almashinuv (MQTT broker, Supabase yoki tarmoq papkasi), offline-first, LWW konflikt yechimi, ixtiyoriy AES-256-GCM shifrlash |
| **Sozlamalar** | kompaniya rekvizitlari, foydalanuvchilar, rollar matritsasi, ma'lumotnomalar, backup/restore, CSV eksport |

### Rollar va ruxsatlar

| Rol | Imkoniyatlar |
|---|---|
| **Administrator** | hammasi (`*`), foydalanuvchi va sozlamalar boshqaruvi |
| **Loyiha rahbari** | loyiha/smeta/xarid/xarajatlarni boshqarish va **tasdiqlash** |
| **Smetachi** | smeta va xarid talablarini yaratish/tahrirlash, **tasdiqlay olmaydi** |
| **Omborchi** | ombor harakatlari, xarid talablari |
| **Kuzatuvchi** | faqat o'qish |

Ruxsat yo'q amallar UI'da bloklanadi **va** servis qatlamida `PermissionDenied` bilan rad etiladi.

---

## 2. O'rnatish

Talab: **Python 3.12+**, Windows 10/11.

```bash
cd buildcontrol
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Ishga tushirish

Loyiha papkasidan (`buildcontrol/`) quyidagilarning **istalgan biri**:

```bash
python run.py
```

```bash
python -m app.main
```

```bash
python app/main.py
```

Birinchi ishga tushirishda baza `%APPDATA%\BuildControl\buildcontrol.db` da yaratiladi va
demo ma'lumotlar bilan to'ldiriladi.

### Demo loginlar

| Login | Parol | Rol |
|---|---|---|
| `admin` | `admin123` | Administrator |
| `rahbar` | `rahbar123` | Loyiha rahbari |
| `smetachi` | `smeta123` | Smetachi |
| `omborchi` | `ombor123` | Omborchi |
| `kuzatuvchi` | `kuzat123` | Kuzatuvchi |

Agar bazada birorta ham foydalanuvchi bo'lmasa, ilova avtomatik ravishda
**"Administrator yaratish"** oynasini ko'rsatadi.

### Demo ma'lumotlar

* **Yunusobod xonadon ta'miri** — 320 mln so'm budjet, tasdiqlangan smeta, budjetdan oshgan band (qizil), tasdiq kutayotgan xarajat (sariq);
* **Samarqand ofis binosi** — 2.45 mlrd so'm budjet, tasdiqlashga yuborilgan smeta, kechikkan bosqich;
* 3 ta yetkazib beruvchi, 2 ta pudratchi, 5 ta material, ombor harakatlari, xarid talablari va takliflari.

## 4. Ko'p kompyuterda ishlash (sinxronizatsiya)

Dastur **offline-first** ishlaydi: har bir kompyuterda to'liq lokal SQLite bazasi bo'ladi,
internet uzilsa ham hamma narsa ishlayveradi. O'zgarishlar umumiy **append-only jurnal**
orqali almashadi.

```
Kompyuter A  ──push──►  ┌─────────────────┐  ◄──push──  Kompyuter B
(lokal SQLite) ◄─pull──  │  umumiy jurnal  │  ──pull──►  (lokal SQLite)
Kompyuter C  ◄─────────►  └─────────────────┘
```

Har bir yozuv global `uid` (UUID) bilan belgilanadi, tashqi kalitlar esa jurnalda
`uid` orqali uzatiladi — shu sababli har bir kompyuterda lokal `id` boshqacha bo'lsa
ham bog'lanishlar to'g'ri tiklanadi.

### 4.1. MQTT broker (tavsiya etiladi — bepul, ro'yxatdan o'tmasdan)

Eng tez yo'l: hech qanday akkaunt, baza yoki server sozlash kerak emas.

1. Dasturda: **Sozlamalar → Sinxronizatsiya** → *Ulanish turi* = `MQTT broker`.
2. *Broker* ro'yxatidan birini tanlang (`broker.hivemq.com:8883` — standart):

   | Broker | Port (TLS) |
   |---|---|
   | `broker.hivemq.com` | 8883 |
   | `broker.emqx.io` | 8883 |
   | `test.mosquitto.org` | 8886 |

3. **Ish maydoni kaliti** — uzun va tasodifiy bo'lsin (masalan `mustahkam-bino-7f3a91c4`).
   Bu sizning firmangizni boshqalardan ajratadi.
4. **Shifrlash paroli** — barcha kompyuter va telefonlarda **bir xil** bo'lsin.
   Yoqilganda ma'lumot AES-256-GCM bilan shifrlanadi va brokerda ochiq ko'rinmaydi.
5. `Ulanishni tekshirish` → `Saqlash`.
6. Birinchi kompyuterda **`Hamma ma'lumotni yuklash`**. Boshqalarida `Hozir sinxronlash`.

**Qanday ishlaydi.** Har bir yozuv o'z mavzusiga `retain` bayrog'i bilan e'lon qilinadi:

```
buildcontrol/<ish-maydoni>/<Entity>/<uid>      retain=1, QoS 1
```

MQTT retained xabarlarni obuna bo'lgan zahoti yetkazadi, shuning uchun **hech qachon
ulanmagan yangi qurilma ham to'liq nusxani oladi** — alohida baza yoki tarix kerak emas.
Keyingi o'zgarishlar jonli ravishda keladi. O'chirish `op="delete"` retained belgisi
sifatida qoladi, shunda keyin ulangan qurilma ham buni biladi.

> **Xavfsizlik.** Ommaviy broker hammaga ochiq: kim mavzuni topsa, o'qiy va yoza oladi.
> Shuning uchun (a) ish maydoni kalitini uzun va tasodifiy qiling, (b) shifrlash parolini
> albatta yoqing. Jiddiy ish uchun o'z brokeringizni (Mosquitto/EMQX) login-parol bilan
> ko'taring — sozlamada foydalanuvchi/parol maydonlari bor.
> Retained xabarlar bepul brokerda kafolatlanmaydi; asosiy nusxa kompyuterda qoladi va
> istalgan payt qayta e'lon qilinadi.

### 4.2. Supabase (bepul Postgres, jurnal saqlanadi)

1. [supabase.com](https://supabase.com) — bepul ro'yxatdan o'ting, yangi loyiha yarating.
2. **SQL Editor** → Sozlamalar → Sinxronizatsiya sahifasidagi SQL'ni nusxalab (`SQL nusxalash`)
   bajaring. U bitta `bc_changes` jadvalini yaratadi.
3. **Settings → API** dan `Project URL` va `anon public` kalitini oling.
4. Dasturda: **Sozlamalar → Sinxronizatsiya** → *Ulanish turi* = `Supabase`, URL va kalitni
   qo'ying, **Ish maydoni kaliti**ga firma nomini yozing (masalan `mustahkam-bino`).
5. `Ulanishni tekshirish` → `Saqlash`.
6. Birinchi kompyuterda **`Hamma ma'lumotni yuklash`** tugmasini bosing — mavjud baza serverga
   yuklanadi. Qolgan kompyuterlarda faqat `Hozir sinxronlash` bosilsa yetadi.

Har bir kompyuterda **bir xil URL, kalit va ish maydoni kaliti** kiritilishi shart.
Turli ish maydoni kalitlari bir-biridan butunlay ajratilgan (bitta Supabase loyihasida
bir nechta firma ishlashi mumkin).

> Xavfsizlik: yuqoridagi SQL test uchun `anon` kalitga to'liq ruxsat beradi. Ishlab
> chiqarishda RLS siyosatini Supabase Auth bilan cheklang yoki o'z serveringizdagi
> PostgREST'ga o'ting — transport bir xil.

### 4.3. Umumiy papka / lokal tarmoq (kalitsiz, internetsiz)

Ofis ichida server yoki umumiy papka bo'lsa: *Ulanish turi* = `Umumiy papka`, manzil
sifatida `\\server\buildcontrol` ni ko'rsating. Hech qanday ro'yxatdan o'tish kerak emas.
Bir xil papkani ko'rsatgan hamma kompyuterlar sinxronlanadi.

### 4.4. Qanday ishlaydi

| Savol | Javob |
|---|---|
| Internet yo'q bo'lsa? | Ishlayveradi. O'zgarishlar `sync_outbox`da to'planadi va ulanish tiklangach yuboriladi. |
| Ikki kishi bitta yozuvni o'zgartirsa? | **Last-write-wins**: `sync_ts` bo'yicha kechroq yozilgani qoladi, eskisi hisobotda `↺` sifatida ko'rsatiladi. |
| Ikki kompyuterda bir xil login/loyiha kodi yaratilsa? | Tabiiy kalit (`username`, `code`, `sku`, `kind+code`) bo'yicha **birlashtiriladi**, dublikat yaratilmaydi. |
| O'chirish tarqaladimi? | Ha. Lekin dastur asosan arxivlashdan foydalanadi, shuning uchun o'chirish kamdan-kam. |
| Demo ma'lumotlar serverga ketadimi? | Yo'q. Ular lokalda qoladi; real ma'lumotni `Hamma ma'lumotni yuklash` bilan e'lon qilasiz. |
| Yangi kompyuter qo'shilsa? | Sozlamani kiritib `Hozir sinxronlash` — butun jurnal boshidan o'qiladi. |
| Fayllar (foto, hujjat) sinxronlanadimi? | Yozuv sinxronlanadi, faylning o'zi emas — fayllarni umumiy papkada saqlang. |

Yuqoridagi sarlavhada sinxronizatsiya indikatori turadi: `✓` — tartibda, `⟳` — jarayonda,
`!` — xato, yonidagi raqam yuborilmagan o'zgarishlar soni. Uni bosish qo'lda sinxronlashni
boshlaydi.

## 5. Testlar

```bash
python -m pytest -q
```

Testlar qamrovi: smeta hisoblari va versiyalash, ombor qoldig'i va yetarsiz qoldiq bloklash,
rol ruxsatlari, budjet ogohlantirishi, xarid qoidalari, pudratchi reytingi, bosqich kechikishi,
PDF/Excel generatsiyasi va Excel import.

MQTT transporti `broker.hivemq.com` bilan jonli sinaladi (`tests/test_sync_mqtt.py`; broker mavjud bo'lmasa test o'tkazib yuboriladi), shifrlash esa har doim tekshiriladi.

**Sinxronizatsiya testlari** ikkita mustaqil "qurilma" (alohida bazalar) o'rtasida haqiqiy
almashinuvni tekshiradi: yaratish/tahrirlash/o'chirishning tarqalishi, tashqi kalitlarning
`uid` orqali tiklanishi, LWW konflikt yechimi, tabiiy kalit bo'yicha birlashtirish,
o'z o'zgarishlarini qayta qo'llamaslik. Supabase transporti lokal PostgREST emulyatori
orqali (`tests/test_sync_supabase.py`) HTTP darajasida sinaladi.

## 6. Kod sifati

```bash
python -m ruff check .
python -m black .
```

## 7. `.exe` build (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Natija: `dist\BuildControl\BuildControl.exe` (papkali build) yoki `-OneFile` bayrog'i bilan
`dist\BuildControl.exe`.

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -OneFile -Clean
```

---

## 8. Arxitektura

```
buildcontrol/
  app/
    main.py                 # kirish nuqtasi
    config.py               # yo'llar, valyuta, sana formati
    database/               # engine, sessiya, migratsiya
    models/                 # SQLAlchemy entity'lari va enum'lar
    repositories/           # so'rovlar (commit qilmaydi)
    services/               # business logic + ruxsatlar + audit
    controllers/            # ilova holati (joriy foydalanuvchi, sozlamalar)
    ui/
      main_window/          # frameless oyna, title bar, sidebar
      pages/                # sahifalar va loyiha tablari
      dialogs/              # BaseDialog + deklarativ FormDialog
      widgets/              # DataTable, Gantt, Card, Badge, Toast, ikonlar
      styles/               # dizayn token'lari va global QSS
    reports/                # PDF (reportlab) va Excel (openpyxl)
    sync/                   # replikatsiya: outbox, engine, transportlar
    utils/                  # i18n, formatlash, xavfsizlik, fayllar
  tests/
```

**Qatlamlar qoidasi:** UI faqat `services` bilan gaplashadi; `services` `repositories` orqali
bazaga kiradi; `repositories` hech qachon commit qilmaydi — tranzaksiyani
`session_scope()` boshqaradi. UI ichida hisob-kitob yozilmaydi.

### Asosiy business qoidalar

* Xarid talabi smeta bandisiz yaratilmaydi (`off_estimate` bayrog'idan tashqari).
* Tasdiqlangan smeta tahrirlanmaydi — o'zgartirish uchun yangi versiya yaratiladi (daraxt klonlanadi, amaldagi xarajatlar nolga tushadi).
* Xarajat tasdiqlanganda yoki material chiqim qilinganda smeta bandining amaldagi qiymati qayta hisoblanadi.
* Budjetdan oshish faqat ogohlantiradi — tizim xaridni to'xtatmaydi, qaror rahbarda.
* O'chirish o'rniga arxivlash (soft-delete) ishlatiladi.
* Har bir pulga oid amal audit jurnaliga yoziladi.
* Har bir lokal o'zgarish o'z tranzaksiyasida `sync_outbox`ga tushadi — commit bo'lmagan
  o'zgarish hech qachon yuborilmaydi, commit bo'lgani esa yo'qolmaydi.

### Hisob-kitob formulalari

```
Reja jami       = miqdor × reja birlik narxi
Amaldagi jami   = tasdiqlangan/to'langan xarajatlar + ombordan chiqim qiymati
Farq            = amaldagi jami − reja jami
Farq foizi      = farq / reja jami × 100
Qoldiq mablag'  = budjet − amaldagi xarajat
Taklif qiymati  = mahsulot narxi × miqdor + yetkazish xarajati
Eng yaxshi taklif = 0.7 × narx_bahosi + 0.3 × muddat_bahosi (kichigi yaxshi)
Pudratchi reytingi = 0.4×vaqt + 0.2×narx + 0.3×sifat + 0.1×nizolar   (0..5)
```

### Ranglar

| Element | Rang |
|---|---|
| Asosiy fon | `#111827` |
| Yon menyu | `#0D131F` |
| Card / jadval | `#1E293B` |
| Aksent | `#3B82F6` |
| Muvaffaqiyat / Ogohlantirish / Muammo | `#22C55E` / `#F5B342` / `#EF4444` |

Qizil: smetadan oshgan band, manfiy qoldiq, kechikkan bosqich.
Sariq: tasdiqlanmagan xarajat, xarid talab qiladigan band, minimal qoldiqdan kam material.

## 9. Ma'lumotlar joylashuvi

| Nima | Qayerda |
|---|---|
| Baza | `%APPDATA%\BuildControl\buildcontrol.db` |
| Zaxira nusxalar | `%APPDATA%\BuildControl\backups\` |
| Biriktirilgan fayllar | `%APPDATA%\BuildControl\files\` |
| Hisobotlar | `%APPDATA%\BuildControl\reports\` |
| Log | `%APPDATA%\BuildControl\buildcontrol.log` |

Bazani nolga qaytarish uchun `buildcontrol.db` faylini o'chiring — ilova qayta ishga
tushganda demo ma'lumotlar bilan yangidan yaratiladi.

## 10. Tillar

Interfeys **o'zbek** va **ingliz** tillarida. Til yuqoridagi title bar'dagi ro'yxatdan
almashtiriladi; tanlov `QSettings` orqali saqlanadi. Kod, nomlar va kommentariyalar inglizcha.
