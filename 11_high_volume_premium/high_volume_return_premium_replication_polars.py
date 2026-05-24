from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUTPUT_DIR = BASE / "output_polars"

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
    frames = [
        pl.read_csv(
            path,
            columns=DATA_COLUMNS,
            schema_overrides={"Stkcd": pl.String},
            try_parse_dates=True,
        )
        for path in list_daily_files()
    ]

    return (
        pl.concat(frames, how="vertical")
        .rename(
            {
                "Stkcd": "stock",
                "Trddt": "date",
                "Clsprc": "close",
                "Dnshrtrd": "shares_traded",
                "Dsmvosd": "float_mkt_cap_thousand",
                "Dretwd": "ret",
            }
        )
        .with_columns(
            pl.col("date").cast(pl.Date),
            pl.col("close").cast(pl.Float64, strict=False),
            pl.col("shares_traded").cast(pl.Float64, strict=False),
            pl.col("float_mkt_cap_thousand").cast(pl.Float64, strict=False),
            pl.col("ret").cast(pl.Float64, strict=False),
        )
        .filter(pl.col("date").is_between(pl.date(2020, 1, 1), pl.date(2024, 12, 31)))
        .drop_nulls(["stock", "date", "close", "shares_traded", "ret"])
        .filter(pl.col("close") > 0)
        .unique(subset=["stock", "date"], keep="first")
        .sort(["stock", "date"])
    )


def add_volume_signal(data):
    log_turnover = (
        pl.when(
            (pl.col("float_mkt_cap_thousand") > 0)
            & (pl.col("shares_traded") > 0)
            & (pl.col("close") > 0)
        )
        .then(
            (
                pl.col("shares_traded")
                * pl.col("close")
                / (pl.col("float_mkt_cap_thousand") * 1000)
            ).log()
        )
        .otherwise(None)
        .alias("log_turnover")
    )

    return (
        data.with_columns(
            (
                pl.col("shares_traded")
                * pl.col("close")
                / (pl.col("float_mkt_cap_thousand") * 1000)
            ).alias("turnover"),
            log_turnover,
        )
        .with_columns(
            pl.col("log_turnover")
            .shift(1)
            .rolling_mean(window_size=LOOKBACK_DAYS, min_samples=MIN_LOOKBACK_DAYS)
            .over("stock")
            .alias("rolling_log_turnover_mean"),
            pl.col("log_turnover")
            .shift(1)
            .rolling_std(window_size=LOOKBACK_DAYS, min_samples=MIN_LOOKBACK_DAYS)
            .over("stock")
            .alias("rolling_log_turnover_std"),
        )
        .with_columns(
            (
                (pl.col("log_turnover") - pl.col("rolling_log_turnover_mean"))
                / pl.col("rolling_log_turnover_std")
            ).alias("volume_shock")
        )
        .with_columns(
            pl.when(pl.col("volume_shock").is_finite())
            .then(pl.col("volume_shock"))
            .otherwise(None)
            .alias("volume_shock")
        )
    )


def add_forward_returns(data):
    expressions = []
    for horizon in FORWARD_HORIZONS:
        expressions.append(
            (
                pl.col("ret")
                .add(1)
                .log()
                .shift(-1)
                .reverse()
                .rolling_sum(window_size=horizon, min_samples=horizon)
                .reverse()
                .over("stock")
                .exp()
                - 1
            ).alias(f"fwd_ret_{horizon}d")
        )
    return data.with_columns(expressions)


def assign_volume_portfolios(data):
    return (
        data.drop_nulls(["volume_shock", "ret"])
        .with_columns(
            (
                pl.col("volume_shock").rank(method="ordinal").over("date")
                / pl.len().over("date")
            ).alias("shock_rank")
        )
        .with_columns(
            pl.when(pl.col("shock_rank") <= TAIL_QUANTILE)
            .then(pl.lit("Low volume"))
            .when(pl.col("shock_rank") >= 1 - TAIL_QUANTILE)
            .then(pl.lit("High volume"))
            .otherwise(pl.lit("Middle"))
            .alias("portfolio")
        )
    )


