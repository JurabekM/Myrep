"""ObjectDetector — YOLOv8n/YOLO11n uchun CPU-optimallashtirilgan inference.

PyTorch (.pt) **ishlatilmaydi**: torch runtime ~1 GB RAM oladi. O'rniga:
  * ``onnx``     — ONNX Runtime (CPUExecutionProvider), ~100 MB RAM.
  * ``openvino`` — Intel CPU/iGPU uchun eng tez variant.

Optimizatsiyalar:
  * Letterbox kanvasi va blob buferi **bir marta** ajratiladi va qayta
    ishlatiladi (har kadrda `np.zeros` chaqirilmaydi -> GC bosimi yo'q).
  * Thread soni cheklanadi (`num_threads`) — IP kamera uchun 1-2 yetarli,
    ko'p thread faqat kontekst almashinuviga CPU yeydi.
  * NMS C++ tomonda (`cv2.dnn.NMSBoxesBatched`, class-aware) — sof Python
    siklidan ~10x tez va turli sinfdagi qutilar bir-birini o'chirmaydi.
  * Class filter inference dan **keyin, lekin NMS dan oldin** qo'llanadi.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .config import DetectorConfig

logger = logging.getLogger(__name__)

COCO_CLASSES: Tuple[str, ...] = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
)


#: OpenCV 4.7+ da mavjud; eskiroq versiyalarda `None` -> fallback ishlaydi
_NMS_BATCHED = getattr(cv2.dnn, "NMSBoxesBatched", None)


def _nms(
    rects: List[List[float]],
    scores: List[float],
    class_ids: List[int],
    conf: float,
    iou: float,
) -> np.ndarray:
    """Class-aware NMS. Iloji bo'lsa C++ `NMSBoxesBatched`, aks holda fallback."""
    if _NMS_BATCHED is not None:
        keep = _NMS_BATCHED(rects, scores, class_ids, conf, iou)
        return np.asarray(keep, dtype=int).reshape(-1) if len(keep) else np.empty(0, int)

    # Fallback: har bir sinf uchun alohida NMS (OpenCV < 4.7)
    cls_arr = np.asarray(class_ids)
    out: List[int] = []
    for cid in np.unique(cls_arr):
        sel = np.flatnonzero(cls_arr == cid)
        idxs = cv2.dnn.NMSBoxes(
            [rects[i] for i in sel], [scores[i] for i in sel], conf, iou
        )
        if len(idxs):
            out.extend(sel[np.asarray(idxs).reshape(-1)].tolist())
    return np.asarray(out, dtype=int)


@dataclass(slots=True)
class Detection:
    """Bitta aniqlangan obyekt (koordinatalar — original kadr o'lchamida)."""

    x1: int
    y1: int
    x2: int
    y2: int
    score: float
    class_id: int
    label: str = ""

    @property
    def xywh(self) -> Tuple[int, int, int, int]:
        return self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1

    def as_dict(self) -> dict:
        return {
            "bbox": [self.x1, self.y1, self.x2, self.y2],
            "score": round(self.score, 3),
            "class_id": self.class_id,
            "label": self.label,
        }


