"""ipcam_detect — IP kameralar uchun yengil real-time obyekt deteksiyasi.

Minimal foydalanish::

    from ipcam_detect import PipelineConfig, StreamConfig, DetectorConfig, PipelineManager

    cfg = PipelineConfig(
        stream=StreamConfig(url="rtsp://user:pass@192.168.1.10:554/stream1"),
        detector=DetectorConfig(model_path="models/yolov8n.onnx"),
        detect_every=3,
    )
    PipelineManager(cfg).run()
"""

from .config import (
    DetectorConfig,
    InferenceBackend,
    PipelineConfig,
    StreamBackend,
    StreamConfig,
    TrackerKind,
)
from .detector import BaseDetector, COCO_CLASSES, Detection, build_detector
from .discovery import (
    Camera,
    discover,
    find_stream_url,
    local_subnets,
    rtsp_describe,
    scan_subnet,
    ws_discover,
)
from .pipeline import PipelineManager
from .resource_monitor import ResourceMonitor, ResourceSnapshot
from .stream_handler import StreamHandler
from .tracker import BoxTracker

__version__ = "1.0.0"

__all__ = [
    "DetectorConfig",
    "PipelineConfig",
    "StreamConfig",
    "StreamBackend",
    "InferenceBackend",
    "TrackerKind",
    "BaseDetector",
    "Detection",
    "Camera",
    "discover",
    "ws_discover",
    "scan_subnet",
    "find_stream_url",
    "rtsp_describe",
    "local_subnets",
    "COCO_CLASSES",
    "build_detector",
    "PipelineManager",
    "StreamHandler",
    "BoxTracker",
    "ResourceMonitor",
    "ResourceSnapshot",
    "__version__",
]
