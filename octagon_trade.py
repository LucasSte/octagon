from octagon.agent.trader_agent import TraderAgent
from octagon.dashboard.dashboard import Dashboard
from octagon.tools.market_data.yahoo import today_date_time

MODEL = "qwen3.8-27b"
URL = "http://localhost:1234/v1"

if __name__ == "__main__":
    initial_prompt = f"""
    You are a quantitative trader allowed to perform trades, and your goal is to increase the available balance 
    of my portfolio by actively trading the available assets and using the provided tools for information access.
    
    You'll have multiple opportunities to buy and sell assets. Do not ask any questions. Use the 
    available tools to enhance your trading decisions.
    
    Do not put more than 70% of your money in a single asset.
    
    Decide realistic profit targets before entering the positon, and write them on memory for next 
    rounds. Unless there is a market downturn, stick to the targets.
    
    Besides monitoring the assets you've purchased, be open to new opportunities in the basket of 
    available assets, so check them during the day as well.
    
    Today's date is {today_date_time()}
    """
    iterations = 35

    trader_agent = TraderAgent(iterations, initial_prompt, URL, MODEL)
    dashboard = Dashboard(trader_agent)

    dashboard.run()
