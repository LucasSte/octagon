import pandas as pd
import yfinance as yf
import numpy as np


def markov_chain_regime(ticker, interval, states):
    if interval not in {'1d', '60m'}:
        return f'Invalid interval: {interval}'

    if states != 2 or states != 3:
        return f'Invalid number of states: {states}'

    price = yf.download(ticker, period='90d', interval=interval, auto_adjust=True)['Close'].dropna()
    df = pd.DataFrame({"price": price})
    df["log_return"] = np.log(df["price"]).diff()
    df["volatility"] = df["log_return"].rolling(10).std()

    # flag and null out returns across large time gaps (overnight/weekend)
    time_gap_hours = df.index.to_series().diff().dt.total_seconds() / 3600.0
    df.loc[time_gap_hours > 3.0, "log_return"] = np.nan

    df = df.dropna()


    formatted_response = ''


    return formatted_response