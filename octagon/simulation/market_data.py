"""
Market data providers.

Every tool fetches prices through the active provider instead of calling yfinance directly:

- `YahooMarketData` is the live provider and behaves like the original code.
- `ReplayMarketData` serves historical data as if the simulated clock's time were "now": it never
  returns a bar that had not finished forming at that time, so the agent cannot look ahead.
"""

import re
import time
from datetime import date, datetime, timedelta
from functools import wraps

import pandas as pd
import yfinance as yf

from octagon.simulation.clock import MARKET_TZ, Clock

OHLCV = ["Open", "High", "Low", "Close", "Volume"]

INTRADAY_MINUTES = {
    "1m": 1,
    "2m": 2,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
    "90m": 90,
    "1h": 60,
}

# Finer intervals first. Yahoo keeps 1m bars for ~30 days, 5m for ~60 days and 1h for ~730 days.
SESSION_INTERVALS = ["1m", "5m", "60m"]

MARKET_OPEN = pd.Timedelta(hours=9, minutes=30)
MARKET_CLOSE = pd.Timedelta(hours=16)

# Yahoo refuses 1m requests spanning more than 8 days.
MAX_1M_REQUEST_DAYS = 7

# Rough delay between a reporting period's end and the filing becoming public.
ANNUAL_REPORT_LAG = timedelta(days=90)
QUARTERLY_REPORT_LAG = timedelta(days=45)


def rate_limit(max_per_second=2):
    """Decorator to rate limit function calls (uses real time: it protects Yahoo, not the agent)."""
    min_interval = 1.0 / max_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait_time = min_interval - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result

        return wrapper

    return decorator


@rate_limit(max_per_second=2)
def _yahoo_history(ticker, **kwargs) -> pd.DataFrame:
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    return yf.Ticker(ticker).history(auto_adjust=True, **kwargs)


