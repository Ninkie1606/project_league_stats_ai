import unittest

from riot.rate_limiter import RateLimiter, parse_limit_header, safe_limit


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept += seconds
        self.now += seconds


def make_limiter():
    clock = FakeClock()
    limiter = RateLimiter(clock=clock, sleep=clock.sleep)
    limiter.set_limits("europe", [(20, 1), (100, 120)])
    return limiter, clock


class RateLimiterTest(unittest.TestCase):
    def test_parse_header(self):
        self.assertEqual(parse_limit_header("20:1,100:120"), [(20, 1), (100, 120)])

    def test_safety_margin(self):
        self.assertEqual(safe_limit(20), 18)
        self.assertEqual(safe_limit(100), 95)

    def test_short_window_blocks(self):
        limiter, clock = make_limiter()
        for _ in range(18):
            limiter.acquire("europe")
        self.assertEqual(clock.slept, 0)
        limiter.acquire("europe")
        self.assertAlmostEqual(clock.slept, 1.0)

    def test_never_exceeds_either_window(self):
        limiter, clock = make_limiter()
        stamps = []
        for _ in range(300):
            limiter.acquire("europe")
            stamps.append(clock.now)
        for i, t in enumerate(stamps):
            in_1s = sum(1 for s in stamps[: i + 1] if s > t - 1)
            in_120s = sum(1 for s in stamps[: i + 1] if s > t - 120)
            self.assertLessEqual(in_1s, 20)
            self.assertLessEqual(in_120s, 100)

    def test_long_window_waits_two_minutes(self):
        limiter, clock = make_limiter()
        for _ in range(95):
            limiter.acquire("europe")
        before = clock.now
        limiter.acquire("europe")
        # The 96th request must wait until the first one leaves the 120 s window.
        self.assertGreaterEqual(clock.now, 120)
        self.assertGreater(clock.now, before)

    def test_buckets_are_independent(self):
        limiter, clock = make_limiter()
        limiter.set_limits("euw1", [(20, 1), (100, 120)])
        for _ in range(18):
            limiter.acquire("europe")
        limiter.acquire("euw1")
        self.assertEqual(clock.slept, 0)

    def test_sync_counts_pads_window(self):
        limiter, clock = make_limiter()
        limiter.acquire("europe")
        limiter.sync_counts("europe", [(18, 1), (18, 120)])
        limiter.acquire("europe")
        self.assertAlmostEqual(clock.slept, 1.0)


if __name__ == "__main__":
    unittest.main()
