import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM


def fit_hmm(df: pd.DataFrame, n_states: int = 2, features=("log_return", "volatility"),
            n_iter: int = 1000, random_state: int = 42):
    """
    Fits a GaussianHMM on the chosen feature columns.

    n_states: number of hidden regimes to detect. 2 is the classic
              "calm vs. stressed" split. 3 is common for bull/choppy/bear.
    features: which columns to feed the model. Using both return AND
              volatility (not just return) helps the model separate
              regimes more cleanly than return alone.
    """
    X = df[list(features)].values

    model = GaussianHMM(
        n_components=n_states,
        covariance_type="full",   # lets each regime have its own return/vol correlation structure
        n_iter=n_iter,
        random_state=random_state,
    )
    model.fit(X)

    hidden_states = model.predict(X)
    return model, hidden_states

def label_regimes(model: GaussianHMM, return_feature_idx: int = 0) -> dict:
    """
    hmmlearn assigns state numbers (0, 1, 2...) arbitrarily -- they carry
    no inherent meaning. This maps each state number to a human-readable
    label based on its fitted mean return, so "state 0" isn't always
    the bull regime by coincidence.
    """
    means = model.means_[:, return_feature_idx]
    order = np.argsort(means)  # ascending: worst return regime first

    if len(order) == 2:
        labels = {order[0]: "bear/high-vol", order[1]: "bull/low-vol"}
    elif len(order) == 3:
        labels = {order[0]: "bear", order[1]: "choppy", order[2]: "bull"}
    else:
        labels = {state: f"regime_{rank}" for rank, state in enumerate(order)}

    return labels

def build_regime_filtered_signal(df: pd.DataFrame, hidden_states: np.ndarray, labels: dict,
                                   fast_window: int = 20, slow_window: int = 50,
                                   allowed_regimes=("bull/low-vol", "bull")) -> pd.DataFrame:
    """
    Use regime as a filter on a simple trend-following signal
    """
    df = df.copy()
    df["regime"] = hidden_states
    df["regime_label"] = df["regime"].map(labels)

    # simple moving-average crossover as the base trend signal
    df["fast_ma"] = df["price"].rolling(fast_window).mean()
    df["slow_ma"] = df["price"].rolling(slow_window).mean()
    df["raw_signal"] = np.where(df["fast_ma"] > df["slow_ma"], 1, -1)

    # only take the trend signal when the HMM says we're in an allowed regime;
    # otherwise stay flat
    df["filtered_position"] = np.where(df["regime_label"].isin(allowed_regimes), df["raw_signal"], 0)

    return df

def backtest(df: pd.DataFrame) -> pd.DataFrame:
    """
    compare filtered vs. unfiltered trend-following
    :param df:
    :return:
    """
    df = df.copy()
    ret = df["price"].pct_change()
    df["unfiltered_ret"] = df["raw_signal"].shift(1) * ret
    df["filtered_ret"] = df["filtered_position"].shift(1) * ret
    df["unfiltered_cum"] = (1 + df["unfiltered_ret"]).cumprod() - 1
    df["filtered_cum"] = (1 + df["filtered_ret"]).cumprod() - 1
    return df

def markov_chain_regime(ticker, states):
    # if interval not in {'1d', '60m'}:
    #     return f'Invalid interval: {interval}'

    if states != 2 and states != 3:
        return f'Invalid number of states: {states}'

    # if interval == '1d':
    #     period = '360d'
    # else:
    #     period = '180d'

    price = yf.download(ticker, period='360d', interval='1d', auto_adjust=True, progress=False)["Close"].dropna().squeeze()
    df = pd.DataFrame({"price": price})
    df["log_return"] = np.log(df["price"]).diff()
    df["volatility"] = df["log_return"].rolling(10).std()

    # flag and null out returns across large time gaps (overnight/weekend)
    # if interval == '60m':
    #     time_gap_hours = df.index.to_series().diff().dt.total_seconds() / 3600.0
    #     df.loc[time_gap_hours > 3.0, "log_return"] = np.nan

    df = df.dropna()
    model, hidden_states = fit_hmm(df, n_states=states, n_iter=1000)
    labels = label_regimes(model)

    df = build_regime_filtered_signal(df, hidden_states, labels,
                                      fast_window=20, slow_window=50)
    df = backtest(df)

    formatted_response = "\nFitted regime means [log_return, volatility]:\n"
    for state, label in labels.items():
        formatted_response += f"  {label} (state {state}): mean = {model.means_[state]}\n"

    formatted_response += '\n'
    selected_entries = df[["price", "regime_label", "raw_signal",
                           "filtered_position", "unfiltered_cum", "filtered_cum"]].tail(15)

    formatted_response +=  selected_entries.to_string()

    return formatted_response