import sys
from pathlib import Path


def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, "frozen", False):  # 是否被 pyinstaller 打包
        base_path = Path(
            sys._MEIPASS
        )  # 如果是双击运行，则获取当前目录，如果是被 pyinstaller 打包，则获取临时目录
    else:
        base_path = Path(__file__).parent
    return base_path / relative_path  # 返回资源文件的绝对路径
