import json
from collections.abc import Callable
from dataclasses import dataclass

from octagon.dashboard.log_type import LogType
from octagon.tools.assets.available_assets import available_assets
from octagon.tools.market_data import yahoo
from octagon.tools.tool_definition import ToolDefinition


@dataclass
class Purchase:
    price: float
    amount: float


@dataclass
class Possession:
    quantity: float
    purchase_value: float
    purchase_history: list[Purchase]


class Portfolio(ToolDefinition):
    def __init__(self, balance: float, portfolio_map: dict[str, Possession]):
        self.balance = balance
        self.portfolio_map = portfolio_map
        self.interface_callback: Callable | None = None
        self.session_history = []

    def get_balance(self):
        return f"Your uninvested balance is ${self.balance:.2f}"

    # Spot trade
    def buy_item(self, ticker, amount):
        price = yahoo.real_time_price(ticker)
        total = amount * price
        if total > self.balance:
            return "Insufficient Balance"

        self.balance -= total

        if ticker in self.portfolio_map:
            self.portfolio_map[ticker].quantity += amount
            self.portfolio_map[ticker].purchase_value += total
            self.portfolio_map[ticker].purchase_history.append(
                Purchase(price=price, amount=amount)
            )
        else:
            self.portfolio_map[ticker] = Possession(
                quantity=amount,
                purchase_value=total,
                purchase_history=[Purchase(price=price, amount=amount)],
            )

        self.update_interface()

        if len(self.session_history) > 10:
            self.session_history.pop(0)
        self.session_history.append(f"Buy {amount} units of {ticker}")

        return f"Bought {amount} units of {ticker} at ${total:.2f}. Your new uninvested balance is ${self.balance:.2f}."

    # Spot trade
    def sell_item(self, ticker, amount):
        if ticker not in self.portfolio_map:
            return f"{ticker} not in portfolio"

        possession = self.portfolio_map[ticker]

        message = ""
        if possession.quantity < amount:
            amount = possession.quantity
            message += (
                f"Selling all {possession.quantity:.2f} of {ticker}, since the request amount of {amount} "
                f"is greater than the current holdings. "
            )

        self.portfolio_map[ticker].quantity -= amount

        if self.portfolio_map[ticker].quantity <= 0:
            del self.portfolio_map[ticker]
        else:
            working_amount = amount
            ticker_history = self.portfolio_map[ticker].purchase_history
            ticker_purchase_value = self.portfolio_map[ticker].purchase_value

            while working_amount > 0.0:
                if ticker_history[0].amount <= working_amount:
                    working_amount -= ticker_history[0].amount
                    ticker_purchase_value -= (
                        ticker_history[0].amount * ticker_history[0].price
                    )
                    ticker_history.pop(0)
                else:
                    ticker_purchase_value -= working_amount * ticker_history[0].price
                    ticker_history[0].amount -= working_amount
                    working_amount = 0.0

            self.portfolio_map[ticker].purchase_value = ticker_purchase_value
            self.portfolio_map[ticker].purchase_history = ticker_history

        price = yahoo.real_time_price(ticker)
        total = amount * price
        self.balance += total

        self.update_interface()
        message += f"Sold {amount} units of {ticker} at ${total:.2f}. You new uninvested balance is ${self.balance:.2f}."

        if len(self.session_history) > 10:
            self.session_history.pop(0)
        self.session_history.append(f"Sell {amount} units of {ticker}")

        return message

    def get_formatted_portfolio(self):
        final_string = f"Uninvested balance: ${self.balance:.2f} \n\n"

        portfolio_value = self.balance

        if len(self.portfolio_map) > 0:
            final_string += "Assets: \n"
            for ticker, possession in self.portfolio_map.items():
                price = yahoo.real_time_price(ticker)
                total = possession.quantity * price
                profit_or_loss = total - possession.purchase_value
                profit_or_loss_percent = (
                    profit_or_loss / possession.purchase_value
                ) * 100
                final_string += f"{ticker} ({available_assets[ticker].name}): {possession.quantity:.2f} <=> ${total:.2f} <=> ${profit_or_loss:.2f} ({profit_or_loss_percent:.2f}%) <=> ${price:.2f} \n"
                portfolio_value += total

            final_string += "\nLegend for assets: \nTICKER (name): quantity <=> market value <=> profit or loss <=> current ticker quote"
            final_string += f"\nTotal portfolio value: ${portfolio_value:.2f}"
        else:
            final_string += "No assets in portfolio"

        return final_string

    def print_portfolio(self, callback: Callable[[LogType, str], None]):
        formatted_portfolio = "PORTFOLIO: \n" + self.get_formatted_portfolio() + "\n"
        callback(LogType.INFO, formatted_portfolio)

    def set_interface_callback(self, callback: Callable):
        self.interface_callback = callback

    def update_interface(self):
        if self.interface_callback is None:
            return

        interface_message = ""
        if len(self.portfolio_map) == 0:
            interface_message = "No assets"
        else:
            for ticker, possession in self.portfolio_map.items():
                interface_message += f"{possession.quantity} X {ticker}\n"

        self.interface_callback(interface_message, self.balance)

    def save(self):
        assets = {}
        for ticker, possession in self.portfolio_map.items():
            purchase_history = [
                {"price": item.price, "amount": item.amount}
                for item in possession.purchase_history
            ]
            assets[ticker] = {
                "quantity": possession.quantity,
                "purchase_price": possession.purchase_value,
                "purchase_history": purchase_history,
            }
        dump_dict = {
            "Uninvested balance": self.balance,
            "Assets": assets,
        }

        with open("portfolio.json", "w") as f:
            json.dump(dump_dict, f)

    def load(self):
        with open("portfolio.json", "r") as f:
            json_data = json.load(f)

        self.balance = json_data["Uninvested balance"]
        json_assets = json_data["Assets"]
        for ticker, possession in json_assets.items():
            json_history = possession["purchase_history"]
            formatted_history = [
                Purchase(price=item["price"], amount=item["amount"])
                for item in json_history
            ]
            self.portfolio_map[ticker] = Possession(
                purchase_value=possession["purchase_price"],
                quantity=possession["quantity"],
                purchase_history=formatted_history,
            )

    def get_session_history(self):
        formatted_response = "Your past ten trades:\n"
        for item in self.session_history:
            formatted_response += f"{item}\n"
        return formatted_response

    def description(self) -> list[dict]:
        return [
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
                    "name": "get_session_history",
                    "description": "List your past ten trades",
                    "returns": {
                        "type": "string",
                        "description": "A list containing your past ten trades.",
                    },
                },
            },
        ]


    def dispatch_dictionary(self):
        dispatch_dict = {
            "get_balance": self.get_balance,
            "buy_item": self.buy_item,
            "sell_item": self.sell_item,
            "get_formatted_portfolio": self.get_formatted_portfolio,
            "get_session_history": self.get_session_history,
        }
        return dispatch_dict
