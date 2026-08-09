from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Static, RichLog
from textual.worker import get_current_worker

from AgentManager.trader_agent import TraderAgent
from Dashboard.log_type import LogType


class OctagonDashboard(App):
    def __init__(
        self,
        agent: TraderAgent,
        driver_class = None,
        css_path = None,
        watch_css = False,
        ansi_color = None,
    ):
        super().__init__(driver_class, css_path, watch_css, ansi_color)
        self.active_worker = None
        self.agent = agent

        self.agent.set_tool_status_callback(self.tool_status_update)
        self.agent.set_log_callback(self.main_log_update)
        self.agent.set_assets_callback(self.update_assets)

    def compose(self) -> ComposeResult:
        with Vertical(id="root"):
            with Horizontal(id="body"):
                with Vertical(id="left"):
                    yield RichLog(
                        max_lines=5,
                        auto_scroll=True,
                        wrap=False,
                        id="top_left",
                    )
                    yield RichLog(
                        max_lines=25,
                        auto_scroll=True,
                        wrap=True,
                        id="bottom_left",
                    )

                with Vertical(id="right"):
                    yield Static(
                        Panel("$0", title="Uninvested balance",
                              border_style="magenta", expand=True),
                        id="top_right",
                    )
                    yield Static(
                        Panel("None", title="Assets",
                              border_style="red", expand=True),
                        id="bottom_right"
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
        recent_tools = self.query_one("#top_left", RichLog)
        recent_tools.styles.height = "1fr"
        recent_tools.styles.border = ("round", "cyan")
        recent_tools.styles.border_title_align = "center"
        recent_tools.styles.background = "transparent"
        recent_tools.border_title = "Most recent tool calls"

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

        # Command box
        command_box = self.query_one("#command", Input)
        command_box.styles.height = 3
        command_box.styles.border = ("round", "yellow")
        command_box.border_title = "Command Input"

    def tool_status_update(self, message: str):
        log = self.query_one("#top_left", RichLog)
        line = Text(message)
        log.write(line)

    def main_log_update(self, log_type: LogType, message: str):
        line = Text()
        match log_type:
            case LogType.INFO:
                line.append('INFO: ', style='cyan')
            case LogType.WARN:
                line.append('WARN: ', style='amber')
            case LogType.ERROR:
                line.append('ERROR: ', style='red')
            case LogType.AGENT_MESSAGE:
                line.append('AGENT: ', style='yellow')
            case LogType.AGENT_REASONING:
                line.append('REASONING: ', style='purple')
        line.append(message)

        log = self.query_one('#bottom_left', RichLog)
        log.write(line)

    def update_assets(self, assets: str, balance: float):
        self.query_one("#top_right", Static).update(
            Panel(f'${balance:.2f}', title="Uninvested balance",
                              border_style="magenta", expand=True)
        )

        self.query_one("#bottom_right", Static).update(
            Panel(assets, title="Assets",
                              border_style="red", expand=True)
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip().lower()
        event.input.value = ""

        if command == "quit":
            self.exit()
            return

        if command == "start":
            self.main_log_update(LogType.INFO, 'Starting agent')
            self.update_assets('None', self.agent.portfolio.balance)
            self.active_worker = self.run_agent()

        if command == "stop":
            self.stop_work()

    def stop_work(self):
        if self.active_worker is not None:
            # This is not stopping the agent
            self.active_worker.cancel()
            self.active_worker = None
            self.main_log_update(LogType.INFO, 'Agent stopped')

    @work(thread=True, exclusive=True, exit_on_error=True)
    def run_agent(self):
        worker = get_current_worker()
        self.agent.agent_loop(should_stop=lambda: worker.is_cancelled)
        self.main_log_update(LogType.INFO, 'Agent loop finished')
