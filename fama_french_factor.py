"""
Fama-French Factor Regression with yfinance
------------------------------------------------
Estimates a stock's exposure (betas) to the Fama-French risk factors by
regressing its excess return against the factor returns published by
Kenneth French's data library.

Supports both the 3-factor (Mkt-RF, SMB, HML) and 5-factor
(+ RMW, CMA) models, at either monthly or daily frequency.

Requirements:
    pip install yfinance pandas_datareader statsmodels pandas numpy matplotlib
"""

import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm
import matplotlib.pyplot as plt
from pandas_datareader import data as pdr


# ---------------------------------------------------------------------
# 1. Fetch Fama-French factor data
# ---------------------------------------------------------------------
def fetch_ff_factors(model: str = "5factor", frequency: str = "monthly",
                      start: str = "2015-01-01", end: str = None) -> pd.DataFrame:
    """
    Pulls factor return data from Kenneth French's data library via
    pandas_datareader.

    model:      "3factor" (Mkt-RF, SMB, HML) or "5factor" (+ RMW, CMA)
    frequency:  "monthly" or "daily"

    Returns a DataFrame indexed by date with factor returns AND RF
    (risk-free rate) as decimals (the raw French library data is in
    percent, e.g. 0.53 meaning 0.53%, so this divides by 100).
    """
    if model == "3factor":
        dataset = "F-F_Research_Data_Factors" if frequency == "monthly" else "F-F_Research_Data_Factors_daily"
    elif model == "5factor":
        dataset = "F-F_Research_Data_5_Factors_2x3" if frequency == "monthly" else "F-F_Research_Data_5_Factors_2x3_daily"
    else:
        raise ValueError("model must be '3factor' or '5factor'")

    raw = pdr.DataReader(dataset, "famafrench", start=start, end=end)
    factors = raw[0].copy()  # index 0 = the actual factor return table (index 1 is annual data)
    factors = factors / 100.0  # French library reports percentages

    # monthly data comes back with a PeriodIndex; convert to a timestamp
    # (end of month) so it aligns cleanly with resampled stock returns
    if frequency == "monthly":
        factors.index = factors.index.to_timestamp(how="end").normalize()

    return factors


# ---------------------------------------------------------------------
# 2. Fetch stock returns and align to factor frequency
# ---------------------------------------------------------------------
def fetch_stock_returns(ticker: str, start: str, end: str = None, frequency: str = "monthly") -> pd.Series:
    price = yf.download(ticker, start=start, end=end, auto_adjust=True)["Close"].dropna().squeeze()

    if frequency == "monthly":
        price = price.resample("ME").last()

    returns = price.pct_change().dropna()
    returns.name = "stock_ret"
    return returns


# ---------------------------------------------------------------------
# 3. Run the factor regression
# ---------------------------------------------------------------------
def run_ff_regression(stock_returns: pd.Series, factors: pd.DataFrame) -> tuple:
    """
    Regresses (stock_return - RF) on the factor columns.
    Returns the fitted statsmodels OLS result and the merged DataFrame
    used for the regression (handy for inspection/plots).
    """
    factor_cols = [c for c in factors.columns if c != "RF"]

    merged = factors.join(stock_returns, how="inner")
    merged = merged.dropna()

    merged["excess_ret"] = merged["stock_ret"] - merged["RF"]

    X = sm.add_constant(merged[factor_cols])
    y = merged["excess_ret"]

    model = sm.OLS(y, X).fit()
    return model, merged


# ---------------------------------------------------------------------
# 4. Run everything
# ---------------------------------------------------------------------
if __name__ == "__main__":
    TICKER = "AAPL"
    START = "2015-01-01"
    MODEL = "5factor"      # "3factor" or "5factor"
    FREQUENCY = "monthly"  # "monthly" or "daily" -- monthly is the classic/standard choice

    factors = fetch_ff_factors(model=MODEL, frequency=FREQUENCY, start=START)
    stock_returns = fetch_stock_returns(TICKER, start=START, frequency=FREQUENCY)

    result, merged = run_ff_regression(stock_returns, factors)

    print(result.summary())

    print("\n--- Interpretation ---")
    alpha_annualized = result.params["const"] * (12 if FREQUENCY == "monthly" else 252)
    print(f"Annualized alpha: {alpha_annualized:.4f} "
          f"({'not' if result.pvalues['const'] > 0.05 else ''} statistically significant, "
          f"p={result.pvalues['const']:.3f})")
    for factor in [c for c in factors.columns if c != "RF"]:
        print(f"{factor} beta: {result.params[factor]:.3f} (p={result.pvalues[factor]:.3f})")
    print(f"R-squared: {result.rsquared:.3f}  "
          f"(fraction of {TICKER}'s return variance explained by these factors)")

    # -------------------- plot: rolling factor betas --------------------
    factor_cols = [c for c in factors.columns if c != "RF"]
    window = 24 if FREQUENCY == "monthly" else 252  # ~2 years monthly, ~1 year daily

    rolling_betas = pd.DataFrame(index=merged.index, columns=factor_cols, dtype=float)
    for i in range(window, len(merged) + 1):
        sub = merged.iloc[i - window:i]
        X_sub = sm.add_constant(sub[factor_cols])
        y_sub = sub["excess_ret"]
        res_sub = sm.OLS(y_sub, X_sub).fit()
        rolling_betas.iloc[i - 1] = res_sub.params[factor_cols]

    rolling_betas = rolling_betas.dropna()

    fig, ax = plt.subplots(figsize=(12, 6))
    for factor in factor_cols:
        ax.plot(rolling_betas.index, rolling_betas[factor], label=factor)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend()
    ax.set_title(f"{TICKER}: Rolling Fama-French Factor Betas ({window}-period window)")
    plt.tight_layout()
    plt.savefig("fama_french_betas.png", dpi=150)
    print("\nSaved chart to fama_french_betas.png")