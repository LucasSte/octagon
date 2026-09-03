import time
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

"""
UTILITY FUNCTIONS.
DO NOT INVOKE THESE DIRECTLY!
"""


def rate_limit(max_per_second=2):
    """Decorator to rate limit function calls."""
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
def real_time_price(ticker):
    # Get stock info
    stock = yf.Ticker(ticker)
    return stock.info["currentPrice"]


@rate_limit(max_per_second=2)
def get_historical_data(symbol, start, end, interval="1d"):
    """
    Get historical OHLCV data.

    Intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval)

    return df


@rate_limit(max_per_second=2)
def get_intraday_historical_data(symbol, period, interval="5m"):
    """
    Get historical OHLCV data.

    Intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    return df


allowed_intervals = {
    "1m",
    "2m",
    "5m",
    "30m",
    "60m",
    "90m",
    "1d",
    "5d",
    "1wk",
    "1mo",
    "3mo",
}
allowed_intraday_intervals = {"1m", "2m", "5m", "15m", "30m", "60m", "90m"}
allowed_intraday_periods = {"1d", "2d", "3d"}


def validate_date(date_string):
    try:
        # Parse the date string
        date_obj = datetime.strptime(date_string, "%Y-%m-%d").replace(
            tzinfo=ZoneInfo("America/New_York")
        )

        # Check if date is not in the future
        today = datetime.now(ZoneInfo("America/New_York"))
        if date_obj >= today:
            return "Date in the future"

        return ""
    except ValueError:
        return "InvalidDate"


allowed_plot_type = {"candle", "line", "renko", "pnf"}