def summarize_forward_returns(portfolios):
    summaries = []
    order = ["Low volume", "Middle", "High volume", "High-Low"]

    for horizon in FORWARD_HORIZONS:
        col = f"fwd_ret_{horizon}d"
        daily = (
            portfolios.drop_nulls(col)
            .group_by(["date", "portfolio"])
            .agg(pl.col(col).mean().alias("mean_return"))
            .pivot(
                values="mean_return",
                index="date",
                on="portfolio",
                aggregate_function="first",
            )
            .with_columns(
                (pl.col("High volume") - pl.col("Low volume")).alias("High-Low")
            )
        )

        rows = []
        for name in order:
            rows.append(
                daily.select(
                    pl.lit(horizon).alias("horizon_days"),
                    pl.lit(name).alias("portfolio"),
                    pl.col(name).mean().alias("mean_return"),
                    pl.col(name).std().alias("std"),
                    pl.col(name).drop_nulls().count().alias("n_days"),
                )
            )
        summaries.append(pl.concat(rows))

    return (
        pl.concat(summaries)
        .with_columns(
            (
                pl.col("mean_return")
                / pl.col("std")
                * pl.col("n_days").cast(pl.Float64).sqrt()
            ).alias("t_stat")
        )
        .select(["horizon_days", "portfolio", "mean_return", "t_stat", "std", "n_days"])
    )


def build_overlapping_holding_returns(portfolios):
    signal = portfolios.filter(
        pl.col("portfolio").is_in(["Low volume", "High volume"])
    ).select(
        "stock",
        "date",
        pl.when(pl.col("portfolio") == "High volume")
        .then(1.0)
        .otherwise(-1.0)
        .alias("position"),
    )

    stock_date = (
        portfolios.select("stock", "date", "ret")
        .join(signal, on=["stock", "date"], how="left")
        .sort(["stock", "date"])
        .with_columns(
            pl.col("position")
            .shift(1)
            .rolling_mean(window_size=HOLDING_DAYS, min_samples=1)
            .over("stock")
            .alias("active_position")
        )
        .drop_nulls(["active_position", "ret"])
    )

    return (
        stock_date.group_by("date")
        .agg(
            (pl.col("active_position") * pl.col("ret"))
            .mean()
            .alias("long_short_return"),
            pl.col("active_position").abs().mean().alias("gross_exposure"),
            pl.col("active_position").count().alias("n_stocks"),
        )
        .sort("date")
        .with_columns(
            ((pl.col("long_short_return") + 1).cum_prod() - 1).alias(
                "cumulative_return"
            )
        )
    )


def run_market_model(daily_strategy, portfolios):
    market = portfolios.group_by("date").agg(
        pl.col("ret").mean().alias("market_return")
    )
    regression_data = (
        daily_strategy.select("date", "long_short_return")
        .join(market, on="date", how="inner")
        .sort("date")
        .to_pandas()
    )
    x = sm.add_constant(regression_data["market_return"])
    model = sm.OLS(regression_data["long_short_return"], x).fit(
        cov_type="HAC", cov_kwds={"maxlags": 5}
    )

    return pl.DataFrame(
        {
            "alpha_daily": [model.params["const"]],
            "t_alpha": [model.tvalues["const"]],
            "beta_market": [model.params["market_return"]],
            "t_market": [model.tvalues["market_return"]],
            "r_squared": [model.rsquared],
            "n_days": [int(model.nobs)],
        }
    )


