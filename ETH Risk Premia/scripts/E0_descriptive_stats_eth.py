#!/usr/bin/env python3
"""
E0：Deribit ETH 成交 parquet 描述性统计（探索性；见 ETH_risk_premia_plan.md §1.5）。

读取 ``data/deribit_transactions_eth/*.parquet``，展开 ``trade`` 后打印汇总。
**跳过**文件名含 ``sample`` 的分片（与 ``S1`` 一致）；不做 sample 专表模式。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DATA_DIR = _ROOT / "data" / "deribit_transactions_eth"


def expand_trade(t):
    """展开 trade 字典为 Series"""
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
    return pd.Series()


def load_data(sample_frac=None):
    """
    加载数据（仅非 sample 分片）。
    - sample_frac: 可选，对每个文件随机抽样比例，如 0.01 表示 1%
    """
    files = sorted(f for f in DATA_DIR.glob("*.parquet") if "sample" not in f.name.lower())

    if not files:
        raise FileNotFoundError(f"未找到 parquet 文件: {DATA_DIR}")

    dfs = []
    for f in files:
        raw = pd.read_parquet(f)
        if sample_frac and sample_frac < 1:
            raw = raw.sample(frac=sample_frac, random_state=42)
        expanded = raw["trade"].apply(expand_trade)
        base_cols = [c for c in ("s", "t") if c in raw.columns]
        if base_cols:
            df = pd.concat([raw[base_cols], expanded], axis=1)
        else:
            df = expanded.copy()
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
        df["date"] = df["datetime"].dt.date
        df["year"] = df["datetime"].dt.year
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


def run_descriptive_stats(df):
    """执行描述性统计并打印"""
    num_cols = ["amount", "contracts", "index_price", "iv", "mark_price", "price"]
    num_cols = [c for c in num_cols if c in df.columns]

    print("=" * 60)
    print("Deribit ETH 交易数据 - 描述性统计 (E0)")
    print("=" * 60)
    print(f"\n总记录数: {len(df):,}")
    print(f"时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")

    print("\n【数值变量统计】")
    print(df[num_cols].describe().round(4).to_string())

    print("\n【方向分布 (direction)】")
    print(df["direction"].value_counts().to_string())

    print("\n【按年交易笔数】")
    print(df.groupby("year").size().to_string())

    print("\n【缺失值统计】")
    print(df.isnull().sum().to_string())

    print("\n【衍生统计】")
    print(f"  唯一 instrument 数量: {df['instrument_name'].nunique():,}")
    print(f"  日均交易笔数: {len(df) / df['date'].nunique():.1f}")
    cmean = df["contracts"].mean()
    print(f"  平均每笔合约数: {cmean:.2f}" if pd.notna(cmean) else "  平均每笔合约数: (全为缺失)")
    print(f"  平均每笔金额(ETH): {df['amount'].mean():4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="E0: ETH 期权成交描述性统计")
    parser.add_argument(
        "--frac",
        type=float,
        metavar="P",
        help="每个分片内随机保留比例 P∈(0,1]，如 0.01=1%%；省略则读全部分片全部行",
    )
    args = parser.parse_args()

    if args.frac:
        df = load_data(sample_frac=args.frac)
    else:
        df = load_data()

    run_descriptive_stats(df)


if __name__ == "__main__":
    main()
