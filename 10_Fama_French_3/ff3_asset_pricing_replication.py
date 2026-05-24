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


# isna() 返回布尔序列（True 表示空值）
# idxmax() 返回的是第一个最大值的索引。对于布尔序列（True=1, False=0）
# .any() 是 pandas/numpy 中的布尔方法，用于判断序列中是否存在至少一个 True 值
# df.iloc 是 pandas 中基于整数位置的索引器：过行/列的数值位置（0,1,2...）而非标签来选取数据，支持切片（如 [:5]）、列表（如 [[0,2,4]]）等操作
# df.iloc[:first_blank]，表示选取从第0行到first_blank（不含）的所有行
# .copy() 用于创建 DataFrame 的独立副本，避免后续操作影响原始数据


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


# 先导入F-F_Research_Data_Factors_daily.csv
# RF（Risk-Free Rate）表示无风险利率，通常采用短期国债收益率作为代理
# .apply(函数) 默认按列 操作：把第一列整个传给函数处理再把第二列整个传给函数处理依此类推
# pd.to_numeric 是 pandas 函数，用于把数据（Series、列表等）强制转换为数值类型（int/float）
# errors="coerce" 的意思：pd.to_numeric 遇到无法转换成数字的值时（比如空字符串 " "、文字、. 等），不报错直接把这个值变成 NaN（缺失值）
# dropna()：删除包含缺失值的行
# subset=[...]：只看这些指定的列，只要这几列中任意一列是 NaN，就把整行删掉
# set_index("Date")：把 "Date" 这一列变成 索引（index），不再是普通数据列
# 后面 merge 时用 left_index=True, right_index=True 就是靠这个日期索引对齐的


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


# port.merge(ff)：把两个 DataFrame 按日期索引合并
# left_index=True + right_index=True：用 port 和 ff 的索引（都是 Date）作为匹配键
# how="inner"：只保留两个表都有的日期（取交集）
# 对每个组合新建一列 _excess（超额收益）,计算公式：组合收益 - 无风险利率 (RF),data 里多了 6 列超额收益（如 SMALL LoBM_excess），后面回归用的就是这些超额收益。


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


# 时间序列回归，对每个投资组合单独做一次 OLS 回归，因变量：该组合的超额收益序列（y_col），自变量：MKT、SMB、HML 的时间序列（x）
# data[FACTOR_COLS] 取出 MKT、SMB、HML 三列
# sm.add_constant() 会在最左侧插入一列全为 1 的常数列（列名 "const"），const 列的值全是 1
# 因变量：y_col = f"{col}_excess"，表示组合的超额收益
# sm.OLS(y, x) 创建一个 OLS 模型对象，x 是自变量，y 是因变量
# model.fit() ，.fit()执行回归计算（最小二乘估计）
# 返回的 model 是一个回归结果对象，里面包含：params（系数：alpha、beta），tvalues（t 统计量），rsquared（R²）等
# 循环跑完 6 个组合后，rows 列表里会有 6 个字典。后面代码会把这个列表转成 DataFrame，形成最终的回归结果表格。
# pd.DataFrame(rows).set_index("portfolio")，把之前收集的 6 个字典转成 DataFrame，把 "portfolio" 列设为索引


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


# data[FACTOR_COLS]：选中 MKT、SMB、HML 三列，.agg(["mean", "std", "min", "max"])：对每列分别计算以下四个统计量
# .loc 是 pandas 中基于标签（label）的索引器，通过行标签名或列标签名来选取或修改数据
# 列表推导式，遍历 PORTFOLIO_COLS 里的每个组合名（如 "SMALL LoBM"），用 f-string 在后面加上 "_excess"
# .corr() 计算因子和超额收益之间的相关系数矩阵，选中 3 个因子（MKT、SMB、HML） + 6 个组合超额收益列，共 9 列
# 把相关系数矩阵 corr 的行标签和列标签里的 _excess 去掉，换成原来的干净组合名
# index=...：重命名行标签，columns=...：重命名列标签
# regression_table 来自 run_ff3_regressions 函数的返回值


def save_tables(factor_stats, portfolio_stats, corr, regression_table):
    OUTPUT_DIR.mkdir(exist_ok=True)
    factor_stats.to_csv(OUTPUT_DIR / "table_factor_statistics.csv")
    portfolio_stats.to_csv(OUTPUT_DIR / "table_portfolio_excess_return_statistics.csv")
    corr.to_csv(OUTPUT_DIR / "table_correlation_matrix.csv")
    regression_table.to_csv(OUTPUT_DIR / "table_ff3_regression_results.csv")


