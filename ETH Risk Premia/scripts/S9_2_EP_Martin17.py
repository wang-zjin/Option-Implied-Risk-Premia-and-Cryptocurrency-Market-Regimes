#!/usr/bin/env python3
"""
S9_2：**Martin（2017）型下界** → **一阶 EP 时间序列**（界形式，**非** S9_0 密度差、**非** S9_1 BP）。

对齐 BTC ``S9_lower_bound.py`` 中 **Martin 段**：由 **逐日风险中性密度**（``Q_matrix`` 列）在 **简单收益** 网格上数值积分得 **M2**（中心二阶矩），再

    ``martin17_EP = M2 / R_f``

其中 **R_f** 与规划 §3 一致：``function.risk_free_simple_one_period()``（一期总收益 **1**）。

**矩定义**（与 BTC ``moments_Q_density`` 同构）：在 ``[-1,1]``、步长 **0.01** 上 ``interp`` 当日 Q（外推 0；负值置 0），再 ``trapz`` 得 **M1**、**M2**、标准化 **M3/M4**。

**输出**（均在 ``EP/Martin17/``）：

- ``EP_Martin17_panel_ttm{τ}day.csv``：全列面板（``date``, ``martin17_EP``, ``M1_rn``…``M4_rn``，可选 ``cluster``）。
- ``Martin17_EP_ttm{τ}day.csv``：**仅 Martin17 EP 时间序列**，列名对齐 BTC ``S9_lower_bound.py`` 存 ``BP_LB.csv`` 时的 **``Date`` + ``MLB``**（``MLB`` = ``M2_rn / R_f``，与面板 ``martin17_EP`` 相同）。
- ``EP_Martin17_ttm{τ}day.png``：与 BTC 同风格的 **Martin17 下界** 折线图（默认写出；``--no-plot`` 跳过）。
- ``S9_2_run_meta_ttm{τ}day.json``

先决：**S6_1** ``Q_matrix_{τ}day.csv``；默认按 **S7** ``common_dates_cluster.csv`` 与 **制度** 取列（与 S9_0/S9_1 可比）；**不依赖** S8_0。

用法::

    python3 scripts/S9_2_EP_Martin17.py
    python3 scripts/S9_2_EP_Martin17.py --ttm 27 --regime HV
    python3 scripts/S9_2_EP_Martin17.py --use-d15
    python3 scripts/S9_2_EP_Martin17.py --all-q-columns   # 不用聚类表，处理矩阵全部日期列
    python3 scripts/S9_2_EP_Martin17.py --no-plot         # 不写 PNG
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_EP_MARTIN17_SUBDIR,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    PRIMARY_TTMS,
    _GRID_FULL,
    clustering_multivariate_run_dir,
    ensure_results_dir,
    risk_free_simple_one_period,
)


def load_cluster(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    col_d = next((c for c in df.columns if str(c).lower() == "date"), df.columns[0])
    col_c = next((c for c in df.columns if str(c).lower() == "cluster"), None)
    if col_c is None:
        raise ValueError(f"missing Cluster: {path}")
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df[col_d], errors="coerce").dt.normalize(),
            "cluster": pd.to_numeric(df[col_c], errors="coerce").astype("Int64"),
        }
    )
    out = out.dropna(subset=["date", "cluster"])
    return out[out["cluster"].isin((0, 1))].reset_index(drop=True)


def regime_date_strings(cluster_df: pd.DataFrame, regime: str) -> List[str]:
    d = pd.to_datetime(cluster_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if regime == "OA":
        m = cluster_df["cluster"].isin((0, 1))
    elif regime == "HV":
        m = cluster_df["cluster"] == 0
    elif regime == "LV":
        m = cluster_df["cluster"] == 1
    else:
        raise ValueError(regime)
    return d[m].tolist()


def load_q_matrix(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, index_col=0)
    df.columns = [str(c).strip() for c in df.columns]
    idx = pd.to_numeric(df.index, errors="coerce")
    df = df.assign(_i=idx).dropna(subset=["_i"]).sort_values("_i").drop(columns=["_i"])
    df.index = pd.to_numeric(df.index, errors="coerce")
    df = df[~df.index.duplicated(keep="last")]
    return df.sort_index()


def default_q_matrix_path(ttm: int, *, use_d15: bool) -> Path:
    base = ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR
    suffix = "_d15" if use_d15 else ""
    return base / f"Q_matrix_{ttm}day{suffix}.csv"


def moments_q_density_btc_style(ret: np.ndarray, return_axis: np.ndarray, q_raw: np.ndarray) -> Dict[str, float]:
    """
    ``ret``: 目标积分网格（递增）；``return_axis`` / ``q_raw``：当日 Q 在原始 ``Q_matrix`` 行轴上。
    """
    q_i = np.interp(ret, return_axis, q_raw.astype(float), left=0.0, right=0.0)
    q_i = np.maximum(q_i, 0.0)
    M1 = float(np.trapz(ret * q_i, ret))
    cent = ret - M1
    M2 = float(np.trapz(cent**2 * q_i, ret))
    if (not np.isfinite(M2)) or M2 <= 0.0:
        M3 = float("nan")
        M4 = float("nan")
    else:
        M3 = float(np.trapz(cent**3 * q_i, ret) / (M2**1.5))
        M4 = float(np.trapz(cent**4 * q_i, ret) / (M2**2))
    return {"M1_rn": M1, "M2_rn": M2, "M3_rn": M3, "M4_rn": M4}


def sort_column_dates(cols: Sequence[str]) -> List[str]:
    pairs: List[Tuple[pd.Timestamp, str]] = []
    for c in cols:
        t = pd.to_datetime(c, errors="coerce")
        if pd.isna(t):
            pairs.append((pd.Timestamp.min, c))
        else:
            pairs.append((pd.Timestamp(t).normalize(), str(c)))
    pairs.sort(key=lambda x: x[0])
    return [c for _, c in pairs]


def martin17_ep_timeseries_btc_columns(panel: pd.DataFrame) -> pd.DataFrame:
    """
    BTC ``S9_lower_bound.py`` 中 Martin 序列存为 ``MB`` 的 ``Date`` / ``Lower_Bound`` 列；
    ``BP_LB.csv`` 记为 ``MLB``。此处输出 **Date + MLB** 两列，便于与 BTC 表头并列对照。
    """
    out = pd.DataFrame(
        {
            "Date": pd.to_datetime(panel["date"], errors="coerce"),
            "MLB": pd.to_numeric(panel["martin17_EP"], errors="coerce"),
        }
    )
    return out.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)


def plot_martin17_lower_bound(
    panel: pd.DataFrame,
    path: Path,
    *,
    ttm: int,
    regime_label: Optional[str],
) -> None:
    """对标 BTC ``S9_lower_bound.py`` 中三条下界图里的 **Martin（2017）红线**（此处仅 Martin 一条）。"""
    d = martin17_ep_timeseries_btc_columns(panel)
    if d.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(d["Date"], d["MLB"], label="Martin (2017) Lower Bound", color="red", linewidth=2)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlabel("Date", fontsize=18)
    ax.set_ylabel("Lower Bound", fontsize=18)
    sub = f" (τ={ttm}d, regime={regime_label})" if regime_label else f" (τ={ttm}d)"
    ax.set_title("Time-Varying ETH Premium Lower Bound (Martin 2017)" + sub, fontsize=16)
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=12, loc="upper right")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description="S9_2: Martin(2017) LB EP time series → EP/Martin17/")
    p.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    p.add_argument("--robust", action="store_true")
    p.add_argument("--cluster-csv", type=Path, default=None)
    p.add_argument("--q-matrix", type=Path, default=None)
    p.add_argument("--use-d15", action="store_true", help="Q_matrix_*_d15.csv")
    p.add_argument(
        "--regime",
        choices=("OA", "HV", "LV"),
        default="OA",
        help="Intersect Q_matrix date columns with these cluster calendar days (default OA = HV∪LV)",
    )
    p.add_argument(
        "--all-q-columns",
        action="store_true",
        help="Ignore clustering; use every column in Q_matrix (sorted by date)",
    )
    p.add_argument(
        "--no-plot",
        action="store_true",
        help="Do not write EP_Martin17_ttm{τ}day.png (default: write PNG like BTC figure)",
    )
    args = p.parse_args()
    do_plot = not args.no_plot

    cluster_path: Optional[Path] = None
    cluster_df: Optional[pd.DataFrame] = None
    if not args.all_q_columns:
        cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
        if not cluster_path.is_file():
            raise SystemExit(f"missing {cluster_path} (use --all-q-columns to skip)")
        cluster_df = load_cluster(cluster_path)

    R_f = float(risk_free_simple_one_period())
    ret_grid = np.asarray(_GRID_FULL, dtype=float)
    n_grid = int(len(ret_grid))

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        q_path = args.q_matrix or default_q_matrix_path(ttm, use_d15=args.use_d15)
        try:
            q_df = load_q_matrix(q_path)
        except FileNotFoundError as e:
            print(f"skip ttm={ttm}: {e}", file=sys.stderr)
            continue

        axis = q_df.index.to_numpy(dtype=float)
        if args.all_q_columns:
            date_cols = sort_column_dates(list(q_df.columns))
        else:
            assert cluster_df is not None
            ds = regime_date_strings(cluster_df, args.regime)
            date_cols = sorted(set(ds) & set(q_df.columns), key=lambda s: pd.to_datetime(s))

        if not date_cols:
            print(f"skip ttm={ttm}: no date columns to process", file=sys.stderr)
            continue

        rows: List[Dict[str, object]] = []
        for col in date_cols:
            mm = moments_q_density_btc_style(ret_grid, axis, q_df[col].to_numpy())
            m2 = mm["M2_rn"]
            martin = float(m2 / R_f) if np.isfinite(m2) and R_f != 0.0 else float("nan")
            dt = pd.to_datetime(col, errors="coerce")
            rows.append(
                {
                    "date": dt.normalize() if not pd.isna(dt) else pd.NaT,
                    "martin17_EP": martin,
                    **mm,
                }
            )

        panel = pd.DataFrame(rows)
        panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.normalize()
        if cluster_df is not None and not args.all_q_columns:
            panel = panel.merge(cluster_df, on="date", how="left")

        out_dir = ttm_root / ETH_EP_MARTIN17_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)
        panel_out = out_dir / f"EP_Martin17_panel_ttm{ttm}day.csv"
        panel.to_csv(panel_out, index=False, encoding="utf-8")

        ts_btc = martin17_ep_timeseries_btc_columns(panel)
        ts_out = out_dir / f"Martin17_EP_ttm{ttm}day.csv"
        ts_btc.to_csv(ts_out, index=False, encoding="utf-8")

        png_out = out_dir / f"EP_Martin17_ttm{ttm}day.png"
        if do_plot:
            plot_martin17_lower_bound(
                panel,
                png_out,
                ttm=ttm,
                regime_label=None if args.all_q_columns else args.regime,
            )

        meta: Dict[str, object] = {
            "script": "S9_2_EP_Martin17.py",
            "ttm": ttm,
            "robust": bool(args.robust),
            "q_matrix": str(q_path),
            "risk_free_one_period_R_f": R_f,
            "integral_grid": {"lo": float(ret_grid[0]), "hi": float(ret_grid[-1]), "step": 0.01, "n": n_grid},
            "regime": None if args.all_q_columns else args.regime,
            "all_q_columns": bool(args.all_q_columns),
            "cluster_csv": None if args.all_q_columns else str(cluster_path),
            "n_rows": int(len(panel)),
            "outputs": {
                "panel_csv": str(panel_out),
                "martin17_ep_timeseries_csv": str(ts_out),
                "note_MLB": "MLB column matches BP_LB.csv MLB in BTC S9_lower_bound.py (Martin segment)",
                "figure_png": str(png_out) if do_plot else None,
            },
            "reference": "martin17.md; BTC S9_lower_bound.py Martin segment (M2/R_f)",
        }
        meta_path = out_dir / f"S9_2_run_meta_ttm{ttm}day.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        print(f"ttm={ttm} regime={meta['regime']} n={len(panel)} -> {panel_out}")
        print(f"  Martin17 EP (BTC cols Date,MLB) -> {ts_out}")
        if do_plot:
            print(f"  figure -> {png_out}")
        print(panel.head(3).to_string())

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
