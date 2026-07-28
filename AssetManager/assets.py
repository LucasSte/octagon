from dataclasses import dataclass


@dataclass
class Asset:
    name: str
    ticker: str

available_assets = {
    'APPL': Asset('Apple Inc.', 'APPL'),
    'NVDA': Asset('NVIDIA Corporation', 'NVDA'),
}

def list_available_assets():
    formatted_response = 'Assets available for trading: \n'
    for asset in available_assets.values():
        formatted_response += f'{asset.ticker}: {asset.name}'

    return formatted_response