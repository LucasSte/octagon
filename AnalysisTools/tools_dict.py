"""
Dictionary containing descriptions of functions for use by language models.
These functions are designed to be used as tools by agents to provide financial analysis.
"""
from AnalysisTools.fama_french_factor import fama_french_factor
from AnalysisTools.kalman_fair_value import kalman_fair_value
from AnalysisTools.markov_chain_regime import markov_chain_regime
from AnalysisTools.particle_filter import particle_filter_forecast
from AnalysisTools.stocktwits import stocktwits_sentiments
from AnalysisTools.utils import wait

TOOLS_DICT = [
    {
        "type": "function",
        "function": {
            "name": "fama_french_factor",
            "description": "Calculates and returns the market risk (MKT), size (SMB), value (HML) for the three factor"
                           " model. In addition to those, the function returns the profitability (RMW) and the "
                           "investment (CMA) for the five factor model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Pass '3factor' to use the three factor model, or '5factor' to use the five "
                                       "factor model."
                    },
                    "frequency": {
                        "type": "string",
                        "description": "Pass 'daily' to calculate the factors with daily data or 'monthly' for a "
                                       "monthly cadence."
                    },
                },
                "required": ["ticker", "model", "frequency"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted table with the calculated factors."
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kalman_fair_value",
            "description": "Use a Kalman filter to estimate the fair price of a stock, and potentially identify if it "
                           "is over or undervalued. It may also serve to estimate hedge ratios or spreads in "
                           "pairs/statistical-arbitrage trading.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "period": {
                        "type": "string",
                        "description": "The amount of days on which to fit a Kalaman filter parameters. The allowed "
                                       "values are 5d, 6d, 7d, 8d, 9d or 10d."
                    },
                    "interval": {
                        "type": "string",
                        "description": "The interval used to calculate the fair value. Allowed values are 1d for one day, "
                                       "60m, 30m, and 15m for 60, 30, and 15 minutes."
                    },
                    "method": {
                        "type": "string",
                        "description": "Use 'level' for a local level model, or 'linear' for a local linear trend model.",
                    },
                },
                "required": ["ticker", "period", "interval", "method"],
            },
            "returns": {
                "type": "string",
                "description": "The kalman fair value for the last 15 entries beginning from the last captured price."
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "markov_chain_regime",
            "description": "Use a hidden markov model to identify distinct regimes in the asset. It allows one to tell"
                           " whether the market is bullish or bearish for an asset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "states": {
                        "type": "number",
                        "description": "The number of regimes to identify. It can be either two (bear/high-vol and "
                                       "bull/low-vol) or three (bear, choppy, and bull). Use numbers 2 or 3 in this "
                                       "parameter."
                    },
                },
                "required": ["ticker", "states"]
            },
            "returns": {
                "type": "string",
                "description": "A formatted table containing the datetime, price, regime label, raw signal,"
                               " filtered position, unfiltered cumulative return, and filtered cumulative return."
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "particle_filter_forecast",
            "description": "Use a particle filter model to estimate price movements in a give asset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "granularity": {
                        "type": "string",
                        "description": "The granularity of time for which to estimate. Use '1d' to estimate for future "
                                       "days, '1h' for upcoming hours, and '1m' for upcoming minutes."
                    },
                },
                "required": ["ticker", "granularity"]
            },
            "returns": {
                "type": "string",
                "description": "A formatted table containing the future datetime, the forecasted median without drift, "
                               "the forecasted median with drift (assuming the detected trends continue), the "
                               " 5% and 95% confidence interval, and the expected volatility."
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stocktwits_sentiments",
            "description": "Analyse the sentiment (bullish or bearish) of messages on stocktwits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, NVDA)"
                    }
                },
                "required": ["ticker"]
            },
            "returns": {
                "type": "string",
                "description": "The number and percentage of messages labeled as bullish, bearish and unlabeled "
                               "messages."
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Wait a number of second to monitor the market later.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "The number of seconds to wait."
                    }
                },
                "required": ["seconds"]
            },
            "returns": {
                "type": "string",
                "description": "A message confirming the waited time."
            }
        }
    },
]

DISPATCH_DICT = {
    'fama_french_factor': fama_french_factor,
    'kalman_fair_value': kalman_fair_value,
    'markov_chain_regime': markov_chain_regime,
    'particle_filter_forecast': particle_filter_forecast,
    'stocktwits_sentiments': stocktwits_sentiments,
    'wait': wait,
}