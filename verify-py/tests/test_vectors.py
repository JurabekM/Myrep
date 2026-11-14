"""verify-py ni spec/test-vectors ga qarshi tekshiradi (faqat standart kutubxona: unittest).

Ishga tushirish (verify-py papkasidan):  python -m unittest discover -s tests -v
"""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
VECTORS = HERE.parent.parent / "spec" / "test-vectors"

from tamga_verify import ed25519, merkle, mldsa65  # noqa: E402
from tamga_verify.jcs import NotCanonical, canonical  # noqa: E402
from tamga_verify.verify import PublicKey, VerifyError, b64url, payload_opens, verify_all, verify_log  # noqa: E402


def load(name):
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


def digest(s):
    return bytes.fromhex(s[7:])


CHAIN = load("chain.json")
CKPT = load("checkpoint.json")
LOG_TEXT = "".join(line + "\n" for line in CHAIN["lines"])
CKPT_TEXT = "".join(line + "\n" for line in CKPT["lines"])
PK = PublicKey.from_json(CKPT["public_key"])


class Jcs(unittest.TestCase):
    def test_valid_and_invalid(self):
        v = load("jcs.json")
        for case in v["valid"]:
            self.assertEqual(canonical(json.loads(case["input"])), case["canonical"], case["input"])
        for case in v["invalid"]:
            with self.assertRaises(NotCanonical, msg=case["input"]):
                canonical(json.loads(case["input"]))


class Chain(unittest.TestCase):
    def test_chain_verifies_and_hashes_match(self):
        rep = verify_log(LOG_TEXT)
        self.assertEqual([h.hex() for h in rep.hashes], [h[7:] for h in CHAIN["hashes"]])
        self.assertEqual(rep.warnings, [])

    def test_payload_commitments(self):
        records = [json.loads(l) for l in CHAIN["lines"]]
        refs = {r["tool"]["input"]["digest"]: r["tool"]["input"] for r in records if "input" in r.get("tool", {})}
        for p in CHAIN["payloads"]:
            ref = refs[p["digest"]]
            self.assertTrue(payload_opens(ref, bytes.fromhex(p["salt"]), p["payload"].encode()))
            self.assertFalse(payload_opens(ref, bytes.fromhex(p["salt"]), p["payload"].encode() + b"x"))


class Merkle(unittest.TestCase):
    def test_roots_and_proofs(self):
        v = load("merkle.json")
        leaves = [digest(h) for h in CHAIN["hashes"]]
        self.assertEqual(merkle.root([]), digest(v["empty_root"]))
        for r in v["roots"]:
            self.assertEqual(merkle.root(leaves[: r["size"]]), digest(r["root"]))
        full = merkle.root(leaves)
        for p in v["inclusion"]:
            proof = [digest(x) for x in p["proof"]]
            self.assertTrue(merkle.verify_inclusion(p["index"], p["size"], leaves[p["index"]], proof, full))
            self.assertFalse(merkle.verify_inclusion(p["index"], p["size"], b"\x00" * 32, proof, full))
        for p in v["consistency"]:
            proof = [digest(x) for x in p["proof"]]
            first = merkle.root(leaves[: p["first"]])
            self.assertTrue(merkle.verify_consistency(p["first"], p["second"], first, full, proof))
            self.assertFalse(merkle.verify_consistency(p["first"], p["second"], b"\x01" * 32, full, proof))


