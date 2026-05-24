from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUTPUT_DIR = BASE / "output"

START_DATE = "2020-01-01"
END_DATE = "2024-12-31"
LOOKBACK_DAYS = 50
MIN_LOOKBACK_DAYS = 30
TAIL_QUANTILE = 0.10
HOLDING_DAYS = 20
FORWARD_HORIZONS = [1, 5, 10, 20]

DATA_COLUMNS = [
    "Stkcd",
    "Trddt",
    "Clsprc",
    "Dnshrtrd",
    "Dsmvosd",
    "Dretwd",
]


def list_daily_files():
    files = sorted(
        DATA_DIR.glob("TRD_Dalyr*.csv"),
        key=lambda path: (len(path.stem), path.stem),
    )
    if not files:
        raise FileNotFoundError(f"No TRD_Dalyr csv files found in {DATA_DIR}")
    return files


def load_daily_data():
    frames = []
    for path in list_daily_files():
        df = pd.read_csv(path, usecols=DATA_COLUMNS, dtype={"Stkcd": "string"})
        frames.append(df)

    data = pd.concat(frames, ignore_index=True)
    data = data.rename(
        columns={
            "Stkcd": "stock",
            "Trddt": "date",
            "Clsprc": "close",
            "Dnshrtrd": "shares_traded",
            "Dsmvosd": "float_mkt_cap_thousand",
            "Dretwd": "ret",
        }
    )
    data["date"] = pd.to_datetime(data["date"])
    data = data[(data["date"] >= START_DATE) & (data["date"] <= END_DATE)].copy()

    numeric_cols = ["close", "shares_traded", "float_mkt_cap_thousand", "ret"]
    data[numeric_cols] = data[numeric_cols].apply(pd.to_numeric, errors="coerce")
    data = data.dropna(subset=["stock", "date", "close", "shares_traded", "ret"])
    data = data[data["close"] > 0]
    data = data.drop_duplicates(subset=["stock", "date"])
    data = data.sort_values(["stock", "date"]).reset_index(drop=True)
    return data


def add_volume_signal(data):
    data = data.copy()

    float_mkt_cap = data["float_mkt_cap_thousand"] * 1000
    data["turnover"] = data["shares_traded"] * data["close"] / float_mkt_cap
    data.loc[~np.isfinite(data["turnover"]) | (data["turnover"] <= 0), "turnover"] = (
        np.nan
    )
    data["log_turnover"] = np.log(data["turnover"])

    grouped = data.groupby("stock", group_keys=False)
    rolling_mean = grouped["log_turnover"].transform(
        lambda x: (
            x.shift(1).rolling(LOOKBACK_DAYS, min_periods=MIN_LOOKBACK_DAYS).mean()
        )
    )
    rolling_std = grouped["log_turnover"].transform(
        lambda x: x.shift(1).rolling(LOOKBACK_DAYS, min_periods=MIN_LOOKBACK_DAYS).std()
    )
    data["volume_shock"] = (data["log_turnover"] - rolling_mean) / rolling_std
    data.loc[~np.isfinite(data["volume_shock"]), "volume_shock"] = np.nan
    return data


def add_forward_returns(data):
    data = data.copy()
    grouped = data.groupby("stock", group_keys=False)

    for horizon in FORWARD_HORIZONS:
        gross = grouped["ret"].transform(lambda x: future_compound_return(x, horizon))
        data[f"fwd_ret_{horizon}d"] = gross - 1

    return data


def future_compound_return(returns, horizon):
    future_gross = (1 + returns).shift(-1)
    return (
        future_gross.iloc[::-1]
        .rolling(horizon, min_periods=horizon)
        .apply(np.prod, raw=True)
        .iloc[::-1]
    )


