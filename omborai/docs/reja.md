# OmborAI: loyiha rejasi (qoralama, tasdiqlash uchun)

Kichik do'konlar uchun ombor, kassa (savdo), qarz daftari va hisobotlar. Desktop (Python) va mobil (Flutter + Kotlin) ilovalar bitta backend va bitta ma'lumot manbaiga ulangan. Ilova offline ham ishlaydi va internet qaytganda ma'lumotni o'zi sinxronlaydi.

---

## 1. Texnologiya tanlovi

| Qism | Tanlov | Sabab |
|---|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic | Desktop ham Python, bitta til. OpenAPI avtomatik chiqadi |
| Ma'lumotlar bazasi | PostgreSQL 16 | Tranzaksiya, RLS, JSONB, ishonchlilik |
| Fon vazifalari | Celery + Redis | Hisobot, Telegram xabar, webhook qayta ishlash |
| Desktop UI | Python + PySide6 (Qt 6) | Barqaror, printer va skaner bilan ishlaydi, `.exe` ga yig'iladi |
| Desktop lokal baza | SQLite + FTS5 | Offline ishlash, 10 000+ tovar bo'yicha tez qidiruv |
| Mobil UI | Flutter (Dart 3), Riverpod, go_router | Bitta UI kodi, Android va keyinchalik iOS |
| Mobil native qism | Kotlin (Android platform channel) | Shtrix-kod skaneri (CameraX/ML Kit), Bluetooth printer, foreground sync |
| Mobil lokal baza | Drift (SQLite) | Offline, Flutter bilan tayyor integratsiya |
| Auth | JWT (access 15 daqiqa, refresh 30 kun, rotatsiya), qurilma ro'yxati | Qurilmani masofadan bekor qilish mumkin |
| Infratuzilma | Docker Compose, Caddy (avtomatik TLS), VPS | Sodda, arzon, ko'chirish oson |
| CI/CD | GitHub Actions | Repo GitHub'da |
| Kuzatuv | Sentry (xatolar), JSON loglar, UptimeRobot | Minimal, lekin production uchun yetarli |

**Eslatma:** "Mobil uchun kotlin+flutter" ni men shunday tushundim: UI Flutter'da, Android'ga xos qismlar (skaner, printer, fon sinxronizatsiyasi) Kotlin'da yoziladi. Agar siz ikkita alohida native ilova (Android uchun Kotlin, iOS uchun boshqa) nazarda tutgan bo'lsangiz, reja o'zgaradi. Buni tasdiqlashingizni so'rayman.

---

## 2. Arxitektura

```
 [Desktop: PySide6 + SQLite] ──┐
                               ├── HTTPS / JSON ──> [Caddy] ──> [FastAPI]
 [Mobil: Flutter + Drift] ─────┘                        │          │
                                                 [PostgreSQL]  [Redis + Celery]
                                                        │          │
                                              [Click / Payme]   [Telegram bot]
```

**Offline-first printsip:** har bir klient avval o'z lokal bazasiga yozadi va yozuvni "outbox" jadvaliga qo'yadi. Fon ishchisi (worker) uni serverga yuboradi. Internet bo'lmasa sotuv to'xtamaydi.

---

## 3. Ma'lumot modeli (asosiy jadvallar)

- `tenants`: do'kon egasi (hisob).
- `stores`: filial/do'kon. Bir tenant'da bir nechta bo'lishi mumkin.
- `users`, `roles`, `user_store_roles`: rollar: Egasi, Menejer, Kassir, Omborchi, Ko'ruvchi.
- `devices`: desktop va mobil qurilmalar, token, oxirgi faollik.
- `products`, `categories`, `units`, `product_barcodes`: bir tovarda bir nechta shtrix-kod bo'lishi mumkin.
- **`stock_movements`**: ombor qoldig'ining manbai. Qoldiq = `SUM(qty)`. Kirim, sotuv, qaytarish, tuzatish, yo'qotish, ko'chirish, hammasi shu yerda. Bu konfliktlarni kamaytiradi va har bir o'zgarish izli bo'ladi.
- `suppliers`, `purchases`, `purchase_items`: kirim hujjatlari.
- `shifts`: kassa smenasi (ochish, yopish, naqd hisob).
- `sales`, `sale_items`, `payments`: chek va to'lovlar. `sale_items.unit_price` tarixiy narxni saqlaydi, keyin narx o'zgarsa ham eski chek o'zgarmaydi.
- `customers`, `debts`, `debt_payments`: qarz daftari.
- `audit_log`: kim, qachon, nimani o'zgartirdi (narx, chegirma, qoldiq tuzatish, o'chirish).
- `sync_ops`: `idempotency_key` (UUID) unique, dublikatlarni rad etish uchun.
- `subscriptions`, `invoices`: tarif va to'lovlar.

