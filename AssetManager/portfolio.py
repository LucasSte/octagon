from dataclasses import dataclass
from MarketData import yahoo


@dataclass
class Possession:
    quantity: float

class Portfolio:
    def __init__(self, balance: float, portfolio_map: dict[str, Possession]):
        self.balance = balance
        self.portfolio_map = portfolio_map

    def get_balance(self):
        return f'Your uninvested balance is ${self.balance}'

    # Spot trade
    def buy_item(self, ticker, amount):
        price = yahoo.real_time_price(ticker)
        total = amount*price
        if total > self.balance:
            return 'Insufficient Balance'

        self.balance -= total

        if ticker in self.portfolio_map:
            self.portfolio_map[ticker].quantity += total
        else:
            self.portfolio_map[ticker] = Possession(quantity=total)

        return f'Bought {amount} of {ticker} at ${total}. Your new uninvested balance is ${self.balance}.'

    # Spot trade
    def sell_item(self, ticker, amount):
        if ticker not in self.portfolio_map:
            return f'{ticker} not in portfolio'

        possession = self.portfolio_map[ticker]

        if possession.quantity < amount:
            return f'Only {possession.quantity} of {ticker} is available to sell'

        self.portfolio_map[ticker].quantity -= amount

        price = yahoo.real_time_price(ticker)
        total = amount*price
        self.balance += total

        return f'Sold {amount} of {ticker} at ${total}. You new uninvested balance is ${self.balance}.'

    def get_formatted_portfolio(self, assets_map):
        final_string = f'Balance: ${self.balance} \n\n'

        final_string += 'Assets: \n'
        for ticker, possession in self.portfolio_map.items():
            final_string += f'{ticker} ({assets_map[ticker].name})\n'


        final_string += 'Legend for assets: \nTICKER (name): quantity'

        return final_string


