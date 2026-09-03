import os
from collections.abc import Callable

from openai import OpenAI

from octagon.agent.tool_dispatch import ToolDispatch
from octagon.dashboard.log_type import LogType
from octagon.tools.assets.portfolio import Portfolio
from octagon.tools.registration import create_tools_list


class TraderAgent:
    def __init__(self, rounds: int, initial_prompt: str, llm_url: str, model_name: str):
        self.rounds = rounds
        self.initial_prompt = initial_prompt
        api_key = os.environ.get('OPENAI_API_KEY') or 'not-needed'
        self.client = OpenAI(base_url=llm_url, api_key=api_key)
        self.model_name = model_name

        self.portfolio = Portfolio(10000, {})

        self.available_tools = create_tools_list()
        self.dispatcher = ToolDispatch(self.portfolio)

        self.log_callback: Callable | None = None
        self.iterations_callback: Callable | None = None

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

    def set_iterations_callback(self, callback: Callable):
        # Current iteration, maximum iterations
        self.iterations_callback = callback

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

            if self.iterations_callback is not None:
                self.iterations_callback(i+1, self.rounds)

            if should_stop():
                break

            try:
                chat_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=self.available_tools,
                    max_tokens=8196,
                    temperature=0.7,
                    top_p=0.95,
                    extra_body={
                        "top_k": 20,
                    },
                )
            # ruff: noqa: BLE001
            except Exception as e:
                if self.log_callback is not None:
                    self.log_callback(LogType.ERROR, str(e))
                break
            response_message = chat_response.choices[0].message

            if should_stop():
                break

            if self.log_callback is not None:

                if response_message.content is not None and len(response_message.content) > 0:
                    self.log_callback(LogType.AGENT_MESSAGE, response_message.content)

                if response_message.refusal is not None and len(response_message.refusal) > 0:
                    self.log_callback(LogType.AGENT_MESSAGE, response_message.refusal)


                if hasattr(response_message, 'reasoning_content') and len(response_message.reasoning_content) > 0:
                    self.log_callback(LogType.AGENT_REASONING, response_message.reasoning_content)

                if hasattr(response_message, 'reasoning') and len(response_message.reasoning) > 0:
                    self.log_callback(LogType.AGENT_REASONING, response_message.reasoning)

            if not self.dispatcher.dispatch_function(response_message, messages) and self.log_callback is not None:
                self.log_callback(LogType.ERROR, 'Returned response without tool call. Stopping')
                break
