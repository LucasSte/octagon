from dataclasses import dataclass
from datetime import date, datetime, time

import pandas as pd

from octagon.simulation.clock import MARKET_TZ, RealClock, SimulatedClock, set_clock
from octagon.simulation.market_data import (
    ReplayMarketData,
    YahooMarketData,
    set_market_data,
)

# Yahoo keeps 1-minute bars for about this long; older days use coarser bars.
MINUTE_DATA_DAYS = 29

# Tools that only return today's real-world data, which would leak the future during a replay.
REPLAY_UNAVAILABLE_TOOLS = {
    "summarize_headlines",
    "stocktwits_sentiments",
    "get_formatted_company_info",
    "get_options_chain",
    "get_options_activity_simple_threshold_clusters",
    "get_formatted_analyst_data",
}


@dataclass
class ReplayConfig:
    day: date
    start_time: time = time(9, 30)
    end_time: time = time(16, 0)
    # Market time consumed per model response. None uses the real time the model took.
    turn_seconds: float | None = None
    slippage_bps: float = 0.0
    memory_file: str = "memory_replay.json"
    portfolio_file: str = "portfolio_replay.json"


def session_bounds(config: ReplayConfig) -> tuple[datetime, datetime]:
    start = datetime.combine(config.day, config.start_time, tzinfo=MARKET_TZ)
    end = datetime.combine(config.day, config.end_time, tzinfo=MARKET_TZ)
    return start, end


def enable_replay(config: ReplayConfig) -> tuple[SimulatedClock, ReplayMarketData]:
    """Switch every tool to the simulated clock and point-in-time market data."""
    from octagon.tools.utilities import time_management

    start, end = session_bounds(config)
    clock = SimulatedClock(start, end, config.turn_seconds)
    provider = ReplayMarketData(clock, config.slippage_bps)
    set_clock(clock)
    set_market_data(provider)
    time_management.set_memory_file(config.memory_file)
    # Memories written on or after the simulated day would tell the agent the future.
    time_management.discard_memory_from(
        int(datetime.combine(config.day, time(0, 0), tzinfo=MARKET_TZ).timestamp())
    )
    return clock, provider


def disable_replay():
    """Go back to the wall clock and live Yahoo data."""
    from octagon.tools.utilities import time_management

    set_clock(RealClock())
    set_market_data(YahooMarketData())
    time_management.set_memory_file("memory.json")


def parse_replay_start(text: str) -> tuple[date, time]:
    """Parse 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' (New York time). Raises ValueError."""
    parts = text.split()
    if len(parts) not in (1, 2):
        raise ValueError("Use YYYY-MM-DD or YYYY-MM-DD HH:MM")
    day = date.fromisoformat(parts[0])
    start = time.fromisoformat(parts[1]) if len(parts) == 2 else time(9, 30)
    if not time(9, 30) <= start < time(16, 0):
        raise ValueError("The start time must be between 09:30 and 16:00")
    return day, start


def check_replay_day(day: date, today: date) -> tuple[str | None, str | None]:
    """
    Check that `day` can be simulated. Returns (error, warning); error is None when it can.
    `today` is the real current date.
    """
    if day >= today:
        return "Pick a day in the past.", None
    if day.weekday() >= 5:
        return f"{day} is a weekend.", None
    probe = ReplayMarketData(SimulatedClock(datetime.combine(day, time(9, 30))))
    if not probe.has_session(day):
        return f"The market was closed on {day}, or there is no data for it.", None
    if (today - day).days > MINUTE_DATA_DAYS:
        return None, (
            "1-minute bars are only kept for about 30 days, so this day uses coarser bars "
            "for prices and fills."
        )
    return None, None


def trading_days(first: date, count: int) -> list[date]:
    """Weekdays starting at `first`. Exchange holidays are skipped later, when no data is found."""
    return [d.date() for d in pd.bdate_range(start=first, periods=count)]
