# LeadPilot AI

**AI sotuv operatori va lead boshqaruv tizimi** — Windows 10/11 uchun yagona, to‘liq dark-theme
Python desktop CRM. Telegram, Instagram, WhatsApp, website chat va telefon qo‘ng‘iroqlaridan
kelgan leadlarni bitta ish oynasida qabul qiladi, AI bilan javob beradi, bron yaratadi,
operatorga eskalatsiya qiladi va reklama manbalari bo‘yicha ROI hisoblaydi.

> Web dashboard emas — bitta yaxlit PySide6 desktop ilova. Internet va API kalitlarisiz ham
> **Demo/Sandbox rejimda** barcha oqimlar to‘liq ishlaydi.

---

## 1. Imkoniyatlar

| Modul | Nima qiladi |
|---|---|
| **Yagona Inbox** | 3 ustunli messenger workspace: kanal/status filtrlari, chat tarixi, AI tavsiyasi, tezkor javoblar, ichki eslatmalar, fayl biriktirish, bron yaratish, eskalatsiya |
| **Lead CRM** | Qidiruv, 8 filter, bulk amallar, tag, Excel eksport, timeline, dublikat aniqlash va reversible merge |
| **AI sotuv operatori** | uz/ru avtomatik aniqlash, 11 bosqichli holat mashinasi, lead scoring (0–100), eskalatsiya qoidalari, sifat nazorati (foydali/noto‘g‘ri + xato kategoriyasi) |
| **Bilimlar bazasi** | Xizmat/narx/aksiya/FAQ/qoidalar, `AI foydalanishi mumkin` toggle, valid-from/valid-to, PDF/DOCX/TXT biriktirish va matn ekstraktsiyasi |
| **Bronlar** | Kunlik/haftalik/ro‘yxat ko‘rinishi, ikki marta bron qilishning oldini olish, bo‘sh slot taklifi, avtomatik tasdiq va eslatma, kelmagan mijoz follow-up’i |
| **Qo‘ng‘iroqlar** | Demo/Twilio/SIP adapterlari, transkripsiya, AI tahlil (mazmun, e’tirozlar, operator xatolari, keyingi qadam, sifat bahosi, sentiment) |
| **Vazifalar** | Avtomatik qoida dvigateli (15 daq javobsizlik, issiq lead 10 daq, bron eslatmasi, no-show follow-up, overdue) + bildirishnoma markazi |
| **Reklama ROI** | Manba/kampaniya kesimida Lead → Bron → Kelgan → Sotuv → Daromad, CPL/CPB/CPS/ROAS/Conversion, har satrni ochib drill-down |
| **Operatorlar sifati** | Birinchi javob vaqti, konversiya, o‘tkazib yuborilgan follow-up, call quality, AI tavsiyasidan foydalanish, sentiment |
| **Hisobotlar** | 12 ta hisobot, har biri PDF va Excel’ga eksport, sana/kanal/operator/manba/kampaniya/filial/xizmat/status filtrlari |
| **Sozlamalar** | Kompaniya, foydalanuvchilar, rollar, xizmatlar, filiallar, taglar, tezkor javoblar, integratsiyalar (connection test bilan), backup/restore, Excel import/export, audit log |

**Xavfsizlik:** parollar bcrypt bilan hash qilinadi, API kalitlari OS keyring’da saqlanadi
(keyring bo‘lmasa — bazada shifrlangan holda), loglarda kalitlar avtomatik maskalanadi,
har bir muhim amal audit logga yoziladi.

---

## 2. Talablar

* Windows 10/11
* Python **3.12+** (3.13 da sinovdan o‘tgan)

---

## 3. O‘rnatish

