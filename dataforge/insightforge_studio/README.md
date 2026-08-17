# InsightForge Studio

Python va PySide6 asosidagi mustaqil, lokal-first analitik ish stansiyasi.

InsightForge ma'lumotlarni import qilish, sifatini baholash, vizual transform pipeline
qurish, grafiklar chizish, anomaliyalarni topish, ML modellarni solishtirish va auditli
HTML hisobot yaratishni bitta desktop ilovada birlashtiradi.

## Ishga tushirish

```powershell
cd insightforge_studio
python -m pip install -r requirements.txt
python run.py
```

Demo rejim:

```powershell
python run.py --demo
```

Testlar:

```powershell
python -m pytest tests -q
```

## Asosiy farqlar

- Bir nechta dataset uchun markaziy workspace va metadata katalogi
- Nusxa ko'chirmaydigan snapshot/delta uslubidagi transform tarixi
- Ketma-ket bajariladigan, saqlanadigan transform pipeline
- 36 ta transform operatsiyasi va 26 ta grafik turi
- Datasetlararo join va append
- Data quality qoidalari va 0-100 health score
- Segment, trend, korrelyatsiya va anomaliya tahlili
- Klassifikatsiya/regressiya uchun xavfsiz AutoML pipeline
- Lokal `.ifs` workspace formati va mustaqil HTML hisobot
- Barcha og'ir vazifalar uchun bekor qilinadigan background job infratuzilmasi

## Tuzilma

`insightforge/core` — GUI'dan mustaqil biznes mantiq.

`insightforge/ui` — PySide6 interfeys, sahifalar va vidjetlar.

`tests` — core va GUI smoke-testlari.
