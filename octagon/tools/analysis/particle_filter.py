"""
Particle Filter for Stochastic Volatility (SV) + Forecasting
------------------------------------------------------------------
"""

from datetime import time as dtime

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import t as student_t

MARKET_OPEN = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)

GRANULARITY_CONFIG = {
    # periods_per_year: for annualizing volatility (e.g. exp(h/2) is a
    #   PER-PERIOD std -- multiply by sqrt(periods_per_year) to annualize)
    # max_gap: largest allowed time gap between consecutive bars before a
    #   return is treated as a session-crossing gap (overnight/weekend)
    #   and excluded, rather than a real single-step move
    "1d": {"interval": "1d", "periods_per_year": 252, "max_gap": pd.Timedelta(days=4), "unit": "day"},
    "1h": {"interval": "1h", "periods_per_year": 252 * 24, "max_gap": pd.Timedelta(hours=2), "unit": "hour"},
    "1m": {"interval": "1m", "periods_per_year": 252 * 390, "max_gap": pd.Timedelta(minutes=5), "unit": "minute"},
}

def fetch_returns(ticker: str, granularity: str) -> tuple:
    """
    Returns (returns, price) where returns has session/weekend-crossing
    gaps excluded (their log_return set to NaN and dropped), so a
    16:00->9:30 or Friday->Monday jump in minute data doesn't get treated
    as an ordinary single-step return -- important since that gap would
    otherwise look like a wild volatility spike to the SV model.
    """
    if granularity not in GRANULARITY_CONFIG:
        raise ValueError(f"granularity must be one of {list(GRANULARITY_CONFIG)}")
    cfg = GRANULARITY_CONFIG[granularity]

    if granularity == "1d":
        price = yf.download(ticker, start='', interval="1d",
                             auto_adjust=True, progress=False)["Close"]
    elif granularity == "1h":
        price = yf.download(ticker, period='1y', interval="1h",
                            auto_adjust=True, progress=False)["Close"]
    else:
        price = yf.download(ticker, period='7d', interval="1m",
                             auto_adjust=True, progress=False)["Close"]

    price = price.dropna().squeeze()

    log_price = np.log(price)
    returns = log_price.diff()

    # flag and drop returns that span a session/weekend gap rather than
    # a genuine single-period move
    time_gap = price.index.to_series().diff()
    returns[time_gap > cfg["max_gap"]] = np.nan
    returns = returns.dropna()
    returns.name = "log_return"

    # keep price aligned to the same index as the cleaned returns
    price = price.loc[returns.index[0]:]

    return returns, price

def future_timestamps(last_ts: pd.Timestamp, n: int, granularity: str) -> list:
    if granularity == "1d":
        return list(pd.bdate_range(start=last_ts, periods=n + 1, freq="B")[1:])

    if granularity == '1h':
        time_delta = pd.Timedelta(hours=1)
    else:
        time_delta = pd.Timedelta(minutes=1)

    times = []
    t = last_ts
    for _ in range(n):
        t = t + time_delta
        while t.time() >= MARKET_CLOSE or t.weekday() >= 5:
            next_day = (t.normalize() + pd.offsets.BDay(1)).normalize()
            t = next_day + pd.Timedelta(hours=9, minutes=30)
        times.append(t)
    return times

