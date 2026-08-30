from octagon.agent.trader_agent import TraderAgent
from octagon.dashboard.dashboard import Dashboard
from octagon.tools.market_data.yahoo import today_date_time

MODEL = "Ternary-Bonsai-27B-Q2_0.gguf"
URL = "http://localhost:1234/v1"

if __name__ == "__main__":
    initial_prompt = f"""
    You are a quantitative trader allowed to perform day trades, and your goal is to increase the available balance 
    of my portfolio by actively trading the available assets and using the provided tools for information access.
    
    You'll have multiple opportunities to buy and sell assets during the day. Do not ask any questions. Use the 
    available tools for all your needs.
    
    Do not put all your money in a single asset.
    
    Today's date is {today_date_time()}
    """
    rounds = 30

    trader_agent = TraderAgent(rounds, initial_prompt, URL, MODEL)
    dashboard = Dashboard(trader_agent)

    dashboard.run()
