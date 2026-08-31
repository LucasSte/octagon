import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from pandas_datareader import data as pdr


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

    # IMPORTANT: the French library's raw CSVs frequently have leading/
    # trailing whitespace in column headers (e.g. "RF " or " Mkt-RF"),
    # especially in the DAILY files. Left unstripped, this causes silent
    # KeyErrors later (e.g. factors["RF"] not found) or an empty column
    # selection. Always strip before using the column names downstream.
    factors.columns = factors.columns.str.strip()

    factors = factors / 100.0  # French library reports percentages

    # monthly data comes back with a PeriodIndex; convert to a timestamp
    # (end of month) so it aligns cleanly with resampled stock returns.
    # Daily data is already a DatetimeIndex.
    if isinstance(factors.index, pd.PeriodIndex):
        factors.index = factors.index.to_timestamp(how="end").normalize()

    # normalize to plain dates with no time-of-day/timezone component --
    # yfinance's index can be tz-naive or tz-aware depending on version,
    # and mismatched tz-awareness between the two DataFrames makes
    # DataFrame.join silently return zero overlapping rows (or raise,
    # depending on pandas version) instead of erroring clearly.
    #
    # By this point factors.index is guaranteed to be a DatetimeIndex
    # (either it always was, for daily data, or it was just converted
    # above), so .tz is always a valid attribute here.
    if factors.index.tz is not None:
        factors.index = factors.index.tz_localize(None)
    factors.index = factors.index.normalize()

    return factors

def fetch_stock_returns(ticker: str, start: str, end: str = None, frequency: str = "monthly") -> pd.Series:
    price = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)["Close"].dropna().squeeze()

    if frequency == "monthly":
        price = price.resample("ME").last()

    returns = price.pct_change().dropna()
    returns.name = "stock_ret"

    # match the same tz-naive, midnight-normalized index used for factors
    if returns.index.tz is not None:
        returns.index = returns.index.tz_localize(None)
    returns.index = returns.index.normalize()

    return returns

def run_ff_regression(stock_returns: pd.Series, factors: pd.DataFrame,
                       hac: bool = False, hac_maxlags: int = None) -> tuple:
    """
    Regresses (stock_return - RF) on the factor columns.

    hac: if True, uses Newey-West (HAC) standard errors instead of plain
         OLS standard errors. This matters most for DAILY data, where
         residuals are typically autocorrelated (today's leftover return
         is correlated with yesterday's), which makes plain OLS standard
         errors understate the true uncertainty -- t-stats and p-values
         look more significant than they really are. Monthly data has
         much weaker autocorrelation, but HAC doesn't hurt there either.

    hac_maxlags: number of lags to account for in the HAC correction.
         If None, defaults to a common rule of thumb: 5 lags for monthly
         data, and floor(4*(n/100)^(2/9)) (the standard Newey-West
         auto-lag heuristic) for daily data.

    Returns the fitted statsmodels OLS result and the merged DataFrame
    used for the regression (handy for inspection/plots).
    """
    factor_cols = [c for c in factors.columns if c != "RF"]

    merged = factors.join(stock_returns, how="inner")
    merged = merged.dropna()

    if len(merged) == 0:
        raise ValueError(
            "No overlapping dates between factor data and stock returns after "
            "the join -- check that both date ranges actually overlap, and "
            "that both indexes were normalized to the same tz/time-of-day."
        )

    merged["excess_ret"] = merged["stock_ret"] - merged["RF"]

    X = sm.add_constant(merged[factor_cols])
    y = merged["excess_ret"]

    if hac:
        if hac_maxlags is None:
            n = len(merged)
            hac_maxlags = max(1, int(4 * (n / 100) ** (2 / 9)))
        model = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_maxlags})
    else:
        model = sm.OLS(y, X).fit()

    return model, merged


def fama_french_factor(ticker, model, frequency):
    """
    Returns a table containing the results of the fama french factor calculation
    :param ticker: Ticker
    :param model: 3factor or 5factor
    :param frequency: monthly or daily
    :return:
    """
    if frequency == 'daily':
        window_years = 1
        fetch_years_back = 2
    elif frequency == 'monthly':
        window_years = 5
        fetch_years_back = 8
    else:
        return f'Invalid frequency: {frequency}'

    fetch_start = (pd.Timestamp.today() - pd.DateOffset(years=fetch_years_back)).strftime("%Y-%m-%d")

    if model != '3factor' and model != '5factor':
        return f'Invalid model: {model}'

    factors = fetch_ff_factors(model=model, frequency=frequency, start=fetch_start)
    stock_returns = fetch_stock_returns(ticker, start=fetch_start, frequency=frequency)
    if ((frequency == 'daily' and len(stock_returns) < fetch_years_back*240)
            or (frequency == 'monthly' and len(stock_returns) < fetch_years_back*12)):
        return f'Fama french factor unavailable for ticker {ticker}'

    use_hac = True if frequency == 'daily' else False
    result_full, merged = run_ff_regression(stock_returns, factors, hac=use_hac)
    window = window_years * (12 if frequency == "monthly" else 252)

    windowed = merged.tail(window)
    X_window = sm.add_constant(windowed[[c for c in factors.columns if c != "RF"]])
    y_window = windowed["excess_ret"]

    if use_hac:
        maxlags = max(1, int(4 * (window / 100) ** (2 / 9)))
        result = sm.OLS(y_window, X_window).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    else:
        result = sm.OLS(y_window, X_window).fit()

    formatted_response = ''
    formatted_response += (f"Primary regression window: {windowed.index[0].date()} to {windowed.index[-1].date()} "
                           f"({len(windowed)} {'months' if frequency == 'monthly' else 'days'})\n")

    formatted_response += str(result.summary())

    if use_hac:
        formatted_response += (f"\n(Standard errors above are Newey-West/HAC-corrected, "
              f"maxlags={result.cov_kwds['maxlags']})\n")

    formatted_response += "\n\n--- Interpretation ---\n"
    alpha_annualized = result.params["const"] * (12 if frequency == "monthly" else 252)

    formatted_response += (f"Annualized alpha: {alpha_annualized:.4f} "
          f"({'not' if result.pvalues['const'] > 0.05 else ''} statistically significant, "
          f"p={result.pvalues['const']:.3f})\n")

    for factor in [c for c in factors.columns if c != "RF"]:
        formatted_response+= f"{factor} beta: {result.params[factor]:.3f} (p={result.pvalues[factor]:.3f})\n"
    formatted_response += (f"R-squared: {result.rsquared:.3f}  "
          f"(fraction of {ticker}'s return variance explained by these factors)")

    return formatted_response