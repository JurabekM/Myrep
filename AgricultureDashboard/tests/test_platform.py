"""Unit tests for pure-logic components (no database required).

Integration coverage (DB, ML, GIS, AI, reports, backup) runs via:
    python run.py --selfcheck
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.timeseries import (  # noqa: E402
    linear_forecast, moving_average, percent_change, trend_slope,
    zscore_anomalies,
)
from core.cache import TTLCache  # noqa: E402
from core.i18n import translate  # noqa: E402
from core.security import (  # noqa: E402
    RateLimiter, create_token, hash_password, has_permission, verify_password,
    verify_token,
)


class SecurityTests(unittest.TestCase):
    def test_password_hash_roundtrip(self) -> None:
        stored = hash_password("MaxfiyParol#2026")
        self.assertTrue(verify_password("MaxfiyParol#2026", stored))

    def test_password_hash_rejects_wrong(self) -> None:
        stored = hash_password("to'g'ri")
        self.assertFalse(verify_password("noto'g'ri", stored))
        self.assertFalse(verify_password("x", "buzilgan$format"))

    def test_token_roundtrip(self) -> None:
        payload = verify_token(create_token("admin", "admin"))
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "admin")
        self.assertEqual(payload["role"], "admin")

    def test_token_expiry_and_tamper(self) -> None:
        self.assertIsNone(verify_token(create_token("u", "viewer", ttl=-5)))
        token = create_token("u", "viewer")
        body, signature = token.split(".")
        self.assertIsNone(verify_token(body + ".deadbeef"))

    def test_permissions(self) -> None:
        self.assertTrue(has_permission("admin", "manage_users"))
        self.assertFalse(has_permission("viewer", "manage_users"))
        self.assertFalse(has_permission(None, "view_dashboard"))

    def test_rate_limiter_locks(self) -> None:
        limiter = RateLimiter(max_attempts=3, lock_minutes=1)
        for _ in range(3):
            limiter.register_failure("bot")
        self.assertTrue(limiter.is_locked("bot"))
        self.assertFalse(limiter.is_locked("odam"))


class TimeSeriesTests(unittest.TestCase):
    def test_linear_forecast_length_and_trend(self) -> None:
        forecast, lower, upper = linear_forecast([1, 2, 3, 4, 5], periods=3)
        self.assertEqual(len(forecast), 3)
        self.assertGreater(forecast[0], 5)
        self.assertTrue(all(lo <= f <= hi for lo, f, hi
                            in zip(lower, forecast, upper)))

    def test_linear_forecast_degenerate(self) -> None:
        self.assertEqual(linear_forecast([], 2), ([], [], []))
        forecast, _, _ = linear_forecast([7.0], 2)
        self.assertEqual(forecast, [7.0, 7.0])

    def test_zscore_anomalies(self) -> None:
        values = [10, 11, 10, 12, 11, 10, 60]
        self.assertIn(6, zscore_anomalies(values, threshold=2.0))
        self.assertEqual(zscore_anomalies([5, 5, 5, 5]), [])

    def test_moving_average_and_slope(self) -> None:
        self.assertEqual(moving_average([2, 4, 6], window=2), [2.0, 3.0, 5.0])
        self.assertGreater(trend_slope([1, 2, 3, 4]), 0.9)

    def test_percent_change(self) -> None:
        self.assertEqual(percent_change(100, 150), 50.0)
        self.assertEqual(percent_change(0, 10), 0.0)


class CacheTests(unittest.TestCase):
    def test_ttl_cache_set_get_expire(self) -> None:
        cache = TTLCache(ttl=0.1)
        cache.set("k", 42)
        self.assertEqual(cache.get("k"), 42)
        time.sleep(0.15)
        self.assertIsNone(cache.get("k"))

    def test_ttl_cache_bounded(self) -> None:
        cache = TTLCache(ttl=60, max_items=10)
        for i in range(25):
            cache.set(i, i)
        self.assertLessEqual(len(cache), 10)


class I18nTests(unittest.TestCase):
    def test_translate_known_and_fallback(self) -> None:
        self.assertEqual(translate("Xarita", "en"), "Map")
        self.assertEqual(translate("Xarita", "uz"), "Xarita")
        self.assertEqual(translate("Noma'lum satr", "en"), "Noma'lum satr")


class ReportSanitizeTests(unittest.TestCase):
    def test_latin_sanitize(self) -> None:
        from reports.exporter import _latin

        text = _latin("Bugʻdoy — hosildorlik 4.5 t/ga, maydon 100 m²")
        text.encode("latin-1")  # must not raise
        self.assertIn("Bug'doy", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
