"""CAPM empirical analysis using simulated market data.

This module implements a complete pipeline from data generation through
cross-sectional and time-series evaluation of the Capital Asset Pricing Model
(CAPM). It is intentionally self-contained so that the analysis can be
reproduced and extended without relying on external data files.

CAPM specification estimated for each asset i:
    R_i(t) - R_f(t) = alpha_i + beta_i * (R_m(t) - R_f(t)) + epsilon_i(t)

where:
    R_i  : asset return
    R_f  : risk-free rate
    R_m  : market return
    beta : systematic risk exposure to the market factor
    alpha: pricing error (should be statistically zero if CAPM holds)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm

# ---------------------------------------------------------------------------
# Paths and configuration
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUTPUT_DIR = BASE / "output"

SEED = 42
START_DATE = "2020-01-01"
END_DATE = "2024-12-31"
N_STOCKS = 30
TRUE_MARKET_BETA = 0.05  # daily market excess return in percent
TRUE_BETA_SPREAD = 0.02  # cross-sectional spread around the market mean
MARKET_BETA_RANGE = (0.4, 1.6)
MARKET_VOLATILITY = 1.0
IDIOSYNCRATIC_VOLATILITY = 1.5
ANNUAL_RISK_FREE_RATE = 0.03

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------
@dataclass
class SimulationParameters:
    """Parameters that fully determine the simulated return distribution."""

    n_stocks: int = N_STOCKS
    start_date: str = START_DATE
    end_date: str = END_DATE
    market_beta_mean: float = TRUE_MARKET_BETA
    market_beta_spread: float = TRUE_BETA_SPREAD
    market_volatility: float = MARKET_VOLATILITY
    idiosyncratic_volatility: float = IDIOSYNCRATIC_VOLATILITY
    annual_risk_free_rate: float = ANNUAL_RISK_FREE_RATE
    seed: int = SEED

    def __post_init__(self):
        np.random.seed(self.seed)


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------
class DataGenerator:
    """Simulate a panel of stock returns, market returns, and risk-free rates.

    The simulation is designed to be consistent with CAPM intuition: assets have
    heterogeneous market betas, expected returns are increasing in beta, and the
    market factor is the dominant source of common co-movement.
    """

    def __init__(self, params: SimulationParameters | None = None):
        self.params = params or SimulationParameters()
        self.dates = self._generate_trading_dates()
        self.market_returns = self._generate_market_returns()
        self.risk_free_rates = self._generate_risk_free_rates()
        self.stock_betas = self._generate_stock_betas()
        self.stock_returns = self._generate_stock_returns()

    def _generate_trading_dates(self) -> pd.DatetimeIndex:
        """Create a business-day date index."""
        return pd.bdate_range(
            start=self.params.start_date, end=self.params.end_date, name="Date"
        )

    def _generate_market_returns(self) -> pd.Series:
        """Simulate daily market excess returns (in percent)."""
        n = len(self.dates)
        shocks = np.random.normal(0, self.params.market_volatility, size=n)
        returns = self.params.market_beta_mean + shocks
        return pd.Series(returns, index=self.dates, name="Market")

    def _generate_risk_free_rates(self) -> pd.Series:
        """Simulate a daily risk-free rate (in percent)."""
        daily_rate = self.params.annual_risk_free_rate / 252 * 100
        noise = np.random.normal(0, 0.01, size=len(self.dates))
        return pd.Series(daily_rate + noise, index=self.dates, name="RiskFree")

    def _generate_stock_betas(self) -> pd.Series:
        """Draw cross-sectional market betas."""
        betas = np.random.uniform(
            MARKET_BETA_RANGE[0], MARKET_BETA_RANGE[1], size=self.params.n_stocks
        )
        tickers = [f"Stock_{i+1:02d}" for i in range(self.params.n_stocks)]
        return pd.Series(betas, index=tickers, name="Beta")

    def _generate_stock_returns(self) -> pd.DataFrame:
        """Simulate individual stock returns from a single-factor market model."""
        n_days = len(self.dates)
        market = self.market_returns.values
        betas = self.stock_betas.values
        idiosyncratic = np.random.normal(
            0, self.params.idiosyncratic_volatility, size=(n_days, self.params.n_stocks)
        )
        # Expected return is proportional to beta according to CAPM
        expected_returns = betas * self.params.market_beta_mean
        returns = expected_returns + np.outer(market, betas) + idiosyncratic
        return pd.DataFrame(
            returns, index=self.dates, columns=self.stock_betas.index
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Combine all simulated series into a single DataFrame."""
        return pd.concat(
            [
                self.stock_returns,
                self.market_returns.to_frame(),
                self.risk_free_rates.to_frame(),
            ],
            axis=1,
        )

    def save(self, path: Path | None = None) -> Path:
        """Persist simulated data to the data directory."""
        path = path or DATA_DIR / "simulated_returns.csv"
        DATA_DIR.mkdir(exist_ok=True)
        self.to_dataframe().to_csv(path)
        return path


