import os

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
    
    For day trading, gains of 1% or more are significant to lock profits.
    Besides monitoring the assets you've purchased, be open to new opportunities in the basket of 
    available assets, so check them during the day as well.
    
    Today's date is {today_date_time()}
    """
    rounds = 30

    if os.path.exists("memory.txt"):
        with open("memory.text", "r") as f:
            lines = f.readlines()
            initial_prompt += f"\n\nYour memory says:\n {lines}"

    trader_agent = TraderAgent(rounds, initial_prompt, URL, MODEL)
    dashboard = Dashboard(trader_agent)

    dashboard.run()
