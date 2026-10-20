from collections.abc import Callable
from dataclasses import dataclass

from octagon.tools.tool_definition import ToolDefinition


@dataclass
class Asset:
    name: str
    ticker: str


available_assets = {
    "AAPL": Asset("Apple Inc.", "AAPL"),
    "NVDA": Asset("NVIDIA Corporation", "NVDA"),
    "TSLA": Asset("Tesla, Inc.", "TSLA"),
    "BA": Asset("The Boeing Company", "BA"),
    "MSFT": Asset("Microsoft Coporation", "MSFT"),
    "AMD": Asset("Advanced Micro Devices, Inc.", "AMD"),
    "HSBC": Asset("HSBC Holdings plc", "HSBC"),
    "ASML": Asset("ASML Holding N.V.", "ASML"),
    "EMBJ": Asset("Embraer S.A.", "EMBJ"),
    "QCOM": Asset("QUALCOMM Incorporated", "QCOM"),
    "UNH": Asset("UnitedHealth Group Incorporated", "UNH"),
    "AMZN": Asset("Amazon.com, Inc.", "AMZN"),
    "AVGO": Asset("Broadcom Inc.", "AVGO"),
    "MRNA": Asset("Moderna, Inc.", "MRNA"),
    "GS": Asset("The Goldman Sachs Group, Inc.", "GS"),
    "AAAU": Asset("Goldman Sachs Physical Gold ETF", "AAAU"),
}


def list_available_assets():
    formatted_response = "Assets available for trading: \n"
    for asset in available_assets.values():
        formatted_response += f"{asset.ticker}: {asset.name}"

    return formatted_response


class AssetsTool(ToolDefinition):
    def __init__(self):
        pass

    def description(self) -> list[dict]:
        return [
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
            }
        ]

    def dispatch_dictionary(self) -> dict[str, Callable]:
        return {"list_available_assets": list_available_assets}
