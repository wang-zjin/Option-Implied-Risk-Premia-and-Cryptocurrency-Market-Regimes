#!/usr/bin/env python3
"""
S6_0：由 **S5_1 插值后 IV 曲面**（``results/IV/IV_surface_SVI/``）估计风险中性 Q 密度（Rookley）。

对齐 BTC ``SVI_independent_tau/S2_v1_3_estimate_Qdensity.py``：对 ``log(1+k)`` 网格上的 IV 求数值导数，
调用 ``deribit/r/Q_from_IV.R`` 中 ``estimate_Q_from_IV``。

**输入**（默认）：``results/IV/IV_surface_SVI/moneyness_step_0d01/interpolated_*_allR2.csv``

**输出**（默认）：``results/Q_from_pure_SVI/moneyness_step_0d01/tau_{ttm}/eth_Q_{YYYY-MM-DD}.csv``

依赖：本机已安装 **R**，Python 包 **rpy2**（``pip install rpy2``）；R 从 ``deribit/r/`` 加载 ``Q_from_IV.R``（同目录 ``EPK_library_1.R``）。

无风险利率：``function.load_ir_daily()`` / ``data/Interest_Rate/DTB3.csv``（DTB3/100）。
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_IV_SURFACE_FULL_DIR,
    ETH_IV_SURFACE_MON_STEP_SUBDIR,
    ETH_Q_FROM_SVI_MON_STEP_SUBDIR,
    ETH_Q_FROM_SVI_OUT_DIR,
    SVI_TAU_MAX_DAYS,
    SVI_TAU_MIN_DAYS,
    load_ir_daily,
)

R_ETH_DIR = _ROOT / "r"
Q_FROM_IV_R = R_ETH_DIR / "Q_from_IV.R"


def _interest_rate_for_date(ir_df: pd.DataFrame, date_str: str) -> Optional[float]:
    """不晚于 date_str 的最近一条 DTB3（自然日可对周末用上一交易日利率）。"""
    d = pd.to_datetime(date_str).normalize()
    sub = ir_df.loc[ir_df["date"] <= d, "interest_rate"]
    if sub.empty:
        return None
    v = float(sub.iloc[-1])
    if pd.isna(v) or not math.isfinite(v):
        return None
    return v


def _init_r() -> Any:
    try:
        from rpy2 import robjects
    except ImportError as e:
        raise ImportError(
            "需要安装 rpy2：pip install rpy2；并确保系统已安装 R。"
        ) from e
    old = os.getcwd()
    try:
        os.chdir(R_ETH_DIR)
        robjects.r["source"](str(Q_FROM_IV_R.name))
    finally:
        os.chdir(old)
    return robjects.r


def estimate_Q(
    log_ret: List[float],
    IV: np.ndarray,
    dIVdr: List[float],
    d2IVdr2: List[float],
    rf: float,
    tau_years: float,
    r_obj: Any,
    out_dir: str,
) -> Optional[pd.DataFrame]:
    """调用 R ``estimate_Q_from_IV``，返回与 BTC 同构的 DataFrame。"""
    try:
        from rpy2 import robjects
    except ImportError:
        return None

    try:
        moneyness_r, spd, logret_r, spd_logret, volas, cdf_m, cdf_ret, sigmas1, sigmas2 = (
            r_obj.estimate_Q_from_IV(
                robjects.FloatVector(log_ret),
                robjects.FloatVector(IV),
                robjects.FloatVector(dIVdr),
                robjects.FloatVector(d2IVdr2),
                robjects.FloatVector([rf]),
                robjects.FloatVector([tau_years]),
                robjects.StrVector([out_dir]),
            )
        )
        moneyness = np.array(moneyness_r) - 1
        spd_df = pd.DataFrame(
            {
                "m": moneyness,
                "spdy": spd,
                "ret": logret_r,
                "spd_ret": spd_logret,
                "volatility": volas,
                "cdf_m": cdf_m,
                "cdf_ret": cdf_ret,
                "sigma_prime": sigmas1,
                "sigma_double_prime": sigmas2,
            }
        )
        return spd_df
    except Exception as e:
        print("Exception in estimate_Q:", e)
        return None


def process_file(
    file: str,
    ttm: int,
    out_path: Path,
    ir_df: pd.DataFrame,
    iv_dir: Path,
) -> str:
    """处理单日曲面文件、固定 TTM（天）。``tau`` 传入 R 为 ``ttm/365``。"""
    tau_years = ttm / 365.0
    tau_dir = out_path / f"tau_{ttm}"
    tau_dir.mkdir(parents=True, exist_ok=True)
    out_dir_str = str(tau_dir)

    file_path = iv_dir / file
    try:
        df_all = pd.read_csv(file_path)
    except Exception as e:
        return f"Failed to read file {file}: {e}"

    if "TTM" not in df_all.columns:
        return f"TTM column not found in {file}."
    if ttm not in df_all["TTM"].unique():
        return f"TTM value {ttm} not in file {file}."

    try:
        date = file.split("_")[1]
    except IndexError:
        return f"Filename {file} does not contain expected date info."

    df = df_all[df_all["TTM"] == ttm]
    row = df[df["Date"] == date]
    if row.empty:
        return f"No data for date {date} in file {file}."
    row = row.iloc[0]

    meta_cols = ("Date", "TTM")
    k_cols = [c for c in df_all.columns if c not in meta_cols]
    try:
        k_vals = np.array([float(c) for c in k_cols], dtype=float)
    except Exception as e:
        return f"Error parsing moneyness column names in {file}: {e}"

    # 与 BTC S2_v1_3 完全一致
    logret = np.log(k_vals + 1.0 + 1e-10)

    IV = row[list(k_cols)].to_numpy(dtype=float)

    try:
        dIVdr = (IV[2:] - IV[:-2]) / (logret[2:] - logret[:-2])
        dIVdr = [float("nan")] + list(dIVdr) + [float("nan")]
        dIVdr[0] = (IV[1] - IV[0]) / (logret[1] - logret[0])
        dIVdr[-1] = (IV[-1] - IV[-2]) / (logret[-1] - logret[-2])
    except Exception as e:
        return f"Error computing first derivative for file {file}: {e}"

    try:
        d2IVdr2 = (IV[2:] - 2 * IV[1:-1] + IV[:-2]) / ((logret[2:] - logret[:-2]) ** 2)
        d2IVdr2 = [float("nan")] + list(d2IVdr2) + [float("nan")]
        d2IVdr2[0] = (IV[2] - 2 * IV[1] + IV[0]) / ((logret[1] - logret[0]) ** 2)
        d2IVdr2[-1] = (IV[-1] - 2 * IV[-2] + IV[-3]) / ((logret[-1] - logret[-2]) ** 2)
    except Exception as e:
        return f"Error computing second derivative for file {file}: {e}"

    rf = _interest_rate_for_date(ir_df, date)
    if rf is None:
        return f"No risk-free rate data for date {date} in DTB3.csv."

    try:
        r_obj = _init_r()
    except Exception as e:
        return f"Error initializing R in file {file}: {e}"

    spd_eth = estimate_Q(
        logret.tolist(),
        IV,
        dIVdr,
        d2IVdr2,
        rf,
        tau_years,
        r_obj,
        out_dir_str,
    )
    if spd_eth is None:
        return f"Failed to compute Q for date {date} in file {file}."

    try:
        output_file = tau_dir / f"eth_Q_{date}.csv"
        spd_eth.to_csv(output_file, index=False, float_format="%.4f")
    except Exception as e:
        return f"Error saving CSV for date {date} in file {file}: {e}"

    return f"Successfully processed file {file} for date {date}"


def _list_iv_files(iv_dir: Path) -> List[str]:
    return sorted(p.name for p in iv_dir.iterdir() if p.suffix.lower() == ".csv" and p.name.startswith("interpolated"))


def main() -> None:
    p = argparse.ArgumentParser(
        description="S6_0：IV 曲面（S5_1）→ Q 密度（Rookley），对齐 BTC S2_v1_3"
    )
    p.add_argument(
        "--iv-dir",
        type=Path,
        default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR,
        help="含 interpolated_*_allR2.csv 的目录（默认 S5_1 全量曲面）",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ETH_Q_FROM_SVI_OUT_DIR / ETH_Q_FROM_SVI_MON_STEP_SUBDIR,
        help="Q 密度输出根目录（下建 tau_{ttm}/；默认 moneyness_step_0d01）",
    )
    p.add_argument(
        "--ttm-min",
        type=int,
        default=SVI_TAU_MIN_DAYS,
        help="最小 TTM（天），默认与 SVI 范围一致",
    )
    p.add_argument(
        "--ttm-max",
        type=int,
        default=SVI_TAU_MAX_DAYS,
        help="最大 TTM（天）",
    )
    p.add_argument(
        "--ttm-list",
        type=int,
        nargs="+",
        default=None,
        help="仅处理这些 TTM（天）；若指定则忽略 --ttm-min/max",
    )
    p.add_argument(
        "--ir-csv",
        type=Path,
        default=None,
        help="DTB3.csv 路径（默认 function.DTB3_CSV）",
    )
    p.add_argument(
        "--n-jobs",
        type=int,
        default=-2,
        help="joblib 并行作业数（默认 -2，与 BTC 一致）",
    )
    args = p.parse_args()

    iv_dir = args.iv_dir.resolve()
    out_path = args.out_dir.resolve()
    if not iv_dir.is_dir():
        print(f"错误：IV 目录不存在: {iv_dir}", file=sys.stderr)
        raise SystemExit(2)

    files = _list_iv_files(iv_dir)
    if not files:
        print(f"错误：目录中无 interpolated*.csv: {iv_dir}", file=sys.stderr)
        raise SystemExit(2)

    if args.ttm_list is not None:
        ttms: Sequence[int] = tuple(args.ttm_list)
    else:
        lo, hi = args.ttm_min, args.ttm_max
        if lo > hi:
            print("错误：--ttm-min 不能大于 --ttm-max", file=sys.stderr)
            raise SystemExit(2)
        ttms = tuple(range(lo, hi + 1))

    ir_df = load_ir_daily(args.ir_csv)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"IV 目录: {iv_dir}（{len(files)} 个文件）")
    print(f"输出根: {out_path}")
    print(f"TTM 列表: {len(ttms)} 个（{ttms[0]}…{ttms[-1]}）")

    for ttm in ttms:
        print(f"Processing TTM = {ttm} ...")
        results: List[Union[str, Any]] = Parallel(n_jobs=args.n_jobs)(
            delayed(process_file)(f, ttm, out_path, ir_df, iv_dir) for f in files
        )
        for result in results:
            print(result)


if __name__ == "__main__":
    main()
