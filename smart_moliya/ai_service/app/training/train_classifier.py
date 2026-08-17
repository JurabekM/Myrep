"""Kategoriyalash modelini vazn faylga saqlab o'qitish (CLI skript).

Runtime'da (`ClassifierService`) model har safar jarayon boshlanganda seed
to'plamdan xotirada o'qitiladi - bu kichik to'plam uchun yetarli va tez.
Foydalanuvchi tranzaksiyalari to'plangach, ushbu skript orqali kattaroq
datasetda o'qitib, natijani diskka saqlash mumkin:

    python -m app.training.train_classifier --output app/models/weights/classifier.pt

Keyin `ClassifierService.__init__` shu faylni yuklaydigan qilib
(torch.load) yangilanadi.
"""

import argparse
from pathlib import Path

import torch

from app.models.classifier import build_and_train_seed_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Moliya kategoriyalash modelini o'qitish")
    parser.add_argument("--output", type=str, default="app/models/weights/classifier.pt")
    parser.add_argument("--epochs", type=int, default=300)
    args = parser.parse_args()

    model, vocabulary, labels = build_and_train_seed_model(epochs=args.epochs)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "vocabulary": vocabulary.token_to_index,
            "labels": labels,
        },
        output_path,
    )
    print(f"Model saqlandi: {output_path} ({len(labels)} kategoriya, {vocabulary.size} so'zlik lug'at)")


if __name__ == "__main__":
    main()
