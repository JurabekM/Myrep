# GCOM Signal Monitor (desktop dashboard)

`gcom_signal_logger` yozib borayotgan CSV log faylini real vaqtda o'qib,
chuqurroq tahlil bilan boyitilgan PyQt6 + pyqtgraph + pandas asosidagi
dark-tema desktop oynada ko'rsatadi (brauzersiz).

## O'rnatish

```
cd gcom_signal_dashboard
pip install -r requirements.txt
```

## Ishga tushirish

Avval `gcom_signal_logger` ishlab, log faylni to'ldirib turishi kerak:
```
cd ../gcom_signal_logger
python logger.py
```

Boshqa terminalda dashboardni ishga tushiring:
```
cd gcom_signal_dashboard
python main.py
```

`config.ini` da log fayl yo'li, so'rov intervali, jonli grafiklarda
saqlanadigan nuqtalar soni (`live_window_points`) va statistika uchun
xotirada tutiladigan maksimal qatorlar soni (`max_stored_rows`) sozlanadi.

## Yorliqlar (tabs)

1. **Jonli monitoring** — joriy holat kartalari (holat, band, RSSI/RSRP/RSRQ/
   SINR sifatga qarab rangda, SCC soni, tashqi IP, ulanish vaqti, trafik),
   **joriy PCC va SCC1-4 kartalari** (har birining aniq diapazoni va kanal
   kengligi, masalan "B1 / 10MHz") + RSRP/RSRQ/SINR uchun real vaqtdagi
   trend grafiklari.
2. **Statistika** — tanlangan vaqt oynasi (10 daqiqa / 1 soat / 24 soat /
   barchasi) bo'yicha RSSI/RSRP/RSRQ/SINR uchun min/max/o'rtacha/median/
   standart chetlanish/p5-p95 jadvali, taqsimot gistogrammalari va
   ko'rsatkichlar orasidagi korrelyatsiya matritsasi (masalan RSRQ va SINR
   qanchalik bog'liqligini ko'rsatadi).
3. **Band tahlili** — har bir diapazonda (B3, B7 va h.k.) o'tkazilgan
   namunalar soni, vaqt ulushi foizda va o'sha banddagi o'rtacha signal
   sifati; band bo'yicha o'rtacha RSRP taqqoslash grafigi — qaysi band
   odatda yaxshiroq signal berishini ko'rsatadi.
4. **Carrier Aggregation** — faol carrier'lar soni vaqt bo'yicha (1=faqat
   PCC, 2/3=CA yoqilgan); har bir CA konfiguratsiyasi (masalan "B1+B3+B20")
   qancha marta va qancha vaqt ulushida ishlatilgani hamda o'sha
   konfiguratsiyadagi o'rtacha RSRP/SINR; har bir jismoniy diapazon PCC
   yoki SCC sifatida jami necha marta ishtirok etgani; bir vaqtdagi
   carrier soni (1/2/3/4) taqsimoti.
5. **Hodisalar** — avtomatik aniqlanadigan xronologik jurnal: ulanish
   uzilishi/qayta ulanish, handover (uyali minora almashinuvi - CID/PCID
   o'zgarishi), band almashinuvi, carrier aggregation (SCC soni) o'zgarishi,
   RSRP/SINR sifat toifasi pasayishi yoki yaxshilanishi. Yuqorida jami
   uzilishlar soni, o'rtacha sessiya davomiyligi, onlayn ulush foizi va
   handoverlar soni ko'rsatiladi.
6. **Trafik** — kumulyativ TX/RX trafik grafigi va oraliqdagi qiymatlar
   farqidan hisoblangan baholangan tezlik (MB/daqiqa); router qayta
   ishga tushib trafik hisoblagichi 0 ga qaytgan holatlar (manfiy farq)
   avtomatik e'tiborga olinmaydi.

## Fayllar

- `main.py` — PyQt6/pyqtgraph interfeysi, real vaqtda log o'qish, tab'larni
  yangilash.
- `analytics.py` — pandas asosidagi tahlil qatlami: CSV qatorini tiplangan
  yozuvga aylantirish, statistika, band taqqoslash, korrelyatsiya va
  hodisalarni aniqlash (`EventDetector`).

## Eslatma

- Dashboard `gcom_signal_logger` yozgan CSV ustun sxemasiga qattiq bog'liq
  (`timestamp,state,...,pcc_1,pcc_2,scc_1..scc_4,scc_count`). Logger
  tomonidagi ustunlar o'zgarsa, `analytics.row_to_record()` ni ham yangilang.
- Jonli grafiklar xotirada faqat oxirgi `live_window_points` (default 500)
  nuqtani ko'rsatadi, lekin Statistika/Band/Hodisalar tahlili uchun
  `max_stored_rows` (default 200000) gacha bo'lgan butun tarix xotirada
  saqlanadi - to'liq tarix baribir CSV faylda ham qoladi.
