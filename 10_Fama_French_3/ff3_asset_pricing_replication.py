from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUTPUT_DIR = BASE / "output"

FACTOR_FILE = DATA_DIR / "F-F_Research_Data_Factors_daily.csv"
PORTFOLIO_FILE = DATA_DIR / "6_Portfolios_2x3_Daily.csv"

PORTFOLIO_COLS = [
    "SMALL LoBM",
    "ME1 BM2",
    "SMALL HiBM",
    "BIG LoBM",
    "ME2 BM2",
    "BIG HiBM",
]
FACTOR_COLS = ["MKT", "SMB", "HML"]


def read_first_panel(path):
    """Ken French CSV files can contain several panels separated by blank rows."""
    df = pd.read_csv(path)
    first_blank = df["TIME"].isna().idxmax() if df["TIME"].isna().any() else len(df)
    return df.iloc[:first_blank].copy()


def load_factors():
    ff = read_first_panel(FACTOR_FILE)
    ff = ff.rename(
        columns={
            "TIME": "Date",
            "Mkt-RF": "MKT",
            "SMB": "SMB",
            "HML": "HML",
            "RF": "RF",
        }
    )
    ff[FACTOR_COLS + ["RF"]] = ff[FACTOR_COLS + ["RF"]].apply(
        pd.to_numeric, errors="coerce"
    )
    ff = ff.dropna(subset=["Date"] + FACTOR_COLS + ["RF"])
    ff["Date"] = pd.to_datetime(ff["Date"], format="%Y%m%d")
    return ff.set_index("Date")


def load_portfolios():
    port = read_first_panel(PORTFOLIO_FILE)
    port = port.rename(columns={"TIME": "Date"})
    port[PORTFOLIO_COLS] = port[PORTFOLIO_COLS].apply(pd.to_numeric, errors="coerce")
    port = port.dropna(subset=["Date"] + PORTFOLIO_COLS)
    port["Date"] = pd.to_datetime(port["Date"], format="%Y%m%d")
    return port.set_index("Date")


def prepare_regression_data():
    ff = load_factors()
    port = load_portfolios()
    data = port.merge(ff, left_index=True, right_index=True, how="inner")

    for col in PORTFOLIO_COLS:
        data[f"{col}_excess"] = data[col] - data["RF"]

    return data


def run_ff3_regressions(data):
    x = sm.add_constant(data[FACTOR_COLS])
    rows = []
    models = {}

    for col in PORTFOLIO_COLS:
        y_col = f"{col}_excess"
        model = sm.OLS(data[y_col], x).fit()
        models[col] = model
        rows.append(
            {
                "portfolio": col,
                "alpha": model.params["const"],
                "t_alpha": model.tvalues["const"],
                "beta_mkt": model.params["MKT"],
                "t_mkt": model.tvalues["MKT"],
                "beta_smb": model.params["SMB"],
                "t_smb": model.tvalues["SMB"],
                "beta_hml": model.params["HML"],
                "t_hml": model.tvalues["HML"],
                "r_squared": model.rsquared,
                "adj_r_squared": model.rsquared_adj,
                "n_obs": int(model.nobs),
            }
        )

    return pd.DataFrame(rows).set_index("portfolio"), models


def build_summary_tables(data, regression_table):
    factor_stats = data[FACTOR_COLS].agg(["mean", "std", "min", "max"])
    factor_stats.loc["t-stat"] = (
        factor_stats.loc["mean"] / factor_stats.loc["std"] * np.sqrt(len(data))
    )

    excess_cols = [f"{col}_excess" for col in PORTFOLIO_COLS]
    portfolio_stats = data[excess_cols].agg(["mean", "std", "min", "max"]).T
    portfolio_stats.index = PORTFOLIO_COLS
    portfolio_stats["t-stat"] = (
        portfolio_stats["mean"] / portfolio_stats["std"] * np.sqrt(len(data))
    )

    corr = data[FACTOR_COLS + excess_cols].corr()
    corr = corr.rename(
        index={f"{col}_excess": col for col in PORTFOLIO_COLS},
        columns={f"{col}_excess": col for col in PORTFOLIO_COLS},
    )

    return factor_stats, portfolio_stats, corr, regression_table.round(4)


