import inspect
import json

def dispatch_function(response_message, dispatch_dictionary, allowed_assets, message_list):
    if response_message.tool_calls:
        message_list.append(response_message)
        for tool_call in response_message.tool_calls:
            if tool_call.function.name in dispatch_dictionary:
                sig = inspect.signature(dispatch_dictionary[tool_call.function.name])
                parameters = json.loads(tool_call.function.arguments)
                if len(parameters) != len(sig.parameters):
                    print(f'ERROR: function not found: {tool_call.function.name}, LHS: {len(parameters)}, RHS: {len(sig.parameters)}')
                    message_list.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "Function not found",
                    })
                    continue

                if 'ticker' in parameters and parameters['ticker'] not in allowed_assets:
                    print(f'ERROR: invalid ticker {parameters['ticker']}')
                    message_list.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f'Ticker {parameters['ticker']} not available.'
                    })
                    continue

                call_response = dispatch_dictionary[tool_call.function.name](**parameters)
                message_list.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": call_response,
                })

        return True

    return False
