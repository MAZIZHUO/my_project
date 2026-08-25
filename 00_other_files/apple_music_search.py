"""Apple Music / iTunes 目录搜索工具（零第三方依赖）。

用法示例：
    uv run python apple_music_search.py "Taylor Swift"
    uv run python apple_music_search.py "周杰伦" --media album --limit 20
    uv run python apple_music_search.py "Coldplay" --save data.json
    uv run python apple_music_search.py "播客" --media podcast --country US
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"

MEDIA_TYPES = {
    "song": "歌曲",
    "album": "专辑",
    "artist": "艺人",
    "movie": "电影",
    "podcast": "播客",
    "musicVideo": "音乐视频",
    "ebook": "电子书",
}

# 展示时用到的字段：键 -> 中文列名
DISPLAY_FIELDS = [
    ("trackName", "名称"),
    ("artistName", "艺人"),
    ("collectionName", "专辑"),
    ("releaseDate", "发行日期"),
    ("trackPrice", "价格"),
    ("currency", "货币"),
]


def fetch_results(
    term: str,
    media: str = "song",
    limit: int = 10,
    country: str = "CN",
) -> list[dict[str, Any]]:
    """调用 iTunes Search API 获取搜索结果。"""
    params = f"term={quote(term)}&entity={media}&limit={limit}&country={country}"
    url = f"{ITUNES_SEARCH_URL}?{params}"
    with urlopen(url, timeout=15) as resp:
        payload = json.loads(resp.read())
    return payload.get("results", [])


def _char_width(text: str) -> int:
    """计算字符串显示宽度（中文等全角字符按 2 计）。"""
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in text)


def _truncate(text: str | None, width: int) -> str:
    """按字符宽度截断（中文按 2 个宽度计算）。"""
    if not text:
        return ""
    text = str(text)
    current = 0
    for i, ch in enumerate(text):
        current += 2 if ord(ch) > 0x2E7F else 1
        if current > width - 1:
            return text[:i] + "…"
    return text


def print_table(results: list[dict[str, Any]]) -> None:
    """以对齐表格打印结果。"""
    if not results:
        print("没有找到结果。")
        return

    headers = [label for _, label in DISPLAY_FIELDS]
    widths = [_char_width(h) for h in headers]
    rows: list[list[str]] = []
    for item in results:
        row = [str(item.get(key, "")) for key, _ in DISPLAY_FIELDS]
        rows.append(row)
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], _char_width(cell))

    def render(cell: str, width: int) -> str:
        return _truncate(cell, width).ljust(width)

    print(" | ".join(render(h, w) for h, w in zip(headers, widths)))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(" | ".join(render(c, w) for c, w in zip(row, widths)))
    print(f"\n共 {len(results)} 条结果")


def print_stats(results: list[dict[str, Any]]) -> None:
    """按艺人统计歌曲数量。"""
    if not results:
        return
    counts: dict[str, int] = {}
    for item in results:
        artist = item.get("artistName") or "未知艺人"
        counts[artist] = counts.get(artist, 0) + 1
    print("按艺人统计：")
    for artist, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {artist}: {count} 条")


def save_json(results: list[dict[str, Any]], path: Path) -> None:
    path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已保存 JSON: {path}")


def save_csv(results: list[dict[str, Any]], path: Path) -> None:
    if not results:
        print("没有结果可保存。")
        return
    keys = [key for key, _ in DISPLAY_FIELDS]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows({k: item.get(k, "") for k in keys} for item in results)
    print(f"已保存 CSV: {path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="搜索 Apple Music / iTunes 目录数据",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "term", nargs="?", help="搜索关键词（艺人 / 歌曲 / 专辑名），不填则进入交互模式"
    )
    parser.add_argument(
        "--media",
        choices=MEDIA_TYPES,
        default="song",
        help="媒体类型",
    )
    parser.add_argument("--limit", type=int, default=10, help="返回条数")
    parser.add_argument("--country", default="CN", help="国家/地区代码（CN/US/JP...）")
    parser.add_argument("--save", type=Path, help="将结果保存为 JSON 文件")
    parser.add_argument("--csv", type=Path, help="将结果保存为 CSV 文件")
    parser.add_argument("--stats", action="store_true", help="按艺人统计数量")
    return parser.parse_args(argv)


def _prompt_term() -> str:
    """交互模式：让用户输入搜索关键词。"""
    while True:
        term = input("请输入搜索关键词（回车退出）：").strip()
        if not term:
            raise SystemExit(0)
        return term


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not args.term:
        print("未提供搜索词，进入交互模式（直接运行脚本可用）\n")
        args.term = _prompt_term()

    print(
        f"搜索：{args.term}（{MEDIA_TYPES[args.media]}，"
        f"地区 {args.country}，最多 {args.limit} 条）\n"
    )
    try:
        results = fetch_results(args.term, args.media, args.limit, args.country)
    except Exception as exc:  # noqa: BLE001 - 命令行工具，统一兜底
        print(f"请求失败：{exc}", file=sys.stderr)
        return 1

    print_table(results)
    if args.stats:
        print()
        print_stats(results)
    if args.save:
        save_json(results, args.save)
    if args.csv:
        save_csv(results, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