# ---------------------------------------------------------------------------
# Data preprocessing
# ---------------------------------------------------------------------------
class DataPreprocessor:
    """Prepare excess returns and merge asset returns with the market factor."""

    def __init__(self, data: pd.DataFrame, stock_cols: list[str] | None = None):
        self.raw = data.copy()
        self.stock_cols = stock_cols or [
            col for col in self.raw.columns if col.startswith("Stock_")
        ]

    def compute_excess_returns(self) -> pd.DataFrame:
        """Convert gross returns to excess returns over the risk-free rate."""
        excess = self.raw[self.stock_cols].subtract(self.raw["RiskFree"], axis=0)
        excess["MarketExcess"] = self.raw["Market"] - self.raw["RiskFree"]
        return excess

    def validate(self, excess: pd.DataFrame) -> pd.DataFrame:
        """Remove rows with missing or infinite values."""
        cleaned = excess.replace([np.inf, -np.inf], np.nan).dropna()
        if cleaned.empty:
            raise ValueError("No valid observations after cleaning.")
        return cleaned


# ---------------------------------------------------------------------------
# CAPM model fitting
# ---------------------------------------------------------------------------
class CAPMModel:
    """Estimate asset-level CAPM regressions via ordinary least squares (OLS)."""

    def __init__(self, excess_returns: pd.DataFrame, market_excess_col: str = "MarketExcess"):
        self.excess = excess_returns.copy()
        self.market_col = market_excess_col
        self.stock_cols = [c for c in self.excess.columns if c != market_excess_col]
        self.market_factor = sm.add_constant(self.excess[market_excess_col])
        self.fitted_models: dict[str, Any] = {}
        self.summary_table: pd.DataFrame | None = None

    def fit(self) -> pd.DataFrame:
        """Run time-series CAPM regressions for each asset and tabulate results."""
        rows = []
        for stock in self.stock_cols:
            y = self.excess[stock]
            model = sm.OLS(y, self.market_factor).fit(
                cov_type="HC0", use_t=True
            )
            self.fitted_models[stock] = model
            rows.append(
                {
                    "ticker": stock,
                    "alpha": model.params["const"],
                    "alpha_pvalue": model.pvalues["const"],
                    "alpha_tvalue": model.tvalues["const"],
                    "beta": model.params[self.market_col],
                    "beta_pvalue": model.pvalues[self.market_col],
                    "beta_tvalue": model.tvalues[self.market_col],
                    "r_squared": model.rsquared,
                    "adj_r_squared": model.rsquared_adj,
                    "n_obs": int(model.nobs),
                }
            )
        self.summary_table = pd.DataFrame(rows).set_index("ticker")
        return self.summary_table


