# OmborAI — Desktop (kassa)

Python 3.12+ va PySide6. Serversiz: do'kon ma'lumoti qurilmalar orasida MQTT (`broker.hivemq.com`, TLS 8883) orqali
imzolangan operatsiyalar bilan sinxronlanadi. Protokol: `../docs/sync-mqtt.md` (v2).

## Ishga tushirish (Windows, PowerShell)

```powershell
cd desktop
py -3.13 -m venv .venv        # 3.12 yoki 3.13 (sqlcipher3 wheel'i shu versiyalar uchun)
.venv\Scripts\activate
pip install PySide6 keyring paho-mqtt cryptography pytest pytest-qt ruff mypy
# sqlcipher3 — SHIFRLANGAN baza. PyPI'da Windows wheel yo'q: manbadan yig'iladi (pastga qarang)
pip install -e .
python -m omborai_desktop
```

### sqlcipher3 ni Windows'da yig'ish

`sqlcipher3` SQLCipher (OpenSSL kripto bilan) manbasidan yig'iladi. Talab: MSVC (Visual Studio Build Tools 2022+),
Python headers, `conan` (OpenSSL ni o'zi oladi):

```powershell
pip install conan
pip wheel --no-build-isolation --no-deps -w wheels sqlcipher3==0.6.3   # sdist'dan
pip install wheels\sqlcipher3-0.6.3-*.whl
```

Tekshiruv: `python -c "import sqlcipher3; print(sqlcipher3.sqlite_version)"` — `3.51.x` chiqishi kerak.

## Ma'lumot joylashuvi

- Baza: `~/.omborai/local_v2.db` (SQLCipher, kalit OS keyring'da). `OMBORAI_LOCAL_DB` bilan o'zgartiriladi.
- Qurilma imzo kaliti (Ed25519) va do'kon kaliti — OS keyring'da (`omborai-desktop` xizmati).

## Juftlash (qo'shimcha qurilma)

1. Egasi qurilmasi: **Foydalanuvchilar va qurilmalar → Juftlash kodi** (faqat egasi hisobi va egasi qurilmasida).
2. Yangi qurilma: "Mavjud do'konga qo'shilish", kodni kiriting. Qurilma tasdiq so'raydi.
3. Egasi qurilmasida "Yangi qurilma" oynasi: **Kassir** yoki **Egasi** sifatida qo'shish, yoki **Rad etish**.
4. Tasdiqdan keyin do'kon ma'lumoti (snapshot) keladi, login ochiladi. Egasi qurilmasi o'chiq bo'lsa, kutish oynasi
   "egasi qurilmasini tekshiring" deb eslatadi.

## Klaviatura

| Tugma | Amal |
|---|---|
| F2 | Qidiruv maydoniga o'tish |
| Enter | Shtrix-kod yoki nomni qidirish (skaner shu yerga yozadi) |
| F12 | To'lash |
| Del | Tanlangan qatorni o'chirish |
| Esc | Qidiruvni tozalash |

## Rollar

- **Kassir** qurilmasi: savdo, o'z smenasi. Tovar, qaytarish, foydalanuvchi va qurilma boshqaruvi yo'q (tugmalari
  o'chiq, sababi tooltip'da).
- **Egasi** qurilmasi + egasi hisobi: hammasi. Egasi hisobi boshqa qurilmada bo'lsa, boshqaruv tugmalari o'chiq.

## Testlar va tekshiruvlar

```powershell
pytest -q                                   # 100+ test (GUI offscreen, SQLCipher bilan)
ruff check . ; mypy omborai_desktop --ignore-missing-imports
python ..\tools\mqtt_smoke.py               # HAQIQIY broker bilan to'liq sikl (mock yo'q)
```

`tools/mqtt_smoke.py`: egasi va kassa qurilmasi brokerda juftlanadi, snapshot oladi, savdo va qaytarish o'tkaziladi.

## Arxitektura

- `omborai_desktop/sync/` — `crypto.py` (konvert, canonical JSON, imzo), `identity.py` (Ed25519 kalit),
  `ops.py` (turlar, ruxsatlar), `mqtt_sync.py` (transport, xatolarga chidamli)
- `omborai_desktop/offline/store.py` — lokal baza va protokol qoidalari (`apply_op`: imzo → muallif faolligi →
  ruxsat → tekshiruv → qo'llash; kutish buferi; bootstrap)
- `omborai_desktop/ui/` — PySide6 oynalar. `theme.py` — tungi (dark) mavzu, ranglar bitta joyda.
- `omborai_desktop/money.py`, `cart.py` — pul yaxlitlash (ROUND_HALF_UP) va savat (Qt'siz)

## Muhim qoidalar

- Savdo narxi katalogdagi narx bilan mos bo'lishi shart; mos bo'lmasa savdo hech qanday qurilmada qo'llanmaydi.
- Qaytarish faqat egasi tomonidan; qaytarish o'z mahsulotlarini olib yuradi (sotuv boshqa qurilmada bo'lsa ham).
- Har bir qurilmaning o'z smenasi bor (bir qurilmada bitta ochiq smena).
- Ilova ishlashi uchun `QT_QPA_PLATFORM` talab qilinmaydi; testlar `offscreen` rejimida ishlaydi.
