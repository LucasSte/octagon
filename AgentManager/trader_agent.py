from openai import OpenAI
from AssetManager.portfolio import Portfolio
import MarketData.tools_dict
import AssetManager.tools_dict
from typing import Callable

class TraderAgent:
    def __init__(self, rounds: int, initial_prompt: str):
        self.rounds = rounds
        self.initial_prompt = initial_prompt
        self.client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
        self.portfolio = Portfolio(10000, dict())

        available_tools = MarketData.tools_dict.TOOLS_DICT + AssetManager.tools_dict.TOOLS_DICT

        self.tool_status_callback = Callable | None
        self.log_callback = Callable | None

    def set_tool_status_callback(self, callback: Callable):
        self.tool_status_callback = callback

    def set_log_callback(self, callback: Callable):
        self.log_callback = callback

    def set_assets_callback(self, callback: Callable):
        self.portfolio.set_interface_callback(callback)