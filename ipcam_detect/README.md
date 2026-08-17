# ipcam_detect — IP kamera uchun yengil real-time obyekt deteksiyasi

RTSP / HTTP / ONVIF oqimlaridan real vaqtda kadr olib, YOLOv8n / YOLO11n
(ONNX yoki OpenVINO) bilan obyektlarni aniqlaydigan **kam CPU va kam RAM**
sarflaydigan Python moduli. PyTorch runtime'ga bog'liq emas.

---

## 1. Arxitektura

```
┌──────────────┐   RTSP/TCP   ┌────────────────────┐
│  IP kamera   │─────────────▶│  StreamHandler     │  (alohida thread)
└──────────────┘              │  PyAV / OpenCV     │
                              │  reconnect + drop  │
                              └─────────┬──────────┘
                                        │ deque(maxlen=1)   ← faqat eng
                                        ▼                     oxirgi kadr
                              ┌────────────────────┐
                              │  PipelineManager   │  (asosiy thread)
                              └─────────┬──────────┘
                    har N-kadr │        │ oraliq kadrlar
                               ▼        ▼
                  ┌──────────────┐  ┌──────────────┐
                  │ObjectDetector│  │  BoxTracker  │
                  │ ONNX/OpenVINO│  │ cache / MOSSE│
                  └──────┬───────┘  └──────┬───────┘
                         └────────┬────────┘
                                  ▼
                  Visualizer (ixtiyoriy) │ JSONL │ callback
```

**Producer-Consumer**: o'qish (I/O-bound) va inference (CPU-bound) butunlay
ajratilgan. Ular orasida `deque(maxlen=1)` — eski kadr avtomatik tashlanadi,
navbat hech qachon o'smaydi, latency bir kadrdan oshmaydi.

**Backpressure**: iste'molchi band bo'lsa, producer YUV→BGR konvertatsiyasini
(eng qimmat operatsiya) umuman bajarmaydi — dekod davom etadi, CPU tejaladi.

| Sinf | Fayl | Vazifa |
|---|---|---|
| `StreamHandler` | [stream_handler.py](ipcam_detect/stream_handler.py) | Kadr o'qish thread'i, reconnect, frame dropping |
| `BaseDetector` / `OnnxDetector` / `OpenVinoDetector` | [detector.py](ipcam_detect/detector.py) | Letterbox, inference, class-aware NMS |
| `BoxTracker` | [tracker.py](ipcam_detect/tracker.py) | Oraliq kadrlarda qutilar |
| `PipelineManager` | [pipeline.py](ipcam_detect/pipeline.py) | Umumiy quvur, graceful shutdown |
| `ResourceMonitor` | [resource_monitor.py](ipcam_detect/resource_monitor.py) | psutil CPU/RAM |
| `Visualizer` | [visualizer.py](ipcam_detect/visualizer.py) | Ixtiyoriy GUI (headless default) |
| `discovery` | [discovery.py](ipcam_detect/discovery.py) | ONVIF/port qidiruvi, RTSP URL aniqlash |

---

## 2. O'rnatish

```bash
pip install -r requirements.txt
```

GUI (`--show`) kerak bo'lsa `opencv-python-headless` o'rniga `opencv-python`,
`--tracker light` kerak bo'lsa `opencv-contrib-python` o'rnating.

**RTSP uchun PyAV shart emas, lekin kuchli tavsiya etiladi** (`pip install av`):
aniq ulanish timeout'i, past kechikish (`fflags=nobuffer`) va apparat dekod
faqat unda bor. O'rnatilmagan bo'lsa dastur avtomatik OpenCV backend'iga
o'tadi va bu haqda logda ogohlantiradi.

### Modelni tayyorlash (bir marta)

`ultralytics` + `torch` faqat shu bosqichda kerak — ishlash paytida emas:

```bash
python -m venv .venv_export                       # asosiy muhitni buzmaslik uchun
.venv_export/Scripts/pip install ultralytics onnx onnxslim
.venv_export/Scripts/python export_model.py --model yolov8n.pt --format onnx --imgsz 640
```

