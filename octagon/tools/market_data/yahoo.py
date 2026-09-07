import mplfinance as mpf
import pytz

from octagon.tools.market_data.yahoo_utils import *

"""
FUNCTIONS TO BE USED AS TOOLS FOR AGENTS.
"""


def formatted_price(ticker):
    """Return ticker current price formatted for LLM"""
    price = real_time_price(ticker)
    return f"{ticker}: ${price:.2f}"


def today_date_time():
    """
    Return's today's date in the format YYYY-MM-DD
    Synced to New York time zone (stock exchange)
    :return: Date
    """
    ny_tz = pytz.timezone("America/New_York")
    now_ny = datetime.now(ny_tz)
    formatted = "Today's date (YYYY-MM-DD HH:MM): "
    return formatted + now_ny.strftime("%Y-%m-%d %H:%M")


def formatted_historical_data(ticker, start, end, interval):
    """
    Dates in YYYY-MM-DD. The end date cannot be the same as the start one, even if you want today's information.
    Intervals: 1, 2, 5, 15, 30, 60 or 90 minutes, 1 or 5 days, 1 week, 1mo, 3mo
    Maximum of ten entries
    """
    if interval not in allowed_intervals:
        return f"Invalid interval: {interval}"
    historical_data = get_historical_data(ticker, start, end, interval)

    if start is not None:
        start_val = validate_date(start)
        if start_val != "":
            return start_val

    if end is not None:
        end_val = validate_date(end)
        if end_val != "":
            return end_val

    if historical_data.empty:
        return f"No data available for {ticker}"

    return format_historical_data_pandas(historical_data)


def formatted_intraday_data(ticker, period, interval):
    """
    Period as days, and interval only in minutes.
    """
    if interval not in allowed_intraday_intervals:
        return f"Invalid interval: {interval}"
    if period not in allowed_intraday_periods:
        return f"Invalid period: {period}"

    historical_data = get_intraday_historical_data(ticker, period, interval)

    if historical_data.empty:
        return f"Not data available for {ticker}"

    return format_historical_data_markdown(historical_data)


def formatted_historical_data_as_plot_figure(
    ticker, start, end, interval, plot_type, moving_average
):
    """
    Returns historical data in a graph plot.
    Graph type: candle, line, renko, pnf
    Moving average: numbers in (1, 2, 3)
    """
    if interval not in allowed_intervals:
        return f"Invalid interval: {interval}"

    if plot_type not in allowed_plot_type:
        return f"Invalid plot type: {plot_type}"

    if start is not None:
        start_val = validate_date(start)
        if start_val != "":
            return start_val

    if end is not None:
        end_val = validate_date(end)
        if end_val != "":
            return end_val

    historical_data = get_historical_data(ticker, start, end, interval)

    ohlc = historical_data.loc[:, ["Open", "High", "Low", "Close"]]
    ohlc["Date"] = pd.to_datetime(ohlc.index)
    fig_name = f"{ticker}_{start}_{end}.jpg"
    if moving_average is not None:
        mpf.plot(ohlc, type="candle", mav=moving_average, savefig=fig_name)
    else:
        mpf.plot(ohlc, type="candle", savefig=fig_name)

    return fig_name


def get_formatted_company_info(ticker):
    """
    Returns company information formatted to an LLM.
    """
    c_info = get_company_info(ticker)

    # Leaving description out
    #     Description: {c_info['description']}
    formatted = f"""
    Information for {ticker}:
    
    Name: {c_info["name"]}
    Sector: {c_info["sector"]}
    Industry: {c_info["industry"]}
    Market capitalization: {c_info["market_cap"]:e}
    Trailing PE ratio: {c_info["pe_ratio"]}
    Forward PE ration: {c_info["forward_pe"]}
    Dividend Yield: {c_info["dividend_yield"]}
    Beta: {c_info["beta"]}
    52 week high: {c_info["52_week_high"]}
    52 week low: {c_info["52_week_low"]}
    """

    return formatted


def get_formatted_financials_for_past_three_years(symbol):
    """
    Returns total revenue, gross profit, net income, ebitda, total assets, and free cash flow for the past three years
    """
    # Try the pandas version too <===
    return build_financials_table(
        symbol, "income_statement", "balance_sheet", "cash_flow"
    )