class MarketData:
    is_live = True

    def last_price(self, ticker: str) -> float:
        """Most recent traded price."""
        raise NotImplementedError

    def execution_price(self, ticker: str, side: str) -> float:
        """Price at which a market order placed now fills. side is 'buy' or 'sell'."""
        raise NotImplementedError

    def history(
        self,
        ticker: str,
        start=None,
        end=None,
        period: str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """OHLCV bars indexed by bar start time, like yfinance's Ticker.history."""
        raise NotImplementedError

    def financial_statements(self, ticker: str) -> dict[str, pd.DataFrame]:
        raise NotImplementedError


class YahooMarketData(MarketData):
    is_live = True

    @rate_limit(max_per_second=2)
    def last_price(self, ticker: str) -> float:
        return yf.Ticker(ticker).fast_info["lastPrice"]

    def execution_price(self, ticker: str, side: str) -> float:
        return self.last_price(ticker)

    def history(self, ticker, start=None, end=None, period=None, interval="1d"):
        if start is None and end is None and period is None:
            period = "1mo"
        return _yahoo_history(
            ticker, start=start, end=end, period=period, interval=interval
        )

    @rate_limit(max_per_second=2)
    def financial_statements(self, ticker):
        t = yf.Ticker(ticker)
        return {
            "income_statement": t.financials,
            "quarterly_income": t.quarterly_financials,
            "balance_sheet": t.balance_sheet,
            "quarterly_balance": t.quarterly_balance_sheet,
            "cash_flow": t.cashflow,
            "quarterly_cash_flow": t.quarterly_cashflow,
        }


class MarketClosedError(Exception):
    pass


class ReplayMarketData(MarketData):
    is_live = False

    def __init__(self, clock: Clock, slippage_bps: float = 0.0, fetch=None):
        """
        :param clock: The simulated clock that defines "now".
        :param slippage_bps: Slippage applied to fills, in basis points (buy higher, sell lower).
        :param fetch: Function (ticker, interval, start_date, end_date) -> DataFrame, with an
            exclusive end date. Defaults to Yahoo. Tests and offline data sources can replace it.
        """
        self.clock = clock
        self.slippage = slippage_bps / 10_000
        self._fetch_fn = fetch or (
            lambda ticker, interval, start, end: _yahoo_history(
                ticker, start=start, end=end, interval=interval
            )
        )
        self._cache: dict[tuple, pd.DataFrame] = {}

    # ---------- raw data ----------

    def _fetch(self, ticker, interval, start: date, end: date) -> pd.DataFrame:
        key = (ticker, interval, start, end)
        if key in self._cache:
            return self._cache[key]

        if interval == "1m" and (end - start).days > MAX_1M_REQUEST_DAYS:
            parts = []
            chunk_start = start
            while chunk_start < end:
                chunk_end = min(chunk_start + timedelta(days=MAX_1M_REQUEST_DAYS), end)
                parts.append(self._fetch(ticker, interval, chunk_start, chunk_end))
                chunk_start = chunk_end
            parts = [part for part in parts if not part.empty]
            self._cache[key] = pd.concat(parts).sort_index() if parts else _empty_bars()
        else:
            try:
                df = self._fetch_fn(ticker, interval, start, end)
            # ruff: noqa: BLE001
            except Exception:
                df = None
            self._cache[key] = _to_market_tz(df)
        return self._cache[key]

    def _session_bars(self, ticker, day: date) -> tuple[pd.DataFrame, str | None]:
        """All intraday bars of one session (including ones in the future), finest interval available."""
        for interval in SESSION_INTERVALS:
            bars = self._fetch(ticker, interval, day, day + timedelta(days=1))
            if not bars.empty:
                return bars, interval
        return _empty_bars(), None

    def _today_daily_bar(self, ticker, day: date) -> pd.DataFrame:
        bars = self._fetch(ticker, "1d", day, day + timedelta(days=1))
        return bars[bars.index.date == day] if not bars.empty else bars

    def has_session(self, day: date, ticker: str = "SPY") -> bool:
        """Whether the exchange traded on `day` (False on weekends and holidays)."""
        return not self._today_daily_bar(ticker, day).empty

    # ---------- point-in-time views ----------

    def history(self, ticker, start=None, end=None, period=None, interval="1d"):
        now = self.clock.now()

        if start is not None:
            start_ts = _parse_ts(start)
        else:
            start_ts = period_start(now, period or "1mo")

        fetch_end = now.date() + timedelta(days=1)
        if end is not None:
            end_ts = _parse_ts(end)
            fetch_end = min(fetch_end, end_ts.date())
        else:
            end_ts = None

        if fetch_end <= start_ts.date():
            return _empty_bars()

        df = self._fetch(ticker, interval, start_ts.date(), fetch_end)
        if not df.empty:
            df = df[df.index >= start_ts]
        df = completed_bars(df, interval, now)

        # Live Yahoo shows today's still-forming daily bar; rebuild it from what has traded so far.
        if (
            interval == "1d"
            and (end_ts is None or end_ts.date() > now.date())
            and start_ts.date() <= now.date()
        ):
            partial = self._partial_daily_bar(ticker, now)
            if partial is not None and (df.empty or df.index[-1] < partial.index[0]):
                df = pd.concat([df, partial]) if not df.empty else partial

        return df

    def _partial_daily_bar(self, ticker, now) -> pd.DataFrame | None:
        bars, interval = self._session_bars(ticker, now.date())
        if interval is None:
            return None
        done = completed_bars(bars, interval, now)
        if done.empty:
            return None
        row = {
            "Open": done["Open"].iloc[0],
            "High": done["High"].max(),
            "Low": done["Low"].min(),
            "Close": done["Close"].iloc[-1],
            "Volume": done["Volume"].sum(),
        }
        index = pd.DatetimeIndex([pd.Timestamp(now.date(), tz=MARKET_TZ)], name="Date")
        return pd.DataFrame([row], index=index)

    def last_price(self, ticker: str) -> float:
        now = self.clock.now()
        bars, interval = self._session_bars(ticker, now.date())
        if interval is not None:
            done = completed_bars(bars, interval, now)
            if not done.empty:
                return float(done["Close"].iloc[-1])
            started = bars[bars.index <= now]
            if not started.empty:
                # The bar's opening print has happened even though the bar is unfinished.
                return float(started["Open"].iloc[-1])
        else:
            # No intraday data that far back: only the open and close of the day are known.
            today = self._today_daily_bar(ticker, now.date())
            minutes = _time_of_day(now)
            if not today.empty and minutes >= MARKET_CLOSE:
                return float(today["Close"].iloc[-1])
            if not today.empty and minutes >= MARKET_OPEN:
                return float(today["Open"].iloc[-1])

        previous = self.history(ticker, period="10d", interval="1d")
        previous = previous[previous.index.date < now.date()]
        if previous.empty:
            raise ValueError(f"No price data for {ticker} at {now:%Y-%m-%d %H:%M}")
        return float(previous["Close"].iloc[-1])

    def market_open(self, ticker: str) -> bool:
        now = self.clock.now()
        bars, interval = self._session_bars(ticker, now.date())
        if interval is not None:
            session_end = bars.index[-1] + pd.Timedelta(
                minutes=INTRADAY_MINUTES[interval]
            )
            return bars.index[0] <= now < session_end
        if self._today_daily_bar(ticker, now.date()).empty:
            return False
        return MARKET_OPEN <= _time_of_day(now) < MARKET_CLOSE

    def execution_price(self, ticker: str, side: str) -> float:
        now = self.clock.now()
        if not self.market_open(ticker):
            raise MarketClosedError(
                f"The market is closed at {now:%Y-%m-%d %H:%M}. Orders can only be filled during "
                "regular trading hours (09:30-16:00 New York time)."
            )

        price = None
        bars, interval = self._session_bars(ticker, now.date())
        if interval == "1m":
            # A market order placed now fills at the open of the next minute bar.
            upcoming = bars[bars.index >= now]
            if not upcoming.empty:
                price = float(upcoming["Open"].iloc[0])
        if price is None:
            price = self.last_price(ticker)

        if side == "buy":
            return price * (1 + self.slippage)
        return price * (1 - self.slippage)

    def financial_statements(self, ticker):
        now = self.clock.now()
        statements = YahooMarketData().financial_statements(ticker)
        lags = {
            "income_statement": ANNUAL_REPORT_LAG,
            "balance_sheet": ANNUAL_REPORT_LAG,
            "cash_flow": ANNUAL_REPORT_LAG,
            "quarterly_income": QUARTERLY_REPORT_LAG,
            "quarterly_balance": QUARTERLY_REPORT_LAG,
            "quarterly_cash_flow": QUARTERLY_REPORT_LAG,
        }
        filtered = {}
        for key, frame in statements.items():
            cutoff = (now - lags[key]).replace(tzinfo=None)
            keep = [c for c in frame.columns if pd.Timestamp(c) <= cutoff]
            filtered[key] = frame[keep]
        return filtered


# ---------- helpers ----------


def _empty_bars() -> pd.DataFrame:
    return pd.DataFrame(
        columns=OHLCV, index=pd.DatetimeIndex([], tz=MARKET_TZ, name="Datetime")
    )


def _to_market_tz(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return _empty_bars()
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize(MARKET_TZ)
    else:
        df.index = df.index.tz_convert(MARKET_TZ)
    return df.sort_index()


def _parse_ts(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize(MARKET_TZ)
    return ts.tz_convert(MARKET_TZ)


def _time_of_day(moment: datetime) -> pd.Timedelta:
    return pd.Timedelta(hours=moment.hour, minutes=moment.minute, seconds=moment.second)


def bar_end_times(index: pd.DatetimeIndex, interval: str) -> pd.DatetimeIndex:
    """When each bar finished forming, i.e. when its close became known."""
    if interval in INTRADAY_MINUTES:
        return index + pd.Timedelta(minutes=INTRADAY_MINUTES[interval])
    if interval == "1d":
        return index.normalize() + MARKET_CLOSE
    # Multi-day bars: treat them as known only once their whole period is over (conservative).
    offsets = {
        "5d": pd.DateOffset(days=7),
        "1wk": pd.DateOffset(days=7),
        "1mo": pd.DateOffset(months=1),
        "3mo": pd.DateOffset(months=3),
    }
    if interval not in offsets:
        raise ValueError(f"Unsupported interval: {interval}")
    return pd.DatetimeIndex([ts.normalize() + offsets[interval] for ts in index])


def completed_bars(df: pd.DataFrame, interval: str, now: datetime) -> pd.DataFrame:
    if df.empty:
        return df
    return df[bar_end_times(df.index, interval) <= pd.Timestamp(now)]


def period_start(now: datetime, period: str) -> pd.Timestamp:
    """Translate a yfinance-style period ('5d', '1y', 'max'...) into a start time relative to now."""
    today = pd.Timestamp(now).tz_convert(MARKET_TZ).normalize()
    if period == "max":
        return pd.Timestamp("1970-01-01", tz=MARKET_TZ)
    if period == "ytd":
        return pd.Timestamp(year=today.year, month=1, day=1, tz=MARKET_TZ)

    match = re.fullmatch(r"(\d+)(d|wk|mo|y)", period)
    if match is None:
        raise ValueError(f"Invalid period: {period}")
    n, unit = int(match.group(1)), match.group(2)

    if unit == "d":
        # Trading days, counting today if it is a weekday: '1d' is today's session.
        last_session = today if today.weekday() < 5 else today - pd.offsets.BDay(1)
        return last_session - pd.offsets.BDay(max(n - 1, 0))
    if unit == "wk":
        return today - pd.DateOffset(weeks=n)
    if unit == "mo":
        return today - pd.DateOffset(months=n)
    return today - pd.DateOffset(years=n)


_provider: MarketData = YahooMarketData()


def get_market_data() -> MarketData:
    return _provider


def set_market_data(provider: MarketData):
    global _provider
    _provider = provider
