from dataclasses import dataclass


@dataclass
class Asset:
    name: str
    ticker: str

available_assets = {
    'APPL': Asset('Apple Inc.', 'APPL'),
    'NVDA': Asset('NVIDIA Corporation', 'NVDA'),
}