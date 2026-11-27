"""
Let the agent trade past days on historical data, as if they were happening in real time.

The agent sees a simulated clock that starts at the market open of each replayed day. Every tool only
returns data that existed at the simulated time, and the clock moves forward when the agent waits or
spends time thinking. Tools that only expose today's real-world data (news, StockTwits, options,
analyst ratings, company info) are not offered during a replay.

Yahoo keeps 1-minute bars for about 30 days, so pick recent days for minute-level fills. Older days
fall back to 5-minute, hourly or daily bars. Prefer days after the model's training cutoff, so the
model cannot simply remember what happened.

Examples:
    python3 octagon_replay.py --date 2026-11-02
    python3 octagon_replay.py --date 2026-11-02 --days 5 --turn-seconds 60 --slippage-bps 2
    python3 octagon_replay.py --date 2026-11-02 --dashboard
"""

import argparse
import os
from dataclasses import replace
from datetime import date, time

from octagon.dashboard.log_type import LogType
from octagon.octagon_agent import OctagonAgent
from octagon.simulation.market_data import get_market_data
from octagon.simulation.replay import ReplayConfig, session_bounds, trading_days
from octagon_trade import INITIAL_PROMPT, MODEL, URL

BENCHMARK = "SPY"

# News is not available while replaying, so don't tell the agent about it.
REPLAY_PROMPT = INITIAL_PROMPT.split("You can fetch curated news")[0]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument(
        "--date", required=True, type=date.fromisoformat, help="First day (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--days", type=int, default=1, help="Number of weekdays to replay"
    )
    parser.add_argument(
        "--start-time",
        type=time.fromisoformat,
        default=time(9, 30),
        help="Simulated start time each day, New York time (default 09:30)",
    )
    parser.add_argument(
        "--turn-seconds",
        type=float,
        default=None,
        help="Market seconds each model response costs (default: the real time the model took)",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=0.0,
        help="Slippage applied to every fill, in basis points",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=200,
        help="Maximum agent iterations per day (the day also ends at the 16:00 close)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep the memory and portfolio files of a previous replay instead of starting fresh",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Run a single day in the terminal dashboard instead of printing logs",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Hide the model's reasoning in the logs"
    )
    return parser.parse_args()


def make_logger(quiet: bool):
    def log(log_type: LogType, message: str):
        if quiet and log_type == LogType.AGENT_REASONING:
            return
        print(f"[{log_type.name}] {message}", flush=True)

    return log


def main():
    args = parse_args()
    tag = args.date.isoformat()
    config = ReplayConfig(
        day=args.date,
        start_time=args.start_time,
        turn_seconds=args.turn_seconds,
        slippage_bps=args.slippage_bps,
        memory_file=f"memory_replay_{tag}.json",
        portfolio_file=f"portfolio_replay_{tag}.json",
    )

    if not args.resume:
        # A memory left by an earlier replay of later days would tell the agent the future.
        for path in (config.memory_file, config.portfolio_file):
            if os.path.exists(path):
                os.remove(path)

    agent = OctagonAgent(args.iterations, REPLAY_PROMPT, URL, MODEL, replay=config)
    portfolio = agent.inner_agent.portfolio
    if args.resume and os.path.exists(config.portfolio_file):
        portfolio.load()

    if args.dashboard:
        if args.days != 1:
            raise SystemExit("--dashboard replays a single day; drop --days.")
        agent.run_with_dashboard()
        return

    log = make_logger(args.quiet)
    agent.set_log_callback(log)
    agent.set_tool_status_callback(
        lambda status: print(
            f"[TOOL {agent.clock.now():%H:%M:%S}] {status}", flush=True
        )
    )

    provider = get_market_data()
    starting_value = None
    benchmark_start = None
    last_day = None

    for day in trading_days(args.date, args.days):
        if not provider.has_session(day):
            print(f"=== {day}: market closed, skipping ===")
            continue

        start, end = session_bounds(replace(config, day=day))
        agent.clock.reset(start, end)
        if starting_value is None:
            starting_value = portfolio.total_value()
            benchmark_start = provider.last_price(BENCHMARK)

        print(
            f"\n=== Replaying {day} from {start:%H:%M} to {end:%H:%M} ===", flush=True
        )
        agent.inner_agent.clear_history()
        agent.run_silent()

        agent.clock.reset(end, end)
        portfolio.save()
        print(
            f"=== {day} close: portfolio value ${portfolio.total_value():,.2f} ===",
            flush=True,
        )
        last_day = day

    if last_day is None:
        print("No trading days in the requested range.")
        return

    final_value = portfolio.total_value()
    benchmark_end = provider.last_price(BENCHMARK)
    agent_return = (final_value / starting_value - 1) * 100
    benchmark_return = (benchmark_end / benchmark_start - 1) * 100

    print("\n=== Replay summary ===")
    print(f"Period: {args.date} to {last_day}")
    print(f"Starting value: ${starting_value:,.2f}")
    print(f"Final value:    ${final_value:,.2f} ({agent_return:+.2f}%)")
    print(f"{BENCHMARK} buy and hold over the same period: {benchmark_return:+.2f}%")
    print(portfolio.get_formatted_portfolio())
    print(
        f"\nPortfolio saved to {config.portfolio_file}, memory in {config.memory_file}"
    )


if __name__ == "__main__":
    main()
