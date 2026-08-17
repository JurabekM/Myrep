"""main.py — ipcam_detect ni CLI orqali ishga tushirish namunasi.

Namunalar::

    # Headless (server rejimi, eng kam resurs)
    python main.py --url "rtsp://admin:pass@192.168.1.10:554/Streaming/Channels/101"

    # Oyna bilan, faqat odamlarni, har 5-kadrda deteksiya
    python main.py --url rtsp://... --show --classes 0 --detect-every 5

    # Webcam yoki lokal fayl bilan sinash
    python main.py --url 0 --backend-stream opencv --show

    # OpenVINO + 416px + kadrni o'qishdayoq 960x540 ga kichraytirish
    python main.py --url rtsp://... --model models/yolov8n_openvino_model/yolov8n.xml \\
        --backend openvino --imgsz 416 --resize 960x540
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Tuple

from ipcam_detect import (
    DetectorConfig,
    PipelineConfig,
    PipelineManager,
    StreamConfig,
)


def _parse_size(value: Optional[str]) -> Optional[Tuple[int, int]]:
    """'960x540' -> (960, 540)."""
    if not value:
        return None
    try:
        w, h = value.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Noto'g'ri o'lcham: {value} (kutilgan: WxH)")


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="IP kamera real-time obyekt deteksiyasi (low CPU / low RAM)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # --- Oqim ---
    g = p.add_argument_group("Video oqim")
    g.add_argument("--url", required=True,
                   help="RTSP/HTTP URL, video fayl yo'li yoki webcam indeksi (0)")
    g.add_argument("--backend-stream", choices=("av", "opencv"), default="av",
                   help="Dekod backend: av (PyAV, tavsiya) yoki opencv")
    g.add_argument("--transport", choices=("tcp", "udp"), default="tcp",
                   help="RTSP transport (tcp barqarorroq)")
    g.add_argument("--resize", type=str, default=None, metavar="WxH",
                   help="Kadrni o'qishdayoq kichraytirish, masalan 960x540")
    g.add_argument("--read-every", type=int, default=1,
                   help="Har N-chi kadrni o'qish (2 = yarmini tashlab yuborish)")
    g.add_argument("--hwaccel", default=None,
                   help="Apparat dekod: cuda / qsv / d3d11va / vaapi")
    g.add_argument("--decoder-threads", type=int, default=1,
                   help="FFmpeg dekod thread soni (1 = eng kam CPU)")
    g.add_argument("--timeout", type=float, default=8.0, help="Ulanish timeout (s)")
    g.add_argument("--loop", action="store_true",
                   help="Video fayl tugaganda boshidan qayta o'qish (sinov uchun)")

    # --- Model ---
    g = p.add_argument_group("Model")
    g.add_argument("--model", default="models/yolov8n_640.onnx",
                   help=".onnx fayl yoki OpenVINO .xml yo'li")
    g.add_argument("--backend", choices=("onnx", "openvino"), default="onnx")
    g.add_argument("--imgsz", type=int, default=640, help="Model kirish o'lchami")
    g.add_argument("--conf", type=float, default=0.35, help="Ishonch chegarasi")
    g.add_argument("--iou", type=float, default=0.45, help="NMS IoU chegarasi")
    g.add_argument("--classes", type=int, nargs="*", default=None,
                   help="Faqat shu class id lar (0=person, 2=car, ...)")
    g.add_argument("--threads", type=int, default=2, help="Inference thread soni")
    g.add_argument("--labels", default=None, help="Class nomlari fayli (.txt/.names)")

    # --- Pipeline ---
    g = p.add_argument_group("Pipeline")
    g.add_argument("--detect-every", type=int, default=3,
                   help="Har N-chi kadrda inference bajarish")
    g.add_argument("--tracker", choices=("none", "cache", "light"), default="cache",
                   help="Oraliq kadrlarda: cache (CPU~0) yoki light (MOSSE/KCF)")
    g.add_argument("--show", action="store_true", help="GUI oyna (default: headless)")
    g.add_argument("--target-fps", type=float, default=0.0,
                   help="Chiqish FPS cheklovi (0 = cheklanmagan)")
    g.add_argument("--stats-interval", type=float, default=5.0,
                   help="CPU/RAM log intervali, s (0 = o'chirilgan)")
    g.add_argument("--events", default=None, help="Deteksiyalarni JSONL faylga yozish")
    g.add_argument("--gc-every", type=int, default=0,
                   help="Har N deteksiyadan keyin gc.collect() (0 = hech qachon)")
    g.add_argument("--log-level", default="INFO",
                   choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return p.parse_args(argv)


def build_config(args: argparse.Namespace) -> PipelineConfig:
    """CLI argumentlaridan `PipelineConfig` yasaydi."""
    url = args.url
    stream_backend = args.backend_stream
    if url.isdigit():  # webcam indeksi
        url = int(url)  # type: ignore[assignment]
        # PyAV URL sifatida int qabul qilmaydi -> webcam uchun OpenCV backend
        if stream_backend == "av":
            logging.getLogger(__name__).info(
                "Webcam indeksi berildi — stream backend 'opencv' ga o'zgartirildi"
            )
            stream_backend = "opencv"

    return PipelineConfig(
        stream=StreamConfig(
            url=url,  # type: ignore[arg-type]
            backend=stream_backend,
            rtsp_transport=args.transport,
            timeout_sec=args.timeout,
            decoder_threads=args.decoder_threads,
            hwaccel=args.hwaccel,
            resize_to=_parse_size(args.resize),
            read_every=max(1, args.read_every),
            loop_source=args.loop,
        ),
        detector=DetectorConfig(
            model_path=args.model,
            backend=args.backend,
            imgsz=args.imgsz,
            conf_threshold=args.conf,
            iou_threshold=args.iou,
            class_filter=args.classes,
            num_threads=args.threads,
            labels_path=args.labels,
        ),
        detect_every=max(1, args.detect_every),
        tracker=args.tracker,
        show=args.show,
        target_fps=args.target_fps,
        stats_interval=args.stats_interval,
        events_path=args.events,
        gc_every=args.gc_every,
        log_level=args.log_level,
    )


def on_detections(frame, detections) -> None:
    """Namunaviy callback — bu yerga alarm/telegram/DB logikasi qo'yiladi."""
    people = [d for d in detections if d.label == "person"]
    if people:
        logging.getLogger("alarm").debug("%d ta odam aniqlandi", len(people))


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = build_config(args)
    try:
        # `with` -> har qanday holatda ham resurslar bo'shatiladi
        with PipelineManager(cfg, on_detections=on_detections) as pipeline:
            pipeline.run()
    except FileNotFoundError as exc:
        logging.error("%s", exc)
        logging.error("Model eksport qiling: python export_model.py --model yolov8n.pt")
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        logging.exception("Ishga tushirish muvaffaqiyatsiz: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
