from typing import Type

from rich.panel import Panel
from rich.text import Text
from textual import work, messages
from textual._path import CSSPathType
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.driver import Driver
from textual.widgets import Input, Static, RichLog
from textual.worker import get_current_worker
import time

def do_work(command: str, callback, should_stop) -> None:
    """Example cancellable work."""
    for step in range(1, 11):
        if should_stop():
            return

        time.sleep(0.5)  # Replace with one short unit of real work
        callback(f"Running {command}: step {step}/10")

    callback(f"Completed: {command}")

class Dashboard(App):
    def __init__(
        self,
        driver_class: Type[Driver] | None = None,
        css_path: CSSPathType | None = None,
        watch_css: bool = False,
        ansi_color: bool | None = None,
    ):
        super().__init__(driver_class, css_path, watch_css, ansi_color)
        self.active_worker = None

    def compose(self) -> ComposeResult:
        with Vertical(id="root"):
            with Horizontal(id="body"):
                with Vertical(id="left"):
                    yield Static(
                        Panel("Type a command below.", title="Top Left",
                              border_style="cyan", expand=True),
                        id="top_left",
                    )
                    yield RichLog(
                        max_lines=25,
                        auto_scroll=True,
                        wrap=False,
                        id="bottom_left",
                    )

                yield Static(
                    Panel("Waiting for a command.", title="Right",
                          border_style="magenta", expand=True),
                    id="right",
                )

            yield Input(
                placeholder="Enter a command and press Enter...",
                id="command",
            )

    def on_mount(self) -> None:
        # Overall vertical structure
        self.query_one("#root").styles.height = "100%"
        self.query_one("#body").styles.height = "1fr"
        self.query_one("#command").styles.height = 3
        self.query_one("#command").styles.border = ("round", "yellow")

        # Main area: left = 75%, right = 25%
        self.query_one("#left").styles.width = "75%"
        self.query_one("#right").styles.width = "25%"

        # Left panels split the available height equally
        self.query_one("#top_left").styles.height = "1fr"
        recent_messages = self.query_one("#bottom_left", RichLog)
        recent_messages.styles.height = "3fr"
        recent_messages.styles.border = ("round", "green")
        recent_messages.styles.border_title_align = "center"
        recent_messages.styles.background = "transparent"
        recent_messages.border_title = "Recent Messages"

        self.query_one("#right").styles.height = "1fr"

        command_box = self.query_one("#command", Input)

        command_box.styles.height = 3
        command_box.styles.border = ("round", "yellow")
        command_box.border_title = "Command Input"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update a Rich panel while the user types."""
        self.query_one("#top_left", Static).update(
            Panel(
                f"Typing: {event.value or '(nothing yet)'}",
                title="Top Left",
                border_style="cyan",
                expand=True,
            )
        )

    def update_right_panel(self, message: str) -> None:
        self.query_one("#right", Static).update(
            Panel(message, title="Right", border_style="magenta")
        )

    def add_message(self, status: str, message: str) -> None:
        log = self.query_one("#bottom_left", RichLog)

        # Keep each message to one line, so max_lines=5 means five messages.
        line = Text()
        line.append(f"[{status}] ", style="bold yellow")
        line.append(message.replace("\n", " "), style="bright_cyan")

        log.write(line)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Run when Enter is pressed in the Textual input box."""
        command = event.value.strip().lower()
        event.input.value = ""

        if command == "quit":
            self.exit()
            return

        if command == "do_work":
            self.active_worker = self.run_command(command)

        if command == "stop":
            self.stop_work()

        if 'mess' in command:
            self.add_message('INFO', 'Hello!')

        # result = {
        #     "hello": "Hello!",
        #     "status": "System status: OK",
        #     "clear": "Panels cleared.",
        # }.get(command, f"Unknown command: {command}")
        #
        # self.query_one("#right", Static).update(
        #     Panel(result, title="Right", border_style="magenta", expand=True)
        # )

    def stop_work(self):
        if self.active_worker is not None:
            self.active_worker.cancel()
            self.update_right_panel("Stopping")
            self.active_worker = None

    @work(thread=True, exclusive=True, exit_on_error=False)
    def run_command(self, command: str):
        worker = get_current_worker()

        def on_update(message: str):
            if not worker.is_cancelled:
                self.call_from_thread(self.update_right_panel, message)

        do_work(
            command,
            callback=on_update,
            should_stop=lambda: worker.is_cancelled,
        )


if __name__ == "__main__":
    Dashboard().run()