# --------------------------------------------------------------------- base
class BaseDetector(ABC):
    """Barcha backend'lar uchun umumiy pre/post-processing.

    DIQQAT: thread-safe EMAS — pre-processing buferlari qayta ishlatilgani
    uchun bitta obyektni bir vaqtda ikki thread'dan chaqirmang.
    """

    def __init__(self, cfg: DetectorConfig) -> None:
        self.cfg = cfg
        self.imgsz = int(cfg.imgsz)
        self.labels: Tuple[str, ...] = self._load_labels(cfg.labels_path)
        self._class_filter = set(cfg.class_filter) if cfg.class_filter else None

        # --- Qayta ishlatiluvchi buferlar (har kadrda allokatsiya YO'Q) ---
        # `_alloc_buffers()` da ajratiladi:
        #   _canvas — letterbox kanvasi (114 = YOLO ning pad rangi)
        #   _hwc    — oraliq HWC float32 (normalizatsiya natijasi)
        #   _blob   — NCHW float32 model kirishi
        self._canvas: np.ndarray
        self._hwc: np.ndarray
        self._blob: np.ndarray
        self._last_meta: Tuple[float, int, int] = (1.0, 0, 0)  # (ratio, padx, pady)
        self._alloc_buffers()

    def _alloc_buffers(self) -> None:
        """Buferlarni `self.imgsz` bo'yicha (qayta) ajratadi."""
        self._canvas = np.full((self.imgsz, self.imgsz, 3), 114, dtype=np.uint8)
        self._hwc = np.empty((self.imgsz, self.imgsz, 3), dtype=np.float32)
        self._blob = np.empty((1, 3, self.imgsz, self.imgsz), dtype=np.float32)

    def _sync_imgsz(self, model_imgsz: Optional[int]) -> None:
        """Model qat'iy kirish o'lchamiga ega bo'lsa, unga moslashadi.

        ONNX/OpenVINO modellari odatda `dynamic=False` bilan eksport qilinadi,
        ya'ni kirish o'lchami qotirilgan. Konfiguratsiyadagi `imgsz` boshqacha
        bo'lsa, inference "invalid dimensions" xatosi bilan yiqiladi — shuning
        uchun bu yerda jimgina emas, ogohlantirish bilan moslashtiramiz.
        """
        if not model_imgsz or model_imgsz == self.imgsz:
            return
        logger.warning(
            "Model qat'iy %dx%d kirish bilan eksport qilingan — imgsz=%d "
            "o'rniga %d ishlatiladi. Boshqa o'lcham kerak bo'lsa modelni "
            "`export_model.py --imgsz %d` bilan qayta eksport qiling.",
            model_imgsz, model_imgsz, self.imgsz, model_imgsz, self.imgsz,
        )
        self.imgsz = model_imgsz
        self._alloc_buffers()

    @staticmethod
    def _load_labels(path: Optional[str]) -> Tuple[str, ...]:
        if not path:
            return COCO_CLASSES
        with open(path, "r", encoding="utf-8") as fh:
            return tuple(line.strip() for line in fh if line.strip())

    # ---------------------------------------------------------- preprocess
    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """BGR kadr -> NCHW float32 blob. Nisbatni saqlaydi (letterbox)."""
        h, w = frame.shape[:2]
        r = min(self.imgsz / h, self.imgsz / w)
        nw, nh = int(round(w * r)), int(round(h * r))
        pad_x, pad_y = (self.imgsz - nw) // 2, (self.imgsz - nh) // 2

        self._canvas[:] = 114  # kanvasni tozalash (yangi array yaratmasdan)
        # dst= parametri -> natija to'g'ridan-to'g'ri kanvas ichiga yoziladi
        cv2.resize(
            frame, (nw, nh),
            dst=self._canvas[pad_y:pad_y + nh, pad_x:pad_x + nw],
            interpolation=cv2.INTER_LINEAR,
        )
        # BGR->RGB (`[:, :, ::-1]` — bu view, nusxa emas) + /255 normalizatsiya.
        # `out=` tufayli oraliq massiv yaratilmaydi.
        np.divide(self._canvas[:, :, ::-1], 255.0, out=self._hwc)
        # HWC -> CHW: transpose view, natija to'g'ridan-to'g'ri blob buferiga
        self._blob[0] = self._hwc.transpose(2, 0, 1)
        self._last_meta = (r, pad_x, pad_y)
        return self._blob

    # --------------------------------------------------------- postprocess
    def _postprocess(self, output: np.ndarray, frame_shape: Tuple[int, int]) -> List[Detection]:
        """YOLOv8/YOLO11 chiqishini `Detection` ro'yxatiga aylantiradi.

        Kutilgan shakl: (1, 4+nc, N) yoki (1, N, 4+nc).
        """
        pred = output
        if pred.ndim == 3:
            pred = pred[0]
        # Orientatsiyani aniqlash: (4+nc, N) yoki (N, 4+nc)?
        # Avval class nomlari soniga tayanamiz — bu "N < 4+nc" holatida ham
        # (kichik/maxsus modellar) to'g'ri ishlaydi. Topilmasa — evristika.
        nfeat = 4 + len(self.labels)
        if pred.shape[0] == nfeat and pred.shape[1] != nfeat:
            pred = pred.T                       # (4+nc, N) -> (N, 4+nc)
        elif pred.shape[1] != nfeat and pred.shape[0] < pred.shape[1]:
            pred = pred.T

        boxes_xywh = pred[:, :4]
        scores_all = pred[:, 4:]
        class_ids = scores_all.argmax(axis=1)
        scores = scores_all[np.arange(scores_all.shape[0]), class_ids]

        keep = scores >= self.cfg.conf_threshold
        if self._class_filter is not None:
            keep &= np.isin(class_ids, list(self._class_filter))
        if not keep.any():
            return []

        boxes_xywh = boxes_xywh[keep]
        scores = scores[keep]
        class_ids = class_ids[keep]

        r, pad_x, pad_y = self._last_meta
        # cx,cy,w,h (letterbox koordinatasi) -> x1,y1,x2,y2 (original kadr)
        cx, cy, bw, bh = boxes_xywh.T
        x1 = (cx - bw / 2 - pad_x) / r
        y1 = (cy - bh / 2 - pad_y) / r
        x2 = (cx + bw / 2 - pad_x) / r
        y2 = (cy + bh / 2 - pad_y) / r

        H, W = frame_shape
        np.clip(x1, 0, W - 1, out=x1)
        np.clip(y1, 0, H - 1, out=y1)
        np.clip(x2, 0, W - 1, out=x2)
        np.clip(y2, 0, H - 1, out=y2)

        rects = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).tolist()
        # Class-aware NMS: turli sinfdagi ustma-ust qutilar (masalan odam va
        # velosiped) bir-birini o'chirib yubormasligi kerak.
        idxs = _nms(rects, scores.tolist(), class_ids.tolist(),
                    self.cfg.conf_threshold, self.cfg.iou_threshold)
        if len(idxs) == 0:
            return []

        out: List[Detection] = []
        for i in idxs:
            cid = int(class_ids[i])
            out.append(
                Detection(
                    x1=int(x1[i]), y1=int(y1[i]), x2=int(x2[i]), y2=int(y2[i]),
                    score=float(scores[i]), class_id=cid,
                    label=self.labels[cid] if cid < len(self.labels) else str(cid),
                )
            )
        return out

    # ------------------------------------------------------------- public
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Bitta kadrda deteksiya. Kadr **o'zgartirilmaydi**."""
        blob = self._preprocess(frame)
        raw = self._infer(blob)
        return self._postprocess(raw, frame.shape[:2])

    @abstractmethod
    def _infer(self, blob: np.ndarray) -> np.ndarray:
        """Backend-ga xos xom inference."""

    def close(self) -> None:
        """Resurslarni bo'shatish (subclass override qilishi mumkin)."""

    def __enter__(self) -> "BaseDetector":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


