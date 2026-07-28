from openai import OpenAI
from AssetManager.portfolio import Portfolio
from AssetManager.tools_dict import TOOLS_DICT as asset_tools
from MarketData.tools_dict import TOOLS_DICT as market_tools
from MarketData.tools_dict import DISPATCH_DICT as market_dispatch
from AgentManager.tool_dispatch import dispatch_function
from AssetManager.assets import available_assets

def start_trading(rounds):
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
    my_portfolio = Portfolio(1000, dict())
    available_tools = market_tools + asset_tools
    dispatch_dictionary = Portfolio.build_dispatch_dict(my_portfolio) | market_dispatch

    initial_prompt = """
    You are a day trader, and your goal is to increase the available balance of my portfolio by actively trading 
    the available assets and using the provided tools for information access.
    
    You'll have multiple opportunities to buy and sell assets during the day.
    """

    content = [
        {
            "type": "text",
            "text": initial_prompt,
        }
    ]

    messages = [
        {
            "role": "user",
            "content": content,
        }
    ]

    for i in range(rounds):
        chat_response = client.chat.completions.create(
            model="Ternary-Bonsai-27B-Q2_0.gguf",
            messages=messages,
            tools=available_tools,
            max_tokens=4096,
            temperature=0.7,
            top_p=0.95,
            extra_body={
                "top_k": 20,
                # "enable_thinking": False,
            },
        )
        response_message = chat_response.choices[0].message
        if dispatch_function(response_message, dispatch_dictionary, available_assets, messages):
            print('Tool call detected')
        else:
            print('Returned without tool call')
            print(messages)
            break

        if i == rounds - 1:
            print(messages)