def save_tables(portfolios, forward_summary, daily_strategy, market_model):
    OUTPUT_DIR.mkdir(exist_ok=True)

    sample_summary = portfolios.select(
        pl.col("date").min().dt.strftime("%Y-%m-%d").alias("start_date"),
        pl.col("date").max().dt.strftime("%Y-%m-%d").alias("end_date"),
        pl.len().alias("n_stock_days"),
        pl.col("stock").n_unique().alias("n_stocks"),
        pl.lit(LOOKBACK_DAYS).alias("lookback_days"),
        pl.lit(TAIL_QUANTILE).alias("tail_quantile"),
        pl.lit(HOLDING_DAYS).alias("holding_days"),
    )

    signal_counts = (
        portfolios.group_by(["date", "portfolio"])
        .len(name="n_stocks")
        .pivot(
            values="n_stocks",
            index="date",
            on="portfolio",
            aggregate_function="first",
        )
        .select(pl.all().exclude("date"))
        .describe()
    )
    signal_stats = portfolios.select("turnover", "volume_shock", "ret").describe()

    sample_summary.write_csv(OUTPUT_DIR / "table_sample_summary.csv")
    signal_counts.write_csv(OUTPUT_DIR / "table_daily_portfolio_stock_counts.csv")
    signal_stats.write_csv(OUTPUT_DIR / "table_signal_statistics.csv")
    forward_summary.write_csv(OUTPUT_DIR / "table_forward_return_tests.csv")
    daily_strategy.write_csv(OUTPUT_DIR / "table_overlapping_20d_strategy_returns.csv")
    market_model.write_csv(OUTPUT_DIR / "table_market_model_alpha.csv")


def save_figures(forward_summary, daily_strategy):
    OUTPUT_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", font="Arial")

    plot_data = forward_summary.filter(
        pl.col("portfolio").is_in(["Low volume", "High volume", "High-Low"])
    ).to_pandas()
    plt.figure(figsize=(9, 5))
    sns.barplot(data=plot_data, x="horizon_days", y="mean_return", hue="portfolio")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.title("Future Returns After Abnormal Volume Signals")
    plt.xlabel("Forward horizon, trading days")
    plt.ylabel("Average future return")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure_forward_return_premium.png", dpi=300)
    plt.close()

    strategy_plot = daily_strategy.to_pandas()
    plt.figure(figsize=(11, 5))
    plt.plot(
        strategy_plot["date"],
        strategy_plot["cumulative_return"],
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


def round_numeric(data, decimals=4):
    return data.with_columns(pl.col(pl.Float64, pl.Float32).round(decimals))


def print_notes(portfolios, forward_summary, daily_strategy, market_model):
    dates = portfolios.select(
        pl.col("date").min().alias("start_date"),
        pl.col("date").max().alias("end_date"),
    ).row(0)
    n_stocks = portfolios.select(pl.col("stock").n_unique()).item()
    n_stock_days = portfolios.height

    high_low = (
        forward_summary.filter(pl.col("portfolio") == "High-Low")
        .with_columns((pl.col("mean_return") * 100).alias("mean_return_pct"))
        .select("horizon_days", "mean_return_pct", "t_stat", "n_days")
    )

    strategy_returns = daily_strategy["long_short_return"]
    daily_mean = strategy_returns.mean()
    daily_t = daily_mean / strategy_returns.std() * np.sqrt(strategy_returns.len())
    final_cumulative = daily_strategy["cumulative_return"][-1]

    print("\n=== High-Volume Return Premium Replication (Polars) ===")
    print(f"Sample: {dates[0]:%Y-%m-%d} to {dates[1]:%Y-%m-%d}")
    print(f"Stocks: {n_stocks:,}; stock-days with valid signal: {n_stock_days:,}")
    print(
        "Signal: log turnover minus the stock's own trailing 50-day mean, "
        "scaled by its trailing 50-day standard deviation."
    )
    print("\n=== High-minus-Low Forward Return Tests ===")
    print(round_numeric(high_low, 4))
    print("\n=== 20-Day Overlapping Strategy ===")
    print(f"Average daily return: {daily_mean * 100:.4f}%")
    print(f"t-stat: {daily_t:.3f}")
    print(f"Final cumulative return: {final_cumulative * 100:.2f}%")
    print("\n=== Market Model Alpha ===")
    print(round_numeric(market_model, 4))
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