# OUTPUT_DIR 定义在文件顶部，是 output 文件夹的路径（Path 对象），.mkdir() 用于创建这个文件夹，exist_ok=True：如果文件夹已经存在，就不报错，直接跳过
# factor_stats.to_csv(...)：DataFrame 的导出方法


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


# data[excess_cols]：取出 6 个组合的超额收益列（单位是 百分比）
# / 100：把百分比转成小数（例如 0.05 → 0.0005），1 + ...：变成总收益（gross return），即 1 + r
# .cumprod()：逐行累乘（cumulative product）
# plt.figure(figsize=(11, 6))：创建一个新画布，大小 11×6 英寸
# for col in PORTFOLIO_COLS：对 6 个组合逐一画线，
# plt.plot(cumulative.index, cumulative[col], ...)：x 轴是日期，y 轴是该组合的累积收益plt.plot(cumulative.index, cumulative[col], ...)：x 轴是日期，y 轴是该组合的累积收益
# linewidth=1.2, label=col：线宽 + 图例名称
# plt.legend(ncol=3, fontsize=9)：图例排成 3 列，字体小一点
# plt.tight_layout()：自动调整布局，防止标签重叠
# plt.close()：关闭图形，释放内存（重要！多图时防止内存泄漏）


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


# fig：整个图形对象（Figure）,axes：包含 3 个子图的数组，后面可以用 axes[0]、axes[1]、axes[2] 分别操作
# figsize=(11, 7),设置整个图形的大小为 11 英寸宽 × 7 英寸高
# sharex=True：子图共享 x 轴
# ax.axhline(0, color="black", linewidth=0.6),在当前子图画一条 y=0 的黑色水平参考线
# ax.set_ylabel(factor),把当前子图的 y 轴标签设为因子名称（MKT / SMB / HML）
# 在 matplotlib 中，修改 Axes（子图） 的属性，必须使用以 set_ 开头的方法。推荐的面向对象接口，ax 就是具体的子图对象，所以要用 ax.set_xxx() 来设置


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


# regression_table：6 个投资组合的回归结果表（index 是组合名，包含 alpha、beta 等）
# .sort_values("alpha")：按 alpha 的大小排序
# np.where(条件, 满足时的值, 不满足时的值),满足（alpha ≥ 0）：颜色 "#2f6f73"（青绿色）
# x = plot_data.index：x 轴的类别（6 个组合名称，如 "SMALL LoBM"）
# height = plot_data["alpha"]：每个柱子的高度（对应组合的 alpha 值）
# plt.xticks(rotation=25, ha="right") 的作用：rotation=25：把 x 轴的文字旋转 25 度（倾斜显示）
# ha="right"：ha = horizontal alignment（水平对齐方式），设置为 "right"，即文字的右边对齐到对应的刻度位置


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


# sns.heatmap(...),绘制相关系数矩阵的热力图
# corr：要可视化的相关系数矩阵（9×9 的 DataFrame）
# cmap="vlag"：使用 seaborn 的 vlag 配色（发散色图，蓝色 → 白色 → 红色），适合展示以 0 为中心的相关性
# center=0：把颜色映射的中心固定在 0，让正相关和负相关在颜色上对称
# annot=False：不在格子里显示具体数值（如果改成 True 会显示相关系数的数字）
# square=True：让每个小格子都是正方形，视觉上更规整
# linewidths=0.3：格子之间加上白色细线（宽度 0.3），让格子分界更清晰
# cbar_kws={"shrink": 0.8}：控制右侧颜色条（colorbar）的大小，缩小到默认的 80%
# seaborn（sns）底层完全依赖 matplotlib 来绘图，默认情况下，seaborn 会画在 当前激活的 matplotlib 图 上


def save_figures(data, regression_table, corr):
    OUTPUT_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", font="Arial")
    plot_cumulative_returns(data)
    plot_factor_timeseries(data)
    plot_alpha_bar(regression_table)
    plot_correlation_heatmap(corr)


# sns.set_theme(style="whitegrid", font="Arial")，全局设置 seaborn 的绘图风格：style="whitegrid"：白色网格背景，font="Arial"：统一使用 Arial 字体
# 这个设置会影响后面所有 sns 和 plt 画的图（直到程序结束或再次修改）


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


# .strftime("%Y-%m-%d")：把 datetime 对象格式化成字符串，例如 "1990-07-02"
# Unit 单元/单位
# Interpretation 解释、诠释、理解


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
