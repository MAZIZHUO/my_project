"""Fama & MacBeth (1973) 经典实证资产定价论文复现（模拟数据版）。

论文：Fama, E. F., & MacBeth, J. D. (1973).
      "Risk, Return, and Equilibrium: Empirical Tests."
      Journal of Political Economy, 81(3), 607-636.

核心思想（两阶段横截面检验）：
  Step 1（时间序列）：
      用前 L 个月滚动窗口估计每只股票对市场因子的 beta：
          R_i(t) - Rf(t) = alpha_i + beta_i * (Rm(t) - Rf(t)) + e_i(t)

  Step 2（横截面）：
      对每个月 t，用当期收益与最新估计的 beta 做横截面回归：
          R_i(t) - Rf(t) = gamma_0(t) + gamma_1(t) * beta_i + u_i(t)
      论文原文还同时检验了 beta^2（非线性）和残差风险 s(e_i)，
      简化版只保留市场 beta 一项。

  Step 3（检验）：
      对 gamma_1(t) 时间序列做均值 t 检验：
          t = mean(gamma_1) / [std(gamma_1) / sqrt(T)]
      若 CAPM 成立，市场风险溢价 gamma_1 应显著为正。

本脚本使用"模拟数据"（数据生成过程 CAPM 完全成立），
因此预期结果：beta 与平均收益显著正相关，且估计值接近真实市场溢价。

运行方式：
    uv run python 00_other_files/fama_macbeth_1973_replication.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境下安全出图

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]  # Windows 中文字体
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parent
OUTPUT_DIR = BASE / "output"

SEED = 42
N_MONTHS = 240       # 样本总月数（20 年）
N_STOCKS = 200       # 股票数量
WINDOW = 60          # Step 1 滚动估计 beta 的窗口长度（论文用 4-5 年）

MU_MARKET = 0.010    # 市场月超额收益均值（1.0%/月，约年化 12%）
SIGMA_MARKET = 0.04  # 市场月超额收益波动率
BETA_RANGE = (0.3, 1.8)  # 真实 beta 的横截面范围
TRUE_MARKET_PREMIUM = 0.010  # 真实市场风险溢价（月）
SIGMA_IDIO = 0.05    # 特质波动率（月度）
RF_ANNUAL = 0.02     # 无风险利率（年化）


@dataclass
class SimulationConfig:
    """模拟数据生成的完整参数集合。"""

    seed: int = SEED
    n_months: int = N_MONTHS
    n_stocks: int = N_STOCKS
    window: int = WINDOW
    mu_market: float = MU_MARKET
    sigma_market: float = SIGMA_MARKET
    beta_range: tuple[float, float] = BETA_RANGE
    true_market_premium: float = TRUE_MARKET_PREMIUM
    sigma_idio: float = SIGMA_IDIO
    rf_annual: float = RF_ANNUAL
    dates: pd.DatetimeIndex = field(init=False)

    def __post_init__(self) -> None:
        self.dates = pd.date_range(
            start="2016-01-01", periods=self.n_months, freq="ME"
        )


def simulate_data(cfg: SimulationConfig) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """按 CAPM 数据生成过程模拟月度收益。

    返回：
        excess_returns : (T, N) 每列一只股票的超额收益
        market_excess  : (T,)   市场超额收益（因子）
        true_betas     : (N,)   每只股票的真实 beta（用于事后对比）
    """
    rng = np.random.default_rng(cfg.seed)

    # 市场因子：单期可微的随机游走（论文中市场组合近似）
    market_excess = rng.normal(cfg.mu_market, cfg.sigma_market, cfg.n_months)

    # 真实 beta：横截面均匀分布
    lo, hi = cfg.beta_range
    true_betas = rng.uniform(lo, hi, cfg.n_stocks)

    # 特质冲击：每只股票独立
    idio = rng.normal(0.0, cfg.sigma_idio, size=(cfg.n_months, cfg.n_stocks))

    # CAPM 收益生成过程：R_i = beta_i * Rm + e_i
    excess_returns_arr = true_betas[None, :] * market_excess[:, None] + idio
    excess_returns = pd.DataFrame(
        excess_returns_arr,
        index=cfg.dates,
        columns=[f"STK{i:03d}" for i in range(cfg.n_stocks)],
    )

    return (
        excess_returns,
        pd.Series(market_excess, index=cfg.dates, name="MKT"),
        pd.Series(true_betas, index=excess_returns.columns, name="true_beta"),
    )


def rolling_betas(
    excess_returns: pd.DataFrame, market_excess: pd.Series, window: int
) -> pd.DataFrame:
    """Step 1：对每只股票用滚动窗口估计 beta（OLS 闭式解）。

    beta = Cov(R_i, Rm) / Var(Rm)，用前缀和实现 O(window) 滚动计算。
    返回：(T - window + 1, N) 的 beta 估计值矩阵，索引为窗口结束月份。
    """
    x = market_excess.to_numpy(dtype=float)
    y = excess_returns.to_numpy(dtype=float)
    t, n = y.shape
    m = t - window + 1

    # 前缀和（首元素为 0 便于差分）
    sx = np.concatenate([[0.0], np.cumsum(x)])
    sy = np.concatenate([np.zeros((1, n)), np.cumsum(y, axis=0)], axis=0)
    sxy = np.concatenate([np.zeros((1, n)), np.cumsum(x[:, None] * y, axis=0)], axis=0)
    sxx = np.concatenate([[0.0], np.cumsum(x * x)])

    starts = np.arange(m)
    ends = starts + window
    n_w = float(window)

    sum_x = sx[ends] - sx[starts]                                  # (M,)
    sum_y = sy[ends] - sy[starts]                                  # (M, N)
    sum_xy = sxy[ends] - sxy[starts]                               # (M, N)
    sum_xx = sxx[ends] - sxx[starts]                               # (M,)

    cov_xy = sum_xy - sum_x[:, None] * sum_y / n_w                 # (M, N)
    var_x = sum_xx - sum_x * sum_x / n_w                           # (M,)
    betas = cov_xy / var_x[:, None]                                # (M, N)

    return pd.DataFrame(
        betas,
        index=excess_returns.index[window - 1 :],
        columns=excess_returns.columns,
    )


def cross_sectional_regressions(
    excess_returns: pd.DataFrame, betas: pd.DataFrame
) -> pd.Series:
    """Step 2：对每个估计 beta 可用的月份做横截面回归。

    R_i(t) = gamma_0(t) + gamma_1(t) * beta_i + u_i(t)

    返回：gamma_1(t) 的时间序列。
    """
    gammas: list[float] = []
    for date in betas.index:
        if date not in excess_returns.index:
            continue
        y = excess_returns.loc[date]
        x = sm.add_constant(betas.loc[date])
        gamma = sm.OLS(y, x).fit().params
        gammas.append(gamma.iloc[1])
    return pd.Series(gammas, index=betas.index, name="gamma_1")


def fama_macbeth_t(gamma: pd.Series) -> tuple[float, float, float]:
    """Step 3：Fama-MacBeth t 检验。

    t = mean(gamma) / [std(gamma) / sqrt(T)]
    返回：(均值, 标准差, t 统计量)
    """
    mean_g = float(gamma.mean())
    std_g = float(gamma.std(ddof=1))
    t_stat = mean_g / (std_g / np.sqrt(len(gamma))) if std_g > 0 else np.nan
    return mean_g, std_g, t_stat


def portfolio_groups(
    excess_returns: pd.DataFrame, betas: pd.DataFrame, n_groups: int = 10
) -> pd.Series:
    """稳健性检验：按 beta 排序分组的 Fama-MacBeth。

    每月先把股票按 beta 分成 n_groups 组（组合），
    再对组合平均收益与组合平均 beta 做横截面回归，
    可减轻单只股票 beta 估计误差（errors-in-variables）的影响。

    返回：与 cross_sectional_regressions 相同的 gamma_1 序列。
    """
    gammas: list[float] = []
    index: list[pd.Timestamp] = []
    for date in betas.index:
        if date not in excess_returns.index:
            continue
        row_beta = betas.loc[date]
        row_ret = excess_returns.loc[date]

        # 按 beta 排序，切分成 n_groups 个分位数组合
        order = np.argsort(row_beta.values)
        groups = np.array_split(order, n_groups)

        g_beta = [row_beta.iloc[g].mean() for g in groups]
        g_ret = [row_ret.iloc[g].mean() for g in groups]
        x = sm.add_constant(np.asarray(g_beta, dtype=float))
        gamma = sm.OLS(np.asarray(g_ret, dtype=float), x).fit().params
        gammas.append(float(gamma[1]))
        index.append(date)
    return pd.Series(gammas, index=pd.DatetimeIndex(index), name="gamma_1_grouped")


def plot_gamma_series(gamma: pd.Series, title: str, path: Path) -> None:
    """绘制 gamma_1 时间序列图与累计均值。"""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gamma.index, gamma.values, lw=0.8, color="steelblue", label="gamma_1(t)")
    ax.axhline(gamma.mean(), color="crimson", ls="--", lw=1.2, label=f"均值 {gamma.mean():.4f}")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    cfg = SimulationConfig()
    excess_returns, market_excess, true_betas = simulate_data(cfg)

    # ------------------------------------------------------------------
    # Step 1：时间序列滚动回归估计 beta
    # ------------------------------------------------------------------
    # 论文做法：用截至 t-1 月的 60 个月窗口估计 beta，再与 t 月收益做横截面，
    # 避免 look-ahead（beta 估计不包含当期收益信息）。
    betas = rolling_betas(excess_returns, market_excess, cfg.window).shift(1).dropna()
    betas_mean = betas.mean()

    # ------------------------------------------------------------------
    # Step 2：每月横截面回归，得到 gamma_1 时间序列
    # ------------------------------------------------------------------
    gamma1 = cross_sectional_regressions(excess_returns, betas)
    gamma1_grouped = portfolio_groups(excess_returns, betas, n_groups=10)

    # ------------------------------------------------------------------
    # Step 3：Fama-MacBeth t 检验
    # ------------------------------------------------------------------
    mean_g, std_g, t_stat = fama_macbeth_t(gamma1)
    mean_gg, std_gg, t_stat_gg = fama_macbeth_t(gamma1_grouped)

    # ------------------------------------------------------------------
    # 输出报告
    # ------------------------------------------------------------------
    print("=" * 62)
    print("Fama-MacBeth (1973) 两阶段横截面检验复现报告")
    print("=" * 62)
    print(f"模拟样本：{cfg.n_months} 个月 × {cfg.n_stocks} 只股票")
    print(f"Beta 滚动窗口：{cfg.window} 个月；真实市场风险溢价：{cfg.true_market_premium:.4f}/月")
    print()

    print("Step 1 — 时间序列 beta 估计")
    print(f"  beta 横截面分布：均值 {betas_mean.mean():.3f}，"
          f"范围 [{betas_mean.min():.3f}, {betas_mean.max():.3f}]")
    print(f"  真实 beta 范围：[{true_betas.min():.3f}, {true_betas.max():.3f}]")
    print(f"  估计 beta 与真实 beta 相关系数：{betas_mean.corr(true_betas):.3f}")
    print()

    print("Step 2/3 — 横截面回归与 Fama-MacBeth t 检验")
    print(f"  [个股横截面]  gamma_1 均值 = {mean_g:.5f}，"
          f"std = {std_g:.5f}，t = {t_stat:.2f}，样本 = {len(gamma1)}")
    print(f"  [分组横截面]  gamma_1 均值 = {mean_gg:.5f}，"
          f"std = {std_gg:.5f}，t = {t_stat_gg:.2f}，样本 = {len(gamma1_grouped)}")
    print()
    print(f"  真实市场溢价：{cfg.true_market_premium:.5f}；"
          f"市场收益样本均值：{float(market_excess.mean()):.5f}")
    print()

    print("解读：")
    if t_stat > 1.96:
        verdict = "显著为正 -- 与 CAPM 预期一致：beta 与平均收益正相关，市场风险被定价。"
    else:
        verdict = "不显著 -- 模拟数据下 CAPM 应成立，请检查参数或随机种子。"
    print(f"  个股横截面 t = {t_stat:.2f} > 1.96 => {verdict}")
    print(f"  分组方法 t = {t_stat_gg:.2f}（分组可降低 beta 估计误差，结果应更稳定）")
    print()
    print("  统计要点：横截面斜率 gamma_1 的期望值等于市场溢价 E[Rm]（乘衰减因子），")
    print("  其显著性取决于市场波动 sqrt(T) 的相对大小 -- 这正是资产定价检验"
          "功效低的根源。")
    print()

    # ------------------------------------------------------------------
    # 稳健性检查：gamma_1 与真实溢价的偏差
    # ------------------------------------------------------------------
    bias = mean_g - cfg.true_market_premium
    print(f"  估计值相对真实溢价的偏差：{bias:+.5f}")
    print()

    # 图表
    plot_gamma_series(gamma1, "个股横截面 gamma_1 时间序列（Fama-MacBeth）", OUTPUT_DIR / "fm1973_gamma1.png")
    plot_gamma_series(gamma1_grouped, "分组横截面 gamma_1 时间序列（Fama-MacBeth）", OUTPUT_DIR / "fm1973_gamma1_grouped.png")

    # 汇总表
    summary = pd.DataFrame(
        {
            "个股横截面": [mean_g, std_g, t_stat],
            "分组横截面": [mean_gg, std_gg, t_stat_gg],
        },
        index=["gamma_1 均值", "gamma_1 标准差", "t 统计量"],
    )
    summary.to_csv(OUTPUT_DIR / "fm1973_summary.csv", encoding="utf-8-sig")
    print(f"结果已保存：{OUTPUT_DIR}")
    print("  - fm1973_summary.csv（汇总表）")
    print("  - fm1973_gamma1.png（个股 gamma_1 序列图）")
    print("  - fm1973_gamma1_grouped.png（分组 gamma_1 序列图）")


if __name__ == "__main__":
    main()
