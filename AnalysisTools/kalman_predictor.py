import yfinance as yf
import numpy as np
from pykalman import KalmanFilter

def fit_trend_model(price: np.ndarray, n_iter: int = 20):
    """
    Fit local linear trend model via EM (level + trend state)
    """
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

def kalman_predictor(ticker):
    horizon = 10

    price = yf.download(ticker, period='2d', interval='1m', auto_adjust=True)["Close"].dropna().squeeze()
    kf, state_means, state_covs = fit_trend_model(price.values, n_iter=20)

    level_est = state_means[:, 0]
    trend_est = state_means[:, 1]
    last_mean = state_means[-1]
    last_cov = state_covs[-1]
    forecast_level, forecast_std = forecast_ahead(kf, last_mean, last_cov, horizon)
    last_date = price.index[-1]

    formatted_response = f"Last observed price ({last_date}): {price.values[-1]:.2f}\n"
    formatted_response += f"Last estimated level: {level_est[-1]:.2f}, estimated trend/day: {trend_est[-1]:.4f}\n\n"

    formatted_response += "10 minutes forecast:\n"
    for i in range(horizon):
        formatted_response += f'+{i+1} minutes: {forecast_level[i]:.2f} +/- {1.96 * forecast_std[i]:.2f} (95% interval)\n'

    return formatted_response


