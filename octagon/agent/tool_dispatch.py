import inspect
import json
from collections.abc import Callable

from octagon.dashboard.log_type import LogType
from octagon.tools.assets.available_assets import available_assets
from octagon.tools.assets.portfolio import Portfolio
from octagon.tools.registration import create_dispatch_dictionary


class ToolDispatch:
    def __init__(self, portfolio: Portfolio):
        self.dispatch_dictionary = create_dispatch_dictionary(portfolio)

        self.log_callback: Callable | None = None
        self.tool_status_callback: Callable | None = None

    def set_log_callback(self, callback: Callable):
        self.log_callback = callback

    def set_tool_status_callback(self, callback: Callable):
        self.tool_status_callback = callback

    def dispatch_function(self, response_message, message_list):
        if response_message.tool_calls:
            message_list.append(response_message)
            for tool_call in response_message.tool_calls:
                if tool_call.function.name in self.dispatch_dictionary:
                    sig = inspect.signature(
                        self.dispatch_dictionary[tool_call.function.name]
                    )
                    optional_parameters = sum(
                        1
                        for param in sig.parameters.values()
                        if param.default is not inspect.Parameter.empty
                    )
                    parameters = json.loads(tool_call.function.arguments)
                    if len(parameters) < len(
                        sig.parameters
                    ) - optional_parameters or len(parameters) > len(sig.parameters):
                        if self.log_callback is not None:
                            log_message = f"function not found: {tool_call.function.name}. Incorrect number of parameters."
                            self.log_callback(LogType.ERROR, log_message)
                            # print(f'ERROR: function not found: {tool_call.function.name}, LHS: {len(parameters)}, RHS: {len(sig.parameters)}')
                        message_list.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": "Function not found",
                            }
                        )
                        continue

                    if (
                        "ticker" in parameters
                        and parameters["ticker"] not in available_assets
                    ):
                        if self.log_callback is not None:
                            log_message = f"invalid ticker {parameters['ticker']}"
                            self.log_callback(LogType.ERROR, log_message)
                            # print(f'ERROR: invalid ticker {parameters['ticker']}')
                        message_list.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Ticker {parameters['ticker']} not available.",
                            }
                        )
                        continue

                    call_response = self.dispatch_dictionary[tool_call.function.name](
                        **parameters
                    )

                    if self.tool_status_callback is not None:
                        tool_log = tool_call.function.name + "("
                        for item in parameters.values():
                            tool_log += f"{item},"
                        tool_log += ")"
                        self.tool_status_callback(tool_log)

                    message_list.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": call_response,
                        }
                    )

            return True

        return False
