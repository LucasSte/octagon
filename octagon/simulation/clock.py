"""
Clock abstraction so that every tool reads "now" from a single place.

In live mode the clock is the wall clock. In replay mode it is a simulated clock that only moves
forward when the agent waits or spends time thinking, which lets the agent trade on historical data
as if it were happening in real time.
"""

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MARKET_TZ = ZoneInfo("America/New_York")


class Clock:
    is_simulated = False

    def now(self) -> datetime:
        """Current time, timezone-aware, in the exchange's timezone."""
        raise NotImplementedError

    def sleep(self, seconds: float):
        raise NotImplementedError

    def on_agent_turn(self, wall_seconds: float):
        """Called after each model response with how long the model took to answer."""

    def session_over(self) -> bool:
        """Whether the simulated trading session has ended. Always False for the real clock."""
        return False


class RealClock(Clock):
    def now(self) -> datetime:
        return datetime.now(MARKET_TZ)

    def sleep(self, seconds: float):
        time.sleep(seconds)


class SimulatedClock(Clock):
    is_simulated = True

    def __init__(
        self,
        start: datetime,
        session_end: datetime | None = None,
        turn_seconds: float | None = None,
    ):
        """
        :param start: Simulated time at which the session starts.
        :param session_end: Simulated time at which the session ends (e.g. market close).
        :param turn_seconds: Market time consumed by each model response. If None, the real time the
            model took to answer is used, so slower reasoning costs market time like it would live.
        """
        self.current = _as_market_time(start)
        self.session_end = (
            _as_market_time(session_end) if session_end is not None else None
        )
        self.turn_seconds = turn_seconds

    def now(self) -> datetime:
        return self.current

    def sleep(self, seconds: float):
        self.advance(seconds)

    def advance(self, seconds: float):
        if seconds > 0:
            self.current += timedelta(seconds=seconds)

    def on_agent_turn(self, wall_seconds: float):
        self.advance(
            self.turn_seconds if self.turn_seconds is not None else wall_seconds
        )

    def session_over(self) -> bool:
        return self.session_end is not None and self.current >= self.session_end

    def reset(self, start: datetime, session_end: datetime | None = None):
        self.current = _as_market_time(start)
        self.session_end = (
            _as_market_time(session_end) if session_end is not None else None
        )


def _as_market_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=MARKET_TZ)
    return value.astimezone(MARKET_TZ)


_clock: Clock = RealClock()


def get_clock() -> Clock:
    return _clock


def set_clock(clock: Clock):
    global _clock
    _clock = clock


def now() -> datetime:
    return _clock.now()