def calibrate_sv_params(returns: np.ndarray, phi: float = 0.95) -> dict:
    """
    A full maximum-likelihood calibration of an SV model is its own
    involved topic (particle MCMC / SMC^2 are the rigorous approaches).
    This uses the standard "quasi-likelihood" moment estimator instead
    (Harvey, Ruiz & Shephard 1994), which is a well-known shortcut for
    getting sensible starting parameters without a full particle-MCMC fit:

    Take logs of squared returns: X_t = log(r_t^2) = h_t + log(eps_t^2).
    If eps_t ~ N(0,1), then log(eps_t^2) has a known, fixed distribution
    (log of a chi-squared with 1 df) with:
        E[log(eps_t^2)]   ~= -1.2704
        Var[log(eps_t^2)] = pi^2 / 2 ~= 4.9348
    This turns "recover h_t's mean/variance from noisy squared returns"
    into a simple moment-matching problem on X_t:
        mu           = mean(X) - E[log(eps^2)]
        var(h)        = var(X) - Var[log(eps^2)]         (clipped >= 0)
        sigma_eta     = sqrt(var(h) * (1 - phi^2))       (stationary AR(1) variance relation)

    phi: persistence of volatility shocks -- fixed at a typical empirical
         value (0.90-0.98 is typical for daily equity data; higher = vol
         regimes last longer) rather than estimated here, since phi is
         harder to pin down with this simple moment approach.
    """
    r = returns[~np.isnan(returns)]
    X = np.log(r**2 + 1e-12)

    E_LOG_EPS2 = -1.2704   # E[log(chi-squared_1)] for a standard normal shock
    VAR_LOG_EPS2 = (np.pi ** 2) / 2  # ~4.9348

    mu = X.mean() - E_LOG_EPS2
    var_h = max(X.var() - VAR_LOG_EPS2, 1e-4)
    sigma_eta = np.sqrt(var_h * (1 - phi ** 2))

    return {"mu": mu, "phi": phi, "sigma_eta": max(sigma_eta, 0.05)}

def sv_particle_filter(returns: np.ndarray, mu: float, phi: float, sigma_eta: float,
                        n_particles: int = 5000, dof: float = 6.0,
                        resample_threshold: float = 0.5, random_state: int = 42):
    """
    Filters the hidden log-volatility state h_t given observed returns.

    dof: degrees of freedom for the Student-t observation noise (fat
         tails on top of the stochastic volatility itself -- captures
         extra kurtosis beyond what time-varying vol alone explains).

    Returns: filtered_h (posterior mean of h_t at each step),
             filtered_vol (= exp(filtered_h/2), in return-scale units),
             ess_history, and the final particle cloud + weights (for
             forecasting onward from the last observation).
    """
    rng = np.random.default_rng(random_state)
    n = len(returns)

    stationary_std = sigma_eta / np.sqrt(max(1e-8, 1 - phi**2))
    h_particles = rng.normal(mu, stationary_std, n_particles)
    weights = np.ones(n_particles) / n_particles

    filtered_h = np.zeros(n)
    ess_history = np.zeros(n)

    for t in range(n):
        h_particles = mu + phi * (h_particles - mu) + sigma_eta * rng.standard_normal(n_particles)

        vol = np.exp(h_particles / 2)
        likelihood = student_t.pdf(returns[t], df=dof, loc=0, scale=vol)
        weights = weights * likelihood
        weights += 1e-300
        weights /= weights.sum()

        filtered_h[t] = np.sum(h_particles * weights)

        ess = 1.0 / np.sum(weights ** 2)
        ess_history[t] = ess
        if ess < resample_threshold * n_particles:
            idx = rng.choice(n_particles, size=n_particles, p=weights)
            h_particles = h_particles[idx]
            weights = np.ones(n_particles) / n_particles

    filtered_vol = np.exp(filtered_h / 2)
    return filtered_h, filtered_vol, ess_history, h_particles, weights

def estimate_drift(returns: np.ndarray, lookback: int = None) -> float:
    """
    Per-period drift = mean log-return over the trailing `lookback` bars
    (or the full series if lookback is None).

    IMPORTANT CAVEAT: this is just the recent historical average return,
    extrapolated forward unchanged.
    """
    r = returns[~np.isnan(returns)]
    if lookback is not None:
        r = r[-lookback:]
    return float(np.mean(r))