Natija: `models/yolov8n_640.onnx` (12.3 MB). Fayl nomiga `imgsz` qo'shiladi —
416 eksporti 640 modelni ustidan yozib yubormaydi.

**Muhim:** ONNX modeli qat'iy kirish o'lchami bilan eksport qilinadi. `--imgsz`
ni ishlash paytida o'zgartirish yetarli emas: har o'lcham uchun alohida eksport
kerak. Mos kelmasa detektor ogohlantirish berib model o'lchamiga moslashadi
(ORT ning "invalid dimensions" xatosi bilan yiqilmaydi).

Intel protsessor uchun (eng tejamkor):

```bash
python export_model.py --model yolov8n.pt --format openvino --imgsz 416 --int8
```

---

## 3. GUI (terminalsiz ishlash)

```bash
python gui.py
```

Windows'da `run_gui.bat` faylini ikki marta bosish yetarli (konsol oynasi
ochilmaydi). Barcha sozlamalar oynadan boshqariladi — terminal shart emas.

![GUI](out/gui_screenshot.png)

### Kameralarni avtomatik topish

«🔍 Tarmoqdan kamera qidirish» tugmasi — IP manzil va RTSP yo'lini qo'lda
izlash shart emas:

![Qidiruv](out/gui_discovery.png)

1. **ONVIF WS-Discovery** — UDP multicast `239.255.255.250:3702` ga Probe
   yuboriladi, ONVIF kameralar o'zi javob berib nomi va model'ini bildiradi.
2. **Port skaneri** — ONVIF o'chirilgan/eski kameralar uchun tarmoq
   554, 8554, 80, 8080, 88, 8000, 8899, 2020, 34567, 37777 portlari bo'yicha
   tekshiriladi (portlar ro'yxatini oynadan o'zgartirish mumkin).
3. Kamerani tanlab **faqat login va parol** kiritiladi. Keyin dastur:
   * ONVIF `GetStreamUri` orqali RASMIY RTSP manzilini so'raydi;
   * bo'lmasa **19 ta vendor shabloni**ni (Hikvision, Dahua, Reolink, Axis,
     TP-Link Tapo/VIGI, Uniview, Foscam, Hanwha, Vivotek, Bosch, generic…)
     RTSP `DESCRIBE` bilan birma-bir sinaydi;
   * NVR uchun kanal raqamini ko'rsatish mumkin.
4. Natija: `401` — parol xato (aniq shunday deb yoziladi), `200` — URL
   tayyor, «TANLASH» bilan asosiy oynaga o'tadi.

Tekshiruv `DESCRIBE` orqali bajariladi — video dekodlanmaydi, shuning uchun
19 ta shablonni sinash bir necha soniya oladi. Digest va Basic
autentifikatsiya ikkalasi ham qo'llab-quvvatlanadi.

> **Xavfsizlik:** topilgan URL ichida parol bo'ladi. Loglarda u `***` bilan
> yashiriladi, lekin profilga saqlashda ochiq matnda yoziladi — dastur bu
> haqda ogohlantiradi.

