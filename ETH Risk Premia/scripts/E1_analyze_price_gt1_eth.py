#!/usr/bin/env python3
"""
E1：筛选 ``trade.price > 1`` 的 ETH 期权成交并打印描述统计（探索性；见 ETH_risk_premia_plan.md §1.5）。

输入：``data/deribit_transactions_eth/*.parquet``（排除文件名含 ``sample``）。
输出：默认仅 stdout；可重定向到文件。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def option_type(name):
    if not isinstance(name, str):
        return None
    if name.endswith("-C"):
        return "Call"
    if name.endswith("-P"):
        return "Put"
    return "Other"


def main() -> None:
    data_dir = _ROOT / "data" / "deribit_transactions_eth"
    files = sorted(f for f in data_dir.glob("*.parquet") if "sample" not in f.name.lower())

    subs = []
    total = 0
    for f in files:
        t = pq.read_table(f)
        total += t.num_rows
        prices = pc.struct_field(t["trade"], "price")
        mask = pc.greater(prices, 1)
        hi = t.filter(mask)
        n = hi.num_rows
        if n:
            df = hi.to_pandas()
            tr = pd.json_normalize(df["trade"])
            merged = pd.concat([df.drop(columns=["trade"]), tr], axis=1)
            subs.append(merged)
        print(f"{f.name[:55]}: total={t.num_rows}, price>1={n}")

    if not subs:
        print("No rows with price > 1")
        return

    sub = pd.concat(subs, ignore_index=True)
    sub["option_type"] = sub["instrument_name"].apply(option_type)

    print(f"\n全库记录数: {total:,}")
    print(f"price > 1 记录数: {len(sub):,} ({100 * len(sub) / total:.4f}%)")

    print("\n=== Option type (instrument ends with -C / -P) ===")
    print(sub["option_type"].value_counts().to_string())

    num = [
        c
        for c in ["amount", "contracts", "index_price", "iv", "mark_price", "price"]
        if c in sub.columns
    ]
    print("\n=== Descriptive stats (price > 1) ===")
    print(sub[num].describe().round(4).to_string())
    if "contracts" in sub.columns and sub["contracts"].notna().sum() < len(sub):
        print(
            f"\n(Note: `contracts` 在早期导出中可能缺失；非空行数 {sub['contracts'].notna().sum():,})"
        )

    print("\n=== direction ===")
    print(sub["direction"].value_counts().to_string())

    print("\n=== Top 15 instrument_name ===")
    print(sub["instrument_name"].value_counts().head(15).to_string())

    agg_kw = dict(
        n=("price", "count"),
        mean_price=("price", "mean"),
        mean_iv=("iv", "mean"),
        mean_index=("index_price", "mean"),
    )
    if "contracts" in sub.columns and sub["contracts"].notna().any():
        agg_kw["mean_contracts"] = ("contracts", "mean")
    print("\n=== By option_type ===")
    print(sub.groupby("option_type").agg(**agg_kw).round(4).to_string())


if __name__ == "__main__":
    main()
