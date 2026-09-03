from octagon.tools.market_data.yahoo import *

"""
Dictionary containing descriptions of functions for use by language models.
These functions are designed to be used as tools by agents to provide financial data.
"""

DESCRIPTION_LIST = [
    {
        "type": "function",
        "function": {
            "name": "formatted_price",
            "description": "Return ticker current price of an asset",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    }
                },
                "required": ["ticker"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted string with ticker symbol and current price (e.g., 'AAPL: $150.25')",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "today_date_time",
            "description": "Returns today's date and current time.",
            "returns": {
                "type": "string",
                "description": "Current date and time in New York timezone formatted as 'Today's date (YYYY-MM-DD HH:MM): YYYY-MM-DD HH:MM'",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "formatted_historical_data",
            "description": "Returns historical stock data for a given period in a table",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for data points (1m, 2m, 5m, 15m, 30m, 60m or 90m for minutes, 1d or 5d for days, 1w for week, 1mo, 3mo for months)",
                    },
                },
                "required": ["ticker", "start", "end", "interval"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted table with historical data. Includes datetime, open, high, low, close, and volume with scientific notation for volume. "
                "Also includes average return, volatility, and average close price. Not available for intraday data.",
            },
        },
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
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    },
                    "period": {
                        "type": "string",
                        "description": "Period starting from now in days. Use 1d, 2d or 3d for 1 day, 2 days or 3 days in the past.",
                    },
                    "interval": {
                        "type": "string",
                        "description": "Time interval for data points (1m, 2m, 5m, 15m, 30m, 60m or 90m for minutes).",
                    },
                },
                "required": ["ticker", "period", "interval"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted table with intraday data. Includes datetime, open, high, low, close, and volume with scientific notation for volume. "
                "Also includes average return, volatility, and average close price.",
            },
        },
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
                        "description": "The stock ticker symbol (e.g., AAPL, NVDA)",
                    }
                },
                "required": ["ticker"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted company information including name, sector, industry, market capitalization, PE ratios, dividend yield, beta, and 52-week high/low",
            },
        },
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
                        "description": "The stock ticker symbol (e.g., NVDA)",
                    }
                },
                "required": ["symbol"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted financial data including total revenue, gross profit, net income, EBITDA, total assets, and free cash flow for the past three years",
            },
        },
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
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    }
                },
                "required": ["symbol"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted financial data including total revenue, gross profit, net income, EBITDA, total assets, and free cash flow for the past three quarters",
            },
        },
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
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    },
                    "expiration_date": {
                        "type": "string",
                        "description": "Expiration date (optional). Uses the most recent one if none provided",
                    },
                },
                "required": ["symbol"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted table showing top 5 calls and top 5 puts sorted by volume, including strike price, last price, volume, open interest, and implied volatility",
            },
        },
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
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    }
                },
                "required": ["symbol"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted table showing the top 5 option chains with highest activity scores, including expiration date, days to expiration, total volume, total open interest, and activity score",
            },
        },
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
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    }
                },
                "required": ["symbol"],
            },
            "returns": {
                "type": "string",
                "description": "Formatted analyst data including recommendations, five most recent upgrades/downgrades, and price targets (low, mean, high, current)",
            },
        },
    },
]

DISPATCH_DICT = {
    "formatted_price": formatted_price,
    "today_date_time": today_date_time,
    "formatted_historical_data": formatted_historical_data,
    "formatted_intraday_data": formatted_intraday_data,
    "get_formatted_company_info": get_formatted_company_info,
    "get_formatted_financials_for_past_three_years": get_formatted_financials_for_past_three_years,
    "get_formatted_financials_for_past_three_quarters": get_formatted_financials_for_past_three_quarters,
    "get_options_chain": get_options_chain,
    "get_options_activity_simple_threshold_clusters": get_options_activity_simple_threshold_clusters,
    "get_formatted_analyst_data": get_formatted_analyst_data,
}
