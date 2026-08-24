"""
Dictionary containing descriptions of functions for use by language models.
These functions are designed to be used as tools by agents to provide financial analysis.
"""

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
                }
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
            "name": "markov_chain_regime====WRONG!",
            "description": "Returns historical stock data for a given period in a table",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for data points (1m, 2m, 5m, 15m, 30m, 60m or 90m for minutes, 1d or 5d for days, 1w for week, 1mo, 3mo for months)"
                    }
                },
                "required": ["ticker", "start", "end", "interval"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted table with historical data. Includes datetime, open, high, low, close, and volume with scientific notation for volume. "
                               "Also includes average return, volatility, and average close price. Not available for intraday data."
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "formatted_intraday_data",
            "description": "Returns intraday stock data for a given period in a table",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "period": {
                        "type": "string",
                        "description": "Period starting from now in days. Use 1d, 2d or 3d for 1 day, 2 days or 3 days in the past."
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for data points (1m, 2m, 5m, 15m, 30m, 60m or 90m for minutes)."
                    }
                },
                "required": ["ticker", "period", "interval"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted table with intraday data. Includes datetime, open, high, low, close, and volume with scientific notation for volume. "
                               "Also includes average return, volatility, and average close price."
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_formatted_company_info",
            "description": "Returns company information formatted for LLM",
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
                "description": "Formatted company information including name, sector, industry, market capitalization, PE ratios, dividend yield, beta, and 52-week high/low"
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_formatted_financials_for_past_three_years",
            "description": "Returns financial data for the past three years",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., NVDA)"
                    }
                },
                "required": ["symbol"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted financial data including total revenue, gross profit, net income, EBITDA, total assets, and free cash flow for the past three years"
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_formatted_financials_for_past_three_quarters",
            "description": "Returns financial data for the past three quarters",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    }
                },
                "required": ["symbol"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted financial data including total revenue, gross profit, net income, EBITDA, total assets, and free cash flow for the past three quarters"
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_options_chain",
            "description": "Returns the top 5 calls and top 5 puts per volume for a given stock",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "expiration_date": {
                        "type": "string",
                        "description": "Expiration date (optional). Uses the most recent one if none provided"
                    }
                },
                "required": ["symbol"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted table showing top 5 calls and top 5 puts sorted by volume, including strike price, last price, volume, open interest, and implied volatility"
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_options_activity_simple_threshold_clusters",
            "description": "Returns option chains cluster statistical outliers whose z score is greater than one",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    }
                },
                "required": ["symbol"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted table showing the top 5 option chains with highest activity scores, including expiration date, days to expiration, total volume, total open interest, and activity score"
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_formatted_analyst_data",
            "description": "Returns analyst recommendations, upgrades/downgrades, and price targets",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    }
                },
                "required": ["symbol"]
            },
            "returns": {
                "type": "string",
                "description": "Formatted analyst data including recommendations, five most recent upgrades/downgrades, and price targets (low, mean, high, current)"
            }
        }
    }
]