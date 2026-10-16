from app.services.ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_blocks_at_the_limit_and_reports_the_wait():
    clock = Clock()
    limiter = SlidingWindowLimiter(2, 60, clock)
    assert limiter.check("u") == 0
    clock.now += 10
    assert limiter.check("u") == 0
    assert limiter.check("u") == 50  # the oldest event (at 1000) expires at 1060; it is now 1010


def test_the_window_slides():
    clock = Clock()
    limiter = SlidingWindowLimiter(2, 60, clock)
    limiter.check("u")
    clock.now += 10
    limiter.check("u")
    clock.now = 1060
    assert limiter.check("u") == 0  # the first event has expired
    assert limiter.check("u") == 10  # but the limit is reached again


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(1, 60, Clock())
    assert limiter.check("a") == 0
    assert limiter.check("a") > 0
    assert limiter.check("b") == 0