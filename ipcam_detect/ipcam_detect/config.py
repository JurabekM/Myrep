"""Konfiguratsiya obyektlari.

Butun pipeline sozlamalari shu yerda — dataclass ko'rinishida, type-hint bilan.
Hech qanday og'ir import yo'q (numpy/torch/cv2 emas), shuning uchun modul
juda tez yuklanadi va CLI `--help` ham bir zumda ishlaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Sequence, Tuple

# Backend nomlari
StreamBackend = Literal["av", "opencv"]
InferenceBackend = Literal["onnx", "openvino"]
TrackerKind = Literal["none", "cache", "light"]


@dataclass(slots=True)
class StreamConfig:
    """Video oqim (RTSP/HTTP/ONVIF snapshot URL) sozlamalari."""

    url: str
    backend: StreamBackend = "av"
    #: RTSP uchun transport. UDP paket yo'qotadi -> artefakt; TCP barqaror.
    rtsp_transport: Literal["tcp", "udp"] = "tcp"
    #: Ulanish/o'qish timeout (sekund). PyAV va FFmpeg mikrosoniyaga o'giradi.
    timeout_sec: float = 8.0
    #: Uzilganda qayta ulanish urinishlari orasidagi minimal/maksimal pauza.
    reconnect_min_delay: float = 1.0
    reconnect_max_delay: float = 30.0
    #: 0 = cheksiz qayta ulanish.
    max_reconnects: int = 0
    #: Chekli manba (video fayl) tugaganda boshidan qayta o'qish.
    #: Jonli oqimga (RTSP) ta'siri yo'q — u har doim qayta ulanadi.
    loop_source: bool = False
    #: Video faylni o'z FPS'ida (real vaqt tezligida) o'qish. Aks holda
    #: fayl maksimal tezlikda "so'rib" olinadi va dekod thread'i inference
    #: bilan CPU uchun raqobatlashadi. Jonli oqimda ahamiyatsiz — u allaqachon
    #: tarmoq tezligi bilan cheklangan.
    pace_source: bool = True
    #: Dekoder ichidagi thread soni (0 = FFmpeg o'zi tanlaydi).
    decoder_threads: int = 1
    #: Apparat dekod nomi: "cuda", "qsv", "vaapi", "d3d11va" yoki None (CPU).
    hwaccel: Optional[str] = None
    #: Freymni o'qishdayoq kichraytirish (W, H). None -> original o'lcham.
    #: Bu RAM va CPU ni eng ko'p tejaydigan sozlama.
    resize_to: Optional[Tuple[int, int]] = None
    #: Har N-chi kadrni o'qish (2 = yarmini tashlab yuborish). Dekod baribir
    #: bo'ladi, lekin rang konvertatsiyasi (eng qimmat qism) tashlanadi.
    read_every: int = 1


@dataclass(slots=True)
class DetectorConfig:
    """Model va inference sozlamalari."""

    #: .onnx fayl yo'li yoki OpenVINO uchun .xml / model_dir.
    model_path: str
    backend: InferenceBackend = "onnx"
    #: Modelga kiruvchi kvadrat o'lcham (640 yoki 416).
    imgsz: int = 640
    conf_threshold: float = 0.35
    iou_threshold: float = 0.45
    #: Faqat shu class id lar qoldiriladi (masalan {0} = odam). None = hammasi.
    class_filter: Optional[Sequence[int]] = None
    #: ONNX Runtime / OpenVINO uchun CPU thread soni. Kam thread = kam
    #: kontekst almashinuvi = past CPU. 1..2 IP-kamera uchun odatda yetarli.
    num_threads: int = 2
    providers: Optional[Sequence[str]] = None  # None -> CPUExecutionProvider
    #: COCO class nomlari fayli (har qatorda bitta nom). None -> ichki ro'yxat.
    labels_path: Optional[str] = None


@dataclass(slots=True)
class PipelineConfig:
    """Umumiy quvur sozlamalari."""

    stream: StreamConfig
    detector: DetectorConfig
    #: Har nechchinchi kadrda haqiqiy inference bajarilsin.
    detect_every: int = 3
    #: Oraliq kadrlarda nima qilinsin.
    tracker: TrackerKind = "cache"
    #: GUI oyna. False -> headless (server rejimi, eng tejamkor).
    show: bool = False
    window_name: str = "IPCam Detect"
    #: Chiqish FPS cheklovi (0 = cheklanmagan). CPU ni tejash uchun foydali.
    #: Bu YUQORI CHEGARA, aniq qiymat emas: kadrlar faqat manba tezligida
    #: keladi, shuning uchun natija manba kadr-panjarasiga kvantlanadi
    #: (25 fps manba + target 15 -> amalda ~12.5 FPS, chunki 66 ms 40 ms
    #: karrasiga yaxlitlanadi).
    target_fps: float = 0.0
    #: Resurs monitoringi intervali (sekund, 0 = o'chirilgan).
    stats_interval: float = 5.0
    #: Natijalarni JSONL faylga yozish.
    events_path: Optional[str] = None
    log_level: str = "INFO"
    #: Nechta detektsiyadan keyin gc.collect() chaqirilsin (0 = hech qachon).
    gc_every: int = 0
    extra: dict = field(default_factory=dict)