Imkoniyatlari:
* **Jonli preview** — bounding-box'lar bilan, preview tezligi alohida
  sozlanadi (GUI ning o'zi CPU yemasligi uchun).
* **Ko'rsatkich kartalari** — FPS, inference (ms), CPU, RAM + jonli grafik.
* **Oqim holati** — o'qilgan/tashlangan kadr, qayta ulanishlar, deteksiyalar.
* **Aniqlangan obyektlar jadvali** — sinf bo'yicha real vaqtda.
* **Log konsoli** — modulning barcha loglari rangli ko'rinishda.
* **Profillar** — har kamera uchun sozlamalar to'plamini saqlash/yuklash
  (`gui_presets.json`).
* **Sinf tanlash** — 80 ta COCO sinfi qidiruv bilan, «Faqat odam» tugmasi.
* **Snapshot** — joriy kadrni `out/snapshots/` ga saqlash.
* Model topilmasa — eksport buyrug'i bilan ogohlantirish banneri.

Pipeline alohida `QThread` da ishlaydi, shuning uchun og'ir inference paytida
ham interfeys muzlab qolmaydi.

---

## 4. CLI orqali ishga tushirish

```bash
python main.py --url "rtsp://admin:parol@192.168.1.10:554/Streaming/Channels/101"
```

Faqat odamlarni, har 5-kadrda, oyna bilan:

```bash
python main.py --url rtsp://... --show --classes 0 --detect-every 5
```

Eng tejamkor konfiguratsiya (edge qurilma / Raspberry Pi):

```bash
python main.py --url rtsp://... --model models/yolov8n_416.onnx --imgsz 416 --resize 640x360 --detect-every 5 --threads 1 --target-fps 10
```

Modul sifatida:

```python
from ipcam_detect import DetectorConfig, PipelineConfig, PipelineManager, StreamConfig

def on_det(frame, dets):
    if any(d.label == "person" for d in dets):
        print("Odam aniqlandi!")

cfg = PipelineConfig(
    stream=StreamConfig(url="rtsp://...", backend="av", resize_to=(960, 540)),
    detector=DetectorConfig(model_path="models/yolov8n_640.onnx", imgsz=640, class_filter=[0]),
    detect_every=3,
    tracker="cache",
    show=False,
)
PipelineManager(cfg, on_detections=on_det).run()
```

---

## 5. Resurslarni sozlash

Ta'sir kuchi bo'yicha tartiblangan:

| Sozlama | Ta'siri | Tavsiya |
|---|---|---|
| `--imgsz 416` (640 o'rniga) | inference **2.5x tez** (o'lchangan) | uzoq obyektlar kerak bo'lmasa |
| `--detect-every N` | CPU ni ~N marta kamaytiradi | 3–5 |
| `--resize WxH` | dekod + RAM ni kamaytiradi | 960x540 yoki 640x360 |
| `--threads 1` | kontekst almashinuvini kamaytiradi | 1–2 |
| `--target-fps 10` | ortiqcha ishni umuman boshlamaydi | 8–12 |
| `--read-every 2` | rang konvertatsiyasining yarmini tashlaydi | 25 fps kamera uchun |
| headless (default) | GUI CPU/RAM sarfi yo'q | serverda doim |
| `--hwaccel qsv/cuda` | dekodni GPU ga o'tkazadi | drayver bo'lsa |
| `--tracker cache` | oraliq kadrlarda CPU ~0 | statsionar kamera |

Xotira bo'yicha nima qilingan:
* Letterbox kanvasi va NCHW blob **bir marta** ajratiladi va qayta ishlatiladi.
* `np.divide(..., out=...)` — oraliq massivlar yaratilmaydi.
* Kadrlar `copy()` qilinmaydi; chizish in-place bajariladi.
* `deque(maxlen=1)` — navbat o'smaydi, eski kadrga havola darhol uziladi.
* `gc.collect()` faqat `--gc-every N` bilan, har kadrda emas.

### O'lchangan natijalar (haqiqiy yolov8n.onnx, Windows 10, Python 3.13, CPU)

| imgsz | threads | ms/kadr | inference FPS |
|---|---|---|---|
| 640 | 2 | 67.4 | 14.8 |
| 640 | 1 | 107.7 | 9.3 |
| 416 | 2 | **27.2** | **36.7** |
| 416 | 1 | 44.7 | 22.4 |

End-to-end (960x540 manba, imgsz=640, `--detect-every 3`, `--target-fps 15`,
headless): **12.8 FPS**, peak RSS **179 MB**, 500 kadrdan keyin RAM o'sishi
**0.00 MB**.

`--target-fps` — bu yuqori chegara, aniq qiymat emas: kadrlar manba tezligida
keladi, shuning uchun natija manba kadr-panjarasiga kvantlanadi (25 fps manba +
target 15 → amalda ~12.5 FPS).

Dastur `--stats-interval` bo'yicha o'zi hisobot beradi:

```
[RES] CPU   3.4% ( 0.4% umumiy) | RAM   88.9 MB | threads 12 | FPS  12.0 | infer   7.5 ms
```

---

## 6. Barqarorlik

* **Reconnect**: uzilishda eksponensial backoff (1→2→4…30 s), `--timeout`
  orqali FFmpeg `stimeout` beriladi. RTSP default `tcp` — UDP paket
  yo'qotishidan kelib chiqadigan artefaktlar bo'lmaydi.
* **EOF farqlanadi**: video fayl tugashi xato deb hisoblanmaydi (RTSP uzilishi
  esa hisoblanadi). Faylni aylantirish uchun `--loop`.
* **Manba tezligi**: video fayl real vaqt tezligida o'qiladi (`pace_source`).
  Aks holda dekod thread'i faylni maksimal tezlikda "so'rib" olib, inference
  bilan CPU uchun raqobatlashadi — sinovda bu 21 → 24 FPS farqni berdi.
* **Tuzatib bo'lmaydigan xatolar qayta urinilmaydi**: PyAV o'rnatilmagan
  bo'lsa modul bir marta ogohlantirib OpenCV backend'iga o'tadi (avval bu
  cheksiz «qayta ulanish» sikliga tushib qolar edi). Apparat dekod
  (`--hwaccel`) drayver qo'llamasa — xuddi shunday, bir marta ogohlantirib
  CPU dekodga qaytadi.