def get_formatted_financials_for_past_three_quarters(symbol):
    """
    Returns total revenue, gross profit, net income, ebitda, total assets, and free cash flow for the past three quarters
    """
    # Try the pandas version too <===
    return build_financials_table(
        symbol, "quarterly_income", "quarterly_balance", "quarterly_cash_flow"
    )


@rate_limit(max_per_second=2)
def get_options_chain(symbol, expiration_date=None):
    """
    Returns the top 5 calls and top 5 puts per volume
    :param symbol: Ticker
    :param expiration_date: Expiration date (optional). It uses the most recent one if none.
    :return: formatted table
    """
    ticker = yf.Ticker(symbol)

    expirations = ticker.options
    exp_date = expiration_date or expirations[0]

    try:
        opt = ticker.option_chain(exp_date)
    except ValueError as v:
        return str(v)

    names = ["1", "2", "3", "4", "5"]
    top_calls = opt.calls.nlargest(5, "volume")[
        ["strike", "lastPrice", "volume", "openInterest", "impliedVolatility"]
    ]
    top_puts = opt.puts.nlargest(5, "volume")[
        ["strike", "lastPrice", "volume", "openInterest", "impliedVolatility"]
    ]

    top_calls.index = names
    top_puts.index = names

    formatted = f"Top 5 calls by volume with expiration on {exp_date}:\n"
    formatted += top_calls.to_string()
    formatted += f"\n\nTop 5 puts by volume with expiration on {exp_date}:\n"
    formatted += top_puts.to_string()
    return formatted


@rate_limit(max_per_second=2)
def get_options_activity_simple_threshold_clusters(symbol):
    """
    Returns the option chains cluster statistical outliers
    :param symbol:
    :return: Formatted table
    """
    # z-score is a simple threshold — if you want true clustering
    # (grouping nearby expirations by combined date-proximity + activity,
    # not just flagging outliers), you could instead run KMeans from
    # sklearn.cluster on ['days_to_expiration', 'activity_score']
    # (scaled first).
    ticker = yf.Ticker(symbol)
    expirations = ticker.options

    rows = []
    for exp in expirations:
        opt = ticker.option_chain(exp)
        calls, puts = opt.calls, opt.puts

        total_volume = calls["volume"].sum() + puts["volume"].sum()
        total_oi = calls["openInterest"].sum() + puts["openInterest"].sum()
        days_out = (pd.Timestamp(exp) - pd.Timestamp.today()).days

        rows.append(
            {
                "expiration": exp,
                "days_to_expiration": days_out,
                "total_volume": total_volume,
                "total_oi": total_oi,
                "activity_score": total_volume + total_oi,
            }
        )

    z_thresh = 1.0
    activity = pd.DataFrame(rows).sort_values("activity_score", ascending=False)
    activity["z_score"] = (
        activity["activity_score"] - activity["activity_score"].mean()
    ) / activity["activity_score"].std()
    activity.sort_values("activity_score", ascending=False)
    filtered = activity[activity["z_score"] > z_thresh]

    five_best = filtered[:5]
    names = ["1", "2", "3", "4", "5"]
    five_best.index = names[: len(five_best)]

    formatted = "Option chains activity clusters statistical outliers\n\n"
    formatted += five_best.to_string()
    return formatted


@rate_limit(max_per_second=2)
def get_formatted_analyst_data(symbol):
    """
    Return the analyst recommendations, five most recent upgrades and downgrades by firms and
    price targets.
    """
    ticker = yf.Ticker(symbol)

    formatted = "Recommendations (-1m stands for 1 month in the past):\n"
    formatted += ticker.recommendations.to_string()

    formatted += "\n\n"

    formatted += "Five most recent upgrades and downgrades:\n"
    new_index = ticker.upgrades_downgrades.head(5).reset_index()
    new_index.index = ["1", "2", "3", "4", "5"]
    formatted += new_index.to_string()

    formatted += "\n\n"

    targets = ticker.analyst_price_targets
    formatted += "Analyst price targets:\n"
    formatted += f"  Low: ${targets['low']}\n"
    formatted += f"  Mean: ${targets['mean']}\n"
    formatted += f"  High: ${targets['high']}\n"
    formatted += f"  Current: ${targets['current']}\n"

    return formatted
