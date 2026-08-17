# DataForge Pro

**Universal ma'lumot va log tahlili platformasi** — istalgan manbadan ma'lumot o'qiydi,
chuqur tahlil qiladi, tahrirlaydi, 25 xil grafik chizadi va Machine Learning bilan
naqsh, anomaliya hamda bashoratlarni topadi.

Python · PySide6 (zamonaviy dark UI) · pandas · scikit-learn · matplotlib

---

## Ishga tushirish

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

Uchala usul ham ishlaydi:

```bash
python run.py
python -m dataforge
python dataforge/main.py
```

Demo ma'lumotlarni yaratish:

```bash
python run.py --samples
```

---

## Imkoniyatlar

### 1. Ma'lumot yuklash — istalgan manba, istalgan format

| Manba | Tafsilot |
|---|---|
| **Fayl** | CSV, TSV, JSON, JSONL/NDJSON, Excel, Parquet, XML, YAML, HTML jadval, SQLite, `.gz`, `.zip` |
| **Log fayl** | Format **avtomatik aniqlanadi**: Apache/Nginx access, Nginx error, Syslog (RFC3164), Python logging, JSON Lines, logfmt (key=value), ISO+level, ajratgichli, erkin matn |
| **Papka** | Yuzlab faylni bitta jadvalga birlashtiradi (`_source` ustuni bilan) |
| **Internet** | HTTP/HTTPS — JSON API, CSV, HTML jadval, xom log; maxsus sarlavhalar (token) bilan |
| **Baza** | SQLite: jadval yoki ixtiyoriy SQL so'rov |
| **Matn** | Clipboard yoki qo'lda kiritilgan matn |

Yuklashda kodlash (`chardet`), ajratgich, ustun turlari (son / sana-vaqt / mantiqiy /
kategoriya) avtomatik aniqlanadi. Vaqt belgilari epoch (s/ms) ko'rinishida ham tushuniladi.

### 2. Tahrirlash — 30+ amal, to'liq undo/redo

**Filtr:** shart bo'yicha (`pandas.query`), matn/regex qidiruv, son oralig'i, vaqt oralig'i
**Tozalash:** dublikatlar, bo'sh qatorlar, bo'shliklarni to'ldirish (o'rtacha/mediana/moda/
interpolyatsiya/oldingi/keyingi), chetlanuvchilarni cheklash (IQR / kvantil / z-score),
doimiy ustunlarni olib tashlash
**Ustunlar:** tanlash, o'chirish, nom, tur o'zgartirish
**Matn:** almashtirish, registr, bo'lish, regex bilan ajratib olish
**Hisoblash:** ifoda bilan yangi ustun, sanadan qismlar (yil/oy/soat/hafta kuni/kun vaqti),
binlash, masshtablash (z-score / min-max / robust / log1p)
**Kodlash:** one-hot, label encoding
**Tuzilma:** guruhlab jamlash, pivot, melt, vaqt bo'yicha resample, transponatsiya

Jadvalda kataklar to'g'ridan-to'g'ri tahrirlanadi, ustun sarlavhasidagi kontekst menyu
tez amallarni beradi. Har bir o'zgarish tarixga yoziladi — istalgan holatga qaytish mumkin.

### 3. Profil va tahlil

- Har bir ustun bo'yicha: tur, bo'sh/unikal ulush, min/max/o'rtacha/mediana/kvantillar,
  assimetriya, ekstsess, entropiya, chetlanuvchilar, eng ko'p uchraydigan qiymatlar
- **Ma'lumot sifati bahosi (0–100)** va avtomatik ogohlantirishlar: ko'p bo'sh qiymat,
  doimiy ustun, ID-ga o'xshash ustun, kuchli assimetriya, ko'p chetlanuvchi, dublikatlar
- Korrelyatsiya (Pearson / Spearman / Kendall) + eng kuchli juftliklar ro'yxati
- Kategorik bog'liqlik — Cramér's V
- Interaktiv guruhlash / pivot va vaqt qatori tahlili

### 4. Grafiklar — 25 tur

Chiziqli · Maydon · Pog'onali · Ustunli · Yotiq ustunli · Yig'ma ustunli · Doiraviy ·
Halqa · Chastota · Nuqtali · Pufakchali · Hexbin · Gistogramma · KDE · ECDF · Quti ·
Skripka · Strip · Issiqlik xaritasi · Korrelyatsiya matritsasi · Juftliklar matritsasi ·
Bo'sh qiymatlar xaritasi · Vaqt qatori · Soat × hafta kuni · Siljuvchi o'rtacha

Har birida rang (hue), o'lcham, jamlash funksiyasi, log o'q, trend chizig'i sozlamalari.
PNG / SVG / PDF sifatida saqlanadi yoki hisobot galereyasiga qo'shiladi.

### 5. ML Studio

