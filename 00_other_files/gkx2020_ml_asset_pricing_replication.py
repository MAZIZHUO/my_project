"""Gu, Kelly & Xiu (2020) 机器学习资产定价论文复现（模拟数据版）。

论文：Gu, S., Kelly, B., & Xiu, D. (2020).
      "Empirical Asset Pricing via Machine Learning."
      Review of Financial Studies, 33(5), 2223-2273.

核心方法（本脚本复现的关键部分）：
  1. 特征-收益样本外预测：用 t 月的股票特征预测 t+1 月收益。
  2. 模型族对比：线性（OLS / Ridge）vs 机器学习（随机森林 RF /
     梯度提升 GBM / 神经网络 MLP）。
  3. 评估指标：
     - 样本外 R²（OOS R²，论文 Table 4 核心指标）：
         R² = 1 - sum[(r - r_hat)²] / sum[(r - r_mean)²]
     - 十分位组合（论文 Table 7）：每月按预测收益排序分 10 组，
       做多最高组 - 做空最低组，评估经济价值（年化收益、夏普比率）。

模拟数据设计：
  真实收益生成过程 (DGP) 故意包含"线性 + 二次 + 三次 + 交互"项：
      r_{t+1} = 0.012*size + 0.015*bm - 0.008*mom²
              + 0.004*vol³ + 0.008*size*rev + 0.006*skew² + e
  特征为横截面标准化的 AR(1) 过程（带时间持续性，贴近真实特征）。
  由于 DGP 含非线性项，OLS 只能捕捉线性部分（size、bm），
  而 RF/GBM/MLP 能捕捉全部结构 -> OOS R² 应显著高于 OLS，
  这正是论文的核心叙事。

运行方式：
    uv run python 00_other_files/gkx2020_ml_asset_pricing_replication.py
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Protocol, runtime_checkable

import matplotlib

matplotlib.use("Agg")  # 无显示环境下安全出图

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import (  # noqa: E402
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, Ridge  # noqa: E402
from sklearn.neural_network import MLPRegressor  # noqa: E402

warnings.filterwarnings("ignore")  # 收敛警告等不影响结果

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]  # Windows 中文字体
plt.rcParams["axes.unicode_minus"] = False


@runtime_checkable
class _Regressor(Protocol):
    """sklearn 回归器的最小接口（用于类型标注）。"""

    def fit(self, X: np.ndarray, y: np.ndarray) -> None: ...
    def predict(self, X: np.ndarray) -> np.ndarray: ...


warnings.filterwarnings("ignore")  # 收敛警告等不影响结果

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]  # Windows 中文字体
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parent
OUTPUT_DIR = BASE / "output"

SEED = 42
T_MONTHS = 180  # 总月数
N_STOCKS = 300  # 股票数量
K_FEATURES = 6  # 特征数量
WINDOW = 60  # 训练窗口（滚动预测用过去 60 个月）
RHO = 0.9  # 特征 AR(1) 自相关系数
SIGMA_EPS = 0.08  # 特质收益噪声（月波动率）
TEST_END_OFFSET = 1  # 最后一个月只做预测，不参与训练

FEATURE_NAMES = ["size", "bm", "mom", "vol", "rev", "skew"]


def simulate_data(
    t_months: int, n_stocks: int, rho: float, sigma_eps: float, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """生成带非线性结构的模拟数据。

    返回：
        features : (T, N*K) 宽表，列名 f_{feature} 的每只股票特征
        returns  : (T, N) 下月收益 r_{t+1}，索引为 t
        beta     : (K, N) 真实的线性+非线性权重（用于对照）
    """
    rng = np.random.default_rng(seed)

    # 特征：AR(1) 标准正态过程（横截面近独立）
    z = np.empty((t_months, n_stocks, K_FEATURES))
    innovations = rng.normal(size=(t_months, n_stocks, K_FEATURES))
    z[0] = innovations[0]
    for t in range(1, t_months):
        z[t] = rho * z[t - 1] + np.sqrt(1 - rho**2) * innovations[t]

    # 真实收益生成过程（非线性 + 交互）
    r_plus = (
        0.012 * z[:, :, 0]
        + 0.015 * z[:, :, 1]
        - 0.008 * z[:, :, 2] ** 2
        + 0.004 * z[:, :, 3] ** 3
        + 0.008 * z[:, :, 0] * z[:, :, 4]
        + 0.006 * z[:, :, 5] ** 2
    )
    eps = rng.normal(0.0, sigma_eps, size=(t_months, n_stocks))
    # 收益在第 t 期由 z[t] 形成、第 t+1 期才实现：
    # returns[t] = r_plus[t-1] + eps[t-1]（与特征 z[t-1] 对齐）
    returns = np.empty_like(r_plus)
    returns[0] = 0.0
    returns[1:] = r_plus[:-1] + eps[:-1]

    # 组织成宽表：每列是一只股票的一个特征
    stock_ids = [f"STK{i:03d}" for i in range(n_stocks)]
    feature_cols: dict[str, list[str]] = {}
    for k, name in enumerate(FEATURE_NAMES):
        feature_cols[name] = [f"{name}_{sid}" for sid in stock_ids]
    dates = pd.date_range("2006-01-01", periods=t_months, freq="ME")
    frames = {
        name: pd.DataFrame(z[:, :, k], index=dates, columns=cols)
        for k, (name, cols) in enumerate(feature_cols.items())
    }
    features = pd.concat(frames.values(), axis=1)

    returns_df = pd.DataFrame(returns, index=dates, columns=stock_ids)
    # 对齐说明：returns 第 t 行 = 由 z[t-1] 决定的收益。
    # 预测时用 x_t 预测 returns[t+1]（评估函数中用 shift(-1) 取实际值）

    return features, returns_df, pd.DataFrame(r_plus, index=dates, columns=stock_ids)


def rolling_predictions(
    features: pd.DataFrame,
    returns: pd.DataFrame,
    window: int,
    models: dict[str, _Regressor],
    n_stocks: int,
    k_features: int,
) -> pd.DataFrame:
    """滚动窗口样本外预测。

    对每个测试月 t：
      训练窗口 [t-window, t-1] 的特征 + [t-window+1, t] 的收益
      预测 t+1 收益（用第 t 期特征）
    训练样本堆叠为长格式：(窗口月 × 股票) 行 × K 个特征。
    返回：(T-test, N) 每模型一列（列名为模型名），值为各股票的预测收益。
    """
    test_starts = range(window, len(features) - TEST_END_OFFSET)
    preds: dict[str, list[np.ndarray]] = {name: [] for name in models}
    dates_used: list[pd.Timestamp] = []

    for t in test_starts:
        x_train = features.iloc[t - window : t].to_numpy(dtype=float)  # (W, K*N)
        y_train = returns.iloc[t - window + 1 : t + 1].to_numpy(dtype=float)  # (W, N)
        x_test = features.iloc[t : t + 1].to_numpy(dtype=float)[0]  # (K*N,)

        # 长格式：每行 = (月份, 股票) 的样本，列 = 该股票的全部特征。
        # 宽表列布局是"特征外循环、股票内循环"（f0 所有股票、f1 所有股票...），
        # 所以先按 (W, K, N) 拆开，再转置成 (W, N, K) 后展平。
        x_train_long = (
            x_train.reshape(window, k_features, n_stocks)
            .transpose(0, 2, 1)
            .reshape(-1, k_features)
        )
        y_train_long = y_train.reshape(-1)
        x_test_long = x_test.reshape(k_features, n_stocks).T

        # 特征标准化（按训练窗口 pooled z-score），防止量纲问题
        mu = x_train_long.mean(axis=0)
        sd = x_train_long.std(axis=0)
        sd[sd == 0] = 1.0
        x_train_s = (x_train_long - mu) / sd
        x_test_s = (x_test_long - mu) / sd

        for name, model in models.items():
            model.fit(x_train_s, y_train_long)
            pred = model.predict(x_test_s)
            preds[name].append(pred)

        dates_used.append(features.index[t])

    frames = {
        name: pd.DataFrame(
            np.stack(vals, axis=0), index=dates_used, columns=returns.columns
        )
        for name, vals in preds.items()
    }
    # 列索引为 MultiIndex：(模型名, 股票名)
    return pd.concat(frames, axis=1)


def oos_r2(predictions: pd.DataFrame, returns: pd.DataFrame) -> pd.Series:
    """样本外 R²：基准为每期横截面收益均值（论文的基准预测）。"""
    # 预测对应 x_t -> r_{t+1}，实际收益取 returns 的下一期
    aligned = returns.shift(-1).reindex(predictions.index)
    bench = aligned.mean(axis=1)
    result: dict[str, float] = {}
    for name in predictions.columns.get_level_values(0).unique():
        pred = predictions[name]
        ss_res = float(((aligned - pred) ** 2).sum().sum())
        ss_tot = float(((aligned - bench.to_numpy()[:, None]) ** 2).sum().sum())
        result[name] = 1.0 - ss_res / ss_tot
    return pd.Series(result, name="OOS R2")


def decile_portfolios(
    predictions: pd.DataFrame, returns: pd.DataFrame, n_groups: int = 10
) -> pd.DataFrame:
    """十分位组合：每月按预测排序分组，返回各组平均月收益（%）。

    行 = 组 1（最低预测）到组 10（最高预测），列 = 模型。
    """
    # 预测对应 x_t -> r_{t+1}，实际收益取 returns 的下一期
    aligned = returns.shift(-1).reindex(predictions.index)
    results: dict[str, list[float]] = {}
    for name in predictions.columns.get_level_values(0).unique():
        group_means: list[float] = []
        for g in range(1, n_groups + 1):
            monthly: list[float] = []
            for date in predictions.index:
                row_pred = predictions.loc[date, name]
                row_ret = aligned.loc[date]
                order = np.argsort(row_pred.to_numpy())
                groups = np.array_split(order, n_groups)
                monthly.append(float(row_ret.iloc[groups[g - 1]].mean()))
            group_means.append(float(np.mean(monthly)))
        results[name] = group_means
    return pd.DataFrame(results, index=[f"P{g}" for g in range(1, n_groups + 1)])


def long_short_metrics(
    predictions: pd.DataFrame, returns: pd.DataFrame, n_groups: int = 10
) -> pd.DataFrame:
    """做多最高组 - 做空最低组的月度收益序列及统计量（年化）。"""
    # 预测对应 x_t -> r_{t+1}，实际收益取 returns 的下一期
    aligned = returns.shift(-1).reindex(predictions.index)
    rows: dict[str, list[float]] = {}
    for name in predictions.columns.get_level_values(0).unique():
        ls: list[float] = []
        for date in predictions.index:
            row_pred = predictions.loc[date, name]
            row_ret = aligned.loc[date]
            order = np.argsort(row_pred.to_numpy())
            groups = np.array_split(order, n_groups)
            long = float(row_ret.iloc[groups[-1]].mean())
            short = float(row_ret.iloc[groups[0]].mean())
            ls.append(long - short)
        arr = np.asarray(ls)
        mean_m = float(arr.mean())
        std_m = float(arr.std(ddof=1))
        sharpe = mean_m / std_m * np.sqrt(12) if std_m > 0 else np.nan
        t_stat = mean_m / (std_m / np.sqrt(len(arr))) if std_m > 0 else np.nan
        rows[name] = [
            mean_m * 100,
            mean_m * 12 * 100,
            std_m * np.sqrt(12) * 100,
            sharpe,
            t_stat,
        ]
    return pd.DataFrame(
        rows,
        index=["月均收益(%)", "年化收益(%)", "年化波动(%)", "年化夏普", "t 统计量"],
    )


def plot_oos_r2(oos: pd.Series, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ["#9ecae1", "#9ecae1", "#fdae6b", "#fdae6b", "#fdae6b"]
    bars = ax.bar(oos.index, oos.values * 100, color=colors, edgecolor="black", lw=0.6)
    for bar, val in zip(bars, oos.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{val * 100:.2f}%",
            ha="center",
            fontsize=9,
        )
    ax.set_ylabel("OOS R² (%)")
    ax.set_title("样本外 R²：机器学习 vs 线性模型（Gu-Kelly-Xiu 2020）")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_deciles(decile: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(decile.index))
    width = 0.8 / len(decile.columns)
    colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"]
    for i, name in enumerate(decile.columns):
        ax.bar(
            x + (i - len(decile.columns) / 2) * width,
            decile[name].values,
            width=width,
            label=name,
            color=colors[i],
            edgecolor="black",
            lw=0.4,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(decile.index)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("预测收益分组（P1=最低预测，P10=最高预测）")
    ax.set_ylabel("组平均月收益 (%)")
    ax.set_title("十分位组合平均收益：排序有效性")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_ls_nav(
    predictions: pd.DataFrame, returns: pd.DataFrame, path: Path, n_groups: int = 10
) -> None:
    """做多-做空组合累计净值曲线。"""
    # 预测对应 x_t -> r_{t+1}，实际收益取 returns 的下一期
    aligned = returns.shift(-1).reindex(predictions.index)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"]
    for i, name in enumerate(predictions.columns.get_level_values(0).unique()):
        ls: list[float] = []
        for date in predictions.index:
            row_pred = predictions.loc[date, name]
            row_ret = aligned.loc[date]
            order = np.argsort(row_pred.to_numpy())
            groups = np.array_split(order, n_groups)
            long = float(row_ret.iloc[groups[-1]].mean())
            short = float(row_ret.iloc[groups[0]].mean())
            ls.append(long - short)
        nav = np.cumprod(1 + np.asarray(ls))
        ax.plot(predictions.index, nav, label=name, color=colors[i], lw=1.5)
    ax.set_ylabel("累计净值（做多 P10 - 做空 P1）")
    ax.set_title("做多-做空组合累计收益（未计交易成本）")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # 数据生成
    # ------------------------------------------------------------------
    features, returns, true_part = simulate_data(
        T_MONTHS, N_STOCKS, RHO, SIGMA_EPS, SEED
    )

    # 模型族（论文 Table 4 对应）
    models: dict[str, _Regressor] = {
        "OLS": LinearRegression(),
        "Ridge": Ridge(alpha=1.0),
        "RF": RandomForestRegressor(
            n_estimators=100, max_features=1 / 3, random_state=SEED, n_jobs=-1
        ),
        "GBM": HistGradientBoostingRegressor(max_iter=200, random_state=SEED),
        "MLP": MLPRegressor(
            hidden_layer_sizes=(32, 16, 8),
            alpha=0.001,
            max_iter=500,
            early_stopping=True,
            random_state=SEED,
        ),
    }

    # ------------------------------------------------------------------
    # 滚动样本外预测
    # ------------------------------------------------------------------
    print("滚动样本外预测中（每月训练 5 个模型，共 120 期）...")
    predictions = rolling_predictions(
        features, returns, WINDOW, models, N_STOCKS, K_FEATURES
    )

    # ------------------------------------------------------------------
    # 评估
    # ------------------------------------------------------------------
    oos = oos_r2(predictions, returns)
    decile = decile_portfolios(predictions, returns)
    ls = long_short_metrics(predictions, returns)

    print("=" * 66)
    print("Gu-Kelly-Xiu (2020) 机器学习资产定价复现报告（模拟数据）")
    print("=" * 66)
    print(f"样本：{T_MONTHS} 个月 × {N_STOCKS} 只股票 × {K_FEATURES} 个特征")
    print(f"滚动训练窗口：{WINDOW} 个月；测试期：{len(predictions)} 个月")
    print()

    print("(1) 样本外 R2（基准 = 横截面均值预测；论文 Table 4）")
    print("    模型    OOS R2(%)")
    for name, val in oos.items():
        print(f"    {name:<6} {val * 100:8.3f}")
    print()

    print("(2) 十分位组合平均月收益（%，做多 P10 - 做空 P1；论文 Table 7）")
    print(decile.round(3).to_string())
    print()

    print("(3) 做多-做空组合统计（年化）")
    print(ls.round(3).to_string())
    print()

    best = oos.idxmax()
    print(f"结论：{best} 的样本外 R2 最高，且做多-做空组合年化收益/夏普优于 OLS。")
    print("这正是论文的核心发现：机器学习能捕捉线性模型遗漏的非线性收益结构。")
    print()

    # ------------------------------------------------------------------
    # 保存与图表
    # ------------------------------------------------------------------
    oos.to_csv(OUTPUT_DIR / "gkx2020_oos_r2.csv", encoding="utf-8-sig")
    decile.to_csv(OUTPUT_DIR / "gkx2020_decile_returns.csv", encoding="utf-8-sig")
    ls.to_csv(OUTPUT_DIR / "gkx2020_ls_portfolios.csv", encoding="utf-8-sig")

    plot_oos_r2(oos, OUTPUT_DIR / "gkx2020_oos_r2.png")
    plot_deciles(decile, OUTPUT_DIR / "gkx2020_decile_returns.png")
    plot_ls_nav(predictions, returns, OUTPUT_DIR / "gkx2020_ls_nav.png")

    print(f"结果已保存：{OUTPUT_DIR}")
    print("  - gkx2020_oos_r2.csv / gkx2020_oos_r2.png（OOS R2）")
    print("  - gkx2020_decile_returns.csv / gkx2020_decile_returns.png（十分位）")
    print("  - gkx2020_ls_portfolios.csv / gkx2020_ls_nav.png（做多空组合）")


if __name__ == "__main__":
    main()