Har jadvalda: `id` (UUID v7), `tenant_id`, `created_at`, `updated_at`, `deleted_at` (soft delete), `version`.

---

## 4. Sinxronizatsiya

- **ID:** klient UUID v7 yaratadi. Shunda offline ham yozuvni yaratish mumkin, serverda to'qnashuv bo'lmaydi.
- **Push:** `POST /v1/sync/push`. Outbox elementlari ro'yxati keladi. Server har birini `idempotency_key` bo'yicha tekshiradi. Dublikat bo'lsa xatolik emas, "allaqachon qabul qilingan" deb javob beradi.
- **Pull:** `GET /v1/sync/pull?cursor=...`. Server global monoton `change_seq` bo'yicha o'zgarishlarni qaytaradi.
- **Konflikt siyosati:**
  - Sotuv, to'lov va `stock_movements` faqat qo'shiladi (append-only). Konflikt bo'lmaydi.
  - Tovar nomi, narxi kabi tahrirlanadigan yozuvlar: `version` maydoni bo'yicha optimistik qulflash. Konflikt bo'lsa, server versiyasi saqlanadi, mahalliy o'zgarish alohida "konflikt" yozuvi sifatida egasiga ko'rsatiladi.
- **Vaqt:** server vaqti asosiy. Mahalliy vaqt faqat ko'rsatish uchun.

---

## 5. Funksional modullar

