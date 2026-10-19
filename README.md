# Octagon

> Leave your agent trading on your computer while you work

Octagon is your agentic trader. It monitors the market and trades on your behalf.
Differently from other available tools, octagon carries a set of tools that helps the agent to better 
analyze and understand the market, and act like a quantitative trader.

Besides basic market and historical data, Octagon calculates the Fama French Factors, Kalman fair values,
Markov Chain regimes, and estimates short term prices with particle filters. Additionally, it analyzes
market sentiment from the web.

<div align="center">
<img src="assets/agent_running.png" width="80%" alt="img"/>
</div>

## Usage

Octagon offers a straightforward terminal interface for easy agent observability. To start it,
run the following:

```
git clone https://github.com/LucasSte/octagon
cd octagon
pip install .
python3 octagon_trade.py
```

The project has been conceived to run with local models, so you can have unlimited tokens, and run it 
during the entire trading hours. It works with OpenAI API compatible inference engines, like LMStudio or llama.cpp. 

Check [octagon_trade.py](octagon_trade.py) for the initial prompt, the endpoint and the model name.
If you wish not to execute a local model, set up the environment variable `OPENAI_API_KEY`.

Since models do not have infinite context window, you also define in [octagon_trade.py](octagon_trade.py) the
number of iterations the agent runs for. Before finishing, it writes down session summary in `memory.json` 
and loads it again for the next session.

Use `save` and `load` to save and restore the trading portfolio between sessions, and type `help` for all the
available commands.

### Adding new tools

Trading strategies may vary between people. If you want to customize trading decisions and data sources, the best way 
to do so is to add a new tool. Follow these steps to include new functionality:

1. If your new tool does is not one of the default ones (see `register_defaut_tools`
   in [trader_agent.py](octagon/agent/trader_agent.py)), derive the `ToolDefinition` (see 
   [tool_definition.py](octagon/tools/tool_definition.py)) class with your new functionality.
2. Register your tool by doing `octangon_agent.register_tool(MyAwesmomeTool())`.
3. If your tool requires a state to be stored between calls, add it to the derived `ToolDefinition` class and register
   on the agent an active instance of it: `octagon_agent.register_tool(instace_of_tool)`.
4. Make sure to follow the correct formats for the tool description and dispatch dictionary. See 
   [metadata.py](octagon/tools/analysis/metadata.py) for an example.

## Benchmarks

We ran the trading benchmark between September 14 and September 18, 2026, with an extra test on Monday the following 
week. The repository state was commit
[96d8c6a](https://github.com/LucasSte/octagon/commit/96d8c6a985ff33052ef64c109ac51f0ed12a65e2). The assets available
for the agent are described in [assets.py](https://github.com/LucasSte/octagon/blob/103c5f42ef7177de064b066ce99ed2abb5d8c9e3/octagon/tools/assets/available_assets.py#L10-L27). For the LLM, we used LMStudio with Qwen3.8-27b 6-bit running on a 
MacBook Pro M3 Max with 48 GB of RAM.

The memory recorded and the portfolio state for each trading session (two to four sessions every day) are available in 
the [benchmarks](benchmarks) folder. It contains a screenshot of the portfolio value on market close for each day.

The results are in the table below. The agent started with $10,000 on Monday, September 14.

| Date           | Portfolio value | Day change      | Accumulated gain |
|----------------|-----------------|-----------------|------------------|
| Start          | $10,000.00      | -               | -                |
| September 14   | $10,068.41      | +68.41 (0.68%)  | +68.41 (0.68%)   |
| September 15   | $10,053.53      | -14.88 (-0.14%) | +53.53 (0.53%)   |
| September 16   | $10,029.30      | -24.23 (-0.24%) | +24.23 (0.24%)   |
| September 17   | $10,239.95      | +210.65 (2.10%) | +239.95 (2.39%)  |
| September 18   | $10,176.02      | -63.93 (-0.62%) | +176.02 (1.76%)  |
| Weekend        | -               | -               | -                |
| September 21 * | $10,352.49      | +176.47 (1.73%) | +352.49 (3.32%)  |

Footnote: The repository state on September 21st was updated to [6e2ccef](https://github.com/LucasSte/octagon/commit/6e2ccef2550a4680b001f67257782ecd45c4d07a).

To make sense of these numbers, the table below shows a comparison for the accumulated gain between the S&P 500 IVV 
ETF and Octagon.

| Date           | IVV Accumulated gain | Octagon accumulated gain |
|----------------|----------------------|--------------------------|
| September 14   | -                    | -                        |
| September 15   | -0.7%                | +0.53%                   |
| September 16   | -1.17%               | +0.24%                   |
| September 17   | -0.05%               | +2.39%                   |
| September 18   | +0.05%               | +1.76%                   |
| Weekend        | -                    | -                        |
| September 21 * | +1.61%               | +3.32%                   |

## Leaderboard

Changes in the tooling, initial prompt and available assets will impact the agent's performance. If you've found a
configuration that outperforms the leaderboard below, submit a PR and with your changes, and update the 
leaderboard.

| User      | Date         | Day Gain | Commit                                                                                         |
|-----------|--------------|----------|------------------------------------------------------------------------------------------------|
| @LucasSte | September 17 | +2.10%   | [96d8c6a](https://github.com/LucasSte/octagon/commit/96d8c6a985ff33052ef64c109ac51f0ed12a65e2) |

## Feature backlog

There are some ideas for the future of this project. They are going to be implemented soon, but
not necessarily in this order.

* Allow the agent to access curated news about the trading stock. More information, like the announcement of earnings, 
  may influence trading decisions.
* Connect to real trading venues. One option might be connecting to blockchains, like Solana or Hyperliquid, which 
  allows the agent to trade 24/7.
* Ability to talk to the agent in the terminal interface.
* Simulate trading with historical data.

Feature requests and bug fixes are welcomed! If you want anything else not in this list, or if you've found a bug, 
please file an issue. Also, open an issue if you want any of these backlog items prioritized.

## Limitations

1. This project came to life as a research and side project. Returns are not guaranteed, so use it at your own risk.
2. Although the agent uses real market data, all trades, balances and portfolio are simulated, so no money 
   is actually spent. If someone wishes a connection to a trading venue, the easiest way is to modify the `Portfolio` 
   class in [portfolio.py](octagon/tools/assets/portfolio.py).
