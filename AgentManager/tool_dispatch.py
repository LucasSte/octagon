import inspect
import json
from typing import Callable

from AssetManager.portfolio import Portfolio
import MarketData.tools_dict
import AssetManager.tools_dict
from AssetManager.assets import available_assets

class ToolDispatch:
    def __init__(self, portfolio: Portfolio):
        self.dispatch_dictionary = (Portfolio.build_dispatch_dict(portfolio) |
                               MarketData.tools_dict.DISPATCH_DICT |
                               AssetManager.tools_dict.DISPATCH_DICT)

        self.log_callback: Callable | None = None
        self.tool_status_callback: Callable | None = None

    def dispatch_function(self, response_message, message_list):
        if response_message.tool_calls:
            message_list.append(response_message)
            for tool_call in response_message.tool_calls:
                if tool_call.function.name in self.dispatch_dictionary:
                    sig = inspect.signature(self.dispatch_dictionary[tool_call.function.name])
                    optional_parameters = sum(
                        1 for param in sig.parameters.values()
                        if param.default is not inspect.Parameter.empty
                    )
                    parameters = json.loads(tool_call.function.arguments)
                    if len(parameters) < len(sig.parameters) - optional_parameters or len(parameters) > len(sig.parameters):
                        print(f'ERROR: function not found: {tool_call.function.name}, LHS: {len(parameters)}, RHS: {len(sig.parameters)}')
                        message_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": "Function not found",
                        })
                        continue

                    if 'ticker' in parameters and parameters['ticker'] not in available_assets:
                        print(f'ERROR: invalid ticker {parameters['ticker']}')
                        message_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f'Ticker {parameters['ticker']} not available.'
                        })
                        continue

                    call_response = self.dispatch_dictionary[tool_call.function.name](**parameters)
                    message_list.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": call_response,
                    })

            return True

        return False
