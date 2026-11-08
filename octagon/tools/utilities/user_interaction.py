from collections.abc import Callable

from octagon.dashboard.log_type import LogType
from octagon.tools.tool_definition import ToolDefinition


class UserInteractionTools(ToolDefinition):
    def __init__(self, log_callback: Callable[[LogType, str], None]) -> None:
        self.log_callback = log_callback

    def reply_to_user(self, message: str) -> str:
        self.log_callback(LogType.AGENT_REPLY, message)
        return "Reponse displayed to user."

    def description(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "reply_to_user",
                    "description": "Reply a question the user has asked. This function prints the output in the correct prompt where users can read.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The reponse meant to be shown to the user.",
                            }
                        },
                        "required": ["text"],
                    },
                    "returns": {
                        "type": "string",
                        "description": "A message confirming the reponse was displayed.",
                    },
                },
            },
        ]

    def dispatch_dictionary(self) -> dict[str, Callable]:
        return {
            "reply_to_user": self.reply_to_user,
        }