# --------------------------------------------------------------------- ONNX
class OnnxDetector(BaseDetector):
    """ONNX Runtime backend (cross-platform, CPU/CUDA/DirectML)."""

    def __init__(self, cfg: DetectorConfig) -> None:
        super().__init__(cfg)
        import onnxruntime as ort  # og'ir import — faqat kerak bo'lganda

        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # Thread cheklovi — past CPU footprint uchun eng muhim sozlama
        so.intra_op_num_threads = cfg.num_threads
        so.inter_op_num_threads = 1
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.enable_mem_pattern = True   # bufer qayta ishlatiladi -> kam malloc
        so.enable_cpu_mem_arena = True
        so.log_severity_level = 3

        providers = list(cfg.providers) if cfg.providers else ["CPUExecutionProvider"]
        available = ort.get_available_providers()
        providers = [p for p in providers if p in available] or ["CPUExecutionProvider"]

        if not os.path.exists(cfg.model_path):
            raise FileNotFoundError(
                f"Model topilmadi: {cfg.model_path} — avval export_model.py ni ishga tushiring"
            )
        self.session = ort.InferenceSession(cfg.model_path, so, providers=providers)
        self._input_name = self.session.get_inputs()[0].name
        self._output_names = [o.name for o in self.session.get_outputs()]
        # IOBinding uchun ort qiymat — har chaqiriqda yangi obyekt yaratmaslik
        self._run_opts = ort.RunOptions()
        logger.info(
            "ONNX Runtime tayyor: %s | providers=%s | threads=%d",
            os.path.basename(cfg.model_path), providers, cfg.num_threads,
        )

        # Model kirish o'lchami qat'iy bo'lsa (dynamic=False) — unga moslashamiz
        shape = self.session.get_inputs()[0].shape
        self._sync_imgsz(shape[-1] if isinstance(shape[-1], int) else None)

    def _infer(self, blob: np.ndarray) -> np.ndarray:
        outputs = self.session.run(self._output_names, {self._input_name: blob}, self._run_opts)
        return outputs[0]

    def close(self) -> None:
        self.session = None  # type: ignore[assignment]


# ----------------------------------------------------------------- OpenVINO
class OpenVinoDetector(BaseDetector):
    """OpenVINO backend — Intel CPU/iGPU/NPU da eng yuqori FPS/Watt."""

    def __init__(self, cfg: DetectorConfig) -> None:
        super().__init__(cfg)
        from openvino import Core, properties  # type: ignore

        core = Core()
        device = (cfg.providers[0] if cfg.providers else "CPU").upper()
        model = core.read_model(cfg.model_path)
        config = {
            properties.hint.performance_mode(): "LATENCY",  # bitta oqim -> latency
            properties.inference_num_threads(): cfg.num_threads,
            properties.hint.num_requests(): 1,
        }
        self.compiled = core.compile_model(model, device, config)
        self.request = self.compiled.create_infer_request()  # bitta qayta ishlatiluvchi request
        self._out_port = self.compiled.output(0)
        logger.info("OpenVINO tayyor: %s | device=%s", cfg.model_path, device)

        # ONNX dagi kabi: qat'iy kirish o'lchamiga moslashamiz
        try:
            in_shape = list(self.compiled.input(0).shape)
            self._sync_imgsz(int(in_shape[-1]) if in_shape[-1] else None)
        except Exception:  # dinamik shakl -> o'lchamni o'zimiz belgilaymiz
            logger.debug("OpenVINO kirish shakli dinamik")

    def _infer(self, blob: np.ndarray) -> np.ndarray:
        self.request.infer({0: blob})
        return self.request.get_tensor(self._out_port).data

    def close(self) -> None:
        self.request = None  # type: ignore[assignment]
        self.compiled = None  # type: ignore[assignment]


def build_detector(cfg: DetectorConfig) -> BaseDetector:
    """Factory: konfiguratsiyaga qarab kerakli backend'ni qaytaradi."""
    if cfg.backend == "openvino":
        return OpenVinoDetector(cfg)
    if cfg.backend == "onnx":
        return OnnxDetector(cfg)
    raise ValueError(f"Noma'lum backend: {cfg.backend}")
