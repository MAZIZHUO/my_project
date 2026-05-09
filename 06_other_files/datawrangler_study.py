"""
Data Wrangler 使用示例 - 模拟数据清洗完整流程

本示例演示如何使用 Data Wrangler 进行数据清洗，
以及导出为 Pandas 代码后的效果。
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ==================== 第一步：创建模拟原始数据 ====================


def create_sample_data():
    """
    创建包含各种数据问题的模拟数据集

    数据问题包括：
    - 缺失值 (NaN)
    - 重复行
    - 不一致的格式
    - 异常值
    - 需要转换的数据类型
    """
    np.random.seed(42)  # 设置随机种子，保证每次生成相同数据

    # 生成基础数据
    n_rows = 20
    data = {
        "user_id": [f"U{i:03d}" for i in range(1, n_rows + 1)],
        "name": [f"用户{i}" for i in range(1, n_rows + 1)],
        "age": np.random.randint(15, 65, n_rows),
        "salary": np.random.uniform(3000, 20000, n_rows).round(2),
        "join_date": [
            (datetime(2020, 1, 1) + timedelta(days=i * 30)).strftime("%Y/%m/%d")
            for i in range(n_rows)
        ],
        "department": np.random.choice(
            ["技术部", "销售部", "人事部", "财务部"], n_rows
        ),
        "performance_score": np.random.uniform(50, 100, n_rows).round(1),
        "is_active": np.random.choice([True, False], n_rows),
    }

    df = pd.DataFrame(data)

    # ==================== 人为制造数据问题 ====================

    # 1. 制造缺失值
    df.loc[2, "age"] = np.nan  # 年龄缺失
    df.loc[5, "salary"] = np.nan  # 薪资缺失
    df.loc[8, "department"] = np.nan  # 部门缺失
    df.loc[12, "join_date"] = np.nan  # 入职日期缺失

    # 2. 制造重复行
    duplicate_row = df.iloc[3].copy()
    df = pd.concat([df, pd.DataFrame([duplicate_row])], ignore_index=True)

    # 3. 制造异常值
    df.loc[15, "age"] = 200  # 不合理的年龄
    df.loc[16, "salary"] = -5000  # 负数薪资
    df.loc[17, "performance_score"] = 150  # 超过100分的绩效

    # 4. 制造不一致的数据格式
    df.loc[10, "user_id"] = "u011"  # 小写id
    df.loc[11, "name"] = "  用户12  "  # 前后空格

    return df


# ==================== 第二步：查看原始数据问题 ====================

print("=" * 80)
print("📊 原始数据概览")
print("=" * 80)

df_original = create_sample_data()
print(f"\n数据形状：{df_original.shape}")
print("\n前 5 行数据：")
print(df_original.head())

print("\n" + "=" * 80)
print("🔍 数据质量检查")
print("=" * 80)

print("\n1. 缺失值统计：")
print(df_original.isnull().sum())

print("\n2. 数据类型：")
print(df_original.dtypes)

print("\n3. 基本统计信息：")
print(df_original.describe())

print(f"\n4. 重复行数量：{df_original.duplicated().sum()}")

print("\n5. 异常值检测（年龄 > 100）：")
print(df_original[df_original["age"] > 100])

# ==================== 第三步：使用 Data Wrangler 进行数据清洗 ====================

print("\n" + "=" * 80)
print("🛠️  开始数据清洗（模拟 Data Wrangler 操作）")
print("=" * 80)

df = df_original.copy()

# ─────────────────────────────────────────────
# 操作 1：删除重复行
# ─────────────────────────────────────────────
print("\n[操作 1] 删除重复行")
print(f"删除前：{len(df)} 行")
df = df.drop_duplicates()
print(f"删除后：{len(df)} 行")

# ─────────────────────────────────────────────
# 操作 2：数据筛选 - 保留年龄合理的记录
# ─────────────────────────────────────────────
print("\n[操作 2] 筛选年龄合理的记录（18 <= age <= 65）")
print(f"筛选前：{len(df)} 行")
df = df[(df["age"] >= 18) & (df["age"] <= 65)]
print(f"筛选后：{len(df)} 行")

# ─────────────────────────────────────────────
# 操作 3：填充缺失值
# ─────────────────────────────────────────────
print("\n[操作 3] 填充缺失值")
print("填充前缺失值：")
print(df.isnull().sum())

# 年龄：用中位数填充
age_median = df["age"].median()
df["age"] = df["age"].fillna(age_median)
print(f"  - age: 用中位数 {age_median} 填充")

# 薪资：用 0 填充（或可用中位数）
df["salary"] = df["salary"].fillna(0)
print("  - salary: 用 0 填充")

# 部门：用 '未知' 填充
df["department"] = df["department"].fillna("未知")
print("  - department: 用 '未知' 填充")

# 入职日期：用最早日期填充
df["join_date"] = df["join_date"].fillna(df["join_date"].min())
print("  - join_date: 用最早日期填充")

print("\n填充后缺失值：")
print(df.isnull().sum())

# ─────────────────────────────────────────────
# 操作 4：处理异常值
# ─────────────────────────────────────────────
print("\n[操作 4] 处理异常值")

# 薪资为负数的处理为 0
negative_salary_count = (df["salary"] < 0).sum()
df.loc[df["salary"] < 0, "salary"] = 0
print(f"  - 修正负数薪资：{negative_salary_count} 条记录")

# 绩效分数超过 100 的修正为 100
high_score_count = (df["performance_score"] > 100).sum()
df.loc[df["performance_score"] > 100, "performance_score"] = 100
print(f"  - 修正超高分绩效：{high_score_count} 条记录")

# ─────────────────────────────────────────────
# 操作 5：数据格式标准化
# ─────────────────────────────────────────────
print("\n[操作 5] 数据格式标准化")

# user_id 统一转为大写
df["user_id"] = df["user_id"].str.upper()
print("  - user_id: 统一转为大写")

# name 去除前后空格
df["name"] = df["name"].str.strip()
print("  - name: 去除前后空格")

# join_date 转换为标准日期格式
df["join_date"] = pd.to_datetime(df["join_date"], format="%Y/%m/%d")
print("  - join_date: 转换为 datetime 类型")

# ─────────────────────────────────────────────
# 操作 6：重命名列
# ─────────────────────────────────────────────
print("\n[操作 6] 重命名列")
df = df.rename(
    columns={
        "user_id": "员工ID",
        "name": "姓名",
        "age": "年龄",
        "salary": "薪资",
        "join_date": "入职日期",
        "department": "部门",
        "performance_score": "绩效分数",
        "is_active": "是否在职",
    }
)
print("列名已重命名为中文")

# ─────────────────────────────────────────────
# 操作 7：添加计算列
# ─────────────────────────────────────────────
print("\n[操作 7] 添加计算列")

# 计算年薪
df["年薪"] = df["薪资"] * 12
print("  - 添加 '年薪' 列（薪资 * 12）")


# 绩效等级
def get_performance_level(score):
    if score >= 90:
        return "优秀"
    elif score >= 80:
        return "良好"
    elif score >= 70:
        return "合格"
    else:
        return "待改进"


df["绩效等级"] = df["绩效分数"].apply(get_performance_level)
print("  - 添加 '绩效等级' 列")

# ─────────────────────────────────────────────
# 操作 8：数据排序
# ─────────────────────────────────────────────
print("\n[操作 8] 数据排序")
df = df.sort_values(by=["部门", "薪资"], ascending=[True, False])
print("  - 按部门升序、薪资降序排序")

# ─────────────────────────────────────────────
# 操作 9：重置索引
# ─────────────────────────────────────────────
df = df.reset_index(drop=True)
print("\n[操作 9] 重置索引")

# ==================== 第四步：查看清洗后的数据 ====================

print("\n" + "=" * 80)
print("✅ 数据清洗完成")
print("=" * 80)

print(f"\n最终数据形状：{df.shape}")
print("\n清洗后的数据预览：")
print(df.head(10))

print("\n数据质量检查：")
print(f"  - 缺失值：{df.isnull().sum().sum()} 个")
print(f"  - 重复行：{df.duplicated().sum()} 行")

print("\n薪资统计：")
print(f"  - 平均薪资：{df['薪资'].mean():.2f}")
print(f"  - 最高薪资：{df['薪资'].max():.2f}")
print(f"  - 最低薪资：{df['薪资'].min():.2f}")

print("\n绩效等级分布：")
print(df["绩效等级"].value_counts())

# ==================== 第五步：导出数据 ====================

print("\n" + "=" * 80)
print("💾 导出清洗后的数据")
print("=" * 80)

# 导出为 CSV
output_file = "cleaned_employee_data.csv"
df.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"\n✅ 数据已导出到：{output_file}")

# 也可以导出为 Excel（需要 openpyxl）
try:
    df.to_excel("cleaned_employee_data.xlsx", index=False)
    print("✅ 数据已导出到：cleaned_employee_data.xlsx")
except Exception as e:
    print(f"⚠️  Excel 导出失败（可能需要安装 openpyxl）：{e}")

print("\n" + "=" * 80)
print("📝 总结：Data Wrangler 操作流程")
print("=" * 80)
print("""
以上所有操作都可以通过 Data Wrangler 的可视化界面完成：

1. 打开 CSV 文件 → 右键 "Open with Data Wrangler"
2. 在右侧操作面板中依次应用：
   ✓ Remove Duplicates（删除重复行）
   ✓ Filter（筛选数据）
   ✓ Fill Missing（填充缺失值）
   ✓ Replace Values（替换异常值）
   ✓ Transform（数据格式转换）
   ✓ Rename（重命名列）
   ✓ Add Column（添加计算列）
   ✓ Sort（排序）
3. 点击 "Export" → 生成 Python 代码
4. 运行生成的代码完成数据清洗

优势：
- 无需编写代码，可视化操作
- 实时预览每步效果
- 自动生成可复用的 Python 代码
- 操作历史可追溯、可撤销
""")
