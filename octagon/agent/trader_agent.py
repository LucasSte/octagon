import os
import time
from collections.abc import Callable

from openai import OpenAI

from octagon.agent.tool_dispatch import ToolDispatch
from octagon.dashboard.log_type import LogType
from octagon.simulation.clock import get_clock
from octagon.simulation.replay import (
    REPLAY_UNAVAILABLE_TOOLS,
    ReplayConfig,
    disable_replay,
    enable_replay,
)
from octagon.tools.analysis.metadata import AnalysisTools
from octagon.tools.analysis.news_analysis import NewsHeadlines
from octagon.tools.assets.available_assets import AssetsTool
from octagon.tools.assets.portfolio import Portfolio
from octagon.tools.market_data.metadata import MarketDataTools
from octagon.tools.market_data.yahoo import today_date_time
from octagon.tools.tool_definition import ToolDefinition
from octagon.tools.utilities.metadata import UtilityTools
from octagon.tools.utilities.user_interaction import UserInteractionTools

# How many replies in a row without a tool call are tolerated before stopping.
MAX_TEXT_ONLY_REPLIES = 2

INITIAL_BALANCE = 10000


class TraderAgent:
    def __init__(
        self,
        rounds: int,
        initial_prompt: str,
        llm_url: str,
        model_name: str,
        default_tools,
        replay: ReplayConfig | None = None,
    ):
        self.initial_rounds = rounds
        self.rounds = rounds
        self.initial_prompt = initial_prompt
        api_key = os.environ.get("OPENAI_API_KEY") or "not-needed"
        self.client = OpenAI(base_url=llm_url, api_key=api_key)
        self.model_name = model_name

        self.portfolio = Portfolio(INITIAL_BALANCE, {})

        self.all_tools = []
        self.dispatcher = ToolDispatch()

        self.log_callback: Callable[[LogType, str], None] | None = None
        self.iterations_callback: Callable[[int, int], None] | None = None

        self.history = []
        self.use_default_tools = default_tools
        self.news_tool = None
        if self.use_default_tools:
            self.register_default_tools()

        # Simulation (replay) state. Live and simulated portfolios are kept apart.
        self.replay: ReplayConfig | None = None
        self.live_portfolio = None
        self.simulated_portfolio = None
        self.last_simulated_day = None
        if replay is not None:
            self.set_replay(replay)

    @property
    def available_tools(self) -> list[dict]:
        """Tools offered to the model. Live-only data tools are hidden during a simulation."""
        return [
            item
            for item in self.all_tools
            if item["function"]["name"] not in self.dispatcher.excluded_tools
        ]

    def register_tool(self, tool: ToolDefinition):
        self.all_tools += tool.description()
        self.dispatcher.register_dispatch(tool.dispatch_dictionary())

    def register_default_tools(self):
        self.news_tool = NewsHeadlines(self.client, self.model_name)
        self.register_tool(AnalysisTools())
        self.register_tool(AssetsTool())
        self.register_tool(self.portfolio)
        self.register_tool(MarketDataTools())
        self.register_tool(UtilityTools())
        self.register_tool(self.news_tool)

    def set_replay(self, config: ReplayConfig | None) -> str:
        """
        Switch between live trading (config None) and simulating a past day on historical data.
        Must not be called while the agent loop runs. Returns a message describing the switch.
        """
        if config is None:
            if self.replay is None:
                return "Already in live mode."
            self.simulated_portfolio = self.portfolio.snapshot()
            disable_replay()
            self.portfolio.restore(self.live_portfolio)
            self.portfolio.file_path = "portfolio.json"
            self.dispatcher.excluded_tools = set()
            self.replay = None
            return "Switched to live trading with the live portfolio."

        if self.replay is None:
            self.live_portfolio = self.portfolio.snapshot()
        else:
            self.simulated_portfolio = self.portfolio.snapshot()

        enable_replay(config)
        self.dispatcher.excluded_tools = set(REPLAY_UNAVAILABLE_TOOLS)
        self.portfolio.file_path = config.portfolio_file

        # Holdings from a later day would leak the future, so only carry them forward in time.
        carried = (
            self.simulated_portfolio is not None
            and self.last_simulated_day is not None
            and config.day > self.last_simulated_day
        )
        if carried:
            self.portfolio.restore(self.simulated_portfolio)
            message = f"Kept the simulated portfolio from {self.last_simulated_day}."
        else:
            self.portfolio.restore(Portfolio(INITIAL_BALANCE, {}).snapshot())
            message = f"Started a new simulated portfolio with ${INITIAL_BALANCE:,}."

        self.replay = config
        self.last_simulated_day = config.day
        return (
            f"Simulating {config.day} from {config.start_time:%H:%M} New York time. "
            + message
        )

    def set_tool_status_callback(self, callback: Callable[[str], None]):
        # message
        self.dispatcher.set_tool_status_callback(callback)

    def set_log_callback(self, callback: Callable[[LogType, str], None]):
        # Log type, message
        self.log_callback = callback
        self.dispatcher.set_log_callback(callback)
        if self.use_default_tools:
            user_interaction = UserInteractionTools(callback)
            self.register_tool(user_interaction)
        if self.news_tool is not None:
            self.news_tool.register_log_callback(callback)

    def set_assets_callback(self, callback: Callable[[str, float], None]):
        # Assets, balance
        self.portfolio.set_interface_callback(callback)

    def set_iterations_callback(self, callback: Callable[[int, int], None]):
        # Current iteration, maximum iterations
        self.iterations_callback = callback

    def talk_to_agent(self, message: str):
        content = [
            {
                "type": "text",
                "text": f"{message}\n Respond to this using the 'reply_to_user' function if available.",
            }
        ]
        self.history.append(
            {
                "role": "user",
                "content": content,
            }
        )

    def clear_history(self):
        self.rounds = self.initial_rounds
        self.history = []

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

        consecutive_text_replies = 0
        clock = get_clock()
        close_notified = False
        for i in range(self.rounds + 1):
            if self.iterations_callback is not None and i < self.rounds:
                self.iterations_callback(i + 1, self.rounds)

            if clock.session_over():
                if close_notified:
                    if self.log_callback is not None:
                        self.log_callback(
                            LogType.INFO, "Simulated trading session is over."
                        )
                    break
                # Give the agent one last turn to write its memory, like on the last iteration.
                close_notified = True
                self.history.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"The market closed ({today_date_time()}). Trading is no longer "
                                "possible. Write a summary of your actions with the write_memory function "
                                "or call stop so that you maintain a good knowledge for the next round.",
                            }
                        ],
                    }
                )
            elif i == self.rounds - 1:
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
                self.rounds = self.initial_rounds - i - 1
                break

            try:
                request_start = time.monotonic()
                chat_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.history,
                    tools=self.available_tools,
                    max_tokens=8196,
                    temperature=0.5,
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
            # In a replay, thinking costs market time just like it would live.
            clock.on_agent_turn(time.monotonic() - request_start)

            if should_stop():
                self.rounds = self.initial_rounds - i - 1
                break

            self.log_model_returns(response_message)

            executed_action, has_stop = self.dispatcher.dispatch_function(
                response_message, self.history
            )
            if not executed_action:
                consecutive_text_replies += 1
                if consecutive_text_replies > MAX_TEXT_ONLY_REPLIES:
                    if self.log_callback is not None:
                        self.log_callback(
                            LogType.ERROR,
                            "Agent repeatedly replied without a tool call. Stopping",
                        )
                    break

                if self.log_callback is not None:
                    self.log_callback(
                        LogType.INFO,
                        "Returned response without tool call. Nudging agent.",
                    )
                self.history.append(
                    {
                        "role": "assistant",
                        "content": response_message.content or "",
                    }
                )
                self.history.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "You replied without calling a tool. Continue trading by calling "
                                "one of the available tools (for example, 'wait' to monitor the market "
                                "later, or 'stop' to end the session).",
                            }
                        ],
                    }
                )
                continue

            consecutive_text_replies = 0

            if has_stop:
                if self.log_callback is not None:
                    self.log_callback(LogType.INFO, "Stop requested by agent.")
                break
