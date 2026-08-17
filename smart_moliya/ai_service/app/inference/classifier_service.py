import torch
import torch.nn.functional as F

from app.models.classifier import build_and_train_seed_model


class ClassifierService:
    """Kategoriyalash servisi - jarayon boshlanganda seed model bir marta o'qitiladi."""

    def __init__(self):
        self.model, self.vocabulary, self.labels = build_and_train_seed_model()

    def predict(self, text: str) -> tuple[str, float]:
        vector = torch.tensor([self.vocabulary.vectorize(text)], dtype=torch.float32)
        with torch.no_grad():
            logits = self.model(vector)
            probabilities = F.softmax(logits, dim=1)[0]
        best_index = int(torch.argmax(probabilities).item())
        confidence = float(probabilities[best_index].item())

        if vector.sum().item() == 0:
            # Lug'atda mavjud bo'lmagan matn - ishonchli bashorat qilib bo'lmaydi
            return "other", 0.0

        return self.labels[best_index], confidence


_classifier_service: ClassifierService | None = None


def get_classifier_service() -> ClassifierService:
    global _classifier_service
    if _classifier_service is None:
        _classifier_service = ClassifierService()
    return _classifier_service
