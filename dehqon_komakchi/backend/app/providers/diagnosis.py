"""Provider-agnostic crop diagnosis, mirroring the Android app's on-device
`CropDiagnosisProvider` contract. Useful for a future server-side/ensemble model or for
clients that cannot run on-device inference. Swap `MockCropDiagnosisProvider` for a real
model server via `get_diagnosis_provider()` once `CROP_DIAGNOSIS_MODEL_ENDPOINT` is set.

Safety contract (must hold for every implementation):
- Never assert high confidence when the signal is weak; prefer "unclear" + low confidence.
- Never include specific chemical brand names, dosages, or off-label/banned treatment
  instructions in the guidance text -- keep chemical-related advice generic and always
  recommend consulting a licensed agronomist first.
"""

import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from PIL import Image, UnidentifiedImageError

from app.config import get_settings

LOW_CONFIDENCE_THRESHOLD = 0.45
MIN_DIMENSION_PX = 200


class DiagnosisCategory(str, Enum):
    PEST = "PEST"
    FUNGAL = "FUNGAL"
    NUTRIENT = "NUTRIENT"
    WATERING = "WATERING"
    HEAT_STRESS = "HEAT_STRESS"
    UNCLEAR = "UNCLEAR"


@dataclass
class DiagnosisResult:
    category: DiagnosisCategory
    confidence: float
    cause: str
    safe_steps: list[str]
    watch_for: list[str]
    consult_advice: str


class PhotoQualityError(ValueError):
    def __init__(self, reason_key: str):
        self.reason_key = reason_key
        super().__init__(reason_key)


_CONTENT: dict[DiagnosisCategory, dict] = {
    DiagnosisCategory.PEST: {
        "cause": "Bargda zararkunanda hasharotlar ta'siri belgilari ko'rinmoqda.",
        "steps": [
            "Barglarning orqa tomonini tekshirib, hasharot yoki tuxumlarni qo'lda yig'ib oling.",
            "Zararlangan barglarni kesib, ekin maydonidan uzoqlashtiring.",
            "Har qanday kimyoviy dori qo'llashdan oldin agronom bilan maslahatlashing.",
        ],
        "watch": ["Yangi teshiklar", "Barglarning tez sarg'ayishi"],
        "consult": "Agar tez tarqalsa, mahalliy agronomga murojaat qiling.",
    },
    DiagnosisCategory.FUNGAL: {
        "cause": "Zamburug' kasalligiga xos qorong'i dog'lar ehtimoli bor.",
        "steps": [
            "Sug'orishni ildiz ostidan qiling, barglarga suv tegishidan saqlaning.",
            "Zararlangan qismlarni olib tashlang (kompostga qo'shmang).",
            "Fungitsid kerak bo'lsa, faqat ruxsat etilgan preparatlarni yorliq bo'yicha ishlating.",
        ],
        "watch": ["Dog'larning kattalashishi", "Barglarning to'kilishi"],
        "consult": "Dog'lar tez tarqalsa, zudlik bilan agronomga murojaat qiling.",
    },
    DiagnosisCategory.NUTRIENT: {
        "cause": "Sarg'ayish oziqa moddalari yetishmovchiligiga o'xshaydi.",
        "steps": [
            "Tuproq namligini tekshiring.",
            "Yorliqda ko'rsatilgan me'yordagi o'g'itlardan foydalaning.",
        ],
        "watch": ["Sarg'ayish naqshi", "O'sishning sekinlashishi"],
        "consult": "1-2 haftada yaxshilanish bo'lmasa, agronomga murojaat qiling.",
    },
    DiagnosisCategory.WATERING: {
        "cause": "So'lish sug'orish tartibi bilan bog'liq muammoga ishora qiladi.",
        "steps": [
            "So'nggi sug'orish sanasini va tuproq namligini tekshiring.",
            "Sug'orishni erta tong yoki kech kechqurun amalga oshiring.",
        ],
        "watch": ["Kunduzi so'lish, kechqurun tiklanish", "Ildiz chirishi belgilari"],
        "consult": "Holat yomonlashsa, agronomga murojaat qiling.",
    },
    DiagnosisCategory.HEAT_STRESS: {
        "cause": "Ko'rinish issiqlik/quyosh stressiga xos.",
        "steps": [
            "Kunning eng issiq soatlarida vaqtinchalik soyabon qo'ying.",
            "Mulchalash tuproq haroratini pasaytirishga yordam beradi.",
        ],
        "watch": ["Barg qirralarining qovjirashi", "Quyosh kuyishi dog'lari"],
        "consult": "Issiq havo davom etsa, agronom bilan maslahatlashing.",
    },
    DiagnosisCategory.UNCLEAR: {
        "cause": "Suratdan aniq xulosa chiqarib bo'lmadi.",
        "steps": [
            "Yaxshi yorug'likda, bargga yaqinroq yana surat oling.",
            "O'simlikni bir necha kun kuzatib boring.",
        ],
        "watch": ["Belgilarning kuchayishi yoki tarqalishi"],
        "consult": "Ishonchli tashxis kerak bo'lsa, agronomlik xizmatiga murojaat qiling.",
    },
}


