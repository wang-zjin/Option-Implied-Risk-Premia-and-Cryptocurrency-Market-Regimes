#!/usr/bin/env python3
"""
S5_0：由 S4 SVI 参数（仅 **有观测且拟合成功** 的 τ）生成逐日、逐 TTM 的 IV curve。

对齐 BTC ``S2_v1_1_IV_surface.py``：在 moneyness 网格 ``k ∈ [-1,1]``（步长与 S4 一致，201 点）上，
用 τ-independent SVI 参数 ``(a,b,ρ,m,σ)`` 写出 IV 行；列名 ``f"{k:.4f}"`` 与 S4
``svi_Tau-Ind_Mon-Uni_iv_and_r2_results.csv`` 一致，便于校验。

**输入**（默认）：``results/SVI/svi_Tau-Ind_Mon-Uni_paras.csv``（``function.ETH_SVI_FULL_OUT_DIR``）。

**输出**（默认）：``results/IV/IV_surface_observed/moneyness_step_0d01/``，
按日文件 ``interpolated_{YYYY-MM-DD}_allR2.csv``（列 ``Date``, ``TTM``, 各 k 列；IV 为 **小数**），
另写 ``interpolated_all_dates_allR2.csv``（全日拼接）。

**下游**：``S5_1_iv_surface_interpolate_ttm_eth.py`` 读入本步产出，在 TTM 维插值得到全量曲面。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_IV_SURFACE_MON_STEP_SUBDIR,
    ETH_IV_SURFACE_OBSERVED_DIR,
    ETH_SVI_FULL_OUT_DIR,
    SVI_TAU_MAX_DAYS,
    SVI_TAU_MIN_DAYS,
)


def svi_model_ind(theta: np.ndarray, k: float) -> float:
    """与 ``S4_estimate_SVI_eth.svi_model_ind`` 相同（总方差 w，未开方）。"""
    a, b, rho, m, sigma = theta[:5]
    return float(a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma**2)))


def _iv_from_theta(theta: np.ndarray, k_grid: np.ndarray) -> np.ndarray:
    out = np.empty_like(k_grid, dtype=float)
    for i, k in enumerate(k_grid):
        w = svi_model_ind(theta, float(k))
        out[i] = float(np.sqrt(max(w, 0.0)))
    return out


def _date_from_filename(name: str) -> Optional[str]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else None


def _process_one_file(
    filename: str,
    paras_sub: pd.DataFrame,
    k_grid: np.ndarray,
    k_cols: List[str],
    tau_min: int,
    tau_max: int,
) -> pd.DataFrame:
    """单日（单 IV 矩阵文件名）上所有观测 TTM 的 IV 行。"""
    date_str = _date_from_filename(filename)
    if not date_str:
        return pd.DataFrame()

    rows: List[dict[str, Any]] = []
    ttms = paras_sub["tau"].drop_duplicates().sort_values()
    for ttm in ttms:
        ttm = int(ttm)
        if ttm < tau_min or ttm > tau_max:
            continue
        sub = paras_sub.loc[paras_sub["tau"] == ttm, ["a", "b", "rho", "m", "sigma"]]
        if sub.empty:
            continue
        theta = np.asarray(sub.iloc[0].values, dtype=float)
        iv = _iv_from_theta(theta, k_grid)
        row: dict[str, Any] = {"Date": date_str, "TTM": ttm}
        row.update({col: iv[j] for j, col in enumerate(k_cols)})
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(
        description="S5_0：SVI 有参数 τ → IV curve（观测 TTM）；对齐 BTC S2_v1_1"
    )
    p.add_argument(
        "--svi-dir",
        type=Path,
        default=ETH_SVI_FULL_OUT_DIR,
        help="含 svi_Tau-Ind_Mon-Uni_paras.csv 的目录",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ETH_IV_SURFACE_OBSERVED_DIR,
        help="IV 曲面（仅观测 τ）根目录",
    )
    p.add_argument(
        "--relative-subdir",
        type=Path,
        default=ETH_IV_SURFACE_MON_STEP_SUBDIR,
        help="相对 out-dir 的子目录（默认 moneyness_step_0d01）",
    )
    p.add_argument(
        "--tau-min",
        type=int,
        default=SVI_TAU_MIN_DAYS,
        help=f"仅输出 τ≥该值（天），默认 {SVI_TAU_MIN_DAYS}",
    )
    p.add_argument(
        "--tau-max",
        type=int,
        default=SVI_TAU_MAX_DAYS,
        help=f"仅输出 τ≤该值（天），默认 {SVI_TAU_MAX_DAYS}",
    )
    p.add_argument(
        "--n-jobs",
        type=int,
        default=-2,
        help="joblib 并行作业数（默认 -2）",
    )
    p.add_argument(
        "--no-concat",
        action="store_true",
        help="不写 interpolated_all_dates_allR2.csv",
    )
    args = p.parse_args()

    svi_dir = args.svi_dir.resolve()
    paras_path = svi_dir / "svi_Tau-Ind_Mon-Uni_paras.csv"
    if not paras_path.is_file():
        print(f"错误：未找到 {paras_path}", file=sys.stderr)
        raise SystemExit(2)

    paras = pd.read_csv(paras_path)
    need = {"filename", "tau", "a", "b", "rho", "m", "sigma"}
    if not need.issubset(set(paras.columns)):
        print(f"错误：{paras_path} 需含列 {sorted(need)}", file=sys.stderr)
        raise SystemExit(2)

    paras = paras.drop_duplicates(subset=["filename", "tau"], keep="last")
    paras = paras.loc[
        (paras["tau"] >= args.tau_min) & (paras["tau"] <= args.tau_max)
    ].copy()

    k_grid = np.linspace(-1.0, 1.0, 201)
    k_cols = [f"{float(k):.4f}" for k in k_grid]

    out_root = (args.out_dir / args.relative_subdir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    unique_files = paras["filename"].drop_duplicates().sort_values().tolist()
    print(f"SVI 参数: {paras_path}（{len(paras)} 行, {len(unique_files)} 个交易日文件）")
    print(f"输出目录: {out_root}")

    def _job(fn: str) -> pd.DataFrame:
        sub = paras.loc[paras["filename"] == fn]
        return _process_one_file(
            fn, sub, k_grid, k_cols, args.tau_min, args.tau_max
        )

    parts: List[pd.DataFrame] = Parallel(n_jobs=args.n_jobs)(
        delayed(_job)(fn) for fn in unique_files
    )

    all_concat: List[pd.DataFrame] = []
    for fn, df in zip(unique_files, parts):
        if df.empty:
            continue
        date_str = df["Date"].iloc[0]
        out_path = out_root / f"interpolated_{date_str}_allR2.csv"
        df = df.sort_values(by=["Date", "TTM"]).reset_index(drop=True)
        df.to_csv(out_path, index=False)
        all_concat.append(df)
        print(f"  {fn} -> {out_path.name}（{len(df)} 行 TTM）")

    if not all_concat:
        print("未写出任何文件：请检查 S4 是否已产出有效 SVI 参数。", file=sys.stderr)
        raise SystemExit(1)

    if not args.no_concat:
        merged = pd.concat(all_concat, ignore_index=True)
        merged = merged.sort_values(by=["Date", "TTM"]).reset_index(drop=True)
        all_path = out_root / "interpolated_all_dates_allR2.csv"
        merged.to_csv(all_path, index=False)
        print(f"全日拼接: {all_path}（{len(merged)} 行）")


if __name__ == "__main__":
    main()