```powershell
cd C:\Users\<siz>\Downloads\claude_cowork\leadpilot_ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> Agar `Activate.ps1` ishga tushmasa:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

---

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

Boshqa demo hisoblar: `rahbar/rahbar123` (sotuv rahbari), `dilnoza/dilnoza123` va
`jamshid/jamshid123` (operatorlar), `analitik/analitik123` (analitik).

Birinchi ishga tushishda baza `MedLine Clinic` demo ma’lumotlari bilan to‘ldiriladi:
4 xizmat, 2 filial, 5 foydalanuvchi, 7 lead, 4 suhbat (AI bron qilgan, eskalatsiya qilingan,
narx e’tirozi, “menga boshqa yozmang”), 4 bron, 2 tahlil qilingan qo‘ng‘iroq,
4 reklama manbasi va byudjetli kampaniyalar.

---

## 5. Klaviatura shortcutlari

| Shortcut | Amal |
|---|---|
| `Ctrl+K` | Global qidiruv |
| `Ctrl+N` | Yangi lead |
| `Ctrl+Enter` | Xabar yuborish (Inbox) |
| `Ctrl+1/2/3` | Inbox / Leadlar / Bronlar |
| `F5` | Joriy sahifani yangilash |

---

## 6. Testlar

```powershell
python -m pytest tests -q
```

Qamrov: lead scoring, status transition, booking conflict, opt-out / Do-Not-Contact,
AI eskalatsiya qoidalari, dublikat aniqlash va merge, role permission,
marketing ROI formulalari, adapter fallback va 12 ta hisobot eksporti.

Kod sifati:

```powershell
python -m ruff check app tests
python -m black app tests
```

---

## 7. Integratsiyalarni sozlash

Sozlamalar → **Integratsiyalar** bo‘limida har bir provider uchun credential maydonlari,
`Ulanishni tekshirish` tugmasi, ulanish holati, oxirgi sinxronizatsiya vaqti va
`Demo adapterdan foydalanish` toggle’i mavjud.

| Provider | Kerakli maydonlar |
|---|---|
| Telegram | `Bot token` (@BotFather) |
| WhatsApp Cloud API | `Phone number ID`, `Access token`, ixtiyoriy `Relay URL` |
| Instagram | `IG account ID`, `Access token`, ixtiyoriy `Relay URL` |
| Website chat | `Relay URL`, `Send URL` |
| Twilio Voice | `Account SID`, `Auth token`, `From number` |
| SIP / PBX | `Base URL`, `API key` |
| LLM (OpenAI-compatible) | `API key`, `Base URL`, `Model` |
| Speech-to-Text | `API key`, `Model` |
| Bitrix24 / amoCRM / Webhook | mos webhook yoki token |

**Muhim:** desktop ilovada ochiq HTTP endpoint yo‘q, shuning uchun WhatsApp/Instagram/website
uchun kiruvchi xabarlar ixtiyoriy **relay URL** orqali (JSON massiv) tortib olinadi.
Telegram esa to‘g‘ridan-to‘g‘ri `getUpdates` bilan ishlaydi.

Credential kiritilmagan bo‘lsa dastur **buzilmaydi** — avtomatik ravishda demo adapterga
o‘tadi va top bar’da holat nuqtasi ranglar bilan ko‘rsatiladi
(kulrang = sozlanmagan, ko‘k = demo, yashil = ulangan, qizil = xatolik).

---

## 8. Windows `.exe` build

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Skript virtual muhit yaratadi, dependency’larni o‘rnatadi, testlarni ishga tushiradi va
PyInstaller bilan `dist\LeadPilotAI\LeadPilotAI.exe` fayl yaratadi.
Build qilingan versiyada baza va loglar `%APPDATA%\LeadPilotAI` papkasida saqlanadi.

---

## 9. Arxitektura

```
leadpilot_ai/
  app/
    main.py            # kirish nuqtasi
    config.py          # Pydantic config (maxfiy ma'lumotsiz)
    bootstrap.py       # logging + DB + seed + QApplication
    database/          # engine, migrations, seed
    models/            # 30+ SQLAlchemy modeli
    repositories/      # so'rovlar qatlami
    services/          # BIZNES MANTIQ (UI ichida mantiq yo'q)
    integrations/      # adapterlar: channels / telephony / llm / crm
    controllers/       # AppContext — event bus va background timerlar
    ui/                # pages, dialogs, widgets, styles, i18n
    reports/           # Excel va PDF generatorlari
    utils/             # dates, formatting, logging, security
  tests/
```

Adapter ierarxiyasi:

```
ChannelAdapter    → Telegram / WhatsApp / Instagram / WebsiteChat / DemoChannel
TelephonyAdapter  → Twilio / SIPProvider / DemoTelephony
LLMProvider       → OpenAICompatible / DemoRuleBased
TranscriberAdapter→ OpenAICompatibleSTT / MockTranscriber
CRMExporter       → InternalCRM / Bitrix24 / amoCRM / Webhook
```

**Qoida:** UI hech qachon tashqi servisga bevosita ulanmaydi — faqat service → adapter orqali.

---

## 10. Biznes qoidalari (qisqacha)

* Telefon raqamlari `+998901234567` ko‘rinishiga normalizatsiya qilinadi; dublikatlar
  telefon / Telegram username / email bo‘yicha aniqlanadi va merge qilinadi (reversible, audit bilan).
* `Stop`, `yozmang`, `не пишите` kabi so‘zlar aniqlansa lead avtomatik **Do Not Contact** bo‘ladi
  va chiquvchi xabarlar bloklanadi.
* AI tasdiqlanmagan narx/chegirma aytmaydi, tibbiy-huquqiy-moliyaviy maslahat bermaydi;
  javobni bilmasa yoki mijoz salbiy kayfiyatda bo‘lsa — operatorga eskalatsiya qiladi.
* Operator javob berishi bilan AI o‘sha suhbatda avtomatik javob berishni to‘xtatadi.
* `Yo‘qotildi` statusi uchun sabab **majburiy**, `Sotuv bo‘ldi` uchun summa va sana kiritiladi.
* O‘chirish o‘rniga har doim arxivlash (soft delete) ishlatiladi.
* Barcha vaqtlar `Asia/Tashkent`, sana formati `01.08.2026`, pul formati `12 500 000 so‘m`.

---

## 11. Muammolarni bartaraf etish

| Holat | Yechim |
|---|---|
| Login oynasi ochilmadi | `logs/leadpilot.log` faylini tekshiring (yoki `%APPDATA%\LeadPilotAI\logs`) |
| “Ulanib bo‘lmadi” xatosi | Integratsiyada `Demo adapterdan foydalanish` ni yoqing — dastur ishlashda davom etadi |
| Bazani noldan boshlash | `leadpilot.db` faylini o‘chiring va dasturni qayta ishga tushiring |
| Boshqa papkada baza saqlash | `LEADPILOT_DATA_DIR` muhit o‘zgaruvchisini belgilang |
