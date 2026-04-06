#!/usr/bin/env python3
"""
S5_1：在 **TTM（τ）维** 对 S5_0 的 IV 曲面做插值，补齐无观测 τ，得到 **全量 IV surface**。

对齐 BTC ``S2_v1_2_IV_interpolation.py``：对每个 moneyness 列在 ``TTM_min … TTM_max`` 的整数天上
线性插值，端点用 ``ffill`` / ``bfill``（与 BTC 一致）。

**输入**（默认）：``results/IV/IV_surface_observed/moneyness_step_0d01/``
（``S5_0`` 产出的 ``interpolated_*_allR2.csv``）。

**输出**（默认）：``results/IV/IV_surface_SVI/moneyness_step_0d01/``，同名 ``interpolated_{date}_allR2.csv``，
供 **S6_0 Q 密度** 按 τ 切片读取。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_IV_SURFACE_FULL_DIR,
    ETH_IV_SURFACE_MON_STEP_SUBDIR,
    ETH_IV_SURFACE_OBSERVED_DIR,
)


def _interpolate_one_file(iv_path: Path, out_dir: Path) -> Path:
    """
    单日文件：按 TTM 排序，在 [TTM_min, TTM_max] 上逐列线性插值，再 ffill/bfill。
    输出文件名与输入相同。
    """
    name = iv_path.name
    # 与 BTC 一致：interpolated_2020-09-23_allR2.csv -> 2020-09-23
    parts = name.replace(".csv", "").split("_")
    if len(parts) < 3 or parts[0] != "interpolated":
        raise ValueError(f"非预期文件名: {name}")
    date_str = parts[1]

    df_iv = pd.read_csv(iv_path)
    if "TTM" not in df_iv.columns or "Date" not in df_iv.columns:
        raise ValueError(f"{iv_path} 需含 Date, TTM 列")

    df_iv = df_iv.sort_values(by="TTM")
    ttm_min = int(df_iv["TTM"].min())
    ttm_max = int(df_iv["TTM"].max())
    full_ttm = pd.DataFrame(
        {"Date": date_str, "TTM": np.arange(ttm_min, ttm_max + 1, dtype=int)}
    )

    df_iv_full = full_ttm.merge(df_iv, on=["Date", "TTM"], how="left")

    numeric_cols = df_iv_full.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        df_iv_full[numeric_cols] = df_iv_full[numeric_cols].interpolate(method="linear")
    df_iv_full.ffill(inplace=True)
    df_iv_full.bfill(inplace=True)

    column_order = ["Date", "TTM"] + [
        c for c in df_iv_full.columns if c not in ("Date", "TTM")
    ]
    df_iv_full = df_iv_full[column_order]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name
    df_iv_full.to_csv(out_path, index=False)
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(
        description="S5_1：TTM 维插值 → 全量 IV surface；对齐 BTC S2_v1_2"
    )
    p.add_argument(
        "--observed-dir",
        type=Path,
        default=ETH_IV_SURFACE_OBSERVED_DIR,
        help="S5_0 根目录（默认仅搜 relative-subdir 下按日文件）",
    )
    p.add_argument(
        "--relative-subdir",
        type=Path,
        default=ETH_IV_SURFACE_MON_STEP_SUBDIR,
        help="相对 observed-dir 的子路径（与 S5_0 一致）",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ETH_IV_SURFACE_FULL_DIR,
        help="插值后全量 IV 曲面根目录",
    )
    p.add_argument(
        "--n-jobs",
        type=int,
        default=-2,
        help="joblib 并行作业数（默认 -2）",
    )
    args = p.parse_args()

    iv_dir = (args.observed_dir / args.relative_subdir).resolve()
    out_root = (args.out_dir / args.relative_subdir).resolve()

    if not iv_dir.is_dir():
        print(f"错误：目录不存在: {iv_dir}", file=sys.stderr)
        raise SystemExit(2)

    files: List[Path] = sorted(
        p
        for p in iv_dir.glob("interpolated_*_allR2.csv")
        if p.is_file() and "all_dates" not in p.name
    )
    if not files:
        print(
            f"错误：{iv_dir} 下无 interpolated_*_allR2.csv（请先运行 S5_0）",
            file=sys.stderr,
        )
        raise SystemExit(2)

    print(f"输入: {iv_dir}（{len(files)} 个按日文件）")
    print(f"输出: {out_root}")

    def _job(fp: Path) -> str:
        out = _interpolate_one_file(fp, out_root)
        return str(out)

    paths = Parallel(n_jobs=args.n_jobs)(delayed(_job)(fp) for fp in files)
    for s in sorted(paths):
        print(f"  -> {s}")
    print("TTM 插值完成。")


if __name__ == "__main__":
    main()
