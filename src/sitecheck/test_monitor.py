import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sitecheck.monitor import _compile_summary, TargetStats
from sitecheck.monitor import check_host


class TestMonitorSummary(unittest.TestCase):
    def setUp(self):
        self.target = {"host": "https://example.com"}
        self.logger = type("L", (), {"info": lambda self, msg: None})()
        self.base = datetime(2026, 1, 1, 12, 0, 0)

    def _build_stats(self, entries):
        stats = TargetStats()
        for ts, success in entries:
            stats.history.append((ts, success))
            stats.total_checks += 1
            if success:
                stats.success_count += 1
        return stats

    def test_single_failure_followed_by_success_is_fluke(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=1), False),
            (self.base + timedelta(minutes=2), True),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)
        self.assertIn("1 fluke", summary)
        self.assertNotIn("Down for", summary)

    def test_two_consecutive_failures_is_downtime(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=1), False),
            (self.base + timedelta(minutes=2), False),
            (self.base + timedelta(minutes=3), True),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)
        self.assertIn("Down for", summary)
        self.assertNotIn("fluke", summary)

    def test_ongoing_failure_not_counted_as_fluke(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=1), False),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)
        self.assertNotIn("fluke", summary)
        self.assertNotIn("Down for", summary)

    def test_single_fluke_and_downtime(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=1), False),
            (self.base + timedelta(minutes=2), True),
            (self.base + timedelta(minutes=3), False),
            (self.base + timedelta(minutes=4), False),
            (self.base + timedelta(minutes=5), True),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)

        self.assertIn("1 fluke", summary)
        self.assertIn("Down for 1m", summary)

    def test_single_fluke_and_downtime_shuffled(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=5), True),
            (self.base + timedelta(minutes=2), True),
            (self.base + timedelta(minutes=1), False),
            (self.base + timedelta(minutes=3), False),
            (self.base + timedelta(minutes=4), False),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)

        self.assertIn("1 fluke", summary)
        self.assertIn("Down for 1m", summary)

    def test_multiple_flukes_and_downtimes(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=5), True),
            (self.base + timedelta(minutes=2), True),
            (self.base + timedelta(minutes=1), False), # Fluke 1
            (self.base + timedelta(minutes=3), False), # Down 1, for 1m
            (self.base + timedelta(minutes=4), False),
            (self.base + timedelta(minutes=6), False), # Fluke 2
            (self.base + timedelta(minutes=7), True),
            (self.base + timedelta(minutes=8), False), # Down 2, for 2m
            (self.base + timedelta(minutes=9), False),
            (self.base + timedelta(minutes=10), False),
            (self.base + timedelta(minutes=11), True),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)

        self.assertIn("2 flukes", summary)
        self.assertIn("Down for 1m", summary)
        self.assertIn(" 2m ", summary)

    def test_summary_icon_for_availability70(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=1), True),
            (self.base + timedelta(minutes=2), False),
            (self.base + timedelta(minutes=3), True),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)
        self.assertTrue(summary.startswith("🔴"))

    def test_summary_icon_for_availability100(self):
        entries = [
            (self.base, True),
            (self.base + timedelta(minutes=1), True),
            (self.base + timedelta(minutes=2), True),
            (self.base + timedelta(minutes=3), True),
        ]
        stats = self._build_stats(entries)
        summary = _compile_summary(self.target, stats, self.logger)
        self.assertTrue(summary.startswith("✅"))


class TestCheckHostRetry(unittest.TestCase):
    def test_retry_success_is_marked_as_recovered(self):
        response = Mock(status_code=200)
        with patch("sitecheck.monitor.requests.get", side_effect=[Exception("temporary"), response]):
            success, status = check_host({"host": "https://example.com", "retry": 1})

        self.assertTrue(success)
        self.assertEqual(status, 200)
        self.assertTrue(status.recovered)

    def test_exhausted_retry_returns_failure(self):
        response = Mock(status_code=503)
        with patch("sitecheck.monitor.requests.get", return_value=response) as request:
            success, status = check_host({"host": "https://example.com", "retry": 1})

        self.assertFalse(success)
        self.assertEqual(status, 503)
        self.assertEqual(request.call_count, 2)

    def test_retry_recovery_is_counted_as_fluke(self):
        stats = TargetStats()
        recovery_time = datetime(2026, 1, 1, 12, 1, 0)
        stats.total_checks = 1
        stats.success_count = 1
        stats.history.extend([(recovery_time, False), (recovery_time, True)])

        summary = _compile_summary(
            {"host": "https://example.com"},
            stats,
            Mock(),
        )

        self.assertIn("1 fluke", summary)


if __name__ == "__main__":
    unittest.main()
