#!/usr/bin/env python3
"""
S1：Deribit ETH 期权成交分片读取 + 合并为单文件（ETH_risk_premia_plan.md §1.1 步骤 ①；仅展平+合并）

本脚本做什么
------------
- 遍历输入目录中的 ``*.parquet``，跳过文件名含 ``sample`` 的分片（可调 ``--exclude``）。
- 将嵌套列 ``trade`` 展平为普通列，便于 CSV 存储与下游读取。
- 保留与 ``trade`` 同级的顶层列 ``s``、``t``（若存在）。
- 追加 ``source_file``、``datetime``、``trade_date``、``year``，便于追溯来源与按日对齐。
- 默认输出 ``data/eth_options_processed/eth_options_fullsample.csv``；可选单一 parquet
  （``--format parquet|both`` 时会内存拼接全表，数据极大时慎用）。

本脚本不做什么（请勿与「数据清洗」脚本混淆）
----------------------------------------------
- 不去重、不去极值、不修正异常 IV/价格、不做样本筛选规则（除按文件名排除 sample 分片）。
- 不解析 ``instrument_name``、不计算 moneyness / tau、不聚合到日度期权链。
- 不负责无风险利率、现货对齐或风险溢价估计。

链式清洗、IV 单位统一、moneyness 等请使用 ``S3_prepare_moneyness_eth.py`` 或其它专门管道；
本脚本的产出可视为「合并后的原始成交长表」，供后续步骤使用。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, List

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DEFAULT_INPUT_DIR = _ROOT / "data" / "deribit_transactions_eth"
DEFAULT_OUT_DIR = _ROOT / "data" / "eth_options_processed"
DEFAULT_CSV_NAME = "eth_options_fullsample.csv"
DEFAULT_PARQUET_NAME = "eth_options_fullsample.parquet"


def _expand_trade(t: Any) -> pd.Series:
    """将单笔 ``trade`` 转为扁平列；不做业务清洗。"""
    if isinstance(t, dict):
        return pd.Series(
            {
                "amount": t.get("amount"),
                "contracts": t.get("contracts"),
                "direction": t.get("direction"),
                "index_price": t.get("index_price"),
                "iv": t.get("iv"),
                "mark_price": t.get("mark_price"),
                "price": t.get("price"),
                "instrument_name": t.get("instrument_name"),
                "timestamp": t.get("timestamp"),
            }
        )
    return pd.Series(
        {
            "amount": None,
            "contracts": None,
            "direction": None,
            "index_price": None,
            "iv": None,
            "mark_price": None,
            "price": None,
            "instrument_name": None,
            "timestamp": None,
        }
    )


def _list_parquet_files(input_dir: Path, exclude_substring: str) -> List[Path]:
    files = sorted(input_dir.glob("*.parquet"))
    out = [f for f in files if exclude_substring not in f.name.lower()]
    return out


def _process_one_parquet(path: Path) -> pd.DataFrame:
    """读取单个 parquet：展平 ``trade`` + 时间衍生列；不删行、不改字段语义。"""
    raw = pd.read_parquet(path)
    if "trade" not in raw.columns:
        raise ValueError(f"缺少列 trade: {path}")

    expanded = raw["trade"].apply(_expand_trade)
    base_cols = [c for c in ("s", "t") if c in raw.columns]
    if base_cols:
        df = pd.concat([raw[base_cols], expanded], axis=1)
    else:
        df = expanded.copy()

    df.insert(0, "source_file", path.name)
    ts = df["timestamp"]
    df["datetime"] = pd.to_datetime(ts, unit="ms", errors="coerce")
    df["trade_date"] = df["datetime"].dt.normalize()
    df["year"] = df["datetime"].dt.year
    return df


def consolidate_to_csv(
    input_dir: Path,
    output_csv: Path,
    exclude_substring: str = "sample",
) -> int:
    """按文件合并为单一 CSV（追加写入，省内存）。返回总行数。"""
    files = _list_parquet_files(input_dir, exclude_substring)
    if not files:
        raise FileNotFoundError(f"未找到可用 parquet（已排除含 {exclude_substring!r} 的文件）: {input_dir}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if output_csv.exists():
        output_csv.unlink()

    total_rows = 0
    header = True
    for i, fpath in enumerate(files):
        df = _process_one_parquet(fpath)
        n = len(df)
        total_rows += n
        df.to_csv(
            output_csv,
            mode="a",
            header=header,
            index=False,
            encoding="utf-8",
        )
        header = False
        print(f"[{i + 1}/{len(files)}] {fpath.name}: +{n:,} 行 (累计 {total_rows:,})")

    return total_rows


def consolidate_to_parquet(
    input_dir: Path,
    output_pq: Path,
    exclude_substring: str = "sample",
) -> int:
    """合并为单一 parquet（内存中 concat，大库慎用）。返回总行数。"""
    files = _list_parquet_files(input_dir, exclude_substring)
    if not files:
        raise FileNotFoundError(f"未找到可用 parquet: {input_dir}")

    output_pq.parent.mkdir(parents=True, exist_ok=True)
    dfs = []
    total_rows = 0
    for i, fpath in enumerate(files):
        df = _process_one_parquet(fpath)
        n = len(df)
        total_rows += n
        dfs.append(df)
        print(f"[{i + 1}/{len(files)}] {fpath.name}: +{n:,} 行 (累计 {total_rows:,})")

    out = pd.concat(dfs, ignore_index=True)
    out.to_parquet(output_pq, index=False)
    return total_rows


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "合并 Deribit ETH 成交 parquet 为单文件（仅读取+展平+合并，非数据清洗；"
            "清洗见 S3_prepare_moneyness_eth.py）"
        )
    )
    p.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"parquet 目录（默认 {DEFAULT_INPUT_DIR})",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"输出目录（默认 {DEFAULT_OUT_DIR})",
    )
    p.add_argument(
        "--format",
        choices=("csv", "parquet", "both"),
        default="csv",
        help="输出格式：优先 csv；parquet 需一次性拼接内存，数据极大时慎用",
    )
    p.add_argument(
        "--csv-name",
        default=DEFAULT_CSV_NAME,
        help=f"CSV 文件名（默认 {DEFAULT_CSV_NAME})",
    )
    p.add_argument(
        "--parquet-name",
        default=DEFAULT_PARQUET_NAME,
        help=f"Parquet 文件名（默认 {DEFAULT_PARQUET_NAME})",
    )
    p.add_argument(
        "--exclude",
        default="sample",
        help="跳过文件名中包含该子串的 parquet（不区分大小写子串匹配用 lower）",
    )
    args = p.parse_args()

    exclude = args.exclude.lower()

    if args.format in ("csv", "both"):
        out_csv = args.out_dir / args.csv_name
        n = consolidate_to_csv(args.input_dir, out_csv, exclude_substring=exclude)
        print(f"\n已写入 CSV: {out_csv}  总行数: {n:,}")

    if args.format in ("parquet", "both"):
        out_pq = args.out_dir / args.parquet_name
        n = consolidate_to_parquet(args.input_dir, out_pq, exclude_substring=exclude)
        print(f"\n已写入 Parquet: {out_pq}  总行数: {n:,}")


if __name__ == "__main__":
    main()
