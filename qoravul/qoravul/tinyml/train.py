"""Train, quantise, evaluate and export the QORAVUL detector.

    python -m qoravul.tinyml.train [--seed 0] [--epochs 40] [--out models/qv_model.json]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .export_c import export
from .meter import ATTACKS
from .model import train_and_quantize, evaluate

ROOT = Path(__file__).resolve().parents[2]
FPR_MAX = 0.005
TPR_MIN = 0.95


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--meters", type=int, default=4096)
    ap.add_argument("--n-train", type=int, default=120_000)
    ap.add_argument("--out", default=str(ROOT / "models" / "qv_model.json"))
    ap.add_argument("--firmware", default=str(ROOT / "firmware"))
    args = ap.parse_args(argv)

    t0 = time.time()
    q, info = train_and_quantize(meters=args.meters, n_train=args.n_train, epochs=args.epochs, seed=args.seed,
                                 verbose=True)
    t_train = time.time() - t0
    rep = evaluate(q)
    print(f"trained in {t_train:.1f} s, threshold={q.threshold}, feat_thresh={q.feat_thresh.tolist()}")
    print(f"envelope lo={q.env_lo.tolist()} hi={q.env_hi.tolist()}")
    print(f"FPR (window, 100k unseen normal windows): {rep['fpr'] * 100:.3f}%  "
          f"[envelope {rep['fpr_envelope'] * 100:.3f}%, score {rep['fpr_score'] * 100:.3f}%]")
    ok = rep["fpr"] < FPR_MAX
    for att in ATTACKS:
        tpr = rep["tpr"][att]
        ok &= tpr > TPR_MIN
        print(f"TPR {att:<11s}: {tpr * 100:6.2f}%")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    q.save(args.out, extra={"params": info["params"], "train_mse": info["train_mse"], "seed": args.seed,
                            "epochs": args.epochs, **rep})
    ex = export(q, args.firmware)
    print(f"saved {args.out}; exported qv_model.h + qv_vectors.h ({ex['vectors']} vectors, "
          f"{ex['anomalous']} anomalous)")
    print("ACCEPTANCE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
