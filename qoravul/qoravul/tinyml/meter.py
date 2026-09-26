"""Synthetic single-phase household meter (230 V / 50 Hz) and attack models.

All data here is SYNTHETIC. The load profile, noise model and attack
signatures are hand-crafted approximations, not field measurements.

One *window* = one minute of aggregated measurements:
V (RMS volts), I (phase RMS amps), I_n (neutral RMS amps), pf, thd, f (Hz).
"""
from __future__ import annotations

import numpy as np

FEATURES = ["v_dev", "i_norm", "pf", "thd", "f_dev", "n_imb", "h_sin", "h_cos"]
N_FEATURES = len(FEATURES)
ATTACKS = ["bypass", "magnet", "sag", "freq", "night_load"]
NIGHT_HOURS = (1.0, 5.0)  # night_load theft happens between 01:00 and 05:00


def _bump(h, centre, width):
    d = (h - centre + 12.0) % 24.0 - 12.0  # circular distance in hours
    return np.exp(-0.5 * (d / width) ** 2)


def load_profile(h):
    """Mean household current (A) at local hour ``h`` for scale 1."""
    return (
        1.2  # night base: fridge, standby
        + 3.0 * _bump(h, 7.5, 0.9)  # morning 07:30
        + 5.0 * _bump(h, 20.0, 1.6)  # evening 20:00
        + 1.8 * _bump(h, 13.5, 2.5)  # daytime peak
    )


def simulate(hour, scale, phase, rng: np.random.Generator, attack: str | None = None) -> dict:
    """Vectorised window generator. ``hour``, ``scale``, ``phase`` are arrays of equal length."""
    hour = np.asarray(hour, dtype=np.float64)
    n = hour.shape[0]
    scale = np.broadcast_to(np.asarray(scale, dtype=np.float64), (n,))
    phase = np.broadcast_to(np.asarray(phase, dtype=np.float64), (n,))

    i_true = scale * load_profile((hour - phase) % 24.0) * rng.lognormal(0.0, 0.25, n)
    burst = rng.random(n) < 0.05  # kettle / iron / heater
    i_true = i_true + burst * rng.uniform(4.0, 9.0, n)

    if attack == "night_load":
        i_true = rng.uniform(25.0, 45.0, n)

    v = 231.0 + rng.normal(0.0, 1.8, n) - 0.15 * i_true  # feeder impedance drop
    pf = np.clip(0.93 - 0.12 * np.exp(-i_true / 4.0) + rng.normal(0.0, 0.02, n), 0.3, 1.0)
    thd = np.clip(0.03 + 0.07 * np.exp(-i_true / 5.0) + rng.normal(0.0, 0.008, n), 0.005, 1.0)
    f = 50.0 + rng.normal(0.0, 0.03, n)
    i_n = i_true * (1.0 + rng.normal(0.0, 0.008, n))
    i_ph = i_true.copy()

    if attack == "bypass":  # part of the load returns around the phase CT
        i_ph = i_true * rng.uniform(0.2, 0.8, n)
    elif attack == "magnet":  # saturated CT: distorted, under-reading
        i_ph = i_true * rng.uniform(0.3, 0.7, n)
        thd = rng.uniform(0.28, 0.5, n)
        pf = rng.uniform(0.45, 0.65, n)
    elif attack == "sag":  # tampered voltage channel
        v = v * rng.uniform(0.70, 0.85, n)
    elif attack == "freq":  # spoofed / injected frequency reference
        f = 50.0 + rng.choice([-1.0, 1.0], n) * rng.uniform(0.6, 1.5, n)
    elif attack == "night_load":
        pf = rng.uniform(0.95, 0.99, n)
    elif attack is not None:
        raise ValueError(f"unknown attack {attack!r}")

    return {"hour": hour, "V": v, "I": i_ph, "I_n": i_n, "pf": pf, "thd": thd, "f": f}


def features(raw: dict) -> np.ndarray:
    """Map raw window measurements to the 8 detector features (float32, shape (n, 8))."""
    i, i_n = raw["I"], raw["I_n"]
    ang = 2.0 * np.pi * raw["hour"] / 24.0
    x = np.stack(
        [
            raw["V"] / 230.0 - 1.0,
            i / 60.0,
            raw["pf"],
            raw["thd"],
            raw["f"] - 50.0,
            np.abs(i - i_n) / np.maximum(np.maximum(i, i_n), 0.1),
            np.sin(ang),
            np.cos(ang),
        ],
        axis=-1,
    )
    return x.astype(np.float32)


def attack_hours(attack: str | None, rng: np.random.Generator, n: int) -> np.ndarray:
    """Hours of day at which an attack is plausible (night_load only at night)."""
    if attack == "night_load":
        return rng.uniform(*NIGHT_HOURS, n)
    return rng.uniform(0.0, 24.0, n)


def dataset(meters: int = 4096, n: int = 120_000, seed: int = 0, attack: str | None = None) -> np.ndarray:
    """``n`` feature windows drawn from ``meters`` random households."""
    rng = np.random.default_rng(seed)
    scale = rng.uniform(0.6, 1.8, meters)
    phase = rng.normal(0.0, 0.7, meters)
    idx = rng.integers(0, meters, n)
    hours = attack_hours(attack, rng, n)
    return features(simulate(hours, scale[idx], phase[idx], rng, attack))


class VirtualMeter:
    """One household meter producing a window per simulated minute."""

    def __init__(self, seed: int, scale: float | None = None, phase: float | None = None) -> None:
        self.rng = np.random.default_rng(seed)
        self.scale = float(self.rng.uniform(0.6, 1.8) if scale is None else scale)
        self.phase = float(self.rng.normal(0.0, 0.7) if phase is None else phase)
        self.attack: str | None = None

    def attack_active(self, hour: float) -> bool:
        if self.attack is None:
            return False
        if self.attack == "night_load":
            return NIGHT_HOURS[0] <= hour % 24.0 < NIGHT_HOURS[1]
        return True

    def window(self, minute: int) -> tuple[dict, np.ndarray]:
        """Measurements and features for absolute simulated ``minute``."""
        hour = (minute / 60.0) % 24.0
        att = self.attack if self.attack_active(hour) else None
        raw = simulate(np.array([hour]), self.scale, self.phase, self.rng, att)
        raw = {k: float(v[0]) for k, v in raw.items()}
        return raw, features({k: np.array([v]) for k, v in raw.items()})[0]
