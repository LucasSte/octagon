from dataclasses import dataclass


@dataclass
class Asset:
    name: str
    ticker: str

available_assets = {
    'AAPL': Asset('Apple Inc.', 'AAPL'),
    'NVDA': Asset('NVIDIA Corporation', 'NVDA'),
    'TSLA': Asset('Tesla, Inc.', 'TSLA'),
    'BA': Asset('The Boeing Company', 'BA'),
    'MSFT': Asset('Microsoft Coporation', 'MSFT'),
}

def list_available_assets():
    formatted_response = 'Assets available for trading: \n'
    for asset in available_assets.values():
        formatted_response += f'{asset.ticker}: {asset.name}'

    return formatted_response