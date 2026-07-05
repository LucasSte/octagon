import yfinance as yf
import mplfinance as mpf
import pandas as pd
import time
from functools import wraps

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
def real_time_price():
    print('Real time price')
    # Get stock info
    apple = yf.Ticker("AAPL")
    print(apple.info['longName'])
    print(apple.info['currentPrice'])  # 178.50

real_time_price()

print('History of prices')

@rate_limit(max_per_second=2)
def get_historical_data(symbol, start, end, interval='1d'):
    """
    Get historical OHLCV data.

    Intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval)

    return df

# Get daily data for the last year
df = get_historical_data('AAPL', '2025-01-01', '2026-01-01')
print(df.tail())

# Calculate simple metrics
df['Daily_Return'] = df['Close'].pct_change()
df['MA_20'] = df['Close'].rolling(window=20).mean()
df['MA_50'] = df['Close'].rolling(window=50).mean()

print(f"Average daily return: {df['Daily_Return'].mean():.4f}")
print(f"Volatility (std): {df['Daily_Return'].std():.4f}")

ohlc = df.loc[:, ['Open', 'High', 'Low', 'Close']]

# Converting date into datetime format
# ohlc['Date'] = pd.to_datetime(ohlc.index)
# ohlc['Date'] = ohlc['Date'].apply(mpl_dates.date2num)
# ohlc = ohlc.astype(float)

# mpf.plot(ohlc, type='candle')

@rate_limit(max_per_second=2)
def get_company_info(symbol):
    """Get comprehensive company information."""
    ticker = yf.Ticker(symbol)
    info = ticker.info

    return {
        'name': info.get('longName'),
        'symbol': info.get('symbol'),
        'sector': info.get('sector'),
        'industry': info.get('industry'),
        'website': info.get('website'),
        'employees': info.get('fullTimeEmployees'),
        'description': info.get('longBusinessSummary'),
        'market_cap': info.get('marketCap'),
        'pe_ratio': info.get('trailingPE'),
        'forward_pe': info.get('forwardPE'),
        'dividend_yield': info.get('dividendYield'),
        'beta': info.get('beta'),
        '52_week_high': info.get('fiftyTwoWeekHigh'),
        '52_week_low': info.get('fiftyTwoWeekLow')
    }

info = get_company_info('MSFT')
print(f"{info['name']} ({info['symbol']})")
print(f"Pe ration: {info['pe_ratio']}")
print(f"Forward PE: ${info['forward_pe']:,.0f}")
print(f'beta: {info['beta']}')
print(f'52 week high: {info['52_week_high']}')
print(f'52 week low: {info['52_week_low']}')

@rate_limit(max_per_second=2)
def get_financials(symbol):
    """Get financial statements."""
    ticker = yf.Ticker(symbol)

    # Add earnings
    return {
        'income_statement': ticker.financials,
        'quarterly_income': ticker.quarterly_financials,
        'balance_sheet': ticker.balance_sheet,
        'quarterly_balance': ticker.quarterly_balance_sheet,
        'cash_flow': ticker.cashflow,
        'quarterly_cash_flow': ticker.quarterly_cashflow
    }

# Get Apple financials
financials = get_financials('AAPL')

# Income Statement
income = financials['income_statement']
print("Annual Income Statement:")
print(income.loc[['Total Revenue', 'Gross Profit', 'Net Income']])

# Balance Sheet
balance = financials['balance_sheet']
print("\nBalance Sheet:")
print(balance.loc[['Total Assets', 'Total Liabilities Net Minority Interest', 'Total Equity Gross Minority Interest']])

@rate_limit(max_per_second=2)
def get_options_chain(symbol, expiration_date=None):
    """Get options chain for a symbol."""
    ticker = yf.Ticker(symbol)

    # Get available expiration dates
    expirations = ticker.options
    print(f"Available expirations: {expirations[:5]}...")

    # Use first expiration if not specified
    exp_date = expiration_date or expirations[0]

    # Get options chain
    opt = ticker.option_chain(exp_date)

    return {
        'expiration': exp_date,
        'calls': opt.calls,
        'puts': opt.puts
    }

# Get options for Apple
options = get_options_chain('AAPL')

print(f"\nOptions expiring {options['expiration']}:")
print(f"Calls: {len(options['calls'])} contracts")
print(f"Puts: {len(options['puts'])} contracts")

# Show top 5 calls by volume
top_calls = options['calls'].nlargest(5, 'volume')[['strike', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']]
print("\nTop 5 calls by volume:")
print(top_calls)

@rate_limit(max_per_second=2)
def get_analyst_data(symbol):
    """Get analyst recommendations and price targets."""
    ticker = yf.Ticker(symbol)

    return {
        'recommendations': ticker.recommendations,
        'upgrades_downgrades': ticker.upgrades_downgrades,
        'analyst_price_targets': ticker.analyst_price_targets
    }

data = get_analyst_data('AAPL')

# Recent recommendations
print("Recent Analyst Actions:")
print(data['recommendations'].tail(10))

# Price targets
targets = data['analyst_price_targets']
print(f"\nPrice Targets:")
print(f"  Low: ${targets['low']}")
print(f"  Mean: ${targets['mean']}")
print(f"  High: ${targets['high']}")
print(f"  Current: ${targets['current']}")

@rate_limit(max_per_second=2)
def get_news(symbol):
    """Get analyst recommendations and price targets."""
    ticker = yf.Ticker(symbol)

    print('Holders')
    print(ticker.news)

get_news('APPL')