* **Graceful shutdown**: `SIGINT`/`SIGTERM` ushlanadi, `finally` da thread,
  dekoder, ONNX sessiyasi, GUI oynasi va fayl deskriptorlari yopiladi.

---

## 7. Sinov

Kamera va model bo'lmasa ham to'liq quvurni tekshiradi (sintetik video +
soxta ONNX model yaratadi):

```bash
python tests/selfcheck.py
```

Joriy holat: **43/43 test o'tadi** — pre/post-processing matematikasi,
letterbox teskari transformatsiyasi, class-aware NMS, frame dropping,
reconnect, EOF, tracker, ONNX Runtime sessiyasi, end-to-end pipeline va
500 kadrlik xotira barqarorligi.

Haqiqiy og'irliklar bilan sifat va benchmark (model eksport qilingandan keyin):

```bash
python tests/real_model_check.py
```

**20/20 test o'tadi.** `bus.jpg` da 4 odam + 1 avtobus (max ishonch 0.89),
`zidane.jpg` da 2 odam topiladi; natija rasmlari `out/` papkasiga yoziladi.

GUI ni qo'lda bosmasdan tekshirish (oynani ochadi, oqimni yuritadi,
skrinshot oladi, to'xtatadi):

```bash
python tests/gui_selftest.py
```

**19/19 test o'tadi.**

Kamera qidirish moduli (soxta RTSP va ONVIF serverlari ko'tarilib, Digest
autentifikatsiya, noto'g'ri parol, shablon tanlash, ONVIF `GetStreamUri`,
port skaneri sinaladi):

```bash
python tests/discovery_selftest.py       # 27/27
python tests/gui_discovery_selftest.py   # 25/25
```

---

## 8. Ma'lum cheklovlar

* `--hwaccel` PyAV ≥ 12 va mos FFmpeg build talab qiladi; drayver bo'lmasa
  PyAV xato beradi — CPU dekodga qaytish uchun bayroqni olib tashlang.
* `--tracker light` uchun `opencv-contrib-python` kerak; topilmasa modul
  ogohlantirish bilan `cache` rejimiga o'tadi.
* OpenCV backend'da FFmpeg opsiyalari faqat global env orqali beriladi —
  modul uni lock bilan himoyalab, `VideoCapture` yaratilgach darhol tiklaydi.
* Detektor **thread-safe emas** (letterbox/blob buferlari qayta ishlatilgani
  uchun). Bitta `PipelineManager` ichida bu muammo emas, lekin bir nechta
  kamera kerak bo'lsa har biriga o'z detektorini bering yoki har kamerani
  alohida jarayonda yuriting (`detector=` parametri asosan test/mock uchun).
