#!/usr/bin/env python3
"""M-Pay Shield — LightGBM o'qitish va ONNX eksport.

Kirish: `shield-replay featurize` chiqargan `data/train/features_txn.csv` va
`data/test/features_txn.csv` (belgilarni Rust feature store hisoblagan).
Chiqish (`crates/mpay-shield/models/`):
  shield_v0.onnx  — TreeEnsembleClassifier (LOGISTIC), kirish `input` [N, 27], zipmap yo'q;
  shield_v0.json  — versiya, belgi nomlari, metrikalar;
  data/parity.csv — 500 test qatori + onnxruntime ehtimoli (Rust tract bilan solishtirish uchun).

    uv run python train.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import lightgbm as lgb
import numpy as np
import onnxruntime as ort
import pandas as pd
from onnxmltools import convert_lightgbm
from onnxmltools.convert.common.data_types import FloatTensorType

HERE = Path(__file__).parent
MODELS = HERE.parent / "crates" / "mpay-shield" / "models"
VERSION = "shield-lgbm-v0"


def load(split: str) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(HERE / "data" / split / "features_txn.csv")
    feats = [c for c in df.columns if c not in ("label", "scenario")]
    return df, feats


def metrics(y: np.ndarray, p: np.ndarray, scen: pd.Series) -> dict:
    out = {}
    for thr in (0.5, 0.8):
        pred = p >= thr
        tp = int((pred & (y == 1)).sum())
        fp = int((pred & (y == 0)).sum())
        out[f"precision@{thr}"] = tp / max(tp + fp, 1)
        out[f"recall@{thr}"] = tp / max(int((y == 1).sum()), 1)
        out[f"fpr@{thr}"] = fp / max(int((y == 0).sum()), 1)
    out["per_scenario_recall@0.5"] = {
        s: float((p[scen == s] >= 0.5).mean()) for s in sorted(scen.unique()) if not s.startswith("legit")
    }
    out["per_scenario_flag_rate@0.5_legit"] = {
        s: float((p[scen == s] >= 0.5).mean()) for s in sorted(scen.unique()) if s.startswith("legit")
    }
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    train, feats = load("train")
    test, feats_t = load("test")
    assert feats == feats_t, "train/test belgilari mos emas"
    Xtr, ytr = train[feats].to_numpy(np.float32), train["label"].to_numpy()
    Xte, yte = test[feats].to_numpy(np.float32), test["label"].to_numpy()
    pos = max(int(ytr.sum()), 1)
    model = lgb.LGBMClassifier(
        n_estimators=150,
        num_leaves=15,
        learning_rate=0.05,
        min_child_samples=20,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        scale_pos_weight=min((len(ytr) - pos) / pos, 20.0),
        random_state=7,
        verbose=-1,
    )
    model.fit(Xtr, ytr)
    p_lgb = model.predict_proba(Xte)[:, 1]

    onx = convert_lightgbm(
        model,
        initial_types=[("input", FloatTensorType([None, len(feats)]))],
        zipmap=False,
        target_opset=15,
    )
    MODELS.mkdir(parents=True, exist_ok=True)
    onnx_path = MODELS / "shield_v0.onnx"
    onnx_path.write_bytes(onx.SerializeToString())

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    outs = sess.run(None, {"input": Xte})
    p_onnx = outs[1][:, 1]
    diff = float(np.abs(p_onnx - p_lgb).max())
    assert diff < 1e-4, f"ONNX va LightGBM farqi {diff}"

    m = metrics(yte, p_onnx, test["scenario"])
    meta = {
        "version": VERSION,
        "feature_names": feats,
        "trained_on": f"shield-ml generate.py seed=1 (train), seed=2 (test), {date.today().isoformat()}",
        "lightgbm": lgb.__version__,
        "n_train": int(len(ytr)),
        "n_test": int(len(yte)),
        "onnx_vs_lightgbm_max_diff": diff,
        "test_metrics": m,
        "feature_importance_gain": dict(
            sorted(
                zip(feats, map(float, model.booster_.feature_importance("gain"))), key=lambda kv: -kv[1]
            )[:12]
        ),
    }
    (MODELS / "shield_v0.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    idx = np.random.default_rng(3).choice(len(Xte), size=500, replace=False)
    par = pd.DataFrame(Xte[idx], columns=feats)
    par["prob"] = p_onnx[idx]
    par.to_csv(HERE / "data" / "parity.csv", index=False, float_format="%.9g")

    print(f"model: {onnx_path} ({onnx_path.stat().st_size // 1024} KiB), ONNX↔LightGBM farq {diff:.2e}")
    print(json.dumps(m, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