@rate_limit(max_per_second=2)
def get_company_info(symbol):
    """Get comprehensive company information."""
    ticker = yf.Ticker(symbol)
    info = ticker.info

    return {
        "name": info.get("longName"),
        "symbol": info.get("symbol"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
        "employees": info.get("fullTimeEmployees"),
        "description": info.get("longBusinessSummary"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
    }


@rate_limit(max_per_second=2)
def get_financials(symbol):
    ticker = yf.Ticker(symbol)

    # Add earnings
    return {
        "income_statement": ticker.financials,
        "quarterly_income": ticker.quarterly_financials,
        "balance_sheet": ticker.balance_sheet,
        "quarterly_balance": ticker.quarterly_balance_sheet,
        "cash_flow": ticker.cashflow,
        "quarterly_cash_flow": ticker.quarterly_cashflow,
    }


def build_financials_table(symbol, income_key, balance_key, cash_flow_key):
    financials = get_financials(symbol)

    income = financials[income_key]
    balance = financials[balance_key]
    cash_flow = financials[cash_flow_key]

    header = "|----------------|"
    revenue_row = "| Total Revenue  |"
    profit_row = "| Gross Profit   |"
    income_row = "| Net Income     |"
    ebitda_row = "| EBITDA         |"
    assets_row = "| Total Assets   |"
    flow_row = "| Free Cash Flow |"

    total_revenue = income.loc["Total Revenue"]
    gross_profit = income.loc["Gross Profit"]
    net_income = income.loc["Net Income"]
    ebitda = income.loc["EBITDA"]
    total_assets = balance.loc["Total Assets"]
    free_cash_flow = cash_flow.loc["Free Cash Flow"]

    for i in range(3):
        header += f" {income.keys()[i].strftime('%Y-%m-%d')}   |"
        revenue_row += f" {total_revenue.iloc[i]:e} |"
        profit_row += f" {gross_profit.iloc[i]:e} |"
        income_row += f" {net_income.iloc[i]:e} |"
        ebitda_row += f" {ebitda.iloc[i]:e} |"
        assets_row += f" {total_assets.iloc[i]:e} |"
        flow_row += f" {free_cash_flow.iloc[i]:e} |"

    header += "\n"
    revenue_row += "\n"
    income_row += "\n"
    ebitda_row += "\n"
    assets_row += "\n"
    flow_row += "\n"

    full_table = header + revenue_row + income_row + ebitda_row + assets_row + flow_row

    return full_table


def build_financials_table_with_pandas(symbol, income_key, balance_key, cash_flow_key):
    financials = get_financials(symbol)

    income = financials[income_key]
    balance = financials[balance_key]
    cash_flow = financials[cash_flow_key]

    total_revenue = income.loc["Total Revenue"]
    gross_profit = income.loc["Gross Profit"]
    net_income = income.loc["Net Income"]
    ebitda = income.loc["EBITDA"]
    total_assets = balance.loc["Total Assets"]
    free_cash_flow = cash_flow.loc["Free Cash Flow"]

    # Use the first 3 period columns as dates
    dates = [income.keys()[i].strftime("%Y-%m-%d") for i in range(3)]

    data = {
        "Total Revenue": [total_revenue.iloc[i] for i in range(3)],
        "Gross Profit": [gross_profit.iloc[i] for i in range(3)],
        "Net Income": [net_income.iloc[i] for i in range(3)],
        "EBITDA": [ebitda.iloc[i] for i in range(3)],
        "Total Assets": [total_assets.iloc[i] for i in range(3)],
        "Free Cash Flow": [free_cash_flow.iloc[i] for i in range(3)],
    }

    df = pd.DataFrame(data, index=dates).T  # rows = metrics, columns = dates

    formatted = df.map(lambda x: f"{x:e}").to_string()
    return formatted


def format_historical_data_markdown(historical_data):
    # Reset index to make datetime a column
    df_reset = historical_data.reset_index()

    # Create markdown table header
    markdown_table = "| Datetime | Open | High | Low | Close | Volume |\n"
    markdown_table += "|----------|------|------|-----|-------|--------|\n"

    # Add each row of data
    for index, row in df_reset.iterrows():
        if "Date" in row:
            datetime_str = row["Date"].strftime("%Y-%m-%d %H:%M:%S")
        else:
            datetime_str = row["Datetime"].strftime("%Y-%m-%d %H:%M:%S")
        markdown_table += f"| {datetime_str} | {row['Open']:.2f} | {row['High']:.2f} | {row['Low']:.2f} | {row['Close']:.2f} | {row['Volume']:,.0f} |\n"

    average_return = df_reset["Close"].pct_change().mean()
    volatility = df_reset["Close"].pct_change().std()
    average = df_reset["Close"].mean()

    markdown_table += "\n\n"

    markdown_table += f"Average return: {average_return:.4f}\n"
    markdown_table += f"Volatility (std): {volatility:.4f}\n"
    markdown_table += f"Average close price: {average: .4f}\n"

    return markdown_table


def format_historical_data_pandas(historical_data):
    # Reset index to make datetime a column
    df_reset = historical_data.reset_index()

    # Build the output dataframe with the columns/formatting we want
    if "Date" in df_reset:
        date_and_time = df_reset["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        date_and_time = df_reset["Datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    result = pd.DataFrame(
        {
            "Datetime": date_and_time,
            "Open": df_reset["Open"].round(2),
            "High": df_reset["High"].round(2),
            "Low": df_reset["Low"].round(2),
            "Close": df_reset["Close"].round(2),
            "Volume": df_reset["Volume"].apply(lambda x: f"{x:e}"),
            "Return (%)": df_reset["Close"].pct_change() * 100,
        }
    )

    result.set_index("Datetime", inplace=True)

    formatted = result.to_string()

    average_return = df_reset["Close"].pct_change().mean()
    volatility = df_reset["Close"].pct_change().std()
    average = df_reset["Close"].mean()

    formatted += "\n\n"

    formatted += f"Average return: {average_return * 100:.4f}%\n"
    formatted += f"Volatility (std): {volatility:.4f}\n"
    formatted += f"Average close price: {average: .4f}\n"

    return formatted
