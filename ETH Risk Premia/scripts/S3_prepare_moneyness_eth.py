#!/usr/bin/env python3
"""
S3：ETH 期权链清洗与 moneyness 表（对照 SVI_independent_tau 中 S1_data_prepare_moneyness_unique.ipynb）。

管线位置：ETH_risk_premia_plan.md §1.1 步骤 ③；上游为步骤 ② 的 (date, expiry, strike) 表或链 CSV。

输入：长表 CSV 或 Parquet，需含交易日、到期日、行权价、标的价、IV（或可由你方预处理得到 IV）、数量（可选）。
默认路径为 S2 产出 ``eth_options_chain_daily.csv``（可用 ``-i`` 覆盖）。

输出（默认**分目录**）：
- ``eth_processed_moneyness.csv``、``eth_ATM_IV.csv`` → ``--tables-dir``（默认 ``data/eth_options_processed/prepare_moneyness_for_SVI/``）
- 日度 IV 矩阵 → ``--out-dir`` 下 ``IV/IV_raw/unique/moneyness/`` 与 ``.../standardized_moneyness/``（默认 ``data/IV/``），供 S4 等读取

IV 约定：默认认为输入 IV 为「小数形式」年化波动（如 0.65 表示 65%），脚本内部转为百分比以与 BTC/SVI 一致；
若输入已是百分比，请使用 --iv-already-percent。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

# 允许从仓库根目录运行: python scripts/S3_prepare_moneyness_eth.py
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (
    ETH_OPTIONS_CHAIN_DAILY_CSV,
    ETH_OPTIONS_IV_OUT_DIR,
    ETH_OPTIONS_PREPARE_SVI_DIR,
    SVI_TAU_MIN_DAYS,
)


def _read_table(path: Path) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf == ".parquet":
        return pd.read_parquet(path)
    if suf in (".csv", ".txt"):
        return pd.read_csv(path)
    raise ValueError(f"不支持的扩展名: {path}")


def _to_percent_iv(iv: pd.Series, already_percent: bool) -> pd.Series:
    if already_percent:
        return iv.astype(float)
    return iv.astype(float) * 100.0


def _weighted_iv_mean(g: pd.DataFrame, iv_col: str, w_col: str) -> float:
    w = g[w_col].to_numpy(dtype=float)
    v = g[iv_col].to_numpy(dtype=float)
    s = np.nansum(w)
    if s <= 0 or not np.isfinite(s):
        return float(np.nanmean(v))
    return float(np.average(v, weights=w))


def prepare(
    df: pd.DataFrame,
    date_col: str,
    expiry_col: str,
    strike_col: str,
    spot_col: str,
    iv_col: str,
    quantity_col: Optional[str],
    tau_min: int,
    iv_already_percent: bool,
    extra_agg_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    extra_agg_cols = extra_agg_cols or []
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], utc=True).dt.tz_convert(None).dt.normalize()
    d[expiry_col] = pd.to_datetime(d[expiry_col], utc=True).dt.tz_convert(None).dt.normalize()
    d["tau"] = (d[expiry_col] - d[date_col]).dt.days.astype(int)
    d["K"] = d[strike_col].astype(float)
    d["S"] = d[spot_col].astype(float)
    d["IV_pct"] = _to_percent_iv(d[iv_col], iv_already_percent)

    if quantity_col is None or quantity_col not in d.columns:
        d["quantity"] = 1.0
        quantity_col = "quantity"
    else:
        d["quantity"] = d[quantity_col].astype(float).clip(lower=0.0)
        d.loc[d["quantity"] <= 0, "quantity"] = 1.0

    d = d[(d["IV_pct"] > 0) & (d["tau"] >= tau_min)].copy()
    d["moneyness"] = d["K"] / d["S"] - 1.0

    group_cols = ["date", "tau", "moneyness"]
    rows = []
    for _, g in d.groupby(group_cols, sort=False):
        row = {
            "date": g[date_col].iloc[0],
            "tau": int(g["tau"].iloc[0]),
            "moneyness": float(g["moneyness"].iloc[0]),
            "IV": _weighted_iv_mean(g, "IV_pct", "quantity"),
            "quantity": float(g["quantity"].sum()),
        }
        for c in extra_agg_cols:
            if c in g.columns:
                row[c] = float(np.nanmean(g[c].astype(float)))
        rows.append(row)
    out = pd.DataFrame(rows)

    atm_rows = []
    for (dt, tau), g in out.groupby(["date", "tau"]):
        closest = g.iloc[(g["moneyness"].abs()).argsort()[:1]]
        atm_rows.append(
            {
                "date": dt,
                "tau": tau,
                "IV_atm": float(closest["IV"].values[0]),
                "moneyness_atm": float(closest["moneyness"].values[0]),
            }
        )
    atm_df = pd.DataFrame(atm_rows)
    out = out.merge(atm_df, on=["date", "tau"], how="left")
    out["standardized_moneyness"] = out["moneyness"] / out["IV_atm"] * 100.0
    return out


def _export_daily_iv_matrices(
    df: pd.DataFrame,
    mon_folder: Path,
    std_folder: Path,
    date_fmt: str = "%Y-%m-%d",
) -> None:
    mon_folder.mkdir(parents=True, exist_ok=True)
    std_folder.mkdir(parents=True, exist_ok=True)
    for dt in sorted(df["date"].unique()):
        day = df[df["date"] == dt]
        m_pivot = day.pivot_table(
            index="moneyness", columns="tau", values="IV", aggfunc="mean"
        ).reset_index()
        fn = mon_folder / f"IV_matrix_{pd.Timestamp(dt).strftime(date_fmt)}.csv"
        m_pivot.to_csv(fn, index=False)

        s_pivot = day.pivot_table(
            index="standardized_moneyness", columns="tau", values="IV", aggfunc="mean"
        ).reset_index()
        sfn = std_folder / f"IV_matrix_{pd.Timestamp(dt).strftime(date_fmt)}.csv"
        s_pivot.to_csv(sfn, index=False)


def main() -> None:
    p = argparse.ArgumentParser(description="ETH 期权 moneyness 与 IV 矩阵（S1 等价）")
    p.add_argument(
        "--input",
        "-i",
        type=Path,
        default=ETH_OPTIONS_CHAIN_DAILY_CSV,
        help=f"期权链 CSV 或 Parquet（默认 S2 产出：{ETH_OPTIONS_CHAIN_DAILY_CSV}）",
    )
    p.add_argument(
        "--out-dir",
        "-o",
        type=Path,
        default=ETH_OPTIONS_IV_OUT_DIR,
        help=f"日度 IV 矩阵输出根目录（默认 {ETH_OPTIONS_IV_OUT_DIR}，其下 IV/IV_raw/unique/...）",
    )
    p.add_argument(
        "--tables-dir",
        type=Path,
        default=ETH_OPTIONS_PREPARE_SVI_DIR,
        help=(
            "eth_processed_moneyness.csv 与 eth_ATM_IV.csv 输出目录 "
            f"（默认 {ETH_OPTIONS_PREPARE_SVI_DIR}）"
        ),
    )
    p.add_argument("--date-col", default="date")
    p.add_argument("--expiry-col", default="expiry")
    p.add_argument("--strike-col", default="K")
    p.add_argument("--spot-col", default="spot")
    p.add_argument("--iv-col", default="IV")
    p.add_argument("--quantity-col", default="quantity")
    p.add_argument("--no-quantity", action="store_true", help="无数量列时等权聚合")
    p.add_argument(
        "--tau-min",
        type=int,
        default=SVI_TAU_MIN_DAYS,
        help=f"最小 tau（天），默认 {SVI_TAU_MIN_DAYS}（与 function.SVI_TAU_MIN_DAYS 一致，含 τ=1,2）",
    )
    p.add_argument(
        "--iv-already-percent",
        action="store_true",
        help="IV 已为百分比（0–100），不再乘以 100",
    )
    args = p.parse_args()

    if not args.input.exists():
        print(
            f"输入文件不存在: {args.input}\n"
            "请先运行 S2 生成链表面板，或使用 -i 指定其它 CSV/Parquet。",
            file=sys.stderr,
        )
        raise SystemExit(1)

    raw = _read_table(args.input)
    qcol = None if args.no_quantity else args.quantity_col
    if qcol and qcol not in raw.columns:
        qcol = None

    processed = prepare(
        raw,
        date_col=args.date_col,
        expiry_col=args.expiry_col,
        strike_col=args.strike_col,
        spot_col=args.spot_col,
        iv_col=args.iv_col,
        quantity_col=qcol,
        tau_min=args.tau_min,
        iv_already_percent=args.iv_already_percent,
    )

    tables_dir = args.tables_dir
    tables_dir.mkdir(parents=True, exist_ok=True)
    long_path = tables_dir / "eth_processed_moneyness.csv"
    processed.to_csv(long_path, index=False)

    atm = (
        processed[["date", "tau", "IV_atm", "moneyness_atm"]]
        .drop_duplicates(subset=["date", "tau"])
        .sort_values(["date", "tau"])
    )
    atm_path = tables_dir / "eth_ATM_IV.csv"
    atm.to_csv(atm_path, index=False)

    iv_root = args.out_dir
    iv_root.mkdir(parents=True, exist_ok=True)
    iv_base = iv_root / "IV" / "IV_raw" / "unique"
    _export_daily_iv_matrices(
        processed,
        iv_base / "moneyness",
        iv_base / "standardized_moneyness",
    )

    print(f"已写入: {long_path} ({len(processed)} 行)")
    print(f"已写入: {atm_path} ({len(atm)} 行)")
    print(f"日度 IV 矩阵目录: {iv_base / 'moneyness'}")


if __name__ == "__main__":
    main()
