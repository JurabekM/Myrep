"""ML-DSA-65 ni mustaqil C implementatsiyasi (liboqs, FIPS 204) bilan ikki tomonlama tekshirish.

1. KeyGen: liboqs'ning randombytes manbasi spec vektoridagi ξ urug'ini qaytaradi →
   liboqs yaratgan ochiq kalit Rust (RustCrypto ml-dsa) kaliti bilan bayt-bir-xil bo'lishi shart.
2. Rust → liboqs: checkpoint.json dagi Rust imzolari liboqs'da (kontekst bilan) tasdiqlanadi.
3. liboqs → Rust: liboqs yangi kalit bilan imzolaydi; natija spec/test-vectors/interop-liboqs.json
   ga yoziladi va Rust testi (`tests/interop.rs`) uni tasdiqlaydi.

Talab: liboqs-python 0.16 (liboqs C kutubxonasi o'rnatilgan).
Ishga tushirish:  py -3.14 scripts/interop_liboqs.py
"""

import base64
import ctypes
import json
import sys
from pathlib import Path

import oqs
import oqs.rand

ROOT = Path(__file__).resolve().parent.parent
VECTORS = ROOT / "spec" / "test-vectors"


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def keygen_from_seed(seed: bytes) -> bytes:
    """liboqs randombytes'ini vaqtincha `seed` ga almashtirib, ML-DSA-65 ochiq kalitini yaratadi."""
    lib = oqs.rand.oqs.native()
    callback_t = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
    calls = []

    def fill(buf, n):
        calls.append(n)
        if n != len(seed):
            raise SystemExit(f"kutilmagan randombytes uzunligi: {n}")
        ctypes.memmove(buf, seed, n)

    cb = callback_t(fill)
    lib.OQS_randombytes_custom_algorithm(cb)
    try:
        with oqs.Signature("ML-DSA-65") as s:
            pk = s.generate_keypair()
    finally:
        oqs.rand.randombytes_switch_algorithm("system")
    if calls != [32]:
        raise SystemExit(f"randombytes chaqiruvlari: {calls}")
    return bytes(pk)


def main() -> int:
    cp = json.loads((VECTORS / "checkpoint.json").read_text(encoding="utf-8"))
    ctx = cp["ml_dsa_context"].encode()
    rust_pk = b64d(cp["public_key"]["ml-dsa-65"])
    ok = True

    # 0. Mustaqil Python JCS: spec vektorlari va jurnal qatorlari bayt-bir-xil chiqishi shart.
    jv = json.loads((VECTORS / "jcs.json").read_text(encoding="utf-8"))
    chain = json.loads((VECTORS / "chain.json").read_text(encoding="utf-8"))
    jcs_ok = all(canonical(json.loads(c["input"])) == c["canonical"] for c in jv["valid"])
    jcs_ok &= all(canonical(json.loads(line)) == line for line in chain["lines"])
    ok &= jcs_ok
    print(f"[{'OK' if jcs_ok else 'XATO'}] Python JCS: {len(jv['valid'])} vektor va {len(chain['lines'])} jurnal qatori bayt-bir-xil")

    # 1. KeyGen (FIPS 204 ML-DSA.KeyGen_internal(ξ)).
    seed = bytes.fromhex(cp["ml_dsa_65_seed"])
    oqs_pk = keygen_from_seed(seed)
    same = oqs_pk == rust_pk
    ok &= same
    print(f"[{'OK' if same else 'XATO'}] KeyGen(ξ): liboqs ochiq kaliti Rust bilan bayt-bir-xil ({len(oqs_pk)} bayt)")

    # 2. Rust imzolari → liboqs.
    with oqs.Signature("ML-DSA-65") as v:
        for i, line in enumerate(cp["lines"]):
            obj = json.loads(line)
            body = {k: obj[k] for k in obj if k != "sig"}
            msg = b"TAMGA-CHECKPOINT-v1\x00" + canonical(body).encode()
            if i == 0:
                same_msg = msg.hex() == cp["signing_message_hex"]
                ok &= same_msg
                print(f"[{'OK' if same_msg else 'XATO'}] Python JCS imzolanadigan xabarni bayt-bir-xil qurdi")
            sig = b64d(obj["sig"]["ml-dsa-65"])
            good = v.verify_with_ctx_str(msg, sig, ctx, rust_pk)
            bad = v.verify_with_ctx_str(msg, sig, b"boshqa", rust_pk)
            ok &= good and not bad
            print(f"[{'OK' if good and not bad else 'XATO'}] checkpoint #{i}: Rust imzosi liboqs'da tasdiqlandi, boshqa kontekst rad etildi")

    # 3. liboqs imzosi → Rust (vektor fayli).
    with oqs.Signature("ML-DSA-65") as s:
        pk = s.generate_keypair()
        msg = bytes.fromhex(cp["signing_message_hex"])
        sig = s.sign_with_ctx_str(msg, ctx)
    out = {
        "description": "ML-DSA-65 signature produced by liboqs (independent C implementation) — tamga-core MUST verify it.",
        "source": f"liboqs {oqs.oqs_version()} via liboqs-python {oqs.oqs_python_version()}",
        "context": cp["ml_dsa_context"],
        "message_hex": msg.hex(),
        "public_key": b64e(bytes(pk)),
        "signature": b64e(bytes(sig)),
    }
    path = VECTORS / "interop-liboqs.json"
    if path.exists() and "--refresh" not in sys.argv:
        print(f"[--] {path.name} mavjud — o'zgartirilmadi (--refresh bilan qayta yaratiladi)")
    else:
        path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] {path.name} yozildi")

    print("NATIJA:", "hammasi mos" if ok else "MOS EMAS")
    return 0 if ok else 1


def canonical(v) -> str:
    """TR-JSON (spec §2.1) — Rust'dan mustaqil Python implementatsiyasi."""
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        if abs(v) > 2**53 - 1:
            raise ValueError("oraliqdan tashqari")
        return str(v)
    if isinstance(v, float):
        raise ValueError("butun bo'lmagan son")
    if isinstance(v, str):
        out = ['"']
        esc = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
        for ch in v:
            if ch in esc:
                out.append(esc[ch])
            elif ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
            else:
                out.append(ch)
        out.append('"')
        return "".join(out)
    if isinstance(v, list):
        return "[" + ",".join(canonical(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(canonical(k) + ":" + canonical(v[k]) for k in keys) + "}"
    raise TypeError(type(v))


if __name__ == "__main__":
    sys.exit(main())