def _build_result(category: DiagnosisCategory, confidence: float) -> DiagnosisResult:
    content = _CONTENT[category]
    return DiagnosisResult(
        category=category,
        confidence=confidence,
        cause=content["cause"],
        safe_steps=content["steps"],
        watch_for=content["watch"],
        consult_advice=content["consult"],
    )


class CropDiagnosisProvider(ABC):
    @abstractmethod
    def check_photo_quality(self, image_bytes: bytes) -> str | None:
        """Returns a reason key if the photo should be rejected for retake, else None."""

    @abstractmethod
    def diagnose(self, image_bytes: bytes) -> DiagnosisResult: ...


class MockCropDiagnosisProvider(CropDiagnosisProvider):
    """Same brightness/edge-variance/hue-bucket heuristic as the Android mock, implemented with
    Pillow so backend integration tests exercise equivalent logic without any external model."""

    def _load(self, image_bytes: bytes) -> Image.Image | None:
        try:
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except (UnidentifiedImageError, OSError):
            return None

    def check_photo_quality(self, image_bytes: bytes) -> str | None:
        img = self._load(image_bytes)
        if img is None:
            return "decode_failed"
        if img.width < MIN_DIMENSION_PX or img.height < MIN_DIMENSION_PX:
            return "too_small"

        stats = self._stats(img)
        if stats["mean_brightness"] < 35:
            return "too_dark"
        if stats["mean_brightness"] > 235:
            return "too_bright"
        if stats["edge_variance"] < 8.0:
            return "too_blurry"
        return None

    def diagnose(self, image_bytes: bytes) -> DiagnosisResult:
        img = self._load(image_bytes)
        if img is None:
            return _build_result(DiagnosisCategory.UNCLEAR, 0.2)

        stats = self._stats(img)
        seed = (len(image_bytes) + int(stats["mean_hue"])) & 0xFFFFFFFF
        import random

        rng = random.Random(seed)

        if stats["brown_ratio"] > 0.30:
            category = DiagnosisCategory.FUNGAL
        elif stats["yellow_ratio"] > 0.30:
            category = DiagnosisCategory.NUTRIENT
        elif stats["dark_ratio"] > 0.12:
            category = DiagnosisCategory.PEST
        elif stats["mean_brightness"] > 190 and stats["edge_variance"] < 25:
            category = DiagnosisCategory.HEAT_STRESS
        elif (stats["yellow_ratio"] * 0.5 + stats["dark_ratio"] * 0.3) > 0.25:
            category = DiagnosisCategory.WATERING
        else:
            category = DiagnosisCategory.UNCLEAR

        base_confidence = (
            0.25 + rng.random() * 0.15
            if category == DiagnosisCategory.UNCLEAR
            else 0.5 + rng.random() * 0.35
        )
        confidence = max(0.0, min(0.95, base_confidence))
        return _build_result(category, confidence)

    def _stats(self, img: Image.Image) -> dict:
        small = img.resize((min(64, img.width), min(64, img.height)))
        hsv = small.convert("HSV")
        rgb_pixels = list(small.getdata())
        hsv_pixels = list(hsv.getdata())

        n = len(rgb_pixels)
        sum_brightness = 0.0
        sum_hue = 0.0
        brown = yellow = dark = 0
        prev_brightness = None
        edge_delta_sum = 0.0

        for (r, g, b), (h, s, v) in zip(rgb_pixels, hsv_pixels, strict=True):
            brightness = (r + g + b) / 3.0
            hue_deg = h / 255.0 * 360.0
            sat = s / 255.0

            sum_brightness += brightness
            sum_hue += hue_deg

            if prev_brightness is not None:
                edge_delta_sum += abs(brightness - prev_brightness)
            prev_brightness = brightness

            if 15 <= hue_deg <= 40 and 0.15 * 255 <= v <= 0.55 * 255:
                brown += 1
            if 45 <= hue_deg <= 65 and sat > 0.35:
                yellow += 1
            if brightness < 60:
                dark += 1

        return {
            "mean_brightness": sum_brightness / n if n else 128.0,
            "mean_hue": sum_hue / n if n else 90.0,
            "edge_variance": edge_delta_sum / (n - 1) if n > 1 else 0.0,
            "brown_ratio": brown / n if n else 0.0,
            "yellow_ratio": yellow / n if n else 0.0,
            "dark_ratio": dark / n if n else 0.0,
        }


def get_diagnosis_provider() -> CropDiagnosisProvider:
    settings = get_settings()
    if settings.crop_diagnosis_model_endpoint:
        # A real implementation would call out to the configured model endpoint here.
        pass
    return MockCropDiagnosisProvider()