1. **Ro'yxatdan o'tish va do'kon yaratish:** telefon + SMS kod (provayder tanlanadi, masalan Eskiz yoki Play Mobile).
2. **Tovarlar:** CRUD, kategoriya, birlik, shtrix-kod, rasm, minimal qoldiq (`min_stock`), CSV/Excel import.
3. **Ombor:** kirim (yetkazuvchi bilan), chiqim, filiallar orasida ko'chirish, inventarizatsiya (sanash), tuzatish (sabab bilan).
4. **Kassa (POS):** shtrix-kod yoki qidiruv, savat, chegirma (ruxsat bilan), to'lov (naqd, karta, Click, Payme, aralash), chek chop etish, smena ochish/yopish, qaytarish.
5. **Qarz daftari:** mijoz kartasi, qarzga sotuv, qisman to'lov, muddat va eslatma.
6. **Hisobotlar:** kunlik/oylik savdo, foyda (kirim narxi bilan hisoblanadi), eng ko'p sotilgan, qoldiq, qarzlar, smena hisoboti. Excel va PDF eksport.
7. **Telegram bot (faqat o'qish):** kam qolgan tovarlar, kunlik hisobot, "X tovar qancha qoldi" so'rovi. Bot ma'lumotni o'zgartirmaydi.
8. **Obuna:** tariflar (Starter, Business, Chain), 14 kunlik sinov, Click/Payme webhook'lari orqali to'lovni tasdiqlash.
9. **Rollar va ruxsatlar:** har endpoint va har ekranda RBAC.
10. **AI prognoz (MVP'dan keyin):** o'tgan savdo bo'yicha tovar qachon tugashini va qancha buyurtma berish kerakligini hisoblaydi. Avval oddiy statistik model (masalan, hareketlanuvchi o'rtacha), keyin ML. Ma'lumot to'planganidan keyin boshlanadi.

---

## 6. Desktop ilova (Python)

- **Stack:** Python 3.12, PySide6, SQLAlchemy (lokal SQLite), httpx, pydantic.
- **Papka tuzilishi:**
  ```
  desktop/omborai_desktop/
    ui/            # ekranlar, widgetlar (PySide6)
    presenters/    # UI mantiqi
    services/      # biznes mantiq (sotuv, qoldiq)
    repositories/  # lokal SQLite
    sync/          # outbox worker (QThread)
    printing/      # ESC/POS chek
    models/
  ```
- **Shtrix-kod skaneri:** odatda klaviatura rejimida (HID) ishlaydi, alohida drayver kerak emas.
- **Printer:** ESC/POS (USB yoki LAN), `python-escpos`.
- **Qidiruv:** SQLite FTS5, 10 000 tovarda 100 ms dan kam.
- **Yig'ish:** PyInstaller yoki Nuitka, Inno Setup bilan Windows o'rnatuvchi.
- **Yangilanish:** versiya manifest URL'i orqali tekshiriladi, yangi versiya bo'lsa yuklab olinadi.
- **Asosiy OS:** Windows (kichik do'konlarda ko'p uchraydi). Linux va macOS keyinroq.

---

## 7. Mobil ilova (Flutter + Kotlin)

- **Stack:** Flutter 3.x, Dart 3, Riverpod, go_router, Drift, dio.
- **Kotlin qismi (Android platform channel):**
  - CameraX + ML Kit orqali shtrix-kod skaneri (Flutter plagin o'rniga, boshqarish uchun).
  - Bluetooth printer (agar do'konlarda kerak bo'lsa).
  - Foreground/WorkManager orqali fon sinxronizatsiyasi.
- **Ekranlar:** Kirish, Bosh sahifa (bugungi savdo, kam qoldiq), Tovarlar, Kirim/Qoldiq, Mobil kassa, Qarzlar, Hisobotlar, Sozlamalar.
- **Minimal Android:** 8.0 (API 26).
- **iOS:** keyinroq. Flutter tayyor, lekin iOS build uchun Mac va Apple Developer hisobi kerak.

---

## 8. Backend API

- REST, `/v1` versiyasi, OpenAPI `/docs` da.
- Asosiy resurslar: `/auth`, `/stores`, `/products`, `/stock/movements`, `/purchases`, `/sales`, `/shifts`, `/customers`, `/debts`, `/reports`, `/sync/push`, `/sync/pull`, `/subscriptions`, `/webhooks/click`, `/webhooks/payme`.
- Standartlar: cursor bo'yicha pagination, xatolik formati RFC 7807 (`application/problem+json`), `Idempotency-Key` headeri.
- Webhook'lar: imzo tekshiruvi, idempotent qayta ishlash.

---

## 9. Xavfsizlik

- Parollar: argon2id.
- Tenant izolyatsiyasi: har so'rovda `tenant_id` filtri, ustiga PostgreSQL RLS (ikkinchi qavat).
- RBAC: har endpointda ruxsat tekshiruvi.
- TLS majburiy (Caddy), rate limit (Redis), CORS qat'iy ro'yxat.
- Sirlar: repo'da yo'q. `.env` faqat lokal, production'da Docker secrets.
- Audit log: narx o'zgarishi, chegirma, qoldiq tuzatish, o'chirish, rol o'zgarishi.
- Zaxira: kunlik `pg_dump`, 30 kun saqlanadi. Oyiga bir marta tiklash sinovi.
- Bog'liqliklar: Dependabot, `pip-audit`, `osv-scanner`.
- Telefon raqam va manzil kabi shaxsiy ma'lumotlar: minimal yig'iladi, saqlashda shifrlanadi.

---

## 10. Sifat va testlash

- **Backend:** pytest, testcontainers (haqiqiy PostgreSQL), kritik modullarda (sotuv, qoldiq, sync) coverage 80%+.
- **Desktop:** pytest + pytest-qt.
- **Mobil:** `flutter test` (unit, widget), `integration_test`.
- **End-to-end:** login, sotuv, chek, qoldiq kamayishi, desktop'da ko'rinishi.
- **Sync sinovlari:** 1 soat offline ishlash, keyin ulanish. Dublikat yo'q, tartib to'g'ri, konflikt to'g'ri ko'rsatiladi.
- **Yuk:** k6 yoki Locust, 100 do'kon, 50 RPS.
- **Linter:** ruff, mypy, `dart analyze`, `dart format`.
- **CI:** har PR'da lint + test. `main` ga merge bo'lganda build va staging'ga deploy. Production'ga qo'lda tasdiqlash bilan.

---

## 11. Deploy

- Monorepo: `backend/`, `desktop/`, `mobile/`, `shared/` (OpenAPI, fixture'lar), `infra/`, `docs/`.
- Docker Compose: `api`, `worker`, `beat`, `postgres`, `redis`, `caddy`.
- Alembic migratsiyalari har release'da avtomatik ishlaydi (orqaga qaytarish skripti bilan).
- Desktop: GitHub Releases orqali. Code signing sertifikati (pullik) keyinroq.
- Android: AAB, Play Console, avval internal testing, keyin production.

---

## 12. Bosqichlar va taxminiy muddat

Taxmin: bitta kuchli dasturchi + AI yordami bilan **~17 hafta**. Jamoa bo'lsa tezroq bo'ladi.

| Faza | Muddat | Natija |
|---|---|---|
| 0. Discovery | 1 hafta | 5 ta do'kon bilan suhbat, talablar, ekran eskizlari |
| 1. Fondament | 2 hafta | Repo, CI, Docker, auth, tenant, OpenAPI skeleton |
| 2. Tovar va ombor | 2 hafta | Tovar, shtrix-kod, kirim/chiqim, `stock_movements`, testlar |
| 3. Desktop kassa | 3 hafta | POS, smena, chek chop etish, qaytarish |
| 4. Sync va offline | 2 hafta | Outbox, pull/push, konflikt, sinov |
| 5. Mobil | 3 hafta | Flutter ekranlari, mobil ko'rish va kassa, Kotlin skaner |
| 6. To'lov, obuna, hisobot, Telegram | 2 hafta | Click/Payme, tariflar, hisobotlar, bot |
| 7. Pilot va hardening | 2 hafta | 3–5 do'konda pilot, bug fix, yuk va xavfsizlik tekshiruvi |
| Keyin | davomiy | AI prognoz, iOS, ko'p filial, fiskal integratsiya |

---

## 13. MVP chegarasi

**Kiradi:** 1-7 bo'limdagi asosiy modullar (AI prognozdan tashqari), Android, Windows desktop, offline sinxronizatsiya.

**Kirmaydi:** AI prognoz, iOS, bank integratsiyasi, yetkazib berish, ko'p valyuta, to'liq fiskal integratsiya (talab qilinsa alohida fazada).

---

## 14. Xavflar

| Xavf | Ehtimol | Yechim |
|---|---|---|
| Fiskal/soliq talablari (chek, OFD) | Yuqori | Huquqiy talablarni aniqlash, MVP'dan oldin tekshirish. Men bu qoidalarni ishonch bilan bilmayman, mutaxassis bilan tekshirish kerak |
| Click/Payme shartnoma va API kirish | O'rtacha | Biznes jarayon uzoq bo'lishi mumkin. Boshlang'ich kodni sandbox'da yozish |
| Internet uzilishi | Yuqori | Offline-first arxitektura (4-bo'lim) |
| Skaner va printer modellari xilma-xil | Yuqori | Sinov ro'yxati, eng keng tarqalgan modellarni qo'llab-quvvatlash |
| Flutter/Kotlin bilan tajriba kamligi | O'rtacha | Erta prototip, platform channel'ni kichik qilib saqlash |
| Excel'dan ma'lumot ko'chirish | Yuqori | Import shabloni va xatoliklar hisoboti |
| Google Play ko'rib chiqish | Past | Maxfiylik siyosati va ruxsatlarni minimal qilish |

---

## 15. Ochiq savollar (javob kerak)

1. **Mobil stack:** taklif: Flutter UI + Kotlin native moduli. Yoki ikki alohida native ilova (Android: Kotlin, iOS: Swift)?
2. **Offline majburiymi?** Taklif: ha.
3. **Fiskal kassa / OFD / soliq integratsiyasi** MVP'da kerakmi?
4. **Hosting:** O'zbekiston hududidagi server yoki xorijiy VPS? Ma'lumot joylashuvi talabi bormi?
5. **Pilot soha:** oziq-ovqat, ulgurji, qurilish mollari yoki kiyim? Bu import va hisobot shablonlariga ta'sir qiladi.
6. **Tillar:** o'zbek (lotin) va rus. Kirill kerakmi?
7. **SMS provayder:** Eskiz, Play Mobile yoki boshqa?
8. **Jamoa:** siz bir o'zingiz ishlaysizmi yoki jamoa bormi? Muddat shunga bog'liq.
9. **Tarif narxlari:** hozircha bo'sh qoldiramizmi yoki taklif qilaymi?

---

## 16. Keyingi qadam

Tasdiqlangandan keyin:
1. Monorepo skeletini yaratish (`backend/`, `desktop/`, `mobile/`, `shared/`, `infra/`, `docs/`).
2. Faza 1 ni boshlash: Docker Compose, CI, auth va tenant.
3. Hammasi `claude/wonderful-dirac-gdu5x2` branch'ida commit va push qilinadi.
