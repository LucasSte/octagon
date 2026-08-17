# from MarketData.yahoo import *
from AnalysisTools.kalman_fair_value import kalman_fair_value
from AnalysisTools.kalman_predictor import kalman_predictor
from AnalysisTools.markov_chain_regime import markov_chain_regime

ticker = 'NVDA'

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

# print('Analyst Data')
# print(get_formatted_analyst_data(ticker))

# print('Kalman fair value')
# print(kalman_fair_value(ticker, '5d', '60m', 'level'))

# print('Markov chain regime')
# print(markov_chain_regime(ticker, 3))

print('Kalman predictor')
print(kalman_predictor(ticker))