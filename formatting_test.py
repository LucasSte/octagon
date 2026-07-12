from MarketData.yahoo import *

ticker = 'AAPL'

# print('Formatted price')
# print(formatted_price(ticker))
#
# print("Today's date ")
# print(today_date())
#
# print("Historical data")
# print(formatted_historical_data_with_pandas(ticker, '2026-01-01', '2026-07-01', '1mo'))
#
# print(formatted_historical_data_as_plot_figure(ticker, '2026-07-07', '2026-07-08', '1m', 'candle', 30))
#
# print('Company info')
# print(get_formatted_company_info(ticker))
#
# print('Financials for past three years')
# print(get_formatted_financials_for_past_three_years(ticker))
#
# print('Financials for past three quarters')
# print(get_formatted_financials_for_past_three_quarters(ticker))
#
# print('Get Options Chain')
# print(get_options_chain(ticker, '2026-07-20'))
#
# print('Get options activity clusters')
# print(get_options_activity_simple_threshold_clusters(ticker))

# TODO:
# 1. This function below does not have a nice formatting
# 2. Integrate with LLM (use an API call).
print('Analyst Data')
print(get_formatted_analyst_data(ticker))