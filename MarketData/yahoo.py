import yfinance as yf
import mplfinance as mpf
import time
from functools import wraps
from datetime import datetime
import pytz

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

def formatted_price(ticker):
    price = real_time_price(ticker)
    return f'{ticker}: ${price}'

@rate_limit(max_per_second=2)
def get_historical_data(symbol, start, end, interval='1d'):
    """
    Get historical OHLCV data.

    Intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval)

    return df

# Return's today's date in the format YYYY-MM-DD
# Synced to New York time zone (stock exchange)
def today_date():
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    return now_ny.strftime('%Y-%m-%d %H:%M')

def validate_date(date_string):
    try:
        # Parse the date string
        date_obj = datetime.strptime(date_string, '%Y-%m-%d')

        # Check if date is not in the future
        today = datetime.now().date()
        if date_obj >= today:
            return 'Date in the future'

        return ''
    except ValueError:
        return 'InvalidDate'

allowed_intervals = {'1m', '2m', '5m', '30m', '60m', '90m', '1d', '5d', '1wk', '1mo', '3mo'}
# Returns everything as a markdown table
# Dates in YYYY-MM-DD. The end date cannot be the same as the start one, even if you want today's information.
# Intervals: 1, 2, 5, 15, 30, 60 or 90 minutes, 1 or 5 days, 1 week, 1mo, 3mo
# Maximum of ten entries
def formatted_historical_data(ticker, start, end, interval):
    if interval not in allowed_intervals:
        return f'Invalid interval: {interval}'
    historical_data = get_historical_data(ticker, start, end, interval)

    if start is not None:
        start_val = validate_date(start)
        if start_val != '':
            return start_val

    if end is not None:
        end_val = validate_date(end)
        if end_val != '':
            return end_val

    if not historical_data.empty:
        # Reset index to make datetime a column
        df_reset = historical_data.reset_index()

        # Create markdown table header
        markdown_table = "| Datetime | Open | High | Low | Close | Volume |\n"
        markdown_table += "|----------|------|------|-----|-------|--------|\n"

        # Add each row of data
        for index, row in df_reset.iterrows():
            datetime_str = row['Date'].strftime('%Y-%m-%d %H:%M:%S')
            markdown_table += f"| {datetime_str} | {row['Open']:.2f} | {row['High']:.2f} | {row['Low']:.2f} | {row['Close']:.2f} | {row['Volume']:,.0f} |\n"

        average_return = df_reset['Close'].pct_change().mean()
        volatility = df_reset['Close'].pct_change().std()
        average = df_reset['Close'].mean()

        markdown_table += '\n\n'

        markdown_table += f'Average return: {average_return:.4f}\n'
        markdown_table += f'Volatility (std): {volatility:.4f}\n'
        markdown_table += f'Average close price: {average: .4f}\n'

        return markdown_table

    return f'No data available for {ticker}'

allowed_plot_type = {'candle', 'line', 'renko', 'pnf'}
# Graph type: candle, line, renko, pnf
# Moving average: numbers in (1, 2, 3)
def formatted_historical_data_as_candle(
        ticker,
        start,
        end,
        interval,
        plot_type,
        moving_average
):
    if interval not in allowed_intervals:
        return f'Invalid interval: {interval}'

    if plot_type not in allowed_plot_type:
        return f'Invalid plot type: {plot_type}'

    if start is not None:
        start_val = validate_date(start)
        if start_val != '':
            return start_val

    if end is not None:
        end_val = validate_date(end)
        if end_val != '':
            return end_val

    historical_data = get_historical_data(ticker, start, end, interval)

    ohlc = historical_data.loc[:, ['Open', 'High', 'Low', 'Close']]
    ohlc['Date'] = historical_data.to_datetime(ohlc.index)
    fig_name = f'{ticker}_{start}_{end}.jpg'
    mpf.plot(ohlc, type='candle', mav=moving_average, savefig=fig_name)

    return fig_name

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

def get_formatted_company_info(ticker):
    c_info = get_company_info(ticker)

    formatted = f'''
    Information for {ticker}:
    
    Name: {c_info['name']}
    Sector: {c_info['sector']}
    Industry: {c_info['industry']}
    Description: {c_info['description']}
    Market capitalization: {c_info['market_cap']}
    Trailing PE ratio: {c_info['pe_ratio']}
    Forward PE ration: {c_info['forward_pe']}
    Dividend Yield: {c_info['dividend_yield']}
    Beta: {c_info['beta']}
    52 week high: {c_info['52_week_high']}
    52 week low: {c_info['52_week_low']}
    '''

    return formatted

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
        header += f' {income.keys()[i].strftime('%Y-%m-%d')} |'
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
    free_cash_flow += '\n'

    full_table = header + revenue_row + income_row + ebitda_row + assets_row + free_cash_flow

    return full_table

# Returns total revenue, gross profit, net income, ebitda, total assets, and free cash flow for the past three years
def get_formatted_financials_for_past_three_years(symbol):
    return build_financials_table(symbol, 'income_statement', 'balance_sheet', 'cash_flow')


# Returns total revenue, gross profit, net income, ebitda, total assets, and free cash flow for the past three quarters
def get_formatted_financials_for_past_three_quarters(symbol):
    return build_financials_table(symbol, 'quarterly_income', 'quarterly_balance', 'quarterly_cash_flow')