def assign_volume_portfolios(data):
    valid = data.dropna(subset=["volume_shock", "ret"]).copy()
    valid["shock_rank"] = valid.groupby("date")["volume_shock"].rank(
        pct=True, method="first"
    )
    valid["portfolio"] = "Middle"
    valid.loc[valid["shock_rank"] <= TAIL_QUANTILE, "portfolio"] = "Low volume"
    valid.loc[valid["shock_rank"] >= 1 - TAIL_QUANTILE, "portfolio"] = "High volume"
    return valid


def summarize_forward_returns(portfolios):
    rows = []
    for horizon in FORWARD_HORIZONS:
        col = f"fwd_ret_{horizon}d"
        subset = portfolios.dropna(subset=[col])
        daily = subset.groupby(["date", "portfolio"])[col].mean().unstack()
        daily["High-Low"] = daily["High volume"] - daily["Low volume"]

        for name in ["Low volume", "Middle", "High volume", "High-Low"]:
            series = daily[name].dropna()
            rows.append(
                {
                    "horizon_days": horizon,
                    "portfolio": name,
                    "mean_return": series.mean(),
                    "t_stat": series.mean() / series.std(ddof=1) * np.sqrt(len(series)),
                    "std": series.std(ddof=1),
                    "n_days": len(series),
                }
            )

    return pd.DataFrame(rows)


def build_overlapping_holding_returns(portfolios):
    signal = portfolios[
        portfolios["portfolio"].isin(["Low volume", "High volume"])
    ].copy()
    signal["position"] = np.where(signal["portfolio"] == "High volume", 1.0, -1.0)

    stock_date = signal[["stock", "date", "position"]].merge(
        portfolios[["stock", "date", "ret"]],
        on=["stock", "date"],
        how="right",
    )
    stock_date = stock_date.sort_values(["stock", "date"])
    stock_date["active_position"] = stock_date.groupby("stock")["position"].transform(
        lambda x: x.shift(1).rolling(HOLDING_DAYS, min_periods=1).mean()
    )
    active = stock_date.dropna(subset=["active_position", "ret"]).copy()

    daily_strategy = active.groupby("date").apply(
        lambda x: pd.Series(
            {
                "long_short_return": (x["active_position"] * x["ret"]).mean(),
                "gross_exposure": x["active_position"].abs().mean(),
                "n_stocks": x["active_position"].notna().sum(),
            }
        ),
        include_groups=False,
    )
    daily_strategy["cumulative_return"] = (
        1 + daily_strategy["long_short_return"]
    ).cumprod() - 1
    return daily_strategy


def run_market_model(daily_strategy, portfolios):
    market = portfolios.groupby("date")["ret"].mean().rename("market_return")
    data = daily_strategy[["long_short_return"]].merge(
        market, left_index=True, right_index=True, how="inner"
    )
    x = sm.add_constant(data["market_return"])
    model = sm.OLS(data["long_short_return"], x).fit(
        cov_type="HAC", cov_kwds={"maxlags": 5}
    )

    return pd.DataFrame(
        [
            {
                "alpha_daily": model.params["const"],
                "t_alpha": model.tvalues["const"],
                "beta_market": model.params["market_return"],
                "t_market": model.tvalues["market_return"],
                "r_squared": model.rsquared,
                "n_days": int(model.nobs),
            }
        ]
    )


def save_tables(portfolios, forward_summary, daily_strategy, market_model):
    OUTPUT_DIR.mkdir(exist_ok=True)

    sample_summary = pd.DataFrame(
        [
            {
                "start_date": portfolios["date"].min().strftime("%Y-%m-%d"),
                "end_date": portfolios["date"].max().strftime("%Y-%m-%d"),
                "n_stock_days": len(portfolios),
                "n_stocks": portfolios["stock"].nunique(),
                "lookback_days": LOOKBACK_DAYS,
                "tail_quantile": TAIL_QUANTILE,
                "holding_days": HOLDING_DAYS,
            }
        ]
    )

    signal_counts = (
        portfolios.groupby(["date", "portfolio"]).size().unstack().describe().T
    )
    signal_stats = portfolios[["turnover", "volume_shock", "ret"]].describe().T

    sample_summary.to_csv(OUTPUT_DIR / "table_sample_summary.csv", index=False)
    signal_counts.to_csv(OUTPUT_DIR / "table_daily_portfolio_stock_counts.csv")
    signal_stats.to_csv(OUTPUT_DIR / "table_signal_statistics.csv")
    forward_summary.to_csv(OUTPUT_DIR / "table_forward_return_tests.csv", index=False)
    daily_strategy.to_csv(OUTPUT_DIR / "table_overlapping_20d_strategy_returns.csv")
    market_model.to_csv(OUTPUT_DIR / "table_market_model_alpha.csv", index=False)


