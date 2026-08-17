import pandas as pd
import yfinance as yf
from pykalman import KalmanFilter
import numpy as np

def fit_local_level_em(price, n_iter: int = 20, em_vars=None):
    """
    Local level model with EM-estimated parameters.

    Fits a local level model:
        fair_value_t = fair_value_(t-1) + w,   w ~ N(0, Q)
        price_t      = fair_value_t + v,       v ~ N(0, R)

    Q and R are estimated via EM instead of being hand-set.

    em_vars: which parameters to let EM estimate. Defaults to both noise
             covariances. You can also let EM estimate the initial state
             mean/covariance, but constraining those to the first observed
             price tends to be more stable with financial data.
    """

    if em_vars is None:
        em_vars = ["transition_covariance", "observation_covariance"]

    kf = KalmanFilter(
        transition_matrices=[1.0],
        observation_matrices=[1.0],
        initial_state_mean=price[0],
        initial_state_covariance=1.0,
        transition_covariance=0.01,
        observation_covariance=1.0,
    )

    kf = kf.em(price, n_iter=n_iter, em_vars=em_vars)

    state_means, state_covs = kf.filter(price)

    return kf, state_means[:, 0]

def fit_local_linear_trend_em(price, n_iter: int = 20):
    """
    Local linear trend model with EM-estimated parameters

    Fits a local linear trend model:
        level_t = level_(t-1) + trend_(t-1) + w_level
        trend_t = trend_(t-1) + w_trend
        price_t = level_t + v

    transition_covariance is a 2x2 matrix (level noise, trend noise),
    estimated jointly via EM.
    """
    transition_matrix = np.array([[1.0, 1.0],
                                   [0.0, 1.0]])
    observation_matrix = np.array([[1.0, 0.0]])

    kf = KalmanFilter(
        transition_matrices=transition_matrix,
        observation_matrices=observation_matrix,
        initial_state_mean=[price[0], 0.0],
        initial_state_covariance=np.eye(2),
        transition_covariance=np.eye(2) * 0.01,
        observation_covariance=1.0,
    )

    kf = kf.em(price, n_iter=n_iter,
               em_vars=["transition_covariance", "observation_covariance"])

    state_means, state_covs = kf.filter(price)

    return kf, state_means[:, 0], state_means[:, 1]


def build_signals(df: pd.DataFrame, entry_z: float = 1.5, exit_z: float = 0.3, z_window: int = 20) -> pd.DataFrame:
    df = df.copy()
    df["deviation"] = df["price"] - df["fair_value"]

    roll_mean = df["deviation"].rolling(z_window).mean()
    roll_std = df["deviation"].rolling(z_window).std()
    df["zscore"] = (df["deviation"] - roll_mean) / roll_std

    df["signal"] = 0
    df.loc[df["zscore"] < -entry_z, "signal"] = 1
    df.loc[df["zscore"] > entry_z, "signal"] = -1
    df.loc[df["zscore"].abs() < exit_z, "signal"] = 0

    df["position"] = df["signal"].replace(0, np.nan)
    df["position"] = df["position"].ffill().fillna(0)
    df.loc[df["zscore"].abs() < exit_z, "position"] = 0
    df["position"] = df["position"].ffill().fillna(0)

    return df


def backtest(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    price_ret = df["price"].pct_change()
    df["strategy_ret"] = df["position"].shift(1) * price_ret
    df["cum_ret"] = (1 + df["strategy_ret"]).cumprod() - 1
    return df


def kalman_fair_value(ticker, period, interval, method):
    """
    Calculates the Kalman fair value, using either a trend or a linear model with EM-estimated parameters.
    :param ticker: Ticker
    :param period: 5d, 6d, 7d, 8d, 9d or 10d
    :param interval: 1d, 60m, 30m, 15m
    :param method: level or trend
    :return: The kalman fair value for the last 15 entries beginning from now.
    """
    if interval not in {'1d', '60m', '30m', '15m'}:
        return f'Invalid interval: {interval}'

    if period not in {'5d', '6d', '7d', '8d', '9d', '10d'}:
        return f'Invalid period: {period}'

    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)["Close"]
    data = data.dropna().squeeze()

    formatted_response = ''

    if method == 'level':
        kf, fair_value = fit_local_level_em(data.values, n_iter=20)
        trend = None
    else:
        kf, fair_value, trend = fit_local_linear_trend_em(data.values, n_iter=20)

    formatted_response += f'EM-estimated transition covariance: {kf.transition_covariance}\n'
    formatted_response += f'EM-estimated observation covariance: {kf.observation_covariance}\n\n'

    df_reset = data.reset_index()
    if 'Date' in df_reset:
        date_and_time = df_reset['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        date_and_time = df_reset['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    df = pd.DataFrame({
        'datetime': date_and_time,
        'price': data.values,
        "fair_value": fair_value
    })

    if trend is not None:
        df['trend'] = trend

    df = build_signals(df, entry_z=1.5, exit_z=0.3, z_window=20)
    df = backtest(df)

    # Add user-friendly labels
    position_labels = {
        1: "Long",
        0: "Flat",
        -1: "Short",
    }
    df["position"] = df["position"].map(position_labels)
    df.rename(columns={'fair_value': 'fair value'}, inplace=True)

    filtered = df[['datetime', 'price', 'fair value', 'position']].tail(15)

    formatted_response += filtered.to_string(index=False)

    return formatted_response