**AutoML** — vazifa (klassifikatsiya/regressiya) avtomatik aniqlanadi, 11 tagacha model
cross-validation bilan taqqoslanadi, reyting jadvali tuziladi. Sonli, kategorik va matn
(TF-IDF) xususiyatlar bitta quvurda qayta ishlanadi, sana ustunlari avtomatik
xususiyatlarga yoyiladi.

Modellar: Logistik/Chiziqli regressiya, Ridge, ElasticNet, Qaror daraxti, Random Forest,
Extra Trees, Gradient Boosting, HistGradientBoosting, KNN, SVM/SVR, Naive Bayes, MLP, SGD

Natijalar: metrikalar (accuracy, balanced accuracy, precision, recall, F1, ROC AUC /
R², MAE, RMSE, MAPE), chalkashlik matritsasi, ROC egri chiziqlari, qoldiqlar tahlili,
xususiyatlar muhimligi (model ichidan yoki permutation importance).
Model `.joblib` sifatida saqlanadi va yangi ma'lumotga qo'llanadi.

**Klasterlash** — KMeans (siluet bo'yicha avtomatik `k`), Agglomerative,
GaussianMixture, DBSCAN. PCA proyeksiyasi, klaster profillari, optimal `k` grafigi.

**Anomaliya deteksiyasi** — Isolation Forest, Local Outlier Factor, One-Class SVM,
Elliptic Envelope, Z-score, IQR, EWMA (vaqt qatori uchun). Natija ustun sifatida
ma'lumotga qaytariladi.

**O'lchov kamaytirish** — PCA (tushuntirilgan dispersiya bilan), t-SNE, TruncatedSVD.

**Bashorat** — Holt-Winters (mavsumiylik bilan), 95% ishonch oralig'i.

### 6. Log AI

- **Shablon qazish** — o'zgaruvchan qismlar (`<NUM>`, `<IP>`, `<UUID>`, `<PATH>`,
  `<STR>`, `<TS>`) niqoblanadi va bir xil naqshli xabarlar guruhlanadi
- **Kam uchraydigan shablonlar** — anomaliya nomzodlari
- **Portlash (burst) deteksiyasi** — vaqt oynasida z-score bo'yicha
- **Matn klasterlash** — TF-IDF + KMeans, har klaster uchun kalit so'zlar va namunalar
- **Entity ajratish** — IP, IPv6, MAC, UUID, email, URL

### 7. Hisobot

Profil, sifat ogohlantirishlari, korrelyatsiya, grafiklar (base64 ichiga joylangan),
ML natijalari va tahrirlar tarixini bitta **mustaqil HTML faylga** jamlaydi —
tashqi bog'liqliksiz, istalgan brauzerda ochiladi.

Ma'lumotni CSV / Excel / Parquet / JSON / JSONL / SQLite / HTML / Markdown sifatida
eksport qilish mumkin. Butun sessiya `.dfp` loyiha faylida saqlanadi.

---

## Tuzilma

```
dataforge/
├── run.py                      ishga tushirish
├── requirements.txt
├── dataforge/
│   ├── main.py                 kirish nuqtasi (--samples, --version)
│   ├── config.py               yo'llar, limitlar, rang palitrasi
│   ├── core/                   GUI'siz sof mantiq (to'liq testlangan)
│   │   ├── ingest.py           universal yuklash + eksport
│   │   ├── logparse.py         log format aniqlash, parser, shablon qazish
│   │   ├── profile.py          statistika, sifat tekshiruvi, korrelyatsiya
│   │   ├── transform.py        30+ amal registri + undo/redo tarixi
│   │   ├── ml.py               AutoML, klaster, anomaliya, PCA, bashorat
│   │   ├── charting.py         25 grafik turi (matplotlib)
│   │   ├── report.py           HTML hisobot
│   │   └── project.py          .dfp loyiha saqlash/yuklash
│   └── ui/                     PySide6 qatlami
│       ├── theme.py            dark tema (QSS)
│       ├── store.py            markaziy ma'lumot ombori (signal'lar bilan)
│       ├── widgets.py          Card, StatTile, DataFrameModel, ChartCanvas…
│       ├── tasks.py            fon oqimlari (GUI muzlamaydi)
│       ├── main_window.py      yon menyu + sahifalar
│       └── pages/              8 ta sahifa
├── samples/generate_samples.py demo ma'lumotlar generatori
└── tests/                      172 test
```

## Testlar

```bash
python -m pytest tests/ -q
```

`tests/test_core.py` — yuklash, log tahlil, profil, tahrirlash, ML, grafiklar,
hisobot, loyiha va to'liq integratsiya quvuri.
`tests/test_ui.py` — ombor, vidjetlar, sahifalar va navigatsiya (offscreen rejimda,
displey talab qilmaydi).

## Tezkor tugmalar

`Ctrl+O` yuklash · `Ctrl+S` loyihani saqlash · `Ctrl+Shift+O` loyihani ochish ·
`Ctrl+Z` bekor · `Ctrl+Y` qaytarish · `Ctrl+E` eksport · `Ctrl+C` nusxalash · `F1` yordam
