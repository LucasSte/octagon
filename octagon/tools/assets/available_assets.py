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
    'AMD': Asset('Advanced Micro Devices, Inc.', 'AMD'),
    'HSBC': Asset('HSBC Holdings plc', 'HSBC'),
    'ASML': Asset('ASML Holding N.V.', 'ASML'),
    'EMBJ': Asset('Embraer S.A.', 'EMBJ'),
    'QCOM': Asset('QUALCOMM Incorporated', 'QCOM'),
    'UNH': Asset('UnitedHealth Group Incorporated', 'UNH'),
    'AMZN': Asset('Amazon.com, Inc.', 'AMZN'),
    'AVGO': Asset('Broadcom Inc.', 'AVGO'),
    'MRNA': Asset('Moderna, Inc.', 'MRNA'),
    'GS': Asset('The Goldman Sachs Group, Inc.', 'GS'),
}

def list_available_assets():
    formatted_response = 'Assets available for trading: \n'
    for asset in available_assets.values():
        formatted_response += f'{asset.ticker}: {asset.name}'

    return formatted_response