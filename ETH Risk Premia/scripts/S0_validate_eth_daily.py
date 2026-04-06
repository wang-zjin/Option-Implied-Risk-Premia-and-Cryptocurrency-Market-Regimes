#!/usr/bin/env python3
"""S0：快速校验 ETH 日度 CSV 与 function.load_eth_daily（现货前置；见 ETH_risk_premia_plan.md）。"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import ETH_DAILY_CSV, load_eth_daily


def main() -> None:
    df = load_eth_daily()
    n = len(df)
    na_ret = df["simple_ret"].isna().sum()
    print(f"路径: {ETH_DAILY_CSV}")
    print(f"行数: {n} | 列: {list(df.columns)}")
    print(f"simple_ret NaN 行数（首行预期为 1）: {na_ret}")
    print("日期范围:", df["date"].min(), "→", df["date"].max())
    print(df[["date", "price", "simple_ret"]].iloc[:3])
    print("…")
    print(df[["date", "price", "simple_ret"]].iloc[-3:])


if __name__ == "__main__":
    main()