def forecast_price_paths(last_price: float, last_h_particles: np.ndarray, last_weights: np.ndarray,
                          h: int, mu: float, phi: float, sigma_eta: float, dof: float,
                          drift: float = 0.0, random_state: int = 123):
    """
    drift: additive per-period log-return drift added to every simulated
           step (0.0 by default -- the model's native, no-drift behavior).
           With drift=0, the median forecast is provably flat (see the
           earlier discussion: median of a sum of symmetric zero-median
           shocks is exactly zero). With drift != 0, the median shifts
           deterministically as last_price * exp(drift * step) -- this is
           the ONLY thing that changes; the volatility/spread dynamics
           are unaffected by drift.
    """
    rng = np.random.default_rng(random_state)
    n_particles = len(last_h_particles)

    idx = rng.choice(n_particles, size=n_particles, p=last_weights)
    h_state = last_h_particles[idx].copy()
    price_paths = np.full(n_particles, last_price)

    forecast_median = np.zeros(h)
    forecast_q05 = np.zeros(h)
    forecast_q25 = np.zeros(h)
    forecast_q75 = np.zeros(h)
    forecast_q95 = np.zeros(h)
    forecast_vol = np.zeros(h)  # expected volatility path itself, useful on its own

    for i in range(h):
        h_state = mu + phi * (h_state - mu) + sigma_eta * rng.standard_normal(n_particles)
        vol = np.exp(h_state / 2)
        r = drift + vol * rng.standard_t(dof, n_particles)
        price_paths = price_paths * np.exp(r)

        forecast_median[i] = np.median(price_paths)
        forecast_q05[i] = np.percentile(price_paths, 5)
        forecast_q25[i] = np.percentile(price_paths, 25)
        forecast_q75[i] = np.percentile(price_paths, 75)
        forecast_q95[i] = np.percentile(price_paths, 95)
        forecast_vol[i] = vol.mean()

    return {
        "median": forecast_median, "q05": forecast_q05, "q25": forecast_q25,
        "q75": forecast_q75, "q95": forecast_q95, "vol": forecast_vol,
        "paths": price_paths,
    }


def particle_filter_forecast(ticker, granularity):
    horizon = 10
    n_particles = 5000
    dof = 6.0
    phi = 0.95 # volatility persistence -- higher means regimes last longer

    if granularity not in GRANULARITY_CONFIG:
        return f'Invalid granularity: {granularity}'

    cfg = GRANULARITY_CONFIG[granularity]
    periods_per_year = cfg["periods_per_year"]
    unit = cfg["unit"]

    returns, price = fetch_returns(ticker, granularity)
    params = calibrate_sv_params(returns.values, phi)

    formatted_response = (f"Calibrated SV params: mu={params['mu']:.4f} (long-run per-{unit} vol "
          f"~{np.exp(params['mu']/2)*100:.3f}%), phi={params['phi']:.2f}, "
          f"sigma_eta={params['sigma_eta']:.3f}\n\n")

    filtered_h, filtered_vol, ess_history, h_particles, weights = sv_particle_filter(
        returns.values, **params, n_particles=n_particles, dof=dof,
    )

    formatted_response += (f"Mean ESS: {ess_history.mean():.0f} / {n_particles} "
          f"({100 * ess_history.mean() / n_particles:.1f}%)\n")
    formatted_response += f"Current filtered per-{unit} volatility: {filtered_vol[-1] * 100:.3f}%  \n\n"

    last_price = price.values[-1]
    fc = forecast_price_paths(last_price, h_particles, weights, horizon, **params, dof=dof, drift=0.0)

    if granularity == "1d":
        drift_lookback = 390
    elif granularity == "1h":
        drift_lookback = 48
    else:
        drift_lookback = 60

    drift_est = estimate_drift(returns.values, drift_lookback)

    fc_drift = forecast_price_paths(last_price, h_particles, weights, horizon, **params, dof=dof,
                                    drift=drift_est)

    formatted_response += ("NOTE: this is just the recent historical average return extrapolated forward -- "
          "not a discovered edge. Treat the drift-adjusted median as a stated assumption, "
          "not a stronger prediction than the driftless one.\n\n")

    if granularity == '1d':
        date_format = '%Y-%m-%d'
        extra_space = ''
    else:
        date_format = '%Y-%m-%d %H:%M'
        extra_space = '      '

    last_ts = returns.index[-1]
    forecast_times = future_timestamps(last_ts, horizon, granularity)

    formatted_response += f"Last price ({last_ts.strftime(date_format)}): {last_price:.2f}\n"
    formatted_response += (f"Forecast  {extra_space} | median (no drift) | median (with drift) | [5th pct, 95th pct] "
                           f"| Expected volatility\n")
    for i in range(horizon):
        formatted_response += (f"{forecast_times[i].strftime(date_format)} | {fc['median'][i]:.2f}            |"
                               f" {fc_drift['median'][i]:.2f}              |"
              f" [{fc_drift['q05'][i]:.2f}, {fc_drift['q95'][i]:.2f}]    | ~{fc['vol'][i] * 100:.3f}%\n")

    return formatted_response