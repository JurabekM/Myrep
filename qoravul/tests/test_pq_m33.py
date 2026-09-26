"""ML-KEM-768 / ML-DSA-65 on an emulated Cortex-M33 vs the Python reference (extension 9.2).

Opt-in (fetches mlkem-native/mldsa-native at pinned commits, needs
arm-none-eabi-gcc + qemu-system-arm): QORAVUL_TEST_PQ_M33=1 pytest tests/test_pq_m33.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("QORAVUL_TEST_PQ_M33") != "1"
    or shutil.which("arm-none-eabi-gcc") is None or shutil.which("qemu-system-arm") is None,
    reason="set QORAVUL_TEST_PQ_M33=1 (needs network, arm-none-eabi-gcc, qemu-system-arm)")


@pytest.fixture(scope="module")
def mcu() -> dict:
    out = subprocess.run(["make", "-s", "-C", str(ROOT / "firmware"), "pq-m33"], capture_output=True, text=True,
                         timeout=900)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    res = {"bench": {}}
    for line in out.stdout.splitlines():
        if line.startswith("bench "):
            _, name, instr, stack = line.split()
            res["bench"][name] = (int(instr.split("=")[1]), int(stack.split("=")[1]))
        elif "=" in line and line.split("=")[0] in ("kem_pk", "kem_ct", "kem_ss", "dsa_pk", "dsa_sig"):
            k, v = line.split("=", 1)
            res[k] = bytes.fromhex(v)
        elif line.startswith("decaps_match="):
            res["decaps_match"] = line.split()[0].endswith("=1")
    return res


def test_mlkem768_kat(mcu):
    from kyber_py.ml_kem import ML_KEM_768

    ek, dk = ML_KEM_768._keygen_internal(bytes(range(32)), bytes(range(32, 64)))
    ss, ct = ML_KEM_768._encaps_internal(ek, bytes(range(0x40, 0x60)))
    assert mcu["kem_pk"] == ek
    assert mcu["kem_ct"] == ct
    assert mcu["kem_ss"] == ss
    assert mcu["decaps_match"]


def test_mldsa65_kat(mcu):
    from dilithium_py.ml_dsa import ML_DSA_65

    pk, sk = ML_DSA_65._keygen_internal(bytes(range(0x80, 0xA0)))
    sig = ML_DSA_65.sign(sk, b"QVL1 evidence test vector", ctx=b"QVL1-EVIDENCE", deterministic=True)
    assert mcu["dsa_pk"] == pk
    assert mcu["dsa_sig"] == sig
    assert ML_DSA_65.verify(pk, b"QVL1 evidence test vector", mcu["dsa_sig"], ctx=b"QVL1-EVIDENCE")


def test_mcu_bench_reported(mcu):
    assert set(mcu["bench"]) == {"mlkem768_keypair", "mlkem768_encaps", "mlkem768_decaps",
                                 "mldsa65_keypair", "mldsa65_sign", "mldsa65_verify"}
    for instr, stack in mcu["bench"].values():
        assert instr > 0 and 0 < stack < 128 * 1024 - 256  # painted region not exhausted