def save_figures(forward_summary, daily_strategy):
    OUTPUT_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", font="Arial")

    plot_data = forward_summary[
        forward_summary["portfolio"].isin(["Low volume", "High volume", "High-Low"])
    ]
    plt.figure(figsize=(9, 5))
    sns.barplot(data=plot_data, x="horizon_days", y="mean_return", hue="portfolio")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.title("Future Returns After Abnormal Volume Signals")
    plt.xlabel("Forward horizon, trading days")
    plt.ylabel("Average future return")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure_forward_return_premium.png", dpi=300)
    plt.close()

    plt.figure(figsize=(11, 5))
    plt.plot(
        daily_strategy.index,
        daily_strategy["cumulative_return"],
        color="#2f6f73",
        linewidth=1.2,
    )
    plt.axhline(0, color="black", linewidth=0.8)
    plt.title("Cumulative Return of 20-Day Overlapping High-minus-Low Volume Strategy")
    plt.xlabel("Date")
    plt.ylabel("Cumulative return")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure_overlapping_20d_strategy.png", dpi=300)
    plt.close()


def print_notes(portfolios, forward_summary, daily_strategy, market_model):
    high_low = forward_summary[forward_summary["portfolio"] == "High-Low"].copy()
    high_low["mean_return_pct"] = high_low["mean_return"] * 100

    daily_mean = daily_strategy["long_short_return"].mean()
    daily_t = (
        daily_mean
        / daily_strategy["long_short_return"].std(ddof=1)
        * np.sqrt(len(daily_strategy))
    )

    print("\n=== High-Volume Return Premium Replication ===")
    print(
        f"Sample: {portfolios['date'].min():%Y-%m-%d} to {portfolios['date'].max():%Y-%m-%d}"
    )
    print(
        f"Stocks: {portfolios['stock'].nunique():,}; stock-days with valid signal: {len(portfolios):,}"
    )
    print(
        "Signal: log turnover minus the stock's own trailing 50-day mean, "
        "scaled by its trailing 50-day standard deviation."
    )
    print("\n=== High-minus-Low Forward Return Tests ===")
    print(high_low[["horizon_days", "mean_return_pct", "t_stat", "n_days"]].round(4))
    print("\n=== 20-Day Overlapping Strategy ===")
    print(f"Average daily return: {daily_mean * 100:.4f}%")
    print(f"t-stat: {daily_t:.3f}")
    print(
        f"Final cumulative return: {daily_strategy['cumulative_return'].iloc[-1] * 100:.2f}%"
    )
    print("\n=== Market Model Alpha ===")
    print(market_model.round(4))
    print(f"\nOutput saved to: {OUTPUT_DIR}")


def main():
    raw = load_daily_data()
    data = add_volume_signal(raw)
    data = add_forward_returns(data)
    portfolios = assign_volume_portfolios(data)

    forward_summary = summarize_forward_returns(portfolios)
    daily_strategy = build_overlapping_holding_returns(portfolios)
    market_model = run_market_model(daily_strategy, portfolios)

    save_tables(portfolios, forward_summary, daily_strategy, market_model)
    save_figures(forward_summary, daily_strategy)
    print_notes(portfolios, forward_summary, daily_strategy, market_model)


if __name__ == "__main__":
    main()
