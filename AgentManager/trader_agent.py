from openai import OpenAI
from AgentManager.tool_dispatch import ToolDispatch
from AssetManager.portfolio import Portfolio
import MarketData.tools_dict
import AssetManager.tools_dict
from typing import Callable
from Dashboard.log_type import LogType


class TraderAgent:
    def __init__(self, rounds: int, initial_prompt: str):
        self.rounds = rounds
        self.initial_prompt = initial_prompt
        self.client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
        self.portfolio = Portfolio(10000, dict())

        self.available_tools = MarketData.tools_dict.TOOLS_DICT + AssetManager.tools_dict.TOOLS_DICT
        self.dispatcher = ToolDispatch(self.portfolio)

        self.log_callback = Callable | None

    def set_tool_status_callback(self, callback: Callable):
        # message
        self.dispatcher.set_tool_status_callback(callback)

    def set_log_callback(self, callback: Callable):
        # Log type, message
        self.log_callback = callback
        self.dispatcher.set_log_callback(callback)

    def set_assets_callback(self, callback: Callable):
        # Assets, balance
        self.portfolio.set_interface_callback(callback)

    def agent_loop(self, should_stop):
        content = [
            {
                "type": "text",
                "text": self.initial_prompt,
            }
        ]

        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]

        for i in range(self.rounds):
            if should_stop():
                break

            chat_response = self.client.chat.completions.create(
                model="Ternary-Bonsai-27B-Q2_0.gguf",
                # model="maple-2bit-mlx",
                messages=messages,
                tools=self.available_tools,
                max_tokens=4096,
                temperature=0.7,
                top_p=0.95,
                extra_body={
                    "top_k": 20,
                    # "enable_thinking": False,
                },
            )
            response_message = chat_response.choices[0].message

            if should_stop():
                break

            if self.log_callback is not None:

                if response_message.content is not None and len(response_message.content) > 0:
                    self.log_callback(LogType.AGENT_MESSAGE, response_message.content)


                if hasattr(response_message, 'reasoning_content') and len(response_message.reasoning_content) > 0:
                    self.log_callback(LogType.AGENT_REASONING, response_message.reasoning_content)

                if hasattr(response_message, 'reasoning') and len(response_message.reasoning) > 0:
                    self.log_callback(LogType.AGENT_REASONING, response_message.reasoning)

            if not self.dispatcher.dispatch_function(response_message, messages):
                if self.log_callback is not None:
                    self.log_callback(LogType.ERROR, 'Returned response without tool call. Stopping')
                    break
