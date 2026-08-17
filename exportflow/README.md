# ExportFlow

Windows uchun yagona, dark-theme, professional **desktop** eksport savdo dasturi.
O'zbekiston ishlab chiqaruvchilari uchun: ko'p tilli mahsulot katalogi, xorijiy
xaridorlar CRM'i, RFQ/quotation, AI kontent, eksport checklist, sertifikatlar,
logistika, follow-up va shartnomalar — bitta ishchi interfeysda.

* Web sayt emas, web dashboard emas — **PySide6 desktop ilova**.
* Lokal **SQLite** baza, internetsiz ham to'liq ishlaydi (**Demo rejim**).
* Interfeys **o'zbek / rus / ingliz** tillarida, dastur ichidan almashtiriladi.
* Kod, fayl nomlari va kommentariyalar — ingliz tilida.

---

## 1. Talablar

| Komponent | Versiya |
|-----------|---------|
| Windows   | 10 yoki 11 |
| Python    | 3.12+ (3.13 da sinovdan o'tgan) |

## 2. O'rnatish

```powershell
cd exportflow
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Bog'liqliklar

`PySide6`, `QtAwesome`, `SQLAlchemy`, `pydantic`, `openpyxl`, `reportlab`,
`Jinja2`, `httpx`, `bcrypt`, `keyring`, `pytest`, `ruff`, `black`, `PyInstaller`.

## 3. Migratsiya va demo ma'lumotlar

Alohida buyruq shart emas: dastur birinchi ishga tushganda
`app/bootstrap.py` avtomatik ravishda

1. baza jadvallarini yaratadi (`app/database/migrations.py`, `schema_version`),
2. ma'lumotnomalarni seed qiladi (rollar, huquqlar, kategoriyalar, chek-list va
   email shablonlari, integratsiya konfiguratsiyalari),
3. bo'sh bazada **demo ma'lumotlarni** yozadi,
4. texnik xizmatni bajaradi (muddati o'tgan narx/taklif, sertifikat holatlari,
   follow-up vazifalari).

Qo'lda ishga tushirish kerak bo'lsa:

```powershell
python -c "from app.bootstrap import bootstrap; print(bootstrap())"
```

## 4. Ishga tushirish

```powershell
python -m app.main
```

yoki

```powershell
python app\main.py
```

### Demo login

```
Username: admin
Password: admin123
```

Boshqa demo hisoblar (parol `demo12345`): `dilshod` (Export Manager),
`nigora` (Sales Manager), `bekzod` (Logistics), `kamola` (Catalog Manager),
`viewer` (faqat ko'rish).

Agar bazada foydalanuvchi bo'lmasa, login oynasi **birinchi administrator**
yaratish rejimiga o'tadi.

### Ma'lumotlar qayerda saqlanadi

`%LOCALAPPDATA%\ExportFlow\`

```
exportflow.db      SQLite baza
logs/              rotatsiyali loglar (maxfiy kalitlar redaksiya qilinadi)
exports/           katalog, hisobot, quotation, backup fayllari
attachments/       biriktirilgan fayllar
outbox/            Demo email outbox (.txt)
```

`EXPORTFLOW_HOME` muhit o'zgaruvchisi bilan boshqa papkaga ko'chirish mumkin.

## 5. Testlar

```powershell
python -m pytest -q
```

50 ta test: quotation hisob-kitobi, narx amal qilishi, sertifikat muddati
alertlari, chek-list avto-shabloni, dublikat xaridor aniqlash, quotation
tasdiqlash huquqi, shipment status o'tishlari, follow-up qoidasi, rol huquqlari,
katalog HTML/PDF/ZIP generatsiyasi va to'liq demo oqimi (`tests/test_demo_flow.py`).

Lint va format:

```powershell
python -m ruff check app tests
python -m black app tests
```

## 6. Modullar

| Sahifa | Nima qiladi |
|--------|-------------|
| Ish maydoni | Bugungi vazifalar, follow-up'lar, ogohlantirishlar, metrikalar |
| Mahsulotlar | PIM: 3 tilli tavsif, HS code, MOQ, qadoqlash, media, eksport tayyorgarligi |
| Narxlar va Incoterms | EXW/FOB/CIF… narxlari, amal qilish muddati, tasdiqlash |
| Kataloglar | Katalog studiyasi → PDF / statik HTML / ZIP eksport |
| AI kontent studiyasi | 13 tur kontent, 3 til, fakt manbalari, versiya tarixi |
| Xaridorlar | Buyer CRM, dublikat aniqlash, 360° detal panel |
| Leadlar | 15 status, filtrlar, ommaviy biriktirish, lead import |
| Savdo quvuri | Kanban, drag-and-drop bosqich almashtirish |
| So'rovlar (RFQ) | Xaridor so'rovlari va pozitsiyalari |
| Takliflar | Quotation workflow: draft → review → approved → sent |
| Shartnomalar | Imzolangan shartnomalar reyestri |
| Chek-listlar | Eksport tayyorgarligi, 11 kategoriya, avto-shablonlar |
| Sertifikatlar | Muddat alertlari (60/30/7 kun), fayl preview |
| Logistika | Shipment, ETD/ETA, forwarder takliflari, invoice/packing list |
| Email va follow-up | Shablon, AI draft, javob kutayotganlar, vazifalar |
| Agentlar va natijalar | Agent kartochkasi, menejer/agent performance |
| Hisobotlar | 18 hisobot, PDF va Excel eksport |
| Sozlamalar | Kompaniya, foydalanuvchilar, rollar, integratsiyalar, backup, audit |

### Klaviatura shortcutlari

`Ctrl+K` global qidiruv · `Ctrl+N` yangi yozuv · `Ctrl+Q` yangi quotation ·
`Ctrl+S` saqlash · `Ctrl+E` eksport · `F5` yangilash.

## 7. Statik katalog eksporti

Katalog studiyasi → **Statik HTML eksport**. Natija:

```
catalog/
  index.html            mahsulot kartalari, sertifikatlar, kontaktlar
  products/<slug>.html  har mahsulot uchun alohida sahifa
  assets/style.css      responsive dark/light tema
  assets/<rasm>         mahsulot fotolari va logo (lokal nusxa)
```

Backend talab qilinmaydi — `index.html` ni brauzerda ochib tekshirish yoki
istalgan hostingga (Netlify, GitHub Pages, oddiy nginx) yuklash mumkin.
"Request a Quote" tugmasi kompaniyaning eksport bo'limi emailiga `mailto:`
havolasi bilan bog'langan. **ZIP eksport** — o'sha papkaning arxivi.

PDF katalog: muqova, kompaniya haqida, sertifikatlar sahifasi, mahsulot fotosi,
spetsifikatsiya, MOQ, qadoqlash, kontaktlar va sahifa raqamlari.

## 8. Integratsiyalar (adapter arxitekturasi)

```
LLMProvider          DemoRuleBasedProvider (offline) | OpenAICompatibleProvider
EmailProvider        DemoOutboxProvider (offline)    | SMTPProvider
LeadImportProvider   DemoLeadProvider (offline) | CSVImportAdapter |
                     AlibabaImportAdapter | LinkedInImportAdapter
CRMProvider          WebhookAdapter | Bitrix24Adapter | AmoCRMAdapter
```

**Credential bo'lmasa ilova buzilmaydi** — `integration_service.build_provider`
avtomatik Demo provayderga qaytadi va titul panelida "Demo rejim" ko'rsatiladi.

### AI (LLM) ulash

Sozlamalar → Integratsiyalar → `llm` qatorini ikki marta bosing →
`OpenAI-compatible API` ni tanlang va to'ldiring:

| Maydon | Misol |
|--------|-------|
| `base_url` | `https://api.openai.com/v1` |
| `model` | `gpt-4o-mini` |
| `api_key` | **maxfiy** — Windows credential manager'ga yoziladi |

"Ulanishni tekshirish" tugmasi holatni yangilaydi. AI qoidalari: generator
faqat bazadagi faktlardan foydalanadi; sertifikat yo'q bo'lsa "certified" deb
yozmaydi; MOQ, narx, lead time va Incoterms to'qib chiqarilmaydi. Har bir matn
tarixga yoziladi va foydalanuvchi tasdiqlashi kerak.

### Email (SMTP) ulash

`smtp` provayderi: `host`, `port`, `username`, `password` (maxfiy),
`from_address`, `use_tls`/`use_ssl`. Sozlanmagan bo'lsa xatlar
`%LOCALAPPDATA%\ExportFlow\outbox\` ga `.txt` sifatida saqlanadi.

### Xavfsizlik

* Parollar bcrypt bilan hash qilinadi (bcrypt yo'q bo'lsa PBKDF2-SHA256).
* API kalitlari va SMTP parollari **hech qachon bazaga yoki logga yozilmaydi** —
  faqat OS keyring'da (`keyring`), bazada esa faqat havola saqlanadi.
* Loglarda `api_key`, `token`, `password` kabi qiymatlar avtomatik `***` ga
  almashtiriladi (`RedactingFilter`).
* O'chirish o'rniga soft delete/archive; barcha muhim o'zgarishlar audit logda.

## 9. Windows `.exe` build

```powershell
.\build_exe.ps1
```

Bir faylli build va tozalash bilan:

```powershell
.\build_exe.ps1 -OneFile -Clean
```

Natija: `dist\ExportFlow\ExportFlow.exe` (yoki `-OneFile` da
`dist\ExportFlow.exe`). Skript virtual muhit yaratadi, bog'liqliklarni
o'rnatadi, `app/templates` va `app/resources` ni bundle'ga qo'shadi va keraksiz
Qt modullarini chiqarib tashlaydi.

## 10. Arxitektura

```
app/
  main.py           kirish nuqtasi, QApplication, login → MainWindow
  bootstrap.py      migratsiya + seed + texnik xizmat
  config.py         yo'llar, valyutalar, tillar, timezone
  database/         engine.py, migrations.py, seed.py
  models/           35+ SQLAlchemy 2.0 modeli
  repositories/     generic CRUD (session'siz commit qilmaydi)
  services/         BARCHA biznes qoidalari shu yerda
  integrations/     llm / email / crm / marketplace adapterlari + registry
  controllers/      AppContext: joriy user, sessiya, signal bus
  ui/               main_window, pages, dialogs, widgets, styles, i18n
  reports/          reportlab PDF, openpyxl Excel, jinja2 HTML katalog
  templates/        catalog/*.j2, base.css
  utils/            formatting, enums, errors, security, logging
tests/
```

Qoida: **UI ichida biznes logika yozilmaydi.** Sahifalar `AppContext.run()`
orqali servis funksiyalarini chaqiradi, servis esa `session_scope()` tranzaksiya
ichida ishlaydi va DTO (dict) qaytaradi.

### Asosiy biznes qoidalar

* Quotation'ga faqat **tasdiqlangan va amal qilayotgan** narx qo'shiladi.
* FOB/CIF/CFR/FCA/CPT/CIP uchun **port yoki yuklash joyi majburiy**.
* Quotation **Approved bo'lmasdan yuborilmaydi**; tahrirlash uni qayta
  tekshiruvga qaytaradi.
* Deal `Won` — shartnoma talab qilinadi; `Lost` — sabab majburiy.
* Shipment status o'tishlari state machine bilan cheklangan; `Delivered`
  bo'lgandan keyingina real daromad kiritiladi.
* Sertifikat muddati 60 / 30 / 7 kun qolganda vazifa yaratiladi.
* Quotation yuborilgandan 3 kun, sample'dan 5 kun keyin follow-up vazifasi.
* Sana formati `01.08.2026`, vaqt zonasi `Asia/Tashkent`, baza valyutasi USD.

## 11. Muammolarni bartaraf etish

| Belgi | Yechim |
|-------|--------|
| `ModuleNotFoundError: app` | Loyiha ildizidan (`exportflow/`) ishga tushiring |
| Login o'tmaydi | `%LOCALAPPDATA%\ExportFlow\exportflow.db` ni o'chirib qayta ishga tushiring — demo baza qaytadan yaratiladi |
| Keyring ishlamaydi | Kalitlar `credentials.local.json` ga base64 bilan yoziladi; fayl himoyalangan foydalanuvchi papkasida |
| PDF'da kirill/o'zbek harflari | Standart Helvetica shrifti ishlatiladi; maxsus shrift kerak bo'lsa `app/reports/pdf_base.py` ga `pdfmetrics.registerFont` qo'shing |
| Loglar | `%LOCALAPPDATA%\ExportFlow\logs\exportflow.log` |
