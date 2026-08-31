from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Static, RichLog
from textual.worker import get_current_worker

from octagon.agent.trader_agent import TraderAgent
from octagon.dashboard.log_type import LogType


class Dashboard(App):
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
        self.agent.set_iterations_callback(self.update_iterations)

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
                            Panel("Iterations: 0/0", title="Agent",
                                  border_style="green", expand=True),
                            id="top_row_right",
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

        # Command box
        command_box = self.query_one("#command", Input)
        command_box.styles.height = 3
        command_box.styles.border = ("round", "yellow")
        command_box.border_title = "Command Input"

    def tool_status_update(self, message: str):
        log = self.query_one("#top_row_left", RichLog)
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

    def update_iterations(self, current: int, maximum: int):
        self.query_one("#top_row_right", Static).update(
            Panel(f'Iterations: {current}/{maximum}', title="Agent",
                  border_style="green", expand=True)
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip().lower()
        event.input.value = ""

        match command:
            case "quit":
                self.stop_work()
                self.exit()
            case "start":
                self.main_log_update(LogType.INFO, 'Starting agent')
                self.agent.portfolio.update_interface()
                self.active_worker = self.run_agent()
            case "stop":
                self.stop_work()
            case "save":
                if self.active_worker is not None:
                    self.main_log_update(LogType.ERROR, 'Cannot save portfolio while agent is running')
                else:
                    self.agent.portfolio.save()
                    self.main_log_update(LogType.INFO, 'Successfully saved portfolio in portfolio.json')
            case "load":
                if self.active_worker is not None:
                    self.main_log_update(LogType.ERROR, 'Cannot load portfolio while agent is running')
                else:
                    self.agent.portfolio.load()
                    self.agent.portfolio.update_interface()
                    self.main_log_update(LogType.INFO, 'Successfully loaded portfolio.json')
            case "portfolio":
                self.main_log_update(LogType.INFO, 'Calculating portoflio value ...')
                self.print_portfolio()

    def stop_work(self):
        if self.active_worker is not None:
            self.active_worker.cancel()
            self.active_worker = None
            self.main_log_update(LogType.INFO, 'Waiting for agent to disconnect. No assets can be traded anymore.')

    @work(thread=True, exclusive=False, exit_on_error=True)
    def run_agent(self):
        worker = get_current_worker()
        self.agent.agent_loop(should_stop=lambda: worker.is_cancelled)
        self.main_log_update(LogType.INFO, 'Agent stopped')

    @work(thread=True, exclusive=False)
    def print_portfolio(self):
        self.agent.portfolio.print_portfolio(self.main_log_update)
