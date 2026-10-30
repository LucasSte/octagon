import os
from collections.abc import Callable

from openai import OpenAI

from octagon.agent.tool_dispatch import ToolDispatch
from octagon.dashboard.log_type import LogType
from octagon.tools.analysis.metadata import AnalysisTools
from octagon.tools.assets.available_assets import AssetsTool
from octagon.tools.assets.portfolio import Portfolio
from octagon.tools.market_data.metadata import MarketDataTools
from octagon.tools.market_data.yahoo import today_date_time
from octagon.tools.tool_definition import ToolDefinition
from octagon.tools.utilities.metadata import UtilityTools


class TraderAgent:
    def __init__(
        self,
        rounds: int,
        initial_prompt: str,
        llm_url: str,
        model_name: str,
        default_tools,
    ):
        self.rounds = rounds
        self.initial_prompt = initial_prompt
        api_key = os.environ.get("OPENAI_API_KEY") or "not-needed"
        self.client = OpenAI(base_url=llm_url, api_key=api_key)
        self.model_name = model_name

        self.portfolio = Portfolio(10000, {})

        self.available_tools = []
        self.dispatcher = ToolDispatch()

        self.log_callback: Callable[[LogType, str], None] | None = None
        self.iterations_callback: Callable[[int, int], None] | None = None

        self.history = []
        if default_tools:
            self.register_default_tools()

    def register_tool(self, tool: ToolDefinition):
        self.available_tools += tool.description()
        self.dispatcher.register_dispatch(tool.dispatch_dictionary())

    def register_default_tools(self):
        self.register_tool(AnalysisTools())
        self.register_tool(AssetsTool())
        self.register_tool(self.portfolio)
        self.register_tool(MarketDataTools())
        self.register_tool(UtilityTools())

    def set_tool_status_callback(self, callback: Callable[[str], None]):
        # message
        self.dispatcher.set_tool_status_callback(callback)

    def set_log_callback(self, callback: Callable[[LogType, str], None]):
        # Log type, message
        self.log_callback = callback
        self.dispatcher.set_log_callback(callback)

    def set_assets_callback(self, callback: Callable[[str, float], None]):
        # Assets, balance
        self.portfolio.set_interface_callback(callback)

    def set_iterations_callback(self, callback: Callable[[int, int], None]):
        # Current iteration, maximum iterations
        self.iterations_callback = callback

    def talk_to_agent(self, message: str):
        content = [{"type": "text", "text": message}]
        self.history.append(
            {
                "role": "user",
                "content": content,
            }
        )
        try:
            chat_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
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
            return
        response_message = chat_response.choices[0].message
        self.log_model_returns(response_message)

    def clear_history(self):
        self.history = []

    def start_interaction(self):
        self.history.append(
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You are now in user interaction mode. Interrupt what you were "
                        "doing and answer user questions first.",
                    }
                ],
            }
        )

    def end_interaction(self):
        self.history.append(
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "User interaction finished. "
                        "DO NOT ask any more questions while you continue to trade.",
                    }
                ],
            }
        )

    def log_model_returns(self, response_message):
        if self.log_callback is not None:
            if (
                hasattr(response_message, "reasoning_content")
                and len(response_message.reasoning_content) > 0
            ):
                self.log_callback(
                    LogType.AGENT_REASONING, response_message.reasoning_content
                )

            if (
                hasattr(response_message, "reasoning")
                and len(response_message.reasoning) > 0
            ):
                self.log_callback(LogType.AGENT_REASONING, response_message.reasoning)

            if (
                response_message.content is not None
                and len(response_message.content) > 0
            ):
                self.log_callback(LogType.AGENT_MESSAGE, response_message.content)

            if (
                response_message.refusal is not None
                and len(response_message.refusal) > 0
            ):
                self.log_callback(LogType.AGENT_MESSAGE, response_message.refusal)

        _, has_stop = self.dispatcher.dispatch_function(response_message, self.history)

        if has_stop:
            self.log_callback(LogType.INFO, "Stop requested by agent.")

    def agent_loop(self, should_stop):
        start_prompt = self.initial_prompt
        start_prompt += f"\n\n Today's date is {today_date_time()}"

        content = [{"type": "text", "text": start_prompt}]

        self.history.append(
            {
                "role": "user",
                "content": content,
            }
        )

        for i in range(self.rounds + 1):
            if self.iterations_callback is not None and i < self.rounds:
                self.iterations_callback(i + 1, self.rounds)

            if i == self.rounds - 1:
                new_content = [
                    {
                        "type": "text",
                        "text": "This is your last iteration in this trading round. I suggest you write a summary"
                        " of your actions with the write_memory function so that you maintain a good knowledge "
                        "for the next round.",
                    }
                ]
                self.history.append(
                    {
                        "role": "user",
                        "content": new_content,
                    }
                )

            if should_stop():
                break

            try:
                chat_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.history,
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

            self.log_model_returns(response_message)

            executed_action, has_stop = self.dispatcher.dispatch_function(
                response_message, self.history
            )
            if not executed_action and self.log_callback is not None:
                self.log_callback(
                    LogType.ERROR, "Returned response without tool call. Stopping"
                )
                break

            if has_stop:
                self.log_callback(LogType.INFO, "Stop requested by agent.")
                break
