import textwrap
import threading
from datetime import datetime
from enum import Enum

from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, RichLog, Select, Static
from textual.worker import get_current_worker

from octagon.agent.trader_agent import TraderAgent
from octagon.dashboard.log_type import LogType
from octagon.simulation.clock import MARKET_TZ, get_clock
from octagon.simulation.replay import (
    ReplayConfig,
    check_replay_day,
    parse_replay_start,
)

LIVE_MODE = "live"
SIMULATION_MODE = "simulation"


class AgentState(Enum):
    TALKING = 1
    WORKING = 2


class Dashboard(App):
    def __init__(
        self,
        agent: TraderAgent,
        driver_class=None,
        css_path=None,
        watch_css=False,
        ansi_color=None,
    ):
        super().__init__(driver_class, css_path, watch_css, ansi_color)
        self.active_worker = None
        self.agent = agent

        self.agent.set_tool_status_callback(self.tool_status_update)
        self.agent.set_log_callback(self.main_log_update)
        self.agent.set_assets_callback(self.update_assets)
        self.agent.set_iterations_callback(self.update_iterations)
        self.state = AgentState.WORKING
        self.agent_lock = threading.Lock()
        self.iterations = (0, 0)

    def compose(self) -> ComposeResult:
        with Vertical(id="root"):
            with Horizontal(id="body"):
                with Vertical(id="left"):
                    with Horizontal(id="top_left_row"):
                        yield RichLog(
                            max_lines=6,
                            auto_scroll=True,
                            wrap=False,
                            id="top_row_left",
                        )
                        yield Static(
                            Panel(
                                "Iterations: 0/0",
                                title="Agent",
                                border_style="green",
                                expand=True,
                            ),
                            id="top_row_right",
                        )

                    yield RichLog(
                        max_lines=55,
                        auto_scroll=True,
                        wrap=True,
                        id="bottom_left",
                    )

                with Vertical(id="right"):
                    yield Static(
                        Panel(
                            "$0",
                            title="Uninvested balance",
                            border_style="magenta",
                            expand=True,
                        ),
                        id="top_right",
                    )
                    yield Static(
                        Panel("None", title="Assets", border_style="red", expand=True),
                        id="bottom_right",
                    )

            with Horizontal(id="mode_bar"):
                yield Select(
                    [("Live trading", LIVE_MODE), ("Simulation", SIMULATION_MODE)],
                    value=self.current_mode(),
                    allow_blank=False,
                    id="mode_select",
                )
                replay = self.agent.replay
                yield Input(
                    value=(
                        f"{replay.day} {replay.start_time:%H:%M}"
                        if replay is not None
                        else ""
                    ),
                    placeholder="Day to simulate: YYYY-MM-DD or YYYY-MM-DD HH:MM, then Enter",
                    id="sim_date",
                )

            yield Input(
                placeholder="Enter a command and press Enter...",
                id="command",
            )

    def on_mount(self) -> None:
        # Overall vertical structure
        self.query_one("#root").styles.height = "100%"
        self.query_one("#body").styles.height = "1fr"

        # Main area: left = 75%, right = 25%
        self.query_one("#left").styles.width = "75%"
        self.query_one("#right").styles.width = "25%"

        # Tool panel
        recent_tools = self.query_one("#top_row_left", RichLog)
        recent_tools.styles.height = "1fr"
        recent_tools.styles.border = ("round", "cyan")
        recent_tools.styles.border_title_align = "center"
        recent_tools.styles.background = "transparent"
        recent_tools.border_title = "Most recent tool calls"
        recent_tools.styles.width = "4fr"

        # Agent loops
        agent_loops = self.query_one("#top_row_right", Static)
        agent_loops.styles.height = "1fr"
        agent_loops.styles.width = "1fr"

        # Log panel
        recent_messages = self.query_one("#bottom_left", RichLog)
        recent_messages.styles.height = "3fr"
        recent_messages.styles.border = ("round", "green")
        recent_messages.styles.border_title_align = "center"
        recent_messages.styles.background = "transparent"
        recent_messages.border_title = "Monitor logs"

        # Right panels
        self.query_one("#top_right").styles.height = "1fr"
        self.query_one("#bottom_right").styles.height = "5fr"

        # Mode bar
        self.query_one("#mode_bar").styles.height = "auto"
        self.query_one("#mode_select").styles.width = 24
        date_box = self.query_one("#sim_date", Input)
        date_box.styles.width = "1fr"
        date_box.styles.border = ("round", "magenta")
        date_box.border_title = "Simulated day (New York time)"

        # Command box
        self.working_input_box()
        self.refresh_agent_panel()

        self.main_log_update(LogType.INFO, "Welcome to Octagon!")
        self.display_help()
        self.main_log_update(
            LogType.INFO,
            "Run `load` to load a previously saved portfolio for this session.",
        )

    def working_input_box(self):
        command_box = self.query_one("#command", Input)
        command_box.styles.height = 3
        command_box.styles.border = ("round", "yellow")
        command_box.border_title = "Agent command input"

    def tool_status_update(self, message: str):
        log = self.query_one("#top_row_left", RichLog)
        line = Text(message)
        line = (line[:70] + "...") if len(line) > 70 else line
        log.write(line)
        self.refresh_agent_panel()

    def main_log_update(self, log_type: LogType, message: str):
        line = Text()
        match log_type:
            case LogType.INFO:
                line.append("INFO: ", style="cyan")
            case LogType.WARN:
                line.append("WARN: ", style="amber")
            case LogType.ERROR:
                line.append("ERROR: ", style="red")
            case LogType.AGENT_MESSAGE:
                line.append("AGENT: ", style="yellow")
            case LogType.AGENT_REASONING:
                line.append("REASONING: ", style="purple")
            case LogType.USER_MESSAGE:
                line.append("USER: ", style="blue")
            case LogType.AGENT_REPLY:
                line.append("AGENT RESPONSE: ", style="green")
        line.append(message.rstrip())

        log = self.query_one("#bottom_left", RichLog)
        log.write(line)

    def update_assets(self, assets: str, balance: float):
        self.query_one("#top_right", Static).update(
            Panel(
                f"${balance:.2f}",
                title="Uninvested balance",
                border_style="magenta",
                expand=True,
            )
        )

        self.query_one("#bottom_right", Static).update(
            Panel(assets, title="Assets", border_style="red", expand=True)
        )

    def update_iterations(self, current: int, maximum: int):
        self.iterations = (current, maximum)
        self.refresh_agent_panel()

    def refresh_agent_panel(self):
        current, maximum = self.iterations
        text = f"Iterations: {current}/{maximum}\n"
        if self.agent.replay is None:
            text += "Mode: live"
        else:
            text += f"Mode: simulation\n{get_clock().now():%Y-%m-%d %H:%M}"
        self.query_one("#top_row_right", Static).update(
            Panel(text, title="Agent", border_style="green", expand=True)
        )

    # ---------- live / simulation mode ----------

    def current_mode(self) -> str:
        return LIVE_MODE if self.agent.replay is None else SIMULATION_MODE

    def agent_busy(self) -> bool:
        return self.active_worker is not None or self.agent_lock.locked()

    def sync_mode_select(self):
        self.query_one("#mode_select", Select).value = self.current_mode()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "mode_select" or event.value == self.current_mode():
            return
        if event.value == LIVE_MODE:
            self.apply_mode(None)
            return

        day_text = self.query_one("#sim_date", Input).value.strip()
        if day_text:
            self.apply_mode(day_text)
        else:
            self.main_log_update(
                LogType.INFO,
                "Type the day to simulate in the date box and press Enter.",
            )
            self.query_one("#sim_date", Input).focus()

    def apply_mode(self, day_text: str | None):
        """Switch to live trading (None) or to simulating the day in `day_text`."""
        if self.agent_busy():
            self.main_log_update(
                LogType.ERROR, "Stop the agent before changing the trading mode."
            )
            self.sync_mode_select()
            return

        if day_text is None:
            message = self.agent.set_replay(None)
        else:
            try:
                day, start_time = parse_replay_start(day_text)
            except ValueError as e:
                self.main_log_update(LogType.ERROR, f"Invalid day to simulate: {e}")
                self.sync_mode_select()
                return

            error, warning = check_replay_day(day, datetime.now(MARKET_TZ).date())
            if error is not None:
                self.main_log_update(LogType.ERROR, error)
                self.sync_mode_select()
                return
            if warning is not None:
                self.main_log_update(LogType.WARN, warning)
            message = self.agent.set_replay(
                ReplayConfig(day=day, start_time=start_time)
            )

        # The conversation refers to another day's prices, so it must not carry over.
        self.agent.clear_history()
        self.iterations = (0, 0)
        self.main_log_update(LogType.INFO, message + " Agent context cleared.")
        if self.agent.replay is not None:
            self.main_log_update(
                LogType.INFO,
                "News, StockTwits, options, analyst and company info tools are off while simulating.",
            )
        self.sync_mode_select()
        self.refresh_agent_panel()

    def simulated_session_over(self) -> bool:
        if self.agent.replay is not None and get_clock().session_over():
            self.main_log_update(
                LogType.ERROR,
                f"The simulated session of {self.agent.replay.day} is over. "
                "Pick another day to simulate.",
            )
            return True
        return False

    def talk_to_agent(self, message):
        if self.agent_lock.locked():
            self.main_log_update(LogType.ERROR, "Agent is busy.")
            return

        self.main_log_update(LogType.USER_MESSAGE, message)
        self.agent_lock.acquire(blocking=True)
        self.agent.talk_to_agent(message)
        self.agent_lock.release()
        self.main_log_update(
            LogType.INFO,
            "Talking mode disabled.",
        )
        self.state = AgentState.WORKING
        self.working_input_box()
        self.main_log_update(
            LogType.INFO,
            "Message received. Agent will reply using the 'AGENT RESPONSE' tag.",
        )
        if self.active_worker is None and not self.agent_lock.locked():
            self.restart_agent()
        return

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "sim_date":
            self.apply_mode(event.value.strip())
            return

        command = event.value.strip()
        event.input.value = ""

        match command:
            case "quit":
                if self.agent_lock.locked():
                    self.main_log_update(
                        LogType.ERROR, "Can't quit. Waiting for agent to stop."
                    )
                    return
                self.stop_work()
                self.exit()
            case "start":
                if self.state == AgentState.TALKING:
                    self.main_log_update(LogType.ERROR, "Agent is in talking state.")
                elif self.simulated_session_over():
                    pass
                elif self.active_worker is None and not self.agent_lock.locked():
                    self.main_log_update(LogType.INFO, "Starting agent")
                    self.agent.clear_history()
                    self.agent.portfolio.update_interface()
                    self.active_worker = self.run_agent()
                else:
                    self.main_log_update(LogType.ERROR, "Agent is already running")
            case "stop":
                self.stop_work()
            case "save":
                if self.active_worker is not None:
                    self.main_log_update(
                        LogType.ERROR, "Cannot save portfolio while agent is running"
                    )
                else:
                    self.agent.portfolio.save()
                    self.main_log_update(
                        LogType.INFO,
                        f"Successfully saved portfolio in {self.agent.portfolio.file_path}",
                    )
            case "load":
                if self.active_worker is not None:
                    self.main_log_update(
                        LogType.ERROR, "Cannot load portfolio while agent is running"
                    )
                else:
                    self.agent.portfolio.load()
                    self.agent.portfolio.update_interface()
                    self.main_log_update(
                        LogType.INFO,
                        f"Successfully loaded {self.agent.portfolio.file_path}",
                    )
            case "portfolio":
                self.main_log_update(LogType.INFO, "Calculating portfolio value ...")
                self.print_portfolio()
            case "help":
                self.display_help()
            case "talk-on":
                if self.state == AgentState.TALKING:
                    self.main_log_update(
                        LogType.ERROR, "Agent is already in talking state."
                    )
                elif self.active_worker is not None:
                    self.main_log_update(
                        LogType.INFO,
                        "Talking mode enabled. You can talk to the agent after "
                        "as soon as it stops.",
                    )
                    command_box = self.query_one("#command", Input)
                    command_box.styles.height = 3
                    command_box.styles.border = ("round", "cyan")
                    command_box.border_title = "Talking input"
                    self.stop_work()
                    self.state = AgentState.TALKING
                else:
                    self.main_log_update(
                        LogType.ERROR,
                        "Agent must be running for talk mode to function.",
                    )
            case "restart":
                if self.state == AgentState.TALKING:
                    self.main_log_update(LogType.ERROR, "Agent is in talking state.")
                elif self.simulated_session_over():
                    pass
                elif self.active_worker is None and not self.agent_lock.locked():
                    self.restart_agent()
                else:
                    self.main_log_update(LogType.ERROR, "Agent is already running")
            case _:
                if self.state == AgentState.TALKING:
                    self.talk_to_agent(command)
                else:
                    self.main_log_update(LogType.ERROR, f"Unknown command: {command}")

    def restart_agent(self):
        self.main_log_update(LogType.INFO, "Restarting agent")
        self.agent.portfolio.update_interface()
        self.active_worker = self.run_agent()

    def display_help(self):
        help_message = textwrap.dedent("""
            Available commands:
            - `help`: Show available commands.
            - `quit`: Stop agent and exit interface.
            - `start`: Clear context and start trader agent.
            - `restart`: Start agent with existing context.
            - `stop`: Stop agent.
            - `save`: Save portfolio state (portfolio.json, or portfolio_replay.json when simulating).
            - `load`: Load portfolio from the same file.
            - `portfolio`: Print total porfolio value with profits and losses.
            - `talk-on`: Enable talking mode.

            Use the selector at the bottom to switch between live trading and a simulation.
            For a simulation, type a past day (YYYY-MM-DD, optionally followed by HH:MM)
            in the date box and press Enter. The agent then trades that day on historical
            data with a simulated clock. Live and simulated portfolios are kept apart.
        """)
        self.main_log_update(LogType.INFO, help_message)

    def stop_work(self):
        if self.active_worker is not None:
            self.active_worker.cancel()
            self.active_worker = None
            self.main_log_update(
                LogType.INFO,
                "Waiting for agent to disconnect. No assets can be traded anymore.",
            )

    @work(thread=True, exclusive=False, exit_on_error=True)
    def run_agent(self):
        worker = get_current_worker()
        self.agent_lock.acquire(blocking=True)
        self.agent.agent_loop(should_stop=lambda: worker.is_cancelled)
        self.main_log_update(LogType.INFO, "Agent stopped")
        if self.active_worker is not None:
            self.active_worker.cancel()
            self.active_worker = None
        if self.state == AgentState.WORKING:
            self.main_log_update(
                LogType.INFO,
                "Hint: run `save` if you want to persist the portfolio for the next trading session.",
            )
        self.agent_lock.release()

    @work(thread=True, exclusive=False)
    def print_portfolio(self):
        self.agent.portfolio.print_portfolio(self.main_log_update)
