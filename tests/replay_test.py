import os
import unittest
from datetime import date, datetime, timedelta
from datetime import time as dtime

import pandas as pd

from octagon.agent.trader_agent import TraderAgent
from octagon.simulation import clock as clock_module
from octagon.simulation import market_data as market_data_module
from octagon.simulation.clock import MARKET_TZ, RealClock, SimulatedClock
from octagon.simulation.market_data import (
    MarketClosedError,
    ReplayMarketData,
    YahooMarketData,
    period_start,
)
from octagon.simulation.replay import (
    REPLAY_UNAVAILABLE_TOOLS,
    ReplayConfig,
    check_replay_day,
    enable_replay,
    parse_replay_start,
    trading_days,
)
from octagon.tools.assets.portfolio import Portfolio, Possession, Purchase
from octagon.tools.market_data import yahoo
from octagon.tools.utilities import time_management

DAY = date(2026, 11, 3)  # a Tuesday


def price_at(ts: pd.Timestamp) -> float:
    """Deterministic, ever-increasing price, so any look-ahead shows up as a too-high value."""
    return (
        100 + (ts - pd.Timestamp("2026-01-01", tz=MARKET_TZ)).total_seconds() / 60_000
    )


def fake_fetch(ticker, interval, start, end):
    days = [d for d in pd.bdate_range(start, end - timedelta(days=1))]
    rows, index = [], []
    for d in days:
        day = pd.Timestamp(d.date(), tz=MARKET_TZ)
        open_ts = day + pd.Timedelta(hours=9, minutes=30)
        close_ts = day + pd.Timedelta(hours=16)
        if interval == "1d":
            index.append(day)
            rows.append((price_at(open_ts), price_at(close_ts)))
            continue
        step = pd.Timedelta(minutes={"1m": 1, "5m": 5, "60m": 60, "15m": 15}[interval])
        ts = open_ts
        while ts < close_ts:
            index.append(ts)
            rows.append((price_at(ts), price_at(min(ts + step, close_ts))))
            ts += step
    df = pd.DataFrame(
        {
            "Open": [r[0] for r in rows],
            "High": [max(r) for r in rows],
            "Low": [min(r) for r in rows],
            "Close": [r[1] for r in rows],
            "Volume": [1000] * len(rows),
        },
        index=pd.DatetimeIndex(index, name="Date" if interval == "1d" else "Datetime"),
    )
    return df


