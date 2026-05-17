import json
from pathlib import Path

import pandas as pd
import plotly.express as px

# 1. 读取文件并提取日期、最高温度和最低温度
current_dir = Path(__file__).parent
file_path = current_dir / "eq_data" / "eq_data_30_day_m1.geojson"
contents = file_path.read_text(encoding="utf-8")  # 读取文件内容并将其解码为字符串
all_eq_data = json.loads(
    contents
)  # 将字符串解析为Python对象（通常是字典或列表）  json.loads()函数将JSON字符串转换为Python对象。它接受一个字符串参数，并返回一个Python对象，通常是一个字典或列表，具体取决于JSON数据的结构。

# new_file_path = current_dir / "eq_data" / "readable_eq_data.json"
# readable_contents = json.dumps(
#     all_eq_data, indent=4
# )  # 将Python对象转换为JSON字符串，并使用indent参数指定缩进级别，使输出的JSON字符串更易读
# new_file_path.write_text(readable_contents)
# # json.dumps()函数将Python对象转换为JSON字符串。它接受一个Python对象作为参数，并返回一个JSON格式的字符串。indent参数用于指定缩进级别，使输出的JSON字符串更易读。
# # 2. 创建一个列表，用于存储所有eq_data_all_day.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geojson文件中的eq_data_1_day_m1.geo


mags, titles, lons, lats = [], [], [], []
for item in all_eq_data["features"]:
    mag = item["properties"]["mag"]
    title = item["properties"]["title"]
    lon = item["geometry"]["coordinates"][0]
    lat = item["geometry"]["coordinates"][1]
    mags.append(mag)
    titles.append(title)
    lons.append(lon)
    lats.append(lat)


# fig = px.scatter_geo(
#     lon=lons,  # 经度，geo图必须用lon和lat参数
#     lat=lats,
#     size=mags,  # 根据震级大小决定散点(圆圈)的大小
#     color=mags,  # 根据震级大小决定颜色深浅
#     color_continuous_scale="Viridis",  # 选择一个好看的渐变色板 (例如 Viridis)
#     width=800,  # 设置图表的宽度
#     height=800,  # 设置图表的高度
#     labels={
#         "lat": "Latitude",
#         "lon": "Longitude",
#     },
#     title="Global Earthquakes",
#     hover_name=titles,
# )

# 创建一个DataFrame对象，包含经度、纬度、标题和震级数据,columns参数指定列的名称,zip函数将多个列表或元组转换为一个DataFrame对象
data = pd.DataFrame(
    data=zip(lons, lats, titles, mags),
    columns=["经度", "纬度", "位置", "震级"],
)

fig = px.scatter(
    data,
    x="经度",
    y="纬度",
    range_x=[-200, 200],
    range_y=[-90, 90],
    width=800,
    height=800,
    labels={
        "经度": "经度",
        "纬度": "纬度",
    },
    title="全球地震",
    hover_name="位置",  # 鼠标悬停时显示的列
    size="震级",
    size_max=20,
    color="震级",
    color_continuous_scale="Viridis",
)

fig.show()
