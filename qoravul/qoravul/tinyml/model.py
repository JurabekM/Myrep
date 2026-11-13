"""8-16-4-16-8 autoencoder: float training (numpy Adam) and int8 deployment.

Quantisation scheme (symmetric, zero-point 0):
  * input  : x_q = clip(rint((x - mean) / std / s_in), -127, 127), s_in = 8/127
  * weights: per-tensor int8, s_w = max|W| / 127
  * bias   : int32, b / (s_x * s_w)
  * requant: M = s_x * s_w / s_y = M0 * 2^-sh, M0 in [2^30, 2^31)
             y = (acc * M0 + 2^(sh-1)) >> sh   (int64, arithmetic shift)
  * clamp  : hidden [0, 127] (ReLU), output [-127, 127]; output scale = s_in
Detection = envelope stage OR reconstruction score > threshold.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import numpy as np

from .meter import ATTACKS, FEATURES, N_FEATURES, dataset

LAYERS = [8, 16, 4, 16, 8]
S_IN = np.float32(8.0 / 127.0)  # lesson 2: 4/127 clips Gaussian tails
Z_CLIP = 8.0
ENV_MARGIN = 12
ENV_PCT = (0.002, 99.998)
THRESH_PCT = 99.9  # lesson 4
ACT_PCT = 99.9
# Denoising noise (z-units) added to the training *inputs*; targets stay clean.
# A plain AE (or one with noise on every feature) detects night_load only by
# luck of the seed (16%..100%): high current is normal in the evening, and the
# model may equally "explain" a night spike by moving the hour features, whose
# range is only +-22 in x_q. The hour is a noise-free clock, so it gets no
# noise; the measurement features get sigma = 1.5. The AE must then pull
# current back towards what is plausible *for that hour*. Chosen on selection
# seeds (smallest sigma robust on 8/8 seeds); see ARCHITECTURE.md section 5.
DAE_NOISE = np.array([1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 0.0, 0.0])


# ---------------------------------------------------------------- float model
class FloatAE:
    def __init__(self, seed: int = 0) -> None:
        rng = np.random.default_rng(seed)
        self.W, self.b = [], []
        for n_in, n_out in zip(LAYERS[:-1], LAYERS[1:]):
            self.W.append(rng.normal(0.0, math.sqrt(2.0 / n_in), (n_out, n_in)))
            self.b.append(np.zeros(n_out))

    @property
    def n_params(self) -> int:
        return sum(w.size + b.size for w, b in zip(self.W, self.b))

    def forward(self, z: np.ndarray) -> list[np.ndarray]:
        acts = [z]
        for li, (w, b) in enumerate(zip(self.W, self.b)):
            a = acts[-1] @ w.T + b
            if li < len(self.W) - 1:
                a = np.maximum(a, 0.0)
            acts.append(a)
        return acts

    def fit(self, z: np.ndarray, epochs: int = 40, batch: int = 256, lr: float = 3e-3, seed: int = 0,
            noise=0.0) -> list[float]:
        rng = np.random.default_rng(seed)
        params = self.W + self.b
        m = [np.zeros_like(p) for p in params]
        v = [np.zeros_like(p) for p in params]
        b1, b2, eps, t = 0.9, 0.999, 1e-8, 0
        history = []
        nl = len(self.W)
        for ep in range(epochs):
            lr_ep = lr * 0.5 * (1 + math.cos(math.pi * ep / epochs))  # cosine decay
            perm = rng.permutation(len(z))
            tot = 0.0
            for s in range(0, len(z), batch):
                xb = z[perm[s : s + batch]]
                xin = xb + rng.normal(0.0, 1.0, xb.shape) * noise if np.any(noise) else xb
                acts = self.forward(xin)
                diff = acts[-1] - xb
                tot += float((diff**2).sum())
                g = 2.0 * diff / diff.size
                gW, gb = [None] * nl, [None] * nl
                for li in range(nl - 1, -1, -1):
                    gW[li] = g.T @ acts[li]
                    gb[li] = g.sum(0)
                    if li:
                        g = (g @ self.W[li]) * (acts[li] > 0)
                t += 1
                for i, (p, gr) in enumerate(zip(params, gW + gb)):
                    m[i] = b1 * m[i] + (1 - b1) * gr
                    v[i] = b2 * v[i] + (1 - b2) * gr * gr
                    p -= lr_ep * (m[i] / (1 - b1**t)) / (np.sqrt(v[i] / (1 - b2**t)) + eps)
            history.append(tot / z.size)
        return history


# ------------------------------------------------------------- quantisation
def quantize_multiplier(m: float) -> tuple[int, int]:
    """Return (M0, sh) with M0 in [2^30, 2^31) and m ~= M0 * 2^-sh."""
    if not (0.0 < m < 1.0):
        raise ValueError("multiplier must be in (0, 1)")
    q, e = math.frexp(m)  # m = q * 2^e, q in [0.5, 1)
    m0 = int(round(q * (1 << 31)))
    if m0 == 1 << 31:
        m0 //= 2
        e += 1
    sh = 31 - e
    if not (1 <= sh <= 62):
        raise ValueError("shift out of range")
    return m0, sh


def requant(acc: np.ndarray, m0: int, sh: int) -> np.ndarray:
    acc = acc.astype(np.int64)
    return (acc * np.int64(m0) + np.int64(1 << (sh - 1))) >> np.int64(sh)


@dataclass
class QuantAE:
    mean: np.ndarray
    std: np.ndarray
    layers: list[dict]  # w:int8 (out,in), b:int32, m0, sh, relu
    threshold: int = 0
    feat_thresh: np.ndarray = field(default_factory=lambda: np.ones(N_FEATURES, np.int64))
    env_lo: np.ndarray = field(default_factory=lambda: np.full(N_FEATURES, -127, np.int64))
    env_hi: np.ndarray = field(default_factory=lambda: np.full(N_FEATURES, 127, np.int64))
    s_in: np.float32 = S_IN

    # --- inference (must match firmware/qv_infer.c bit for bit)
    def quantize(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)
        z = (x - self.mean) / self.std / self.s_in  # float32 throughout
        return np.clip(np.rint(z), -127, 127).astype(np.int64)

    def reconstruct(self, xq: np.ndarray) -> np.ndarray:
        a = np.asarray(xq, dtype=np.int64)
        for L in self.layers:
            acc = a @ L["w"].astype(np.int64).T + L["b"].astype(np.int64)
            y = requant(acc, L["m0"], L["sh"])
            a = np.clip(y, 0, 127) if L["relu"] else np.clip(y, -127, 127)
        return a

    def errors(self, xq: np.ndarray) -> np.ndarray:
        return (xq - self.reconstruct(xq)) ** 2

    def score_q(self, xq: np.ndarray) -> np.ndarray:
        return self.errors(xq).sum(-1)

    def detect(self, x: np.ndarray) -> dict:
        """Vectorised detection. Returns arrays: xq, score, env, anomaly, culprit."""
        xq = self.quantize(np.atleast_2d(x))
        yq = self.reconstruct(xq)
        err = (xq - yq) ** 2
        score = err.sum(-1)
        viol = (xq < self.env_lo) | (xq > self.env_hi)
        env = viol.any(-1)
        anomaly = env | (score > self.threshold)
        culprit = np.where(env, viol.argmax(-1), _argmax_ratio(err, self.feat_thresh))
        return {"xq": xq, "yq": yq, "score": score, "env": env, "anomaly": anomaly, "culprit": culprit}

    # --- persistence
    def to_dict(self) -> dict:
        return {
            "arch": LAYERS,
            "features": FEATURES,
            "s_in": float(self.s_in),
            "mean": [float(v) for v in self.mean],
            "std": [float(v) for v in self.std],
            "layers": [
                {"w": L["w"].tolist(), "b": L["b"].tolist(), "m0": L["m0"], "sh": L["sh"], "relu": L["relu"]}
                for L in self.layers
            ],
            "threshold": int(self.threshold),
            "feat_thresh": [int(v) for v in self.feat_thresh],
            "env_lo": [int(v) for v in self.env_lo],
            "env_hi": [int(v) for v in self.env_hi],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuantAE":
        layers = [
            {"w": np.array(L["w"], np.int8), "b": np.array(L["b"], np.int32), "m0": int(L["m0"]),
             "sh": int(L["sh"]), "relu": bool(L["relu"])}
            for L in d["layers"]
        ]
        return cls(
            mean=np.array(d["mean"], np.float32),
            std=np.array(d["std"], np.float32),
            layers=layers,
            threshold=int(d["threshold"]),
            feat_thresh=np.array(d["feat_thresh"], np.int64),
            env_lo=np.array(d["env_lo"], np.int64),
            env_hi=np.array(d["env_hi"], np.int64),
            s_in=np.float32(d["s_in"]),
        )

    def save(self, path, extra: dict | None = None) -> None:
        d = self.to_dict()
        if extra:
            d["report"] = extra
        with open(path, "w") as fh:
            json.dump(d, fh, indent=1)

    @classmethod
    def load(cls, path) -> "QuantAE":
        with open(path) as fh:
            return cls.from_dict(json.load(fh))


def _argmax_ratio(err: np.ndarray, ft: np.ndarray) -> np.ndarray:
    """argmax_k err[k]/ft[k] with exact integer comparison, first index on ties."""
    err = np.atleast_2d(err).astype(np.int64)
    best = np.zeros(err.shape[0], np.int64)
    for k in range(1, err.shape[1]):
        cur_e = np.take_along_axis(err, best[:, None], 1)[:, 0]
        cur_t = ft[best]
        better = err[:, k] * cur_t > cur_e * ft[k]
        best = np.where(better, k, best)
    return best


def quantize_float(ae: FloatAE, mean, std, z_calib: np.ndarray) -> QuantAE:
    acts = ae.forward(z_calib)
    layers = []
    s_x = float(S_IN)
    n = len(ae.W)
    for li, (w, b) in enumerate(zip(ae.W, ae.b)):
        s_w = float(np.abs(w).max()) / 127.0
        wq = np.clip(np.round(w / s_w), -127, 127).astype(np.int8)
        bq = np.round(b / (s_x * s_w)).astype(np.int64)
        assert np.abs(bq).max() < 2**31
        relu = li < n - 1
        # Per-tensor scale = widest per-unit 99.9th percentile, so no unit saturates
        # on more than 0.1% of windows (a pooled percentile lets wide units clip).
        s_y = float(np.percentile(acts[li + 1], ACT_PCT, axis=0).max()) / 127.0 if relu else float(S_IN)
        m0, sh = quantize_multiplier(s_x * s_w / s_y)
        layers.append({"w": wq, "b": bq.astype(np.int32), "m0": m0, "sh": sh, "relu": relu})
        s_x = s_y
    return QuantAE(mean=mean.astype(np.float32), std=std.astype(np.float32), layers=layers)


def calibrate(q: QuantAE, x_train: np.ndarray, x_val: np.ndarray) -> None:
    """Envelope from training x_q, score/feature thresholds from validation."""
    xq = q.quantize(x_train)
    lo, hi = np.percentile(xq, ENV_PCT, axis=0)
    q.env_lo = np.floor(lo).astype(np.int64) - ENV_MARGIN
    q.env_hi = np.ceil(hi).astype(np.int64) + ENV_MARGIN
    err = q.errors(q.quantize(x_val))
    q.threshold = int(math.ceil(np.percentile(err.sum(-1), THRESH_PCT)))
    q.feat_thresh = (np.ceil(np.percentile(err, THRESH_PCT, axis=0)) + 1).astype(np.int64)


def evaluate(q: QuantAE, n_test: int = 100_000, n_attack: int = 5_000, seed: int = 100) -> dict:
    """Window-level FPR on unseen households and per-attack TPR."""
    x = dataset(meters=4096, n=n_test, seed=seed)
    d = q.detect(x)
    rep = {
        "fpr": float(d["anomaly"].mean()),
        "fpr_envelope": float(d["env"].mean()),
        "fpr_score": float((d["score"] > q.threshold).mean()),
        "tpr": {},
    }
    for i, att in enumerate(ATTACKS):
        da = q.detect(dataset(meters=4096, n=n_attack, seed=seed + 1 + i, attack=att))
        rep["tpr"][att] = float(da["anomaly"].mean())
    return rep


def train_and_quantize(meters: int = 4096, n_train: int = 120_000, n_val: int = 60_000, epochs: int = 40,
                       seed: int = 0, verbose: bool = False) -> tuple[QuantAE, dict]:
    x_tr = dataset(meters=meters, n=n_train, seed=seed + 1)
    x_val = dataset(meters=meters, n=n_val, seed=seed + 2)
    mean = x_tr.mean(0).astype(np.float32)
    std = x_tr.std(0).astype(np.float32)
    z_tr = np.clip((x_tr - mean) / std, -Z_CLIP, Z_CLIP).astype(np.float64)
    ae = FloatAE(seed)
    hist = ae.fit(z_tr, epochs=epochs, seed=seed, noise=DAE_NOISE)
    if verbose:
        print(f"float AE: {ae.n_params} params, final train MSE {hist[-1]:.4f}")
    q = quantize_float(ae, mean, std, z_tr[:20_000])
    calibrate(q, x_tr, x_val)
    return q, {"params": ae.n_params, "train_mse": hist[-1], "loss_curve": hist}
