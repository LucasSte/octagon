from collections.abc import Callable

from octagon.agent.trader_agent import TraderAgent
from octagon.dashboard.dashboard import Dashboard
from octagon.dashboard.log_type import LogType
from octagon.simulation.clock import get_clock
from octagon.simulation.replay import ReplayConfig
from octagon.tools.tool_definition import ToolDefinition


class OctagonAgent:
    def __init__(
        self,
        iterations: int,
        initial_prompt: str,
        url,
        model,
        default_tools=True,
        replay: ReplayConfig | None = None,
    ):
        """
        :param iterations: Number of iterations to run the agent for
        :param initial_prompt: Initial prompt to start with
        :param url: URL endpoint to invoke the agent
        :param model: The model that is serving as the LLM
        :param default_tools: Whether to use the TraderAgent default tools
        :param replay: If set, the agent trades a past day on historical data with a simulated clock
        """
        self.inner_agent = TraderAgent(
            iterations, initial_prompt, url, model, default_tools, replay
        )
        self.dashboard = None

    @property
    def clock(self):
        return get_clock()

    def set_replay(self, config: ReplayConfig | None) -> str:
        """Switch between live trading (None) and simulating a past day."""
        return self.inner_agent.set_replay(config)

    def register_tool(self, tool: ToolDefinition):
        self.inner_agent.register_tool(tool)

    def set_tool_status_callback(self, callback: Callable[[str], None]):
        """
        :param callback: A call back to log tool status
        :return: None
        """
        self.inner_agent.set_tool_status_callback(callback)

    def set_log_callback(self, callback: Callable[[LogType, str], None]):
        """
        :param callback: A call back for general logging
        :return: None
        """
        self.inner_agent.set_log_callback(callback)

    def set_assets_callback(self, callback: Callable[[str, float], None]):
        """
        :param callback: A callback to log assets
        :return: None
        """
        self.inner_agent.set_assets_callback(callback)

    def set_iterations_callback(self, callback: Callable[[int, int], None]):
        """
        :param callback: A callback to log the number of iterations run
        :return: None
        """
        self.inner_agent.set_iterations_callback(callback)

    def run_with_dashboard(self):
        """
        Run the agent with a visual dashboard interface. This function never returns.
        """
        if self.dashboard is None:
            self.dashboard = Dashboard(self.inner_agent)

        self.dashboard.run()

    def run_silent(self):
        """
        Run the agent without a visual interface. This function returns once the number of iterations is reached or
        the agent requests to stop.
        """
        self.inner_agent.agent_loop(should_stop=lambda: False)
