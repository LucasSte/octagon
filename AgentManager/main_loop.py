from openai import OpenAI
from AssetManager.portfolio import Portfolio
import MarketData.tools_dict
import AssetManager.tools_dict
from AgentManager.tool_dispatch import dispatch_function
from AssetManager.assets import available_assets

def start_trading(rounds):
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
    my_portfolio = Portfolio(1000, dict())
    available_tools = MarketData.tools_dict.TOOLS_DICT + AssetManager.tools_dict.TOOLS_DICT
    dispatch_dictionary = Portfolio.build_dispatch_dict(my_portfolio) | MarketData.tools_dict.DISPATCH_DICT | AssetManager.tools_dict.DISPATCH_DICT

    initial_prompt = """
    You are a day trader, and your goal is to increase the available balance of my portfolio by actively trading 
    the available assets and using the provided tools for information access.
    
    You'll have multiple opportunities to buy and sell assets during the day. Do not ask any questions. Use the 
    available tools for all your needs.
    
    Do not put all your money in a single asset.
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
        try:
            chat_response = client.chat.completions.create(
                model="Ternary-Bonsai-27B-Q2_0.gguf",
                # model="maple-2bit-mlx",
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
                print(chat_response)
                break

            if i == rounds - 1:
                print(messages)
        except Exception as e:
            print(messages)
            raise e



