from dataclasses import dataclass
from MarketData import yahoo
from AssetManager.assets import available_assets


@dataclass
class Possession:
    quantity: float
    purchase_value: float

class Portfolio:
    def __init__(self, balance: float, portfolio_map: dict[str, Possession]):
        self.balance = balance
        self.portfolio_map = portfolio_map

    def get_balance(self):
        return f'Your uninvested balance is ${self.balance:.2f}'

    # Spot trade
    def buy_item(self, ticker, amount):
        price = yahoo.real_time_price(ticker)
        total = amount*price
        if total > self.balance:
            return 'Insufficient Balance'

        self.balance -= total

        if ticker in self.portfolio_map:
            self.portfolio_map[ticker].quantity += amount
            self.portfolio_map[ticker].purchase_value += total
        else:
            self.portfolio_map[ticker] = Possession(quantity=amount, purchase_value=total)

        return f'Bought {amount} units of {ticker} at ${total:.2f}. Your new uninvested balance is ${self.balance:.2f}.'

    # Spot trade
    def sell_item(self, ticker, amount):
        if ticker not in self.portfolio_map:
            return f'{ticker} not in portfolio'

        possession = self.portfolio_map[ticker]

        if possession.quantity < amount:
            return f'Only {possession.quantity:.2f} units of {ticker} is available to sell'

        self.portfolio_map[ticker].quantity -= amount

        price = yahoo.real_time_price(ticker)
        total = amount*price
        self.balance += total

        return f'Sold {amount} units of {ticker} at ${total:.2f}. You new uninvested balance is ${self.balance:.2f}.'

    def get_formatted_portfolio(self):
        final_string = f'Balance: ${self.balance:.2f} \n\n'

        final_string += 'Assets: \n'
        for ticker, possession in self.portfolio_map.items():
            price = yahoo.real_time_price(ticker)
            total = possession.quantity*price
            profit_or_loss = total - possession.purchase_value
            profit_or_loss_percent = (profit_or_loss / possession.purchase_value) * 100
            final_string += f'{ticker} ({available_assets[ticker].name}): {possession.quantity:.2f} <=> ${total:.2f} <=> ${profit_or_loss:.2f} ({profit_or_loss_percent:.2f}%) \n'


        final_string += '\nLegend for assets: \nTICKER (name): quantity <=> market value <=> profit or loss'

        return final_string

    @staticmethod
    def build_dispatch_dict(instance: Portfolio):
        dispatch_dict = {
            'get_balance': instance.get_balance,
            'buy_item': instance.buy_item,
            'sell_item': instance.sell_item,
            'get_formatted_portfolio': instance.get_formatted_portfolio,
        }
        return dispatch_dict