def at(hour, minute, second=0, day=DAY):
    return datetime(
        day.year, day.month, day.day, hour, minute, second, tzinfo=MARKET_TZ
    )


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.clock = SimulatedClock(at(10, 0), at(16, 0))
        self.provider = ReplayMarketData(self.clock, slippage_bps=10, fetch=fake_fetch)
        clock_module.set_clock(self.clock)
        market_data_module.set_market_data(self.provider)

    def tearDown(self):
        clock_module.set_clock(RealClock())
        market_data_module.set_market_data(YahooMarketData())
        time_management.set_memory_file("memory.json")
        if os.path.exists("memory_replay_test.json"):
            os.remove("memory_replay_test.json")

    def test_last_price_uses_last_completed_minute(self):
        self.clock.reset(at(10, 0, 30))
        # The 09:59 bar closed at 10:00; the 10:00 bar is still forming.
        self.assertAlmostEqual(
            self.provider.last_price("AAPL"), price_at(pd.Timestamp(at(10, 0)))
        )

    def test_last_price_before_open_is_previous_close(self):
        self.clock.reset(at(8, 0))
        previous_close = pd.Timestamp(at(16, 0, day=DAY - timedelta(days=1)))
        self.assertAlmostEqual(
            self.provider.last_price("AAPL"), price_at(previous_close)
        )

    def test_intraday_history_has_no_future_bars(self):
        self.clock.reset(at(11, 7, 30))
        for interval in ["1m", "5m", "15m", "60m"]:
            df = self.provider.history("AAPL", period="1d", interval=interval)
            self.assertFalse(df.empty, interval)
            minutes = {"1m": 1, "5m": 5, "15m": 15, "60m": 60}[interval]
            last_end = df.index[-1] + pd.Timedelta(minutes=minutes)
            self.assertLessEqual(last_end, pd.Timestamp(self.clock.now()), interval)
            self.assertLessEqual(
                df["High"].max(), price_at(pd.Timestamp(self.clock.now()))
            )

    def test_daily_history_rebuilds_todays_partial_bar(self):
        self.clock.reset(at(12, 0))
        df = self.provider.history("AAPL", period="5d", interval="1d")
        self.assertEqual(df.index[-1].date(), DAY)
        self.assertAlmostEqual(df["Close"].iloc[-1], price_at(pd.Timestamp(at(12, 0))))
        self.assertEqual(len(df), 5)

    def test_daily_history_with_end_date_in_past(self):
        self.clock.reset(at(12, 0))
        df = self.provider.history("AAPL", start="2026-10-26", end="2026-10-31")
        self.assertEqual(df.index[-1].date(), date(2026, 10, 30))

    def test_execution_price_is_next_minute_open_plus_slippage(self):
        self.clock.reset(at(10, 0, 30))
        expected = price_at(pd.Timestamp(at(10, 1))) * 1.001
        self.assertAlmostEqual(self.provider.execution_price("AAPL", "buy"), expected)

    def test_no_orders_when_market_closed(self):
        self.clock.reset(at(16, 30))
        with self.assertRaises(MarketClosedError):
            self.provider.execution_price("AAPL", "buy")
        self.clock.reset(at(10, 0, day=date(2026, 11, 7)))  # Saturday
        with self.assertRaises(MarketClosedError):
            self.provider.execution_price("AAPL", "sell")

    def test_failed_sell_keeps_holdings(self):
        self.clock.reset(at(17, 0))
        portfolio = Portfolio(
            0.0, {"AAPL": Possession(2, 200.0, [Purchase(price=100.0, amount=2)])}
        )
        with self.assertRaises(MarketClosedError):
            portfolio.sell_item("AAPL", 1)
        self.assertEqual(portfolio.portfolio_map["AAPL"].quantity, 2)
        self.assertEqual(portfolio.balance, 0.0)

    def test_tools_use_simulated_time(self):
        self.clock.reset(at(13, 44))
        self.assertIn("2026-11-03 13:44", yahoo.today_date_time())
        self.assertEqual(yahoo.validate_date("2026-11-04"), "Date in the future")
        table = yahoo.formatted_intraday_data("AAPL", "1d", "15m")
        self.assertIn("2026-11-03 13:15:00", table)
        self.assertNotIn("2026-11-03 13:30:00", table)

    def test_wait_advances_clock_and_reports_close(self):
        self.clock.reset(at(15, 50), at(16, 0))
        self.assertEqual(time_management.wait(300), "Waited 300")
        self.assertEqual(self.clock.now(), at(15, 55))
        self.assertIn("market is now closed", time_management.wait(600))
        self.assertTrue(self.clock.session_over())

    def test_turn_cost(self):
        self.clock.reset(at(10, 0))
        self.clock.on_agent_turn(12.5)
        self.assertEqual(self.clock.now(), at(10, 0, 12) + timedelta(milliseconds=500))
        fixed = SimulatedClock(at(10, 0), turn_seconds=60)
        fixed.on_agent_turn(3)
        self.assertEqual(fixed.now(), at(10, 1))

    def test_period_start(self):
        now = at(11, 0)  # Tuesday
        self.assertEqual(period_start(now, "1d").date(), DAY)
        self.assertEqual(period_start(now, "3d").date(), date(2026, 10, 30))
        saturday = at(11, 0, day=date(2026, 11, 7))
        self.assertEqual(period_start(saturday, "1d").date(), date(2026, 11, 6))
        self.assertEqual(period_start(now, "1y").date(), date(2025, 11, 3))

    def make_agent(self, replay=None):
        return TraderAgent(1, "prompt", "http://localhost:1", "model", True, replay)

    def sim_config(self, day, **kwargs):
        return ReplayConfig(day=day, memory_file="memory_replay_test.json", **kwargs)

    def test_replay_agent_hides_live_only_tools(self):
        agent = self.make_agent(self.sim_config(DAY))
        offered = {tool["function"]["name"] for tool in agent.available_tools}
        self.assertFalse(offered & REPLAY_UNAVAILABLE_TOOLS)
        self.assertEqual(agent.dispatcher.excluded_tools, REPLAY_UNAVAILABLE_TOOLS)
        self.assertIn("buy_item", offered)

        agent.set_replay(None)
        offered = {tool["function"]["name"] for tool in agent.available_tools}
        self.assertTrue(REPLAY_UNAVAILABLE_TOOLS <= offered)
        self.assertIsInstance(clock_module.get_clock(), RealClock)
        self.assertIsInstance(market_data_module.get_market_data(), YahooMarketData)
        self.assertEqual(time_management.MEMORY_FILE, "memory.json")

    def test_switching_modes_keeps_portfolios_apart(self):
        agent = self.make_agent()
        agent.portfolio.balance = 1234.0
        agent.portfolio.portfolio_map["AAPL"] = Possession(
            1, 100.0, [Purchase(100.0, 1)]
        )

        agent.set_replay(self.sim_config(DAY))
        self.assertEqual(agent.portfolio.balance, 10000)
        self.assertEqual(agent.portfolio.portfolio_map, {})
        self.assertEqual(agent.portfolio.file_path, "portfolio_replay.json")
        self.assertEqual(clock_module.get_clock().now(), at(9, 30))
        agent.portfolio.balance = 9000.0

        # Moving forward in time keeps the simulated portfolio...
        message = agent.set_replay(self.sim_config(DAY + timedelta(days=1)))
        self.assertIn("Kept", message)
        self.assertEqual(agent.portfolio.balance, 9000.0)

        # ...going back to live restores the live one...
        agent.set_replay(None)
        self.assertEqual(agent.portfolio.balance, 1234.0)
        self.assertIn("AAPL", agent.portfolio.portfolio_map)
        self.assertEqual(agent.portfolio.file_path, "portfolio.json")

        # ...and going back in time starts over, since later holdings would leak the future.
        message = agent.set_replay(self.sim_config(DAY))
        self.assertIn("new simulated portfolio", message)
        self.assertEqual(agent.portfolio.balance, 10000)

    def test_memory_from_later_days_is_discarded(self):
        time_management.set_memory_file("memory_replay_test.json")
        self.clock.reset(at(15, 0))
        time_management.write_memory("tuesday")
        self.clock.reset(at(15, 0, day=DAY + timedelta(days=1)))
        time_management.write_memory("wednesday")

        enable_replay(self.sim_config(DAY + timedelta(days=1)))
        entries = [item["entry"] for item in time_management.read_memory_raw()]
        self.assertEqual(entries, ["tuesday"])

    def test_parse_replay_start(self):
        self.assertEqual(
            parse_replay_start("2026-11-20"), (date(2026, 11, 20), dtime(9, 30))
        )
        self.assertEqual(
            parse_replay_start("2026-11-20 13:15"), (date(2026, 11, 20), dtime(13, 15))
        )
        for bad in [
            "2026-11-31",
            "yesterday",
            "2026-11-20 17:00",
            "2026-11-20 10:00 x",
        ]:
            with self.assertRaises(ValueError):
                parse_replay_start(bad)

    def test_check_replay_day_rejects_future_and_weekends(self):
        today = date(2026, 11, 26)
        self.assertIsNotNone(check_replay_day(today, today)[0])
        self.assertIsNotNone(check_replay_day(date(2026, 11, 21), today)[0])

    def test_enable_replay_sets_globals(self):
        clock, provider = enable_replay(
            ReplayConfig(day=DAY, memory_file="memory_replay_test.json")
        )
        self.assertIs(clock_module.get_clock(), clock)
        self.assertIs(market_data_module.get_market_data(), provider)
        self.assertEqual(clock.now(), at(9, 30))
        time_management.write_memory("note")
        self.assertTrue(os.path.exists("memory_replay_test.json"))
        self.assertEqual(
            time_management.read_memory_raw()[0]["datetime"], int(at(9, 30).timestamp())
        )

    def test_minute_requests_are_split_into_short_ranges(self):
        def strict_fetch(ticker, interval, start, end):
            if interval == "1m" and (end - start).days > 8:
                raise ValueError("Only 8 days worth of 1m data per request")
            return fake_fetch(ticker, interval, start, end)

        provider = ReplayMarketData(self.clock, fetch=strict_fetch)
        self.clock.reset(at(11, 0))
        df = provider.history("AAPL", period="7d", interval="1m")
        self.assertEqual(len(set(df.index.date)), 7)
        self.assertLessEqual(df.index[-1], pd.Timestamp(at(10, 59)))

    def test_trading_days_skips_weekends(self):
        days = trading_days(date(2026, 11, 6), 3)
        self.assertEqual(
            days, [date(2026, 11, 6), date(2026, 11, 9), date(2026, 11, 10)]
        )


if __name__ == "__main__":
    unittest.main()
