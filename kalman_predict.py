"""
Kalman Filter Forecasting (Future Value Estimation)
--------------------------------------------------------
Extends the local linear trend fair-value model to project FUTURE prices,
not just estimate the current smoothed level. This works by repeating the
Kalman "predict" step (with no observation update) forward h steps from
the last filtered state -- the trend gets extrapolated linearly, and the
forecast's uncertainty (variance) grows with every step ahead since there's
no new data correcting it.

IMPORTANT CAVEAT: this is an extrapolation of a locally-linear trend, not
a magic predictor. For a pure local-level (no trend) model, this collapses
to a flat, no-drift forecast -- mathematically identical to a naive "today
equals tomorrow" forecast, consistent with the efficient market /
random-walk view of prices. Any apparent predictive edge here comes purely
from the trend term persisting, which is a strong and often wrong
assumption for financial prices over more than a few steps ahead.

Requirements:
    pip install yfinance numpy pandas matplotlib pykalman
"""

# Is this any useful? I can only estimate minutes (variance over 5m is too big, and
# the model takes at least 30 seconds to finish processing).

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from pykalman import KalmanFilter


# ---------------------------------------------------------------------
# 1. Fetch data
# ---------------------------------------------------------------------
def fetch_price(ticker: str, start: str, end: str = None) -> pd.Series:
    data = yf.download(ticker, start=start, end=end, auto_adjust=True)["Close"]
    return data.dropna().squeeze()


# ---------------------------------------------------------------------
# 2. Fit local linear trend model via EM (level + trend state)
# ---------------------------------------------------------------------
def fit_trend_model(price: np.ndarray, n_iter: int = 20):
    F = np.array([[1.0, 1.0],
                  [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])

    kf = KalmanFilter(
        transition_matrices=F,
        observation_matrices=H,
        initial_state_mean=[price[0], 0.0],
        initial_state_covariance=np.eye(2),
        transition_covariance=np.eye(2) * 0.01,
        observation_covariance=1.0,
    )
    kf = kf.em(price, n_iter=n_iter,
               em_vars=["transition_covariance", "observation_covariance"])

    state_means, state_covs = kf.filter(price)
    return kf, state_means, state_covs


# ---------------------------------------------------------------------
# 3. Forecast h steps ahead: predict-only, no observation updates
# ---------------------------------------------------------------------
def forecast_ahead(kf: KalmanFilter, last_mean: np.ndarray, last_cov: np.ndarray, h: int):
    F = kf.transition_matrices
    Q = kf.transition_covariance
    H = kf.observation_matrices

    mean = last_mean.copy()
    cov = last_cov.copy()

    forecast_level = np.zeros(h)
    forecast_std = np.zeros(h)

    for i in range(h):
        mean = F @ mean
        cov = F @ cov @ F.T + Q

        obs_mean = (H @ mean)[0]
        obs_var = (H @ cov @ H.T)[0, 0]

        forecast_level[i] = obs_mean
        forecast_std[i] = np.sqrt(obs_var)

    return forecast_level, forecast_std


# ---------------------------------------------------------------------
# 4. Run everything
# ---------------------------------------------------------------------
if __name__ == "__main__":
    TICKER = "AAPL"
    START = "2022-01-01"
    HORIZON = 20     # number of future bars to forecast
    N_ITER = 20

    price = fetch_price(TICKER, START)
    kf, state_means, state_covs = fit_trend_model(price.values, n_iter=N_ITER)

    level_est = state_means[:, 0]
    trend_est = state_means[:, 1]

    last_mean = state_means[-1]
    last_cov = state_covs[-1]
    forecast_level, forecast_std = forecast_ahead(kf, last_mean, last_cov, HORIZON)

    # build a forward date index (calendar days as a simple placeholder --
    # for daily equities you may want a trading-day calendar instead)
    last_date = price.index[-1]
    forecast_dates = pd.bdate_range(start=last_date, periods=HORIZON + 1, freq="B")[1:]

    print(f"Last observed price ({last_date.date()}): {price.values[-1]:.2f}")
    print(f"Last estimated level: {level_est[-1]:.2f}, estimated trend/day: {trend_est[-1]:.4f}")
    print("\nForecast (first 5 steps):")
    for i in range(min(5, HORIZON)):
        print(f"  {forecast_dates[i].date()}: {forecast_level[i]:.2f} "
              f"+/- {1.96 * forecast_std[i]:.2f} (95% interval)")
    print("...")
    print(f"  {forecast_dates[-1].date()}: {forecast_level[-1]:.2f} "
          f"+/- {1.96 * forecast_std[-1]:.2f} (95% interval)")

    # -------------------- plot --------------------
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(price.index, price.values, label="Observed Price", alpha=0.5)
    ax.plot(price.index, level_est, label="Kalman Filtered Level", linewidth=2)

    ax.plot(forecast_dates, forecast_level, label="Forecast", linewidth=2, color="red")
    ax.fill_between(
        forecast_dates,
        forecast_level - 1.96 * forecast_std,
        forecast_level + 1.96 * forecast_std,
        color="red", alpha=0.15, label="95% forecast interval",
    )

    ax.legend()
    ax.set_title(f"{TICKER}: Kalman Filtered Level + {HORIZON}-Step Forecast\n"
                 f"(Local Linear Trend Model)")
    plt.tight_layout()
    plt.savefig("kalman_forecast.png", dpi=150)
    print("\nSaved chart to kalman_forecast.png")