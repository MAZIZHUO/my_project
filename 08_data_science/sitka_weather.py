import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt

# 从文件中获取日期、最高温度和最低温度
current_dir = Path(__file__).parent
file_path = current_dir / "weather_data" / "sitka_weather_2021_simple.csv"
lines = file_path.read_text().splitlines()  # 读取文件内容并将其分割成行

reader = csv.reader(lines)  # 创建一个csv.reader对象来读取文件内容
print(
    reader
)  # 由于 reader 是迭代器，你可以把它想象成一根吸管。print(reader) 只是给你看了这根吸管本身，要想尝到饮料（数据），你必须用 next() 吸一口，或者用 for 循环一口口吸完。
# 打印前 5 行的原始内容
for line in lines[:5]:
    print(line)

header_row = next(reader)  # 读取文件的第一行作为表头，next()方法返回下一行的内容

# 打印文件头
print(header_row)
for index, column_header in enumerate(
    header_row
):  # 遍历表头并打印索引和列头,enumerate用于获取索引和值
    print(index, column_header)


# 获取日期、最高温度和最低温度
dates, highs, lows = [], [], []  # 创建三个空列表来存储日期、最高温度和最低温度
for row in reader:  # 遍历剩余的行
    current_date = datetime.strptime(row[2], "%Y-%m-%d")  # 获取当前行的日期
    high = int(row[4])  # 获取当前行的最高温度
    low = int(row[5])  # 获取当前行的最低温度
    dates.append(current_date)  # 将当前日期添加到dates列表中
    highs.append(high)  # 将当前最高温度添加到highs列表中
    lows.append(low)  # 将当前最低温度添加到lows列表中

print(dates[:5])  # 打印前 5 个日期
print(highs[:5])  # 打印前 5 个最高温度
print(lows[:5])  # 打印前 5 个最低温度

# 使用 Matplotlib 绘制最高温度和最低温度的图表
plt.style.use("seaborn-v0_8")  # 设置图表的样式
fig, ax = plt.subplots()
ax.plot(
    dates, highs, c="red", alpha=0.5
)  # 绘制最高温度的折线图，使用红色（c="red"）和半透明（alpha=0.5）
ax.plot(
    dates, lows, c="blue", alpha=0.5
)  # 绘制最低温度的折线图，使用蓝色（c="blue"）和半透明（alpha=0.5）
ax.fill_between(
    dates, highs, lows, facecolor="blue", alpha=0.1
)  # 填充最高温度和最低温度之间的区域

# 设置图表的格式
ax.set_title("Daily high and low temperatures - 2021", fontsize=24)
ax.set_xlabel(
    "", fontsize=16
)  # 由于 x 轴上的日期标签太密集了，无法正常显示，因此我们将 x 轴的标签设置为空字符串。
fig.autofmt_xdate()  # 自动调整 x 轴上的日期标签，使其以斜体显示并避免重叠
ax.set_ylabel(
    "Temperature (F)", fontsize=16
)  # 设置 y 轴的标签为 "Temperature (F)"，并将字体大小设置为 16
ax.tick_params(
    axis="both", which="major", labelsize=12
)  # 设置 x 轴和 y 轴的主刻度标签的字体大小为 12

plt.show()
