from backend.app.infrastructure.limits.sliding_window import SlidingWindowLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_a_key_gets_its_limit_then_waits_for_its_oldest_event_to_leave_the_window() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(clock)

    assert limiter.hit("a", 2, 60) is None
    clock.now = 1020
    assert limiter.hit("a", 2, 60) is None
    clock.now = 1030
    # The event of 1000 leaves the window at 1060
    assert limiter.hit("a", 2, 60) == 30
    clock.now = 1060
    # The refused event was not counted, so a place is free again
    assert limiter.hit("a", 2, 60) is None


def test_each_key_is_counted_apart() -> None:
    limiter = SlidingWindowLimiter(Clock())

    assert limiter.hit("a", 1, 60) is None
    assert limiter.hit("b", 1, 60) is None
    assert limiter.hit("a", 1, 60) == 60
