import yfinance as yf
import time
from functools import wraps
from datetime import datetime
import pandas as pd

'''
UTILITY FUNCTIONS.
DO NOT INVOKE THESE DIRECTLY!
'''

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
    return stock.info['currentPrice']

@rate_limit(max_per_second=2)
def get_historical_data(symbol, start, end, interval='1d'):
    """
    Get historical OHLCV data.

    Intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval)

    return df

allowed_intervals = {'1m', '2m', '5m', '30m', '60m', '90m', '1d', '5d', '1wk', '1mo', '3mo'}

def validate_date(date_string):
    try:
        # Parse the date string
        date_obj = datetime.strptime(date_string, '%Y-%m-%d')

        # Check if date is not in the future
        today = datetime.now()
        if date_obj >= today:
            return 'Date in the future'

        return ''
    except ValueError:
        return 'InvalidDate'


allowed_plot_type = {'candle', 'line', 'renko', 'pnf'}

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

@rate_limit(max_per_second=2)
def get_financials(symbol):
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

def build_financials_table(symbol, income_key, balance_key, cash_flow_key):
    financials = get_financials(symbol)

    income = financials[income_key]
    balance = financials[balance_key]
    cash_flow = financials[cash_flow_key]

    header = '|----------------|'
    revenue_row = '| Total Revenue  |'
    profit_row = '| Gross Profit   |'
    income_row = '| Net Income     |'
    ebitda_row = '| EBITDA         |'
    assets_row = '| Total Assets   |'
    flow_row = '| Free Cash Flow |'

    total_revenue = income.loc['Total Revenue']
    gross_profit = income.loc['Gross Profit']
    net_income = income.loc['Net Income']
    ebitda = income.loc['EBITDA']
    total_assets = balance.loc['Total Assets']
    free_cash_flow = cash_flow.loc['Free Cash Flow']

    for i in range(0, 3):
        header += f' {income.keys()[i].strftime('%Y-%m-%d')}   |'
        revenue_row += f' {total_revenue.iloc[i]:e} |'
        profit_row += f' {gross_profit.iloc[i]:e} |'
        income_row += f' {net_income.iloc[i]:e} |'
        ebitda_row += f' {ebitda.iloc[i]:e} |'
        assets_row += f' {total_assets.iloc[i]:e} |'
        flow_row += f' {free_cash_flow.iloc[i]:e} |'

    header += '\n'
    revenue_row += '\n'
    income_row += '\n'
    ebitda_row += '\n'
    assets_row += '\n'
    flow_row += '\n'

    full_table = header + revenue_row + income_row + ebitda_row + assets_row + flow_row

    return full_table

def build_financials_table_with_pandas(symbol, income_key, balance_key, cash_flow_key):
    financials = get_financials(symbol)

    income = financials[income_key]
    balance = financials[balance_key]
    cash_flow = financials[cash_flow_key]

    total_revenue = income.loc['Total Revenue']
    gross_profit = income.loc['Gross Profit']
    net_income = income.loc['Net Income']
    ebitda = income.loc['EBITDA']
    total_assets = balance.loc['Total Assets']
    free_cash_flow = cash_flow.loc['Free Cash Flow']

    # Use the first 3 period columns as dates
    dates = [income.keys()[i].strftime('%Y-%m-%d') for i in range(3)]

    data = {
        'Total Revenue': [total_revenue.iloc[i] for i in range(3)],
        'Gross Profit':  [gross_profit.iloc[i] for i in range(3)],
        'Net Income':    [net_income.iloc[i] for i in range(3)],
        'EBITDA':        [ebitda.iloc[i] for i in range(3)],
        'Total Assets':  [total_assets.iloc[i] for i in range(3)],
        'Free Cash Flow':[free_cash_flow.iloc[i] for i in range(3)],
    }

    df = pd.DataFrame(data, index=dates).T  # rows = metrics, columns = dates

    formatted = df.map(lambda x: f'{x:e}').to_string()
    return formatted
