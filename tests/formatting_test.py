import unittest

from octagon.tools.analysis.fama_french_factor import fama_french_factor
from octagon.tools.analysis.kalman_fair_value import kalman_fair_value
from octagon.tools.analysis.markov_chain_regime import markov_chain_regime
from octagon.tools.analysis.particle_filter import particle_filter_forecast
from octagon.tools.analysis.stocktwits import stocktwits_sentiments
from octagon.tools.market_data.yahoo import *


class TestPortfolio(unittest.TestCase):
    def setUp(self) -> None:
        self.ticker = 'AAPL'

    def test_formatted_price(self):
        print(formatted_price(self.ticker))

    def test_today_date(self):
        print(today_date_time())

    def test_formatted_historical_data(self):
        print(formatted_historical_data(self.ticker, '2026-01-01', '2026-09-03', '1mo'))

    def test_company_info(self):
        print(get_formatted_company_info(self.ticker))

    def test_financials_three_years(self):
        print(get_formatted_financials_for_past_three_years(self.ticker))

    def test_financials_three_quarters(self):
        print(get_formatted_financials_for_past_three_quarters(self.ticker))

    def test_get_options_chain(self):
        print(get_options_chain(self.ticker, '2026-09-20'))

    def test_options_chain(self):
        print(get_options_activity_simple_threshold_clusters(self.ticker))

    def test_analyst_data(self):
        print(get_formatted_analyst_data(self.ticker))

    def test_kalman_fair_value(self):
        print(kalman_fair_value(self.ticker, '5d', '60m', 'level'))

    def test_markov_chain_regime(self):
        print(markov_chain_regime(self.ticker, 3))

    def test_particle_filter(self):
        print(particle_filter_forecast(self.ticker, '1d'))

    def test_fama_french_factor(self):
        print(fama_french_factor(self.ticker, '5factor', 'daily'))

    def test_stocktwits_sentiments(self):
        print(stocktwits_sentiments(self.ticker))