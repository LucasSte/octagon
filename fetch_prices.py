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
print(income.loc[['Total Revenue', 'Gross Profit', 'Net Income', 'EBITDA']])

# Balance Sheet
balance = financials['balance_sheet']
print("\nBalance Sheet:")
print(balance.loc[['Total Assets']])

cash_flow = financials['cash_flow']
print(cash_flow.loc[['Free Cash Flow']])


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

top_puts = options['puts'].nlargest(5, 'volume')[['strike', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']]
print('\nTop 5 puts by volume:')
print(top_puts)

def get_expiration_activity(symbol):
    """Aggregate volume and open interest across all expirations."""
    ticker = yf.Ticker(symbol)
    expirations = ticker.options

    rows = []
    for exp in expirations:
        opt = ticker.option_chain(exp)
        calls, puts = opt.calls, opt.puts

        total_volume = calls['volume'].sum() + puts['volume'].sum()
        total_oi = calls['openInterest'].sum() + puts['openInterest'].sum()
        days_out = (pd.Timestamp(exp) - pd.Timestamp.today()).days

        rows.append({
            'expiration': exp,
            'days_to_expiration': days_out,
            'total_volume': total_volume,
            'total_oi': total_oi,
            'activity_score': total_volume + total_oi
        })

    return pd.DataFrame(rows).sort_values('activity_score', ascending=False)


def find_activity_clusters(df, z_thresh=1.0):
    """Flag expirations whose activity is a statistical outlier (cluster) vs the rest."""
    df = df.copy()
    df['z_score'] = (df['activity_score'] - df['activity_score'].mean()) / df['activity_score'].std()
    df['is_cluster'] = df['z_score'] > z_thresh
    return df.sort_values('activity_score', ascending=False)

activity = get_expiration_activity("AAPL")
clustered = find_activity_clusters(activity)
print(clustered[['expiration', 'days_to_expiration', 'activity_score', 'is_cluster']])

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

# This returns a list of news headers and their website.
# I believe this content is too raw to be fed to an LLM.
# @rate_limit(max_per_second=2)
# def get_news(symbol):
#     """Get analyst recommendations and price targets."""
#     ticker = yf.Ticker(symbol)
#
#     print('Holders')
#     print(ticker.news)
#
# get_news('APPL')
