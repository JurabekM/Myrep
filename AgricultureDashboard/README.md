# 🌾 AgroVision — Qishloq xo'jaligi analitik platformasi

Enterprise darajadagi, **100% Python** asosidagi analitik dashboard: GIS,
Business Intelligence, Machine Learning, sun'iy yo'ldosh monitoringi,
ob-havo, bozor narxlari, moliya va ichki AI yordamchi — yagona tizimda.

## Ishga tushirish (bitta buyruq)

```
python run.py
```

yoki monolit (bitta fayl) nashri:

```
python AgricultureDashboard.py
```

Birinchi ishga tushirishda platforma o'zi:
1. yetishmayotgan pip kutubxonalarini aniqlaydi va (ruxsat so'rab) o'rnatadi;
2. barcha papkalarni (`data/ logs/ backups/ exports/ uploads/ models/ ...`) yaratadi;
3. SQLite bazani yaratadi (SpatiaLite topilsa — yoqadi, bo'lmasa oddiy SQLite);
4. demo ma'lumotlarni yuklaydi: 13 viloyat, 26 tuman, 60 fermer, 75 xo'jalik,
   140 dala (GeoJSON poligonlar bilan), 23 ekin, 5 yillik hosildorlik,
   kunlik ob-havo, haftalik bozor narxlari, sug'orish, moliya, NDVI/EVI;
5. ML modellarini o'qitadi va brauzerda dashboardni ochadi.

**Demo hisoblar:** `admin/admin123` · `menejer/manager123` · `kuzatuvchi/viewer123`

## Buyruqlar

| Buyruq | Vazifa |
|---|---|
| `python run.py` | Platformani ishga tushirish (http://127.0.0.1:8080) |
| `python run.py --selfcheck` | 8 quyi tizimni salomatlik tekshiruvi |
| `python run.py --port 9000 --no-browser --yes` | Parametrlar bilan |
| `python build_monolith.py` | Variant-2: bitta `AgricultureDashboard.py` yig'ish |
| `python -m unittest discover tests` | Unit testlar |

## Modullar (Variant-1)

```
AgricultureDashboard/
  run.py               — kirish nuqtasi, installer, selfcheck
  build_monolith.py    — Variant-2 generatori
  config/              — sozlamalar, yo'llar, konstantalar
  core/                — logging, xavfsizlik, kesh, i18n, plaginlar, fon ishlari
  database/            — SQLAlchemy modellari, engine, seed, backup/restore
  analytics/           — KPI, time series, prognoz, avtomatik xulosalar
  gis/                 — folium xarita (3 qatlam, klaster, heatmap), geometriya
  ml/                  — hosil/kasallik/suv/tavsiya modellari (sklearn + XGBoost*)
  weather/             — Open-Meteo, NASA POWER, offlayn kesh
  market/              — narxlar, trend, prognoz, qo'lda kiritish
  irrigation/          — suv sarfi va samaradorlik tahlili
  finance/             — P&L, ROI, kredit/subsidiya
  satellite/           — provayder zanjiri: GEE* → lokal demo; dron GeoTIFF
  ai/                  — offlayn NLQ dvigatel (o'zbekcha savollar)
  reports/             — PDF, Excel, CSV, Word*, HTML, JSON, GeoJSON, PNG*
  utils/               — universal import (CSV/Excel/GeoJSON/SHP/KML/TIFF/ZIP), qidiruv
  api/                 — REST API (Bearer token): /api/health, /api/kpi, ...
  app/                 — NiceGUI yig'uvi, tema, layout, chartlar
  dashboard/pages/     — 15 sahifa (login, xarita, analitika, ML, AI, admin...)
  plugins/             — plagin tizimi (namuna: tuproq tahlili)
  tests/               — unit testlar
```

`*` — ixtiyoriy paket o'rnatilganda avtomatik faollashadi (`requirements.txt` ga qarang);
o'rnatilmagan bo'lsa to'liq ishlaydigan lokal muqobil ishlatiladi.

## REST API

```
POST /api/token            {"username":"admin","password":"admin123"}
GET  /api/kpi              Authorization: Bearer <token>
GET  /api/yields?year=2025
GET  /api/prices/1?days=365
GET  /api/weather/3?days=90
POST /api/ai/ask           {"question":"Jizzaxda bug'doy hosili nima uchun pasaydi?"}
GET  /api/health           (ochiq)
```

## Xavfsizlik

PBKDF2 (120k iteratsiya) parol xeshlari · HMAC-imzoli muddatli tokenlar ·
RBAC (admin/manager/viewer) · login rate-limit · audit jurnali ·
avtomatik zaxira nusxalar (ixtiyoriy Fernet shifrlash) · sessiyalar
server tomonida saqlanadi; API cookie emas, Bearer token ishlatadi.

## Offlayn rejim

Internet bo'lmasa: barcha analitika, ML, AI, hisobotlar va jadvallar so'nggi
saqlangan ma'lumotlar bilan to'liq ishlaydi; ob-havo keshdagi so'nggi prognozni
ko'rsatadi. Faqat xarita plitkalari (tile) va jonli API yangilanishlari
internetga bog'liq. Rejim: Sozlamalar → Offlayn rejim (avto/majburiy).

## Plagin yozish

`plugins/mening_plaginim.py`:

```python
PLUGIN = {"name": "IoT Sensorlar", "icon": "sensors", "route": "/plugin/iot"}

def register():
    from nicegui import ui
    from app import layout

    @ui.page(PLUGIN["route"])
    def page():
        user = layout.require_login()
        if user is None:
            return
        with layout.shell(user, "IoT Sensorlar"):
            ui.label("Salom, plagin!")
```

Fayl saqlangach, platformani qayta ishga tushiring — bo'lim menyuda paydo bo'ladi.
