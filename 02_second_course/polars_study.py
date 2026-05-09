# Polars 入门学习
# Polars 是一个高性能的数据分析库，常用来处理表格数据。
# 它的功能和 pandas 类似，但在大数据、链式表达式、Lazy API 方面更有优势。

from pathlib import Path

import polars as pl


def show_title(title):
    """打印分隔标题，让运行结果更清楚。"""
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)


# ==================== 1. 创建 DataFrame ====================


def create_dataframe():
    """用字典创建 Polars DataFrame。"""
    students = pl.DataFrame(
        {
            "name": ["小明", "小红", "小刚", "小丽", "小强"],
            "class": ["一班", "一班", "二班", "二班", "一班"],
            "math": [90, 85, 76, 95, 88],
            "english": [82, 91, 80, 89, 73],
            "age": [18, 19, 18, 20, 19],
        }
    )
    return students


# ==================== 2. 查看数据 ====================


def basic_info(df):
    """查看 DataFrame 的基本信息。"""
    show_title("1. 查看数据")
    print("完整数据:")
    print(df)

    print("\n前 3 行:")
    print(df.head(3))

    print("\n数据形状:")
    print(df.shape)

    print("\n列名:")
    print(df.columns)

    print("\n字段类型:")
    print(df.schema)


# ==================== 3. 选择列和筛选行 ====================


def select_and_filter(df):
    """演示 select 和 filter。"""
    show_title("2. 选择列和筛选行")

    print("只选择姓名和数学成绩:")
    print(df.select(["name", "math"]))

    print("\n筛选数学成绩大于等于 88 的学生:")
    print(df.filter(pl.col("math") >= 88))

    print("\n筛选一班并且英语成绩大于 80 的学生:")
    print(df.filter((pl.col("class") == "一班") & (pl.col("english") > 80)))


# ==================== 4. 新增列和修改列 ====================


def add_columns(df):
    """用 with_columns 新增计算列。"""
    show_title("3. 新增列")

    result = df.with_columns(
        total=pl.col("math") + pl.col("english"),
        average=(pl.col("math") + pl.col("english")) / 2,
        passed=pl.col("math") >= 80,
    )

    print(result)
    return result


# ==================== 5. 排序 ====================


def sort_data(df):
    """按照成绩排序。"""
    show_title("4. 排序")

    print("按照总分从高到低排序:")
    print(df.sort("total", descending=True))


# ==================== 6. 分组统计 ====================


def group_data(df):
    """按照班级分组统计。"""
    show_title("5. 分组统计")

    result = df.group_by("class").agg(
        student_count=pl.len(),
        math_avg=pl.col("math").mean(),
        english_avg=pl.col("english").mean(),
        total_max=pl.col("total").max(),
    )

    print(result)


# ==================== 7. CSV 文件读写 ====================


def csv_example(df):
    """演示写入 CSV 和读取 CSV。"""
    show_title("6. CSV 文件读写")

    current_dir = Path(__file__).parent
    csv_path = current_dir / "students_polars.csv"

    df.write_csv(csv_path)
    print(f"已经写入 CSV 文件: {csv_path}")

    loaded_df = pl.read_csv(csv_path)
    print("\n从 CSV 读取的数据:")
    print(loaded_df)


# ==================== 8. Lazy API ====================


def lazy_example(df):
    """演示 Lazy API：先描述计算步骤，最后 collect 执行。"""
    show_title("7. Lazy API")

    result = (
        df.lazy()
        .filter(pl.col("math") >= 80)
        .with_columns(total=pl.col("math") + pl.col("english"))
        .select(["name", "class", "total"])
        .sort("total", descending=True)
        .collect()
    )

    print("Lazy 查询结果:")
    print(result)


# ==================== 9. 常用表达式总结 ====================


def expression_summary():
    """打印 Polars 常用写法。"""
    show_title("8. 常用写法总结")

    print("pl.col('列名')              选择某一列")
    print("df.select([...])            选择列")
    print("df.filter(条件)             筛选行")
    print("df.with_columns(...)        新增列或修改列")
    print("df.sort('列名')             排序")
    print("df.group_by('列名').agg(...) 分组统计")
    print("pl.read_csv('文件.csv')      读取 CSV")
    print("df.write_csv('文件.csv')     写入 CSV")
    print("df.lazy().collect()         使用 Lazy API")


# ==================== 运行示例 ====================


if __name__ == "__main__":
    students_df = create_dataframe()

    basic_info(students_df)
    select_and_filter(students_df)

    students_with_score = add_columns(students_df)
    sort_data(students_with_score)
    group_data(students_with_score)
    csv_example(students_with_score)
    lazy_example(students_df)
    expression_summary()
