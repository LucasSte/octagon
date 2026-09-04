"""
Dictionary containing descriptions of functions for use by language models.
These functions are designed to be used as tools by agents for portfolio management.
"""

from octagon.tools.assets.available_assets import list_available_assets

DESCRIPTION_LIST = [
    {
        "type": "function",
        "function": {
            "name": "get_balance",
            "description": "Get the current uninvested balance of the portfolio",
            "returns": {
                "type": "string",
                "description": "Formatted string showing the uninvested balance (e.g., 'Your uninvested balance is $1500.00')",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy_item",
            "description": "Buy a specified amount of an asset",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    },
                    "amount": {
                        "type": "number",
                        "description": "The quantity of the asset to buy (decimals accepted)",
                    },
                },
                "required": ["ticker", "amount"],
            },
            "returns": {
                "type": "string",
                "description": "Confirmation message showing the purchase details and updated balance (e.g., 'Bought 10 units of AAPL at $1500.00. Your new uninvested balance is $500.00.') or error message if insufficient balance",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sell_item",
            "description": "Sell a specified amount of an asset",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)",
                    },
                    "amount": {
                        "type": "number",
                        "description": "The quantity of the asset to sell",
                    },
                },
                "required": ["ticker", "amount"],
            },
            "returns": {
                "type": "string",
                "description": "Confirmation message showing the sale details and updated balance (e.g., 'Sold 5 units of AAPL at $750.00. You new uninvested balance is $2250.00.') or error message",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_formatted_portfolio",
            "description": "Get a formatted display of the current portfolio including assets and balance",
            "returns": {
                "type": "string",
                "description": "Formatted string showing portfolio balance and assets with quantities and market values, including a legend (e.g., 'Balance: $1500.00 \\n\\nAssets: \\nAAPL (Apple Inc.): 10.00 <=> $1500.00\\n...')",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_assets",
            "description": "List assets available to trade",
            "returns": {
                "type": "string",
                "description": "Formatted string listing the assets available to trade",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_session_history",
            "description": "List your past ten trades",
            "returns": {
                "type": "string",
                "description": "A list containing your past ten trades.",
            },
        },
    },
]

DISPATCH_DICT = {"list_available_assets": list_available_assets}
