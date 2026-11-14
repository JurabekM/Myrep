# OmborAI — chuqur tahlil

Sana: 2026-10-11
Manba: `C:\Users\comp_2.1\Downloads\claude_cowork\omborai\` (sessiya worktree'i bo'sh edi: faqat `.gitkeep`).
Loyiha fayllariga o'zgartirish kiritilmadi. Tekshiruv skriptlari sessiya scratchpad'ida.

---

## 1. Qamrov va usul

- **O'qildi:** desktop (`omborai_desktop/`, ~2 885 qator Python), backend (`app/`, ~2 470 qator), mobil (`lib/`, ~3 355 qator Dart + 193 qator Kotlin), infra (compose, Caddy), hujjatlar (`README`, `docs/*`, `loyiha-xotira.md`).
- **Haqiqatan ishga tushirildi:**
  - Desktop pytest: **44 o'tdi, 3 o'tkazib yuborildi** (mosquitto yo'q), **6 yurgizilmadi** (`test_encryption.py`, `sqlcipher3` yo'q). Muhit: Python 3.13, PySide6, paho-mqtt 2.1.0, cryptography, keyring, pytest-qt.
  - `ruff check` desktop va backend: o'tdi.
  - Sinxron yadro 7 ta stsenariy bilan qayta ishlab chiqarildi (MQTT'siz, Qt'siz, offscreen).
  - Kross-platforma kripto test vektori (docs 8.4): mavzu, ochiq matn va AAD tekshiruvi mos.
- **Yurgizilmadi:** backend pytest (PostgreSQL yo'q), mobil `flutter test`, broker testlari, Docker/Caddy.
- **Git holati:** `omborai/` asosiy `claude_cowork` reposida **untracked** (`?? omborai/`, branch `master`, HEAD `20aebd3`). `loyiha-xotira.md` dagi `claude/wonderful-dirac-gdu5x2`, PR #6, `/home/user/Myrep` va `.github/workflows` bu mashinada yo'q.

---

## 2. Xulosa

Loyiha: kichik do'konlar uchun ombor + kassa. Desktop (Python/PySide6) va mobil (Flutter + Kotlin skaner) ilovalari **serversiz** ishlaydi va qurilmalar o'rtasida ma'lumotni ommaviy MQTT broker (`broker.hivemq.com`) orqali shifrlangan holda sinxronlaydi. Backend (FastAPI + PostgreSQL) kodi bor, lekin hech bir klient uni ishlatmaydi.

**Kod sifati:** toza (ruff), kriptografiya to'g'ri amalga oshirilgan, desktop testlari o'tadi. Lekin **ishlab chiqarishga tayyor emas.** Eng muhim topilmalar:

1. **Desktopda do'konga qo'shilish mumkin emas** (login va snapshot o'rtasida deadlock). Simulyatsiyada tasdiqlandi.
2. **Desktop Windows'da o'rnatilmaydi:** `sqlcipher3-binary` uchun PyPI'da Windows wheel yo'q (Python 3.13 va 3.14 uchun tekshirildi). Foydalanuvchi mashinasi Windows.
3. **Sinxron yadro qurilmalarni ajratadi:** snapshot poygasi, qaytarish divergensiyasi, tartibsiz yetkazilgan qaytarish, bir vaqtda ochilgan ikki smena. Hammasi takrorlandi.
4. **Avtorizatsiya yo'q:** do'kon kaliti bo'lgan har qanday qurilma egani nofaol qila oladi yoki o'zini `owner` qilib yarata oladi. Rol tekshiruvi faqat UI'da.
5. **Mobil ma'lumot yo'qolishi:** operatsiya PUBACK kutilmasdan outbox'dan o'chiriladi, va mobil ulanish `clean session` bilan ishlaydi (kod bo'yicha, broker bilan tasdiqlanmagan).

---

## 3. Muammolar ro'yxati

Og'irlik: **Kritik** — ishlab chiqarishdan oldin tuzatilishi shart; **Yuqori** — MVP'dan oldin; **O'rta**, **Past** — keyingi bosqich.
"Tasdiqlandi" — ishga tushirib yoki statik qidiruvda isbotlangan. "Kod" — faqat o'qib aniqlangan.

| ID | Og'irlik | Muammo | Joy | Dalil |
|---|---|---|---|---|
| K1 | Kritik | Desktop: birinchi marta juftlash — login doim muvaffaqiyatsiz. `run_login` MQTT ishga tushishidan oldin foydalanuvchi kutadi, MQTT esa login'dan keyin yaratiladi. Snapshot so'ralmaydi, qurilma do'konga qo'shila olmaydi. | `desktop/omborai_desktop/ui/login.py:197-226`, `__main__.py:23-38` | Tasdiqlandi: `repro_join.py` → `run_login=None`, `applied_ops=0`, foydalanuvchilar `[]` |
| K2 | Kritik | Desktop Windows'da o'rnatilmaydi: `sqlcipher3-binary` uchun Windows wheel yo'q. `pip install -e ".[dev]"` shu yerda yiqiladi. | `desktop/pyproject.toml:12` | Tasdiqlandi: `pip index versions` py3.13/3.14 win → "No matching distribution". Linux cp312 wheel bor. `sqlcipher3` (sdist, 0.6.3) SQLCipher C kutubxonasini talab qiladi (sinalmagan) |
| K3 | Kritik | Avtorizatsiya yo'q. Protokolda operatsiya muallifining roli tekshirilmaydi; har qurilmada kalit bor. Kassir `user` op yuborib egani nofaol qiladi yoki `role: owner` bilan yangi foydalanuvchi yaratadi. Shuningdek, `set_active` egani himoyasi ham faqat UI'da. | `desktop/omborai_desktop/offline/store.py:447-481` (`_apply_user`, `_upsert_user`), `users.py:52-53` | Tasdiqlandi: `repro_omborai.py` §5 |
| K4 | Kritik | Mobil ma'lumot yo'qolishi. `flushOutbox` har bir op'ni `send()` dan keyin darhol o'chiradi, `send()` esa PUBACK kutmaydi (`publishMessage` messageId qaytaradi). Uzilish oynasida op yo'qoladi. Bundan tashqari mobil `connectionMessage` ni sozlamaydi, mqtt_client default `startClean()` ishlatadi (clean session) — desktop esa `clean_session=False`. | `mobile/lib/src/app_session.dart:304-318`, `mobile/lib/src/sync/mqtt_sync.dart:44-48, 81-91`; mqtt_client 10.11.11 `mqtt_client.dart` (default `getConnectMessage` → `startClean()`) | Kod. Broker xulqi bilan tasdiqlanmagan |
| K5 | Kritik (ma'lumot) | Snapshot poygasi. Snapshot faqat `applied_ops` bo'sh qurilmada qabul qilinadi. Bitta jonli op (`store`, `user`, `sale`) kelsa, snapshot rad etiladi va tovar/foydalanuvchilar hech qachon kelmaydi. Mobilda ham xuddi shunday. | `store.py:355-356`; mobil `local_db.dart:509` | Tasdiqlandi: §1 — snapshot `False`, `get_product=None`, `list_users=[]` |
| K6 | Kritik (ma'lumot) | Qaytarish divergensiyasi. `snapshot_payload` sotuv tarixini kiritmaydi. Snapshot'dan keyin olingan qurilmaga qaytarish kelsa, `_apply_refund` sotuvni topmaydi, jim qaytadi, lekin `op_id` yoziladi. Natija: egasi qoldig'i 10, yangi qurilma 7. | `store.py:398-411`, `snapshot_payload` (295-341) | Tasdiqlandi: §2 — A=10, D2=7, `apply_op(refund)` → `True` |
| K7 | Yuqori | Tartibsiz yetkazish: qaytarish sotuvdan oldin kelsa, u yo'qoladi (op_id yozilgani uchun qayta kelmaydi), sotuv keyin `completed` holatda qoladi. Mobilda ham shu mantiq. | `store.py:398-402`; mobil `local_db.dart:615` | Tasdiqlandi: §3 — E qoldiq 7, chek `completed` |
| K8 | Yuqori | Bir vaqtda smena ochish. Ikki qurilma o'z smenasini ochsa va bir-birining op'ini olsa, `_apply_shift_open` ikkinchisini e'tiborsiz qoldiradi. Har biri boshqa smena ID bilan qoladi. Bitta qurilma smenani yopganda ikkinchisi ochiq qoladi. | `store.py:413-420`, `close` — 422-433 | Tasdiqlandi: §4 |
| Y1 | Yuqori | Narx ishonchi yo'q. Sotuv summasi (`unit_price`, `total`) qo'llashda tekshirilmaydi. Do'kon kaliti bor qurilma 1 so'mlik chek yuborishi mumkin. Qoldiq ham qo'llashda tekshirilmaydi (faqat UI). | `store.py:373-396`; `cart.py:92` (izoh) | Tasdiqlandi: §6 — `total=1` qayd etildi |
| Y2 | Yuqori | Buzilgan xabar desktop MQTT thread'ini to'xtatishi mumkin. `open_envelope` JSON ildizi ob'ekt bo'lmasa `AttributeError` beradi; `_on_message` faqat `DecryptionError` ni ushlaydi; paho `on_message` istisnosini qayta ko'taradi (`suppress_exceptions=False`); `_thread_main` faqat `try/finally` — thread o'ladi. | `sync/crypto.py:50-61`, `sync/mqtt_sync.py:100-112`; paho 2.1.0 `client.py:4501-4506`, `4521-4525` | Tasdiqlandi (callback darajasida): `repro_mqtt_thread.py`. Thread o'lishi — kod bo'yicha. UI "MQTT ulangan" ko'rsatishi mumkin (taxmin, `_on_disconnect` chaqirilmaydi) |
| Y3 | Yuqori | Qaytarish hamma rol uchun ochiq (desktop va mobil). Kassir istalgan `completed` chekni qaytara oladi. | `main_window.py:516-532`; mobil `home_screen.dart:199-209` (rol tekshiruvi yo'q) | Kod |
| Y4 | Yuqori | Kalit ekrani barcha rollarga ochiq. Mobilda "Juftlash" tugmasi `isOwner` tekshiruvisiz. Kassir `store_id:key` ni ko'rib, yangi qurilmani ulay oladi. | `mobile/lib/src/screens/home_screen.dart:103-106` | Kod |
| Y5 | Yuqori | Mobil: login/do'kon yaratish/juftlashdan keyin bosh ekranga o'tilmaydi. `_Bootstrap` FutureBuilder faqat bir marta tekshiradi; `login_screen.dart` da `Navigator` yo'q. | `mobile/lib/main.dart`, `login_screen.dart` | Kod (hujjat bilan mos) |
| Y6 | Yuqori (backend, hozir ishlatilmaydi) | (a) `FORCE ROW LEVEL SECURITY` yo'q — jadval egasi RLS'ni chetlab o'tadi. (b) `require_roles` do'kon bo'yicha emas, barcha membership rollari bo'yicha. (c) `GET /v1/sales`, `GET /v1/stock/movements`, `GET /v1/stock/balances` a'zolikni tekshirmaydi. (d) `/auth/login` rate-limit yo'q. (e) `refresh` `users.deleted_at` ni tekshirmaydi va `FOR UPDATE` yo'q (ikki parallel refresh). (f) `login` membership `LIMIT 1` bilan, `ORDER BY` yo'q. | `backend/migrations/versions/0001_init.py:115-120` (+0002–0004), `backend/app/deps.py:41-52`, `api/stock.py:39-65`, `api/sales.py:91-100`, `api/auth.py:74-127` | Kod + grep (FORCE, rate limit yo'q, with_for_update yo'q auth.py da) |
| Y7 | O'rta | Release APK debug kalit bilan imzolanadi. TODO kommentariy tasdiqlaydi. Play'ga chiqarib bo'lmaydi. | `mobile/android/app/build.gradle.kts:37` | Kod |
| O1 | O'rta | Desktop smena yorlig'i boshqa qurilmadan kelgan o'zgarishda yangilanmaydi (faqat o'z amalidan keyin). | `main_window.py:574-582` | Kod |
| O2 | O'rta | LWW vaqt formati aralash: desktop `isoformat()` → `+00:00` (mikrosekund nolda kasr yo'q), Dart → `Z`. Solishtirish xom satr bo'yicha. Teng `ts` da `device` tie-break yo'q. Vaqt manbai — qurilma soati. | `sync/ops.py:35`, `store.py:452, 463, 542`; mobil `local_db.dart` | Kod |
| O3 | O'rta | PBKDF2 iteratsiyasi 100 000. OWASP tavsiyasi (PBKDF2-HMAC-SHA256) — 600 000. Do'kon kaliti sizsa parol xeshidan oflayn brute-force xavfi. | `desktop/omborai_desktop/auth.py:13`; `mobile/lib/src/auth.dart` | Tashqi standart bilan solishtirish |
| O4 | Past | Redis hech qayerda ishlatilmaydi, lekin compose `api` uchun uni majburiy qiladi va parolni env orqali uzatadi. | `backend/app/config.py:18`; `infra/docker-compose.yml:21-31, 54` | grep |
| O5 | Past | `*.apk` `omborai/.gitignore:35` da — relizdagi APK git'ga kirmaydi. | `omborai/.gitignore:35` | `git check-ignore` tasdiqladi |
| O6 | Past | Har bir qurilma snapshot so'rovi kelganda javob beradi (N ta to'liq snapshot). Trafik va tarmoq yuki. | `main_window.py:621-626`; mobil `_sendSnapshot` | Kod |

---

## 4. Xavfsizlik modeli

**Ijobiy:**
- AES-256-GCM, AAD = mavzu nomi; mavzu HKDF-SHA256 orqali kalitdan olinadi. Kross-platforma test vektori mos.
- Deterministik `op_id` (`refund:<sale_id>`, `sale` = sotuv UUID) qayta yuborishda dublikatni to'xtatadi.
- SQLCipher kaliti 64 hex belgi bilan qat'iy validatsiya qilinadi (`store.py` `HEX_KEY`), PRAGMA injection yo'q.
- Kalitlar OS keyring/Android Keystore da; fayl yoki repo'da emas.
- Backend: JWT `typ`/`require` claims, refresh token SHA-256 xeshi va family revocation, argon2 + timing uchun dummy hash, prod uchun JWT secret validatsiyasi, `stock`/`sales` da `FOR UPDATE`.

**Zaif:**
- **Bitta kalit = bitta daraja.** Do'kon kaliti barcha qurilmalarda bir xil; kassir ham egasi kabi operatsiya yuboradi. Rol modeli faqat UI'da (K3).
- **Juftlash kodi = kalit.** `store_id:key` ko'rinishi Y4 da barcha rollarga ochiq.
- **Ommaviy broker** (`broker.hivemq.com`), autentifikatsiyasiz; metama'lumot (mavzu, vaqt, hajm) ko'rinadi. `MqttSync` da login/parol sozlamasi yo'q.
- **Parol xeshlari kalit bilan birga tarqaladi** (snapshot va `user` op). Hujjatda qabul qilingan xavf sifatida belgilangan, lekin PBKDF2 iteratsiyasi past (O3).

---

## 5. Test va sifat holati

| Qism | Buyruq | Natija (bu mashinada) | Eslatma |
|---|---|---|---|
| Desktop | `pytest` (Py 3.13 venv, sqlcipher testidan tashqari) | 44 passed, 3 skipped, 6 yurgizilmadi | Skip = mosquitto yo'q. 6 = `sqlcipher3` yo'q (K2). Hujjatdagi "53 passed" boshqa muhitda |
| Desktop | `ruff check .` | All checks passed | `pyproject` konfiguratsiyasi bilan |
| Backend | `ruff check .` | All checks passed | |
| Backend | `pytest` | **Yurgizilmadi** | PostgreSQL yo'q. Statik: 47 test funksiyasi |
| Mobil | `flutter test` / `analyze` | **Yurgizilmadi** | Statik: 30 `test()`, 2 `testWidgets()`. Hujjatdagi "analyze o'tgan" bu sessiyada qayta tekshirilmadi |
| Protokol | Kross-platforma vektor (8.4) | Mos | `desktop` `topic_for` + `open_envelope` |
| Sinxron stsenariylar | `repro_omborai.py`, `repro_join.py`, `repro_mqtt_thread.py` | K1, K3, K5–K8, Y1, Y2 tasdiqlandi | Bular **regressiya testi emas** — tuzatishdan keyin qayta yozish kerak |

**Test qamrovi bo'shliqlari** (testlar bor, lekin bu stsenariylar yo'q): join oqimi (`run_login` / `join_store`), snapshot poygasi, qaytarish divergensiyasi, smena to'qnashuvi, buzilgan xabar bilan MQTT thread, mobil login navigatsiyasi. Hujjat (`loyiha-xotira.md` 14.1) bularni "Testi yo'q" deb tan oladi — to'g'ri.

---

## 6. Hujjat va kod nomuvofiqligi

`docs/loyiha-xotira.md` ning ko'p qismi to'g'ri (desktop/mobil lokal sxema, MQTT vektor, 10.2-1/2/4, 6.2 navigatsiya). Lekin:

1. **Git ma'lumoti boshqa muhitga oid.** `/home/user/Myrep`, `claude/wonderful-dirac-gdu5x2`, PR #6, `.github/workflows` — bu mashinada yo'q. `omborai/` untracked. CI haqidagi da'volar tekshirib bo'lmaydigan.
2. **"Windows'da sqlcipher3-binary wheel mavjudligi UNVERIFIED"** — endi tasdiqlandi: Windows wheel **yo'q** (K2). Shu sabab 12.5/5.3 dagi "pip install -e .[dev]" Windows uchun ishlamaydi.
3. **12.5-qadam 3** ("snapshot kelguncha kuting") desktop uchun **amalga oshmaydi** — K1 sababli.
4. **"53 passed" (13-bo'lim)** — bu mashinada 44 + 3 skip + 6 yurgizilmadi.
5. **`docs/sync-mqtt.md` 14.2:** "snapshot poygasi kichik oynada qoldiq farqi" — aslida tovar va foydalanuvchilar umuman yo'qoladi (K5). Hujjatdagi xato, qayta yozish kerak.
6. **Mobil `flushOutbox` "PUBACK kutmaydi (UNVERIFIED)"** — kod bo'yicha tasdiqlandi (K4).
7. **`PairingScreen` xavfsizligi** hujjatda yo'q: rol cheklovi yo'qligi (Y4) yozilmagan.
8. **`reja.md` va `README.md` eskirgan** (Riverpod, Drift, Celery, REST sync, `/customers`, `/debts`). Hujjat o'zi shu nomuvofiqlikni 14.2 da qayd etadi.

---

## 7. Tavsiya etilgan tartib

**P0 — ishlab chiqarishdan oldin**
1. **K1:** desktop join oqimini tuzatish: MQTT ni `run_login` dan oldin ishga tushirish yoki "snapshot kutilmoqda" holati. Regressiya testi: fake MQTT bilan join → snapshot → login.
2. **K2:** Windows'da shifrlash yechimi (qarorga muhtoj, quyida).
3. **K4:** mobil outbox — PUBACK tasdig'i bo'lmaguncha op o'chirilmasin; persistent session. mqtt_client ack API'sini tekshirish kerak.
4. **K3:** tahdid modeli bo'yicha qaror (quyida). Minimal chora: `user` va `owner`-ga tegishli op'larni faqat egasi qurilmasi imzolasi bilan qabul qilish.
5. **K5–K8:** dizayn tuzatishlari:
   - snapshot qabul qilishni "applied_ops == 0" o'rniga "katalog bo'sh" bo'yicha qilish (yoki snapshot'ga sotuv/items qo'shish);
   - `refund` op'ga sotuv items'ini kiritish (qaytarish sotuvdan mustaqil bo'lsin);
   - `shift_open` to'qnashuvi uchun deterministik tie-break (ts, device) yoki qurilma bo'yicha alohida smena;
   - tartibsiz qaytarish: kutilmagan qaytarishni saqlab, sotuv kelganda qo'llash.
6. **Y4, Y3:** Juftlash kalit ekrani faqat egasi uchun; qaytarish rol bo'yicha cheklansin.
7. **Y5:** mobil login'dan keyin navigatsiya.

**P1 — MVP'dan oldin**
8. **Y1:** qo'llashda sotuv summasini tekshirish (`subtotal`, `total` = items yig'indisi) — hech bo'lmasa qayd etish.
9. **Y2:** `open_envelope` ni `(ValueError, KeyError, TypeError, AttributeError, InvalidTag)` bilan kengaytirish va `_on_message` da `except Exception` + log. Paho thread o'lmasligi kerak.
10. **O1, O2:** UI'da smena holatini sinxron qilish; `ts` formatini bir xil (UTC, `Z`) qilish va teng ts'da tie-break.
11. **Y7:** release signing konfiguratsiyasi.
12. Backend ishga tushirilmasa: uni alohida "keyingi bosqich" sifatida belgilash yoki olib tashlash (ikki yo'nalish zid — hujjat 7.4).
13. Backend ishga tushirilsa: Y6 ning hammasi (FORCE RLS, store scope, rate limit, refresh `deleted_at` + `FOR UPDATE`, `ORDER BY`).

**P2**
14. O3: PBKDF2 iteratsiyasini oshirish (migratsiya: eski xeshlarni yangilash mexanizmi kerak).
15. O4: Redis'ni compose'dan olib tashlash yoki ishlatish.
16. O5: releases APK'ni git'ga qanday kiritish (`.gitignore` istisnosi yoki Releases).
17. Hujjatlarni (`README`, `reja`, `docs/*`, `loyiha-xotira`) kod bilan sinxronlash.

---

## 8. Sizdan kerakli qarorlar

1. **Tahdid modeli:** kassirlar ishonchli deb hisoblanadimi? Agar yo'q bo'lsa, har bir qurilmaga alohida kalit/imzo kerak — bu sinxron protokolning katta o'zgarishi (K3). Hozirgi `ishonchli kalit` modeli bo'yicha qolish ham mumkin, lekin unda rol tushunchasi faqat ko'rinish sifatida qoladi.
2. **Windows'da shifrlash:** `sqlcipher3` ni manbadan (SQLCipher bilan) yig'ish, yoki boshqa yechim (masalan, `pysqlcipher3` yoki shifrlashni OS darajasiga o'tkazish)? Har biri boshqa mehnat talab qiladi.
3. **Git va hujjatlar:** `omborai/` ni alohida branch'ga commit qilish kerakmi (hozir untracked)? Xotira hujjatini shu mashina holatiga moslashtirish kerakmi? Commit/push faqat siz aytsangiz.

---

## 9. Release APK

- **Yo'l:** `C:\Users\comp_2.1\Downloads\claude_cowork\omborai\releases\OmborAI-release-arm64-v8a-v0.1.0.apk`
- **Hajm:** 30 025 916 bayt. **Fayl sanasi:** 2026-10-10 19:56.
- **SHA-256:** `28c9ecc414792c762065bbb48e50d37e314aec932f9e2366ed906b7673c99756` — `.sha256` fayli bilan mos.
- **Arxitektura:** faqat `lib/arm64-v8a` (7 ta native fayl). Telefonga mos.
- **Imzo:** debug kalit (Y7).
- **Qaysi koddan:** aniq commit noma'lum (`omborai/` untracked). Mobil manba fayllarining hech biri APK'dan yangiroq emas (mtime bo'yicha) — ehtimol shu koddan yasalgan, lekin buni git bilan tasdiqlab bo'lmaydi.
- **Telefonga:** arm64 — mos. Desktop uchun Windows o'rnatish hozircha to'siqli (K2), mobil APK esa K1 ga tegishli emas.

---

## Ilova: tekshiruv skriptlari

Sessiya scratchpad'ida (loyiha fayllari o'zgarmagan):
- `repro_omborai.py` — §1–§7: snapshot poygasi, qaytarish divergensiyasi, tartibsiz qaytarish, smena to'qnashuvi, kassir soxta `user`, narx ishonchi, `open_envelope` xatosi.
- `repro_join.py` — desktop juftlash deadlock'i (Qt offscreen, dialoglar soxtalashtirilgan).
- `repro_mqtt_thread.py` — paho callback istisnosi (MqttSync darajasida).
- `vector_check.py` — kross-platforma kripto vektori.

Bular tuzatishdan keyin regressiya testlariga aylantirilishi kerak.