class Signatures(unittest.TestCase):
    def test_checkpoints_verify(self):
        rep = verify_all(LOG_TEXT, CKPT_TEXT, PK)
        self.assertEqual([c["size"] for c in rep.checkpoints], [4, 6])

    def test_signing_message_matches_vector(self):
        from tamga_verify.verify import CKPT_DOMAIN
        from tamga_verify.jcs import without

        first = json.loads(CKPT["lines"][0])
        self.assertEqual((CKPT_DOMAIN + canonical(without(first, "sig")).encode()).hex(), CKPT["signing_message_hex"])

    def test_liboqs_interop(self):
        v = load("interop-liboqs.json")
        pk, sig, msg = b64url(v["public_key"]), b64url(v["signature"]), bytes.fromhex(v["message_hex"])
        self.assertTrue(mldsa65.verify(pk, msg, sig, v["context"].encode()))
        bad = bytearray(sig)
        bad[100] ^= 1
        self.assertFalse(mldsa65.verify(pk, msg, bytes(bad), v["context"].encode()))
        self.assertFalse(mldsa65.verify(pk, msg + b"x", sig, v["context"].encode()))

    def test_ed25519_strictness(self):
        line = json.loads(CKPT["lines"][0])
        msg = bytes.fromhex(CKPT["signing_message_hex"])
        sig = b64url(line["sig"]["ed25519"])
        self.assertTrue(ed25519.verify(PK.ed, msg, sig))
        s = int.from_bytes(sig[32:], "little") + ed25519.L  # S + L: matematik jihatdan teng, kanonik emas
        self.assertFalse(ed25519.verify(PK.ed, msg, sig[:32] + s.to_bytes(32, "little")))
        identity = (1).to_bytes(32, "little")  # kichik tartibli nuqta (neytral element)
        self.assertFalse(ed25519.verify(identity, msg, sig))

    def test_key_id_is_checked(self):
        bad = dict(CKPT["public_key"], key="k:" + "0" * 32)
        with self.assertRaises(ValueError):
            PublicKey.from_json(bad)

    def test_rust_parity_edge_cases(self):
        """M-1: chegaraviy holatlarda Rust bilan bir xil natija (OK/FAIL va kod)."""
        # 1) result.size = true (bool) -> E_FIELD (Rust bilan bir xil), OK emas.
        rec = json.loads(LOG_TEXT.splitlines()[-1])
        rec["result"] = {"digest": "sha256:" + "0" * 64, "size": True}
        from tamga_verify.jcs import canonical as _canon
        line = _canon(rec)
        with self.assertRaises(VerifyError) as cm:
            verify_log(line + "\n")
        self.assertEqual(cm.exception.code, "E_FIELD")

        # 2) checkpoint sig = {} -> E_CKPT_FORMAT (Rust bilan bir xil), E_CKPT_SIG emas.
        cp = json.loads(CKPT["lines"][0])
        cp["sig"] = {}
        with self.assertRaises(VerifyError) as cm:
            verify_all(LOG_TEXT, _canon(cp) + "\n", PK)
        self.assertEqual(cm.exception.code, "E_CKPT_FORMAT")

        # 3) egri chiziqdan tashqari ed25519 kaliti -> ValueError (CLI da exit 2, Rust bilan bir xil).
        off = dict(CKPT["public_key"], ed25519="A" * 43)
        with self.assertRaises(ValueError):
            PublicKey.from_json(off)


class Tamper(unittest.TestCase):
    def test_every_case_reports_the_same_error_as_rust(self):
        for case in load("tamper.json")["cases"]:
            with self.subTest(case["name"]):
                with self.assertRaises(VerifyError) as e:
                    verify_all(case["log"], case["checkpoints"], PK)
                self.assertEqual((e.exception.code, e.exception.index), (case["expect"]["code"], case["expect"]["index"]))

    def test_every_single_byte_change_is_detected_at_its_record(self):
        data = LOG_TEXT.encode("utf-8")
        line_of, idx = [], 0
        for b in data:
            line_of.append(idx)
            if b == 0x0A:
                idx += 1
        checked = 0
        for pos, b in enumerate(data):
            if b >= 0x80:
                continue
            for rep in b"0x ":
                if rep == b:
                    continue
                mutated = bytearray(data)
                mutated[pos] = rep
                with self.assertRaises(VerifyError, msg=f"bayt {pos}") as e:
                    verify_log(mutated.decode("utf-8"))
                self.assertEqual(e.exception.index, line_of[pos], f"bayt {pos}")
                checked += 1
        self.assertGreater(checked, 5000)



class Rotation(unittest.TestCase):
    """spec §7.5: kalit almashtirish — Rust bilan aynan bir xil natija."""

    def test_rotation_cases(self):
        v = load("rotation.json")
        for case in v["cases"]:
            log = "".join(l + "\n" for l in case["log"])
            cps = "".join(l + "\n" for l in case["checkpoints"])
            with self.subTest(case["name"]):
                if case["expect"].get("ok"):
                    rep = verify_all(log, cps, PK)
                    self.assertEqual(rep.keys, case["expect"]["keys"])
                else:
                    with self.assertRaises(VerifyError) as cm:
                        verify_all(log, cps, PK)
                    self.assertEqual({"code": cm.exception.code, "index": cm.exception.index}, case["expect"])

if __name__ == "__main__":
    unittest.main()