# ---------------------------------------------------------------------------
# Results evaluation
# ---------------------------------------------------------------------------
class ResultsEvaluator:
    """Aggregate, evaluate, and visualise CAPM estimation results."""

    def __init__(
        self,
        summary_table: pd.DataFrame,
        excess_returns: pd.DataFrame,
        market_excess_col: str = "MarketExcess",
    ):
        self.summary = summary_table.copy()
        self.excess = excess_returns.copy()
        self.market_col = market_excess_col

    def cross_sectional_test(self) -> pd.DataFrame:
        """Run a cross-sectional regression of average excess returns on betas.

        Under the CAPM, the intercept should be zero and the slope should equal
        the average market excess return (the market risk premium).
        """
        avg_returns = self.excess.drop(columns=self.market_col).mean()
        betas = self.summary["beta"].reindex(avg_returns.index)
        data = pd.DataFrame({"avg_excess_return": avg_returns, "beta": betas}).dropna()
        x = sm.add_constant(data["beta"])
        model = sm.OLS(data["avg_excess_return"], x).fit(cov_type="HC0", use_t=True)

        return pd.DataFrame(
            [
                {
                    "intercept": model.params["const"],
                    "intercept_tvalue": model.tvalues["const"],
                    "intercept_pvalue": model.pvalues["const"],
                    "slope": model.params["beta"],
                    "slope_tvalue": model.tvalues["beta"],
                    "slope_pvalue": model.pvalues["beta"],
                    "r_squared": model.rsquared,
                    "n_assets": int(model.nobs),
                }
            ]
        )

    def diagnostic_statistics(self) -> pd.DataFrame:
        """Compute sample-wide diagnostics for the market factor and returns."""
        market = self.excess[self.market_col]
        stocks = self.excess.drop(columns=self.market_col)
        stats = {
            "Market excess return": {
                "mean": market.mean(),
                "std": market.std(),
                "annualized_mean": market.mean() * 252,
                "annualized_vol": market.std() * np.sqrt(252),
                "sharpe": market.mean() / market.std() * np.sqrt(252),
            },
            "Average stock excess return": {
                "mean": stocks.mean().mean(),
                "std": stocks.mean().std(),
                "annualized_mean": stocks.mean().mean() * 252,
                "annualized_vol": stocks.mean().std() * np.sqrt(252),
            },
        }
        return pd.DataFrame(stats).T

    def significance_counts(self) -> pd.DataFrame:
        """Count how many alphas and betas are statistically significant."""
        alpha_sig = (self.summary["alpha_pvalue"] < 0.05).sum()
        beta_sig = (self.summary["beta_pvalue"] < 0.05).sum()
        return pd.DataFrame(
            {
                "n_significant_5pct": [alpha_sig, beta_sig],
                "n_total": [len(self.summary)] * 2,
            },
            index=["Alpha", "Beta"],
        )

    def plot_beta_vs_return(self, path: Path | None = None) -> Path:
        """Scatter plot of estimated beta against average excess return."""
        path = path or OUTPUT_DIR / "figure_beta_vs_return.png"
        avg_returns = self.excess.drop(columns=self.market_col).mean()
        plot_data = pd.DataFrame(
            {
                "beta": self.summary["beta"].reindex(avg_returns.index),
                "avg_excess_return": avg_returns,
            }
        ).dropna()

        x = sm.add_constant(plot_data["beta"])
        model = sm.OLS(plot_data["avg_excess_return"], x).fit()
        fitted = model.predict(x)

        plt.figure(figsize=(9, 6))
        sns.regplot(
            data=plot_data,
            x="beta",
            y="avg_excess_return",
            ci=None,
            scatter_kws={"s": 40, "alpha": 0.7, "color": "#2f6f73"},
            line_kws={"color": "#a84c4c", "linewidth": 1.5},
        )
        plt.title("Cross-Sectional Relation: Beta vs. Average Excess Return")
        plt.xlabel("Estimated CAPM beta")
        plt.ylabel("Average excess return (% per day)")
        plt.tight_layout()
        plt.savefig(path, dpi=300)
        plt.close()
        return path

    def plot_alpha_distribution(self, path: Path | None = None) -> Path:
        """Histogram of estimated alphas with a zero-reference line."""
        path = path or OUTPUT_DIR / "figure_alpha_distribution.png"
        plt.figure(figsize=(9, 5))
        plt.hist(self.summary["alpha"], bins=15, color="#2f6f73", edgecolor="white")
        plt.axvline(0, color="#a84c4c", linewidth=1.5, linestyle="--", label="Zero alpha")
        plt.title("Distribution of CAPM Alphas")
        plt.xlabel("Daily alpha (%)")
        plt.ylabel("Number of assets")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path, dpi=300)
        plt.close()
        return path

    def plot_r_squared_distribution(self, path: Path | None = None) -> Path:
        """Histogram of R-squared values from the time-series regressions."""
        path = path or OUTPUT_DIR / "figure_r_squared_distribution.png"
        plt.figure(figsize=(9, 5))
        plt.hist(self.summary["r_squared"], bins=15, color="#6f5aa8", edgecolor="white")
        plt.title("Distribution of Time-Series R-Squared")
        plt.xlabel("R-squared")
        plt.ylabel("Number of assets")
        plt.tight_layout()
        plt.savefig(path, dpi=300)
        plt.close()
        return path

    def plot_security_market_line(
        self, cross_section: pd.DataFrame, path: Path | None = None
    ) -> Path:
        """Plot the empirical security market line (SML) over the data range."""
        path = path or OUTPUT_DIR / "figure_security_market_line.png"
        intercept = cross_section["intercept"].iloc[0]
        slope = cross_section["slope"].iloc[0]
        beta_grid = np.linspace(
            self.summary["beta"].min() - 0.1, self.summary["beta"].max() + 0.1, 100
        )
        sml = intercept + slope * beta_grid

        avg_returns = self.excess.drop(columns=self.market_col).mean()
        plot_data = pd.DataFrame(
            {
                "beta": self.summary["beta"].reindex(avg_returns.index),
                "avg_excess_return": avg_returns,
            }
        ).dropna()

        plt.figure(figsize=(9, 6))
        plt.plot(beta_grid, sml, color="#a84c4c", linewidth=1.5, label="Security market line")
        plt.scatter(
            plot_data["beta"], plot_data["avg_excess_return"], color="#2f6f73", s=40, alpha=0.7
        )
        plt.title("Empirical Security Market Line")
        plt.xlabel("Beta")
        plt.ylabel("Average excess return (% per day)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path, dpi=300)
        plt.close()
        return path


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def save_tables(
    summary_table: pd.DataFrame,
    cross_section: pd.DataFrame,
    diagnostics: pd.DataFrame,
    significance: pd.DataFrame,
    excess_returns: pd.DataFrame,
    output_dir: Path = OUTPUT_DIR,
) -> None:
    """Persist numerical results to CSV files."""
    output_dir.mkdir(exist_ok=True)
    summary_table.round(6).to_csv(output_dir / "table_capm_time_series_results.csv")
    cross_section.round(6).to_csv(
        output_dir / "table_capm_cross_sectional_test.csv", index=False
    )
    diagnostics.round(6).to_csv(output_dir / "table_diagnostics.csv")
    significance.to_csv(output_dir / "table_significance_counts.csv")
    excess_returns.round(6).to_csv(output_dir / "table_excess_returns.csv")


def print_report(
    summary_table: pd.DataFrame,
    cross_section: pd.DataFrame,
    diagnostics: pd.DataFrame,
    significance: pd.DataFrame,
) -> None:
    """Print a concise, reproducible summary of the CAPM analysis."""
    print("\n" + "=" * 70)
    print("CAPM EMPIRICAL ANALYSIS (Simulated Data)")
    print("=" * 70)
    print("\n--- Sample Diagnostics ---")
    print(diagnostics.round(4))

    print("\n--- Time-Series CAPM Regressions (First 10 Assets) ---")
    display_cols = [
        "alpha",
        "alpha_tvalue",
        "alpha_pvalue",
        "beta",
        "beta_tvalue",
        "beta_pvalue",
        "r_squared",
    ]
    print(summary_table[display_cols].head(10).round(4))

    print("\n--- Summary of Beta Estimates ---")
    print(summary_table["beta"].describe().round(4))

    print("\n--- Summary of R-Squared ---")
    print(summary_table["r_squared"].describe().round(4))

    print("\n--- Significance Counts (5% level) ---")
    print(significance)

    print("\n--- Cross-Sectional Regression: E[R_i] = gamma_0 + gamma_1 * beta_i ---")
    print(cross_section.round(4))

    mean_r2 = summary_table["r_squared"].mean()
    print(f"\nMean time-series R-squared: {mean_r2:.4f}")
    print(
        "Interpretation: assets with higher market betas earn higher average excess returns "
        "if the CAPM slope is positive and significant; non-zero alphas suggest pricing errors."
    )
    print(f"\nAll outputs saved to: {OUTPUT_DIR}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the full CAPM analysis pipeline."""
    sns.set_theme(style="whitegrid", font="Arial")
    OUTPUT_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    # 1. Generate simulated market data
    generator = DataGenerator()
    raw_data = generator.to_dataframe()
    generator.save()

    # 2. Preprocess: compute excess returns and clean
    preprocessor = DataPreprocessor(raw_data)
    excess_returns = preprocessor.validate(preprocessor.compute_excess_returns())

    # 3. Estimate CAPM regressions for each asset
    capm = CAPMModel(excess_returns)
    summary_table = capm.fit()

    # 4. Evaluate and visualise results
    evaluator = ResultsEvaluator(summary_table, excess_returns)
    cross_section = evaluator.cross_sectional_test()
    diagnostics = evaluator.diagnostic_statistics()
    significance = evaluator.significance_counts()

    evaluator.plot_beta_vs_return()
    evaluator.plot_alpha_distribution()
    evaluator.plot_r_squared_distribution()
    evaluator.plot_security_market_line(cross_section)

    # 5. Save and report
    save_tables(summary_table, cross_section, diagnostics, significance, excess_returns)
    print_report(summary_table, cross_section, diagnostics, significance)


if __name__ == "__main__":
    main()
