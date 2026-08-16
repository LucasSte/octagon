"""
HMM Regime Detection with yfinance
--------------------------------------
Fits a Gaussian Hidden Markov Model to an asset's returns (and optionally
volatility) to infer which unobserved "regime" the market is likely in at
each point in time -- e.g. low-vol/trending vs. high-vol/choppy.

The regime labels are then used as a FILTER: only take trend-following
signals in the "good" regime, sit out (or flip strategy) in the "bad" one.

Requirements:
    pip install yfinance numpy pandas matplotlib hmmlearn
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from hmmlearn.hmm import GaussianHMM


# ---------------------------------------------------------------------
# 1. Fetch data and build features
# ---------------------------------------------------------------------
def fetch_and_prepare(ticker: str, start: str, end: str = None, vol_window: int = 10) -> pd.DataFrame:
    price = yf.download(ticker, start=start, end=end, interval='60m', auto_adjust=True)["Close"].dropna().squeeze()

    df = pd.DataFrame({"price": price})
    df["log_return"] = np.log(df["price"]).diff()
    df["volatility"] = df["log_return"].rolling(vol_window).std()

    # flag and null out returns across large time gaps (overnight/weekend)
    time_gap_hours = df.index.to_series().diff().dt.total_seconds() / 3600.0
    df.loc[time_gap_hours > 3.0, "log_return"] = np.nan

    df = df.dropna()
    return df


# ---------------------------------------------------------------------
# 2. Fit the HMM
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# 3. Label regimes by their characteristics (not by arbitrary state index)
# ---------------------------------------------------------------------
def label_regimes(model: GaussianHMM, df: pd.DataFrame, hidden_states: np.ndarray,
                   return_feature_idx: int = 0) -> dict:
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


# ---------------------------------------------------------------------
# 4. Use regime as a filter on a simple trend-following signal
# ---------------------------------------------------------------------
def build_regime_filtered_signal(df: pd.DataFrame, hidden_states: np.ndarray, labels: dict,
                                   fast_window: int = 20, slow_window: int = 50,
                                   allowed_regimes=("bull/low-vol", "bull")) -> pd.DataFrame:
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


# ---------------------------------------------------------------------
# 5. Backtest: compare filtered vs. unfiltered trend-following
# ---------------------------------------------------------------------
def backtest(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ret = df["price"].pct_change()
    df["unfiltered_ret"] = df["raw_signal"].shift(1) * ret
    df["filtered_ret"] = df["filtered_position"].shift(1) * ret
    df["unfiltered_cum"] = (1 + df["unfiltered_ret"]).cumprod() - 1
    df["filtered_cum"] = (1 + df["filtered_ret"]).cumprod() - 1
    return df


# Use always 60d gap
# Inputs: states, ticker, period: 60m or 1d
# ---------------------------------------------------------------------
# 6. Run everything
# ---------------------------------------------------------------------
if __name__ == "__main__":
    TICKER = "EXFY"
    START = "2026-04-01"
    N_STATES = 2

    df = fetch_and_prepare(TICKER, START, vol_window=10)
    model, hidden_states = fit_hmm(df, n_states=N_STATES, n_iter=1000)
    labels = label_regimes(model, df, hidden_states)

    print("Regime label mapping:", labels)
    print("\nFitted regime means [log_return, volatility]:")
    for state, label in labels.items():
        print(f"  {label} (state {state}): mean = {model.means_[state]}")
    print("\nRegime transition matrix (rows=from, cols=to):")
    print(model.transmat_)

    df = build_regime_filtered_signal(df, hidden_states, labels,
                                       fast_window=20, slow_window=50,
                                       allowed_regimes=("bull/low-vol",))
    df = backtest(df)

    print("\n", df[["price", "regime_label", "raw_signal", "filtered_position",
                     "unfiltered_cum", "filtered_cum"]].tail(10))

    # -------------------- plots --------------------
    # fig, axes = plt.subplots(4, 1, figsize=(12, 13), sharex=True)
    #
    # # price colored by regime
    # for state, label in labels.items():
    #     mask = df["regime"] == state
    #     axes[0].scatter(df.index[mask], df["price"][mask], s=4, label=label)
    # axes[0].legend(markerscale=3)
    # axes[0].set_title(f"{TICKER} Price Colored by HMM-Detected Regime")
    #
    # axes[1].plot(df.index, df["log_return"])
    # axes[1].set_title("Log Returns")
    #
    # axes[2].plot(df.index, df["volatility"])
    # axes[2].set_title("Rolling Volatility")
    #
    # axes[3].plot(df.index, df["unfiltered_cum"], label="Trend-following (unfiltered)")
    # axes[3].plot(df.index, df["filtered_cum"], label="Trend-following (regime-filtered)")
    # axes[3].legend()
    # axes[3].set_title("Cumulative Return: Filtered vs. Unfiltered")
    #
    # plt.tight_layout()
    # plt.savefig("hmm_regime_detection.png", dpi=150)
    # print("\nSaved chart to hmm_regime_detection.png")