from AgentManager.trader_agent import TraderAgent
from Dashboard.dashboard import OctagonDashboard
from MarketData.yahoo import today_date

if __name__ == "__main__":
    initial_prompt = f"""
    You are a day trader, and your goal is to increase the available balance of my portfolio by actively trading 
    the available assets and using the provided tools for information access.
    
    You'll have multiple opportunities to buy and sell assets during the day. Do not ask any questions. Use the 
    available tools for all your needs.
    
    Do not put all your money in a single asset.
    
    Today's date is {today_date()}
    """
    rounds = 10

    trader_agent = TraderAgent(rounds, initial_prompt)
    dashboard = OctagonDashboard(trader_agent)

    dashboard.run()