def save_tables(factor_stats, portfolio_stats, corr, regression_table):
    OUTPUT_DIR.mkdir(exist_ok=True)
    factor_stats.to_csv(OUTPUT_DIR / "table_factor_statistics.csv")
    portfolio_stats.to_csv(OUTPUT_DIR / "table_portfolio_excess_return_statistics.csv")
    corr.to_csv(OUTPUT_DIR / "table_correlation_matrix.csv")
    regression_table.to_csv(OUTPUT_DIR / "table_ff3_regression_results.csv")


def plot_cumulative_returns(data):
    excess_cols = [f"{col}_excess" for col in PORTFOLIO_COLS]
    cumulative = (1 + data[excess_cols] / 100).cumprod()
    cumulative.columns = PORTFOLIO_COLS

    plt.figure(figsize=(11, 6))
    for col in PORTFOLIO_COLS:
        plt.plot(cumulative.index, cumulative[col], linewidth=1.2, label=col)
    plt.title("Cumulative Excess Returns of 6 Size-BM Portfolios")
    plt.xlabel("Date")
    plt.ylabel("Cumulative return, initial value = 1")
    plt.legend(ncol=3, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure_cumulative_excess_returns.png", dpi=300)
    plt.close()


def plot_factor_timeseries(data):
    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    colors = ["#2f6f73", "#8a5a44", "#6f5aa8"]

    for ax, factor, color in zip(axes, FACTOR_COLS, colors):
        ax.plot(data.index, data[factor], color=color, linewidth=0.7)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_ylabel(factor)

    axes[0].set_title("Daily Fama-French Three Factors")
    axes[-1].set_xlabel("Date")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure_factor_timeseries.png", dpi=300)
    plt.close()


def plot_alpha_bar(regression_table):
    plot_data = regression_table.sort_values("alpha")

    plt.figure(figsize=(9, 5))
    colors = np.where(plot_data["alpha"] >= 0, "#2f6f73", "#a84c4c")
    plt.bar(plot_data.index, plot_data["alpha"], color=colors)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.title("FF3 Alpha Estimates")
    plt.xlabel("Portfolio")
    plt.ylabel("Daily alpha (%)")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure_alpha_bar.png", dpi=300)
    plt.close()


def plot_correlation_heatmap(corr):
    plt.figure(figsize=(9, 7))
    sns.heatmap(
        corr,
        cmap="vlag",
        center=0,
        annot=False,
        square=True,
        linewidths=0.3,
        cbar_kws={"shrink": 0.8},
    )
    plt.title("Correlation Matrix")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure_correlation_heatmap.png", dpi=300)
    plt.close()


def save_figures(data, regression_table, corr):
    OUTPUT_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", font="Arial")
    plot_cumulative_returns(data)
    plot_factor_timeseries(data)
    plot_alpha_bar(regression_table)
    plot_correlation_heatmap(corr)


def print_paper_ready_notes(data, regression_table):
    start_date = data.index.min().strftime("%Y-%m-%d")
    end_date = data.index.max().strftime("%Y-%m-%d")
    print("\n=== Sample Information ===")
    print(f"Sample period: {start_date} to {end_date}")
    print(f"Number of daily observations: {len(data)}")
    print("Unit: returns and factors are in percent per day.")

    print("\n=== FF3 Regression Results ===")
    print(regression_table.round(4))

    mean_r2 = regression_table["r_squared"].mean()
    print("\n=== Brief Interpretation ===")
    print(
        "The FF3 model explains the six portfolio excess returns well: "
        f"the average R-squared is {mean_r2:.4f}."
    )
    print(
        "Positive SMB loadings indicate stronger small-cap exposure, while "
        "positive HML loadings indicate stronger value exposure."
    )


def main():
    data = prepare_regression_data()
    regression_table, _ = run_ff3_regressions(data)
    factor_stats, portfolio_stats, corr, rounded_regression = build_summary_tables(
        data, regression_table
    )

    save_tables(factor_stats, portfolio_stats, corr, rounded_regression)
    save_figures(data, regression_table, corr)

    print_paper_ready_notes(data, regression_table)

    print("\n=== Output Files ===")
    print(f"Tables and figures saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

# 直接运行（python xxx.py）时，__name__ 的值是 "__main__"
# 被当作模块导入（import xxx）时，__name__ 是模块名（如 "ff3_asset_pricing_replication"）
