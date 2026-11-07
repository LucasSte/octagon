from collections.abc import Callable

from octagon.tools.tool_definition import ToolDefinition


class UserInteractionTools(ToolDefinition):
    def __init__(self) -> None:
        pass

    def return_control(self):
        pass

    def description(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "return_control",
                    "description": "Transfer control back to user. Call this function to stop the execution loop once you have finished a user request or response.",
                    "returns": {
                        "type": "string",
                        "description": "A message confirming the transfer.",
                    },
                },
            },
        ]

    def dispatch_dictionary(self) -> dict[str, Callable]:
        return {
            "return_control": self.return_control,
        }
