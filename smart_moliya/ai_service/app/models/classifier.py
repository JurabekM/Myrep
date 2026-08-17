import torch
from torch import nn

from app.models.seed_data import CATEGORY_SAMPLES
from app.models.vocabulary import Vocabulary


class CategoryClassifier(nn.Module):
    """Bag-of-words + chiziqli qatlam - tranzaksiya matnidan kategoriya bashorati.

    Kichik va tez: to'liq transformer o'rniga ishga tushirishda bir necha soniyada
    o'qitiladigan baseline model. Production'da `app/training/train_classifier.py`
    orqali haqiqiy foydalanuvchi tranzaksiyalari bilan qayta o'qitiladi.
    """

    def __init__(self, vocab_size: int, num_classes: int):
        super().__init__()
        self.linear = nn.Linear(vocab_size, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


def build_and_train_seed_model(epochs: int = 300, lr: float = 0.5) -> tuple[CategoryClassifier, Vocabulary, list[str]]:
    labels = sorted(CATEGORY_SAMPLES.keys())
    label_to_index = {label: idx for idx, label in enumerate(labels)}

    texts: list[str] = []
    targets: list[int] = []
    for label, samples in CATEGORY_SAMPLES.items():
        for sample in samples:
            texts.append(sample)
            targets.append(label_to_index[label])

    vocabulary = Vocabulary.build(texts)
    features = torch.tensor([vocabulary.vectorize(t) for t in texts], dtype=torch.float32)
    target_tensor = torch.tensor(targets, dtype=torch.long)

    model = CategoryClassifier(vocab_size=vocabulary.size, num_classes=len(labels))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        logits = model(features)
        loss = loss_fn(logits, target_tensor)
        loss.backward()
        optimizer.step()

    model.eval()
    return model, vocabulary, labels
