"""py -m pytest tools/rostor_report  (yoki: py tools/rostor_report/test_rostor_report.py)"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rostor_report as rr  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import mldsa  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

NOW = 1_790_000_000


def device():
    return Ed25519PrivateKey.from_private_bytes(os.urandom(32)), mldsa.MLDSA65PrivateKey.from_seed_bytes(os.urandom(32))


def report(dev, value="+998901234567", *, created=NOW - 3600, rid=None, ttype="phone"):
    ed, ml = dev
    did = rr.device_id(ed.public_key().public_bytes_raw(), ml.public_key().public_bytes_raw())
    c = {"v": 1, "report_id": rid or os.urandom(16).hex(), "created_at": created, "category": "T2",
         "target_type": ttype, "target_value": value, "target_value_hash": rr.target_hash(ttype, value),
         "claimed_org": "Uzcard", "device_id": did}
    return json.dumps(rr.make_report(c, ed, ml))


def contents(raws):
    out = []
    for r in raws:
        ok, err, c = rr.verify(r)
        assert ok, err
        out.append(c)
    return out


class AggregateTest(unittest.TestCase):
    def test_threshold_needs_distinct_devices(self):
        devs = [device() for _ in range(rr.SCORE_THRESHOLD)]
        g = rr.aggregate(contents([report(d) for d in devs]), NOW)
        self.assertEqual(len(g), 1)
        self.assertTrue(g[0]["candidate"])
        self.assertEqual(g[0]["distinct_devices"], rr.SCORE_THRESHOLD)
        g = rr.aggregate(contents([report(d) for d in devs[:-1]]), NOW)
        self.assertFalse(g[0]["candidate"])

    def test_one_device_is_one_vote(self):
        d = device()
        g = rr.aggregate(contents([report(d, created=NOW - 86400 * i - 60) for i in range(20)]), NOW)
        self.assertEqual(g[0]["distinct_devices"], 1)
        self.assertFalse(g[0]["candidate"])

    def test_duplicates_old_and_future_reports_ignored(self):
        d1, d2, d3 = device(), device(), device()
        same = report(d1, rid="aa" * 16)
        g = rr.aggregate(contents([same, same, report(d2, created=NOW - rr.DECAY_WINDOW_SECS - 10),
                                   report(d3, created=NOW + 3600)]), NOW)
        self.assertEqual(g[0]["distinct_devices"], 1)
        self.assertEqual(len(g[0]["report_ids"]), 1)

    def test_rate_limit_per_device_day(self):
        d = device()
        raws = [report(d, value=f"+99890000{i:04d}", created=NOW - 3600) for i in range(rr.RATE_LIMIT_PER_DAY + 5)]
        g = rr.aggregate(contents(raws), NOW)
        self.assertEqual(len(g), rr.RATE_LIMIT_PER_DAY)

    def test_tampered_and_garbage_rejected(self):
        raw = json.loads(report(device()))
        raw["device_id"] = "00" * 16
        self.assertFalse(rr.verify(json.dumps(raw))[0])
        self.assertFalse(rr.verify("not json")[0])
        self.assertFalse(rr.verify(json.dumps({"format": rr.FORMAT}))[0])

    def test_kat_vector_still_valid(self):
        kat = json.loads(rr.KAT_PATH.read_text(encoding="utf-8"))
        ok, err, c = rr.verify(kat["report"])
        self.assertTrue(ok, err)
        self.assertEqual(c["device_id"], kat["device_id"])


if __name__ == "__main__":
    unittest.main()
